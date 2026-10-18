#compdef startupctl
# encoding: utf-8
# startupctl 补全（zsh）：安装时由 installer/shell-setup.sh 接进 ~/.zshrc 的
# `# >>> startupctl >>>` 块（source 安装目录里的这一份）。手工使用也可直接 source。
#
# **本工具没有选项**，所以 `-` 之后不补任何东西。补全是纯位置驱动的，而且
# **每一层都给描述**（和 `startupctl <TAB>` 第一层一样）：
#   startupctl <TAB>                     → 10 个外层命令
#   startupctl list <TAB>                → all / system
#   startupctl mode <TAB>                → off / deny_all / blacklist / whitelist
#   startupctl whitelist <TAB>           → startup / process
#   startupctl whitelist startup <TAB>   → selector
#   startupctl update <TAB>              → check
#   startupctl uninstall <TAB>           → confirm
#   startupctl help <TAB>                → 子命令

_startupctl_subcmds=(
  'list:列出启动项（默认第三方）'
  'mode:看/设模式（off · deny_all · blacklist · whitelist）'
  'whitelist:白名单：启动项 / 进程两个维度'
  'blacklist:黑名单：启动项 / 进程两个维度'
  'config:显示配置、数据目录与模式'
  'version:显示版本'
  'help:帮助'
  'update:检查并更新到最新版本'
  'install:完整安装（从源码目录）'
  'uninstall:卸载（保留名单）'
)
_startupctl_scopes=(
  'all:连系统项一起列'
  'system:只看系统项'
)
_startupctl_modes=(
  'off:不干预，只报告（默认）'
  'deny_all:全部拒绝：除系统基础进程外一律结束'
  'blacklist:黑名单：只结束挑中的'
  'whitelist:白名单：只放行挑中的'
)
_startupctl_dims=(
  'startup:启动项维度'
  'process:进程维度'
)
_startupctl_selector=(
  'selector:开窗口挑条目加入名单'
)
_startupctl_update_acts=(
  'check:只比对版本，不落盘'
)
_startupctl_uninstall_acts=(
  'confirm:跳过确认，直接卸载'
)

_startupctl() {
  local -a subcmds scopes modes dims selector update_acts uninstall_acts
  subcmds=("${_startupctl_subcmds[@]}")
  scopes=("${_startupctl_scopes[@]}")
  modes=("${_startupctl_modes[@]}")
  dims=("${_startupctl_dims[@]}")
  selector=("${_startupctl_selector[@]}")
  update_acts=("${_startupctl_update_acts[@]}")
  uninstall_acts=("${_startupctl_uninstall_acts[@]}")

  if (( CURRENT == 2 )); then
    _describe -t commands 'startupctl' subcmds
    return
  fi

  case ${words[2]} in
    list)
      (( CURRENT == 3 )) && _describe -t scopes '范围' scopes && return
      ;;
    mode)
      (( CURRENT == 3 )) && _describe -t modes '模式' modes && return
      ;;
    whitelist|blacklist)
      if (( CURRENT == 3 )); then
        _describe -t dims '维度' dims
        return
      elif (( CURRENT == 4 )); then
        _describe -t actions '动作' selector
        return
      fi
      ;;
    update)
      (( CURRENT == 3 )) && _describe -t actions '动作' update_acts && return
      ;;
    uninstall)
      (( CURRENT == 3 )) && _describe -t actions '动作' uninstall_acts && return
      ;;
    help)
      (( CURRENT == 3 )) && _describe -t commands '子命令' subcmds && return
      ;;
  esac
}

# 注册。直接 source 时 `#compdef` 只是注释，必须显式 compdef 才会生效。
# compinit 未初始化时先初始化，否则 compdef 不存在。
if (( ! $+functions[compdef] )); then
  autoload -Uz compinit && compinit
fi
compdef _startupctl startupctl
