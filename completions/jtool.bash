# jtool bash 补全
# 由 jtool 安装脚本生成，请勿手动修改
# 配置文件: @CONFIG_FILE@
# 兼容 bash 3.2（macOS 自带版本）

_jtool_versions() {
    local config_file="@CONFIG_FILE@"
    local base_dir=""
    [ -f "$config_file" ] && base_dir=$(grep '^JAVA_BASE_DIR=' "$config_file" 2>/dev/null | tail -1 | cut -d'"' -f2)
    [ -n "$base_dir" ] || return 0

    local dir name ver
    # macOS 是 jdk-21.jdk，Linux 是 jdk-21（后者由第二个通配兜底）
    for dir in "$base_dir"/jdk-*.jdk "$base_dir"/jdk-*; do
        [ -d "$dir" ] || continue
        name=$(basename "$dir")
        ver=${name#jdk-}
        ver=${ver%.jdk}
        [ -n "$ver" ] && echo "$ver"
    done
}

_jtool_complete() {
    local cur cmd
    local subcmds="list use current home info tools run scan config install setup uninstall update shim help"
    local tools="java javac jar jshell javadoc javap"

    cur="${COMP_WORDS[COMP_CWORD]}"
    cmd="${COMP_WORDS[1]}"

    if [ "$COMP_CWORD" -eq 1 ]; then
        COMPREPLY=( $(compgen -W "$subcmds $tools" -- "$cur") )
        return 0
    fi

    case "$cmd" in
        use|home|info|tools)
            COMPREPLY=( $(compgen -W "$(_jtool_versions | sort -uV)" -- "$cur") )
            ;;
        run)
            # jtool run <版本> <文件.java>
            if [ "$COMP_CWORD" -eq 2 ]; then
                COMPREPLY=( $(compgen -W "$(_jtool_versions | sort -uV)" -- "$cur") )
            else
                COMPREPLY=( $(compgen -f -X '!*.java' -- "$cur") )
            fi
            ;;
        java|javac|jar|jshell|javadoc|javap)
            if [ "$COMP_CWORD" -eq 2 ]; then
                COMPREPLY=( $(compgen -W "$(_jtool_versions | sort -uV)" -- "$cur") )
            else
                COMPREPLY=( $(compgen -f -- "$cur") )
            fi
            ;;
        *)
            COMPREPLY=( $(compgen -f -- "$cur") )
            ;;
    esac
    return 0
}

complete -F _jtool_complete jtool


# ============================================
# 包装函数
# 函数在父 shell 中执行，所以 jtool update / install 跑完后可以立刻重新加载
# 本文件，不必手动 source ~/.bashrc 或重开终端。
# （脚本本身是子进程，无法修改父 shell 的环境，只有 shell 函数能做到这一点）
# ============================================
jtool() {
    command jtool "$@"
    local _jtool_ret=$?
    case "$1" in
        update|install|setup|shim)
            [ -f "@SELF@" ] && source "@SELF@"
            hash -r 2>/dev/null
            ;;
    esac
    return $_jtool_ret
}
