# ptool zsh 补全
# 由 ptool 安装脚本生成，请勿手动修改
# 配置文件: @CONFIG_FILE@

# 从配置文件读取 PYTHON_BASE_DIR，列出已安装的版本号（不执行解释器，保证 <TAB> 响应速度）
_ptool_versions() {
    local config_file="@CONFIG_FILE@"
    local base_dir=""
    [ -f "$config_file" ] && base_dir=$(grep '^PYTHON_BASE_DIR=' "$config_file" 2>/dev/null | tail -1 | cut -d'"' -f2)
    [ -n "$base_dir" ] || return 0

    local bin name ver
    for bin in "$base_dir"/python[0-9]*; do
        [ -x "$bin" ] || continue
        name=${bin:t}
        # 跳过 python3-config、python3-intel64 等非解释器
        case "$name" in *-*) continue ;; esac
        ver=${name#python}
        # python3.13t / python3.6m → 3.13 / 3.6
        ver=${ver%%[^0-9.]*}
        [ -n "$ver" ] && print -r -- "$ver"
    done
}

_ptool() {
    local -a subcmds tools versions

    subcmds=(
        'list:列出所有已安装的 Python'
        'use:设置默认版本'
        'current:查看当前默认版本'
        'home:输出安装路径'
        'info:显示详细信息'
        'tools:列出可用工具'
        'run:运行 Python 文件'
        'scan:扫描 Python 路径并更新配置'
        'config:显示配置'
        'install:完整安装'
        'update:检查并更新 ptool'
        'shim:重建 shim 脚本'
        'help:显示帮助'
    )
    tools=(python python3 pip pip3 pip2)
    # o=排序 n=按数字比较 u=去重，使 3.6 排在 3.10 前面
    versions=(${(onu)${(f)"$(_ptool_versions)"}})

    # 第一个参数：子命令 + 工具名
    if (( CURRENT == 2 )); then
        _describe -t commands 'ptool 命令' subcmds
        _describe -t tools 'Python 工具' tools
        return
    fi

    case ${words[2]} in
        use|home|info|tools)
            # ptool <子命令> <版本>
            (( CURRENT == 3 )) && _describe -t versions 'Python 版本' versions
            ;;
        run)
            # ptool run <版本> <文件>
            if (( CURRENT == 3 )); then
                _describe -t versions 'Python 版本' versions
            else
                _files -g '*.py'
            fi
            ;;
        python|python3|pip|pip3|pip2)
            # ptool python <版本> [参数...]
            if (( CURRENT == 3 )); then
                _describe -t versions 'Python 版本' versions
            else
                _files
            fi
            ;;
        *)
            _files
            ;;
    esac
}

# compinit 未初始化时（例如 .zshrc 里没有 compinit）先初始化，否则 compdef 不存在
if (( ! $+functions[compdef] )); then
    autoload -Uz compinit && compinit
fi
compdef _ptool ptool ptool.sh
