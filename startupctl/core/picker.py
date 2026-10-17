# -*- coding: utf-8 -*-
"""选择器：进程选择器与启动项选择器。

用户要求「需要有一个窗口选择器来选择进程【系统基础进程要禁用不给选择】」，
后来又补了一条：「选择器是扫描进程还是启动项……再增加一层命令，启动项选择器、
进程选择器」。所以这里是**两个选择器**，共用同一套状态与回退链：

    pick_processes(procs, ...)   系统基础进程与锁定项**真的选不了**
    pick_startup(items, ...)     启动项（系统项也可选——它只是一条放行规则）

`Rows.toggle()` 会拒绝任何 `guard.is_protected()` 为真的进程行。UI 上的灰与
`[系统]` 标记是提示，真正的防线在 guard.is_protected()，而执行器（enforce.py）
动手前会**再查一次**。两层都要有：只在 UI 拦，策略文件是可以手改的；只在执行器拦，
用户会以为自己选中了。

三条回退链，每一步都说明原因，绝不静默换界面：
    窗口（tkinter） → 终端窗口（curses） → 纯文本（编号清单）
"""
import sys

from . import guard as guard_mod
from . import gui as gui_mod


class Row(object):
    """一个可选择的进程行。"""
    __slots__ = ('proc', 'protected', 'why', 'selected', 'locked')

    def __init__(self, proc, protected, why, selected=False, locked=False):
        self.proc = proc
        self.protected = protected
        self.why = why
        self.selected = selected
        # 锁定 = 用户自己钉住的条目。表现与系统基础进程一样：置灰、选不动。
        # 区别是它能被解锁，而系统进程永远不行。
        self.locked = locked

    @property
    def frozen(self):
        return self.protected or self.locked

    @property
    def mark(self):
        if self.protected:
            return '[系统]'
        if self.locked:
            return '[锁定]'
        return '[x]' if self.selected else '[ ]'

    @property
    def label(self):
        p = self.proc
        return p.comm or p.program or '?'

    @property
    def detail(self):
        p = self.proc
        return 'pid=%s  %s' % (p.pid, p.program or p.args_str or '')


class StartupRow(object):
    """一个可选择的启动项行。"""
    __slots__ = ('item', 'selected')

    def __init__(self, item, selected=False):
        self.item = item
        self.selected = selected

    frozen = False

    @property
    def mark(self):
        return '[x]' if self.selected else '[ ]'

    @property
    def label(self):
        it = self.item
        name = getattr(it, 'name', '') or getattr(it, 'anchor', '') or '?'
        return '%s%s' % (self.mark + ' ', name)

    @property
    def detail(self):
        it = self.item
        kind = getattr(it, 'kind', '') or ''
        scope = getattr(it, 'scope', '') or ''
        anchor = getattr(it, 'anchor', '') or ''
        prog = getattr(it, 'program', '') or ''
        return '%s/%s  %s  %s' % (kind, scope, anchor, prog)


class Rows(object):
    """进程选择器的状态。**可选性只由这里决定**，各 UI 共用。"""

    def __init__(self, procs, platform='', own_pids=(), preselect=None,
                 locked_matcher=None):
        self.platform = platform
        self.rows = []
        for p in sorted(procs, key=lambda x: (x.comm or x.program or '', x.pid)):
            prot, why = guard_mod.is_protected(p, platform, own_pids)
            locked = bool(locked_matcher(p)) if (locked_matcher and not prot) else False
            r = Row(p, prot, why, locked=locked)
            if locked:
                r.selected = True       # 锁定 = 留着它，必然在集合里
            elif preselect and not prot and p.pid in preselect:
                r.selected = True
            self.rows.append(r)

    def toggle(self, i):
        """切换第 i 行。**系统基础进程与锁定项是真的选不了**，不是只画成灰的。"""
        r = self.rows[i]
        if r.protected:
            return False, '系统基础进程不可选择（任何模式都不会结束它们）'
        if r.locked:
            return False, '已锁定——要改必须先解锁'
        r.selected = not r.selected
        return True, ''

    def toggle_lock(self, i):
        """锁定/解锁第 i 行。锁定 = 别动它：置灰、选不动，且必然在集合里。"""
        r = self.rows[i]
        if r.protected:
            return False, '系统基础进程本来就是不可动的，不需要锁定'
        r.locked = not r.locked
        if r.locked:
            r.selected = True
        return True, ''

    def selected_procs(self):
        return [r.proc for r in self.rows if r.selected and not r.protected]

    def results(self):
        return [(r.proc, r.locked) for r in self.rows
                if r.selected and not r.protected]


