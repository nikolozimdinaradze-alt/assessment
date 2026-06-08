#!/bin/sh
set -e

echo "Running app with uvicorn"
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

exec "$@"
