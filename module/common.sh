#!/bin/bash
# jtool 安装模块（被 jtool.sh source 调用）

# 登录 shell 对应的 rc 文件（macOS 默认 zsh）
get_shell_rc() {
    case "${SHELL##*/}" in
        bash) echo "$HOME/.bashrc" ;;
        *)    echo "$HOME/.zshrc" ;;
    esac
}

# 安装目录（不支持的系统返回空并报错，避免拼出 "/bin" 之类的危险路径）
get_install_dir() {
    case "$(uname -s)" in
        Darwin) echo "/Library/devtools/jtool" ;;
        Linux)  echo "/usr/local/devtools/jtool" ;;
        *)
            echo "错误: 不支持的系统: $(uname -s)" >&2
            echo "jtool 仅支持 macOS / Linux，Windows 请使用 install.bat" >&2
            return 1
            ;;
    esac
}

# ============================================
# JDK 路径解析（全平台唯一实现）
#
# 版本号 -> JDK home，分三段，先廉价后昂贵：
#   1. 快路径：按序试确定性候选路径，命中即返回（不 glob、不执行 java）
#   2. 命名匹配：遍历 JAVA_BASE_DIR 下的目录，用**目录名**推出的版本匹配（不执行 java）
#   3. 真实版本：名字对不上时跑 java -version 读真实版本再匹配（兜底）
#
# 前两段都不起子进程，所以 java shim 这类热路径没有探测开销；第三段兜住命名与
# 实际版本不符的情况。之所以要认名字，是因为 JDK 装在哪、叫什么，各家各写各的：
#   jdk-21.jdk / jdk-21             Oracle、Adoptium、SDKMAN
#   java-17-openjdk-amd64           Debian / Ubuntu
#   java-1.8.0-openjdk              RHEL / Fedora
#   temurin-21.jdk / zulu-17.0.9.jdk / amazon-corretto-21.jdk    厂商包
# ============================================

# 候选目录 -> JDK home：优先 macOS bundle 布局，其次平铺布局
_jdk_home_of_dir() {
    local dir="$1"
    if [ -x "$dir/Contents/Home/bin/java" ]; then
        echo "$dir/Contents/Home"
        return 0
    fi
    if [ -x "$dir/bin/java" ]; then
        echo "$dir"
        return 0
    fi
    return 1
}

# 目录名 -> 版本号（只看名字，不启动 java）
# 取名字里第一段以数字开头的 [0-9._] 连续串，厂商前缀与发行版后缀自然被跳过：
#   jdk-21.jdk -> 21              java-17-openjdk-amd64 -> 17
#   temurin-21.jdk -> 21          java-1.8.0-openjdk -> 1.8.0
#   jdk1.8.0_392 -> 1.8.0_392     amazon-corretto-21.jdk -> 21
_jdk_name_version() {
    local name="$1"
    name=${name%.jdk}
    if [[ "$name" =~ ([0-9][0-9._]*) ]]; then
        local v="${BASH_REMATCH[1]}"
        v=${v%.}
        printf '%s\n' "$v"
        return 0
    fi
    return 1
}

# JDK home -> 真实版本号（21.0.1 -> 21.0.1，1.8.0_392 -> 1.8）
_jdk_real_version() {
    local home="$1"
    local raw
    raw=$("$home/bin/java" -version 2>&1 | head -1 | sed -n 's/.*version "\([^"]*\)".*/\1/p')
    [ -n "$raw" ] || return 1
    case "$raw" in
        1.*) echo "${raw%.*}" | cut -d. -f1,2 ;;
        *)   echo "$raw" ;;
    esac
}

# 请求版本 req 是否命中候选版本 cand（cand 来自目录名或 java -version）
_jdk_version_matches() {
    local req="$1" cand="$2"
    [ "$req" = "8" ] && req="1.8"
    [ "$req" = "$cand" ] && return 0
    case "$cand" in
        "$req".*) return 0 ;;   # 21 命中 21.0.1
        "$req"_*) return 0 ;;   # 1.8 命中 1.8_392
    esac
    return 1
}

