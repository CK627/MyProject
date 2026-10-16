# -*- coding: utf-8 -*-
"""图形选择器（tkinter，标准库，零第三方依赖）。

为什么要有它：TUI 靠键盘、纯文本要打编号，两者都怕**输入出错**——而"选了半天其实
没生效"正是最难受的失败形态（选错了你看得见，没生效你看不见）。图形窗口里
每一条都是看得见的勾选框，点一下就变，**所见即所得**，没有"编号打错"这条路。

设计要点：

1. **用 `ttk.Treeview` 而不是一堆 Checkbutton**。900+ 个进程要是一行两个复选框，
   就是 1800 个控件，建窗口要好几秒；Treeview 是原生列表控件，几千行照样顺。
   勾选以**单元格文字**表达（`✓` / `锁`），点单元格即切换。
2. **系统基础进程在这里也真的点不动**：不仅显示成灰的 `系统`，点击处理里也直接忽略。
   与另两个选择器共用同一份 `picker.Rows`，所以"能不能选"的规则只有一处。
3. **返回前再过滤一遍 `is_protected()`**，与 tui/plain 一致（三道 UI 一条底线）。
4. 任何一步失败都**抛 GuiUnavailable**，由调用方回退到 TUI/纯文本——
   绝不能"窗口没弹出来但命令报成功"。
"""
import os
import sys

from . import guard as guard_mod
from . import picker as picker_mod

# 测试接缝：设 STARTUPCTL_GUI_SELFTEST=<N> 时，窗口弹出后自动"选前 N 个可选项并确定"。
# 没有它，"图形窗口真的能选出结果"就只能靠人手点一遍——而那意味着 CI 永远验不到
# 这条路径，出问题时用户才发现。与注册表 shim 同一性质：为可测性付一点复杂度是值的。
_SELFTEST_ENV = 'STARTUPCTL_GUI_SELFTEST'


class GuiUnavailable(Exception):
    """tkinter 不可用 / 无显示环境 / 窗口创建失败。调用方据此回退。"""


def available():
    """能不能用图形选择器。**只做探测**，不建窗口。"""
    try:
        import tkinter                                          # noqa: F401
    except ImportError:
        return False, 'tkinter 未安装（Linux 上通常需要装 python3-tk）'
    if sys.platform not in ('darwin', 'win32'):
        if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            return False, '没有图形显示环境（DISPLAY 未设置）'
    if os.environ.get('STARTUPCTL_NO_GUI'):
        return False, 'STARTUPCTL_NO_GUI 已设置'
    # ⚠️ 只在**交互式终端**下弹窗。CI / 管道里弹一个等人点的窗口会让任务直接挂住，
    #    而那种失败极难归因（没有输出、没有报错，就是不动）。自测接缝不受此限。
    if not os.environ.get(_SELFTEST_ENV):
        try:
            if not (sys.stdin.isatty() and sys.stdout.isatty()):
                return False, '当前不是交互式终端（管道/CI），不弹窗'
        except Exception:
            return False, '无法判断是否交互式终端'
    return True, ''


# 勾选标记：都用能稳定渲染的字符。✓ 是 BMP 常见字符；锁用汉字最稳。
_MARK_ON = '✓'
_MARK_OFF = ''
_SYS_LABEL = '系统'
_LOCK_LABEL = '锁'


