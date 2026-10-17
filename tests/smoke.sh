#!/usr/bin/env bash
# encoding: utf-8
# startupctl 冒烟测试（CI 的唯一门禁；本地也直接跑）
#
# 九段：语法门 → 单元冒烟 → shell 语法 → 启动器 → HELP 契约 →
#       安装/卸载与布局契约 → 引导模式与真更新（file:// 镜像）→ 域契约 → 安全不变量
# 后两段在 tests/test_smoke.py 里，这里只负责编排。
#
# ⚠️ 纪律：**整个套件绝不碰真机。** 安装测试用隔离的 HOME 且强制 STARTUPCTL_USER=1
#    （CI 没有 tty、也没有免密 sudo）；夹具测试靠 STARTUPCTL_ROOTS 重定向所有扫描根。
#    真机上的启动项一次都不会被读到，更不会被改到。
#
# 注意 set 里**没有 -e**：失败要聚合着报出来，而不是第一个错就退出——
# 一次跑完看全所有问题，比修一个跑一次快得多。
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PASS=0
FAIL=0
FAILED_NAMES=()

ok()   { PASS=$((PASS+1)); printf '[ok  ] %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); FAILED_NAMES+=("$1"); printf '[FAIL] %s\n' "$1"; }
stage() { printf '\n=== %s ===\n' "$1"; }

# 断言"输出里含某串"
has() {  # has <输出> <子串> <说明>
    case "$1" in *"$2"*) ok "$3" ;; *) bad "$3（输出里没有: $2）" ;; esac
}

# grep -c 的坑：没命中时它**既打印 0 又返回 1**，所以 `$(grep -c ... || echo 0)`
# 会得到 "0\n0" 两行，字符串比较必然失败（还会让人以为是功能坏了）。
# 统一走这个 helper 取计数。
count_of() {  # count_of <文件> <模式>
    grep -c "$2" "$1" 2>/dev/null | head -1 | tr -d ' \n'
    # 命令替换里若 grep 失败，上面已由 head 兜住空输出的情况，返回 0
}
# 断言两串相等
eq() {   # eq <得到> <期望> <说明>
    if [ "$1" = "$2" ]; then ok "$3"; else bad "$3（得到 '$1'，期望 '$2'）"; fi
}

PY=python3
command -v "$PY" >/dev/null 2>&1 || { echo "找不到 python3" >&2; exit 1; }

# ================================================================ 1 语法门
stage "1/9 语法门（含 Python 3.8 兼容）"
if "$PY" -m compileall -q startupctl tests >/tmp/startupctl-compile.log 2>&1; then
    ok "compileall 通过"
else
    bad "compileall 失败"; cat /tmp/startupctl-compile.log
fi

# 3.9+ 语法在 3.8 上会被 compileall 抓到，但本机可能是 3.13——显式扫一遍源码里
# 那些"只在 3.9+ 合法"的写法，让本机跑也能提前发现。
if grep -rnE '\blist\[|\bdict\[|\btuple\[|\bset\[|^\s*match .*:\s*$|\bfunctools\.cache\b' \
        startupctl --include='*.py' 2>/dev/null | grep -v '^\s*#' >/tmp/startupctl-py39.log; then
    bad "发现 3.9+ 专有语法（会让 3.8 用户装不上）"
    cat /tmp/startupctl-py39.log
else
    ok "没有 3.9+ 专有语法"
fi

# ================================================================ 2 单元冒烟
stage "2/9 单元冒烟（域契约 + 安全不变量）"
if "$PY" -I tests/test_smoke.py; then
    ok "tests/test_smoke.py 全部通过"
else
    bad "tests/test_smoke.py 有失败"
fi

