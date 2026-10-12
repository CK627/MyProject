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
    subcmds="update install uninstall config train label learning help"

    # 子命令专属参数（ctfsweep uninstall ... / ctfsweep train ...）
    if [ "$COMP_CWORD" -ge 2 ]; then
        case "${COMP_WORDS[1]}" in
            update)
                return 0   # update 无参数（仅输出更新指引）
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
            label)
                case "$prev" in
                    --batch)
                        COMPREPLY=( $(compgen -W "5 10 20 50" -- "$cur") )
                        return 0
                        ;;
                esac
                COMPREPLY=( $(compgen -W "--batch" -- "$cur") )
                return 0
                ;;
            learning)
                case "$prev" in
                    --min-auc)
                        COMPREPLY=( $(compgen -W "0.80 0.85 0.90 0.95" -- "$cur") )
                        return 0
                        ;;
                    --min-samples|--max-epochs|--epochs)
                        COMPREPLY=( $(compgen -W "8 16 32 64 100 200 500 1000" -- "$cur") )
                        return 0
                        ;;
                esac
                COMPREPLY=( $(compgen -W "--min-auc --min-samples --max-epochs --epochs" -- "$cur") )
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
# 说明（源码直跑模式）
# 补全与 PATH 均由本文件所在的项目目录提供；代码更新（git pull）后无需刷新。
# （历史版本曾在此定义 ctfsweep 包装函数用于安装后的即时刷新，已随安装模式移除）
# ============================================
