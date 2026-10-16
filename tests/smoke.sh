#!/usr/bin/env bash
# ctfsweep 冒烟（macOS / Linux）：语法门 + 单元冒烟 + 启动器 + 安装/布局契约 + 引导模式 + 自管理子命令
# （5/7 守布局契约：PATH 上只能有一个无后缀软链；7/7 用 file:// 镜像跑真更新与离线失败路径，
#   全程无需网络与 sudo，同时守住「部署/卸载都不碰扫描缓存」与「clear 只清数据、不碰功能项」）
#
# ⚠️ 安装层级一律显式写 CTFSWEEP_USER=1（用户级）：默认层级是系统级 /Library/devtools
#    （与 jtool / ptool 一致），CI 里既没有 tty 也没有免密 sudo，跑默认路径会卡在密码提示上。
#    默认层级的正确性由 5/7 末尾的 print-install-dir 断言守着——只问不装。
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"

# 版本号从 VERSION 推导，**不硬编码**。
# ⚠️ 原来这里写死了 "1.10.10 → 1.10.11"，于是每次升版本都必须记得回来改测试——
#    漏改的表现是「update --check 输出异常」，看着像功能坏了，其实只是断言过期。
#    cur = 当前版本，next = 下一个 patch（抬高假镜像用，验"发现新版本"那条路）。
_CUR="$(tr -d '[:space:]' < VERSION)"
_NEXT="$(printf '%s' "$_CUR" | awk -F. '{printf "%s.%s.%d", $1, $2, $3+1}')"

echo "== 1/7 语法门（compileall）=="
"$PY" -m compileall -q ctfsweep tests

echo "== 2/7 python 冒烟 =="
"$PY" tests/test_smoke.py

echo "== 3/7 shell 语法 =="
bash -n bin/ctfsweep.sh
bash -n installer/install.sh
bash -n installer/install-from-source.sh
bash -n installer/deploy.sh
bash -n installer/shell-setup.sh
bash -n installer/uninstall.sh
bash -n installer/publish-mirror.sh
bash -n installer/windows/build-from-mac.sh
bash -n completions/ctfsweep.bash
if command -v zsh >/dev/null 2>&1; then
    zsh -n completions/ctfsweep.zsh
fi

echo "== 4/7 启动器 =="
./bin/ctfsweep.sh --version

echo "== 5/7 安装/卸载循环 + 布局契约（隔离 HOME）=="
# 契约（本布局的正题）：PATH 上只能出现一个无后缀的 ctfsweep。
# 仓库 bin/ 是素材目录（ctfsweep.sh + ctfsweep.bat），整体进 PATH 的话，zsh 的命令名
# 补全走 $commands 哈希，而那个哈希不检查可执行位——Windows 启动器照样进候选。
_tmp_home="$(mktemp -d)"
_log="$_tmp_home/install.log"
_inst="$_tmp_home/.devtools/ctfsweep"

# 层级解析（只问不装）：默认系统级、CTFSWEEP_USER=1 用户级、CTFSWEEP_DEVROOT 最高优先
_root_default="$(bash installer/install-from-source.sh print-install-dir)"
case "$(uname -s)" in
    Darwin) _root_want="/Library/devtools/ctfsweep" ;;
    *)      _root_want="/usr/local/devtools/ctfsweep" ;;
esac
[ "$_root_default" = "$_root_want" ] \
    || _fail5 "默认安装根是 ${_root_default}（应为系统级 ${_root_want}）"
_root_user="$(CTFSWEEP_USER=1 HOME="$_tmp_home" bash installer/install-from-source.sh print-install-dir)"
[ "$_root_user" = "$_tmp_home/.devtools/ctfsweep" ] \
    || _fail5 "CTFSWEEP_USER=1 的安装根是 ${_root_user}（应为用户级）"
_root_custom="$(CTFSWEEP_DEVROOT=/tmp/csdevroot bash installer/install-from-source.sh print-install-dir)"
[ "$_root_custom" = "/tmp/csdevroot/ctfsweep" ] \
    || _fail5 "CTFSWEEP_DEVROOT 未生效：${_root_custom}"

