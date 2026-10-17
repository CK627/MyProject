#!/usr/bin/env bash
# jtool 冒烟测试（macOS / Linux）
#
# 用法: bash tests/smoke.sh
#
# 覆盖：
#   1) shell 语法门（bash -n / zsh -n）
#   2) 含空格路径的 config 解析 —— jtool.sh 的 JDK 解析（回归：tr -d 删过空格）
#   3) 生成的 shim（瘦转发到 jtool）能按默认版本转发到 java
#   4) jtool run 把脚本后的参数透传给 java
#   5) install-from-source.sh 的工具名推导（目录名是 jtool-<版本> 时也要找对配置）
#   6) install.sh 的 tag 解析：git 路径与 GitHub API 回退路径
#   7) jtool use 写回、do_install 不得吞掉 do_scan 失败
#
# 全部 hermetic：sudo 用桩替换、安装目录与家目录都指向临时目录，不写系统目录、
# 不碰真家目录，所以本地和 CI 跑法完全一致。

set -uo pipefail   # 不用 -e：用例失败要汇总而不是中途退出

FAIL=0
pass() { printf '  ok   - %s\n' "$*"; }
fail() { printf '  FAIL - %s\n' "$*"; FAIL=1; }

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# sudo 桩：把提权调用降级成直接执行（只对临时目录生效）
mkdir -p "$TMP/stub"
printf '#!/bin/sh\nexec "$@"\n' > "$TMP/stub/sudo"
chmod +x "$TMP/stub/sudo"

# ------------------------------------------------------------ 1) 语法门
echo "== 语法检查 =="
SHELL_FILES=(
    "$REPO/bin/jtool.sh" "$REPO/module/common.sh"
    "$REPO/installer/install.sh" "$REPO/installer/install-from-source.sh"
    "$REPO/installer/linux-build.sh" "$REPO/installer/macos/build.sh"
    "$REPO/installer/macos/postinstall.in" "$REPO/installer/macos/uninstall.in"
    "$REPO/installer/windows/build-from-mac.sh" "$REPO/completions/jtool.bash"
)
for f in "${SHELL_FILES[@]}"; do
    if bash -n "$f" 2>/dev/null; then
        pass "bash -n ${f#"$REPO"/}"
    else
        fail "bash -n ${f#"$REPO"/}"
        bash -n "$f"
    fi
done
if command -v zsh >/dev/null 2>&1; then
    for f in "$REPO/installer/install.sh" "$REPO/completions/jtool.zsh"; do
        if zsh -n "$f" 2>/dev/null; then
            pass "zsh -n ${f#"$REPO"/}"
        else
            fail "zsh -n ${f#"$REPO"/}"
            zsh -n "$f"
        fi
    done
else
    echo "  skip - 未安装 zsh，跳过 zsh -n"
fi

# ------------------------------- 2) 含空格路径：JDK 解析（jtool.sh）
echo "== JDK 解析（含空格路径） =="
TOOL_DIR="$TMP/tool"
mkdir -p "$TOOL_DIR" "$TMP/java base/jdk-21/bin" "$TMP/home"
cp -R "$REPO/bin" "$REPO/module" "$REPO/config" "$REPO/completions" "$REPO/installer" "$TOOL_DIR/"
cat > "$TMP/java base/jdk-21/bin/java" <<'EOF'
#!/bin/sh
if [ "$1" = "-version" ]; then
    echo 'openjdk version "21.0.1"' >&2
    exit 0
fi
echo "fake-java $*"
EOF
chmod +x "$TMP/java base/jdk-21/bin/java"
printf '#!/bin/sh\nexit 0\n' > "$TMP/java base/jdk-21/bin/javac"
chmod +x "$TMP/java base/jdk-21/bin/javac"
printf 'JAVA_BASE_DIR="%s/java base"\nJTOOL_DEFAULT_VERSION="21"\n' "$TMP" \
    > "$TOOL_DIR/config/jtool.conf"

out="$("$TOOL_DIR/bin/jtool.sh" list 2>&1)"; rc=$?
if [ "$rc" -eq 0 ]; then pass "jtool list 退出码 0"; else fail "jtool list 退出码 $rc"; fi
home_out="$("$TOOL_DIR/bin/jtool.sh" home 21 2>&1)"
if [ "$home_out" = "$TMP/java base/jdk-21" ]; then
    pass "jtool home 展开出含空格的 JDK home"
else
    fail "jtool home 输出异常: $home_out"
fi

# ------------------------------- 3) 生成的 shim（瘦转发到 jtool）
echo "== 生成的 shim（含空格路径） =="
FAKE_HOME="$TMP/home"
# shim 现在写在安装目录里（属 root），所以这里既要一个临时安装目录，也要 sudo 桩：
# 真跑 sudo 会在无人值守的 CI 里挂住等密码。
SHIM_INSTALL="$TMP/shim-install"
mkdir -p "$SHIM_INSTALL"
if HOME="$FAKE_HOME" bash -c '
        sudo() { "$@"; }
        source "$1/module/common.sh"
        do_create_shims "$2" "$3"
    ' _ "$TOOL_DIR" "$SHIM_INSTALL" "$TOOL_DIR/config/jtool.conf" >/dev/null 2>&1; then
    pass "do_create_shims 生成成功"
