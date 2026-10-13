# ctfsweep 补全（bash）：source 本文件，或放入 /etc/bash_completion.d/。
# 兼容 bash 3.2（macOS 自带版本）。
# 行为与 zsh 版对齐：TAB 直接列出全部选项（不必先敲 "-"）；
# 子命令专属参数（update --check / uninstall -y / train --data）与选项值补全亦已支持。
_ctfsweep() {
    local cur prev opts subcmds
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="-f --file -F --folder -k --keywords --min-score --no-decode --depth --limit --extract --extract-dir --pwd-file --judge -q --brief --config --version -h --help"
    subcmds="update install uninstall config train label learning help"

    # 子命令专属参数（ctfsweep uninstall ... / ctfsweep train ...）
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
# 说明（devtools 安装形态）
# 安装后 PATH 与补全都由安装目录提供，接线写在 ~/.bashrc 的
# `# >>> ctfsweep >>>` 块里（由 installer/shell-setup.sh 维护，幂等）。
# 仓库 bin/ 是素材目录（ctfsweep.sh + ctfsweep.bat），**不进 PATH** ——
# 命令名补全走 $commands 哈希，而它不检查可执行位，整体挂上会连
# Windows 启动器 ctfsweep.bat 一起列出来。ctfsweep update 后补全自动刷新。
# ============================================
