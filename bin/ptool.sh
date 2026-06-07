#!/bin/bash
# ptool - 统一 Python 版本管理工具
# 支持 macOS / Linux

# ============================================
# 路径
# ============================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config/ptool.conf"

# 加载安装模块（安装后在 module/，安装前在根目录）
if [ -f "$PROJECT_DIR/module/common.sh" ]; then
    source "$PROJECT_DIR/module/common.sh"
elif [ -f "$PROJECT_DIR/common.sh" ]; then
    source "$PROJECT_DIR/common.sh"
fi

# ============================================
# 加载配置
# ============================================
load_config() {
    PYTHON_BASE_DIR=""
    PTOOL_DEFAULT_VERSION=""

    if [ -f "$CONFIG_FILE" ]; then
        while IFS='=' read -r key value; do
            [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
            key=$(echo "$key" | tr -d ' ')
            value=$(echo "$value" | tr -d " '\"")
            case "$key" in
                PYTHON_BASE_DIR) PYTHON_BASE_DIR="$value" ;;
                PTOOL_DEFAULT_VERSION) PTOOL_DEFAULT_VERSION="$value" ;;
            esac
        done < "$CONFIG_FILE"
    fi

    if [ -z "$PYTHON_BASE_DIR" ]; then
        echo "错误: 未配置 PYTHON_BASE_DIR"
        echo "请运行: ptool scan"
        exit 1
    fi
}

# ============================================
# 拼接 Python 路径
# ============================================
get_python_path() {
    local version="$1"
    echo "$PYTHON_BASE_DIR/python$version"
}

# ============================================
# 列出所有已安装的 Python
# ============================================
list_pythons() {
    echo "Python 路径: $PYTHON_BASE_DIR"
    echo ""
    echo "已安装的 Python:"

    local found=0
    for bin in "$PYTHON_BASE_DIR"/python[0-9]*.[0-9]* "$PYTHON_BASE_DIR"/python[0-9]*; do
        [ -f "$bin" ] && [ -x "$bin" ] || continue

        local version
        version=$(basename "$bin" | sed -n 's/^python\([0-9]*\.[0-9]*\).*/\1/p')
        [ -z "$version" ] && version=$(basename "$bin" | sed -n 's/^python\([0-9]*\)$/\1/p')
        [ -z "$version" ] && continue

        local real_version
        real_version=$("$bin" --version 2>&1 | head -1)

        echo "  $version - $real_version ($bin)"
        found=1
    done

    [ "$found" -eq 0 ] && echo "  (未找到)"

    echo ""
    [ -n "$PTOOL_DEFAULT_VERSION" ] && echo "默认版本: $PTOOL_DEFAULT_VERSION" || echo "默认版本: 未设置"
}

# ============================================
# 显示帮助
# ============================================
show_help() {
    cat << 'EOF'
ptool - 统一 Python 版本管理工具

用法:
  ptool <工具名> <版本号> [参数...]   运行指定版本的 Python 工具
  ptool list                          列出所有已安装的 Python
  ptool use <版本号>                  设置默认版本
  ptool current                       显示当前默认版本
  ptool home <版本号>                 输出安装路径
  ptool info <版本号>                 显示详细信息
  ptool tools <版本号>                列出可用工具
  ptool run <版本号> <python文件>     运行 Python 文件
  ptool scan                          扫描 Python 路径，更新配置
  ptool config                        显示配置
  ptool install                       完整安装
  ptool help                          帮助

示例:
  ptool python 3.11 --version
  ptool pip 3.12 install requests
  ptool use 3.11
  ptool run 3.11 hello.py
  ptool scan
EOF
}

# ============================================
# 设置默认版本
# ============================================
cmd_use() {
    local version="$1"
    local python_path
    python_path=$(get_python_path "$version")

    if [ ! -f "$python_path" ]; then
        echo "错误: Python $version 不存在 ($python_path)"
        return 1
    fi

    sed -i.bak '/^PTOOL_DEFAULT_VERSION/d' "$CONFIG_FILE"
    rm -f "$CONFIG_FILE.bak"
    echo "PTOOL_DEFAULT_VERSION=\"$version\"" >> "$CONFIG_FILE"
    PTOOL_DEFAULT_VERSION="$version"

    echo "已设置默认版本: $version"
    echo "路径: $python_path"
}

cmd_current() {
    if [ -z "$PTOOL_DEFAULT_VERSION" ]; then
        echo "未设置默认版本"
        return 1
    fi
    echo "默认版本: $PTOOL_DEFAULT_VERSION"
    echo "路径: $(get_python_path "$PTOOL_DEFAULT_VERSION")"
}

