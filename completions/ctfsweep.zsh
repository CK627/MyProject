#compdef ctfsweep
# ctfsweep 补全（zsh）：把本文件所在目录加入 fpath 后重开终端，或直接 source 本文件
# （installer/install.sh 会把 source 行写进 ~/.zshrc，自动生效）。

_ctfsweep_subcmds=(
  'update:检查并更新到最新版（镜像优先，回退 GitHub）'
  'install:从源码仓库安装到 devtools'
  'uninstall:卸载 ctfsweep'
  'config:显示配置与安装信息'
  'help:显示帮助'
)

_ctfsweep() {
  if (( CURRENT == 2 )); then
    _describe -t commands 'ctfsweep 子命令' _ctfsweep_subcmds
  fi
  _arguments -s \
    '(-f --file)'{-f,--file}'[指定要扫描的文件]:文件:_files' \
    '(-k --keywords)'{-k,--keywords}'[追加关键词，逗号分隔]:关键词:' \
    '--min-score[只显示置信度不低于该值的结果]:分数:(0.40 0.55 0.85 0.95)' \
    '--no-decode[关闭 hex/base64 自动解码]' \
    '--depth[解码链最大深度]:深度:(1 2 3 4 5)' \
    '--limit[每个文件最多输出条数]:条数:' \
    '--extract[从流量中提取文件（ZIP/图片/PDF/GZ 等）]' \
    '--extract-dir[提取输出目录]:目录:_files -/' \
    '--pwd-file[压缩包口令字典文件]:文件:_files' \
    '--config[指定配置文件]:文件:_files' \
    '--version[显示版本]' \
    '(-h --help)'{-h,--help}'[显示帮助]' \
    '*:待扫描文件或目录:_files'
}

if (( $+functions[compdef] )); then
  compdef _ctfsweep ctfsweep
fi

# ============================================
# 包装函数
# 函数在当前 shell 里执行，所以 ctfsweep update / install / uninstall 跑完后可以
# 立刻刷新补全与 shell 状态，不必手动 source ~/.zshrc 或重开终端。
# （脚本本身是子进程，无法修改父 shell 的环境，只有 shell 函数能做到这一点）
# ============================================
ctfsweep() {
  command ctfsweep "$@"
  local _ctfsweep_ret=$?
  case "$1" in
    update|install)
      [ -f "$HOME/.devtools/ctfsweep/completions/ctfsweep.zsh" ] \
        && source "$HOME/.devtools/ctfsweep/completions/ctfsweep.zsh"
      hash -r 2>/dev/null
      ;;
    uninstall)
      # 卸载后重载 shell 配置并移除本包装函数
      source ~/.zshrc 2>/dev/null
      unfunction ctfsweep 2>/dev/null
      hash -r 2>/dev/null
      ;;
  esac
  return $_ctfsweep_ret
}
