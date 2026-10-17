#compdef startupctl
# encoding: utf-8
# startupctl 补全（zsh）：安装时由 installer/shell-setup.sh 接进 ~/.zshrc 的
# `# >>> startupctl >>>` 块（source 安装目录里的这一份）。手工使用也可直接 source。
#
# **本工具没有选项**，所以 `-` 之后不补任何东西。补全是纯位置驱动的：
#   startupctl <TAB>                     → 子命令
#   startupctl list <TAB>                → all / system
#   startupctl mode <TAB>                → off / deny_all / blacklist / whitelist
#   startupctl whitelist <TAB>           → startup / process
#   startupctl whitelist startup <TAB>   → selector
#   startupctl update <TAB>              → check
#   startupctl uninstall <TAB>           → confirm
#   startupctl help <TAB>                → 子命令

_startupctl_subcmds=(
  'list:列出启动项（默认第三方）'
  'mode:看/设模式（off|deny_all|blacklist|whitelist）'
  'whitelist:白名单：启动项 / 进程两个维度'
  'blacklist:黑名单：启动项 / 进程两个维度'
  'config:显示配置、数据目录与模式'
  'version:显示版本'
  'help:帮助'
  'update:检查并更新到最新版本'
  'install:完整安装（从源码目录）'
  'uninstall:卸载（保留名单）'
)

_startupctl() {
  local -a subcmds
  subcmds=("${_startupctl_subcmds[@]}")

  if (( CURRENT == 2 )); then
    _describe -t commands 'startupctl' subcmds
    return
  fi

  local sub=${words[2]}
  case $sub in
    list)
      (( CURRENT == 3 )) && _values '范围' all system && return
      ;;
    mode)
      (( CURRENT == 3 )) && _values '模式' off deny_all blacklist whitelist && return
      ;;
    whitelist|blacklist)
      if (( CURRENT == 3 )); then
        _values '维度' startup process
        return
      elif (( CURRENT == 4 )); then
        _values '动作' selector
        return
      fi
      ;;
    update)
      (( CURRENT == 3 )) && _values '动作' check && return
      ;;
    uninstall)
      (( CURRENT == 3 )) && _values '动作' confirm && return
      ;;
    help)
      (( CURRENT == 3 )) && _describe -t commands '子命令' subcmds && return
      ;;
  esac
}

_startupctl "$@"
