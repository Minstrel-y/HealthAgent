#!/bin/sh
# 康鉴智航｜一键启动（开发模式）
# 后端 FastAPI: http://127.0.0.1:8000   （被占用时改用 BACKEND_PORT=8123 ./start_dev.sh）
# 前端 Vue:     http://127.0.0.1:5173
set -e
cd "$(dirname "$0")"

BACKEND_PORT="${BACKEND_PORT:-8000}"
VITE_API_TARGET="http://127.0.0.1:${BACKEND_PORT}"

echo "==> 启动后端 :${BACKEND_PORT}"
cd backend
# 优先用项目自带 .venv，其次用 WorkBuddy 隔离环境（已装 fastapi/dashscope 等）
if [ -x .venv/bin/python ]; then
  PY=".venv/bin/python"
elif [ -x /Users/zhangzhipeng/.workbuddy/binaries/python/envs/default/bin/python ]; then
  PY="/Users/zhangzhipeng/.workbuddy/binaries/python/envs/default/bin/python"
else
  PY="python3"
fi
"${PY}" -m uvicorn main:app --host 127.0.0.1 --port "${BACKEND_PORT}" --reload &
BACKEND_PID=$!

echo "==> 启动前端 :5173"
cd ../frontend
# Vite 启动会清理旧的依赖预构建缓存，本机安全策略会拦截删除操作导致崩溃。
# 解决：先把缓存目录改名移走（不删除），缓存被重建后再由系统统一回收。
if [ -d node_modules/.vite ]; then
  mv node_modules/.vite "node_modules/.vite_old_$(date +%s)" 2>/dev/null || true
fi
VITE_API_TARGET="${VITE_API_TARGET}" npm run dev

# 前端退出时一起收掉后端
trap "kill ${BACKEND_PID} 2>/dev/null" EXIT
wait ${BACKEND_PID}
