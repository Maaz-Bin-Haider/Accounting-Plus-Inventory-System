#!/bin/sh
# Disaster-recovery drill: proves a full database restore AND the production
# application-rollback mechanism using only throwaway containers. It never
# connects to EC2, never touches the production database, and cleans up after
# itself. Run it on any machine with Docker before relying on the CD pipeline.
#
# Scope (DRILL_SCOPE): "all" (default), "db" (restore only), or "rollback" only.
# Env:
#   BACKUP_FILE   backup to restore (default: newest db_backup_*.sql in repo).
#                 A .dump is restored with pg_restore, a .sql with psql.
#   DRILL_IMAGE   prebuilt "good" web image to reuse (default: build from Dockerfile).
#   DRILL_PORT    host port for the rollback stack's nginx (default: 18090).
set -eu

DRILL_SCOPE="${DRILL_SCOPE:-all}"
DRILL_PORT="${DRILL_PORT:-18090}"
PROJECT="financee-drill"
PG_IMAGE="postgres:16@sha256:eb4759788a2182f08257135e61a34f2cfc3c2914079f3465d64ee62350f4d081"
DB_CONTAINER="${PROJECT}-db"
GOOD_IMAGE="${DRILL_IMAGE:-financee:drill-good}"
BROKEN_IMAGE="financee:drill-broken"
BUILT_GOOD_IMAGE=0

log() { echo "== drill: $1"; }
die() { echo "DRILL FAILED: $1" >&2; exit 1; }

BACKUP_FILE="${BACKUP_FILE:-$(ls -1 db_backup_*.sql 2>/dev/null | sort | tail -n1 || true)}"

cleanup() {
  docker rm -f "${DB_CONTAINER}" >/dev/null 2>&1 || true
  docker compose -p "${PROJECT}" -f docker-compose.smoke.yml -f docker-compose.deploy.yml \
    down --volumes --remove-orphans >/dev/null 2>&1 || true
  docker image rm -f "${BROKEN_IMAGE}" >/dev/null 2>&1 || true
  [ "${BUILT_GOOD_IMAGE}" = 1 ] && docker image rm -f "${GOOD_IMAGE}" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

command -v docker >/dev/null 2>&1 || die "docker is required"
docker version >/dev/null 2>&1 || die "docker daemon is not available"

# ---------------------------------------------------------------------------
# Part 1: full database restore into a disposable PostgreSQL.
# ---------------------------------------------------------------------------
restore_drill() {
  [ -n "${BACKUP_FILE}" ] || die "no backup file found; set BACKUP_FILE"
  [ -f "${BACKUP_FILE}" ] || die "backup file not found: ${BACKUP_FILE}"
  log "restoring ${BACKUP_FILE} into a disposable PostgreSQL"

  docker rm -f "${DB_CONTAINER}" >/dev/null 2>&1 || true
  docker run -d --name "${DB_CONTAINER}" \
    --tmpfs /var/lib/postgresql/data \
    -e POSTGRES_DB=financee_drill \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=drill-only-password \
    "${PG_IMAGE}" >/dev/null

  log "waiting for PostgreSQL to accept connections"
  i=0
  while [ "${i}" -lt 30 ]; do
    if docker exec "${DB_CONTAINER}" pg_isready -U postgres -d financee_drill >/dev/null 2>&1; then
      break
    fi
    i=$((i + 1))
    sleep 2
  done
  docker exec "${DB_CONTAINER}" pg_isready -U postgres -d financee_drill >/dev/null 2>&1 \
    || die "disposable PostgreSQL never became ready"

  case "${BACKUP_FILE}" in
    *.dump)
      docker exec -i "${DB_CONTAINER}" pg_restore -U postgres -d financee_drill \
        --no-owner --exit-on-error < "${BACKUP_FILE}" \
        || die "pg_restore of ${BACKUP_FILE} failed"
      ;;
    *)
      docker exec -i "${DB_CONTAINER}" psql -U postgres -d financee_drill \
        -v ON_ERROR_STOP=1 < "${BACKUP_FILE}" >/dev/null \
        || die "psql restore of ${BACKUP_FILE} failed"
      ;;
  esac
  log "restore completed"

  if [ -f production_fixes.sql ]; then
    log "applying production_fixes.sql to the restored database"
    docker exec -i "${DB_CONTAINER}" psql -U postgres -d financee_drill \
      -v ON_ERROR_STOP=1 < production_fixes.sql 2>&1 \
      | grep -F "production_fixes.sql applied successfully." >/dev/null \
      || die "production_fixes.sql did not apply cleanly to the restored database"
  fi

  q() {
    docker exec "${DB_CONTAINER}" psql -U postgres -d financee_drill \
      --no-psqlrc --tuples-only --no-align -c "$1" 2>/dev/null | tr -d '[:space:]'
  }

  log "verifying restored schema and data"
  for t in parties items journalentries journallines salesinvoices purchaseinvoices; do
    exists="$(q "SELECT to_regclass('public.${t}') IS NOT NULL;")"
    [ "${exists}" = t ] || die "expected table ${t} missing after restore"
  done

  jl="$(q 'SELECT count(*) FROM journallines;')"
  [ -n "${jl}" ] && [ "${jl}" -gt 0 ] || die "journallines is empty after restore"

  balanced="$(q 'SELECT COALESCE(sum(debit),0) = COALESCE(sum(credit),0) FROM journallines;')"
  [ "${balanced}" = t ] || die "restored books do not balance (debits != credits)"

  tb="$(q "SELECT to_regclass('public.vw_trial_balance') IS NOT NULL;")"
  [ "${tb}" = t ] || die "vw_trial_balance view missing after restore"

  log "database restore drill PASSED (journallines rows=${jl}, books balanced)"
  docker rm -f "${DB_CONTAINER}" >/dev/null 2>&1 || true
}

