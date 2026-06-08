#!/bin/bash

# ============================================================
#  智慧校园服务平台 - CentOS 7 停止脚本
# ============================================================

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PID_DIR="$PROJECT_DIR/.pids"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "========================================"
echo "  智慧校园服务平台 - 停止服务"
echo "========================================"
echo ""

STOPPED=0

# 通过 PID 文件停止后端
if [ -f "$PID_DIR/backend.pid" ]; then
    PID=$(cat "$PID_DIR/backend.pid")
    if ps -p "$PID" > /dev/null 2>&1; then
        kill "$PID"
        echo -e "  ${GREEN}✓ 后端已停止 (PID: $PID)${NC}"
        STOPPED=$((STOPPED + 1))
    else
        echo -e "  ${YELLOW}~ 后端进程已不存在 (PID: $PID)${NC}"
    fi
    rm -f "$PID_DIR/backend.pid"
else
    # 兜底：按进程名查找
    PIDS=$(pgrep -f "uvicorn app.main:app" 2>/dev/null)
    if [ -n "$PIDS" ]; then
        kill $PIDS 2>/dev/null
        echo -e "  ${GREEN}✓ 后端已停止 (PID: $PIDS)${NC}"
        STOPPED=$((STOPPED + 1))
    else
        echo "  - 后端未在运行"
    fi
fi

# 通过 PID 文件停止前端
if [ -f "$PID_DIR/frontend.pid" ]; then
    PID=$(cat "$PID_DIR/frontend.pid")
    if ps -p "$PID" > /dev/null 2>&1; then
        kill "$PID"
        echo -e "  ${GREEN}✓ 前端已停止 (PID: $PID)${NC}"
        STOPPED=$((STOPPED + 1))
    else
        echo -e "  ${YELLOW}~ 前端进程已不存在 (PID: $PID)${NC}"
    fi
    rm -f "$PID_DIR/frontend.pid"
else
    PIDS=$(pgrep -f "next-server" 2>/dev/null)
    if [ -n "$PIDS" ]; then
        kill $PIDS 2>/dev/null
        echo -e "  ${GREEN}✓ 前端已停止 (PID: $PIDS)${NC}"
        STOPPED=$((STOPPED + 1))
    else
        echo "  - 前端未在运行"
    fi
fi

echo ""
if [ $STOPPED -gt 0 ]; then
    echo -e "  ${GREEN}已停止 $STOPPED 个服务${NC}"
else
    echo "  没有正在运行的服务"
fi
echo ""
