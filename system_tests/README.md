# Isolated database system tests

This folder contains destructive integration tests for the accounting and inventory
stored procedures. The runner never uses the Django `.env` database. It creates a
new PostgreSQL database whose name starts with `financee_test_`, restores the
repository SQL backup into it, applies `production_fixes.sql`, removes all restored
business and user data, and retains only the seven named core ledger accounts.
It then creates its own fixtures, runs the scenarios, and writes `RESULTS.md` in
this folder.

## Requirements

- A local PostgreSQL server (`localhost`, `127.0.0.1`, or a Unix socket)
- `createdb`/`dropdb` permission for the supplied PostgreSQL user
- `psql` on `PATH`
- Python package `psycopg2` (installed by `pip install -r requirements.txt`)

The restore remaps the backup's `postgres` object ownership to `TEST_PGUSER` in
memory. It does not modify the backup or create server-wide roles.

## Run

The supported, fully isolated command is:

```bash
scripts/run_system_tests.sh
```

It starts PostgreSQL 16 without a host port or persistent volume, runs the
suite in a container with `psql`, and always removes the disposable stack.

For development against an existing local PostgreSQL installation, run:

```bash
python3 system_tests/run_system_tests.py
```

Connection settings can be supplied without changing application configuration:

```bash
TEST_PGHOST=localhost TEST_PGPORT=5432 TEST_PGUSER=postgres \
TEST_PGPASSWORD=postgres python3 system_tests/run_system_tests.py
```

By default the temporary database is removed even if tests fail. To inspect it:

```bash
python3 system_tests/run_system_tests.py --keep-db
```

The generated report is `system_tests/RESULTS.md`. A nonzero process exit status
means at least one test failed or the test environment could not be created.

## Safety

The runner refuses non-local PostgreSQL hosts and refuses database names without
the `financee_test_` prefix. It restores only into the database it created. It does
not import or read Django production database settings. The only non-loopback
hostname accepted is the fixed `system-test-db` service in the isolated Compose
stack.
