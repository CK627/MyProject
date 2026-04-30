#!/bin/bash

# ============================================================
#  智慧校园服务平台 - CentOS 7.9 一键安装脚本
#  install-CentOS7.sh
#
#  安装内容:
#    - Python 3.10 (从源码编译)
#    - OpenSSL 1.1.1 (从源码编译，Python 3.10 依赖)
#    - Node.js 20 LTS (unofficial-builds，兼容 GLIBC 2.17)
#    - MySQL 8.0 客户端库
#    - Redis (可选)
#    - 后端 Python 虚拟环境 + 依赖
#    - 前端 npm 依赖 + 构建
#    - 数据库迁移
#    - 防火墙放行
#
#  使用方法:
#    chmod +x install-CentOS7.sh
#    sudo ./install-CentOS7.sh
# ============================================================

set -e


# ---------- 颜色定义 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail()    { echo -e "${RED}[FAIL]${NC}  $1"; exit 1; }

# ---------- 权限检查 ----------
if [ "$EUID" -ne 0 ]; then
    fail "请使用 root 权限运行: sudo ./install-CentOS7.sh"
fi

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON_VERSION="3.10.14"
OPENSSL_VERSION="1.1.1w"
NODE_VERSION="20.18.3"

echo ""
echo "========================================================"
echo "  智慧校园服务平台 - CentOS 7.9 安装脚本"
echo "========================================================"
echo "  项目目录: $PROJECT_DIR"
echo "  Python:   $PYTHON_VERSION"
echo "  OpenSSL:  $OPENSSL_VERSION"
echo "  Node.js:  $NODE_VERSION (unofficial glibc-217)"
echo "========================================================"
echo ""

# ==========================================================
#  Step 1: 系统基础依赖
# ==========================================================
info "[1/9] 安装系统基础依赖..."

yum groupinstall -y "Development Tools" > /dev/null 2>&1 || true

yum install -y \
    gcc gcc-c++ make \
    openssl-devel bzip2-devel libffi-devel zlib-devel \
    readline-devel sqlite-devel xz-devel tk-devel \
    mysql-devel \
    wget curl git \
    > /dev/null 2>&1

success "系统基础依赖安装完成"

# ==========================================================
#  Step 2: 编译 OpenSSL 1.1.1 (Python 3.10 需要)
# ==========================================================
info "[2/9] 检查/安装 OpenSSL 1.1.1..."

if [ -f /usr/local/openssl11/lib/libssl.so ]; then
    success "OpenSSL 1.1.1 已安装"
else
    info "从源码编译 OpenSSL $OPENSSL_VERSION ..."
    cd /tmp
    wget -q "https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz"
    tar xzf "openssl-${OPENSSL_VERSION}.tar.gz"
    cd "openssl-${OPENSSL_VERSION}"
    ./config --prefix=/usr/local/openssl11 --openssldir=/usr/local/openssl11 shared > /dev/null 2>&1
    make -j "$(nproc)" > /dev/null 2>&1
    make install > /dev/null 2>&1
    echo "/usr/local/openssl11/lib" > /etc/ld.so.conf.d/openssl11.conf
    ldconfig
    cd "$PROJECT_DIR"
    rm -rf "/tmp/openssl-${OPENSSL_VERSION}" "/tmp/openssl-${OPENSSL_VERSION}.tar.gz"
    success "OpenSSL $OPENSSL_VERSION 安装成功"
fi

# ==========================================================
#  Step 3: 安装 Python 3.10
# ==========================================================
info "[3/9] 检查/安装 Python 3.10..."

if command -v python3.10 &> /dev/null; then
    PYTHON_CURRENT=$(python3.10 --version 2>&1 | awk '{print $2}')
    success "Python 3.10 已安装 (${PYTHON_CURRENT})"
