#!/bin/bash
# jtool - 统一 Java 版本管理工具
# 支持 macOS / Linux

# ============================================
# 路径
# ============================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config/jtool.conf"

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
    JAVA_BASE_DIR=""
    JTOOL_DEFAULT_VERSION=""

    if [ -f "$CONFIG_FILE" ]; then
        while IFS='=' read -r key value; do
            [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
            key=$(echo "$key" | tr -d ' ')
            value=$(echo "$value" | tr -d " '\"")
            case "$key" in
                JAVA_BASE_DIR) JAVA_BASE_DIR="$value" ;;
                JTOOL_DEFAULT_VERSION) JTOOL_DEFAULT_VERSION="$value" ;;
            esac
        done < "$CONFIG_FILE"
    fi

    if [ -z "$JAVA_BASE_DIR" ]; then
        echo "错误: 未配置 JAVA_BASE_DIR"
        echo "请运行: jtool scan"
        exit 1
    fi
}

# ============================================
# 拼接 JDK 路径
# ============================================
get_jdk_home() {
    local version="$1"
    [ "$version" = "8" ] && version="1.8"
    echo "$JAVA_BASE_DIR/jdk-$version.jdk/Contents/Home"
}

# ============================================
# 列出所有已安装的 JDK
# ============================================
list_jdks() {
    echo "Java 路径: $JAVA_BASE_DIR"
    echo ""
    echo "已安装的 JDK:"

    local found=0
    for dir in "$JAVA_BASE_DIR"/jdk-*.jdk; do
        [ -d "$dir" ] || continue
        [ -f "$dir/Contents/Home/bin/java" ] || continue

        local version
        version=$(basename "$dir" | sed 's/jdk-//;s/\.jdk//')
        local real_version
        real_version=$("$dir/Contents/Home/bin/java" -version 2>&1 | head -1)

        echo "  $version - $real_version"
        found=1
    done

    [ "$found" -eq 0 ] && echo "  (未找到)"

    echo ""
    [ -n "$JTOOL_DEFAULT_VERSION" ] && echo "默认版本: $JTOOL_DEFAULT_VERSION" || echo "默认版本: 未设置"
}

# ============================================
# 显示帮助
# ============================================
show_help() {
    cat << 'EOF'
jtool - 统一 Java 版本管理工具

用法:
  jtool <工具名> <版本号> [参数...]   运行指定版本的 Java 工具
  jtool list                          列出所有已安装的 JDK
  jtool use <版本号>                  设置默认版本
  jtool current                       显示当前默认版本
  jtool home <版本号>                 输出 JAVA_HOME
  jtool info <版本号>                 显示详细信息
  jtool tools <版本号>                列出可用工具
  jtool run <版本号> <java文件>       编译并运行
  jtool scan                          扫描 Java 路径，更新配置
  jtool config                        显示配置
  jtool install                       完整安装
  jtool update                        检查并更新 jtool 到最新版本
  jtool shim                          重建 shim 脚本
  jtool help                          帮助

示例:
  jtool java 26 -version
  jtool javac 21 -d out MyClass.java
  jtool use 21
  jtool run 26 Hello.java
  jtool scan
EOF
}

# ============================================
# 设置默认版本
# ============================================
cmd_use() {
    local version="$1"
    local jdk_home
    jdk_home=$(get_jdk_home "$version")

    if [ ! -d "$jdk_home" ]; then
        echo "错误: JDK $version 不存在 ($jdk_home)"
        return 1
    fi

    sudo sed -i.bak '/^JTOOL_DEFAULT_VERSION/d' "$CONFIG_FILE"
    sudo rm -f "$CONFIG_FILE.bak"
    echo "JTOOL_DEFAULT_VERSION=\"$version\"" | sudo tee -a "$CONFIG_FILE" > /dev/null
    JTOOL_DEFAULT_VERSION="$version"

    echo "已设置默认版本: $version"
    echo "JAVA_HOME: $jdk_home"
}

cmd_current() {
    if [ -z "$JTOOL_DEFAULT_VERSION" ]; then
        echo "未设置默认版本"
        return 1
    fi
    echo "默认版本: $JTOOL_DEFAULT_VERSION"
    echo "JAVA_HOME: $(get_jdk_home "$JTOOL_DEFAULT_VERSION")"
}

cmd_home() {
    local version="$1"
    local jdk_home
    jdk_home=$(get_jdk_home "$version")

    if [ ! -d "$jdk_home" ]; then
        echo "错误: JDK $version 不存在" >&2
        return 1
    fi
    echo "$jdk_home"
}

cmd_info() {
    local version="$1"
    local jdk_home
    jdk_home=$(get_jdk_home "$version")

    if [ ! -d "$jdk_home" ]; then
        echo "错误: JDK $version 不存在"
        return 1
    fi

    echo "=== JDK $version ==="
    echo "JAVA_HOME: $jdk_home"
    echo ""
    "$jdk_home/bin/java" -version 2>&1 | sed 's/^/  /'
    echo ""
    echo "工具:"
    for tool in "$jdk_home"/bin/*; do
        [ -f "$tool" ] && [ -x "$tool" ] && echo "  $(basename "$tool")"
    done
}

cmd_tools() {
    local version="$1"
    local jdk_home
    jdk_home=$(get_jdk_home "$version")

    if [ ! -d "$jdk_home" ]; then
        echo "错误: JDK $version 不存在"
        return 1
    fi

    echo "JDK $version 工具:"
    for tool in "$jdk_home"/bin/*; do
        [ -f "$tool" ] && [ -x "$tool" ] && echo "  $(basename "$tool")"
    done
}

cmd_run() {
    local version="$1"
    local java_file="$2"

    if [ -z "$java_file" ] || [ ! -f "$java_file" ]; then
        echo "错误: 请指定有效的 Java 文件"
        return 1
    fi

    local jdk_home
    jdk_home=$(get_jdk_home "$version")

    if [ ! -d "$jdk_home" ]; then
        echo "错误: JDK $version 不存在"
        return 1
    fi

    local class_name
    class_name=$(basename "$java_file" .java)

    echo "=== 编译 (JDK $version) ==="
    "$jdk_home/bin/javac" "$java_file" || { echo "编译失败"; return 1; }

    echo ""
    echo "=== 运行 ==="
    "$jdk_home/bin/java" "$class_name"
    local exit_code=$?

    rm -f "${class_name}.class"
    return $exit_code
}

# ============================================
# 主逻辑
# ============================================
load_config

[ $# -lt 1 ] && { show_help; exit 0; }

case "$1" in
    list)     list_jdks; exit 0 ;;
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
    update)   do_update "jtool" "jtool" "https://github.com/CK627/MyProject.git" "$(get_install_dir)" "$CONFIG_FILE"; exit $? ;;
    shim)     do_create_shims "$(get_install_dir)/config/jtool.conf"; exit $? ;;
esac

# 运行工具
tool="$1"
if [ $# -lt 2 ]; then
    if [ -n "$JTOOL_DEFAULT_VERSION" ]; then
        version="$JTOOL_DEFAULT_VERSION"
        shift 1
    else
        echo "错误: 需要指定工具名和版本号"
        exit 1
    fi
else
    version="$2"
    shift 2
fi

jdk_home=$(get_jdk_home "$version")

if [ ! -d "$jdk_home" ]; then
    echo "错误: JDK $version 不存在 ($jdk_home)"
    echo ""
    list_jdks
    exit 1
fi

tool_path="$jdk_home/bin/$tool"

if [ ! -f "$tool_path" ]; then
    echo "错误: JDK $version 没有 $tool 工具"
    exit 1
fi

exec "$tool_path" "$@"
