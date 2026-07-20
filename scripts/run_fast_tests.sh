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

build_option="--build"
if [ "${SKIP_DOCKER_BUILD:-0}" = "1" ]; then
    build_option=""
fi

# Intentional word splitting omits the optional flag when CI prebuilt images.
# shellcheck disable=SC2086
docker compose -f "$COMPOSE_FILE" up $build_option \
    --abort-on-container-exit \
    --exit-code-from test \
    test
