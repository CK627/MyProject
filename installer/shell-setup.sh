#!/usr/bin/env bash
# startupctl shell 接线：PATH + 补全（macOS / Linux）
#
# 用法:
#   shell-setup.sh install <安装根>     写入（先摘旧块，幂等）
#   shell-setup.sh remove  [安装根]     摘除（卸载时用）
#
# 形态与 jtool / ptool 一致：用 `# >>> startupctl >>>` / `# <<< startupctl <<<` 成对标记
# 框住整段（含块内那行空行）——卸载时整段删除，装多少轮都不会在 rc 里堆积空行；
# 写死路径的三行老格式无法定位块外那行空行，所以仍按行删一次（升级时清干净）。
# 老格式那一段的标题注释（`# startupctl` / `# startupctl（源码直跑：…）`）也一起删——
# 它就在被删的三行正上方，留着就是一句对不上现状的说明。
#
# 对外只有 `startupctl` 一个命令名（无后缀软链），**没有别名**。母本（CtfSweep）曾写过
# `alias ctf=ctfsweep` 并为此保留了 legacy 清理规则；本项目从未有过别名，所以这里
# **不需要**那段规则——照抄一份只会让后来人以为存在需要清理的历史接线。
# ⚠️ 若将来有人想加短别名：别加。短名在同一环境里撞车是必然的（谁后接线谁赢），
#    而 _strip 的识别规则一旦要为此保留，就再也删不掉了。
#
# sudo 场景：rc 要写到**登录用户**的家目录（root 的 rc 里写了也没人会 source），
# 且 sed -i 会把文件属主改成 root，写完必须交还。
#
# 末尾那句提示是本脚本按「rc 到底改没改」自己判的，两种形态：
#   改过 →「已写入 shell 配置: <rc>（重开终端或 source 后生效）」
#   没改 →「shell 配置未变: <rc>（接线一致，无需重开终端）」——升级时的常态
# 调用方（install.sh / install-from-source.sh / selfmgr.update）**不要再补一句**
# 同样的话，否则一次更新会连报两三次「重开终端」。
set -euo pipefail

ACTION="${1:-}"
INSTALL_DIR="${2:-}"
case "$ACTION" in
    install|remove) ;;
    *)
        echo "用法: $0 install <安装根> | $0 remove [安装根]" >&2
        exit 2
        ;;
esac
if [ "$ACTION" = "install" ] && [ -z "$INSTALL_DIR" ]; then
    echo "用法: $0 install <安装根>" >&2
    exit 2
fi

# ---- 目标用户：sudo 下取登录用户，而非 root ----
TARGET_HOME="$HOME"
TARGET_USER=""
if [ "$(id -u)" = "0" ] && [ -n "${SUDO_USER:-}" ]; then
    TARGET_HOME="$(eval echo "~${SUDO_USER}")"
    TARGET_USER="$SUDO_USER"
fi

_strip() {
    local rc_file="$1"
    local dir="${2:-}"
    [ -f "$rc_file" ] || return 1

    local hit=0
    # 成对标记 / 老格式的 `# startupctl…` 注释行 / 散落的路径行 / 手工接线（本仓库 bin）
    if grep -q -e "^# >>> startupctl >>>$" -e "^# startupctl" \
              -e "completions/startupctl" -e "devtools/startupctl/bin" \
              -e "StartupItemManagement/bin" "$rc_file" 2>/dev/null; then
        hit=1
    fi
    if [ -n "$dir" ] && grep -qF -- "$dir" "$rc_file" 2>/dev/null; then
        hit=1
    fi
    [ "$hit" -eq 1 ] || return 1

    sed -i.bak \
        -e "/^# >>> startupctl >>>$/,/^# <<< startupctl <<<$/d" \
        -e "/^# startupctl/d" \
        -e "\|completions/startupctl|d" \
        -e "\|devtools/startupctl/bin|d" \
        -e "\|StartupItemManagement/bin|d" \
        "$rc_file"
    rm -f "${rc_file}.bak"
    return 0
}

_chown_back() {
    [ -n "$TARGET_USER" ] || return 0
    chown "$TARGET_USER" "$1" 2>/dev/null || true
}

if [ "$ACTION" = "remove" ]; then
    _found=0
    for rc in "$TARGET_HOME/.zshrc" "$TARGET_HOME/.bashrc"; do
        if _strip "$rc" "$INSTALL_DIR"; then
            _chown_back "$rc"
            echo "已清理: $rc"
            _found=1
        fi
    done
    [ "$_found" -eq 1 ] || echo "（shell 配置中未发现 startupctl 接线）"
    exit 0
fi

# ---- install：选 rc（按登录用户的登录 shell）----
shell_name="$(basename "${SHELL:-}")"
if [ -n "$TARGET_USER" ]; then
    rs=""
    if [ "$(uname -s)" = "Darwin" ]; then
        rs="$(dscl . -read "/Users/${TARGET_USER}" UserShell 2>/dev/null | awk '{print $2}')" || true
    else
        rs="$(getent passwd "$TARGET_USER" 2>/dev/null | cut -d: -f7)" || true
    fi
    if [ -n "${rs:-}" ]; then
        shell_name="$(basename "$rs")"
    fi
fi
case "$shell_name" in
    bash) RC="$TARGET_HOME/.bashrc" COMP="startupctl.bash" ;;
    *)    RC="$TARGET_HOME/.zshrc"  COMP="startupctl.zsh" ;;
esac

# rc 不存在也要建（否则隔离环境里装完等于没接线）
[ -d "$TARGET_HOME" ] || { echo "家目录不存在: $TARGET_HOME" >&2; exit 1; }
[ -f "$RC" ] || : > "$RC"

# 摘掉旧块，再写入固定三行（幂等：重复安装不会堆叠）
#
# ⚠️ 「要不要重开终端」取决于这次**有没有真改到接线**：先记下 rc 的指纹，写完再比一次。
#    升级（update）时块内容通常一字不变（路径与命令名都没变），此时提示重开终端是
#    在提醒一件根本没发生的事——本脚本是这句提示的**唯一出处**，调用方不要自己再补一句。
_rc_sum() { cksum < "$1" 2>/dev/null || true; }
_rc_before="$(_rc_sum "$RC")"
_strip "$RC" "$INSTALL_DIR" || true
{
    echo "# >>> startupctl >>>"
    echo ""
    echo "export PATH=\"$INSTALL_DIR/bin:\$PATH\""
    echo "[ -f \"$INSTALL_DIR/completions/$COMP\" ] && source \"$INSTALL_DIR/completions/$COMP\""
    echo "# <<< startupctl <<<"
} >> "$RC"
_chown_back "$RC"

# 指纹取不到（缺 cksum 等）时按「改过」处理——保守方向是让用户多 source 一次，不是少一次
if [ -n "$_rc_before" ] && [ "$_rc_before" = "$(_rc_sum "$RC")" ]; then
    echo "shell 配置未变: ${RC}（接线一致，无需重开终端）"
else
    echo "已写入 shell 配置: ${RC}（重开终端或 source 后生效）"
fi