# ================================================================ 3 shell 语法
stage "3/9 shell 语法"
for f in installer/*.sh installer/macos/build.sh installer/windows/build-from-mac.sh bin/startupctl.sh completions/startupctl.bash; do
    if bash -n "$f" 2>/dev/null; then ok "bash -n $f"; else bad "bash -n $f"; fi
done
if command -v zsh >/dev/null 2>&1; then
    if zsh -n completions/startupctl.zsh 2>/dev/null; then
        ok "zsh -n completions/startupctl.zsh"
    else
        bad "zsh -n completions/startupctl.zsh"
    fi
fi

# $VAR 后面直接跟中文：shell 会把变量名连着中文字节一起解析，导致变量取空。
# 这是本项目踩过的坑，机制上只能靠机器守。
#
# ⚠️ 这里**刻意不用 grep**：BSD grep（macOS 自带）不支持 `\xNN` 转义，早先那条
#    `grep -E '[^\x00-\x7f]'` 会以 `grep: invalid character range` **rc=2 退出**，
#    而 `if grep ...; then` 把命令出错当成了"没匹配"——于是这条检查在本项目里
#    从来没生效过（一直是假阴性，直到把同一套用法搬到 CtfSweep 上才暴露）。
#    改用 Python 检查器：精确、可移植，而且**它自己出错会以非零退出**，能被看见。
if _cjk_out="$("$PY" tests/check_shell_vars.py 2>&1)"; then
    ok "\$VAR 后没有紧跟中文"
else
    _cjk_rc=$?
    if [ "$_cjk_rc" -eq 2 ]; then
        bad "shell 变量名体检**自身出错**（rc=2），结果不可信"
    else
        bad "发现 \$VAR 后紧跟非 ASCII 字符（变量会解析失败）"
    fi
    printf '%s\n' "$_cjk_out"
fi

# ================================================================ 4 启动器
stage "4/9 启动器"
out="$(./bin/startupctl.sh --version 2>&1)"
has "$out" "startupctl" "仓库启动器能跑（bin/startupctl.sh --version）"

# ================================================================ 5 HELP 契约
stage "5/9 HELP 契约"
help_out="$("$PY" -I -c "
import sys; sys.path.insert(0,'.')
from startupctl import help as H
print('LINES=%d' % H.help_lines())
print('PROBLEMS=%d' % len(H.align_report()))
print('WIDEST=%d' % max(H.dw(l) for l in H.HELP.splitlines()))
")"
lines="$(printf '%s\n' "$help_out" | sed -n 's/^LINES=//p')"
probs="$(printf '%s\n' "$help_out" | sed -n 's/^PROBLEMS=//p')"
widest="$(printf '%s\n' "$help_out" | sed -n 's/^WIDEST=//p')"
if [ "${lines:-99}" -le 50 ]; then ok "HELP 行数 $lines <= 50"; else bad "HELP 行数 $lines 超过 50"; fi
eq "${probs:-x}" "0" "HELP 各节描述列对齐一致"
if [ "${widest:-999}" -le 100 ]; then ok "HELP 最宽行 $widest <= 100 列"; else bad "HELP 最宽行 $widest 超过 100"; fi

# ================================================================ 6 安装/卸载
stage "6/9 安装 / 卸载与布局契约"
TESTHOME="$(mktemp -d)"
cleanup_install() { rm -rf "$TESTHOME"; }
trap cleanup_install EXIT

# 默认层级（不装，只问）
got="$(HOME="$TESTHOME" ./installer/install-from-source.sh print-install-dir 2>/dev/null)"
case "$got" in
    */devtools/startupctl) ok "print-install-dir 默认层级: $got" ;;
    *) bad "print-install-dir 默认层级异常: $got" ;;
esac

# 用户级
got="$(HOME="$TESTHOME" STARTUPCTL_USER=1 ./installer/install-from-source.sh print-install-dir 2>/dev/null)"
eq "$got" "$TESTHOME/.devtools/startupctl" "STARTUPCTL_USER=1 → 用户级安装根"

# 自定义 devroot（优先级最高）
got="$(HOME="$TESTHOME" STARTUPCTL_DEVROOT=/tmp/scdevroot ./installer/install-from-source.sh print-install-dir 2>/dev/null)"
eq "$got" "/tmp/scdevroot/startupctl" "STARTUPCTL_DEVROOT 优先级最高"

# 真装一次（用户级，不需要密码）
inst="$TESTHOME/.devtools/startupctl"
if HOME="$TESTHOME" STARTUPCTL_USER=1 bash installer/install-from-source.sh install >/tmp/startupctl-install.log 2>&1; then
    ok "用户级安装成功"
else
    bad "用户级安装失败"; cat /tmp/startupctl-install.log
fi

if [ -x "$inst/bin/startupctl" ] || [ -L "$inst/bin/startupctl" ]; then
    ok "命令入口存在: $inst/bin/startupctl"
else
    bad "命令入口缺失: $inst/bin/startupctl"
fi

n="$(ls -A "$inst/bin" 2>/dev/null | wc -l | tr -d ' ')"
eq "$n" "1" "bin/ 里只有 1 个条目（否则 .sh/.bat 会一起进 PATH 补全）"

if [ -L "$inst/bin/startupctl" ]; then
    tgt="$(readlink "$inst/bin/startupctl")"
    eq "$tgt" "../lib/startupctl.sh" "bin/startupctl 是指向 ../lib/startupctl.sh 的软链"
else
    bad "bin/startupctl 不是软链"
