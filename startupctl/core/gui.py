# -*- coding: utf-8 -*-
"""窗口界面：选择器（加条目）与管理窗口（删/改条目）。

用户要的是「一个简单的 GUI 来选择，主要是怕输入的问题导致没有起作用」。所以
这里只做两件事，都尽量朴素：

    pick(...)     选择器——列出一屏东西，勾选后确定
    manage(...)   管理窗口——把名单里的条目列出来，删除/刷新

**没有 GUI 也绝不能挂**：`available()` 在非交互终端里返回 False，调用方回退到
纯文本；`pick` 只在真能弹窗时被调用。CI 与管道里弹一个等人点的窗口会让任务
直接挂住，而且没有输出、没有报错，极难归因。

测试接缝 `STARTUPCTL_GUI_SELFTEST=<N>`：窗口弹出后自动"选前 N 个可选项并确定"。
没有它，"GUI 真的能选出结果"就只能靠人手点，于是 CI 永远验不到这条路径。
"""
import os
import sys

_SELFTEST_ENV = 'STARTUPCTL_GUI_SELFTEST'


class GuiUnavailable(Exception):
    """窗口起不来（没有 tkinter / 没有显示）。调用方据此回退。"""


def available():
    """现在能不能弹窗？

    两个条件都满足才弹：有 tkinter，且**在交互式终端里**（或测试显式放开）。
    管道/CI 里 `isatty()` 为 False —— 那种环境下弹窗等于把任务挂死。
    """
    if os.environ.get(_SELFTEST_ENV):
        try:
            import tkinter  # noqa: F401
        except Exception:
            return False
        return True
    try:
        import tkinter  # noqa: F401
    except Exception:
        return False
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:
        return False


def _root(title):
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception as e:                      # pragma: no cover - 无 tkinter
        raise GuiUnavailable(str(e))
    try:
        root = tk.Tk()
    except Exception as e:                      # pragma: no cover - 无显示
        raise GuiUnavailable(str(e))
    root.title(title)
    root.geometry('900x560')
    root.minsize(620, 380)
    return root, tk, ttk


def _tree(parent, tk, ttk, cols):
    wrap = ttk.Frame(parent)
    wrap.pack(fill='both', expand=True, padx=10, pady=(10, 6))
    tree = ttk.Treeview(wrap, columns=cols, show='headings', selectmode='browse')
    for c, w in zip(cols, (260, 560)):
        tree.heading(c, text=c)
        tree.column(c, width=w, anchor='w', stretch=True)
    vs = ttk.Scrollbar(wrap, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=vs.set)
    tree.pack(side='left', fill='both', expand=True)
    vs.pack(side='right', fill='y')
    return tree


