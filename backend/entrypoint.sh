#!/bin/sh
set -e

wait_for_db() {
    python - <<'PY'
import os
import sys
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

max_attempts = 30
attempt = 0
while attempt < max_attempts:
    try:
        from django.db import connection
        connection.ensure_connection()
        print("Database is ready.")
        sys.exit(0)
    except Exception as e:
        attempt += 1
        print(f"Waiting for database... ({attempt}/{max_attempts}): {e}")
        time.sleep(2)

print("Database did not become ready in time.")
sys.exit(1)
PY
}

echo "Waiting for database..."
wait_for_db

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Starting gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 "$@"
