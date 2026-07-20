#!/bin/sh
set -eu

COMPOSE_FILE="docker-compose.smoke.yml"
SMOKE_PORT="${SMOKE_PORT:-18080}"
BASE_URL="http://127.0.0.1:${SMOKE_PORT}"

cleanup() {
    docker compose -f "$COMPOSE_FILE" down --volumes --remove-orphans
}
trap cleanup EXIT INT TERM

docker compose -f "$COMPOSE_FILE" up --build --detach --wait
docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -t

health_body="$(curl --fail --silent --show-error "$BASE_URL/health/")"
test "$health_body" = '{"status": "ok"}'

login_headers="$(curl --fail --silent --show-error --dump-header - --output /dev/null "$BASE_URL/authentication/login/")"
printf '%s' "$login_headers" | grep -q '200 OK'

static_headers="$(curl --fail --silent --show-error --dump-header - --output /dev/null "$BASE_URL/static/css/login_styling.css")"
printf '%s' "$static_headers" | grep -qi 'cache-control: public, immutable'

echo "Production stack smoke tests passed."