# 枚举基准目录下的 JDK：每行 `<目录名>\t<JDK home>`。
# 判据是「目录里有 bin/java 或 bundle 的 Contents/Home/bin/java」，所以不挑名字，
# 厂商怎么起名都认得出。
#
# 先解析到真实目录再取名：Ubuntu 的 java-1.17.0-openjdk-amd64 只是指向
# java-17-openjdk-amd64 的软链接，两者是同一个 JDK。不解析就会按软链接的名字
# 显示成「1.17.0」，且按字母序还会顶掉真名。解析后二者同一 key，只出一条、且是真名。
#
# list / scan / 上面三段解析共用，保证「列得出来」的就是「用得起来」的。
_jdk_dirs() {
    local base="$1"
    [ -n "$base" ] || return 1

    local dir top home seen=""
    for dir in "$base"/*; do
        [ -d "$dir" ] || continue
        top=$(cd "$dir" 2>/dev/null && pwd -P) || continue
        home=$(_jdk_home_of_dir "$top") || continue
        case "$seen" in
            *"|$top|"*) continue ;;
        esac
        seen="$seen|$top|"
        # 用 ${top##*/} 而不是 basename：这里是 java shim 的热路径，少一个外部命令
        printf '%s\t%s\n' "${top##*/}" "$home"
    done
}

# 解析版本号 -> JDK home；成功打印 home，失败返回 1
do_resolve_jdk_home() {
    local version="$1"
    local base="${JAVA_BASE_DIR:-}"
    [ -n "$version" ] || return 1
    [ -n "$base" ] || return 1
    [ "$version" = "8" ] && version="1.8"

    # ---- 1. 快路径：确定性候选路径，不 glob、不执行 java ----
    local cand home
    for cand in \
        "$base/jdk-$version.jdk" \
        "$base/jdk-$version" \
        "$base/$version.jdk" \
        "$base/$version"
    do
        [ -d "$cand" ] || continue
        if home=$(_jdk_home_of_dir "$cand"); then
            echo "$home"
            return 0
        fi
    done

    # ---- 2. 命名匹配：目录名说了算，仍不执行 java ----
    local name nver
    while IFS=$'\t' read -r name home; do
        [ -n "$home" ] || continue
        nver=$(_jdk_name_version "$name") || continue
        if _jdk_version_matches "$version" "$nver"; then
            echo "$home"
            return 0
        fi
    done < <(_jdk_dirs "$base")

    # ---- 3. 真实版本：名字与目录对不上时才付出一次 java -version ----
    local real
    while IFS=$'\t' read -r name home; do
        [ -n "$home" ] || continue
        real=$(_jdk_real_version "$home" 2>/dev/null) || continue
        if _jdk_version_matches "$version" "$real"; then
            echo "$home"
            return 0
        fi
    done < <(_jdk_dirs "$base")

    return 1
}

# 枚举已安装的 JDK，每行三个制表符分隔字段：
#   <显示版本>\t<JDK home>\t<java -version 首行>
# list 与 scan 共用，保证「列得出来」和「用得起来」一致
# 参数: [基准目录]，缺省用 JAVA_BASE_DIR
do_list_jdk_dirs() {
    local base="${1:-${JAVA_BASE_DIR:-}}"
    [ -n "$base" ] || return 1

    local name home version first_line
    while IFS=$'\t' read -r name home; do
        [ -n "$home" ] || continue
        # 目录名推不出版本时（如 Homebrew 的 openjdk.jdk 软链接）退回真实版本。
        # 这里本来就要跑一次 java -version 取首行，所以是白捡的。
        version=$(_jdk_name_version "$name") || version=""
        if [ -z "$version" ]; then
            version=$(_jdk_real_version "$home" 2>/dev/null) || version="$name"
        fi
        first_line=$("$home/bin/java" -version 2>&1 | head -1)
        printf '%s\t%s\t%s\n' "$version" "$home" "$first_line"
    done < <(_jdk_dirs "$base")
}

