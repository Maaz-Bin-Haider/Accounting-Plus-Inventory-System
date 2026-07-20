#!/bin/sh
set -eu

COMPOSE_FILE="docker-compose.test.yml"

mkdir -p artifacts

cleanup() {
    docker compose -f "$COMPOSE_FILE" down --volumes --remove-orphans
}
trap cleanup EXIT INT TERM

for script in docker/entrypoint.sh scripts/*.sh; do
    sh -n "$script"
done

docker compose -f docker-compose.test.yml config --quiet
docker compose -f docker-compose.system-test.yml config --quiet
docker compose -f docker-compose.smoke.yml config --quiet

if [ "${SKIP_DOCKER_BUILD:-0}" != "1" ]; then
    docker compose -f "$COMPOSE_FILE" build test
fi
docker compose -f "$COMPOSE_FILE" run --rm --no-deps test \
    python -m compileall -q \
    accountsReports authentication contra financee home items parties \
    payments purchase purchaseReturn receipts sale saleReturn system_tests

docker compose -f "$COMPOSE_FILE" run --rm --no-deps test \
    python manage.py check --settings=financee.test_settings --fail-level WARNING

docker compose -f "$COMPOSE_FILE" run --rm --no-deps \
    -e SECRET_KEY=ci-deployment-check-key-only-7d9a3e6b4c1f8a2d5e0b9c6f3a7d4e1b \
    -e ALLOWED_HOSTS=swisstechfinance.com,www.swisstechfinance.com \
    -e CSRF_TRUSTED_ORIGINS=https://swisstechfinance.com,https://www.swisstechfinance.com \
    -e SECURE_SSL_REDIRECT=True \
    -e SESSION_COOKIE_SECURE=True \
    -e CSRF_COOKIE_SECURE=True \
    -e SECURE_HSTS_SECONDS=31536000 \
    -e SECURE_HSTS_INCLUDE_SUBDOMAINS=True \
    -e SECURE_HSTS_PRELOAD=True \
    -e TRUST_X_FORWARDED_PROTO=True \
    test python manage.py check --deploy --settings=financee.settings \
    --fail-level WARNING

echo "Syntax, configuration, and Django checks passed."
