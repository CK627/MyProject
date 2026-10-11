# ctfsweep 补全（bash）：source 本文件，或放入 /etc/bash_completion.d/。
# 兼容 bash 3.2（macOS 自带版本）。
# 行为与 zsh 版对齐：TAB 直接列出全部选项（不必先敲 "-"）；
# 子命令专属参数（update --check / uninstall -y / train --data）与选项值补全亦已支持。
_ctfsweep() {
    local cur prev opts subcmds
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="-f --file -F --folder -k --keywords --min-score --no-decode --depth --limit --extract --extract-dir --pwd-file --judge --config --version -h --help"
    subcmds="update install uninstall config train help"

    # 子命令专属参数（ctfsweep update ... / ctfsweep train ...）
    if [ "$COMP_CWORD" -ge 2 ]; then
        case "${COMP_WORDS[1]}" in
            update)
                COMPREPLY=( $(compgen -W "--check" -- "$cur") )
                return 0
                ;;
            uninstall)
                COMPREPLY=( $(compgen -W "-y --yes" -- "$cur") )
                return 0
                ;;
            train)
                case "$prev" in
                    --data|--model-out|--model)
                        COMPREPLY=( $(compgen -f -- "$cur") )
                        return 0
                        ;;
                    --epochs)
                        COMPREPLY=( $(compgen -W "100 250 500 1000" -- "$cur") )
                        return 0
                        ;;
                esac
                COMPREPLY=( $(compgen -W "--data --model-out --epochs" -- "$cur") )
                return 0
                ;;
            install|config|help)
                return 0
                ;;
        esac
    fi

    if [ "$COMP_CWORD" -eq 1 ]; then
        if [[ "$cur" == -* ]]; then
            COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
        else
            COMPREPLY=( $(compgen -W "$subcmds" -- "$cur") $(compgen -W "$opts" -- "$cur") $(compgen -f -- "$cur") )
        fi
        return 0
    fi
    case "$prev" in
        -k|--keywords)
            COMPREPLY=( $(compgen -W "flag ctf key secret" -- "$cur") )
            return 0
            ;;
        --extract-dir)
            COMPREPLY=( $(compgen -d -- "$cur") )
            return 0
            ;;
        -f|--file|--pwd-file|--config)
            COMPREPLY=( $(compgen -f -- "$cur") )
            return 0
            ;;
        -F|--folder)
            COMPREPLY=( $(compgen -d -- "$cur") )
            return 0
            ;;
        --depth)
            COMPREPLY=( $(compgen -W "1 2 3 4 5" -- "$cur") )
            return 0
            ;;
        --min-score)
            COMPREPLY=( $(compgen -W "0.40 0.55 0.85 0.95" -- "$cur") )
            return 0
            ;;
    esac
    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
    else
        COMPREPLY=( $(compgen -W "$opts" -- "$cur") $(compgen -f -- "$cur") )
    fi
}
complete -o filenames -F _ctfsweep ctfsweep

# ============================================
# 包装函数
# 函数在当前 shell 里执行，所以 ctfsweep update / install / uninstall 跑完后可以
# 立刻刷新补全与 shell 状态，不必手动 source ~/.bashrc 或重开终端。
# （脚本本身是子进程，无法修改父 shell 的环境，只有 shell 函数能做到这一点）
# ============================================
ctfsweep() {
    command ctfsweep "$@"
    local _ctfsweep_ret=$?
    case "$1" in
        update|install)
            [ -f "$HOME/.devtools/ctfsweep/completions/ctfsweep.bash" ] \
                && source "$HOME/.devtools/ctfsweep/completions/ctfsweep.bash"
            hash -r 2>/dev/null
            ;;
        uninstall)
            # 卸载后重载 shell 配置并移除本包装函数
            source ~/.bashrc 2>/dev/null
            unset -f ctfsweep 2>/dev/null
            hash -r 2>/dev/null
            ;;
    esac
    return $_ctfsweep_ret
}
