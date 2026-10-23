#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export $(grep -v '^#' .env | xargs) 2>/dev/null || true

echo "[serve] starting FastAPI on :${API_PORT:-8000}"
uvicorn api.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}" --reload