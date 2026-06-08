#!/bin/bash

# 智慧校园服务平台 - 启动脚本
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=80
BACKEND_LOG="$PROJECT_DIR/backend.log"
FRONTEND_LOG="$PROJECT_DIR/frontend.log"

echo "========================================"
echo "  智慧校园服务平台 启动脚本"
echo "========================================"
echo "  项目目录: $PROJECT_DIR"

# 停止已有进程
echo "[1/4] 停止已有服务..."
pkill -f "uvicorn" 2>/dev/null
pkill -f "next-server" 2>/dev/null
pkill -f "app.main" 2>/dev/null
# 按端口强杀（兜底）
lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null
lsof -ti :$FRONTEND_PORT | xargs kill -9 2>/dev/null
sleep 2

# 启动后端
echo "[2/4] 启动后端服务 (端口: $BACKEND_PORT)..."
cd "$PROJECT_DIR/backend"
if [ -f "venv/bin/uvicorn" ]; then
    UVICORN="$PROJECT_DIR/backend/venv/bin/uvicorn"
elif command -v uvicorn &> /dev/null; then
    UVICORN="uvicorn"
else
    echo "   ✗ 找不到 uvicorn，请先运行安装脚本"
    exit 1
fi
nohup "$UVICORN" app.main:app --host 0.0.0.0 --port $BACKEND_PORT > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# 等待端口监听，最多15秒
BACKEND_OK=0
for i in $(seq 1 15); do
    if lsof -i :$BACKEND_PORT | grep LISTEN > /dev/null 2>&1; then
        BACKEND_OK=1
        break
    fi
    sleep 1
done

if [ $BACKEND_OK -eq 1 ]; then
    echo "   ✓ 后端启动成功 (PID: $BACKEND_PID)"
else
    echo "   ✗ 后端启动失败，请检查日志: $BACKEND_LOG"
    echo ""
    echo "--- 最近日志 ---"
    tail -30 "$BACKEND_LOG"
    echo "----------------"
    exit 1
fi

# 启动前端
echo "[3/4] 启动前端服务 (端口: $FRONTEND_PORT)..."
cd "$PROJECT_DIR"
nohup npm run start -- -p $FRONTEND_PORT > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

# 等待端口监听，最多20秒
FRONTEND_OK=0
for i in $(seq 1 20); do
    if lsof -i :$FRONTEND_PORT | grep LISTEN > /dev/null 2>&1; then
        FRONTEND_OK=1
        break
    fi
    sleep 1
done

if [ $FRONTEND_OK -eq 1 ]; then
    echo "   ✓ 前端启动成功 (PID: $FRONTEND_PID)"
else
    echo "   ✗ 前端启动失败，请检查日志: $FRONTEND_LOG"
    echo ""
    echo "--- 最近日志 ---"
    tail -30 "$FRONTEND_LOG"
    echo "----------------"
    exit 1
fi

# 显示状态
echo "[4/4] 服务状态检查..."
echo ""
echo "========================================"
echo "  服务已启动"
echo "========================================"
echo "  后端 API:  http://localhost:$BACKEND_PORT"
echo "  前端访问:  http://localhost:$FRONTEND_PORT"
echo "  API 文档:  http://localhost:$BACKEND_PORT/docs"
echo "========================================"
echo ""
echo "日志文件:"
echo "  后端: $BACKEND_LOG"
echo "  前端: $FRONTEND_LOG"
echo ""
