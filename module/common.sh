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
# 扫描 Java 路径
# ============================================
do_scan() {
    local config_file="$1"
    local java_base_dir=""

    echo "扫描 Java 安装路径..."

    local candidates=(
        "/Library/Java/JavaVirtualMachines"
        "/usr/lib/jvm"
        "/opt/java"
    )

    for dir in "${candidates[@]}"; do
        if [ -d "$dir" ] && ls "$dir"/jdk-*.jdk &>/dev/null 2>&1; then
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
    for dir in "$java_base_dir"/jdk-*.jdk; do
        [ -d "$dir" ] || continue
        local version
        version=$(basename "$dir" | sed 's/jdk-//;s/\.jdk//')
        if [ -f "$dir/Contents/Home/bin/java" ]; then
            local ver
            ver=$("$dir/Contents/Home/bin/java" -version 2>&1 | head -1)
            echo "  $version - $ver"
        fi
    done

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
# jtool 配置文件

# Java 安装路径（父目录）
JAVA_BASE_DIR="$java_base_dir"

# 默认版本
$keep_default

# jtool 版本（由 install / update 维护，请勿手动修改）
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

    # Step 1: 读取远程版本号（raw 文件，不依赖 git）
    echo "正在检查更新..."
    local remote_version=""
    remote_version=$(curl -fsSL "$base_url/raw/refs/heads/$branch/VERSION" 2>/dev/null | tr -d '[:space:]')
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
    for tool in "${tools[@]}"; do
        cat > "$shims_dir/$tool" << SHIM
#!/bin/bash
# jtool shim - auto generated
CONFIG_FILE="$config_file"
JAVA_BASE_DIR=""
JTOOL_DEFAULT_VERSION=""
if [ -f "\$CONFIG_FILE" ]; then
    while IFS='=' read -r key value; do
        [[ "\$key" =~ ^#.*$ || -z "\$key" ]] && continue
        key=\$(echo "\$key" | tr -d ' ')
        value=\$(echo "\$value" | tr -d " '\"")
        case "\$key" in
            JAVA_BASE_DIR) JAVA_BASE_DIR="\$value" ;;
            JTOOL_DEFAULT_VERSION) JTOOL_DEFAULT_VERSION="\$value" ;;
        esac
    done < "\$CONFIG_FILE"
fi
if [ -z "\$JTOOL_DEFAULT_VERSION" ]; then
    echo "jtool: 未设置默认版本，请运行 jtool use <版本号>" >&2
    exit 1
fi
VER="\$JTOOL_DEFAULT_VERSION"
[ "\$VER" = "8" ] && VER="1.8"
if [ "\$(uname -s)" = "Darwin" ]; then
    JDK_HOME="\$JAVA_BASE_DIR/jdk-\$VER.jdk/Contents/Home"
else
    JDK_HOME="\$JAVA_BASE_DIR/jdk-\$VER"
fi
if [ ! -d "\$JDK_HOME" ]; then
    echo "jtool: JDK \$JTOOL_DEFAULT_VERSION 不存在" >&2
    exit 1
fi
exec "\$JDK_HOME/bin/$tool" "\$@"
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
    sed -i.bak "/^# jtool$/d; \|$install_dir|d; \|$shims_dir|d; \|$comp_dir|d" "$shell_rc"
    rm -f "${shell_rc}.bak"

    # 只写固定的 3 行。包装函数不放在这里——它是多行的，按行模式清理会漏掉
    # 函数体导致重复累积；放进被 source 的补全文件里，每次整体重新生成即可。
    local comp_file
    if [ "${shell_rc##*/}" = ".zshrc" ]; then
        comp_file="$comp_dir/jtool.zsh"
    else
        comp_file="$comp_dir/jtool.bash"
    fi

    {
        echo ""
        echo "# jtool"
        echo "export PATH=\"$shims_dir:$bin_dir:\$PATH\""
        echo "[ -f \"$comp_file\" ] && source \"$comp_file\""
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
    if ! grep -q "^# ${tool_name}$" "$shell_rc" 2>/dev/null; then
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
    echo "完成"
    echo ""

    echo "[2/5] 设置权限..."
    case "$(uname -s)" in
        Darwin|Linux) sudo chmod +x "$lib_dir/jtool.sh" ;;
    esac
    echo "完成"
    echo ""

    echo "[3/5] 扫描 Java..."
    do_scan "$config_file"
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

    # 清理 shell 配置中的 PATH 行、补全 source 行与 # jtool 标记
    for rc_file in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile"; do
        [ -f "$rc_file" ] || continue
        grep -q -e "$install_dir" -e "$shims_dir" -e "$comp_dir" -e "^# jtool$" "$rc_file" 2>/dev/null || continue
        sed -i.bak "/^# jtool$/d; \|$install_dir|d; \|$shims_dir|d; \|$comp_dir|d" "$rc_file"
        rm -f "${rc_file}.bak"
        echo "已清理: $rc_file"
    done

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
