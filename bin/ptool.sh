#!/bin/bash
# encoding: utf-8
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
            # Trim surrounding whitespace and strip one wrapping pair of double
            # quotes. Never delete every space: PYTHON_BASE_DIR such as
            # "/opt/My Python/bin" must survive intact (the old tr -d " '\""
            # collapsed it to /opt/MyPython/bin).
            value=$(printf '%s' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"\(.*\)"$/\1/')
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

    local entries=""
    local seen=""
    local unusable=0 hint=""
    for bin in "$PYTHON_BASE_DIR"/python[0-9]*.[0-9]* "$PYTHON_BASE_DIR"/python[0-9]*; do
        [ -f "$bin" ] && [ -x "$bin" ] || continue

        # 跳过 python*-config、python*-intel64 等非解释器文件
        basename "$bin" | grep -q '-' && continue

        local version
        version=$(basename "$bin" | sed -n 's/^python\([0-9]*\.[0-9]*\).*/\1/p')
        [ -z "$version" ] && version=$(basename "$bin" | sed -n 's/^python\([0-9]*\)$/\1/p')
        [ -z "$version" ] && continue

        # 跳过重复版本
        case " $seen " in *" $version "*) continue ;; esac
        seen="$seen $version"

        local real_version
        if python_probe "$bin"; then
            real_version="$PYTHON_PROBE_VERSION"
        else
            # 跑不起来的照样列出来，但标清楚——最误导人的就是把报错当成版本号打印
            # （旧版就是这样：`3.6 - ... Bad CPU type in executable`）。
            real_version="不可用：$PYTHON_PROBE_ERROR"
            unusable=$((unusable + 1))
            [ -z "$hint" ] && hint="$PYTHON_PROBE_ERROR"
        fi

        entries="${entries}  $version - $real_version ($bin)"$'\n'
    done

    if [ -z "$entries" ]; then
        echo "  (未找到)"
    elif sort -V </dev/null >/dev/null 2>&1; then
        printf '%s' "$entries" | sort -V
    else
        printf '%s' "$entries" | sort
    fi

    if [ "$unusable" -gt 0 ]; then
        echo ""
        echo "  注：标「不可用」的解释器在这台机器上跑不起来，ptool use 不会接受它们。"
        PYTHON_PROBE_ERROR="$hint" python_probe_hint
    fi

    echo ""
    [ -n "$PTOOL_DEFAULT_VERSION" ] && echo "默认版本: $PTOOL_DEFAULT_VERSION" || echo "默认版本: 未设置"
}

# ============================================
# 当前状态（不带子命令时显示）
# ============================================
show_state() {
    echo "ptool - Python 版本管理"
    if [ -n "$PTOOL_DEFAULT_VERSION" ]; then
        local cur
        cur=$(get_python_path "$PTOOL_DEFAULT_VERSION")
        echo "当前版本: $PTOOL_DEFAULT_VERSION"
        echo "路径:     $cur"
        # 默认版本可能是在别的机器上设的，或者装完系统后架构变了——探一次，别让
        # 用户敲 python 才发现坏了。
        if ! python_probe "$cur"; then
            echo "⚠ 这个解释器在本机跑不起来：$PYTHON_PROBE_ERROR"
            echo "  裸敲 python 会失败，用 ptool use <版本> 换一个（ptool list 看哪些可用）"
        fi
    else
        echo "当前版本: （未设置，用 ptool use <版本号> 设置）"
    fi
    echo "基础目录: $PYTHON_BASE_DIR"
    local n=0 unusable=0 seen="" bin version
    for bin in "$PYTHON_BASE_DIR"/python[0-9]*.[0-9]* "$PYTHON_BASE_DIR"/python[0-9]*; do
        [ -f "$bin" ] && [ -x "$bin" ] || continue
        case "$(basename "$bin")" in *-*) continue ;; esac
        version=$(basename "$bin" | sed -n 's/^python\([0-9]*\.[0-9]*\).*/\1/p')
        [ -z "$version" ] && version=$(basename "$bin" | sed -n 's/^python\([0-9]*\)$/\1/p')
        [ -z "$version" ] && continue
        case " $seen " in *" $version "*) continue ;; esac
        seen="$seen $version"
        if python_probe "$bin"; then
            n=$((n + 1))
        else
            unusable=$((unusable + 1))
        fi
    done
    if [ "$unusable" -gt 0 ]; then
        echo "已安装:   $n 个可用（另有 $unusable 个跑不起来，ptool list 看明细）"
    else
        echo "已安装:   $n 个（ptool list 看明细）"
    fi
    echo ""
    echo "ptool help 看全部命令"
}

