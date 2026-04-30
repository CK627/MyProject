#!/bin/bash

# ============================================================
#  智慧校园服务平台 - MacOS 卸载/清理脚本
# ============================================================

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo "========================================"
echo "  智慧校园服务平台 - 卸载与环境清理 (MacOS)"
echo "========================================"
echo "  项目目录: $PROJECT_DIR"
echo ""

echo "警告: 此操作将删除前端 node_modules, .next 构建缓存, 后端 venv 虚拟环境, Python 缓存以及所有日志文件。"
echo "注意: 数据库文件 (campus.db) 和用户上传的附件将保留。"
read -p "确认要执行清理吗？(y/n): " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "已取消清理操作。"
    exit 0
fi

echo ""
echo "[1/4] 正在停止正在运行的服务..."
sh "$PROJECT_DIR/scripts/MacOS/stop.sh"

echo "[2/4] 清理前端环境和构建文件..."
cd "$PROJECT_DIR"
if [ -d "node_modules" ]; then
    rm -rf node_modules
    echo "   ✓ 已删除 node_modules"
fi
if [ -d ".next" ]; then
    rm -rf .next
    echo "   ✓ 已删除 .next 构建缓存"
fi

echo "[3/4] 清理后端环境和缓存..."
cd "$PROJECT_DIR/backend"
if [ -d "venv" ]; then
    rm -rf venv
    echo "   ✓ 已删除后端 venv 虚拟环境"
fi
# 删除所有 __pycache__ 目录
find "$PROJECT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
echo "   ✓ 已清理 Python 缓存 (__pycache__)"

echo "[4/4] 清理日志文件..."
rm -f "$PROJECT_DIR"/*.log
echo "   ✓ 已删除日志文件"

echo ""
echo "========================================"
echo "  环境清理完成！"
echo "  现在你可以将整个项目目录打包分享给他人了。"
echo "========================================"
