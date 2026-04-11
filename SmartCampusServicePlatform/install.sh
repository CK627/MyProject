#!/bin/bash

# ============================================================
#  智慧校园服务平台 - 安装脚本
#  适用系统: CentOS / RHEL 9 (x86_64)
#  功能: 安装运行环境、配置后端、构建前端
# ============================================================

set -e

PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)
BACKEND_DIR="$PROJECT_DIR/backend"

echo "========================================"
echo "  智慧校园服务平台 安装脚本"
echo "========================================"
echo "  项目目录: $PROJECT_DIR"
echo "========================================"
echo ""

# ----------------------------------------------------------
# 1. 检测并安装 Node.js 20.x
# ----------------------------------------------------------
echo "[1/6] 检查 Node.js 环境..."

install_node() {
    echo "   安装 Node.js 20.x ..."
    curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
    # 清理旧版本冲突
    yum remove -y npm nodejs-full-i18n 2>/dev/null || true
    yum install -y nodejs --allowerasing
}

if command -v node &>/dev/null; then
    NODE_MAJOR=$(node -v | cut -d'.' -f1 | tr -d 'v')
    if [ "$NODE_MAJOR" -lt 18 ]; then
        echo "   当前 Node.js $(node -v) 版本过低，需要 >= 18"
        install_node
    else
        echo "   ✓ Node.js $(node -v) 已安装"
    fi
else
    install_node
fi

echo "   Node.js: $(node -v)"
echo "   npm:     $(npm -v)"
echo ""

# ----------------------------------------------------------
# 2. 检测并安装 Python 3 + venv
# ----------------------------------------------------------
echo "[2/6] 检查 Python 环境..."

if command -v python3 &>/dev/null; then
    echo "   ✓ Python3 $(python3 --version | awk '{print $2}') 已安装"
else
    echo "   安装 Python3 ..."
    yum install -y python3 python3-pip python3-venv
fi

# 安装 venv 模块（部分系统需单独安装）
python3 -c "import venv" 2>/dev/null || yum install -y python3-venv 2>/dev/null || true
echo ""

# ----------------------------------------------------------
# 3. 配置后端 Python 虚拟环境 + 依赖
# ----------------------------------------------------------
echo "[3/6] 配置后端环境..."

cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    echo "   创建 Python 虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "   安装后端依赖..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "   ✓ 后端依赖安装完成"
deactivate
echo ""

# ----------------------------------------------------------
# 4. 配置后端数据库连接（交互式）
# ----------------------------------------------------------
echo "[4/6] 配置数据库连接..."

CONFIG_FILE="$BACKEND_DIR/app/config.py"

if [ -f "$CONFIG_FILE" ]; then
    echo "   检测到已有配置文件: $CONFIG_FILE"
    read -p "   是否重新配置数据库? (y/N): " RECONFIG
    if [ "$RECONFIG" = "y" ] || [ "$RECONFIG" = "Y" ]; then
        read -p "   数据库地址 [localhost]: " INPUT_DB_HOST
        DB_HOST=${INPUT_DB_HOST:-localhost}

        read -p "   数据库端口 [3306]: " INPUT_DB_PORT
        DB_PORT=${INPUT_DB_PORT:-3306}

        read -p "   数据库用户 [root]: " INPUT_DB_USER
        DB_USER=${INPUT_DB_USER:-root}

        read -sp "   数据库密码: " DB_PASSWORD
        echo ""

        read -p "   数据库名称 [smart_campus]: " INPUT_DB_NAME
        DB_NAME=${INPUT_DB_NAME:-smart_campus}

        read -p "   JWT密钥 [自动生成]: " INPUT_JWT_KEY
        JWT_KEY=${INPUT_JWT_KEY:-$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")}

        cat > "$CONFIG_FILE" << PYEOF
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # 数据库配置
    DB_HOST: str = "$DB_HOST"
    DB_PORT: int = $DB_PORT
    DB_USER: str = "$DB_USER"
    DB_PASSWORD: str = "$DB_PASSWORD"
    DB_NAME: str = "$DB_NAME"

    # JWT配置
    SECRET_KEY: str = "$JWT_KEY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # 应用配置
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
PYEOF
        echo "   ✓ 数据库配置已更新"
    else
        echo "   跳过，使用现有配置"
    fi
else
    echo "   ✗ 未找到配置文件，请手动配置 $CONFIG_FILE"
fi
echo ""

# ----------------------------------------------------------
# 5. 安装前端依赖
# ----------------------------------------------------------
echo "[5/6] 安装前端依赖..."

cd "$PROJECT_DIR"

# 如果 node_modules 不存在或 package-lock 不存在，重新安装
if [ ! -d "node_modules" ]; then
    echo "   执行 npm install ..."
    npm install
else
    echo "   node_modules 已存在，跳过安装"
    echo "   如需重新安装，请删除 node_modules 后重新运行"
fi

echo "   ✓ 前端依赖安装完成"
echo ""

# ----------------------------------------------------------
# 6. 构建前端生产包
# ----------------------------------------------------------
echo "[6/6] 构建前端生产包..."

cd "$PROJECT_DIR"
npm run build

echo "   ✓ 前端构建完成"
echo ""

# ----------------------------------------------------------
# 完成
# ----------------------------------------------------------
echo "========================================"
echo "  安装完成!"
echo "========================================"
echo ""
echo "  启动服务:  ./start.sh"
echo "  停止服务:  ./stop.sh"
echo ""
echo "  默认端口:"
echo "    前端: 80"
echo "    后端: 8000"
echo ""
echo "  注意事项:"
echo "    1. 确保 MySQL 数据库已创建 (smart_campus)"
echo "    2. 确保 80 端口未被占用 (如被 httpd 占用，执行: systemctl stop httpd)"
echo "    3. 首次运行后端会自动建表"
echo "========================================"