else
    info "从源码编译安装 Python $PYTHON_VERSION (链接 OpenSSL 1.1.1) ..."
    cd /tmp
    
    if [ ! -f "Python-${PYTHON_VERSION}.tgz" ]; then
        wget -q "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"
    fi
    
    tar xzf "Python-${PYTHON_VERSION}.tgz"
    cd "Python-${PYTHON_VERSION}"
    
    export CFLAGS="-I/usr/local/openssl11/include"
    export LDFLAGS="-L/usr/local/openssl11/lib -Wl,-rpath,/usr/local/openssl11/lib"
    
    ./configure --enable-optimizations --prefix=/usr/local \
        --with-openssl=/usr/local/openssl11 > /dev/null 2>&1
    make -j "$(nproc)" > /dev/null 2>&1
    make altinstall > /dev/null 2>&1
    
    unset CFLAGS LDFLAGS
    cd "$PROJECT_DIR"
    rm -rf "/tmp/Python-${PYTHON_VERSION}" "/tmp/Python-${PYTHON_VERSION}.tgz"
    
    # 验证
    if command -v python3.10 &> /dev/null; then
        success "Python $(python3.10 --version 2>&1 | awk '{print $2}') 安装成功"
    else
        fail "Python 3.10 安装失败"
    fi
fi

# 确保 pip 可用
python3.10 -m ensurepip --upgrade > /dev/null 2>&1 || true
python3.10 -m pip install --upgrade pip > /dev/null 2>&1

# ==========================================================
#  Step 4: 安装 Node.js 20 (unofficial-builds, 兼容 GLIBC 2.17)
# ==========================================================
info "[4/9] 检查/安装 Node.js ${NODE_VERSION}..."

