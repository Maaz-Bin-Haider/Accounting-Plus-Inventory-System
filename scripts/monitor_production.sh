#!/bin/sh
# Production health monitor. Designed to run ON the EC2 host from the project
# directory (the monitor workflow pipes it over SSH). It checks uptime,
# container health, disk, backup freshness, PostgreSQL, and recent error volume.
# It reports every problem it finds and exits non-zero if any check fails, so a
# scheduled GitHub Actions run turns red and GitHub emails the failure. It only
# reads state; it never restarts containers or writes to the database.
set -eu

PRODUCTION_PATH=${1:-.}
MAX_BACKUP_AGE_HOURS=${MAX_BACKUP_AGE_HOURS:-26}
MIN_FREE_PERCENT=${MIN_FREE_PERCENT:-10}
LOG_WINDOW=${MONITOR_LOG_WINDOW:-30m}
MAX_ERRORS=${MONITOR_MAX_ERRORS:-25}
SERVICES="web nginx db redis"

cd "$PRODUCTION_PATH"
status=0
fail() { echo "MONITOR FAIL: $1" >&2; status=1; }

# 1. HTTP uptime through the nginx loopback health endpoint.
if body="$(curl --fail --silent --show-error --max-time 10 http://127.0.0.1/health/ 2>/dev/null)"; then
  [ "$body" = '{"status": "ok"}' ] || fail "health endpoint returned unexpected body: $body"
else
  fail "health endpoint http://127.0.0.1/health/ is unreachable"
fi

# 2. Every expected container is running and (if it has a healthcheck) healthy.
for svc in $SERVICES; do
  cid="$(docker compose ps -q "$svc" 2>/dev/null || true)"
  if [ -z "$cid" ]; then
    fail "service $svc has no container"
    continue
  fi
  running="$(docker inspect "$cid" --format '{{.State.Running}}' 2>/dev/null || echo false)"
  [ "$running" = true ] || fail "service $svc is not running"
  health="$(docker inspect "$cid" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' 2>/dev/null || echo none)"
  case "$health" in
    healthy|none) ;;
    *) fail "service $svc health is $health" ;;
  esac
done

# 3. Free disk space on the production filesystem.
free_pct="$(df -Pk "$PRODUCTION_PATH" | awk 'NR==2 {printf "%d", ($4/$2)*100}' 2>/dev/null || echo 0)"
[ "$free_pct" -ge "$MIN_FREE_PERCENT" ] || fail "low disk: ${free_pct}% free (< ${MIN_FREE_PERCENT}%)"

# 4. Backup freshness: newest dump under backups/ or backups/offsite/.
newest_epoch=0
newest_file=""
for d in backups backups/offsite; do
  [ -d "$d" ] || continue
  for f in "$d"/*.dump; do
    [ -e "$f" ] || continue
    e="$(date -u -r "$f" +%s 2>/dev/null || echo 0)"
    if [ "$e" -gt "$newest_epoch" ]; then
      newest_epoch="$e"
      newest_file="$f"
    fi
  done
done
if [ -n "$newest_file" ]; then
  age_s=$(( $(date -u +%s) - newest_epoch ))
  max_s=$(( MAX_BACKUP_AGE_HOURS * 3600 ))
  [ "$age_s" -le "$max_s" ] || fail "newest backup $newest_file is older than ${MAX_BACKUP_AGE_HOURS}h"
else
  fail "no database backup files found under backups/ or backups/offsite/"
fi

# 5. PostgreSQL is accepting connections and answers a trivial query.
if docker compose exec -T db sh -eu -c 'exec pg_isready --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' >/dev/null 2>&1; then
  one="$(docker compose exec -T db sh -eu -c 'exec psql --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --no-psqlrc --tuples-only --no-align -c "SELECT 1"' 2>/dev/null | tr -d '[:space:]' || true)"
  [ "$one" = 1 ] || fail "PostgreSQL SELECT 1 did not return 1"
else
  fail "PostgreSQL is not accepting connections"
fi

# 6. Recent error volume in the application/proxy/database logs (canary only).
for svc in web nginx db; do
  errs="$(docker compose logs --since "$LOG_WINDOW" "$svc" 2>/dev/null | grep -Eic 'traceback|critical|error|exception' || true)"
  errs="${errs:-0}"
  [ "$errs" -le "$MAX_ERRORS" ] || fail "service $svc has $errs error-like log lines in the last $LOG_WINDOW"
done

if [ "$status" -eq 0 ]; then
  echo "Production monitor: all checks passed."
fi
exit "$status"
