#!/bin/sh
set -eu

python -m coverage erase
python -m coverage run manage.py test \
    --settings=financee.test_settings \
    --noinput \
    --verbosity="${TEST_VERBOSITY:-1}"
python -m coverage report
