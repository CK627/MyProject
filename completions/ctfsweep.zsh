#compdef ctfsweep
# ctfsweep 补全（zsh）：把本文件所在目录加入 fpath 后重开终端，或直接 source 本文件
# （源码直跑模式：在 ~/.zshrc 中 source 项目里的本文件即可）。
#
# 候选为手写清单（不依赖 _arguments）：
#   ctf <TAB>             → 子命令 + 全部选项 + 文件（不敲 "-" 也能看到 --选项）
#   ctf -<TAB> / --<TAB>  → 全部选项；同义短/长选项合并为一行显示（如 "-f --file"）
#   ctf -f<TAB>           → 直接补全 -f（短形式仍可按前缀补全；--f<TAB> → --file）
#   ctf -f <TAB>          → 补全文件；-F <TAB> → 补全文件夹；--extract-dir <TAB> → 补全目录
#   ctf --min-score <TAB> → 0.40 / 0.55 / 0.85 / 0.95
#   ctf uninstall <TAB>   → -y / --yes
#   ctf train <TAB>       → --data / --epochs / --model-out
#   已输入过的选项不会重复列出（-f 与 --file 视为同一个）

# ---- 候选清单 ----
_ctfsweep_subcmds=(
  'update:更新指引（源码直跑：git pull）'
  'install:已弃用（源码直跑，不安装外部副本）'
  'uninstall:清理旧版安装残留（保留数据）'
  'config:显示运行信息与配置'
  'train:训练本地判断核（judge）模型'
  'label:交互式标注未标注候选'
  'learning:自主学习（带收敛判断）'
  'help:显示帮助'
)

_ctfsweep_opts_long=(
  '--config:指定配置文件'
  '--depth:解码链最大深度'
  '--extract:从流量中提取文件（ZIP/图片/PDF/GZ 等）'
  '--extract-dir:提取输出目录'
  '--file:指定要扫描的文件'
  '--folder:指定要扫描的文件夹（整个项目目录）'
  '--help:显示帮助'
  '--judge:用判断核模型对候选打分（需先 train）'
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
)

_ctfsweep_opts_uninstall=(
  '-y:跳过确认'
  '--yes:跳过确认'
)

_ctfsweep_opts_train=(
  '--data:数据集文件（默认 ~/.devtools/ctfsweep/judge/dataset.jsonl）'
  '--epochs:训练轮数'
  '--model-out:模型输出路径'
)

_ctfsweep_opts_label=(
  '--batch:每批标注条数（默认 10）'
)

_ctfsweep_opts_learning=(
  '--min-auc:最低 AUC 达标值（默认 0.85）'
  '--min-samples:最低样本数（默认 16）'
  '--max-epochs:最大训练轮数（默认 500）'
  '--epochs:每轮训练轮数（默认 200）'
)

_ctfsweep() {
  local cur prev i item name used_str disp dw pshort pitem
  local use_short=0
  cur="${words[CURRENT]}"
  prev="${words[CURRENT-1]}"

  # 子命令专属参数区（ctfsweep update ... / ctfsweep train ...）
  if (( CURRENT >= 3 )); then
    case "${words[2]}" in
      update)
        return 0   # update 无参数（仅输出更新指引）
        ;;
      uninstall)
        _describe -O 'uninstall 选项' _ctfsweep_opts_uninstall
        return 0
        ;;
      train)
        case "$prev" in
          --data|--model-out|--model)
            _files
            return 0
            ;;
          --epochs)
            compadd -- 100 250 500 1000
            return 0
            ;;
        esac
        _describe -O 'train 选项' _ctfsweep_opts_train
        return 0
        ;;
      label)
        case "$prev" in
          --batch)
            compadd -- 5 10 20 50
            return 0
            ;;
        esac
        _describe -O 'label 选项' _ctfsweep_opts_label
        return 0
        ;;
      learning)
        case "$prev" in
          --min-auc)
            compadd -- 0.80 0.85 0.90 0.95
            return 0
            ;;
          --min-samples|--max-epochs|--epochs)
            compadd -- 8 16 32 64 100 200 500 1000
            return 0
            ;;
        esac
        _describe -O 'learning 选项' _ctfsweep_opts_learning
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

  # 收集已用过的选项（空格分隔串；-f / -k / -h 归一为对应长选项；--x=y 截到 --x）
  used_str=' '
  for (( i = 2; i < CURRENT; i++ )); do
    case "${words[i]}" in
      -f) used_str+='--file ' ;;
      -F) used_str+='--folder ' ;;
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
# 说明（源码直跑模式）
# 补全与 PATH 均由本文件所在的项目目录提供；代码更新（git pull）后无需刷新。
# （历史版本曾在此定义 ctfsweep 包装函数用于安装后的即时刷新，已随安装模式移除）
# ============================================
