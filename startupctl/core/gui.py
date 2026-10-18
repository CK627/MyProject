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

# 分组默认**折叠**：用户要求一打开是收起来的状态，先看应用列表再展开。
EXPAND_BY_DEFAULT = False


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
    # 居中：用户要求窗口开在屏幕中间。先 withdraw，摆好位置再显示，
    # 否则会先在左上角闪一下再跳过去。
    root.withdraw()
    w, h = 900, 560
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry('%dx%d+%d+%d' % (w, h, max(0, (sw - w) // 2), max(0, (sh - h) // 2)))
    root.minsize(720, 420)
    root.deiconify()
    return root, tk, ttk


def _tree(parent, tk, ttk, cols, widths=None):
    wrap = ttk.Frame(parent)
    wrap.pack(fill='both', expand=True, padx=10, pady=(10, 6))
    tree = ttk.Treeview(wrap, columns=cols, show='headings', selectmode='browse')
    if not widths or len(widths) != len(cols):
        widths = tuple(560 // max(1, len(cols)) for _ in cols)
    for c, w in zip(cols, widths):
        tree.heading(c, text=c)
        tree.column(c, width=w, anchor='w', stretch=True)
    vs = ttk.Scrollbar(wrap, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=vs.set)
    tree.pack(side='left', fill='both', expand=True)
    vs.pack(side='right', fill='y')
    return tree


# ------------------------------------------------------------------ 选择器
def pick(rows, title='选择', subtitle='', columns=('选择', '名称', '说明'),
         widths=(70, 340, 480), tabs=None):
    """勾选式选择器。rows 是对象列表，需有 label / detail / frozen / selected。

    **用原生 ttk.Checkbutton**，不是 Treeview 里画的字符或图标：
    用户明确要"原生的"。每行一个 Checkbutton，分组用可折叠的标题行，
    `ttk.Checkbutton` 的 `alternate` 状态表达"部分选中"。

    `tabs` 为 [(页签名, [行下标]) 或 (页签名, [行下标], 分组函数)]。
    返回**选中行的下标列表**（只含可选项）；用户取消返回 None。
    """
    if not rows:
        return []
    columns = columns or ('选择', '名称', '说明')
    root, tk, ttk = _root(title)

    # ★ 颜色写死，不用 macOS 的动态色。
    #   aqua 主题里 TCheckbutton/TLabel 的前景是 systemLabelColor —— 窗口不是
    #   活动窗口时系统把它渲染成灰色，整屏看起来像"全禁用了"（用户实测反馈）。
    #   列表底色同理：用纯白，和之前的表格观感一致。
    style = ttk.Style()
    style.configure('Pick.TCheckbutton', background='#ffffff', foreground='#1d1d1f')
    style.map('Pick.TCheckbutton',
              foreground=[('disabled', '#9a9a9a')],
              background=[('active', '#f2f2f2')])
    style.configure('Pick.TFrame', background='#ffffff')
    style.configure('Pick.TLabel', background='#ffffff', foreground='#3a3a3a')
    style.configure('PickHead.TLabel', background='#ffffff', foreground='#111111',
                    font=('TkDefaultFont', 11, 'bold'))

    head = ttk.Frame(root)
    head.pack(fill='x', padx=10, pady=(10, 0))
    ttk.Label(head, text=subtitle or '勾选要加入的条目（系统项与锁定项不可选）',
              foreground='#444').pack(side='left')
    filter_var = tk.StringVar()
    entry = ttk.Entry(head, textvariable=filter_var, width=22)
    entry.pack(side='right')
    ttk.Label(head, text='筛选:').pack(side='right', padx=(0, 6))

    nb = ttk.Notebook(root)
    nb.pack(fill='both', expand=True, padx=10, pady=(8, 6))
    if not tabs:
        tabs = [('全部', list(range(len(rows))), None)]

    result = {'value': None}
    status_var = tk.StringVar()
    CB_VARS = {}      # 行下标 → BooleanVar（Checkbutton 的状态源）
    pages = []      # [(canvas, inner, idxs, group_by)]

    def make_page(name, idxs, group_by):
        frame = ttk.Frame(nb)
        nb.add(frame, text='%s（%d）' % (name, len(idxs)))
        canvas = tk.Canvas(frame, highlightthickness=0, borderwidth=0,
                           background='#ffffff')
        vs = ttk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vs.set)
        vs.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        inner = ttk.Frame(canvas, style='Pick.TFrame')
        win = canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.bind('<Configure>',
                    lambda e, c=canvas, w=win: c.itemconfigure(w, width=e.width))
        inner.bind('<Configure>',
                   lambda e, c=canvas: c.configure(scrollregion=c.bbox('all')))
        # 滚轮（macOS 是 MouseWheel，X11 是 Button-4/5）
        def wheel(e, c=canvas):
            delta = -1 if getattr(e, 'num', None) == 5 or getattr(e, 'delta', 0) < 0 else 1
            c.yview_scroll(delta, 'units')
            return 'break'
        canvas.bind('<MouseWheel>', wheel)
        canvas.bind('<Button-4>', wheel)
        canvas.bind('<Button-5>', wheel)
        pages.append((canvas, inner, list(idxs), group_by))
        return inner

    for spec in tabs:
        make_page(spec[0], list(spec[1]), spec[2] if len(spec) > 2 else None)

    def match(r, f):
        if not f:
            return True
        return f in (getattr(r, 'label', '') or '').lower() \
            or f in (getattr(r, 'detail', '') or '').lower() \
            or f in (getattr(r, 'display_name', '') or '').lower()

    def refresh_status():
        n = sum(1 for r in rows if r.selected and not getattr(r, 'frozen', False))
        status_var.set('已选 %d 项' % n)

    def rebuild():
        f = filter_var.get().strip().lower()
        for canvas, inner, idxs, group_by in pages:
            for w in inner.winfo_children():
                w.destroy()
            inner.grid_columnconfigure(0, minsize=18)
            inner.grid_columnconfigure(1, weight=1)
            row = 0
            # 表头：没有它，一列列勾选框看起来不像表格
            ttk.Label(inner, text='', style='PickHead.TLabel').grid(row=row, column=0)
            for j, name in enumerate(columns[1:], start=1):
                ttk.Label(inner, text=name, style='PickHead.TLabel').grid(
                    row=row, column=j, sticky='w', padx=(0, 10), pady=(0, 4))
            row += 1
            vis = [gi for gi in idxs if match(rows[gi], f)]
            if group_by:
                groups, order = {}, []
                for gi in vis:
                    g = group_by(rows[gi]) or '其他'
                    if g not in groups:
                        groups[g] = []
                        order.append(g)
                    groups[g].append(gi)
                for gname in sorted(order, key=lambda x: (x == '其他', x.lower())):
                    kids = groups[gname]
                    if len(kids) == 1:
                        row = add_row(inner, row, rows[kids[0]], kids[0], None)
                        continue
                    row = add_group(inner, row, gname, kids)
            else:
                for gi in vis:
                    row = add_row(inner, row, rows[gi], gi, None)
        refresh_status()

    def add_row(parent, row, r, gi, group_ctx):
        live = not getattr(r, 'frozen', False)
        var = tk.BooleanVar(value=r.selected)
        texts = columns[1:] if len(columns) > 1 else ()
        cb = ttk.Checkbutton(parent, style='Pick.TCheckbutton',
                             text=getattr(r, 'display_name', None)
                             or getattr(r, 'label', ''), variable=var)
        if live:
            def _toggle(_r=r, _v=var):
                _r.selected = bool(_v.get())
                refresh_status()
                resync_groups()
            cb.configure(command=_toggle)
        else:
            cb.state(['disabled'])
        cb.grid(row=row, column=1, sticky='w', padx=(0, 8), pady=1)

        cells = list(getattr(r, 'cells', None) or
                     [getattr(r, 'label', ''), getattr(r, 'detail', '')])
        for j, val in enumerate(cells[1:], start=2):
            ttk.Label(parent, text=str(val), style='Pick.TLabel').grid(
                row=row, column=j, sticky='w', padx=(0, 10))
        CB_VARS[gi] = var
        return row + 1

    def add_group(parent, row, gname, kids):
        live = [rows[gi] for gi in kids if not getattr(rows[gi], 'frozen', False)]
        holder = {'open': EXPAND_BY_DEFAULT, 'rows': [], 'kids': kids}
        var = tk.BooleanVar(value=False)
        cb = ttk.Checkbutton(parent, style='Pick.TCheckbutton',
                             text='%s（%d）' % (gname, len(kids)), variable=var)
        if live:
            def _toggle_group(_v=var, _live=live):
                want = bool(_v.get())
                for gi in holder['kids']:
                    r = rows[gi]
                    if getattr(r, 'frozen', False):
                        continue
                    r.selected = want
                    v = CB_VARS.get(gi)
                    if v is not None:
                        v.set(want)
                refresh_status()
                resync_groups()
            cb.configure(command=_toggle_group)
        else:
            cb.state(['disabled'])
        cb.grid(row=row, column=1, sticky='w', pady=(6, 1))

        arrow = ttk.Label(parent, text=('▾' if holder['open'] else '▸'),
                          cursor='hand2', width=2, style='Pick.TLabel')
        arrow.grid(row=row, column=0, sticky='w')
        arrow.bind('<Button-1>', lambda e, h=holder, a=arrow: toggle_open(h, a))
        holder['cb'], holder['var'], holder['live'] = cb, var, live
        GROUPS.append(holder)
        row += 1
        start = row
        for gi in kids:
            row = add_row(parent, row, rows[gi], gi, holder)
        holder['rows'] = list(range(start, row))
        if not holder['open']:
            for rr in holder['rows']:
                parent.grid_rowconfigure(rr, weight=0)
            # 折叠：把子行从布局里摘掉
            for w in parent.grid_slaves():
                try:
                    info = w.grid_info()
                except Exception:
                    continue
                if info and int(info.get('row', -1)) in holder['rows']:
                    w.grid_remove()
        return row

    def toggle_open(h, arrow):
        h['open'] = not h['open']
        arrow.configure(text='▾' if h['open'] else '▸')
        parent = arrow.master
        for w in parent.grid_slaves():
            try:
                info = w.grid_info()
            except Exception:
                continue
            if info and int(info.get('row', -1)) in h['rows']:
                if h['open']:
                    w.grid()
                else:
                    w.grid_remove()

    def resync_groups():
        for h in list(GROUPS):
            if not h['live']:
                continue
            n = sum(1 for r in h['live'] if r.selected)
            cb = h['cb']
            if n == 0:
                cb.state(['!alternate'])
                h['var'].set(False)
            elif n == len(h['live']):
                cb.state(['!alternate'])
                h['var'].set(True)
            else:
                cb.state(['alternate'])
                h['var'].set(False)
            # 组标题上的计数随筛选/选择保持可读
            cb.configure(text=cb.cget('text').split('（')[0] + '（%d）' % len(h['kids']))

    GROUPS = []

    def select_all():
        for r in rows:
            if not getattr(r, 'frozen', False):
                r.selected = True
        rebuild()

    def select_none():
        for r in rows:
            if not getattr(r, 'frozen', False):
                r.selected = False
        rebuild()

    def invert():
        for r in rows:
            if not getattr(r, 'frozen', False):
                r.selected = not r.selected
        rebuild()

    def on_ok():
        result['value'] = [i for i, r in enumerate(rows)
                           if r.selected and not getattr(r, 'frozen', False)]
        root.destroy()

    def on_cancel():
        result['value'] = None
        root.destroy()

    bot = ttk.Frame(root)
    bot.pack(fill='x', padx=10, pady=(0, 10))
    ttk.Button(bot, text='全选可选', command=select_all).pack(side='left')
    ttk.Button(bot, text='全不选', command=select_none).pack(side='left', padx=(6, 0))
    ttk.Button(bot, text='反选', command=invert).pack(side='left', padx=(6, 0))
    ttk.Label(bot, textvariable=status_var, foreground='#333').pack(side='left', padx=(16, 0))
    ttk.Button(bot, text='取消', command=on_cancel).pack(side='right')
    ttk.Button(bot, text='确定', command=on_ok).pack(side='right', padx=(0, 6))

    filter_var.trace_add('write', lambda *a: (rebuild(), None)[1])
    rebuild()
    entry.focus_set()
    # 让窗口真的成为活动窗口：否则 macOS 把控件按"非活动"的灰色画
    try:
        root.lift()
        root.attributes('-topmost', True)
        root.focus_force()
        root.after(300, lambda: root.attributes('-topmost', False))
    except Exception:
        pass
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
        tree = _tree(frame, tk, ttk, ('条目', '说明'), (360, 500))
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
