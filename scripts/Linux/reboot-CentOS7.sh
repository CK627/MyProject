#!/bin/bash

# ============================================================
#  智慧校园服务平台 - CentOS 7 重启脚本（含重新构建）
# ============================================================

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  智慧校园服务平台 - 重启服务${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

echo -e "${YELLOW}[1/3] 正在停止已有服务...${NC}"
sh "$PROJECT_DIR/scripts/Linux/stop-CentOS7.sh"
sleep 2

echo -e "${YELLOW}[2/3] 重新构建前端项目...${NC}"
cd "$PROJECT_DIR"
npm run build
if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✓ 前端构建成功${NC}"
else
    echo -e "  ${RED}✗ 前端构建失败，请检查错误信息${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}[3/3] 正在启动服务...${NC}"
sh "$PROJECT_DIR/scripts/Linux/start-CentOS7.sh"