# ---------------------------------------------------------------------------
# Part 2: application rollback mechanism against a disposable stack. Uses the
# real production override (docker-compose.deploy.yml) with RELEASE_IMAGE and
# --no-build, exactly like the CD workflow.
# ---------------------------------------------------------------------------
compose() {
  docker compose -p "${PROJECT}" \
    -f docker-compose.smoke.yml -f docker-compose.deploy.yml "$@"
}

health_ok() {
  body="$(curl --fail --silent --show-error --max-time 10 "http://127.0.0.1:${DRILL_PORT}/health/" 2>/dev/null)" || return 1
  [ "${body}" = '{"status": "ok"}' ]
}

rollback_drill() {
  log "preparing a good and a deliberately broken web image"
  if [ -z "${DRILL_IMAGE:-}" ]; then
    docker build -t "${GOOD_IMAGE}" . >/dev/null || die "failed to build the drill web image"
    BUILT_GOOD_IMAGE=1
  else
    docker image inspect "${GOOD_IMAGE}" >/dev/null 2>&1 || die "DRILL_IMAGE ${GOOD_IMAGE} not found"
  fi
  # A broken release that starts but never serves /health/, so it fails health.
  printf 'FROM %s\nCMD ["sh","-c","echo broken release; sleep 3600"]\n' "${GOOD_IMAGE}" \
    | docker build -t "${BROKEN_IMAGE}" -f - . >/dev/null || die "failed to build the broken drill image"

  export SMOKE_PORT="${DRILL_PORT}"

  log "deploying the good image as the running baseline"
  RELEASE_IMAGE="${GOOD_IMAGE}" compose up -d --wait --wait-timeout 180 \
    || die "baseline good image did not become healthy"
  health_ok || die "baseline health check failed"
  log "baseline healthy"

  log "deploying the broken release (must fail health)"
  if RELEASE_IMAGE="${BROKEN_IMAGE}" compose up -d --wait --wait-timeout 90 web nginx; then
    die "broken release unexpectedly reported healthy"
  fi
  log "broken release failed health as expected"

  log "rolling back to the good image"
  RELEASE_IMAGE="${GOOD_IMAGE}" compose up -d --wait --wait-timeout 180 web nginx \
    || die "rollback to the good image did not become healthy"
  health_ok || die "post-rollback health check failed"
  log "application rollback drill PASSED (recovered to a healthy release)"

  compose down --volumes --remove-orphans >/dev/null 2>&1 || true
}

case "${DRILL_SCOPE}" in
  all)      restore_drill; rollback_drill ;;
  db)       restore_drill ;;
  rollback) rollback_drill ;;
  *)        die "unknown DRILL_SCOPE '${DRILL_SCOPE}' (use all|db|rollback)" ;;
esac

log "disaster-recovery drill completed successfully."
