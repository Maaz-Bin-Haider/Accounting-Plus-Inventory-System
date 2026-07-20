#!/bin/sh
set -eu

scripts/run_quality_checks.sh
scripts/run_fast_tests.sh
scripts/run_system_tests.sh
scripts/smoke_production_stack.sh

echo "Full test suite passed."
