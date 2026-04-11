#!/bin/bash

# ============================================================
#  智慧校园服务平台 - CentOS 7 启动脚本
#  使用 venv 内的 Python 直接运行，避免 PATH 问题
# ============================================================

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
BACKEND_PORT=8000
FRONTEND_PORT=80
BACKEND_LOG="$PROJECT_DIR/backend.log"
FRONTEND_LOG="$PROJECT_DIR/frontend.log"
PID_DIR="$PROJECT_DIR/.pids"

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "========================================"
echo "  智慧校园服务平台 - 启动"
echo "========================================"
echo "  项目目录: $PROJECT_DIR"
echo ""

# 创建 PID 目录
mkdir -p "$PID_DIR"

# ---------- 停止已有进程 ----------
echo "[1/4] 停止已有服务..."
if [ -f "$PID_DIR/backend.pid" ]; then
    OLD_PID=$(cat "$PID_DIR/backend.pid")
    kill "$OLD_PID" 2>/dev/null && echo "   已停止旧后端进程 (PID: $OLD_PID)"
    rm -f "$PID_DIR/backend.pid"
fi
if [ -f "$PID_DIR/frontend.pid" ]; then
    OLD_PID=$(cat "$PID_DIR/frontend.pid")
    kill "$OLD_PID" 2>/dev/null && echo "   已停止旧前端进程 (PID: $OLD_PID)"
    rm -f "$PID_DIR/frontend.pid"
fi
# 兜底清理
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "next-server" 2>/dev/null
sleep 2

# ---------- 查找 Python ----------
VENV_PYTHON="$BACKEND_DIR/venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    # 尝试 python3.10
    if command -v python3.10 &> /dev/null; then
        VENV_PYTHON="python3.10"
    elif command -v python3 &> /dev/null; then
        VENV_PYTHON="python3"
    else
        echo -e "   ${RED}✗ 找不到 Python，请先运行 install-CentOS7.sh${NC}"
        exit 1
    fi
fi

# ---------- 启动后端 ----------
echo "[2/4] 启动后端服务 (端口: $BACKEND_PORT)..."
cd "$BACKEND_DIR"

# 使用 venv 的 python -m uvicorn 方式启动，彻底避免 PATH 问题
nohup "$VENV_PYTHON" -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_DIR/backend.pid"
sleep 3

if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ 后端启动成功 (PID: $BACKEND_PID)${NC}"
else
    echo -e "   ${RED}✗ 后端启动失败，请检查日志: $BACKEND_LOG${NC}"
    echo "   最后10行日志:"
    tail -10 "$BACKEND_LOG" 2>/dev/null
    exit 1
fi

# ---------- 启动前端 ----------
echo "[3/4] 启动前端服务 (端口: $FRONTEND_PORT)..."
cd "$PROJECT_DIR"

# 检查是否已构建
if [ ! -d ".next" ]; then
    echo "   前端未构建，正在执行 npm run build ..."
    npm run build > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo -e "   ${RED}✗ 前端构建失败${NC}"
        exit 1
    fi
fi

nohup npx next start -p "$FRONTEND_PORT" > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$PID_DIR/frontend.pid"
sleep 5

if ps -p $FRONTEND_PID > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ 前端启动成功 (PID: $FRONTEND_PID)${NC}"
else
    echo -e "   ${RED}✗ 前端启动失败，请检查日志: $FRONTEND_LOG${NC}"
    echo "   最后10行日志:"
    tail -10 "$FRONTEND_LOG" 2>/dev/null
    exit 1
fi

# ---------- 完成 ----------
echo "[4/4] 服务状态检查..."
echo ""
echo "========================================"
echo -e "  ${GREEN}服务已启动${NC}"
echo "========================================"
echo "  后端 API:  http://localhost:$BACKEND_PORT"
echo "  前端访问:  http://localhost:$FRONTEND_PORT"
echo "  API 文档:  http://localhost:$BACKEND_PORT/docs"
echo "========================================"
echo ""
echo "  PID 文件:  $PID_DIR/"
echo "  后端日志:  $BACKEND_LOG"
echo "  前端日志:  $FRONTEND_LOG"
echo ""
echo "  停止服务:  ./stop-CentOS7.sh"
echo ""
