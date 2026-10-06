# jtool zsh 补全
# 由 jtool 安装脚本生成，请勿手动修改
# 配置文件: @CONFIG_FILE@

# 从配置文件读取 JAVA_BASE_DIR，列出已安装的 JDK 版本号（不执行 java，保证 <TAB> 响应速度）
_jtool_versions() {
    local config_file="@CONFIG_FILE@"
    local base_dir=""
    [ -f "$config_file" ] && base_dir=$(grep '^JAVA_BASE_DIR=' "$config_file" 2>/dev/null | tail -1 | cut -d'"' -f2)
    [ -n "$base_dir" ] || return 0

    local dir name ver
    # macOS 是 jdk-21.jdk，Linux 是 jdk-21（后者由第二个通配兜底）
    for dir in "$base_dir"/jdk-*.jdk "$base_dir"/jdk-*; do
        [ -d "$dir" ] || continue
        name=${dir:t}
        ver=${name#jdk-}
        ver=${ver%.jdk}
        [ -n "$ver" ] && print -r -- "$ver"
    done
}

_jtool() {
    local -a subcmds tools versions

    subcmds=(
        'list:列出所有已安装的 JDK'
        'use:设置默认版本'
        'current:查看当前默认版本'
        'home:输出 JAVA_HOME 路径'
        'info:显示详细信息'
        'tools:列出可用工具'
        'run:编译并运行 Java 文件'
        'scan:扫描 Java 路径并更新配置'
        'config:显示配置'
        'install:完整安装'
        'update:检查并更新 jtool'
        'shim:重建 shim 脚本'
        'help:显示帮助'
    )
    tools=(java javac jar jshell javadoc javap)
    # o=排序 n=按数字比较 u=去重，使 1.8 排在 21 前面
    versions=(${(onu)${(f)"$(_jtool_versions)"}})

    # 第一个参数：子命令 + 工具名
    if (( CURRENT == 2 )); then
        _describe -t commands 'jtool 命令' subcmds
        _describe -t tools 'Java 工具' tools
        return
    fi

    case ${words[2]} in
        use|home|info|tools)
            # jtool <子命令> <版本>
            (( CURRENT == 3 )) && _describe -t versions 'JDK 版本' versions
            ;;
        run)
            # jtool run <版本> <文件.java>
            if (( CURRENT == 3 )); then
                _describe -t versions 'JDK 版本' versions
            else
                _files -g '*.java'
            fi
            ;;
        java|javac|jar|jshell|javadoc|javap)
            # jtool java <版本> [参数...]
            if (( CURRENT == 3 )); then
                _describe -t versions 'JDK 版本' versions
            else
                _files
            fi
            ;;
        *)
            _files
            ;;
    esac
}

# compinit 未初始化时（例如 .zshrc 里没有 compinit）先初始化，否则 compdef 不存在
if (( ! $+functions[compdef] )); then
    autoload -Uz compinit && compinit
fi
compdef _jtool jtool


# ============================================
# 包装函数
# 函数在父 shell 中执行，所以 jtool update / install 跑完后可以立刻重新加载
# 本文件，不必手动 source ~/.zshrc 或重开终端。
# （脚本本身是子进程，无法修改父 shell 的环境，只有 shell 函数能做到这一点）
# ============================================
jtool() {
    command jtool "$@"
    local _jtool_ret=$?
    case "$1" in
        update|install|shim)
            [ -f "@SELF@" ] && source "@SELF@"
            hash -r 2>/dev/null
            ;;
    esac
    return $_jtool_ret
}
