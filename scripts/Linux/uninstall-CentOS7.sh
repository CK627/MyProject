#!/bin/bash

# ============================================================
#  智慧校园服务平台 - CentOS 7 卸载/清理脚本
# ============================================================

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  智慧校园服务平台 - 卸载与环境清理 (Linux)${NC}"
echo -e "${YELLOW}========================================${NC}"
echo -e "  项目目录: $PROJECT_DIR"
echo ""

echo -e "${RED}警告: 此操作将删除前端 node_modules, .next 构建缓存, 后端 venv 虚拟环境, Python 缓存以及所有日志文件。${NC}"
echo -e "${RED}注意: 数据库文件 (campus.db) 和用户上传的附件将保留。${NC}"
read -p "确认要执行清理吗？(y/n): " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo -e "${GREEN}已取消清理操作。${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}[1/4] 正在停止正在运行的服务...${NC}"
sh "$PROJECT_DIR/scripts/Linux/stop-CentOS7.sh"

echo -e "${YELLOW}[2/4] 清理前端环境和构建文件...${NC}"
cd "$PROJECT_DIR"
if [ -d "node_modules" ]; then
    rm -rf node_modules
    echo -e "  ${GREEN}✓ 已删除 node_modules${NC}"
fi
if [ -d ".next" ]; then
    rm -rf .next
    echo -e "  ${GREEN}✓ 已删除 .next 构建缓存${NC}"
fi

echo -e "${YELLOW}[3/4] 清理后端环境和缓存...${NC}"
cd "$PROJECT_DIR/backend"
if [ -d "venv" ]; then
    rm -rf venv
    echo -e "  ${GREEN}✓ 已删除后端 venv 虚拟环境${NC}"
fi
# 删除所有 __pycache__ 目录
find "$PROJECT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
echo -e "  ${GREEN}✓ 已清理 Python 缓存 (__pycache__)${NC}"

echo -e "${YELLOW}[4/4] 清理日志文件...${NC}"
rm -f "$PROJECT_DIR"/*.log
echo -e "  ${GREEN}✓ 已删除日志文件${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  环境清理完成！${NC}"
echo -e "${GREEN}  现在你可以将整个项目目录打包分享给他人了。${NC}"
echo -e "${GREEN}========================================${NC}"
