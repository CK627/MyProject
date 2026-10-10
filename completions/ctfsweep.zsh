#compdef ctfsweep
# ctfsweep 补全（zsh）：把本文件所在目录加入 fpath 后重开终端，或直接 source 本文件
# （installer/install.sh 会把 source 行写进 ~/.zshrc，自动生效）。

_ctfsweep() {
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