# ============================================
# 扫描 Java 路径
# ============================================
do_scan() {
    local config_file="$1"
    local java_base_dir=""

    echo "扫描 Java 安装路径..."

    # 官方文档登记的 JDK 安装位置（都是「父目录」）。按序探测，第一个真能扫出
    # JDK 的胜出——顺序即优先级，所以把各平台最标准的那个放在最前。
    local candidates=(
        # macOS：Oracle / Adoptium / Azul / Corretto 的 pkg 都装到这里
        "/Library/Java/JavaVirtualMachines"
        # Linux：Debian / Ubuntu / RHEL / Fedora 包管理器的统一落点
        "/usr/lib/jvm"
        # Linux：Oracle 官方 RPM 的默认位置
        "/usr/java"
        # 手动解压安装的常见位置
        "/opt/java"
        "/usr/local/java"
        "/opt"
    )

    for dir in "${candidates[@]}"; do
        [ -d "$dir" ] || continue
        # 不挑目录名：只要它下面有像 JDK 的子目录就算命中（见 _jdk_dirs）
        if [ -n "$(_jdk_dirs "$dir")" ]; then
            java_base_dir="$dir"
            break
        fi
    done

    if [ -z "$java_base_dir" ]; then
        # 非交互环境（安装包脚本、CI、管道）不能询问：`read -p` 在无 TTY 时
        # 要么立刻返回空、要么阻塞，两种情况都不该发生。
        if [ -t 0 ]; then
            echo "未找到 Java 安装目录"
            read -p "请输入 Java 安装路径: " java_base_dir
        else
            echo "未找到 Java 安装目录（当前为非交互环境，无法询问）"
            echo "请手动编辑配置文件的 JAVA_BASE_DIR"
            return 1
        fi
        [ -d "$java_base_dir" ] || { echo "错误: 路径不存在"; return 1; }
    fi

    echo "找到: $java_base_dir"
    echo ""

    echo "已安装的 JDK:"
    local entry shown=0
    while IFS=$'\t' read -r version home first_line; do
        [ -n "$version" ] || continue
        echo "  $version - $first_line"
        shown=1
    done < <(do_list_jdk_dirs "$java_base_dir")
    [ "$shown" = "0" ] && echo "  (未找到)"

    echo ""

    # 保留已有的默认版本与版本记录，避免 scan 把它们抹掉
    local keep_default='# JTOOL_DEFAULT_VERSION="21"'
    local keep_version='# JTOOL_VERSION=""'
    local line
    if [ -f "$config_file" ]; then
        line=$(grep '^JTOOL_DEFAULT_VERSION=' "$config_file" 2>/dev/null | tail -1)
        [ -n "$line" ] && keep_default="$line"
        line=$(grep '^JTOOL_VERSION=' "$config_file" 2>/dev/null | tail -1)
        [ -n "$line" ] && keep_version="$line"
    fi

    mkdir -p "$(dirname "$config_file")"
    cat > "$config_file" << EOF
# jtool configuration

# Java base directory (the parent directory)
JAVA_BASE_DIR="$java_base_dir"

# Default version
$keep_default

# jtool version (maintained by install / update, do not edit)
$keep_version
EOF

    echo "配置文件已写入: $config_file"
    echo ""
    cat "$config_file"
}

# ============================================
# 完整安装
# ============================================
do_update() {
    local tool_name="$1"
    local branch="$2"
    local remote_url="$3"
    local install_dir="$4"
    local config_file="$5"

    # 优先 curl+tar（不依赖 git）；都不可用时回退 git
    if command -v curl >/dev/null 2>&1 && command -v tar >/dev/null 2>&1; then
        do_update_via_curl "$tool_name" "$branch" "$remote_url" "$install_dir" "$config_file"
    elif command -v git >/dev/null 2>&1; then
        do_update_via_git "$tool_name" "$branch" "$remote_url" "$install_dir" "$config_file"
    else
        echo "错误: 需要 curl+tar 或 git 才能更新"
        return 1
    fi
}

