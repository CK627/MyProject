#!/bin/bash
# jtool 安装模块（被 jtool.sh source 调用）

# 安装目录
get_install_dir() {
    case "$(uname -s)" in
        Darwin) echo "/Library/devtools/jtool" ;;
        Linux)  echo "/usr/local/devtools/jtool" ;;
    esac
}

# ============================================
# 扫描 Java 路径
# ============================================
do_scan() {
    local config_file="$1"
    local java_base_dir=""

    echo "扫描 Java 安装路径..."

    local candidates=(
        "/Library/Java/JavaVirtualMachines"
        "/usr/lib/jvm"
        "/opt/java"
    )

    for dir in "${candidates[@]}"; do
        if [ -d "$dir" ] && ls "$dir"/jdk-*.jdk &>/dev/null 2>&1; then
            java_base_dir="$dir"
            break
        fi
    done

    if [ -z "$java_base_dir" ]; then
        echo "未找到 Java 安装目录"
        read -p "请输入 Java 安装路径: " java_base_dir
        [ -d "$java_base_dir" ] || { echo "错误: 路径不存在"; return 1; }
    fi

    echo "找到: $java_base_dir"
    echo ""

    echo "已安装的 JDK:"
    for dir in "$java_base_dir"/jdk-*.jdk; do
        [ -d "$dir" ] || continue
        local version
        version=$(basename "$dir" | sed 's/jdk-//;s/\.jdk//')
        if [ -f "$dir/Contents/Home/bin/java" ]; then
            local ver
            ver=$("$dir/Contents/Home/bin/java" -version 2>&1 | head -1)
            echo "  $version - $ver"
        fi
    done

    echo ""

    mkdir -p "$(dirname "$config_file")"
    cat > "$config_file" << EOF
# jtool 配置文件

# Java 安装路径（父目录）
JAVA_BASE_DIR="$java_base_dir"

# 默认版本
# JTOOL_DEFAULT_VERSION="21"
EOF

    echo "配置文件已写入: $config_file"
    echo ""
    cat "$config_file"
}

# ============================================
# 完整安装
# ============================================
do_update() {
    local tool_name="$1"
    local branch="$2"
    local remote_url="$3"
    local install_dir="$4"
    local config_file="$5"

    local repo_dir="$HOME/.${tool_name}/repo"

    # Step 1: 确保仓库存在
    if [ ! -d "$repo_dir/.git" ]; then
        echo "首次更新，正在克隆仓库..."
        mkdir -p "$(dirname "$repo_dir")"
        git clone --branch "$branch" --single-branch --depth 1 "$remote_url" "$repo_dir" || { echo "克隆失败"; return 1; }
    fi

    # Step 2: fetch
    echo "正在检查更新..."
    git -C "$repo_dir" fetch origin "$branch" 2>/dev/null || { echo "获取更新失败，请检查网络"; return 1; }

    # Step 3: 从远程获取版本号
    local remote_version
    remote_version=$(git -C "$repo_dir" show "origin/$branch:VERSION" 2>/dev/null | tr -d '[:space:]')
    if [ -z "$remote_version" ]; then
        echo "错误: 无法获取远程版本号"
        return 1
    fi

    # Step 4: 获取本地版本号
    local version_key
    version_key=$(echo "${tool_name}_VERSION" | tr 'a-z' 'A-Z')
    local local_version=""
    if [ -f "$config_file" ]; then
        local_version=$(grep "^${version_key}=" "$config_file" 2>/dev/null | cut -d'"' -f2)
    fi

    # 首次安装（本地无版本号）时，从本地仓库读取
    if [ -z "$local_version" ] && [ -f "$repo_dir/VERSION" ]; then
        local_version=$(cat "$repo_dir/VERSION" | tr -d '[:space:]')
    fi

    if [ "$local_version" = "$remote_version" ]; then
        echo "已是最新版本 (v$local_version)"
        return 0
    fi

    echo "发现新版本: v${local_version:-未知} → v$remote_version"

    # Step 5: pull
    git -C "$repo_dir" checkout "$branch" 2>/dev/null
    git -C "$repo_dir" pull origin "$branch" || { echo "拉取更新失败"; return 1; }

    # Step 6: 复制文件到安装目录（保留用户配置）
    sudo cp "$repo_dir/bin/${tool_name}.sh" "$install_dir/bin/"
    sudo cp "$repo_dir/module/common.sh" "$install_dir/module/"
    sudo chmod +x "$install_dir/bin/${tool_name}.sh"

    # 配置文件仅首次复制
    if [ ! -f "$config_file" ]; then
        sudo cp "$repo_dir/config/${tool_name}.conf" "$config_file"
    fi

    # Step 7: 记录版本到配置文件
    if [ -w "$config_file" ]; then
        sed -i.bak "/^${version_key}/d" "$config_file" 2>/dev/null
        rm -f "${config_file}.bak" 2>/dev/null
        echo "${version_key}=\"$remote_version\"" >> "$config_file"
    else
        sudo sed -i.bak "/^${version_key}/d" "$config_file" 2>/dev/null
        sudo rm -f "${config_file}.bak" 2>/dev/null
        echo "${version_key}=\"$remote_version\"" | sudo tee -a "$config_file" > /dev/null
    fi

    # Step 8: 输出结果
    echo "更新完成！"
    echo "  版本: v${local_version:-未知} → v$remote_version"
}