# ============================================
# 显示帮助
# ============================================
show_help() {
    cat << 'EOF'
ptool - 统一 Python 版本管理工具

用法:
  ptool                               显示当前状态（当前版本 / 路径 / 已安装数）
  ptool <工具名> <版本号> [参数...]   运行指定版本的 Python 工具
  ptool list                          列出所有已安装的 Python
  ptool use [版本号]                  设置默认版本（不带 = 看当前）
  ptool current                       显示当前默认版本
  ptool home [版本号]                 输出安装路径（不带 = 当前版本）
  ptool info [版本号]                 显示详细信息（不带 = 当前版本）
  ptool tools [版本号]                列出可用工具（不带 = 当前版本）
  ptool run <版本号> <python文件>     运行 Python 文件
  ptool scan                          扫描 Python 路径，更新配置
  ptool config                        显示配置
  ptool install                       完整安装（从源码目录）
  ptool setup                         生成 shims/补全 并写入 shell 配置
  ptool uninstall [-y]                卸载（-y 跳过确认）
  ptool update                        检查并更新 ptool 到最新版本
  ptool shim                          重建 shim 脚本
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

    # 存在 ≠ 能跑。新机器上常见 /usr/local/bin 里留着 x86_64 的旧版本，在 Apple
    # Silicon 上一执行就 "Bad CPU type in executable"。真写进配置的话，shim 会 exec
    # 到一个跑不起来的二进制，整台机器的 python 直接坏掉——所以这里先探一次。
    if ! python_probe "$python_path"; then
        echo "错误: Python $version 无法在这台机器上运行" >&2
        echo "      $python_path: $PYTHON_PROBE_ERROR" >&2
        python_probe_hint >&2
        echo "      默认版本未改动。" >&2
        return 1
    fi

    sudo sed -i.bak '/^PTOOL_DEFAULT_VERSION/d' "$CONFIG_FILE"
    sudo rm -f "$CONFIG_FILE.bak"
    echo "PTOOL_DEFAULT_VERSION=\"$version\"" | sudo tee -a "$CONFIG_FILE" > /dev/null
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
    local version="$1"; shift
    local python_file="$1"; shift

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
    # shift 之后剩下的参数原样透传给脚本：ptool run 3.11 f.py --flag
    "$python_path" "$python_file" "$@"
}

# ============================================
# 主逻辑
# ============================================
load_config

[ $# -lt 1 ] && { show_state; exit 0; }

case "$1" in
    list)     list_pythons; exit 0 ;;
    help|-h|--help) show_help; exit 0 ;;
    use)      [ $# -lt 2 ] && { cmd_current; exit $?; }; cmd_use "$2"; exit $? ;;
    current)  cmd_current; exit $? ;;
    home)     [ $# -lt 2 ] && { [ -n "$PTOOL_DEFAULT_VERSION" ] || { echo "错误: 未设置默认版本（先 ptool use <版本号>）" >&2; exit 1; }; cmd_home "$PTOOL_DEFAULT_VERSION"; exit $?; }; cmd_home "$2"; exit $? ;;
    info)     [ $# -lt 2 ] && { [ -n "$PTOOL_DEFAULT_VERSION" ] || { echo "错误: 未设置默认版本（先 ptool use <版本号>）" >&2; exit 1; }; cmd_info "$PTOOL_DEFAULT_VERSION"; exit $?; }; cmd_info "$2"; exit $? ;;
    tools)    [ $# -lt 2 ] && { [ -n "$PTOOL_DEFAULT_VERSION" ] || { echo "错误: 未设置默认版本（先 ptool use <版本号>）" >&2; exit 1; }; cmd_tools "$PTOOL_DEFAULT_VERSION"; exit $?; }; cmd_tools "$2"; exit $? ;;
    run)
        [ $# -lt 3 ] && { echo "错误: 请指定版本号和文件"; exit 1; }
        # $3 之后的参数透传给脚本本身：ptool run 3.11 f.py --flag
        _run_ver="$2"; shift 2; cmd_run "$_run_ver" "$@"; exit $? ;;
    scan)     do_scan "$CONFIG_FILE"; exit $? ;;
    config)   do_config "$CONFIG_FILE"; exit 0 ;;
    install)  do_install "$PROJECT_DIR"; exit $? ;;
    update)
        install_dir=$(get_install_dir) || exit 1
        do_update "ptool" "ptool" "https://github.com/CK627/MyProject.git" "$install_dir" "$CONFIG_FILE"
        exit $?
        ;;
    shim)
        install_dir=$(get_install_dir) || exit 1
        do_create_shims "$install_dir" "$CONFIG_FILE"
        exit $?
        ;;
    setup)
        # --files-only / --shell-only 供 pkg 的 postinstall 拆开用：产物要 root 写
        # （安装目录属 root），shell rc 要登录用户写，一个身份做不完两件事。
        shift
        case "${1:-}" in
            --files-only) do_setup_files "$PROJECT_DIR" "$CONFIG_FILE"; exit $? ;;
            --shell-only) do_setup_shell "$PROJECT_DIR"; exit $? ;;
            *)            do_setup_user  "$PROJECT_DIR" "$CONFIG_FILE"; exit $? ;;
        esac
        ;;
    uninstall) shift; do_uninstall "$@"; exit $? ;;
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
