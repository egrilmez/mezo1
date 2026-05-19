#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$PWD"
HOST="${CBAM_HOST:-0.0.0.0}"
PORT="${CBAM_PORT:-8080}"
exec uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload
