#!/bin/bash

# 智慧校园服务平台 - 重启脚本（含前端重新构建）
# 自动检测项目目录（脚本所在目录）
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=80
BACKEND_LOG="$PROJECT_DIR/backend.log"
FRONTEND_LOG="$PROJECT_DIR/frontend.log"

echo "========================================"
echo "  智慧校园服务平台 重启脚本"
echo "========================================"
echo "  项目目录: $PROJECT_DIR"
echo ""

# ========== 停止服务 ==========
echo "[1/5] 停止已有服务..."

pkill -f "next-server" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✓ 前端服务已停止"
else
    echo "   - 前端服务未运行"
fi

pkill -f "uvicorn app.main:app" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✓ 后端服务已停止"
else
    echo "   - 后端服务未运行"
fi

sleep 2

# ========== 前端重新构建 ==========
echo "[2/5] 重新构建前端项目..."
cd "$PROJECT_DIR"
npm run build
if [ $? -eq 0 ]; then
    echo "   ✓ 前端构建成功"
else
    echo "   ✗ 前端构建失败，请检查错误信息"
    exit 1
fi

# ========== 启动后端 ==========
echo "[3/5] 启动后端服务 (端口: $BACKEND_PORT)..."
cd "$PROJECT_DIR/backend"
if [ -f "venv/bin/uvicorn" ]; then
    UVICORN="$PROJECT_DIR/backend/venv/bin/uvicorn"
elif command -v uvicorn &> /dev/null; then
    UVICORN="uvicorn"
else
    echo "   ✗ 找不到 uvicorn，请先运行 install.sh 或手动安装"
    exit 1
fi
nohup "$UVICORN" app.main:app --host 0.0.0.0 --port $BACKEND_PORT > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
sleep 3

# 检查后端是否启动成功
if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo "   ✓ 后端启动成功 (PID: $BACKEND_PID)"
else
    echo "   ✗ 后端启动失败，请检查日志: $BACKEND_LOG"
    exit 1
fi

# ========== 启动前端 ==========
echo "[4/5] 启动前端服务 (端口: $FRONTEND_PORT)..."
cd "$PROJECT_DIR"
nohup npm run start -- -p $FRONTEND_PORT > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
sleep 5

# 检查前端是否启动成功
if ps aux | grep -v grep | grep "next-server" > /dev/null; then
    echo "   ✓ 前端启动成功"
else
    echo "   ✗ 前端启动失败，请检查日志: $FRONTEND_LOG"
    exit 1
fi

# ========== 显示状态 ==========
echo "[5/5] 服务状态检查..."
echo ""
echo "========================================"
echo "  服务已重启"
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
