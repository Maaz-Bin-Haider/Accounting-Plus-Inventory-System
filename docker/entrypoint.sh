#!/bin/sh
# Entrypoint for the web container: wait for PostgreSQL, collect static
# files into the shared volume, then start the given command (gunicorn).
set -e

echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
python - <<'PY'
import os, time, sys
import psycopg2

for attempt in range(60):
    try:
        conn = psycopg2.connect(
            host=os.environ["DB_HOST"],
            port=os.environ.get("DB_PORT", "5432"),
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            dbname=os.environ["DB_NAME"],
        )
        conn.close()
        print("PostgreSQL is ready.")
        sys.exit(0)
    except Exception as exc:
        time.sleep(2)
print("PostgreSQL did not become ready in time.", file=sys.stderr)
sys.exit(1)
PY

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting: $@"
exec "$@"
