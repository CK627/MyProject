# ptool bash 补全
# 由 ptool 安装脚本生成，请勿手动修改
# 配置文件: @CONFIG_FILE@
# 兼容 bash 3.2（macOS 自带版本）

_ptool_versions() {
    local config_file="@CONFIG_FILE@"
    local base_dir=""
    [ -f "$config_file" ] && base_dir=$(grep '^PYTHON_BASE_DIR=' "$config_file" 2>/dev/null | tail -1 | cut -d'"' -f2)
    [ -n "$base_dir" ] || return 0

    local bin name ver
    for bin in "$base_dir"/python[0-9]*; do
        [ -x "$bin" ] || continue
        name=$(basename "$bin")
        # 跳过 python3-config、python3-intel64 等非解释器
        case "$name" in *-*) continue ;; esac
        ver=${name#python}
        # python3.13t / python3.6m -> 3.13 / 3.6
        ver=${ver%%[^0-9.]*}
        [ -n "$ver" ] && echo "$ver"
    done
}

_ptool_complete() {
    local cur cmd
    local subcmds="list use current home info tools run scan config install update shim help"
    local tools="python python3 pip pip3 pip2"

    cur="${COMP_WORDS[COMP_CWORD]}"
    cmd="${COMP_WORDS[1]}"

    if [ "$COMP_CWORD" -eq 1 ]; then
        COMPREPLY=( $(compgen -W "$subcmds $tools" -- "$cur") )
        return 0
    fi

    case "$cmd" in
        use|home|info|tools)
            COMPREPLY=( $(compgen -W "$(_ptool_versions | sort -uV)" -- "$cur") )
            ;;
        run)
            # ptool run <版本> <文件>
            if [ "$COMP_CWORD" -eq 2 ]; then
                COMPREPLY=( $(compgen -W "$(_ptool_versions | sort -uV)" -- "$cur") )
            else
                COMPREPLY=( $(compgen -f -X '!*.py' -- "$cur") )
            fi
            ;;
        python|python3|pip|pip3|pip2)
            if [ "$COMP_CWORD" -eq 2 ]; then
                COMPREPLY=( $(compgen -W "$(_ptool_versions | sort -uV)" -- "$cur") )
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

complete -F _ptool_complete ptool

# ============================================
# 包装函数
# 函数在父 shell 中执行，所以 ptool update / install 跑完后可以立刻重新加载
# 本文件，不必手动 source ~/.bashrc 或重开终端。
# （脚本本身是子进程，无法修改父 shell 的环境，只有 shell 函数能做到这一点）
# ============================================
ptool() {
    command ptool "$@"
    local _ptool_ret=$?
    case "$1" in
        update|install|shim)
            [ -f "@SELF@" ] && source "@SELF@"
            hash -r 2>/dev/null
            ;;
    esac
    return $_ptool_ret
}
