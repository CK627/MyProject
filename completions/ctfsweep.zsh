#compdef ctfsweep
# ctfsweep 补全（zsh）：安装时由 installer/shell-setup.sh 接进 ~/.zshrc 的
# `# >>> ctfsweep >>>` 块（source 安装目录里的这一份）。手工使用也可直接 source 本文件。
#
# 候选为手写清单（不依赖 _arguments），位置驱动（对齐 jtool/ptool）：
#   ctfsweep <TAB>             → 子命令 + 文件；**不列选项**（选项在敲 "-" 之后出现）
#   ctfsweep -<TAB> / --<TAB>  → 全部选项；同义短/长选项合并为一行显示（如 "-f --file"）
#   ctfsweep -f<TAB>           → 直接补全 -f（短形式仍可按前缀补全；--f<TAB> → --file）
#   ctfsweep -f <TAB>          → 补全文件；-F <TAB> → 补全文件夹；--extract-dir <TAB> → 补全目录
#   ctfsweep -q <TAB>          → 只补文件（选项只在当前词以 "-" 开头时出现）
#   ctfsweep --min-score <TAB> → 0.40 / 0.55 / 0.85 / 0.95
#   ctfsweep -q                → 精简输出（控制台只打汇总块，明细在数据目录 cache/）
#   ctfsweep uninstall <TAB>   → -y / --yes
#   ctfsweep clear <TAB>       → -y / --yes
#（命令名只有 ctfsweep 一个：没有 ctf 短别名，所以本文件也不为它注册补全）
#   已输入过的选项不会重复列出（-f 与 --file 视为同一个）

# ---- 候选清单 ----
_ctfsweep_subcmds=(
  'update:拉取最新源码快照并重装（--check 只比对版本）'
  'install:显示安装方式（装到 devtools 目录）'
  'uninstall:卸载安装副本（保留扫描缓存）'
  'config:显示运行信息与配置（含扫描缓存占用）'
  'clear:清空扫描缓存（-y 跳过确认）'
  'help:显示帮助'
)

_ctfsweep_opts_long=(
  '--brief:精简输出（明细写缓存文件）'
  '--config:指定配置文件'
  '--depth:解码链最大深度'
  '--extract:从流量中提取文件（ZIP/图片/PDF/GZ 等）'
  '--extract-dir:提取输出目录'
  '--file:指定要扫描的文件'
  '--folder:指定要扫描的文件夹（整个项目目录）'
  '--help:显示帮助'
  '--judge:用判断核模型对候选打分（模型随版本发布）'
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
  '-F --folder:指定要扫描的文件夹（整个项目目录）'
  '-f --file:指定要扫描的文件'
  '-h --help:显示帮助'
  '-k --keywords:追加关键词（逗号分隔）'
  '-q --brief:精简输出（明细写缓存文件）'
)

# uninstall / clear 共用：这两个子命令都只有一个"跳过确认"开关
_ctfsweep_opts_confirm=(
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
        compadd -- --check
        return 0
        ;;
      uninstall)
        _describe -O 'uninstall 选项' _ctfsweep_opts_confirm
        return 0
        ;;
      clear)
        _describe -O 'clear 选项' _ctfsweep_opts_confirm
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
    -F|--folder)
      _files -/
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

  # 选项只在当前词以 "-" 开头时作为候选出现（对齐 jtool/ptool 的位置驱动补全：
  # 第一个参数位只出「子命令 + 文件」，不铺选项墙）。缺失这道闸门时
  # `ctfsweep -q <TAB>` 会把除 --brief 外的全部 14 个选项连 --config 一起铺出来
  # （按显示串排序，--config 恰好第一，最扎眼）。
  if [[ "$cur" == -* ]]; then
    # 收集已用过的选项（空格分隔串；-f / -k / -h 归一为对应长选项；--x=y 截到 --x）
    used_str=' '
    for (( i = 2; i < CURRENT; i++ )); do
      case "${words[i]}" in
        -f) used_str+='--file ' ;;
        -F) used_str+='--folder ' ;;
        -k) used_str+='--keywords ' ;;
        -q) used_str+='--brief ' ;;
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
    return 0
  fi

  # 其他位置：子命令（仅第二个词）+ 文件
  if (( CURRENT == 2 )); then
    _describe -t commands 'ctfsweep 子命令' _ctfsweep_subcmds
  fi
  _files
}

# compinit 未初始化时（例如 .zshrc 里没有 compinit）先初始化，否则 compdef 不存在，
# 补全会**静默**不注册——用户只看到"TAB 没反应"，无从排查（与 jtool/ptool 同规）
if (( ! $+functions[compdef] )); then
  autoload -Uz compinit && compinit
fi
compdef _ctfsweep ctfsweep

# ============================================
# 包装函数（与 jtool/ptool 同规）
# 函数在**父 shell** 里执行，所以 ctfsweep update 跑完后可以立刻重载本文件，
# 不必手动 source ~/.zshrc 或重开终端——更新是**就地**替换安装目录里的这一份，
# 而 shell 认的是已加载进内存的那份定义。（脚本本身是子进程，改不了父 shell
# 的环境，只有 shell 函数做得到。）
#   · update 后就地重载（重装会把本文件换成新版，sourced 的旧定义得跟着换）；
#   · uninstall 后本文件已不在，改为重载 rc 让 PATH 接线一起消失，并清掉本函数；
#   · install 不在此列：ctfsweep install 只**打印安装方式**，不落地任何文件。
# ⚠️ 加 sudo 会绕过本函数（sudo 按 PATH 找可执行文件，不看 shell 函数），
#    届时仍需手动 source —— 更新本身会按需提权，正常敲 `ctfsweep update` 即可。
# ============================================
# 本文件自身的路径（source 时取当前文件路径）；重装后重载指向的仍是安装目录那一份
_ctfsweep_self="${(%):-%x}"

ctfsweep() {
  command ctfsweep "$@"
  local ret=$?
  case "$1" in
    update)
      [ -f "$_ctfsweep_self" ] && source "$_ctfsweep_self"
      hash -r 2>/dev/null
      ;;
    uninstall)
      source ~/.zshrc 2>/dev/null
      unfunction ctfsweep 2>/dev/null
      hash -r 2>/dev/null
      ;;
  esac
  return $ret
}

# ============================================
# 说明（devtools 安装形态）
# 安装后 PATH 与补全都由安装目录提供，接线写在 ~/.zshrc 的
# `# >>> ctfsweep >>>` 块里（由 installer/shell-setup.sh 维护，幂等）。
# 仓库 bin/ 是素材目录（ctfsweep.sh + ctfsweep.bat），**不进 PATH** ——
# 命令名补全走 $commands 哈希，而它不检查可执行位，整体挂上会连
# Windows 启动器 ctfsweep.bat 一起列出来。ctfsweep update 后补全自动刷新。
# ============================================