cmd_home() {
    local version="$1"
    local python_path
    python_path=$(get_python_path "$version")

    if [ ! -f "$python_path" ]; then
        echo "错误: Python $version 不存在" >&2
        return 1
    fi
    echo "$(dirname "$python_path")"
}

cmd_info() {
    local version="$1"
    local python_path
    python_path=$(get_python_path "$version")

    if [ ! -f "$python_path" ]; then
        echo "错误: Python $version 不存在"
        return 1
    fi

    echo "=== Python $version ==="
    echo "路径: $python_path"
    echo ""
    "$python_path" --version 2>&1 | sed 's/^/  /'
    echo ""
    echo "工具:"
    local python_dir
    python_dir=$(dirname "$python_path")
    for tool in "$python_dir"/python* "$python_dir"/pip*; do
        [ -f "$tool" ] && [ -x "$tool" ] && echo "  $(basename "$tool")"
    done
}

cmd_tools() {
    local version="$1"
    local python_path
    python_path=$(get_python_path "$version")

    if [ ! -f "$python_path" ]; then
        echo "错误: Python $version 不存在"
        return 1
    fi

    echo "Python $version 工具:"
    local python_dir
    python_dir=$(dirname "$python_path")
    for tool in "$python_dir"/python* "$python_dir"/pip*; do
        [ -f "$tool" ] && [ -x "$tool" ] && echo "  $(basename "$tool")"
    done
}

cmd_run() {
    local version="$1"
    local python_file="$2"

    if [ -z "$python_file" ] || [ ! -f "$python_file" ]; then
        echo "错误: 请指定有效的 Python 文件"
        return 1
    fi

    local python_path
    python_path=$(get_python_path "$version")

    if [ ! -f "$python_path" ]; then
        echo "错误: Python $version 不存在"
        return 1
    fi

    echo "=== 运行 (Python $version) ==="
    "$python_path" "$python_file"
}

# ============================================
# 主逻辑
# ============================================
load_config

[ $# -lt 1 ] && { show_help; exit 0; }

case "$1" in
    list)     list_pythons; exit 0 ;;
    help|-h|--help) show_help; exit 0 ;;
    use)      [ $# -lt 2 ] && { echo "错误: 请指定版本号"; exit 1; }; cmd_use "$2"; exit $? ;;
    current)  cmd_current; exit $? ;;
    home)     [ $# -lt 2 ] && { echo "错误: 请指定版本号"; exit 1; }; cmd_home "$2"; exit $? ;;
    info)     [ $# -lt 2 ] && { echo "错误: 请指定版本号"; exit 1; }; cmd_info "$2"; exit $? ;;
    tools)    [ $# -lt 2 ] && { echo "错误: 请指定版本号"; exit 1; }; cmd_tools "$2"; exit $? ;;
    run)      [ $# -lt 3 ] && { echo "错误: 请指定版本号和文件"; exit 1; }; cmd_run "$2" "$3"; exit $? ;;
    scan)     do_scan "$CONFIG_FILE"; exit $? ;;
    config)   do_config "$CONFIG_FILE"; exit 0 ;;
    install)  do_install "$PROJECT_DIR"; exit $? ;;
esac

# 运行工具
tool="$1"
if [ $# -lt 2 ]; then
    if [ -n "$PTOOL_DEFAULT_VERSION" ]; then
        version="$PTOOL_DEFAULT_VERSION"
        shift 1
    else
        echo "错误: 需要指定工具名和版本号"
        exit 1
    fi
else
    version="$2"
    shift 2
fi

python_path=$(get_python_path "$version")

if [ ! -f "$python_path" ]; then
    echo "错误: Python $version 不存在 ($python_path)"
    echo ""
    list_pythons
    exit 1
fi

case "$tool" in
    python|python3)
        exec "$python_path" "$@"
        ;;
    pip|pip3)
        pip_path="${python_path/python/pip}"
        if [ -f "$pip_path" ]; then
            exec "$pip_path" "$@"
        else
            exec "$python_path" -m pip "$@"
        fi
        ;;
    *)
        tool_path="$(dirname "$python_path")/$tool"
        if [ -f "$tool_path" ] && [ -x "$tool_path" ]; then
            exec "$tool_path" "$@"
        else
            echo "错误: 工具 '$tool' 不存在"
            exit 1
        fi
        ;;
esac
