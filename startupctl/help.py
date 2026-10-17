# -*- coding: utf-8 -*-
"""帮助文本——**由数据表构建**，不手写对齐。

为什么是构建而不是一串字面量：手写的对齐会**漂移**。改一个子命令名、给某个选项
多打一个字，整节描述列就歪了，而这种歪在 review 里几乎看不出来。用 `pad()` 按显示
宽度（CJK 计 2 列）算出来，对齐就是构造上正确的；`tests` 里再用 `output.dw` 复算一遍
作为回归护栏。

**形态与 ptool 一致**：`用法:` 本身就是命令清单，一行一条、全部可见；
不设「子命令:」分区，也不用 `whitelist ...` 这类省略号。

**本工具不用 `--` 旗标**，所有参数都是子命令词。
"""
from .core.output import dw, pad

TITLE = 'startupctl - 启动项扫描与管理（零依赖，Python 3.8+）'

COMMANDS = [
    ('startupctl list', '列出第三方启动项'),
    ('startupctl list all', '连系统项一起列'),
    ('startupctl list system', '只看系统项'),
    ('startupctl mode', '看当前模式与将会发生什么'),
    ('startupctl mode deny_all', '全部拒绝：除系统基础进程外一律结束'),
    ('startupctl mode blacklist', '黑名单：只结束挑中的'),
    ('startupctl mode whitelist', '白名单：只放行挑中的'),
    ('startupctl mode whitelist confirm', '同上，跳过确认（脚本用）'),
    ('startupctl mode off', '关闭干预（默认）'),
    ('startupctl whitelist', '管理白名单：启动项 / 进程两个页'),
    ('startupctl whitelist startup', '只看白名单里的启动项'),
    ('startupctl whitelist process', '只看白名单里的进程'),
    ('startupctl whitelist startup selector', '选择启动项加入白名单'),
    ('startupctl whitelist process selector', '选择进程加入白名单'),
    ('startupctl blacklist', '管理黑名单：启动项 / 进程两个页'),
    ('startupctl blacklist startup', '只看黑名单里的启动项'),
    ('startupctl blacklist process', '只看黑名单里的进程'),
    ('startupctl blacklist startup selector', '选择启动项加入黑名单'),
    ('startupctl blacklist process selector', '选择进程加入黑名单'),
    ('startupctl config', '显示配置、数据目录与模式'),
    ('startupctl version', '显示版本'),
    ('startupctl help [子命令]', '帮助（给子命令名则看它的完整说明）'),
    ('startupctl update [check]', '检查并更新到最新版本'),
    ('startupctl install', '完整安装（从源码目录）'),
    ('startupctl uninstall [confirm]', '卸载（confirm 跳过确认）'),
]

EXAMPLES = [
    ('startupctl list', '看这台机器有哪些第三方启动项'),
    ('startupctl whitelist process selector', '开窗口选要放行的进程'),
    ('startupctl whitelist startup selector', '开窗口选要放行的启动项'),
    ('startupctl mode whitelist', '按白名单执行：只留挑中的'),
    ('startupctl mode', '看这么设置会结束哪些进程（不改动）'),
]

NOTES = [
    '两个维度: 名单同时管启动项与进程，判定时命中任一即算命中',
    '系统永不结束: 三种模式都保留系统基础进程，以及你还在用的 shell / 终端',
    '选中才生效: 名单为空时拒绝切到白/黑名单模式——空名单等于「除系统外全杀」',
    '策略文件: ~/.devtools/startupctl/guard.json（JSON，可直接编辑）',
]