do_create_shims() {
    local config_file="$1"
    local shims_dir="$HOME/.jtool/shims"

    mkdir -p "$shims_dir"

    local tools=("java" "javac" "jar" "jshell" "javadoc" "javap")
    for tool in "${tools[@]}"; do
        cat > "$shims_dir/$tool" << SHIM
#!/bin/bash
# jtool shim - auto generated
CONFIG_FILE="$config_file"
JAVA_BASE_DIR=""
JTOOL_DEFAULT_VERSION=""
if [ -f "\$CONFIG_FILE" ]; then
    while IFS='=' read -r key value; do
        [[ "\$key" =~ ^#.*$ || -z "\$key" ]] && continue
        key=\$(echo "\$key" | tr -d ' ')
        value=\$(echo "\$value" | tr -d " '\"")
        case "\$key" in
            JAVA_BASE_DIR) JAVA_BASE_DIR="\$value" ;;
            JTOOL_DEFAULT_VERSION) JTOOL_DEFAULT_VERSION="\$value" ;;
        esac
    done < "\$CONFIG_FILE"
fi
if [ -z "\$JTOOL_DEFAULT_VERSION" ]; then
    echo "jtool: 未设置默认版本，请运行 jtool use <版本号>" >&2
    exit 1
fi
VER="\$JTOOL_DEFAULT_VERSION"
[ "\$VER" = "8" ] && VER="1.8"
if [ "\$(uname -s)" = "Darwin" ]; then
    JDK_HOME="\$JAVA_BASE_DIR/jdk-\$VER.jdk/Contents/Home"
else
    JDK_HOME="\$JAVA_BASE_DIR/jdk-\$VER"
fi
if [ ! -d "\$JDK_HOME" ]; then
    echo "jtool: JDK \$JTOOL_DEFAULT_VERSION 不存在" >&2
    exit 1
fi
exec "\$JDK_HOME/bin/$tool" "\$@"
SHIM
        chmod +x "$shims_dir/$tool"
    done

    echo "Shim 已创建: $shims_dir"
}

