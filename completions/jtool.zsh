# jtool zsh 补全
# 由 jtool 安装脚本生成，请勿手动修改
# 配置文件: @CONFIG_FILE@

# 从配置文件读取 JAVA_BASE_DIR，列出已安装的 JDK 版本号（不执行 java，保证 <TAB> 响应速度）
_jtool_versions() {
    local config_file="@CONFIG_FILE@"
    local base_dir=""
    [ -f "$config_file" ] && base_dir=$(grep '^JAVA_BASE_DIR=' "$config_file" 2>/dev/null | tail -1 | cut -d'"' -f2)
    [ -n "$base_dir" ] || return 0

    local dir name ver target
    local base_real=${base_dir:A}
    # 不挑目录名，只认里面确实是 JDK 的（macOS bundle 或平铺布局）
    for dir in "$base_dir"/*; do
        [ -x "$dir/Contents/Home/bin/java" ] || [ -x "$dir/bin/java" ] || continue
        if [ -L "$dir" ]; then
            # 指向同一基准目录下真目录的软链接（Ubuntu 的 java-1.17.0-openjdk-amd64）
            # 跳过：真目录自己会列出来。不跳就会多出一个 1.17.0——TAB 里看得见，
            # jtool use 1.17.0 却匹配不到，因为解析那边两个名字是同一个 JDK。
            target=${dir:A}
            [ "${target:h}" = "$base_real" ] && continue
        fi
        name=${dir:t}
        name=${name%.jdk}
        # 版本号取目录名里第一段以数字开头的连续串，厂商前缀 / 发行版后缀自动跳过。
        # 与 module/common.sh 的 _jdk_name_version 同一套规则。
        if [[ "$name" =~ [0-9][0-9._]* ]]; then
            ver=${MATCH%.}
            [ -n "$ver" ] && print -r -- "$ver"
        fi
    done
}

_jtool() {
    local -a subcmds tools versions

    subcmds=(
        'list:列出所有已安装的 JDK'
        'use:设置默认版本'
        'current:查看当前默认版本'
        'home:输出 JAVA_HOME 路径'
        'info:显示详细信息'
        'tools:列出可用工具'
        'run:编译并运行 Java 文件'
        'scan:扫描 Java 路径并更新配置'
        'config:显示配置'
        'install:完整安装（从源码目录）'
        'setup:只做用户级配置（shims/补全/shell）'
        'uninstall:卸载'
        'update:检查并更新 jtool'
        'shim:重建 shim 脚本'
        'help:显示帮助'
    )
    tools=(java javac jar jshell javadoc javap)
    # o=排序 n=按数字比较 u=去重，使 1.8 排在 21 前面
    versions=(${(onu)${(f)"$(_jtool_versions)"}})

    # 第一个参数：子命令 + 工具名
    if (( CURRENT == 2 )); then
        _describe -t commands 'jtool 命令' subcmds
        _describe -t tools 'Java 工具' tools
        return
    fi

    case ${words[2]} in
        use|home|info|tools)
            # jtool <子命令> <版本>
            (( CURRENT == 3 )) && _describe -t versions 'JDK 版本' versions
            ;;
        run)
            # jtool run <版本> <文件.java>
            if (( CURRENT == 3 )); then
                _describe -t versions 'JDK 版本' versions
            else
                _files -g '*.java'
            fi
            ;;
        java|javac|jar|jshell|javadoc|javap)
            # jtool java <版本> [参数...]
            if (( CURRENT == 3 )); then
                _describe -t versions 'JDK 版本' versions
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
compdef _jtool jtool


# ============================================
# 包装函数
# 函数在父 shell 中执行，所以 jtool update / install 跑完后可以立刻重新加载
# 本文件，不必手动 source ~/.zshrc 或重开终端。
# （脚本本身是子进程，无法修改父 shell 的环境，只有 shell 函数能做到这一点）
# ============================================
jtool() {
    command jtool "$@"
    local _jtool_ret=$?
    case "$1" in
        update|install|setup|shim)
            [ -f "@SELF@" ] && source "@SELF@"
            hash -r 2>/dev/null
            ;;
        uninstall)
            # 卸载后重新加载 shell 配置，移除 PATH 里的工具路径并清除本函数
            source ~/.zshrc 2>/dev/null
            unfunction jtool 2>/dev/null
            hash -r 2>/dev/null
            ;;
    esac
    return $_jtool_ret
}
