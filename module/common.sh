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

    echo "[3/4] 扫描 Java..."
    do_scan "$config_file"
    echo ""

    echo "[4/4] 配置 PATH..."
    local shell_rc="$HOME/.zshrc"
    [ -f "$HOME/.bashrc" ] && shell_rc="$HOME/.bashrc"

    if ! grep -q "$bin_dir" "$shell_rc" 2>/dev/null; then
        echo "" >> "$shell_rc"
        echo "# jtool" >> "$shell_rc"
        echo "export PATH=\"$bin_dir:\$PATH\"" >> "$shell_rc"
        echo "已添加到 $shell_rc"
    else
        echo "已存在"
    fi

    export PATH="$bin_dir:$PATH"

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

    for rc_file in "$HOME/.zshrc" "$HOME/.bashrc"; do
        if [ -f "$rc_file" ] && grep -q "$install_dir" "$rc_file" 2>/dev/null; then
            sed -i.bak "/# jtool/d" "$rc_file"
            sed -i.bak "\|$install_dir|d" "$rc_file"
            rm -f "${rc_file}.bak"
            echo "已清理: $rc_file"
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