do_install() {
    local script_dir="$1"
    local install_dir
    install_dir=$(get_install_dir)
    local bin_dir="$install_dir/bin"
    local config_dir="$install_dir/config"
    local module_dir="$install_dir/module"
    local config_file="$config_dir/jtool.conf"

    echo "========================================"
    echo "  jtool 安装程序"
    echo "========================================"
    echo ""

    echo "[1/4] 复制文件..."
    sudo mkdir -p "$bin_dir" "$config_dir" "$module_dir"
    case "$(uname -s)" in
        Darwin|Linux)
            sudo cp "$script_dir/bin/jtool.sh" "$bin_dir/"
            ;;
        *)
            sudo cp "$script_dir/bin/jtool.bat" "$bin_dir/"
            ;;
    esac
    sudo cp "$script_dir/config/jtool.conf" "$config_dir/"
    sudo cp "$script_dir/module/common.sh" "$module_dir/"
    echo "完成"
    echo ""

    echo "[2/4] 设置权限..."
    sudo chmod +x "$bin_dir/jtool.sh"
    echo "完成"
    echo ""

    echo "[3/5] 扫描 Java..."
    do_scan "$config_file"
    sudo chmod 666 "$config_file"
    # 写入版本号
    if [ -f "$script_dir/VERSION" ]; then
        local ver
        ver=$(cat "$script_dir/VERSION" | tr -d '[:space:]')
        echo "JTOOL_VERSION=\"$ver\"" >> "$config_file"
    fi
    echo ""

    echo "[4/5] 创建 shim..."
    do_create_shims "$config_file"
    echo ""

    echo "[5/5] 配置 PATH..."
    local shims_dir="$HOME/.jtool/shims"
    local shell_rc="$HOME/.zshrc"
    [ -f "$HOME/.bashrc" ] && shell_rc="$HOME/.bashrc"

    if ! grep -q "jtool" "$shell_rc" 2>/dev/null; then
        echo "" >> "$shell_rc"
        echo "# jtool" >> "$shell_rc"
        echo "export PATH=\"$shims_dir:$bin_dir:\$PATH\"" >> "$shell_rc"
        echo "已添加到 $shell_rc"
    else
        echo "已存在"
    fi

    export PATH="$shims_dir:$bin_dir:$PATH"

    echo ""
    echo "========================================"
    echo "  安装完成！"
    echo "========================================"
    echo ""
    echo "安装目录: $install_dir"
    echo "配置文件: $config_file"
    echo "执行 source $shell_rc 或重新打开终端"
}

# ============================================
# 卸载
# ============================================
do_uninstall() {
    local install_dir
    install_dir=$(get_install_dir)

    echo "========================================"
    echo "  jtool 卸载程序"
    echo "========================================"
    echo ""

    read -p "确定要卸载吗？(y/n): " confirm
    [ "$confirm" != "y" ] && [ "$confirm" != "Y" ] && { echo "已取消"; return 0; }

    echo ""

    if [ -d "$install_dir" ]; then
        sudo rm -rf "$install_dir"
        echo "已删除: $install_dir"
    else
        echo "安装目录不存在"
    fi

    # 清理 shims
    local shims_dir="$HOME/.jtool/shims"
    if [ -d "$shims_dir" ]; then
        rm -rf "$shims_dir"
        echo "已删除: $shims_dir"
    fi

    # 清理 .repo 目录
    local repo_dir="$HOME/.jtool/repo"
    if [ -d "$repo_dir" ]; then
        rm -rf "$repo_dir"
        echo "已删除: $repo_dir"
    fi

    for rc_file in "$HOME/.zshrc" "$HOME/.bashrc"; do
        if [ -f "$rc_file" ] && grep -q "$install_dir" "$rc_file" 2>/dev/null; then
            sed -i.bak "/# jtool/d" "$rc_file"
            sed -i.bak "\|$install_dir|d" "$rc_file"
            rm -f "${rc_file}.bak"
            echo "已清理: $rc_file"
        fi
        if [ -f "$rc_file" ] && grep -q "$shims_dir" "$rc_file" 2>/dev/null; then
            sed -i.bak "\|$shims_dir|d" "$rc_file"
            rm -f "${rc_file}.bak"
        fi
    done

    echo ""
    echo "卸载完成！"
}

# ============================================
# 查看配置
# ============================================
do_config() {
    local config_file="$1"
    echo "配置文件: $config_file"
    echo ""
    [ -f "$config_file" ] && cat "$config_file" || echo "(不存在，请运行: jtool scan)"
}