SUB_HELP = {
    'list': """
用法: startupctl list [all|system]

列出启动项。默认只列**第三方**——系统项动辄近千个，全列等于没列。

  startupctl list          第三方（默认）
  startupctl list all      全部
  startupctl list system   只看系统项

标记列里 [白]/[黑] 表示该启动项在对应名单里（启动项维度）。
""",
    'mode': """
用法: startupctl mode [off|deny_all|blacklist|whitelist]

    off         不干预，只报告（默认）
    deny_all    全部拒绝：除系统基础进程外一律结束（白名单此时是豁免清单）
    blacklist   黑名单：只结束挑中的，其余放行
    whitelist   白名单：只放行挑中的（+系统基础进程），其余结束

不带参数时只**报告**：当前模式、名单条数、这次会结束哪些进程。不改动任何东西。\n\n末尾加 confirm 可跳过确认（脚本用，与 uninstall confirm 同一套写法）。

切到 deny_all / blacklist / whitelist 时会先打印计划、问一次确认，然后执行一次；
模式随之保存。名单为空时直接拒绝（退出 3）——空名单的白名单模式等于「除系统外全杀」。
""",
    'whitelist': """
用法: startupctl whitelist [startup|process] [selector]

白名单：三种模式下「要留着」的东西。

  startupctl whitelist                    管理窗口（启动项 / 进程两个页签，可删除）
  startupctl whitelist startup            只看启动项那页
  startupctl whitelist process            只看进程那页
  startupctl whitelist startup selector   开窗口挑启动项，加进白名单
  startupctl whitelist process selector   开窗口挑进程，加进白名单

启动项选择器只列第三方项（系统项永远受保护，加进来只是噪声）；进程选择器里
系统基础进程与你自己的 shell / 终端**不可选**。
""",
    'blacklist': """
用法: startupctl blacklist [startup|process] [selector]

黑名单：只结束/禁止挑中的那些。

  startupctl blacklist                    管理窗口（启动项 / 进程两个页签，可删除）
  startupctl blacklist startup            只看启动项那页
  startupctl blacklist process            只看进程那页
  startupctl blacklist startup selector   开窗口挑启动项，加进黑名单
  startupctl blacklist process selector   开窗口挑进程，加进黑名单

两个维度命中任一即算命中：拉黑一个启动项，它拉起的进程同样会被结束。
""",
    'config': """
用法: startupctl config

显示版本、安装根、平台、数据目录与策略文件位置、两个名单的条数、当前模式。
只读，不改动任何东西。
""",
    'version': """
用法: startupctl version

打印版本号。
""",
    'update': """
用法: startupctl update [check]

检查并更新到最新版本（镜像优先，GitHub 回退）。

  startupctl update          真更新
  startupctl update check    只比对，不落盘

更新不会动 guard.json（名单与模式）。
""",
    'install': """
用法: startupctl install

安装说明。真正的安装请用 installer/install.sh（macOS / Linux）或安装包（Windows）。
""",
    'uninstall': """
用法: startupctl uninstall [confirm]

卸载安装副本并摘除 shell 接线。交互式会问一次确认；加 confirm 跳过。

**不会删除** guard.json（白名单 / 黑名单 / 模式）——那是用户逐条确认过的安全产物。
""",
    'help': """
用法: startupctl help [子命令]

不带参数打印总览；给子命令名打印它的完整说明。
""",
}


def _rows(rows, indent=2, gap=2):
    """把 (左, 右) 表渲染成按显示宽度对齐的行。"""
    if not rows:
        return []
    width = max(dw(left) for left, _ in rows)
    out = []
    for left, right in rows:
        out.append(' ' * indent + pad(left, width) + ' ' * gap + right)
    return out


def _build():
    lines = [TITLE, '']
    lines.append('用法:')
    lines.extend(_rows(COMMANDS))
    lines.append('')
    lines.append('示例:')
    lines.extend(_rows(EXAMPLES))
    lines.append('')
    lines.append('说明:')
    lines.extend('  ' + n for n in NOTES)
    return '\n'.join(lines) + '\n'


HELP = _build()


def sub_help(name):
    text = SUB_HELP.get(name)
    if not text:
        return None
    return text.strip('\n') + '\n'


def help_lines():
    """HELP 的行数（冒烟测试断言 <= 50）。"""
    return len(HELP.splitlines())


def align_report():
    """复算各分节的对齐，返回 [(section, lineno, 问题)]。

    测试用它而不是信任字面量：手改数据表导致某一节描述列不齐时，CI 会挂。
    分节内描述列的起始位置必须一致（按显示宽度算，CJK 计 2）。
    """
    problems = []
    section = None
    col = None
    for i, line in enumerate(HELP.splitlines(), 1):
        s = line.rstrip()
        if not s:
            section, col = None, None
            continue
        if s.endswith(':') and not s.startswith(' '):
            section, col = s[:-1], None
            continue
        if section is None or not s.startswith('  '):
            continue
        body = s[2:]
        # 描述列 = **最后一段**连续空格的结束位置。
        # 不能取第一段：左列各条长短不一，第一个双空格就是左列自身的结束处，
        # 于是每条都"不同列"——那正是本检查器第一版报出的假失败。
        start, j = None, 0
        while j < len(body) - 1:
            if body[j] == ' ' and body[j + 1] == ' ':
                k = j
                while k < len(body) and body[k] == ' ':
                    k += 1
                start, j = k, k
            else:
                j += 1
        if start is None:
            # 说明段是单列，不参与对齐
            if section == '说明':
                continue
            problems.append((section, i, '没有描述列'))
            continue
        width = dw(body[:start])
        if col is None:
            col = width
        elif width != col:
            problems.append((section, i, '描述列在 %d，本节应为 %d' % (width, col)))
    return problems