else
    fail "do_create_shims 失败"
fi
SHIM="$SHIM_INSTALL/shims/java"
if [ -x "$SHIM" ]; then
    shim_out="$("$SHIM" -version 2>&1)"; shim_rc=$?
    case "$shim_out" in
        *"21.0.1"*) [ "$shim_rc" -eq 0 ] && pass "shim 能按默认版本转发到 java" \
            || fail "shim 转发退出码 $shim_rc" ;;
        *) fail "shim 转发失败 (rc=$shim_rc out=$shim_out)" ;;
    esac
else
    fail "未生成 shim: $SHIM"
fi

# --------------------------------------- 4) jtool run 的参数透传
echo "== jtool run 参数透传 =="
printf 'public class Hello { public static void main(String[] a){ System.out.println("hi"); } }\n' \
    > "$TMP/Hello.java"
run_out="$(cd "$TMP" && "$TOOL_DIR/bin/jtool.sh" run 21 Hello.java arg1 arg2 2>&1)"; run_rc=$?
case "$run_out" in
    *"arg1 arg2"*) [ "$run_rc" -eq 0 ] && pass "脚本后的参数被透传给 java" \
        || fail "run 退出码 $run_rc" ;;
    *) fail "run 未透传参数: $run_out" ;;
esac

# --------------------------------------- 5) install-from-source.sh 的工具名推导
echo "== install-from-source.sh 工具名推导 =="
cp -R "$TOOL_DIR" "$TMP/jtool-9.9.9"
ifs_out="$(bash "$TMP/jtool-9.9.9/installer/install-from-source.sh" config 2>&1)"; ifs_rc=$?
if [ "$ifs_rc" -eq 0 ] && printf '%s' "$ifs_out" | grep -q 'JAVA_BASE_DIR'; then
    pass "从 jtool-9.9.9 目录运行也能读到 config/jtool.conf"
else
    fail "工具名推导失败: $ifs_out"
fi

# --------------------------------------- 6) install.sh 的 tag 解析
echo "== tag 解析 =="
SAMPLE="$(printf 'aaaaaaa\trefs/tags/jtool-v2.3.4\nbbbbbbb\trefs/tags/jtool-v2.3.11\nccccccc\trefs/tags/jtool-v2.3.11^{}\nddddddd\trefs/tags/jtool-v2.3.2\n')"
got="$(printf '%s\n' "$SAMPLE" | grep -vF '^{}' \
       | sed 's|.*refs/tags/jtool-v||' \
       | sort -t. -k1,1n -k2,2n -k3,3n | tail -1)"
if [ "$got" = "2.3.11" ]; then
    pass "git 路径：剥壳行被过滤，且按数值取最高（2.3.11 > 2.3.4）"
else
    fail "git 路径 tag 解析异常: $got"
fi
API_SAMPLE='[{"tag_name":"ptool-v2.2.9"},{"tag_name":"jtool-v2.3.4"},{"tag_name":"jtool-v2.3.11"}]'
got="$(printf '%s\n' "$API_SAMPLE" \
       | grep -oE '"tag_name"[[:space:]]*:[[:space:]]*"jtool-v[0-9.]+"' \
       | sed -E 's/.*"jtool-v([0-9.]+)"/\1/' \
       | sort -t. -k1,1n -k2,2n -k3,3n | tail -1)"
if [ "$got" = "2.3.11" ]; then
    pass "GitHub API 回退路径：只挑 jtool 的 tag 且取最高"
else
    fail "API 路径 tag 解析异常: $got"
fi

# --------------------------------------- 7) jtool use 写回
echo "== jtool use 写回 =="
if PATH="$TMP/stub:$PATH" "$TOOL_DIR/bin/jtool.sh" use 21 >/dev/null 2>&1; then
    pass "jtool use 成功"
else
    fail "jtool use 失败"
fi
if grep -q '^JTOOL_DEFAULT_VERSION="21"$' "$TOOL_DIR/config/jtool.conf"; then
    pass "use 写回的格式正确"
else
    fail "use 写回格式异常"
fi

# --------------------------------------- 8) do_install 不得吞掉 do_scan 失败
echo "== do_install 的失败传播 =="
out="$( cd "$TOOL_DIR" && PATH="$TMP/stub:$PATH" HOME="$TMP/home" bash -c '
    sudo() { "$@"; }
    source module/common.sh
    get_install_dir() { echo "$PWD/fake-install"; }
    do_scan() { return 1; }
    do_install "$PWD"
' 2>&1 )"; rc=$?
if [ "$rc" -ne 0 ]; then
    pass "do_install 在 do_scan 失败时返回非 0"
else
    fail "do_install 吞掉了 do_scan 失败（rc=0）"
