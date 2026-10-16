#compdef startupctl
# startupctl 补全（zsh）：安装时由 installer/shell-setup.sh 接进 ~/.zshrc 的
# `# >>> startupctl >>>` 块（source 安装目录里的这一份）。手工使用也可直接 source 本文件。
#
# 候选为手写清单（不依赖 _arguments），位置驱动（对齐 jtool/ptool）：
#   startupctl <TAB>              → 子命令 + 文件；**不列选项**（选项在敲 "-" 之后出现）
#   startupctl -<TAB> / --<TAB>   → 全部选项；同义短/长选项合并为一行显示（如 "-y --yes"）
#   startupctl list <TAB>         → list 的专属选项（--all/--running/--vendor …）
#   startupctl whitelist <TAB>    → add / remove / list / doctor / prune
#   startupctl backup <TAB>       → list / prune
#   startupctl update <TAB>       → --check
#   startupctl clean <TAB>        → -y / --yes 及 clean 专属选项
#   startupctl --kind <TAB>       → 启动项类型清单
#   startupctl --confidence <TAB> → high / medium
#   startupctl --scope <TAB>      → system / user
# 已输入过的选项不会重复列出（-y 与 --yes 视为同一个）

# ---- 子命令 ----
_startupctl_subcmds=(
  'list:扫描并列启动项（默认只列第三方）'
  'show:看一项详情：来源 · 命令 · 分类依据 · 原始内容'
  'check:只读体检：启动项干不干净（干净退 0）'
  'scan:快照当前启动项 / 比对载荷漂移'
  'disable:禁用（可逆：停掉并记下禁用态）'
  'enable:恢复启用'
  'remove:移到备份目录（不删文件，可 restore 回来）'
  'add:新建用户级自启项（让某项目开机自动运行）'
  'restore:从备份还原并自动重新启用'
  'backup:看备份 / 清备份'
  'clean:批量禁用第三方项（预览在前，默认只禁用不删）'
  'proc:进程视图：三方进程与启动项聚合'
  'kill:结束进程（先 TERM，--force 才 KILL）'
  'whitelist:白名单：留住自留项'
  'guard:进程守护：三模式 + 选择器（系统基础进程永不结束）'
  'update:拉取最新源码快照并重装（--check 只比对版本）'
  'install:显示安装方式（装到 devtools 目录）'
  'uninstall:卸载安装副本（保留白名单与备份）'
  'config:显示运行信息与配置（含数据目录占用）'
  'help:显示帮助'
)

# 子命令别名（whitelist 的二级动词 / backup 的二级动词）
_startupctl_whitelist_verbs=(
  'add:把一项加入白名单（默认按稳定 id 匹配）'
  'remove:移出白名单（或用 --all-unmatched）'
  'list:列出白名单条目'
  'doctor:报出本次扫描未命中的条目（不自动清理）'
  'prune:清掉未命中的条目'
)
_startupctl_guard_verbs=(
  'status:看当前模式、清单与实时统计'
  'mode:看/设模式（off|deny_all|blacklist|whitelist）'
  'choose:打开选择器（唯一会启动图形窗口的命令）'
  'list:列策略清单'
  'add:按名字/pid 加一条'
  'remove:移除一条（--all 清空）'
  'lock:锁定：任何模式下都不结束它（选择器里也选不动）'
  'unlock:解除锁定'
  'clear:清空策略清单'
  'check:只读：现在会结束哪些'
  'arm:执行一轮；--watch 持续监视'
)
_startupctl_guard_modes=(
  'off:不干预，只报告'
  'deny_all:全部拒绝：除系统基础进程外一律结束'
  'blacklist:黑名单：只结束挑中的'
  'whitelist:白名单：只放行挑中的'
)
_startupctl_backup_verbs=(
  'list:列出备份'
  'prune:按保留策略清理备份'
)

