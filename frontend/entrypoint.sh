#!/bin/sh
PORT="${PORT:-80}"
BACKEND_URL="${BACKEND_URL:-http://backend:8000}"
export PORT BACKEND_URL
envsubst '${PORT} ${BACKEND_URL}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