do_update_via_curl() {
    local tool_name="$1"
    local branch="$2"
    local remote_url="$3"
    local install_dir="$4"
    local config_file="$5"

    local version_key
    version_key=$(echo "${tool_name}_VERSION" | tr 'a-z' 'A-Z')
    # .git 地址去掉后缀，得到 GitHub 网页地址（用于 raw 和 archive 下载）
    local base_url="${remote_url%.git}"

    command -v curl >/dev/null 2>&1 || { echo "错误: 需要 curl，请先安装"; return 1; }
    command -v tar >/dev/null 2>&1 || { echo "错误: 需要 tar，请先安装"; return 1; }

    # Step 1: 读取远程版本号（不依赖 git）
    #
    # 两条路依次降级：raw 跳转（省流，但 raw.githubusercontent.com 在部分网络
    # 不可达）→ GitHub contents API + Accept: raw（走 api.github.com，通常可达）。
    # 只留一条的话，受限网络里「版本读取」会先失败，而真正要装的 archive
    # （走 codeload）其实是通的 —— 用户会看到莫名其妙的「无法获取版本号」。
    echo "正在检查更新..."
    local remote_version="" owner_repo
    owner_repo="${base_url#https://github.com/}"
    remote_version=$(curl -fsSL --max-time 20 "$base_url/raw/refs/heads/$branch/VERSION" 2>/dev/null | tr -d '[:space:]')
    if [ -z "$remote_version" ]; then
        remote_version=$(curl -fsSL --max-time 20 -H 'Accept: application/vnd.github.raw' \
            "https://api.github.com/repos/$owner_repo/contents/VERSION?ref=$branch" 2>/dev/null \
            | tr -d '[:space:]')
    fi
    if [ -z "$remote_version" ]; then
        echo "错误: 无法获取版本号，请检查网络"
        return 1
    fi

    # Step 2: 读取本地版本号
    local local_version=""
    if [ -f "$config_file" ]; then
        local_version=$(grep "^${version_key}=" "$config_file" 2>/dev/null | tail -1 | cut -d'"' -f2)
    fi

    # Step 3: 版本相同则补齐缺失组件后返回
    if [ "$local_version" = "$remote_version" ]; then
        if do_repair_artifacts "$tool_name" "$install_dir" "$install_dir" "$config_file"; then
            echo "已是最新版本 (v$local_version)，并补齐了缺失组件"
        else
            echo "已是最新版本 (v$local_version)"
        fi
        return 0
    fi

    echo "发现新版本: v${local_version:-未知} → v$remote_version"

    # Step 4: 下载源码包并解压（不依赖 git）
    local tmp
    tmp=$(mktemp -d)
    if ! curl -fsSL "$base_url/archive/refs/heads/$branch.tar.gz" | tar xz -C "$tmp"; then
        rm -rf "$tmp"
        echo "错误: 下载更新失败，请检查网络"
        return 1
    fi
    local src="$tmp/MyProject-$branch"

    # Step 5: 复制文件到安装目录（保留用户配置）
    do_install_entry "$tool_name" "$install_dir" "$src"
    sudo cp "$src/module/common.sh" "$install_dir/module/"

    # 补全模板与 VERSION 同步进安装目录（setup 以安装目录为模板来源）
    sudo mkdir -p "$install_dir/completions"
    local f
    for f in "${tool_name}.zsh" "${tool_name}.bash"; do
        [ -f "$src/completions/$f" ] && sudo cp "$src/completions/$f" "$install_dir/completions/"
    done
    [ -f "$src/VERSION" ] && sudo cp "$src/VERSION" "$install_dir/VERSION"

    # 配置文件仅首次复制
    [ -f "$config_file" ] || sudo cp "$src/config/${tool_name}.conf" "$config_file"

    # Step 6: 记录版本号
    sudo sed -i.bak "/^${version_key}/d" "$config_file" 2>/dev/null
    sudo rm -f "${config_file}.bak" 2>/dev/null
    echo "${version_key}=\"$remote_version\"" | sudo tee -a "$config_file" > /dev/null

    # Step 7: 刷新补全与 shell 配置
    do_create_completions "$install_dir" "$config_file"
    do_setup_shell "$install_dir"

    rm -rf "$tmp"

    echo "更新完成！"
    echo "  版本: v${local_version:-未知} → v$remote_version"
}

do_update_via_git() {
    local tool_name="$1"
    local branch="$2"
    local remote_url="$3"
    local install_dir="$4"
    local config_file="$5"

    local repo_dir="$HOME/.devtools/${tool_name}/repo"
    local version_key
    version_key=$(echo "${tool_name}_VERSION" | tr 'a-z' 'A-Z')

    # Step 1: 确保仓库存在
    local fresh_clone=0
    if [ ! -d "$repo_dir/.git" ]; then
        echo "首次更新，正在克隆仓库..."
        mkdir -p "$(dirname "$repo_dir")"
        git clone --branch "$branch" --single-branch --depth 1 "$remote_url" "$repo_dir" || { echo "克隆失败"; return 1; }
        fresh_clone=1
    fi

    # Step 2: 获取远程版本号
    local remote_version=""
    if [ "$fresh_clone" -eq 1 ]; then
        # 刚克隆完，直接读本地文件
        remote_version=$(cat "$repo_dir/VERSION" 2>/dev/null | tr -d '[:space:]')
    else
        # 已有仓库，fetch 后读远程
        echo "正在检查更新..."
        git -C "$repo_dir" fetch origin "$branch" 2>/dev/null || { echo "获取更新失败，请检查网络"; return 1; }
        remote_version=$(git -C "$repo_dir" show "origin/$branch:VERSION" 2>/dev/null | tr -d '[:space:]')
    fi

    if [ -z "$remote_version" ]; then
        echo "错误: 无法获取版本号"
        return 1
    fi

    # Step 3: 获取本地版本号（取最后一行匹配）
    local local_version=""
    if [ -f "$config_file" ]; then
        local_version=$(grep "^${version_key}=" "$config_file" 2>/dev/null | tail -1 | cut -d'"' -f2)
    fi

    if [ "$local_version" = "$remote_version" ]; then
        # 版本号相同不代表装全了（见 do_repair_artifacts 的说明），先补齐缺失组件
        if do_repair_artifacts "$tool_name" "$install_dir" "$repo_dir" "$config_file"; then
            echo "已是最新版本 (v$local_version)，并补齐了缺失组件"
        else
            echo "已是最新版本 (v$local_version)"
        fi
        return 0
    fi

    echo "发现新版本: v${local_version:-未知} → v$remote_version"

    # Step 4: 拉取最新代码（非首次克隆时需要）
    if [ "$fresh_clone" -eq 0 ]; then
        git -C "$repo_dir" checkout "$branch" 2>/dev/null
        git -C "$repo_dir" pull origin "$branch" || { echo "拉取更新失败"; return 1; }
    fi

    # Step 5: 复制文件到安装目录（保留用户配置）
    do_install_entry "$tool_name" "$install_dir" "$repo_dir"
    sudo cp "$repo_dir/module/common.sh" "$install_dir/module/"

    # 补全模板与 VERSION 也要同步进安装目录：安装包场景下没有仓库，
    # `ptool setup` 以安装目录为模板来源，不同步就会把过期的补全写回去
    sudo mkdir -p "$install_dir/completions"
    local f
    for f in "${tool_name}.zsh" "${tool_name}.bash"; do
        if [ -f "$repo_dir/completions/$f" ]; then
            sudo cp "$repo_dir/completions/$f" "$install_dir/completions/"
        fi
    done
    if [ -f "$repo_dir/VERSION" ]; then
        sudo cp "$repo_dir/VERSION" "$install_dir/VERSION"
    fi

    # 配置文件仅首次复制
    if [ ! -f "$config_file" ]; then
        sudo cp "$repo_dir/config/${tool_name}.conf" "$config_file"
    fi

    # Step 6: 记录版本到配置文件
    sudo sed -i.bak "/^${version_key}/d" "$config_file" 2>/dev/null
    sudo rm -f "${config_file}.bak" 2>/dev/null
    echo "${version_key}=\"$remote_version\"" | sudo tee -a "$config_file" > /dev/null

    # Step 7: 刷新补全脚本与 shell 配置（老版本安装的机器也会补上）
    do_create_completions "$repo_dir" "$config_file"
    do_setup_shell "$install_dir"

    # Step 8: 输出结果
    echo "更新完成！"
    echo "  版本: v${local_version:-未知} → v$remote_version"
}

