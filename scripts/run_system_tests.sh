#!/bin/sh
set -eu

COMPOSE_FILE="docker-compose.system-test.yml"

mkdir -p artifacts
rm -f artifacts/postgresql-system-tests.md system_tests/RESULTS.md

cleanup() {
    if [ -f system_tests/RESULTS.md ]; then
        cp system_tests/RESULTS.md artifacts/postgresql-system-tests.md
    fi
    docker compose -f "$COMPOSE_FILE" down --volumes --remove-orphans
}
trap cleanup EXIT INT TERM

docker compose -f "$COMPOSE_FILE" up \
    --build \
    --abort-on-container-exit \
    --exit-code-from system-test \
    system-test