# ------------------------------------------------------------------ 选择器
def pick(rows, title='选择', subtitle='', columns=('名称', '详情')):
    """勾选式选择器。rows 是对象列表，需有 label / detail / frozen / selected。

    返回**选中行的下标列表**（只含可选项）；用户取消返回 None。
    系统基础进程与已锁定条目（frozen=True）在点击处理里就直接忽略，
    不只是画成灰的——UI 只是提示，真正的防线仍在 guard/enforce 里。
    """
    if not rows:
        return []
    root, tk, ttk = _root(title)

    head = ttk.Frame(root)
    head.pack(fill='x', padx=10, pady=(10, 0))
    ttk.Label(head, text=subtitle or '勾选要加入的条目（系统项与锁定项不可选）',
              foreground='#444').pack(side='left')
    filter_var = tk.StringVar()
    entry = ttk.Entry(head, textvariable=filter_var, width=22)
    entry.pack(side='right')
    ttk.Label(head, text='筛选:').pack(side='right', padx=(0, 6))

    tree = _tree(root, tk, ttk, columns)
    bot = ttk.Frame(root)
    bot.pack(fill='x', padx=10, pady=(0, 10))
    status_var = tk.StringVar()

    view = []          # tree iid -> rows 下标
    result = {'value': None}

    def look(r):
        return getattr(r, 'label', '') or ''

    def visible_idx():
        f = filter_var.get().strip().lower()
        if not f:
            return list(range(len(rows)))
        return [i for i, r in enumerate(rows) if f in look(r).lower()
                or f in (getattr(r, 'detail', '') or '').lower()]

    def mark(r):
        if getattr(r, 'frozen', False):
            return '[系统]' if getattr(r, 'protected', False) else '[锁定]'
        return '[x]' if r.selected else '[ ]'

    def fill():
        for iid in tree.get_children():
            tree.delete(iid)
        view[:] = visible_idx()
        for n, idx in enumerate(view):
            r = rows[idx]
            tree.insert('', 'end', iid=str(n), values=(mark(r) + ' ' + look(r),
                                                       getattr(r, 'detail', '')))
        refresh_status()

    def refresh_status():
        n = sum(1 for r in rows if r.selected and not getattr(r, 'frozen', False))
        status_var.set('已选 %d 项' % n)

    def toggle_selected():
        for iid in tree.selection():
            n = int(iid)
            if n >= len(view):
                continue
            r = rows[view[n]]
            if getattr(r, 'frozen', False):
                continue                     # 在点击处理里就忽略，不只是画灰
            r.selected = not r.selected
            tree.item(iid, values=(mark(r) + ' ' + look(r),
                                   getattr(r, 'detail', '')))
        refresh_status()

    def select_all():
        for r in rows:
            if not getattr(r, 'frozen', False):
                r.selected = True
        fill()

    def select_none():
        for r in rows:
            if not getattr(r, 'frozen', False):
                r.selected = False
        fill()

    def invert():
        for r in rows:
            if not getattr(r, 'frozen', False):
                r.selected = not r.selected
        fill()

    def on_ok():
        result['value'] = [i for i, r in enumerate(rows)
                           if r.selected and not getattr(r, 'frozen', False)]
        root.destroy()

    def on_cancel():
        result['value'] = None
        root.destroy()

    tree.bind('<Button-1>', lambda e: (tree.after_idle(toggle_selected), None)[1])
    tree.bind('<space>', lambda e: (toggle_selected(), 'break')[1])
    tree.bind('<Double-1>', lambda e: (toggle_selected(), None)[1])

    ttk.Button(bot, text='全选可选', command=select_all).pack(side='left')
    ttk.Button(bot, text='全不选', command=select_none).pack(side='left', padx=(6, 0))
    ttk.Button(bot, text='反选', command=invert).pack(side='left', padx=(6, 0))
    ttk.Label(bot, textvariable=status_var, foreground='#333').pack(side='left', padx=(16, 0))
    ttk.Button(bot, text='取消', command=on_cancel).pack(side='right')
    ttk.Button(bot, text='确定', command=on_ok).pack(side='right', padx=(0, 6))

    filter_var.trace_add('write', lambda *a: (fill(), None)[1])
    fill()
    entry.focus_set()
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
            for r in rows:
                if getattr(r, 'frozen', False):
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


# ------------------------------------------------------------------ 管理窗口
def manage(tabs, title='名单管理'):
    """管理窗口：一个页签一个维度，列出条目、可删除。

    tabs: [{'name': '启动项', 'provider': () -> [(左, 右)], 'on_remove': fn(下标)}]
    provider 每次刷新时重新取，所以删除后编号不会错位。
    """
    root, tk, ttk = _root(title)
    nb = ttk.Notebook(root)
    nb.pack(fill='both', expand=True, padx=10, pady=(10, 6))

    state = []      # 每个页签的 (tab, tree, provider, on_remove)

    def build_tab(spec):
        frame = ttk.Frame(nb)
        nb.add(frame, text='%s（%d）' % (spec['name'], len(spec['provider']())))
        tree = _tree(frame, tk, ttk, ('条目', '说明'))
        state.append([spec, tree])
        refill(len(state) - 1)
        return tree

    def refill(tab_i):
        spec, tree = state[tab_i]
        for iid in tree.get_children():
            tree.delete(iid)
        for i, (left, right) in enumerate(spec['provider']()):
            tree.insert('', 'end', iid=str(i), values=(left, right))
        nb.tab(tab_i, text='%s（%d）' % (spec['name'], len(spec['provider']())))

    def remove_selected():
        try:
            tab_i = nb.index(nb.select())
        except Exception:
            return
        if tab_i < 0 or tab_i >= len(state):
            return
        spec, tree = state[tab_i]
        sel = tree.selection()
        if not sel:
            return
        spec['on_remove'](int(sel[0]))
        refill(tab_i)

    bot = ttk.Frame(root)
    bot.pack(fill='x', padx=10, pady=(0, 10))
    ttk.Button(bot, text='删除选中', command=remove_selected).pack(side='left')
    ttk.Button(bot, text='刷新', command=lambda: [refill(i) for i in range(len(state))]) \
        .pack(side='left', padx=(6, 0))
    ttk.Button(bot, text='关闭', command=root.destroy).pack(side='right')

    for spec in tabs:
        build_tab(spec)
    try:
        root.protocol('WM_DELETE_WINDOW', root.destroy)
    except Exception:
        pass
    root.mainloop()
