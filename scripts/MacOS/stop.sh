#!/bin/bash

# 智慧校园服务平台 - 停止脚本

echo "========================================"
echo "  智慧校园服务平台 停止脚本"
echo "========================================"

# 停止前端
echo "[1/2] 停止前端服务..."
pkill -f "next-server" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✓ 前端服务已停止"
else
    echo "   - 前端服务未运行"
fi

# 停止后端
echo "[2/2] 停止后端服务..."
pkill -f "uvicorn app.main:app" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✓ 后端服务已停止"
else
    echo "   - 后端服务未运行"
fi

sleep 1

# 检查状态
echo ""
echo "========================================"
echo "  服务状态"
echo "========================================"

if ps aux | grep -v grep | grep "next-server" > /dev/null; then
    echo "  前端: 运行中"
else
    echo "  前端: 已停止"
fi

if ps aux | grep -v grep | grep "uvicorn app.main:app" > /dev/null; then
    echo "  后端: 运行中"
else
    echo "  后端: 已停止"
fi

echo "========================================"