fi
case "$out" in
    *安装完成*) fail "失败路径仍打印了「安装完成！」" ;;
    *) pass "失败路径未打印成功横幅" ;;
esac

# --------------------------------------- 9) 卸载不残留空行 / 空目录
echo "== 卸载：rc 不残留、空目录收干净 =="
mkdir -p "$TMP/rc-test/home"
printf 'export EDITOR=vim\n' > "$TMP/rc-test/home/.bashrc"
RC0="$(cat "$TMP/rc-test/home/.bashrc")"
# 安装过程中的状态必须在 do_uninstall 之前采下来——卸载会把安装目录整个删掉，
# 事后再断言「shim 在安装目录里」永远为假。
STATE="$(HOME="$TMP/rc-test/home" PATH="$TMP/stub:$PATH" bash -c '
    sudo() { "$@"; }
    source "$1/module/common.sh"
    get_install_dir() { echo "$HOME/fake-install"; }
    do_install "$2" >/dev/null 2>&1
    [ -f "$HOME/fake-install/shims/java" ]           && echo SHIM_IN_INSTALL
    [ -f "$HOME/fake-install/completions/jtool.zsh" ] && echo COMP_IN_INSTALL
    [ -e "$HOME/.devtools" ]                         && echo DEVTOOLS_CREATED
    do_uninstall -y >/dev/null 2>&1
' _ "$TOOL_DIR" "$TOOL_DIR" 2>&1)"
RC1="$(cat "$TMP/rc-test/home/.bashrc")"
if [ "$RC1" = "$RC0" ]; then
    pass "卸载后 .bashrc 与安装前逐字节一致（无残留空行）"
else
    fail "卸载后 .bashrc 有残留，末尾为: $(printf '%s' "$RC1" | tail -2)"
fi
case "$STATE" in
    *DEVTOOLS_CREATED*) fail "~/.devtools 被创建了（2.2.18 起所有产物都在安装目录里）" ;;
    *)                  pass "全程未创建 ~/.devtools" ;;
esac
# shim / 补全必须落在安装目录里，否则 PATH 上那两条指向的就是空目录
case "$STATE" in
    *SHIM_IN_INSTALL*) pass "shim 生成在安装目录内" ;;
    *)                 fail "安装目录内没有 shims/java" ;;
esac
case "$STATE" in
    *COMP_IN_INSTALL*) pass "补全生成在安装目录内" ;;
    *)                 fail "安装目录内没有 completions/jtool.zsh" ;;
esac
if [ -d "$TMP/rc-test/home/fake-install" ]; then
    fail "卸载后安装目录未删除"
else
    pass "卸载后安装目录已删除（shim/补全随之清除）"
fi

# ------------------------------- README 骨架章节（devtool 系列一致）
# 系列以 ptool 的 README 为基准，13 个顶级章节是这套文档的招牌。只要求"至少包含"
# ——各项目可以有额外章节（自己特有的功能说明）。缺任何一个都算漂了。
# ------------------------------- shell 文本体检（$VAR 后不得紧跟非 ASCII）
# 变量名后面**直接**跟一个非 ASCII 字符（例如全角括号）时，shell 会把紧跟的
# 多字节字符一起看进变量名，行为随 locale 而变。
# ⚠️ 连注释里也别原样写出那个模式——体检不区分注释与代码（区分要写半个 shell
#    解析器，还会有漏判），所以举例时把变量名与括号**隔开**写。
# ⚠️ 用 Python 而不是 grep：BSD grep 不支持 \xNN 转义，早先那种
#    `grep -E '[^\x00-\x7f]'` 会以 rc=2 报 invalid character range 退出，
#    而 `if grep ...; then` 把命令出错当成"没匹配"，检查会**永远报 ok**。
echo "== shell 文本体检（\$VAR 后不得紧跟非 ASCII）=="
if _cv="$(python3 -I tests/check_shell_vars.py 2>&1)"; then
    pass "\$VAR 后没有紧跟非 ASCII"
else
    fail "shell 变量名体检（${_cv}）"
fi

# ------------------------------- 文本编码契约（声明 = 实际字节）
# 覆盖 .bat/.ps1/.iss/.sh/.py：每个文件首部声明自己的编码，检查器逐条核对实际
# 字节。各运行环境**没有共通的编码 pragma**（cmd 认代码页、PowerShell 只认 BOM、
# irm|iex 连 BOM 都不能有），所以声明是契约、机制按类型分开——详见
# tests/check_text_encoding.py 的文档字符串。
# 放在这里而不是只在 CI：本地跑一遍就能发现（CI 要等推上去才知道）。
echo "== 文本编码契约 =="
if _enc="$(python3 -I tests/check_text_encoding.py 2>&1)"; then
    pass "$_enc"
else
    fail "文本编码契约（${_enc}）"
fi

echo "== README 骨架章节 =="
if _rd="$(python3 -I tests/check_readme.py README.md 2>&1)"; then
    pass "$_rd"
else
    fail "README 骨架章节（${_rd}）"
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "全部通过"
else
    echo "存在失败用例"
fi
exit "$FAIL"
