#compdef ctfsweep
# ctfsweep 补全（zsh）：把本文件所在目录加入 fpath 后重开终端，或直接 source 本文件
# （installer/install.sh 会把 source 行写进 ~/.zshrc，自动生效）。
#
# 候选为手写清单（不依赖 _arguments），保证各版本 zsh 下行为一致、直观：
#   ctf <TAB>             → 子命令 + 全部长选项 + 文件（不敲 "-" 也能看到 --选项）
#   ctf --<TAB>           → 全部长选项
#   ctf -<TAB>            → 全部选项（含 -f / -k / -h）
#   ctf -f <TAB>          → 补全文件；--extract-dir <TAB> → 补全目录
#   ctf --min-score <TAB> → 0.40 / 0.55 / 0.85 / 0.95
#   ctf update <TAB>      → --check；ctf uninstall <TAB> → -y / --yes
#   已输入过的选项不会重复列出（-f 与 --file 视为同一个）

# ---- 候选清单 ----
_ctfsweep_subcmds=(
  'update:检查并更新到最新版（镜像优先，回退 GitHub）'
  'install:从源码仓库安装到 devtools'
  'uninstall:卸载 ctfsweep'
  'config:显示配置与安装信息'
  'help:显示帮助'
)

_ctfsweep_opts_long=(
  '--config:指定配置文件'
  '--depth:解码链最大深度'
  '--extract:从流量中提取文件（ZIP/图片/PDF/GZ 等）'
  '--extract-dir:提取输出目录'
  '--file:指定要扫描的文件'
  '--help:显示帮助'
  '--keywords:追加关键词（逗号分隔）'
  '--limit:每个文件最多输出条数'
  '--min-score:只显示置信度不低于该值的结果'
  '--no-decode:关闭 hex/base64 自动解码'
  '--pwd-file:压缩包口令字典文件'
  '--version:显示版本'
)

_ctfsweep_opts_short=(
  '-f:指定要扫描的文件（同 --file）'
  '-h:显示帮助（同 --help）'
  '-k:追加关键词（同 --keywords）'
)

_ctfsweep_opts_update=(
  '--check:仅检查更新，不执行升级'
)

_ctfsweep_opts_uninstall=(
  '-y:跳过确认'
  '--yes:跳过确认'
)

_ctfsweep() {
  local cur prev i item name used_str
  cur="${words[CURRENT]}"
  prev="${words[CURRENT-1]}"

  # 子命令专属参数区（ctfsweep update ... / ctfsweep uninstall ...）
  if (( CURRENT >= 3 )); then
    case "${words[2]}" in
      update)
        _describe -O 'update 选项' _ctfsweep_opts_update
        return 0
        ;;
      uninstall)
        _describe -O 'uninstall 选项' _ctfsweep_opts_uninstall
        return 0
        ;;
      install|config|help)
        return 0
        ;;
    esac
  fi

  # 主命令：选项的值位置，补对应的值而不是选项
  case "$prev" in
    -f|--file|--pwd-file|--config)
      _files
      return 0
      ;;
    --extract-dir)
      _files -/
      return 0
      ;;
    -k|--keywords)
      compadd -- flag ctf key secret
      return 0
      ;;
    --depth)
      compadd -- 1 2 3 4 5
      return 0
      ;;
    --min-score)
      compadd -- 0.40 0.55 0.85 0.95
      return 0
      ;;
    --limit)
      return 0
      ;;
  esac

  # 收集已用过的选项（空格分隔串；-f / -k / -h 归一为对应长选项；--x=y 截到 --x）
  local -a opts_show
  opts_show=()
  used_str=' '
  for (( i = 2; i < CURRENT; i++ )); do
    case "${words[i]}" in
      -f) used_str+='--file ' ;;
      -k) used_str+='--keywords ' ;;
      -h) used_str+='--help ' ;;
      -*) used_str+="${${words[i]}%%=*} " ;;
    esac
  done
  for item in "${_ctfsweep_opts_long[@]}"; do
    name="${item%%:*}"
    [[ "$used_str" == *" $name "* ]] || opts_show+=("$item")
  done
  if [[ "$cur" == -* && "$cur" != --* ]]; then
    for item in "${_ctfsweep_opts_short[@]}"; do
      name="${item%%:*}"
      [[ "$used_str" == *" $name "* ]] || opts_show+=("$item")
    done
  fi

  # 光标在选项区（- / -- / --x）：列出选项
  # 用 _describe -O（而非 -t options）：后者默认「没敲 - 就不显示选项」（prefix-needed
  # 样式，见 _describe 源码），-O 则总是可列出——这正是「不敲 - 也能 TAB 出选项」的关键。
  if [[ "$cur" == -* ]]; then
    (( ${#opts_show} )) && _describe -O 'ctfsweep 选项' opts_show
    return 0
  fi

  # 其他位置：子命令（仅第二个词）+ 长选项 + 文件
  if (( CURRENT == 2 )); then
    _describe -t commands 'ctfsweep 子命令' _ctfsweep_subcmds
  fi
  (( ${#opts_show} )) && _describe -O 'ctfsweep 选项' opts_show
  _files
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
