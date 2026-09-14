#!/bin/sh
PORT="${PORT:-80}"
BACKEND_URL="${BACKEND_URL:-https://arabic-home-system-backend-6tpv-production.up.railway.app}"
if [ "$BACKEND_URL" = "http://backend:8000" ] || [ "$BACKEND_URL" = "http://backend:8000/api" ]; then
  BACKEND_URL="https://arabic-home-system-backend-6tpv-production.up.railway.app"
fi
BACKEND_URL="${BACKEND_URL%/}"
BACKEND_URL="${BACKEND_URL%/api}"
export PORT BACKEND_URL
envsubst '${PORT} ${BACKEND_URL}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
