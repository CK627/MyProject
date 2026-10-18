# encoding: utf-8
# startupctl 补全（bash）：source 本文件，或放入 /etc/bash_completion.d/。
# 兼容 bash 3.2（macOS 自带版本）。
#
# **本工具没有选项**，所以不补任何 `-` 开头的东西。纯位置驱动：
#   startupctl <TAB>                     → 子命令
#   startupctl list <TAB>                → all / system
#   startupctl mode <TAB>                → off / deny_all / blacklist / whitelist
#   startupctl whitelist <TAB>           → startup / process
#   startupctl whitelist startup <TAB>   → selector
#   startupctl starting <TAB>            → true / false
#   startupctl update <TAB>              → check
#   startupctl uninstall <TAB>           → confirm
#   startupctl help <TAB>                → 子命令

_startupctl() {
    local cur
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"

    local subcmds="list mode whitelist blacklist starting config version help update install uninstall"

    if [ "$COMP_CWORD" -eq 1 ]; then
        COMPREPLY=( $(compgen -W "$subcmds" -- "$cur") )
        return 0
    fi

    case "${COMP_WORDS[1]}" in
        list)
            [ "$COMP_CWORD" -eq 2 ] && COMPREPLY=( $(compgen -W "all system" -- "$cur") )
            ;;
        mode)
            [ "$COMP_CWORD" -eq 2 ] && COMPREPLY=( $(compgen -W "off deny_all blacklist whitelist" -- "$cur") )
            ;;
        whitelist|blacklist)
            if [ "$COMP_CWORD" -eq 2 ]; then
                COMPREPLY=( $(compgen -W "startup process" -- "$cur") )
            elif [ "$COMP_CWORD" -eq 3 ]; then
                COMPREPLY=( $(compgen -W "selector" -- "$cur") )
            fi
            ;;
        starting)
            [ "$COMP_CWORD" -eq 2 ] && COMPREPLY=( $(compgen -W "true false" -- "$cur") )
            ;;
        update)
            [ "$COMP_CWORD" -eq 2 ] && COMPREPLY=( $(compgen -W "check" -- "$cur") )
            ;;
        uninstall)
            [ "$COMP_CWORD" -eq 2 ] && COMPREPLY=( $(compgen -W "confirm" -- "$cur") )
            ;;
        help)
            [ "$COMP_CWORD" -eq 2 ] && COMPREPLY=( $(compgen -W "$subcmds" -- "$cur") )
            ;;
    esac
    return 0
}

complete -F _startupctl startupctl
