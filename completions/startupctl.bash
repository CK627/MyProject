# startupctl 补全（bash）：source 本文件，或放入 /etc/bash_completion.d/。
# 兼容 bash 3.2（macOS 自带版本）。
# 行为与 zsh 版对齐：位置驱动——第一个参数位列「子命令 + 文件」（不列选项），
# 其余位置只在当前词以 "-" 开头时列选项，否则只补文件。
# 子命令专属选项（list / clean / whitelist …）与选项值补全亦已支持。
_startupctl() {
    local cur prev i
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    local opts="--watch --all --confidence --config --deep --diff --dry-run --errors --exec-prefix --force --glob --help --i-know --include-unknown --json --kind --long --name --orphans --pin --purge --raw --reason --remove --resolve --run-at-load --running --save --scope --strict --sudo --system --third-party --vendor --version -y --yes -h"
    local subcmds="list show check scan disable enable remove add restore backup clean proc kill whitelist guard update install uninstall config help"

    # ---- 选项的值位置 ----
    case "$prev" in
        --config)
            COMPREPLY=( $(compgen -f -- "$cur") )
            return 0
            ;;
        --kind)
            COMPREPLY=( $(compgen -W "launchd launchd-daemon launchd-agent login-item btm systemd systemd-user xdg-autostart initd cron registry-run startup-folder win-service task-scheduler" -- "$cur") )
            return 0
            ;;
        --confidence)
            COMPREPLY=( $(compgen -W "high medium" -- "$cur") )
            return 0
            ;;
        --scope)
            COMPREPLY=( $(compgen -W "system user" -- "$cur") )
            return 0
            ;;
    esac

    # ---- 二级动词 ----
    if [ "$COMP_CWORD" -eq 2 ]; then
        case "${COMP_WORDS[1]}" in
            whitelist)
                COMPREPLY=( $(compgen -W "add remove list doctor prune" -- "$cur") )
                return 0
                ;;
            backup)
                COMPREPLY=( $(compgen -W "list prune" -- "$cur") )
                return 0
                ;;
            guard)
                if [ "${COMP_WORDS[2]:-}" = "mode" ]; then
                    COMPREPLY=( $(compgen -W "off deny_all blacklist whitelist" -- "$cur") )
                else
                    COMPREPLY=( $(compgen -W "status mode choose list add remove lock unlock check arm" -- "$cur") )
                fi
                return 0
                ;;
        esac
    fi

    # ---- 子命令专属选项 ----
    if [ "$COMP_CWORD" -ge 2 ]; then
        local sub_opts=""
        case "${COMP_WORDS[1]}" in
            update)
                COMPREPLY=( $(compgen -W "--check" -- "$cur") )
                return 0
                ;;
            list)
                sub_opts="--all --system --third-party --running --vendor --kind --scope --json --long --errors"
                ;;
            clean)
                sub_opts="--remove --confidence --include-unknown --i-know --strict --dry-run --sudo -y --yes"
                ;;
            disable|enable|remove)
                sub_opts="--dry-run --sudo -y --yes"
                ;;
            scan)
                sub_opts="--save --diff --json"
                ;;
            show)
                sub_opts="--raw --resolve --json"
                ;;
            proc)
                sub_opts="--third-party --system --orphans --json"
                ;;
            kill)
                sub_opts="--force --dry-run --sudo -y --yes"
                ;;
            restore)
                sub_opts="--force --dry-run --sudo -y --yes"
                ;;
            add)
                sub_opts="--name --run-at-load --scope"
                ;;
            whitelist)
                [ "${COMP_WORDS[2]:-}" = "add" ] && sub_opts="--glob --vendor --exec-prefix --pin --reason"
                case "${COMP_WORDS[2]:-}" in prune|remove) sub_opts="$sub_opts -y --yes" ;; esac
                ;;
            guard)
                sub_opts="--watch --tui --plain --match --value --reason --lock --whitelist --blacklist --dry-run -y --yes"
                ;;
            install|config|help|check|uninstall|backup)
                return 0
                ;;
        esac
        if [ -n "$sub_opts" ]; then
            if [[ "$cur" == -* ]]; then
                COMPREPLY=( $(compgen -W "$sub_opts" -- "$cur") )
            fi
            return 0
        fi
    fi

    # ---- 第一个参数位：子命令 + 文件（不列选项——位置驱动，选项在敲 "-" 之后才出现） ----
    if [ "$COMP_CWORD" -eq 1 ]; then
        if [[ "$cur" == -* ]]; then
            COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
        else
            COMPREPLY=( $(compgen -W "$subcmds" -- "$cur") $(compgen -f -- "$cur") )
        fi
        return 0
    fi

    # 选项只在当前词以 "-" 开头时出现（缺失这道闸门时 `startupctl -y <TAB>`
    # 会把全部选项连 --config 一起铺出来）
    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
    else
        COMPREPLY=( $(compgen -f -- "$cur") )
    fi
}
complete -o filenames -F _startupctl startupctl

# ============================================
# 包装函数（与 jtool/ptool 同规）
# 函数在**父 shell** 里执行，所以 startupctl update 跑完后可以立刻重载本文件，
# 不必手动 source ~/.bashrc 或重开终端——更新是**就地**替换安装目录里的这一份，
# 而 shell 认的是已加载进内存的那份定义。（脚本本身是子进程，改不了父 shell
# 的环境，只有 shell 函数做得到。）
#   · update 后就地重载（重装会把本文件换成新版，sourced 的旧定义得跟着换）；
#   · uninstall 后本文件已不在，改为重载 rc 让 PATH 接线一起消失，并清掉本函数；
#   · install 不在此列：startupctl install 只**打印安装方式**，不落地任何文件。
# ⚠️ 加 sudo 会绕过本函数（sudo 按 PATH 找可执行文件，不看 shell 函数），
#    届时仍需手动 source —— 更新本身会按需提权，正常敲 `startupctl update` 即可。
# ============================================
# 本文件自身的路径（source 时取当前文件路径）；重装后重载指向的仍是安装目录那一份
_startupctl_self="${BASH_SOURCE[0]}"

startupctl() {
    command startupctl "$@"
    local _startupctl_ret=$?
    case "$1" in
        update)
            [ -f "$_startupctl_self" ] && source "$_startupctl_self"
            hash -r 2>/dev/null
            ;;
        uninstall)
            source ~/.bashrc 2>/dev/null
            unset -f startupctl 2>/dev/null
            hash -r 2>/dev/null
            ;;
    esac
    return $_startupctl_ret
}

# ============================================
# 说明（devtools 安装形态）
# 安装后 PATH 与补全都由安装目录提供，接线写在 ~/.bashrc 的
# `# >>> startupctl >>>` 块里（由 installer/shell-setup.sh 维护，幂等）。
# 仓库 bin/ 是素材目录（startupctl.sh + startupctl.bat），**不进 PATH** ——
# 命令名补全走 $commands 哈希，而它不检查可执行位，整体挂上会连
# Windows 启动器 startupctl.bat 一起列出来。startupctl update 后补全自动刷新。
# ============================================
