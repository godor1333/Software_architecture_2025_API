<<<<<<< HEAD
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export $(grep -v '^#' .env | xargs) 2>/dev/null || true

echo "[train] starting offline training..."
python -m agent.trainer
=======
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export $(grep -v '^#' .env | xargs) 2>/dev/null || true

echo "[train] starting offline training..."
python -m agent.trainer
>>>>>>> 0037982a52b70d8ed1ac0df57ec0f7ee8fcf872b
echo "[train] done. model saved to models/"