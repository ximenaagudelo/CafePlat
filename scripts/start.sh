#!/usr/bin/env bash
set -euo pipefail

# Las migraciones corren en el build (render.yaml), no en cada arranque.
exec gunicorn \
  --bind "0.0.0.0:${PORT:-10000}" \
  --workers 1 \
  --threads 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  run:app
