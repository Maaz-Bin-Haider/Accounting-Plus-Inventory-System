#!/bin/sh
set -eu

COMPOSE_FILE="docker-compose.test.yml"

cleanup() {
    docker compose -f "$COMPOSE_FILE" down --volumes --remove-orphans
}
trap cleanup EXIT INT TERM

docker compose -f "$COMPOSE_FILE" up \
    --build \
    --abort-on-container-exit \
    --exit-code-from test \
    test
