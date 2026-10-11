#compdef ctfsweep
# ctfsweep 补全（zsh）：把本文件所在目录加入 fpath 后重开终端，或直接 source 本文件
# （installer/install.sh 会把 source 行写进 ~/.zshrc，自动生效）。
#
# 候选为手写清单（不依赖 _arguments）：
#   ctf <TAB>             → 子命令 + 全部选项 + 文件（不敲 "-" 也能看到 --选项）
#   ctf -<TAB> / --<TAB>  → 全部选项；同义短/长选项合并为一行显示（如 "-f --file"）
#   ctf -f<TAB>           → 直接补全 -f（短形式仍可按前缀补全；--f<TAB> → --file）
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

# 同义短/长配对（格式 "短 长:描述"）：列表里合并显示为 "-f --file"；
# 单横线输入（如 -f）时按短形式提供补全
_ctfsweep_opts_pairs=(
  '-f --file:指定要扫描的文件'
  '-h --help:显示帮助'
  '-k --keywords:追加关键词（逗号分隔）'
)

_ctfsweep_opts_update=(
  '--check:仅检查更新，不执行升级'
)

_ctfsweep_opts_uninstall=(
  '-y:跳过确认'
  '--yes:跳过确认'
)

_ctfsweep() {
  local cur prev i item name used_str disp dw pshort pitem
  local use_short=0
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
  used_str=' '
  for (( i = 2; i < CURRENT; i++ )); do
    case "${words[i]}" in
      -f) used_str+='--file ' ;;
      -k) used_str+='--keywords ' ;;
      -h) used_str+='--help ' ;;
      -*) used_str+="${${words[i]}%%=*} " ;;
    esac
  done

  # 拼装选项候选与显示串（配对项合并显示为 "-f --file"）
  # 单横线场景（- / -f 等）配对项以【短形式】作为匹配词：保证 -f<TAB> 可补全，
  # 且裸 "-" + TAB 不会被整体补成 "--"（全部候选的共同前缀保持为 "-"）。
  local -a wshow dword dodesc
  wshow=()
  dword=()
  dodesc=()
  use_short=0
  [[ "$cur" == -* && "$cur" != --* ]] && use_short=1
  for item in "${_ctfsweep_opts_long[@]}"; do
    name="${item%%:*}"
    desc="${item#*:}"
    disp="$name"
    pshort=""
    for pitem in "${_ctfsweep_opts_pairs[@]}"; do
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

  # 加入候选：显示串自带 "word -- 描述" 排版；-l 保证一屏一行（不排多列）。
  # 不指定 -o：默认按显示串排序 —— --长选项在前，"-f --file" 等短形式组自然落在末尾。
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

  # 光标在选项区：到此为止（选项场景不补文件）
  if [[ "$cur" == -* ]]; then
    return 0
  fi

  # 其他位置：子命令（仅第二个词）+ 文件
  if (( CURRENT == 2 )); then
    _describe -t commands 'ctfsweep 子命令' _ctfsweep_subcmds
  fi
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
