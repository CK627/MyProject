#!/usr/bin/env bash
# ptool 冒烟测试（macOS / Linux）
#
# 用法: bash tests/smoke.sh
#
# 覆盖：
#   1) shell 语法门（bash -n / zsh -n）
#   2) 含空格路径的 config 解析 —— ptool.sh 路径与生成的 shim 路径（回归：tr -d 删过空格）
#   3) ptool run 把脚本后的参数透传给解释器
#   4) install-from-source.sh 的工具名推导（目录名是 ptool-<版本> 时也要找对配置）
#   5) install.sh 的 tag 解析：git 路径与 GitHub API 回退路径（剥壳行要过滤、按数值取最高）
#   6) ptool use 写回、do_install 不得吞掉 do_scan 失败
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
    "$REPO/bin/ptool.sh" "$REPO/module/common.sh"
    "$REPO/installer/install.sh" "$REPO/installer/install-from-source.sh"
    "$REPO/installer/linux-build.sh" "$REPO/installer/macos/build.sh"
    "$REPO/installer/macos/postinstall.in" "$REPO/installer/macos/uninstall.in"
    "$REPO/installer/windows/build-from-mac.sh" "$REPO/completions/ptool.bash"
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
    # install.sh 要能被 zsh source；补全本身就是 zsh 脚本
    for f in "$REPO/installer/install.sh" "$REPO/completions/ptool.zsh"; do
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

# ---------------------------------------- 2) 含空格路径：config 解析（ptool.sh）
echo "== config 解析（含空格路径） =="
TOOL_DIR="$TMP/tool"
mkdir -p "$TOOL_DIR" "$TMP/py base" "$TMP/home"
cp -R "$REPO/bin" "$REPO/module" "$REPO/config" "$REPO/completions" "$REPO/installer" "$TOOL_DIR/"
cat > "$TMP/py base/python3.11" <<'EOF'
#!/bin/sh
if [ "$1" = "--version" ]; then
    echo "Python 3.11.9"
else
    echo "fake-python $*"
fi
EOF
chmod +x "$TMP/py base/python3.11"
printf 'PYTHON_BASE_DIR="%s/py base"\nPTOOL_DEFAULT_VERSION="3.11"\n' "$TMP" \
    > "$TOOL_DIR/config/ptool.conf"

out="$("$TOOL_DIR/bin/ptool.sh" list 2>&1)"; rc=$?
if [ "$rc" -eq 0 ]; then pass "ptool list 退出码 0"; else fail "ptool list 退出码 $rc"; fi
case "$out" in
    *"$TMP/py base/python3.11"*) pass "路径里的空格被完整保留" ;;
    *) fail "路径被破坏（tr -d 回归？）: $out" ;;
esac
home_out="$("$TOOL_DIR/bin/ptool.sh" home 3.11 2>&1)"
if [ "$home_out" = "$TMP/py base" ]; then
    pass "ptool home 展开出含空格的目录"
else
    fail "ptool home 输出异常: $home_out"
fi

# ------------------------------- 3) 含空格路径：生成的 shim（common.sh 路径）
echo "== 生成的 shim（含空格路径） =="
FAKE_HOME="$TMP/home"
if HOME="$FAKE_HOME" bash -c 'source "$1/module/common.sh"; do_create_shims "$2"' \
        _ "$TOOL_DIR" "$TOOL_DIR/config/ptool.conf" >/dev/null 2>&1; then
    pass "do_create_shims 生成成功"
else
    fail "do_create_shims 失败"
fi
SHIM="$FAKE_HOME/.devtools/ptool/shims/python"
if [ -x "$SHIM" ]; then
    shim_out="$("$SHIM" --version 2>&1)"; shim_rc=$?
    if [ "$shim_rc" -eq 0 ] && [ "$shim_out" = "Python 3.11.9" ]; then
        pass "shim 能按含空格路径转发到解释器"
    else
        fail "shim 转发失败 (rc=$shim_rc out=$shim_out)"
    fi
else
    fail "未生成 shim: $SHIM"
fi

