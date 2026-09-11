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

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    echo "Ensuring configured superuser exists..."
    python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ["DJANGO_SUPERUSER_USERNAME"]
password = os.environ["DJANGO_SUPERUSER_PASSWORD"]
user, created = User.objects.get_or_create(
    username=username,
    defaults={"is_staff": True, "is_superuser": True, "is_active": True},
)
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.set_password(password)
user.save()
print("Superuser created." if created else "Superuser already exists.")
PY
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Starting gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 "$@"