_fail5() {
    echo "安装/卸载循环失败: $1"
    echo "--- 日志 ---"
    cat "$_log" 2>/dev/null || true
    rm -rf "$_tmp_home"
    exit 1
}

HOME="$_tmp_home" CTFSWEEP_USER=1 bash installer/install.sh > "$_log" 2>&1 || _fail5 "install.sh 退出码非 0"
# 重复安装：既验证幂等，也顺带验证「不堆叠 shell 块」
HOME="$_tmp_home" CTFSWEEP_USER=1 bash installer/install.sh > "$_log" 2>&1 || _fail5 "重复安装失败"
# 第二次安装时接线一字未动 → 必须如实报「未变」，不能再让人重开一次终端
grep -q 'shell 配置未变' "$_log" \
    || _fail5 "重复安装后应报「shell 配置未变」（接线未动却提示重开终端）"

_n_bin="$(ls -A "$_inst/bin" | wc -l | tr -d ' ')"
[ "$_n_bin" = "1" ] || _fail5 "安装后 bin/ 有 $_n_bin 个条目（应为 1）"
[ -L "$_inst/bin/ctfsweep" ] || _fail5 "bin/ctfsweep 不是软链"
[ "$(readlink "$_inst/bin/ctfsweep")" = "../lib/ctfsweep.sh" ] \
    || _fail5 "软链指向 $(readlink "$_inst/bin/ctfsweep")（应为 ../lib/ctfsweep.sh）"
[ -f "$_inst/lib/ctfsweep.sh" ] || _fail5 "lib/ctfsweep.sh 不存在"
[ ! -e "$_inst/bin/ctfsweep.sh" ] || _fail5 "旧布局残留 bin/ctfsweep.sh 仍在 PATH 上"
[ ! -e "$_inst/bin/ctfsweep.bat" ] || _fail5 "Windows 启动器 ctfsweep.bat 被带进了 PATH"
[ -f "$_inst/lib/models/model.ctfj" ] || _fail5 "models 未部署（--judge 会静默退化成未训练）"

if [ -f "$_tmp_home/.zshrc" ]; then
    _n_blk="$(grep -c '^# >>> ctfsweep >>>$' "$_tmp_home/.zshrc" || true)"
    [ "$_n_blk" = "1" ] || _fail5 "重复安装后 shell 块有 $_n_blk 个（应为 1）"
    # 命令名只有 ctfsweep 一个：块里不许再写回 ctf 短别名（1.10.5 及更早写过，
    # 短名会与别的 CTF 工具撞名）。7.6 另有一头反向断言——老形态残留必须被摘掉。
    if grep -q "alias ctf" "$_tmp_home/.zshrc"; then
        _fail5 "shell 接线又写回了 ctf 短别名（新增内容里不该有它）"
    fi
fi

HOME="$_tmp_home" "$_inst/bin/ctfsweep" --version >/dev/null || _fail5 "启动器 --version 失败"
HOME="$_tmp_home" bash installer/uninstall.sh > "$_log" 2>&1 || _fail5 "uninstall.sh 退出码非 0"
[ ! -d "$_inst" ] || _fail5 "清理后安装目录仍存在"
if [ -f "$_tmp_home/.zshrc" ] && grep -q 'ctfsweep' "$_tmp_home/.zshrc" 2>/dev/null; then
    _fail5 "卸载后 shell 配置里仍残留 ctfsweep 接线"
fi
echo "安装/卸载循环 OK（bin/ 唯一无后缀软链 · models 就位 · 重复安装不堆叠）"
rm -rf "$_tmp_home"