def pick(rows, platform='', own_pids=()):
    """弹出图形选择器。`rows` 由 picker.pick() 建好后传进来（三个 UI 共用一份状态）。

    返回 `[(proc, locked)]`；**用户点了取消返回 None**。

    ⚠️ 两种"没结果"必须分清，否则会静默退化：
      · 窗口**打不开** → 抛 GuiUnavailable（调用方回退到 TUI/纯文本）
      · 用户**点了取消** → 返回 None（调用方就此打住，不该偷偷换个界面再来一次）
    """
    ok, why = available()
    if not ok:
        raise GuiUnavailable(why)

    import tkinter as tk
    from tkinter import ttk

    if not rows.rows:
        return []

    try:
        root = tk.Tk()
    except Exception as e:                                      # noqa: BLE001
        raise GuiUnavailable('无法创建窗口: %s' % e)

    result = {'value': None}

    root.title('startupctl — 选择进程')
    try:
        root.geometry('1000x640')
    except Exception:
        pass

    # ---------------- 顶部：说明 + 筛选 ----------------
    top = ttk.Frame(root, padding=(10, 8, 10, 4))
    top.pack(fill='x')

    head = ttk.Label(
        top, justify='left',
        text=('勾选要纳入策略的进程。灰底的「系统」行是系统基础进程，'
              '任何模式下都不会被结束，也点不动。'))
    head.pack(anchor='w')

    sub = ttk.Label(
        top, justify='left', foreground='#666',
        text=('点「选择」列勾选/取消 · 点「锁定」列把它钉住（锁定后任何模式下都不结束） · '
              '双击行也能勾选'))
    sub.pack(anchor='w', pady=(2, 6))

    filt_row = ttk.Frame(top)
    filt_row.pack(fill='x')
    ttk.Label(filt_row, text='筛选:').pack(side='left')
    filter_var = tk.StringVar()
    filter_entry = ttk.Entry(filt_row, textvariable=filter_var, width=32)
    filter_entry.pack(side='left', padx=(6, 12))
    ttk.Label(filt_row, text='（按进程名或路径过滤，留空显示全部）',
              foreground='#888').pack(side='left')

    status_var = tk.StringVar()

    # ---------------- 中部：列表 ----------------
    mid = ttk.Frame(root, padding=(10, 0, 10, 0))
    mid.pack(fill='both', expand=True)

    cols = ('sel', 'lock', 'name', 'pid', 'path')
    tree = ttk.Treeview(mid, columns=cols, show='headings', selectmode='browse')
    tree.heading('sel', text='选择')
    tree.heading('lock', text='锁定')
    tree.heading('name', text='进程名')
    tree.heading('pid', text='PID')
    tree.heading('path', text='可执行文件 / 命令行')
    tree.column('sel', width=56, anchor='center', stretch=False)
    tree.column('lock', width=56, anchor='center', stretch=False)
    tree.column('name', width=200, anchor='w', stretch=False)
    tree.column('pid', width=70, anchor='e', stretch=False)
    tree.column('path', width=560, anchor='w', stretch=True)

    vsb = ttk.Scrollbar(mid, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side='left', fill='both', expand=True)
    vsb.pack(side='right', fill='y')

    # 系统行灰底；锁定行浅黄
    tree.tag_configure('sys', foreground='#9a9a9a', background='#f2f2f2')
    tree.tag_configure('locked', background='#fff7d6')
    tree.tag_configure('on', foreground='#0a6b1e')

    # ---------------- 底部：按钮 ----------------
    bot = ttk.Frame(root, padding=(10, 6, 10, 10))
    bot.pack(fill='x')

    def refresh_status():
        sel, prot, total, lock = rows.counts()
        status_var.set('共 %d 个进程 · 已选 %d · 锁定 %d · 系统基础进程 %d（不可选）'
                       % (total, sel, lock, prot))

    # 行号 → 数据行下标（Treeview 的 iid 就是 rows.rows 的下标，便于回查）
    def fill():
        tree.delete(*tree.get_children())
        f = filter_var.get().strip().lower()
        shown = 0
        for i, r in enumerate(rows.rows):
            hay = '%s %s' % (r.proc.comm or '', r.proc.program or '')
            if f and f not in hay.lower():
                continue
            if r.protected:
                sel_mark, lock_mark, tag = _SYS_LABEL, '', 'sys'
            else:
                sel_mark = _MARK_ON if r.selected else _MARK_OFF
                lock_mark = _LOCK_LABEL if r.locked else ''
                tag = 'locked' if r.locked else ('on' if r.selected else '')
            tree.insert('', 'end', iid=str(i),
                        values=(sel_mark, lock_mark,
                                (r.proc.comm or '?')[:40],
                                r.proc.pid,
                                (r.proc.program or r.proc.args_str or '')[:200]),
                        tags=(tag,) if tag else ())
            shown += 1
        refresh_status()
        return shown

    def toggle_selected():
        s = tree.selection()
        if not s:
            return
        idx = int(s[0])
        ok2, why2 = rows.toggle(idx)
        nxt = _next_row(idx)
        _repaint_row(idx)
        if nxt is not None:
            tree.selection_set(str(nxt))
            tree.see(str(nxt))
        if not ok2:
            status_var.set('不能改这一行：%s' % why2)

    def toggle_locked():
        s = tree.selection()
        if not s:
            return
        idx = int(s[0])
        ok2, why2 = rows.toggle_lock(idx)
        _repaint_row(idx)
        if not ok2:
            status_var.set('不能改这一行：%s' % why2)

    def _next_row(idx):
        items = list(tree.get_children())
        for n, iid in enumerate(items):
            if iid == str(idx):
                return int(items[n + 1]) if n + 1 < len(items) else None
        return None

    def _repaint_row(idx):
        iid = str(idx)
        if not tree.exists(iid):
            return
        r = rows.rows[idx]
        if r.protected:
            vals = (_SYS_LABEL, '', (r.proc.comm or '?')[:40], r.proc.pid,
                    (r.proc.program or r.proc.args_str or '')[:200])
            tag = 'sys'
        else:
            vals = (_MARK_ON if r.selected else _MARK_OFF,
                    _LOCK_LABEL if r.locked else '',
                    (r.proc.comm or '?')[:40], r.proc.pid,
                    (r.proc.program or r.proc.args_str or '')[:200])
            tag = 'locked' if r.locked else ('on' if r.selected else '')
        tree.item(iid, values=vals, tags=(tag,) if tag else ())
        refresh_status()

    def on_click(event):
        """点「选择」/「锁定」列即切换。**系统行在这里也直接忽略。**"""
        rowid = tree.identify_row(event.y)
        colid = tree.identify_column(event.x)
        if not rowid:
            return
        tree.selection_set(rowid)
        idx = int(rowid)
        if rows.rows[idx].protected:
            status_var.set('系统基础进程，任何模式下都不会被结束，不可选：%s'
                           % rows.rows[idx].why)
            return
        if colid == '#1':
            toggle_selected()
        elif colid == '#2':
            toggle_locked()

    def on_double(event):
        rowid = tree.identify_row(event.y)
        if rowid:
            tree.selection_set(rowid)
            toggle_selected()

    def on_key(event):
        if event.keysym == 'space':
            toggle_selected()
            return 'break'
        if event.keysym in ('l', 'L'):
            toggle_locked()
            return 'break'
        return None

    tree.bind('<Button-1>', on_click)
    tree.bind('<Double-1>', on_double)
    tree.bind('<space>', on_key)
    tree.bind('<Key-l>', on_key)
    tree.bind('<Key-L>', on_key)

    def select_all():
        f = filter_var.get().strip().lower()
        for i, r in enumerate(rows.rows):
            if r.protected:
                continue
            hay = '%s %s' % (r.proc.comm or '', r.proc.program or '')
            if f and f not in hay.lower():
                continue
            r.selected = True
        fill()

    def select_none():
        for r in rows.rows:
            if not r.protected and not r.locked:
                r.selected = False
        fill()

    def invert():
        f = filter_var.get().strip().lower()
        for i, r in enumerate(rows.rows):
            if r.protected or r.locked:
                continue
            hay = '%s %s' % (r.proc.comm or '', r.proc.program or '')
            if f and f not in hay.lower():
                continue
            r.selected = not r.selected
        fill()

    def on_ok():
        picked = [(p, lk) for (p, lk) in rows.results()
                  if not guard_mod.is_protected(p, platform, own_pids)[0]]
        result['value'] = picked
        root.destroy()

    def on_cancel():
        result['value'] = None
        root.destroy()

    ttk.Button(bot, text='全选可选', command=select_all).pack(side='left')
    ttk.Button(bot, text='全不选', command=select_none).pack(side='left', padx=(6, 0))
    ttk.Button(bot, text='反选', command=invert).pack(side='left', padx=(6, 0))
    ttk.Label(bot, textvariable=status_var, foreground='#333').pack(side='left', padx=(16, 0))
    ttk.Button(bot, text='取消', command=on_cancel).pack(side='right')
    ttk.Button(bot, text='确定', command=on_ok).pack(side='right', padx=(0, 6))

    filter_var.trace_add('write', lambda *a: (fill(), None)[1])
    fill()
    filter_entry.focus_set()
    try:
        root.bind('<Escape>', lambda e: on_cancel())
        root.bind('<Return>', lambda e: on_ok())
        root.protocol('WM_DELETE_WINDOW', on_cancel)
    except Exception:
        pass
    selftest = os.environ.get(_SELFTEST_ENV)
    if selftest:
        def _auto():
            try:
                n = int(selftest)
            except ValueError:
                n = 1
            cnt = 0
            for r in rows.rows:
                if r.protected:
                    continue
                if cnt >= n:
                    break
                r.selected = True
                cnt += 1
            refresh_status()
            on_ok()
        root.after(250, _auto)

    root.mainloop()
    return result['value']