class StartupRows(object):
    """启动项选择器的状态。"""

    def __init__(self, items, preselect=None):
        pre = set(preselect or ())
        self.rows = []
        for it in sorted(items, key=lambda x: ((x.name or x.anchor or '').lower(),)):
            r = StartupRow(it, selected=(getattr(it, 'uid', None) in pre))
            self.rows.append(r)

    def toggle(self, i):
        r = self.rows[i]
        r.selected = not r.selected
        return True, ''

    def results(self):
        return [r.item for r in self.rows if r.selected]


# ---------------------------------------------------------------- 纯文本兜底
def _pick_plain(rows, title, note=''):
    """编号清单 + `1,3,5-8`。返回选中的行（Row/StartupRow）；空输入 = 取消。"""
    print('')
    print(title)
    if note:
        print('  %s' % note)
    print('')
    for i, r in enumerate(rows, 1):
        print('  %3d. %s %s' % (i, r.mark, r.label))
    print('')
    print('  输入编号（如 1,3,5-8；直接回车 = 取消）')
    try:
        line = input('  > ').strip()
    except EOFError:
        return None
    if not line:
        return None
    want = set()
    for part in line.replace('，', ',').split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, _, b = part.partition('-')
            try:
                want.update(range(int(a), int(b) + 1))
            except ValueError:
                continue
        else:
            try:
                want.add(int(part))
            except ValueError:
                continue
    picked = []
    for n in sorted(want):
        if 1 <= n <= len(rows):
            r = rows[n - 1]
            if getattr(r, 'frozen', False):
                print('  跳过第 %d 项（%s）' % (n, r.mark))
                continue
            picked.append(r)
    return picked


def _pick_tui(rows, title, note=''):
    """curses 窗口（POSIX 且有 tty）。返回选中的行；取消返回 None。"""
    import curses

    def _run(scr):
        curses.curs_set(0)
        cur = 0
        while True:
            scr.erase()
            h, w = scr.getmaxyx()
            scr.addnstr(0, 0, title, w - 1)
            if note:
                scr.addnstr(1, 0, note, w - 1)
            top = max(0, cur - (h - 5))
            for n, r in enumerate(rows[top:top + h - 5]):
                y = n + 3
                line = '%s %s  %s' % (r.mark, r.label, getattr(r, 'detail', ''))
                attr = curses.A_DIM if getattr(r, 'frozen', False) else 0
                if top + n == cur:
                    attr |= curses.A_REVERSE
                scr.addnstr(y, 2, line, w - 3, attr)
            scr.addnstr(h - 1, 0,
                        '↑↓ 移动 · 空格 选择 · a 全选 · n 全不选 · Enter 确定 · q 取消',
                        w - 1)
            scr.refresh()
            k = scr.getch()
            if k in (curses.KEY_UP, ord('k')):
                cur = max(0, cur - 1)
            elif k in (curses.KEY_DOWN, ord('j')):
                cur = min(len(rows) - 1, cur + 1)
            elif k == ord(' '):
                r = rows[cur]
                if not getattr(r, 'frozen', False):
                    r.selected = not r.selected
            elif k == ord('a'):
                for r in rows:
                    if not getattr(r, 'frozen', False):
                        r.selected = True
            elif k == ord('n'):
                for r in rows:
                    if not getattr(r, 'frozen', False):
                        r.selected = False
            elif k in (10, 13, curses.KEY_ENTER):
                return [r for r in rows if r.selected and not getattr(r, 'frozen', False)]
            elif k in (ord('q'), 27):
                return None
        return None

    return curses.wrapper(_run)


def _run_picker(rows, title, note='', allow_gui=True):
    if allow_gui and gui_mod.available():
        try:
            idx = gui_mod.pick(rows, title=title, subtitle=note)
            if idx is None:
                return None
            return [rows[i] for i in idx if not getattr(rows[i], 'frozen', False)]
        except gui_mod.GuiUnavailable:
            pass
    if sys.stdin.isatty() and sys.platform.startswith(('linux', 'darwin')):
        try:
            return _pick_tui(rows, title, note)
        except Exception:
            pass
    return _pick_plain(rows, title, note)


# ---------------------------------------------------------------- 两个选择器
def pick_processes(procs, platform='', own_pids=(), preselect=None,
                   locked_matcher=None, allow_gui=True):
    """选进程。返回 [(proc, locked)]；取消返回 None。"""
    state = Rows(procs, platform, own_pids, preselect, locked_matcher)
    picked = _run_picker(state.rows, '选择进程',
                         '系统基础进程与锁定项不可选；空格切换',
                         allow_gui=allow_gui)
    if picked is None:
        return None
    return [(r.proc, r.locked) for r in picked]


def pick_startup(items, preselect=None, allow_gui=True):
    """选启动项。返回 [item]；取消返回 None。"""
    state = StartupRows(items, preselect)
    picked = _run_picker(state.rows, '选择启动项',
                         '空格切换；已在名单里的项默认勾选',
                         allow_gui=allow_gui)
    if picked is None:
        return None
    return [r.item for r in picked]