# ---- 选项 ----
_startupctl_opts_long=(
  '--all:含系统项（默认只列第三方）'
  '--confidence:clean 处理的置信度下限'
  '--config:指定配置文件'
  '--deep:额外扫恶意持久化位置（误报较多）'
  '--diff:与上次快照比对，报载荷漂移'
  '--dry-run:只打印将要做什么，绝不改动任何东西'
  '--errors:显示扫描错误与权限受限的根'
  '--exec-prefix:白名单：按可执行路径前缀匹配'
  '--force:强制执行（restore 覆盖已变化的文件等）'
  '--glob:白名单：按锚点通配匹配'
  '--help:显示帮助'
  '--i-know:配合 --include-unknown 使用，免除二次确认'
  '--include-unknown:把无法判定的项也纳入 clean（危险）'
  '--json:机器可读输出'
  '--kind:按启动项类型筛选'
  '--long:显示分类依据等长字段'
  '--name:新建自启项的名称'
  '--orphans:只看没有对应启动项的三方进程'
  '--pin:白名单：钉住当前载荷指纹'
  '--purge:真正删除（Windows 服务；默认只置为禁用）'
  '--raw:显示原始 plist / unit / 注册表内容'
  '--reason:白名单条目的备注'
  '--remove:clean 改为移除而非禁用'
  '--resolve:解析可执行文件的真实路径与签名'
  '--run-at-load:新建项在加载时即运行'
  '--running:只看正在运行的'
  '--save:保存本次扫描为快照'
  '--scope:限定作用域'
  '--strict:把「跳过」也算作失败（脚本用）'
  '--sudo:需要管理员时整条命令交给 sudo 跑一次'
  '--system:只看系统项'
  '--third-party:只看第三方项'
  '--vendor:按厂商前缀筛选'
  '--version:显示版本'
)

# 同义短/长配对（"短 长:描述"）：合并显示为 "-y --yes"；单横线输入时按短形式补全
_startupctl_opts_pairs=(
  '-h --help:显示帮助'
  '-y --yes:跳过确认'
)

# 需要「跳过确认」开关的子命令共用（uninstall / clean / remove / disable / enable /
# kill / restore / backup prune / whitelist prune）
_startupctl_opts_confirm=(
  '-y:跳过确认'
  '--yes:跳过确认'
)

# 各子命令的专属选项
_startupctl_opts_list='--all --system --third-party --running --vendor --kind --scope --json --long --errors'
_startupctl_opts_clean='--remove --confidence --include-unknown --i-know --strict --dry-run --sudo'
_startupctl_opts_mutate='--dry-run --sudo'
_startupctl_opts_scan='--save --diff --json'
_startupctl_opts_show='--raw --resolve --json'
_startupctl_opts_proc='--third-party --system --orphans --json'
_startupctl_opts_kill='--force'
_startupctl_opts_restore='--force'
_startupctl_opts_add='--name --run-at-load --scope'
_startupctl_opts_whitelist_add='--glob --vendor --exec-prefix --pin --reason'