fi

[ -e "$inst/bin/startupctl.sh" ] && bad "bin/ 里残留 startupctl.sh（会进补全）" || ok "bin/ 无 .sh 残留"
[ -e "$inst/bin/startupctl.bat" ] && bad "bin/ 里残留 startupctl.bat（会进补全）" || ok "bin/ 无 .bat 残留"
[ -d "$inst/lib/startupctl/backends" ] && ok "lib/startupctl/backends 已随包安装" || bad "lib/startupctl/backends 缺失"

rc="$TESTHOME/.zshrc"; [ -f "$rc" ] || rc="$TESTHOME/.bashrc"
cnt="$(count_of "$rc" '^# >>> startupctl >>>$')"
cnt="${cnt:-0}"
eq "$cnt" "1" "rc 里恰好一个 startupctl 配置块"

# 重复安装必须幂等
HOME="$TESTHOME" STARTUPCTL_USER=1 bash installer/install-from-source.sh install >/tmp/startupctl-reinstall.log 2>&1
has "$(cat /tmp/startupctl-reinstall.log)" "接线一致" "重复安装报「接线一致」（不谎称要重开终端）"

# 装上以后，命令真的能跑
v="$(PATH="$inst/bin:$PATH" HOME="$TESTHOME" STARTUPCTL_USER=1 "$inst/bin/startupctl" --version 2>&1)"
has "$v" "startupctl" "安装后的命令可执行"

# 卸载：功能项删掉，**白名单与备份保留**
mkdir -p "$inst/backups/20260101T000000Z-remove"
echo '{"version":1,"entries":[{"match":"id","value":"abc"}]}' > "$inst/whitelist.json"
echo '{"op":"remove"}' > "$inst/backups/20260101T000000Z-remove/manifest.json"
HOME="$TESTHOME" STARTUPCTL_USER=1 bash installer/uninstall.sh >/tmp/startupctl-uninstall.log 2>&1
[ -e "$inst/lib" ] && bad "卸载后 lib/ 仍在" || ok "卸载删除了功能项 lib/"
[ -f "$inst/whitelist.json" ] && ok "卸载**保留**了白名单" || bad "卸载把白名单删了（这是安全产物）"
[ -f "$inst/backups/20260101T000000Z-remove/manifest.json" ] && ok "卸载**保留**了备份（唯一后悔药）" || bad "卸载把备份删了"
c="$(count_of "$rc" '^# >>> startupctl >>>$')"
c="${c:-0}"
eq "$c" "0" "卸载摘除了 rc 配置块"

# ================================================================ 7 引导 + 更新
stage "7/9 引导模式与真更新（file:// 镜像，不联网）"
STAGE="$(mktemp -d)"
# 镜像布局（与 installer/publish-mirror.sh 同一约定）：
#   <base>/VERSION                     纯文本版本号
#   <base>/startupctl-src.tar.gz       源码快照，顶层目录必须叫 MyProject-<分支>
#   <base>/<version>/<asset>           平台资产（本测试不需要）
#
# ⚠️ 快照**内部**的 VERSION 必须与镜像的 VERSION 一致：selfmgr 有"半发布防护"，
#    两者不符就拒绝落盘（防止镜像正在发布中被人装到半成品）。
_build_snapshot() {  # _build_snapshot <版本> <镜像目录>
    local ver="$1" st="$2"
    local snap="$st/MyProject-StartupItemManagement"
    rm -rf "$snap"
    mkdir -p "$snap"
    cp -R "$ROOT/startupctl" "$snap/startupctl"
    cp -R "$ROOT/bin" "$snap/bin"
    cp -R "$ROOT/config" "$snap/config"
    cp -R "$ROOT/completions" "$snap/completions"
    cp -R "$ROOT/installer" "$snap/installer"
    printf '%s\n' "$ver" > "$snap/VERSION"
    tar czf "$st/startupctl-src.tar.gz" -C "$st" "MyProject-StartupItemManagement"
    printf '%s\n' "$ver" > "$st/VERSION"
}

LOCAL_VER="$(tr -d '[:space:]' < "$ROOT/VERSION")"
# 阶段 A：镜像版本 == 本地版本 → 应报"已是最新"
_build_snapshot "$LOCAL_VER" "$STAGE"

H7="$(mktemp -d)"
if HOME="$H7" STARTUPCTL_USER=1 ./installer/install-from-source.sh install >/tmp/sc-i7.log 2>&1; then
    ok "（7）用户级安装成功，准备测更新"
else
    bad "（7）安装失败"; cat /tmp/sc-i7.log
fi

