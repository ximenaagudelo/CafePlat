#!/usr/bin/env bash
set -euo pipefail

flask --app run.py db upgrade

exec gunicorn \
  --bind "0.0.0.0:${PORT:-10000}" \
  --workers 1 \
  --threads 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  run:app