do_create_shims() {
    local config_file="$1"
    local shims_dir="$HOME/.devtools/jtool/shims"

    mkdir -p "$shims_dir"

    local tools=("java" "javac" "jar" "jshell" "javadoc" "javap")
    local tool
    for tool in "${tools[@]}"; do
        cat > "$shims_dir/$tool" << SHIM
#!/bin/bash
# jtool shim - auto generated
# 瘦转发：路径解析只由 jtool 自己做（do_resolve_jdk_home），这里不重复实现
CONFIG_FILE="$config_file"
ROOT="\$(cd "\$(dirname "\$CONFIG_FILE")/.." && pwd)"

if [ -x "\$ROOT/bin/jtool" ]; then
    JTOOL="\$ROOT/bin/jtool"
elif [ -x "\$ROOT/bin/jtool.sh" ]; then
    JTOOL="\$ROOT/bin/jtool.sh"
else
    echo "jtool: \$ROOT/bin/jtool 不存在" >&2
    exit 1
fi

exec "\$JTOOL" $tool "\$@"
SHIM
        chmod +x "$shims_dir/$tool"
    done

    echo "Shim 已创建: $shims_dir"
}

# ============================================
# 生成补全脚本（zsh / bash）
# 模板里的 @CONFIG_FILE@ 会被替换成实际配置路径
# ============================================
do_create_completions() {
    local script_dir="$1"
    local config_file="$2"
    local comp_dir="$HOME/.devtools/jtool/completions"

    if [ ! -d "$script_dir/completions" ]; then
        echo "跳过补全脚本（未找到 completions 目录）"
        return 0
    fi

    mkdir -p "$comp_dir"
    local f dest
    for f in "$script_dir/completions/jtool.zsh" "$script_dir/completions/jtool.bash"; do
        [ -f "$f" ] || continue
        dest="$comp_dir/$(basename "$f")"
        # @SELF@ 是生成文件自身的路径，包装函数据此重新加载自己
        sed -e "s|@CONFIG_FILE@|$config_file|g" -e "s|@SELF@|$dest|g" "$f" > "$dest"
    done

    echo "补全脚本已创建: $comp_dir"
}

