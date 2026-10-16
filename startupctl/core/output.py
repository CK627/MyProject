# -*- coding: utf-8 -*-
"""输出排版：显示宽度 · 对齐 · 颜色 · 表格。

`dw()` 是**契约的一部分**，不只是排版糖：帮助文本的描述列对齐由冒烟测试用同一个
函数重算并断言一致（手改错一行对齐就挂）。统计字符数（`len`）在这里是错的——
终端里一个汉字占 2 列，用 len 对齐会让含中文的行整列歪掉。
"""
import os
import sys
import unicodedata

# ---- 颜色 ----
# 默认 auto：只有 stdout 是终端才上色。重定向到文件/管道时上色会把转义序列
# 写进结果，`startupctl list --json | jq` 会直接炸。
_COLOR_MODE = 'auto'
_CODES = {
    'reset': '\033[0m', 'dim': '\033[2m', 'bold': '\033[1m',
    'red': '\033[31m', 'green': '\033[32m', 'yellow': '\033[33m',
    'blue': '\033[34m', 'magenta': '\033[35m', 'cyan': '\033[36m',
}


def set_color_mode(mode):
    """auto | always | never（来自 --color / 配置 / NO_COLOR 环境变量）"""
    global _COLOR_MODE
    if mode in ('auto', 'always', 'never'):
        _COLOR_MODE = mode


def _color_on():
    if os.environ.get('NO_COLOR'):
        return False
    if _COLOR_MODE == 'always':
        return True
    if _COLOR_MODE == 'never':
        return False
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def c(text, color):
    """给 text 上色（关闭颜色时原样返回）。"""
    if not color or not _color_on():
        return text
    code = _CODES.get(color)
    if not code:
        return text
    return code + text + _CODES['reset']


def dw(s):
    """显示宽度：CJK 全角按 2 列。

    east_asian_width 的 'A'（ambiguous，如 ° ± × ÷）按 **1** 列计——与现代终端在
    Latin locale 下的实际表现一致；按 2 计会在多数终端上把列算歪。
    'W'（Wide）/ 'F'（Fullwidth）才是真正的双宽字符。
    """
    if not s:
        return 0
    total = 0
    for ch in s:
        total += 2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1
    return total


def pad(s, width, align='left'):
    """按**显示宽度**补空格到 width 列（不是字符数）。"""
    s = s or ''
    gap = width - dw(s)
    if gap <= 0:
        return s
    if align == 'right':
        return ' ' * gap + s
    return s + ' ' * gap


def truncate(s, width):
    """按显示宽度截断，超出补 '…'（保证结果宽度 <= width）。"""
    s = s or ''
    if dw(s) <= width:
        return s
    if width <= 1:
        return s[:width]
    out = ''
    used = 0
    for ch in s:
        w = 2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1
        if used + w > width - 1:
            break
        out += ch
        used += w
    return out + '…'


def term_width(default=100):
    """终端宽度（取不到或为 0 时用 default）。"""
    try:
        w = os.get_terminal_size(sys.stdout.fileno()).columns
        return w if w > 20 else default
    except Exception:
        return default


def render_table(rows, headers=None, max_col=None):
    """渲染一张定宽表。

    rows 是「单元格列表」的列表。列宽按每列的最大**显示宽度**算。
    max_col 给出末列的最大宽度（用于把长命令列截断）。
    """
    rows = [[('' if cell is None else str(cell)) for cell in row] for row in (rows or [])]
    if headers:
        headers = [str(h) for h in headers]
    if not rows and not headers:
        return ''

    ncol = max([len(r) for r in rows] + ([len(headers)] if headers else [0]))
    widths = [0] * ncol
    for r in rows + ([headers] if headers else []):
        for i, cell in enumerate(r):
            if i < ncol:
                widths[i] = max(widths[i], dw(cell))
    if max_col is not None:
        for i in max_col:
            if i < ncol:
                widths[i] = min(widths[i], max_col[i])

    lines = []
    if headers:
        lines.append('  '.join(pad(truncate(h, widths[i]), widths[i]) for i, h in enumerate(headers)).rstrip())
        lines.append('  '.join('-' * widths[i] for i in range(ncol)).rstrip())
    for r in rows:
        cells = []
        for i in range(ncol):
            cell = r[i] if i < len(r) else ''
            cells.append(pad(truncate(cell, widths[i]), widths[i]))
        lines.append('  '.join(cells).rstrip())
    return '\n'.join(lines)


def hr(width=None):
    return '-' * (width or min(term_width(), 78))