echo "== 6/7 引导模式（离线模拟：file:// 镜像 + 独立脚本副本）=="
# 造一份源码快照当「镜像服务器目录」：用工作区当前文件（含未提交改动），
# 但只放安装所需的内容，顶层目录名与 GitHub archive 一致。
# 快照在 6/7、7/7 间共用（7/7 的 update 也从它下载）。
_stage="$(mktemp -d)"
_stage_home="$(mktemp -d)"
_boot_root="$(mktemp -d)"
_boot="$_boot_root/boot"          # 只放 install.sh 的隔离目录 → 强制触发远程自举路径
mkdir -p "$_stage/MyProject-CtfSweep" "$_boot"
cp -R ctfsweep bin config completions installer models VERSION "$_stage/MyProject-CtfSweep/"
(cd "$_stage" && tar -czf ctfsweep-src.tar.gz MyProject-CtfSweep)
# 镜像根下也要有 VERSION：update 的第一步就是读它比对版本
#（installer/publish-mirror.sh 发布时同样要发这一份）
cp VERSION "$_stage/VERSION"
cp installer/install.sh "$_boot/install.sh"

_empty="$(mktemp -d)"             # 7.5 的「镜像空目录」
_fail() {
    echo "$1"
    rm -rf "$_stage" "$_stage_home" "$_boot_root" "$_empty"
    exit 1
}

_boot_log="$_stage_home/boot.log"
if (cd "$_boot" && HOME="$_stage_home" CTFSWEEP_USER=1 CTFSWEEP_MIRROR="file://$_stage" bash ./install.sh) > "$_boot_log" 2>&1 \
   && HOME="$_stage_home" "$_stage_home/.devtools/ctfsweep/bin/ctfsweep" --version >/dev/null; then
    echo "引导模式 OK"
else
    echo "引导模式失败，日志："
    cat "$_boot_log" 2>/dev/null || true
    _fail "（见上方日志）"
fi

echo "== 7/7 自管理子命令（config / 真更新 / 离线失败 / uninstall，全程 file:// 镜像）=="
_csw="$_stage_home/.devtools/ctfsweep/bin/ctfsweep"
_inst="$_stage_home/.devtools/ctfsweep"

# 7.1 config：显示 devtools 安装布局
HOME="$_stage_home" "$_csw" config > "$_stage_home/.cfg.out" 2>&1 \
    || _fail "config 子命令失败（退出码非 0）"
case "$(cat "$_stage_home/.cfg.out")" in
    *"运行模式: devtools 安装"*"配置文件:"*) echo "config 子命令 OK" ;;
    *) _fail "config 输出异常：$(cat "$_stage_home/.cfg.out")" ;;
esac

# 7.2 同版本 update：只报「已是最新」，不下载不落盘
HOME="$_stage_home" CTFSWEEP_MIRROR="file://$_stage" "$_csw" update > "$_stage_home/.u1.out" 2>&1 \
    || _fail "update 失败（退出码非 0）"
case "$(cat "$_stage_home/.u1.out")" in
    *"已是最新版本"*) echo "update（同版本）OK" ;;
    *) _fail "update 输出异常：$(cat "$_stage_home/.u1.out")" ;;
esac

# 7.3 抬高镜像版本 → --check 只比对、不落盘
printf '%s\n' "$_NEXT" > "$_stage/VERSION"
printf '%s\n' "$_NEXT" > "$_stage/MyProject-CtfSweep/VERSION"
(cd "$_stage" && rm -f ctfsweep-src.tar.gz && tar -czf ctfsweep-src.tar.gz MyProject-CtfSweep)
_ver_before="$(cat "$_inst/VERSION")"
HOME="$_stage_home" CTFSWEEP_MIRROR="file://$_stage" "$_csw" update --check > "$_stage_home/.u2.out" 2>&1 \
    || _fail "update --check 失败（退出码非 0）"
case "$(cat "$_stage_home/.u2.out")" in
    *"远端 v$_NEXT 可用"*"--check：仅比对"*) : ;;
    *) _fail "update --check 输出异常：$(cat "$_stage_home/.u2.out")" ;;
esac
[ "$(cat "$_inst/VERSION")" = "$_ver_before" ] || _fail "update --check 竟然改动了 VERSION"
echo "update --check OK（仅比对、不落盘）"

