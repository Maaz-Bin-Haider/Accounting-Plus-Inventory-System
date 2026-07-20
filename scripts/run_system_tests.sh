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

build_option="--build"
if [ "${SKIP_DOCKER_BUILD:-0}" = "1" ]; then
    build_option=""
fi

# Intentional word splitting omits the optional flag when CI prebuilt images.
# shellcheck disable=SC2086
docker compose -f "$COMPOSE_FILE" up $build_option \
    --abort-on-container-exit \
    --exit-code-from system-test \
    system-test