same="$(HOME="$H7" STARTUPCTL_USER=1 STARTUPCTL_MIRROR="file://$STAGE" \
        "$H7/.devtools/startupctl/bin/startupctl" update 2>&1)"
has "$same" "已是最新" "同版本 update 报「已是最新」"

# 阶段 B：把镜像推到 9.9.9，再真更新一次
_build_snapshot "9.9.9" "$STAGE"

# --check：只比对不落盘
chk="$(HOME="$H7" STARTUPCTL_USER=1 STARTUPCTL_MIRROR="file://$STAGE" \
       "$H7/.devtools/startupctl/bin/startupctl" update --check 2>&1)"
has "$chk" "仅比对" "update --check 明确说明未落盘"
eq "$(cat "$H7/.devtools/startupctl/VERSION" 2>/dev/null)" "$(cat "$ROOT/VERSION")" \
   "update --check 没有改动安装目录的 VERSION"

# 写一条白名单 + 一个备份，验证更新不动数据
mkdir -p "$H7/.devtools/startupctl/backups/20260101T000000Z-remove"
echo '{"version":1,"entries":[]}' > "$H7/.devtools/startupctl/whitelist.json"
echo 'sentinel' > "$H7/.devtools/startupctl/backups/20260101T000000Z-remove/manifest.json"

if HOME="$H7" STARTUPCTL_USER=1 STARTUPCTL_MIRROR="file://$STAGE" \
   "$H7/.devtools/startupctl/bin/startupctl" update >/tmp/sc-update.log 2>&1; then
    has "$(cat /tmp/sc-update.log)" "更新完成" "真更新（file:// 镜像）成功"
else
    bad "真更新失败"; cat /tmp/sc-update.log
fi
eq "$(cat "$H7/.devtools/startupctl/VERSION" 2>/dev/null)" "9.9.9" "更新后 VERSION 变为 9.9.9"
[ -f "$H7/.devtools/startupctl/whitelist.json" ] && ok "更新**保留**了白名单" || bad "更新把白名单删了"
[ -f "$H7/.devtools/startupctl/backups/20260101T000000Z-remove/manifest.json" ] \
    && ok "更新**保留**了备份" || bad "更新把备份删了"

# 离线失败要优雅
off="$(HOME="$H7" STARTUPCTL_USER=1 STARTUPCTL_MIRROR="file:///nonexistent" STARTUPCTL_GITHUB=none \
       "$H7/.devtools/startupctl/bin/startupctl" update --check 2>&1)"
rc_off=$?
if [ "$rc_off" -ne 0 ]; then ok "镜像不可达时 update 非零退出"; else bad "镜像不可达时 update 却成功"; fi
has "$off" "无法获取" "离线失败给出明确原因"

rm -rf "$H7" "$STAGE"

# ================================================================ 8/9 由 test_smoke.py 覆盖
stage "8/9 域契约 —— 见 tests/test_smoke.py「域契约」段"
stage "9/9 安全不变量 —— 见 tests/test_smoke.py「安全不变量」段"

# ================================================================ 10 描述文件
stage "9.5/10 文本编码契约（声明 = 实际字节）"
# 覆盖 .bat/.ps1/.iss/.sh/.py。各运行环境没有共通的编码 pragma：cmd 认控制台
# 代码页、磁盘上的 .ps1 只认 BOM、irm|iex 分发的 .ps1 连 BOM 都不能有（只能纯
# ASCII + Base64）。声明行是契约，机制按类型分开——详见 tests/check_text_encoding.py。
if _enc_out="$("$PY" tests/check_text_encoding.py 2>&1)"; then
    ok "$_enc_out"
else
    bad "文本编码契约（${_enc_out}）"
fi

stage "10/10 README 骨架章节（devtool 系列一致）"
# 系列以 ptool 的 README 为基准，13 个顶级章节是这套文档的招牌。只要求"至少包含"
# ——各项目可以有额外章节（本项目有「进程守护」）。缺任何一个都算漂了。
if _rd_out="$("$PY" tests/check_readme.py README.md 2>&1)"; then
    ok "$_rd_out"
else
    bad "README 骨架章节（${_rd_out}）"
fi

# ================================================================ 汇总
printf '\n'
printf '=%s\n' "==========================================================="
if [ "$FAIL" -gt 0 ]; then
    printf '失败 %d 项 / 通过 %d 项\n' "$FAIL" "$PASS"
    for n in "${FAILED_NAMES[@]}"; do printf '  [FAIL] %s\n' "$n"; done
    exit 1
fi
printf '冒烟全部通过（%d 项检查）\n' "$PASS"
