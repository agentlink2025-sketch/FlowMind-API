#!/bin/bash
set -euo pipefail

# ===== 环境变量配置 =====
# DeepSeek API Key - 可以通过环境变量或直接在这里设置
DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-sk-5ec306ca459349a4b9caa8e20454b4be}"
export DEEPSEEK_API_KEY

# 服务器配置
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
WORKERS="${WORKERS:-2}"

# ===== 虚拟环境检查 =====
# 检查虚拟环境是否存在
if [ ! -d "myprojectenv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv myprojectenv
fi

# 激活虚拟环境
source myprojectenv/bin/activate

# ===== 依赖安装 =====
# 安装依赖（如果存在 requirements.txt）
if [ -f requirements.txt ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt -i https://mirror.sjtu.edu.cn/pypi/web/simple
fi

# ===== 启动服务 =====
echo "Starting FastAPI server..."
echo "API Key configured: ${DEEPSEEK_API_KEY:0:10}..."
echo "Server will run on http://$HOST:$PORT with $WORKERS workers"

# 停止可能存在的旧进程
pkill -f uvicorn 2>/dev/null || true
sleep 2

exec python -m uvicorn app:app --host "$HOST" --port "$PORT" --workers "$WORKERS"