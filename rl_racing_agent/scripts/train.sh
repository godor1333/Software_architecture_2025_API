#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export $(grep -v '^#' .env | xargs) 2>/dev/null || true

echo "[train] starting offline training..."
python -m agent.trainer
echo "[train] done. model saved to models/"