_startupctl() {
  local cur prev i item name used_str disp dw pshort pitem ptmp
  local -a cand
  cur="${words[CURRENT]}"
  prev="${words[CURRENT-1]}"

  # ---- 选项的值位置：补值，不补选项 ----
  case "$prev" in
    --config)
      _files
      return 0
      ;;
    --kind)
      compadd -- launchd launchd-daemon launchd-agent login-item btm \
                 systemd systemd-user xdg-autostart initd cron \
                 registry-run startup-folder win-service task-scheduler
      return 0
      ;;
    --confidence)
      compadd -- high medium
      return 0
      ;;
    --scope)
      compadd -- system user
      return 0
      ;;
    --remove|--all-unmatched)
      return 0
      ;;
  esac

  # ---- 二级动词（whitelist / backup） ----
  if (( CURRENT == 3 )); then
    case "${words[2]}" in
      whitelist)
        _describe -t verbs 'whitelist 子命令' _startupctl_whitelist_verbs
        return 0
        ;;
      backup)
        _describe -t verbs 'backup 子命令' _startupctl_backup_verbs
        return 0
        ;;
      guard)
        _describe -t verbs 'guard 子命令' _startupctl_guard_verbs
        return 0
        ;;
    esac
  fi

  # guard mode <TAB> → 四种子命令模式
  if (( CURRENT == 4 )) && [ "${words[2]}" = "guard" ] && [ "${words[3]}" = "mode" ]; then
    _describe -t modes '守护模式' _startupctl_guard_modes
    return 0
  fi

  # ---- 子命令专属选项 ----
  if (( CURRENT >= 3 )); then
    # 需要「确认」开关的子命令：-y/--yes 是它们唯一（或首要）的开关
    local confirm_sub=0
    case "${words[2]}" in
      uninstall|clean|remove|disable|enable|kill|restore) confirm_sub=1 ;;
      backup)  [ "${words[3]:-}" = "prune" ] && confirm_sub=1 ;;
      whitelist) case "${words[3]:-}" in prune|remove) confirm_sub=1 ;; esac ;;
    esac
    if [ "$confirm_sub" = 1 ] && [[ "$cur" != -* ]]; then
      _describe -O '确认' _startupctl_opts_confirm
      return 0
    fi

    case "${words[2]}" in
      update)
        compadd -- --check
        return 0
        ;;
      list)
        cand=( ${=_startupctl_opts_list} )
        ;;
      clean)
        cand=( ${=_startupctl_opts_clean} )
        ;;
      disable|enable|remove)
        cand=( ${=_startupctl_opts_mutate} )
        ;;
      scan)
        cand=( ${=_startupctl_opts_scan} )
        ;;
      show)
        cand=( ${=_startupctl_opts_show} )
        ;;
      proc)
        cand=( ${=_startupctl_opts_proc} )
        ;;
      kill)
        cand=( ${=_startupctl_opts_kill} ${=_startupctl_opts_mutate} )
        ;;
      restore)
        cand=( ${=_startupctl_opts_restore} ${=_startupctl_opts_mutate} )
        ;;
      add)
        cand=( ${=_startupctl_opts_add} )
        ;;
      whitelist)
        [ "${words[3]:-}" = "add" ] && cand=( ${=_startupctl_opts_whitelist_add} )
        ;;
      guard)
        cand=( --watch --tui --plain --match --value --reason --lock --whitelist --blacklist --dry-run -y --yes )
        ;;
      install|config|help|check|uninstall|backup)
        return 0
        ;;
    esac
    if (( ${#cand} )); then
      [[ "$cur" == -* ]] && compadd -- "${cand[@]}"
      return 0
    fi
  fi

  # 选项只在当前词以 "-" 开头时作为候选出现（位置驱动：第一个参数位只出
  # 「子命令 + 文件」，不铺选项墙）。缺失这道闸门时 `startupctl -y <TAB>`
  # 会把除 --yes 外的全部选项连 --config 一起铺出来。
  if [[ "$cur" == -* ]]; then
    used_str=' '
    for (( i = 2; i < CURRENT; i++ )); do
      case "${words[i]}" in
        -y) used_str+='--yes ' ;;
        -h) used_str+='--help ' ;;
        -*) used_str+="${${words[i]}%%=*} " ;;
      esac
    done

    # 拼装候选与显示串（配对项合并显示为 "-y --yes"）。
    # 单横线场景（- / -y 等）配对项以【短形式】作为匹配词：保证 -y<TAB> 可补全，
    # 且裸 "-" + TAB 不会被整体补成 "--"。
    local -a wshow dword dodesc
    wshow=()
    dword=()
    dodesc=()
    local use_short=0
    [[ "$cur" == -* && "$cur" != --* ]] && use_short=1
    for item in "${_startupctl_opts_long[@]}"; do
      name="${item%%:*}"
      desc="${item#*:}"
      disp="$name"
      pshort=""
      for pitem in "${_startupctl_opts_pairs[@]}"; do
        ptmp="${pitem%%:*}"
        if [[ "$name" == "${ptmp##* }" ]]; then
          disp="$ptmp"
          pshort="${ptmp%% *}"
          desc="${pitem#*:}"
          break
        fi
      done
      [[ "$used_str" == *" $name "* ]] && continue
      if (( use_short )) && [[ -n "$pshort" ]]; then
        wshow+=("$pshort")
      else
        wshow+=("$name")
      fi
      dword+=("$disp")
      dodesc+=("$desc")
    done

    if (( ${#wshow} )); then
      local wmax=0
      for dw in "${dword[@]}"; do
        (( ${#dw} > wmax )) && wmax=${#dw}
      done
      local -a ddisp
      ddisp=()
      for (( i = 1; i <= ${#wshow}; i++ )); do
        ddisp+=("$(printf "%-$((wmax+2))s-- %s" "${dword[i]}" "${dodesc[i]}")")
      done
      compadd -l -d ddisp -- "${wshow[@]}"
    fi
    return 0
  fi

  # 其他位置：子命令（仅第二个词）+ 文件
  if (( CURRENT == 2 )); then
    _describe -t commands 'startupctl 子命令' _startupctl_subcmds
  fi
  _files
}

# compinit 未初始化时（例如 .zshrc 里没有 compinit）先初始化，否则 compdef 不存在，
# 补全会**静默**不注册——用户只看到"TAB 没反应"，无从排查（与 jtool/ptool 同规）
if (( ! $+functions[compdef] )); then
  autoload -Uz compinit && compinit
fi
compdef _startupctl startupctl

# ============================================
# 包装函数（与 jtool/ptool 同规）
# 函数在**父 shell** 里执行，所以 startupctl update 跑完后可以立刻重载本文件，
# 不必手动 source ~/.zshrc 或重开终端——更新是**就地**替换安装目录里的这一份，
# 而 shell 认的是已加载进内存的那份定义。（脚本本身是子进程，改不了父 shell
# 的环境，只有 shell 函数做得到。）
#   · update 后就地重载（重装会把本文件换成新版，sourced 的旧定义得跟着换）；
#   · uninstall 后本文件已不在，改为重载 rc 让 PATH 接线一起消失，并清掉本函数；
#   · install 不在此列：startupctl install 只**打印安装方式**，不落地任何文件。
# ⚠️ 加 sudo 会绕过本函数（sudo 按 PATH 找可执行文件，不看 shell 函数），
#    届时仍需手动 source —— 更新本身会按需提权，正常敲 `startupctl update` 即可。
# ============================================
# 本文件自身的路径（source 时取当前文件路径）；重装后重载指向的仍是安装目录那一份
_startupctl_self="${(%):-%x}"

startupctl() {
  command startupctl "$@"
  local ret=$?
  case "$1" in
    update)
      [ -f "$_startupctl_self" ] && source "$_startupctl_self"
      hash -r 2>/dev/null
      ;;
    uninstall)
      source ~/.zshrc 2>/dev/null
      unfunction startupctl 2>/dev/null
      hash -r 2>/dev/null
      ;;
  esac
  return $ret
}

# ============================================
# 说明（devtools 安装形态）
# 安装后 PATH 与补全都由安装目录提供，接线写在 ~/.zshrc 的
# `# >>> startupctl >>>` 块里（由 installer/shell-setup.sh 维护，幂等）。
# 仓库 bin/ 是素材目录（startupctl.sh + startupctl.bat），**不进 PATH** ——
# 命令名补全走 $commands 哈希，而它不检查可执行位，整体挂上会连
# Windows 启动器 startupctl.bat 一起列出来。startupctl update 后补全自动刷新。
# ============================================