# ============================================
# 从 shell rc 里移除 jtool 配置块
#
# 两种历史格式都要认：
#   · 新格式：被 `# >>> jtool >>>` / `# <<< jtool <<<` 框住的一段（含块内那行
#     空行），整段删除即可 —— 装/卸多少轮都不会在 rc 里留下任何东西。
#   · 老格式：只有散落的单行（`# jtool` + 两行含路径的行），按行删。老格式的
#     块外那行空行无法用行匹配定位，所以老安装升级后仍会残留一个空行；
#     重装一次就换成新格式，之后不再累积。
# 返回 0 表示确实清掉了内容，1 表示这个 rc 里本来就没有 jtool。
# ============================================
_strip_rc_block() {
    local rc_file="$1"
    local install_dir="$2"
    local tool_name="$3"
    local shims_dir="$HOME/.devtools/$tool_name/shims"
    local comp_dir="$HOME/.devtools/$tool_name/completions"

    [ -f "$rc_file" ] || return 1
    grep -q -e "^# >>> $tool_name >>>$" -e "^# $tool_name$" \
            -e "$install_dir" -e "$shims_dir" -e "$comp_dir" "$rc_file" 2>/dev/null || return 1

    sed -i.bak \
        -e "/^# >>> $tool_name >>>$/,/^# <<< $tool_name <<<$/d" \
        -e "/^# $tool_name$/d" \
        -e "\|$install_dir|d" \
        -e "\|$shims_dir|d" \
        -e "\|$comp_dir|d" \
        "$rc_file"
    rm -f "${rc_file}.bak"
    return 0
}

# ============================================
# 写入 shell 配置（PATH + 补全）
# 幂等：每次先移除旧配置块再追加，便于升级时刷新
# ============================================
do_setup_shell() {
    local install_dir="$1"
    local bin_dir="$install_dir/bin"
    local shims_dir="$HOME/.devtools/jtool/shims"
    local comp_dir="$HOME/.devtools/jtool/completions"

    local shell_rc
    shell_rc=$(get_shell_rc)
    [ -f "$shell_rc" ] || : > "$shell_rc"

    # 移除旧的 jtool 配置块，避免重复或残留
    _strip_rc_block "$shell_rc" "$install_dir" "jtool"

    # 只写固定的 4 行，并用成对标记框住：卸载时整段删除，块内那行空行也一并
    # 消失。老版本把空行写在块外，卸载后每装一轮都会在 rc 里多留一个空行
    # （实测 22→23→24 行累积）——用标记框住是唯一能定位到那行空行的办法。
    # 包装函数不放在这里——它是多行的，按行模式清理会漏掉函数体导致重复累积；
    # 放进被 source 的补全文件里，每次整体重新生成即可。
    local comp_file
    if [ "${shell_rc##*/}" = ".zshrc" ]; then
        comp_file="$comp_dir/jtool.zsh"
    else
        comp_file="$comp_dir/jtool.bash"
    fi

    {
        echo "# >>> jtool >>>"
        echo ""
        echo "export PATH=\"$shims_dir:$bin_dir:\$PATH\""
        echo "[ -f \"$comp_file\" ] && source \"$comp_file\""
        echo "# <<< jtool <<<"
    } >> "$shell_rc"

    echo "已写入: $shell_rc"
    export PATH="$shims_dir:$bin_dir:$PATH"
}

# ============================================
# 用户级安装（供安装包的 postinstall 以登录用户身份调用）
# 只处理 ~/.devtools 与 shell 配置，不碰系统目录，全程非交互。
# 调用方必须保证配置文件已存在——bin/jtool.sh 的 load_config 在分发子命令
# 之前就会检查它，配置缺失时 `jtool setup` 根本走不到这里。
# ============================================
do_setup_user() {
    local install_dir="$1"
    local config_file="$2"

    if [ ! -f "$config_file" ]; then
        echo "错误: 配置文件不存在 ($config_file)"
        echo "安装程序应当在此步之前创建它"
        return 1
    fi

    do_create_shims "$config_file"
    # 补全模板从安装目录取（安装包已随包分发 completions/）
    do_create_completions "$install_dir" "$config_file"
    do_setup_shell "$install_dir"
}

# ============================================
# 安装可执行入口
# 真实脚本放 lib/，bin/ 里只放无后缀的软链接。bin/ 在 PATH 上，
# 若把 jtool.sh 也留在 bin/，命令名补全就会同时列出 jtool 和 jtool.sh。
# $0 始终是 bin/jtool，脚本据此推导目录，所以真实文件在 lib/ 不影响运行。
# ============================================
do_install_entry() {
    local tool_name="$1"
    local install_dir="$2"
    local source_dir="$3"
    local bin_dir="$install_dir/bin"
    local lib_dir="$install_dir/lib"

    sudo mkdir -p "$bin_dir" "$lib_dir"
    sudo cp "$source_dir/bin/${tool_name}.sh" "$lib_dir/${tool_name}.sh"
    sudo chmod +x "$lib_dir/${tool_name}.sh"
    sudo ln -sf "../lib/${tool_name}.sh" "$bin_dir/${tool_name}"
    # 清理旧布局残留，否则它仍在 PATH 上、仍会出现在补全里
    sudo rm -f "$bin_dir/${tool_name}.sh"
}

