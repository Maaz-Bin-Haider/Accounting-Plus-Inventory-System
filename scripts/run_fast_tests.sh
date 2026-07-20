#!/bin/sh
set -eu

COMPOSE_FILE="docker-compose.test.yml"

mkdir -p artifacts
rm -f artifacts/django-tests.log artifacts/coverage.txt \
    artifacts/coverage.xml artifacts/coverage.json

cleanup() {
    docker compose -f "$COMPOSE_FILE" down --volumes --remove-orphans
}
trap cleanup EXIT INT TERM

docker compose -f "$COMPOSE_FILE" up \
    --build \
    --abort-on-container-exit \
    --exit-code-from test \
    test