if command -v node &> /dev/null; then
    NODE_CURRENT=$(node --version)
    NODE_MAJOR_VER=$(echo "$NODE_CURRENT" | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_MAJOR_VER" -ge 20 ]; then
        success "Node.js 已安装 (${NODE_CURRENT})"
    else
        warn "Node.js 版本过低 (${NODE_CURRENT})，需要 v20+，正在升级..."
        rm -f /usr/local/bin/node /usr/local/bin/npm /usr/local/bin/npx
        NEED_NODE=1
    fi
else
    NEED_NODE=1
fi

if [ "${NEED_NODE:-0}" = "1" ]; then
    info "下载 Node.js v${NODE_VERSION} unofficial-builds (glibc-217)..."
    cd /tmp
    wget -q "https://unofficial-builds.nodejs.org/download/release/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64-glibc-217.tar.gz" \
        -O node-v${NODE_VERSION}.tar.gz
    tar xzf "node-v${NODE_VERSION}.tar.gz"
    rm -rf /usr/local/node-v* 2>/dev/null
    mv "node-v${NODE_VERSION}-linux-x64-glibc-217" /usr/local/
    ln -sf "/usr/local/node-v${NODE_VERSION}-linux-x64-glibc-217/bin/node" /usr/local/bin/node
    ln -sf "/usr/local/node-v${NODE_VERSION}-linux-x64-glibc-217/bin/npm" /usr/local/bin/npm
    ln -sf "/usr/local/node-v${NODE_VERSION}-linux-x64-glibc-217/bin/npx" /usr/local/bin/npx
    rm -f "/tmp/node-v${NODE_VERSION}.tar.gz"
    
    if command -v node &> /dev/null; then
        success "Node.js $(node --version) 安装成功"
    else
        fail "Node.js 安装失败"
    fi
fi

# 确保 npm 可用
if ! command -v npm &> /dev/null; then
    fail "npm 未安装，请检查 Node.js 安装"
fi
success "npm $(npm --version) 可用"

# ==========================================================
#  Step 4: 安装 Redis (可选)
# ==========================================================
info "[5/9] 检查/安装 Redis..."

if command -v redis-server &> /dev/null; then
    success "Redis 已安装"
else
    yum install -y epel-release > /dev/null 2>&1 || true
    yum install -y redis > /dev/null 2>&1
    
    if command -v redis-server &> /dev/null; then
        success "Redis 安装成功"
    else
        warn "Redis 安装失败（非必需，跳过）"
    fi
fi

# 启动 Redis
if command -v redis-server &> /dev/null; then
    systemctl enable redis > /dev/null 2>&1 || true
    systemctl start redis > /dev/null 2>&1 || true
    success "Redis 服务已启动"
fi

# ==========================================================
#  Step 5: 配置后端 Python 虚拟环境
# ==========================================================
info "[6/9] 配置后端 Python 虚拟环境..."

cd "$PROJECT_DIR/backend"

if [ ! -d "venv" ]; then
    python3.10 -m venv venv
    success "Python 虚拟环境已创建"
else
    success "Python 虚拟环境已存在"
fi

# 激活虚拟环境并安装依赖
source venv/bin/activate
pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ > /dev/null 2>&1
# greenlet 1.1.3 有预编译 wheel，避免 GCC 4.8 C++11 兼容性问题
pip install greenlet==1.1.3 -i https://mirrors.aliyun.com/pypi/simple/ > /dev/null 2>&1
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ > /dev/null 2>&1

success "后端 Python 依赖安装完成"

# 验证关键依赖
python -c "import fastapi; import uvicorn; import sqlalchemy; import pymysql; import httpx; print('关键依赖验证通过')" 2>/dev/null \
    && success "后端依赖验证通过" \
    || fail "后端依赖验证失败"

deactivate

# ==========================================================
#  Step 6: 安装前端依赖并构建
# ==========================================================
info "[7/9] 安装前端 npm 依赖..."

cd "$PROJECT_DIR"
npm config set registry https://registry.npmmirror.com
npm install > /dev/null 2>&1
success "前端 npm 依赖安装完成"

info "构建前端生产版本..."
npm run build > /dev/null 2>&1
success "前端构建完成"

# ==========================================================
#  Step 7: 数据库迁移
# ==========================================================
info "[8/9] 执行数据库迁移..."

cd "$PROJECT_DIR/backend"
source venv/bin/activate

if python add_auth_columns.py 2>/dev/null; then
    success "数据库迁移完成"
else
    warn "数据库迁移失败（可能数据库不可达或已是最新状态）"
fi

deactivate

# ==========================================================
#  Step 8: 防火墙配置
# ==========================================================
info "[9/9] 配置防火墙..."

if command -v firewall-cmd &> /dev/null && systemctl is-active firewalld > /dev/null 2>&1; then
    firewall-cmd --permanent --add-port=80/tcp   > /dev/null 2>&1 || true
    firewall-cmd --permanent --add-port=8000/tcp > /dev/null 2>&1 || true
    firewall-cmd --reload > /dev/null 2>&1 || true
    success "防火墙已放行端口 80 (前端) 和 8000 (后端API)"
else
    warn "firewalld 未运行，跳过防火墙配置"
fi

# ==========================================================
#  设置脚本权限
# ==========================================================
chmod +x "$PROJECT_DIR/start-CentOS7.sh" 2>/dev/null || true
chmod +x "$PROJECT_DIR/stop-CentOS7.sh" 2>/dev/null || true

# ==========================================================
#  完成
# ==========================================================
echo ""
echo "========================================================"
echo -e "  ${GREEN}安装完成!${NC}"
echo "========================================================"
echo ""
echo "  已安装组件:"
echo "    - Python:   $(python3.10 --version 2>&1 | awk '{print $2}')"
echo "    - Node.js:  $(node --version 2>/dev/null || echo '未安装')"
echo "    - npm:      $(npm --version 2>/dev/null || echo '未安装')"
echo "    - Redis:    $(redis-server --version 2>/dev/null | awk '{print $3}' | tr -d 'v=' || echo '未安装')"
echo ""
echo "  配置文件 (请确认已正确填写):"
echo "    - 后端: $PROJECT_DIR/backend/.env"
echo "    - 前端: $PROJECT_DIR/.env.local"
echo ""
echo "  启动服务:"
echo "    cd $PROJECT_DIR"
echo "    ./start-CentOS7.sh"
echo ""
echo "  停止服务:"
echo "    ./stop-CentOS7.sh"
echo ""
echo "  访问地址:"
echo "    前端: http://<服务器IP>:80"
echo "    API:  http://<服务器IP>:8000/docs"
echo ""
echo "========================================================"
