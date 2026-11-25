#!/bin/sh
# Entrypoint: "serve" (default) starts the API; anything else is executed as a command,
# e.g.  docker compose run --rm api pytest
set -e

if [ "$1" = "serve" ]; then
  exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-4000}" \
    --proxy-headers \
    --forwarded-allow-ips="*"
fi

exec "$@"
