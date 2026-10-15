# ctfsweep 补全（bash）：source 本文件，或放入 /etc/bash_completion.d/。
# 兼容 bash 3.2（macOS 自带版本）。
# 行为与 zsh 版对齐：位置驱动——第一个参数位列「子命令 + 文件」（不列选项），
# 其余位置只在当前词以 "-" 开头时列选项，否则只补文件。
# 子命令专属参数（update --check / uninstall -y）与选项值补全亦已支持。
_ctfsweep() {
    local cur prev opts subcmds
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="-f --file -F --folder -k --keywords --min-score --no-decode --depth --limit --extract --extract-dir --pwd-file --judge -q --brief --config --version -h --help"
    subcmds="update install uninstall clear config help"

    # 子命令专属参数（ctfsweep update --check / ctfsweep uninstall -y）
    if [ "$COMP_CWORD" -ge 2 ]; then
        case "${COMP_WORDS[1]}" in
            update)
                COMPREPLY=( $(compgen -W "--check" -- "$cur") )
                return 0
                ;;
            uninstall|clear)
                COMPREPLY=( $(compgen -W "-y --yes" -- "$cur") )
                return 0
                ;;
            install|config|help)
                return 0
                ;;
        esac
    fi

    # 第一个参数位：子命令 + 文件（不列选项——与 jtool/ptool 的位置驱动一致，
    # 选项在敲 "-" 之后才出现）
    if [ "$COMP_CWORD" -eq 1 ]; then
        if [[ "$cur" == -* ]]; then
            COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
        else
            COMPREPLY=( $(compgen -W "$subcmds" -- "$cur") $(compgen -f -- "$cur") )
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
    # 选项只在当前词以 "-" 开头时出现（位置驱动，与 zsh 版一致）。
    # 缺失这道闸门时 `ctfsweep -q <TAB>` 会把全部选项连 --config 一起铺出来。
    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
    else
        COMPREPLY=( $(compgen -f -- "$cur") )
    fi
}
complete -o filenames -F _ctfsweep ctfsweep

# ============================================
# 包装函数（与 jtool/ptool 同规）
# 函数在**父 shell** 里执行，所以 ctfsweep update 跑完后可以立刻重载本文件，
# 不必手动 source ~/.bashrc 或重开终端——更新是**就地**替换安装目录里的这一份，
# 而 shell 认的是已加载进内存的那份定义。（脚本本身是子进程，改不了父 shell
# 的环境，只有 shell 函数做得到。）
#   · update 后就地重载（重装会把本文件换成新版，sourced 的旧定义得跟着换）；
#   · uninstall 后本文件已不在，改为重载 rc 让 PATH 接线一起消失，并清掉本函数；
#   · install 不在此列：ctfsweep install 只**打印安装方式**，不落地任何文件。
# ⚠️ 加 sudo 会绕过本函数（sudo 按 PATH 找可执行文件，不看 shell 函数），
#    届时仍需手动 source —— 更新本身会按需提权，正常敲 `ctfsweep update` 即可。
# ============================================
# 本文件自身的路径（source 时取当前文件路径）；重装后重载指向的仍是安装目录那一份
_ctfsweep_self="${BASH_SOURCE[0]}"

ctfsweep() {
    command ctfsweep "$@"
    local _ctfsweep_ret=$?
    case "$1" in
        update)
            [ -f "$_ctfsweep_self" ] && source "$_ctfsweep_self"
            hash -r 2>/dev/null
            ;;
        uninstall)
            source ~/.bashrc 2>/dev/null
            unset -f ctfsweep 2>/dev/null
            hash -r 2>/dev/null
            ;;
    esac
    return $_ctfsweep_ret
}

# ============================================
# 说明（devtools 安装形态）
# 安装后 PATH 与补全都由安装目录提供，接线写在 ~/.bashrc 的
# `# >>> ctfsweep >>>` 块里（由 installer/shell-setup.sh 维护，幂等）。
# 仓库 bin/ 是素材目录（ctfsweep.sh + ctfsweep.bat），**不进 PATH** ——
# 命令名补全走 $commands 哈希，而它不检查可执行位，整体挂上会连
# Windows 启动器 ctfsweep.bat 一起列出来。ctfsweep update 后补全自动刷新。
# ============================================
