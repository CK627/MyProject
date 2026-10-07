# jtool bash 补全
# 由 jtool 安装脚本生成，请勿手动修改
# 配置文件: @CONFIG_FILE@
# 兼容 bash 3.2（macOS 自带版本）

_jtool_versions() {
    local config_file="@CONFIG_FILE@"
    local base_dir=""
    [ -f "$config_file" ] && base_dir=$(grep '^JAVA_BASE_DIR=' "$config_file" 2>/dev/null | tail -1 | cut -d'"' -f2)
    [ -n "$base_dir" ] || return 0

    local dir name ver target base_real
    base_real=$(cd "$base_dir" 2>/dev/null && pwd -P)
    # 不挑目录名，只认里面确实是 JDK 的（macOS bundle 或平铺布局）
    for dir in "$base_dir"/*; do
        [ -x "$dir/Contents/Home/bin/java" ] || [ -x "$dir/bin/java" ] || continue
        if [ -L "$dir" ]; then
            # 指向同一基准目录下真目录的软链接（Ubuntu 的 java-1.17.0-openjdk-amd64）
            # 跳过：真目录自己会列出来。不跳就会多出一个 1.17.0——TAB 里看得见，
            # jtool use 1.17.0 却匹配不到，因为解析那边两个名字是同一个 JDK。
            target=$(cd "$dir" 2>/dev/null && pwd -P)
            [ -n "$target" ] && [ "${target%/*}" = "$base_real" ] && continue
        fi
        name=$(basename "$dir")
        name=${name%.jdk}
        # 版本号取目录名里第一段以数字开头的连续串，厂商前缀 / 发行版后缀自动跳过。
        # 与 module/common.sh 的 _jdk_name_version 同一套规则。
        if [[ "$name" =~ ([0-9][0-9._]*) ]]; then
            ver="${BASH_REMATCH[1]%.}"
            [ -n "$ver" ] && echo "$ver"
        fi
    done
}

_jtool_complete() {
    local cur cmd
    local subcmds="list use current home info tools run scan config install setup uninstall update shim help"
    local tools="java javac jar jshell javadoc javap"

    cur="${COMP_WORDS[COMP_CWORD]}"
    cmd="${COMP_WORDS[1]}"

    if [ "$COMP_CWORD" -eq 1 ]; then
        COMPREPLY=( $(compgen -W "$subcmds $tools" -- "$cur") )
        return 0
    fi

    case "$cmd" in
        use|home|info|tools)
            COMPREPLY=( $(compgen -W "$(_jtool_versions | sort -uV)" -- "$cur") )
            ;;
        run)
            # jtool run <版本> <文件.java>
            if [ "$COMP_CWORD" -eq 2 ]; then
                COMPREPLY=( $(compgen -W "$(_jtool_versions | sort -uV)" -- "$cur") )
            else
                COMPREPLY=( $(compgen -f -X '!*.java' -- "$cur") )
            fi
            ;;
        java|javac|jar|jshell|javadoc|javap)
            if [ "$COMP_CWORD" -eq 2 ]; then
                COMPREPLY=( $(compgen -W "$(_jtool_versions | sort -uV)" -- "$cur") )
            else
                COMPREPLY=( $(compgen -f -- "$cur") )
            fi
            ;;
        *)
            COMPREPLY=( $(compgen -f -- "$cur") )
            ;;
    esac
    return 0
}

complete -F _jtool_complete jtool


# ============================================
# 包装函数
# 函数在父 shell 中执行，所以 jtool update / install 跑完后可以立刻重新加载
# 本文件，不必手动 source ~/.bashrc 或重开终端。
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
            source ~/.bashrc 2>/dev/null
            unset -f jtool 2>/dev/null
            hash -r 2>/dev/null
            ;;
    esac
    return $_jtool_ret
}