# 7.4 真更新：埋一个扫描缓存哨兵，更新后它必须还在（R2：部署永不 rm -rf 安装根）
mkdir -p "$_inst/cache/sentinel-abc123"
printf 'sentinel\n' > "$_inst/cache/sentinel-abc123/1.txt"
HOME="$_stage_home" CTFSWEEP_MIRROR="file://$_stage" "$_csw" update > "$_stage_home/.u3.out" 2>&1 \
    || _fail "真更新失败：$(cat "$_stage_home/.u3.out")"
case "$(cat "$_stage_home/.u3.out")" in
    *"更新完成: v$_CUR → v$_NEXT"*) : ;;
    *) _fail "真更新输出异常：$(cat "$_stage_home/.u3.out")" ;;
esac
# 本次更新的安装根与 rc 里已写的一致 → 接线没变，就不该再提示重开终端
case "$(cat "$_stage_home/.u3.out")" in
    *"shell 配置未变"*) : ;;
    *) _fail "更新时接线一字未动，却仍在提示重开终端：$(cat "$_stage_home/.u3.out")" ;;
esac
[ "$(cat "$_inst/VERSION")" = "$_NEXT" ] || _fail "更新后 VERSION 未变：$(cat "$_inst/VERSION")"
[ -f "$_inst/cache/sentinel-abc123/1.txt" ] || _fail "更新删掉了扫描缓存（cache/sentinel-abc123/1.txt 不见了）"
[ "$(ls -A "$_inst/bin" | wc -l | tr -d ' ')" = "1" ] || _fail "更新后 bin/ 不止一个条目"
[ -L "$_inst/bin/ctfsweep" ] || _fail "更新后 bin/ctfsweep 不再是软链"
HOME="$_stage_home" "$_csw" --version >/dev/null || _fail "更新后启动器不可用"
echo "真更新 OK（v${_CUR} → v${_NEXT}；扫描缓存与布局契约都在）"

# 7.4b clear：清空数据目录。用户级安装下**数据根就是安装根**（bin/ lib/ VERSION 都在这儿），
# 所以这条同时守着两件事：缓存真的被删，以及功能项一个都没被碰。
# stdin 显式接 /dev/null：交互式跑 smoke 时终端是 tty，不接的话会停在确认提示上。
# 写法与 7.5 同规（if 判失败）：拒绝执行本来就返回 1，裸命令会被 set -e 当成脚本错误中断。
if HOME="$_stage_home" "$_csw" clear < /dev/null > "$_stage_home/.c1.out" 2>&1; then
    _fail "clear 无 -y 且非交互时竟然返回成功（应拒绝并返回 1）"
fi
case "$(cat "$_stage_home/.c1.out")" in
    *"请加 -y"*) : ;;
    *) _fail "clear 无 -y 且非交互时未拒绝：$(cat "$_stage_home/.c1.out")" ;;
esac
[ -f "$_inst/cache/sentinel-abc123/1.txt" ] || _fail "clear 拒绝执行时竟删了缓存"
HOME="$_stage_home" "$_csw" clear -y > "$_stage_home/.c2.out" 2>&1 \
    || _fail "clear -y 失败：$(cat "$_stage_home/.c2.out")"
case "$(cat "$_stage_home/.c2.out")" in
    *"已清空"*) : ;;
    *) _fail "clear -y 输出异常：$(cat "$_stage_home/.c2.out")" ;;
esac
[ ! -e "$_inst/cache" ] || _fail "clear -y 后 cache/ 仍在"
# 带名称只清一个项目：另一题的目录与缓存必须活着
mkdir -p "$_inst/另一题" "$_inst/cache/另一题-abc123"
printf 'x\n' > "$_inst/cache/另一题-abc123/1.txt"
HOME="$_stage_home" "$_csw" clear 另一题 -y >/dev/null 2>&1 \
    || _fail "clear <名称> 失败"