# --------------------------------------- 4) ptool run 的参数透传
echo "== ptool run 参数透传 =="
printf 'print(1)\n' > "$TMP/script.py"
run_out="$("$TOOL_DIR/bin/ptool.sh" run 3.11 "$TMP/script.py" --flag value 2>&1)"; run_rc=$?
case "$run_out" in
    *"--flag value"*) [ "$run_rc" -eq 0 ] && pass "脚本后的参数被透传给解释器" \
        || fail "run 退出码 $run_rc" ;;
    *) fail "run 未透传参数: $run_out" ;;
esac

# --------------------------------------- 5) install-from-source.sh 的工具名推导
# 发行包解出来的目录名是 ptool-<版本>，不能拿 basename 当工具名
# （否则会去找 config/ptool-9.9.9.conf 这种不存在的配置）
echo "== install-from-source.sh 工具名推导 =="
cp -R "$TOOL_DIR" "$TMP/ptool-9.9.9"
ifs_out="$(bash "$TMP/ptool-9.9.9/installer/install-from-source.sh" config 2>&1)"; ifs_rc=$?
if [ "$ifs_rc" -eq 0 ] && printf '%s' "$ifs_out" | grep -q 'PYTHON_BASE_DIR'; then
    pass "从 ptool-9.9.9 目录运行也能读到 config/ptool.conf"
else
    fail "工具名推导失败: $ifs_out"
fi

# --------------------------------------- 6) install.sh 的 tag 解析
# 与 installer/install.sh 的 resolve_latest 保持同步：样例里带一个 annotated
# tag 的 ^{} 行——去掉过滤就会选中 ptool-v2.2.15^{}，下载 URL 直接 404。
echo "== tag 解析 =="
SAMPLE="$(printf 'aaaaaaa\trefs/tags/ptool-v2.2.9\nbbbbbbb\trefs/tags/ptool-v2.2.15\nccccccc\trefs/tags/ptool-v2.2.15^{}\nddddddd\trefs/tags/ptool-v2.2.10\n')"
got="$(printf '%s\n' "$SAMPLE" | grep -vF '^{}' \
       | sed 's|.*refs/tags/ptool-v||' \
       | sort -t. -k1,1n -k2,2n -k3,3n | tail -1)"
if [ "$got" = "2.2.15" ]; then
    pass "git 路径：剥壳行被过滤，且按数值取最高（2.2.15 > 2.2.9）"
else
    fail "git 路径 tag 解析异常: $got"
fi
API_SAMPLE='[{"tag_name":"jtool-v1.0.0"},{"tag_name":"ptool-v2.2.9"},{"tag_name":"ptool-v2.2.15"}]'
got="$(printf '%s\n' "$API_SAMPLE" \
       | grep -oE '"tag_name"[[:space:]]*:[[:space:]]*"ptool-v[0-9.]+"' \
       | sed -E 's/.*"ptool-v([0-9.]+)"/\1/' \
       | sort -t. -k1,1n -k2,2n -k3,3n | tail -1)"
if [ "$got" = "2.2.15" ]; then
    pass "GitHub API 回退路径：只挑 ptool 的 tag 且取最高"
else
    fail "API 路径 tag 解析异常: $got"
fi

# --------------------------------------- 7) ptool use 写回（sudo 桩，不碰系统）
echo "== ptool use 写回 =="
if PATH="$TMP/stub:$PATH" "$TOOL_DIR/bin/ptool.sh" use 3.11 >/dev/null 2>&1; then
    pass "ptool use 成功"
else
    fail "ptool use 失败"
fi
if grep -q '^PTOOL_DEFAULT_VERSION="3.11"$' "$TOOL_DIR/config/ptool.conf"; then
    pass "use 写回的格式正确"
else
    fail "use 写回格式异常"
fi

# --------------------------------------- 8) do_install 不得吞掉 do_scan 失败
# 回归：do_scan 返回 1 时曾继续跑完 [4/5][5/5] 并打印「安装完成！」
echo "== do_install 的失败传播 =="
out="$( cd "$TOOL_DIR" && PATH="$TMP/stub:$PATH" HOME="$TMP/home" bash -c '
    sudo() { "$@"; }                                  # 函数桩：双保险
    source module/common.sh
    get_install_dir() { echo "$PWD/fake-install"; }   # 不写系统目录
    do_scan() { return 1; }                           # 模拟非交互下找不到 Python
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

echo
if [ "$FAIL" -eq 0 ]; then
    echo "全部通过"
else
    echo "存在失败用例"
fi
exit "$FAIL"