# ============================================
# 补齐缺失的安装组件（软链接 / 补全 / shell 配置）
# 用于「版本号已是最新但组件不全」的情况：从旧版本 update 上来的机器，
# 第一次 update 由旧代码执行，不会创建这些组件，之后版本号相同就再也补不上。
# 返回 0 表示补了东西，1 表示本来就齐全。
# ============================================
do_repair_artifacts() {
    local tool_name="$1"
    local install_dir="$2"
    local source_dir="$3"
    local config_file="$4"
    local comp_dir="$HOME/.devtools/${tool_name}/completions"
    local repaired=0

    # lib 缺失说明安装损坏，无法 repair
    if [ ! -f "$install_dir/lib/${tool_name}.sh" ]; then
        echo "  警告: 缺少 $install_dir/lib/${tool_name}.sh，请重新安装"
        return 1
    fi
    # 入口缺失，或仍是旧布局（bin/ 下还留着 .sh）
    # 无 git 方案下没有源仓库目录，脚本已在 lib/，只需重建软链接
    if [ ! -e "$install_dir/bin/${tool_name}" ] || [ -e "$install_dir/bin/${tool_name}.sh" ]; then
        sudo mkdir -p "$install_dir/bin"
        sudo ln -sf "../lib/${tool_name}.sh" "$install_dir/bin/${tool_name}"
        sudo rm -f "$install_dir/bin/${tool_name}.sh"
        echo "  已重建命令入口: ${tool_name}"
        repaired=1
    fi

    if [ ! -f "$comp_dir/${tool_name}.zsh" ]; then
        do_create_completions "$source_dir" "$config_file" >/dev/null
        echo "  已补建补全脚本: $comp_dir"
        repaired=1
    fi

    local shell_rc
    shell_rc=$(get_shell_rc)
    if ! grep -q -e "^# >>> ${tool_name} >>>$" -e "^# ${tool_name}$" "$shell_rc" 2>/dev/null; then
        do_setup_shell "$install_dir" >/dev/null
        echo "  已补写 shell 配置: $shell_rc"
        repaired=1
    fi

    [ "$repaired" -eq 1 ] && return 0
    return 1
}

do_install() {
    local script_dir="$1"
    local install_dir
    install_dir=$(get_install_dir) || return 1
    local bin_dir="$install_dir/bin"
    local lib_dir="$install_dir/lib"
    local config_dir="$install_dir/config"
    local module_dir="$install_dir/module"
    local config_file="$config_dir/jtool.conf"

    echo "========================================"
    echo "  jtool 安装程序"
    echo "========================================"
    echo ""

    echo "[1/5] 复制文件..."
    sudo mkdir -p "$bin_dir" "$config_dir" "$module_dir" "$lib_dir"
    case "$(uname -s)" in
        Darwin|Linux)
            do_install_entry "jtool" "$install_dir" "$script_dir"
            ;;
        *)
            sudo cp "$script_dir/bin/jtool.bat" "$bin_dir/"
            ;;
    esac
    # 配置文件仅首次创建，重装时保留用户已有配置
    if [ ! -f "$config_file" ]; then
        sudo cp "$script_dir/config/jtool.conf" "$config_dir/"
    fi
    # 安装目录属 root，配置文件必须可写，否则 do_scan / jtool use 无法写入
    sudo chmod 666 "$config_file"
    sudo cp "$script_dir/module/common.sh" "$module_dir/"
    # 安装目录也留一份 VERSION：update 会把它同步进来，安装却不放，会出现
    # 「全新安装的目录里没有 VERSION、update 之后才有」的不一致。
    if [ -f "$script_dir/VERSION" ]; then
        sudo cp "$script_dir/VERSION" "$install_dir/VERSION"
    fi
    echo "完成"
    echo ""

    echo "[2/5] 设置权限..."
    case "$(uname -s)" in
        Darwin|Linux) sudo chmod +x "$lib_dir/jtool.sh" ;;
    esac
    echo "完成"
    echo ""

    echo "[3/5] 扫描 Java..."
    # 非交互环境下找不到 JDK 时 do_scan 返回 1。必须在这里中止：否则会带着
    # 空/错误的配置跑完 [4/5][5/5] 并打印「安装完成！」——和 install.sh 里修过的
    # 「失败仍报成功」是同一类问题（Linux 实测复现过）。
    if ! do_scan "$config_file"; then
        echo "错误: 扫描 Java 失败，安装中止（配置未写入）" >&2
        return 1
    fi
    # 写入版本号（幂等：先清掉旧记录，避免重复追加）
    if [ -f "$script_dir/VERSION" ]; then
        local ver
        ver=$(cat "$script_dir/VERSION" | tr -d '[:space:]')
        sudo sed -i.bak '/^JTOOL_VERSION/d' "$config_file" 2>/dev/null
        sudo rm -f "${config_file}.bak"
        echo "JTOOL_VERSION=\"$ver\"" | sudo tee -a "$config_file" > /dev/null
    fi
    echo ""

    echo "[4/5] 创建 shim 与补全..."
    do_create_shims "$config_file"
    do_create_completions "$script_dir" "$config_file"
    echo ""

    echo "[5/5] 配置 PATH..."
    do_setup_shell "$install_dir"
    echo ""

    echo "========================================"
    echo "  安装完成！"
    echo "========================================"
    echo ""
    echo "安装目录: $install_dir"
    echo "配置文件: $config_file"
    echo "重开终端或执行 source ~/.zshrc 后补全生效（仅首次安装需要）"
}