[ ! -e "$_inst/另一题" ] || _fail "clear <名称> 没删掉那个项目"
[ -d "$_inst/cache" ] || _fail "clear <名称> 把 cache/ 整个删了（应只删该项目那一份）"
[ -f "$_inst/VERSION" ] || _fail "clear -y 删掉了 VERSION（功能项不该被碰）"
[ -d "$_inst/lib/models" ] || _fail "clear -y 删掉了 lib/（用户级安装下数据根就是安装根）"
[ -L "$_inst/bin/ctfsweep" ] || _fail "clear -y 删掉了 bin/ctfsweep"
HOME="$_stage_home" "$_csw" --version >/dev/null || _fail "clear -y 后启动器不可用"
echo "clear OK（清空数据目录 · 功能项与配置保留）"

# 7.5 离线失败：镜像空 + 禁掉 GitHub 回退 → 必须明确报错且退出码非 0（绝不静默成功）
if HOME="$_stage_home" CTFSWEEP_MIRROR="file://$_empty" CTFSWEEP_GITHUB=none \
        "$_csw" update > "$_stage_home/.u4.out" 2>&1; then
    _fail "离线 update 竟然返回成功（应报错退出）"
fi
case "$(cat "$_stage_home/.u4.out")" in
    *"无法获取远端版本号"*) echo "update（离线失败路径）OK" ;;
    *) _fail "离线 update 输出异常：$(cat "$_stage_home/.u4.out")" ;;
esac

# 7.6 uninstall -y：摘除功能文件与 shell 接线，扫描缓存保留
# 哨兵在上一步 clear 里被删掉了，重新埋一个——这样「卸载不碰缓存」仍是当场验证的
mkdir -p "$_inst/cache/sentinel-abc123"
printf 'sentinel\n' > "$_inst/cache/sentinel-abc123/1.txt"
# 先把「老格式手工接线」原样塞回 rc（就是本机 ~/.zshrc 的真实形态）：
# 标题注释 + 指向仓库 bin 的 PATH + alias + source 仓库补全。卸载必须连注释一起清掉——
# 只删三行会留下一句对不上现状的 `# ctfsweep（源码直跑：…）`。
{
    echo '# ctfsweep（源码直跑：功能在项目目录，数据在 ~/.devtools/ctfsweep/）'
    echo 'export PATH="$HOME/Documents/MyCode/MyProject/CtfSweep/bin:$PATH"'
    echo "alias ctf='ctfsweep'"
    echo '[ -f "$HOME/Documents/MyCode/MyProject/CtfSweep/completions/ctfsweep.zsh" ] && source "$HOME/Documents/MyCode/MyProject/CtfSweep/completions/ctfsweep.zsh"'
} >> "$_stage_home/.zshrc"
HOME="$_stage_home" "$_csw" uninstall -y > "$_stage_home/.u5.out" 2>&1 \
    || _fail "uninstall 失败（退出码非 0）"
case "$(cat "$_stage_home/.u5.out")" in
    *"清理完成"*) : ;;
    *) _fail "uninstall 输出异常：$(cat "$_stage_home/.u5.out")" ;;
esac
[ ! -e "$_inst/bin" ] || _fail "卸载后 bin/ 仍在"
[ -f "$_inst/cache/sentinel-abc123/1.txt" ] || _fail "卸载删掉了扫描缓存"
if grep -q 'ctfsweep' "$_stage_home/.zshrc" 2>/dev/null; then
    _fail "卸载后 shell 接线未摘除：$(cat "$_stage_home/.zshrc")"
fi
echo "uninstall -y OK（功能与 shell 接线清理、扫描缓存保留）"

rm -rf "$_stage" "$_stage_home" "$_boot_root" "$_empty"

# ------------------------------- README 骨架章节（devtool 系列一致）
# 系列以 ptool 的 README 为基准，13 个顶级章节是这套文档的招牌。只要求"至少包含"
# ——各项目可以有额外章节（自己特有的功能说明）。缺任何一个都算漂了。
echo "== README 骨架章节 =="
if _rd="$(python3 -I tests/check_readme.py README.md 2>&1)"; then
    echo "$_rd"
else
    _fail "README 骨架章节（${_rd}）"
fi

echo "smoke: 全部通过"
