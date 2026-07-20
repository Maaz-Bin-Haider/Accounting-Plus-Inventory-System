#!/bin/sh
set -eu

ARTIFACT_DIR="${TEST_ARTIFACT_DIR:-artifacts}"
mkdir -p "$ARTIFACT_DIR"

python -m coverage erase
set +e
python -m coverage run manage.py test \
    --settings=financee.test_settings \
    --noinput \
    --verbosity="${TEST_VERBOSITY:-1}" \
    >"$ARTIFACT_DIR/django-tests.log" 2>&1
test_status=$?
set -e

cat "$ARTIFACT_DIR/django-tests.log"

if [ -f .coverage ]; then
    set +e
    python -m coverage report >"$ARTIFACT_DIR/coverage.txt" 2>&1
    coverage_status=$?
    set -e
    cat "$ARTIFACT_DIR/coverage.txt"
    python -m coverage xml -o "$ARTIFACT_DIR/coverage.xml"
    python -m coverage json -o "$ARTIFACT_DIR/coverage.json"
else
    coverage_status=1
    printf '%s\n' "Coverage data was not created." >"$ARTIFACT_DIR/coverage.txt"
fi

if [ "$test_status" -ne 0 ]; then
    exit "$test_status"
fi
exit "$coverage_status"