# ============================================
# 卸载
# ============================================
do_uninstall() {
    local assume_yes=0
    case "${1:-}" in
        -y|--yes) assume_yes=1 ;;
    esac

    local install_dir
    install_dir=$(get_install_dir) || return 1

    echo "========================================"
    echo "  jtool 卸载程序"
    echo "========================================"
    echo ""

    if [ "$assume_yes" -ne 1 ]; then
        read -p "确定要卸载吗？(y/n): " confirm
        [ "$confirm" != "y" ] && [ "$confirm" != "Y" ] && { echo "已取消"; return 0; }
    fi

    echo ""

    if [ -d "$install_dir" ]; then
        sudo rm -rf "$install_dir"
        echo "已删除: $install_dir"
    else
        echo "安装目录不存在"
    fi

    # 清理 shims
    local shims_dir="$HOME/.devtools/jtool/shims"
    if [ -d "$shims_dir" ]; then
        rm -rf "$shims_dir"
        echo "已删除: $shims_dir"
    fi

    # 清理补全脚本
    local comp_dir="$HOME/.devtools/jtool/completions"
    if [ -d "$comp_dir" ]; then
        rm -rf "$comp_dir"
        echo "已删除: $comp_dir"
    fi

    # 清理 .repo 目录
    local repo_dir="$HOME/.devtools/jtool/repo"
    if [ -d "$repo_dir" ]; then
        rm -rf "$repo_dir"
        echo "已删除: $repo_dir"
    fi

    # 清理 shell 配置中的 jtool 配置块。
    # 这里遍历 3 个 rc 文件（do_setup_shell 只写 get_shell_rc() 那一个）是刻意的：
    # 覆盖换过 shell、或被更老版本写到其他 rc 的情况；删的也只是 jtool 自己的块，
    # 不碰用户的其他配置。不要为了「两边对称」缩掉这份清单。
    local rc_file
    for rc_file in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile"; do
        _strip_rc_block "$rc_file" "$install_dir" "jtool" && echo "已清理: $rc_file"
    done

    echo ""

    # 项目根目录 install_dir 已在上方 `sudo rm -rf` 删除。剩下的空目录分两层收掉：
    #   · 用户级 ~/.devtools/jtool、~/.devtools —— 普通 rmdir，只在目录为空时成功，
    #     所以同目录下还有别的东西时不会误删。
    #   · 系统级 $(dirname "$install_dir")（/usr/local/devtools 或 /Library/devtools）
    #     —— 需要 sudo；同样只在为空时删除。
    # 也就是：装了几个工具就只删本项目的目录；只有本项目是最后一个时，才连同
    # devtools 目录本身一起删掉。
    local d
    for d in "$HOME/.devtools/jtool" "$HOME/.devtools"; do
        [ -d "$d" ] || continue
        rmdir "$d" 2>/dev/null && echo "已删除空目录: $d"
    done
    if [ -d "$(dirname "$install_dir")" ]; then
        sudo rmdir "$(dirname "$install_dir")" 2>/dev/null \
            && echo "已删除空目录: $(dirname "$install_dir")"
    fi

    echo ""
    echo "卸载完成！"
}

# ============================================
# 查看配置
# ============================================
do_config() {
    local config_file="$1"
    echo "配置文件: $config_file"
    echo ""
    [ -f "$config_file" ] && cat "$config_file" || echo "(不存在，请运行: jtool scan)"
}
