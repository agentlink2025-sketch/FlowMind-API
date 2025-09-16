#!/bin/bash
set -euo pipefail

# 安装依赖（如果存在 requirements.txt）
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
WORKERS="${WORKERS:-1}"

exec python -m uvicorn app:app --host "$HOST" --port "$PORT" --workers "$WORKERS"