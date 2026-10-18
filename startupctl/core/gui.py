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
import subprocess
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


def _check_images(tk):
    """16x16 的勾选方框（未选 / 选中 / 部分 / 系统 / 锁定）。

    用 PhotoImage 画而不是 ☐☑ 字符：字符大小跟着**字体**走，和系统自带的展开
    三角放在一起高矮不齐。固定 16px 与 macOS 原生复选框同尺寸，观感一致。

    选中是蓝底白勾（macOS 的样子），不是白底蓝勾。
    """
    S = 16

    def box(mark=None, border='#8e8e93', fill='#ffffff', mark_color='#0a84ff'):
        img = tk.PhotoImage(width=S, height=S)
        img.put(fill, to=(0, 0, S, S))
        for i in range(S):
            img.put(border, (i, 0))
            img.put(border, (i, S - 1))
            img.put(border, (0, i))
            img.put(border, (S - 1, i))
        if mark == 'check':
            for (x, y) in ((4, 8), (5, 9), (6, 10), (7, 9), (8, 8), (9, 7), (10, 6), (11, 5)):
                img.put(mark_color, (x, y))
                img.put(mark_color, (x, y + 1))
        elif mark == 'dash':
            for x in range(5, 11):
                img.put(mark_color, (x, 8))
        return img

    return {
        'off': box(),
        'on': box('check', '#0a84ff', '#0a84ff', '#ffffff'),
        'part': box('dash', '#0a84ff', '#ffffff', '#0a84ff'),
        'none': box('dash', '#c7c7cc', '#f2f2f7', '#c7c7cc'),
        'lock': box('dash', '#c9a227', '#fff8e1', '#a67c00'),
    }


# 常见厂商的显示名（组头用）。键是反域名里的第二段，小写。
_VENDOR_NAMES = {
    'adobe': 'Adobe', 'google': 'Google', 'microsoft': 'Microsoft',
    'vmware': 'VMware', 'docker': 'Docker', 'homebrew': 'Homebrew',
    'apple': 'Apple', 'tencent': 'Tencent', 'alibaba': 'Alibaba',
    'netease': 'NetEase', 'oray': 'Oray', 'vivo': 'vivo',
    'better365': 'Better365', 'valvesoftware': 'Valve', 'oracle': 'Oracle',
    'proxyman': 'Proxyman', 'netease': 'NetEase', 'jetbrains': 'JetBrains',
}


def group_title(name):
    """组头的显示名：`com.adobe` → `Adobe`，`homebrew.mxcl` → `Homebrew`。

    用户反馈「有一些还是 com.xxx」——分组标题就是最后残留的包名前缀。
    反域名去掉 TLD 段；不是反域名的取第一段。
    """
    g = (name or '').strip()
    if not g:
        return g
    parts = g.split('.')
    if len(parts) >= 2 and parts[0].lower() in (
            'com', 'cn', 'org', 'io', 'net', 'me', 'dev', 'co', 'app'):
        seg = parts[1]
    else:
        seg = parts[0]
    if not seg:
        return g
    return _VENDOR_NAMES.get(seg.lower(), seg[:1].upper() + seg[1:])


def _tree(parent, tk, ttk, cols, widths=None):
    wrap = ttk.Frame(parent)
    wrap.pack(fill='both', expand=True, padx=10, pady=(10, 6))
    # 16px 图标要在行里放得下；默认行高会把它挤扁
    try:
        ttk.Style().configure('Treeview', rowheight=24)
    except Exception:
        pass
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
def norm_columns(columns, widths):
    """列定义兜底。调用方可能显式传 None（`_run_picker` 转发进程选择器时就是），
    少了这一步 `len(widths)` 会直接 TypeError —— 用户开进程选择器时踩到过。
    单独成函数是为了能在无显示环境下单测。
    """
    columns = columns or ('选择', '名称', '说明')
    if not widths or len(widths) != len(columns):
        widths = tuple(560 // max(1, len(columns)) for _ in columns)
    return tuple(columns), tuple(widths)


def pick(rows, title='选择', subtitle='', columns=('选择', '名称', '说明'),
         widths=(70, 340, 480), tabs=None):
    """勾选式选择器。rows 是对象列表，需有 label / detail / frozen / selected。

    `tabs` 为 [(页签名, [行下标])] 或 [(页签名, [行下标], 分组函数)]。
    给了分组函数时按它的返回值分组成可折叠的树：组行可整组勾选，子行各自勾选。

    返回**选中行的下标列表**（只含可选项）；用户取消返回 None。
    系统基础进程与已锁定条目（frozen=True）在点击处理里就直接忽略，
    不只是画成灰的——UI 只是提示，真正的防线仍在 guard/enforce 里。
    """
    if not rows:
        return []
    columns, widths = norm_columns(columns, widths)
    root, tk, ttk = _root(title)

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

    trees = []          # [(tree, [全局下标], 分组函数)]
    for spec in tabs:
        name, idxs = spec[0], list(spec[1])
        group_by = spec[2] if len(spec) > 2 else None
        frame = ttk.Frame(nb)
        nb.add(frame, text='%s（%d）' % (name, len(idxs)))
        if group_by:
            # 分组用树形：#0 是「选择」列（带缩进与展开箭头），勾选仍单独成列。
            # 数据列 = 调用方给的 columns[1:]（启动项是 名称|类型|说明，
            # 进程是 名称|说明）。
            gcols = tuple(columns[1:]) if columns and len(columns) > 1 else ('名称', '说明')
            gws = tuple(widths[1:]) if widths and len(widths) > 1 else \
                tuple(560 // max(1, len(gcols)) for _ in gcols)
            tree = ttk.Treeview(frame, columns=gcols,
                                show='tree headings', selectmode='browse')
            tree.heading('#0', text=(columns[0] if columns else '选择'))
            tree.column('#0', width=(widths[0] if widths else 80),
                        stretch=False, anchor='w')
            for c, w in zip(gcols, gws):
                tree.heading(c, text=c)
                tree.column(c, width=w, stretch=True, anchor='w')
        else:
            tree = ttk.Treeview(frame, columns=columns, show='headings',
                                selectmode='browse')
            ws = widths if len(widths) == len(columns) else \
                tuple(560 // max(1, len(columns)) for _ in columns)
            for c, w in zip(columns, ws):
                tree.heading(c, text=c)
                tree.column(c, width=w, anchor='w', stretch=True)
        vs = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vs.set)
        tree.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=(10, 6))
        vs.pack(side='right', fill='y', pady=(10, 6))
        trees.append((tree, idxs, group_by))

    bot = ttk.Frame(root)
    bot.pack(fill='x', padx=10, pady=(0, 10))
    status_var = tk.StringVar()
    result = {'value': None}
    IMGS = _check_images(tk)
    _MARK_IMG = {'☑': IMGS['on'], '☐': IMGS['off'],
                 '⊘': IMGS['none'], '▣': IMGS['lock']}

    def img_of(r):
        return _MARK_IMG.get(getattr(r, 'mark', ''), IMGS['off'])

    def group_img(kids):
        live = [rows[gi] for gi in kids if not getattr(rows[gi], 'frozen', False)]
        if not live:
            return IMGS['none']
        n = sum(1 for r in live if r.selected)
        if n == 0:
            return IMGS['off']
        if n == len(live):
            return IMGS['on']
        return IMGS['part']

    def detail_of(r):
        tag = getattr(r, 'tag', '') or ''
        detail = getattr(r, 'detail', '') or ''
        return (tag + '  ' + detail) if tag else detail

    def row_values(r):
        # 勾选**单独一列**：用户反馈并进名称里看不明显。
        tag = getattr(r, 'tag', '') or ''
        cells = list(getattr(r, 'cells', None)
                     or [getattr(r, 'label', ''), getattr(r, 'detail', '')])
        if tag:
            cells[-1] = tag + '  ' + cells[-1]
        return tuple([getattr(r, 'mark', '')] + cells)

    def _group_values(r, group, flat=False):
        """分组树里的数据列：短名 + 其余字段。

        启动项有 cells = [名称, 类型, 说明]；进程是 [名称, 说明]。
        `flat=True` 是"只有一个成员的组摊平"，此时没有组前缀可去，用原名。
        """
        cells = list(getattr(r, 'cells', None)
                     or [getattr(r, 'label', ''), getattr(r, 'detail', '')])
        if not flat and hasattr(r, 'short_name'):
            cells[0] = r.short_name(group)
        else:
            cells[0] = getattr(r, 'label', '')
        tag = getattr(r, 'tag', '') or ''
        if tag:
            cells[-1] = tag + '  ' + cells[-1]
        return tuple(cells)

    def match(r, f):
        if not f:
            return True
        return f in (getattr(r, 'label', '') or '').lower() \
            or f in (getattr(r, 'detail', '') or '').lower()

    def group_mark(kids):
        live = [rows[gi] for gi in kids if not getattr(rows[gi], 'frozen', False)]
        if not live:
            return '⊘'
        n = sum(1 for r in live if r.selected)
        if n == 0:
            return '☐'
        if n == len(live):
            return '☑'
        return '◩'                 # 部分选中

    def fill():
        f = filter_var.get().strip().lower()
        for tree, idxs, group_by in trees:
            for iid in tree.get_children(''):
                tree.delete(iid)
            if group_by:
                groups, order = {}, []
                for gi in idxs:
                    r = rows[gi]
                    if not match(r, f):
                        continue
                    g = group_by(r) or '其他'
                    if g not in groups:
                        groups[g] = []
                        order.append(g)
                    groups[g].append(gi)
                for gname in sorted(order, key=lambda x: (x == '其他', x.lower())):
                    kids = groups[gname]
                    if len(kids) == 1:
                        # 只有一个成员的组不值得多一层缩进，直接平铺，
                        # 否则界面会被一堆"组+单个子项"撑成两倍长。
                        gi = kids[0]
                        r = rows[gi]
                        tree.insert('', 'end', iid='r:%d' % gi,
                                    image=img_of(r), text='',
                                    values=_group_values(r, '', flat=True))
                        continue
                    iid = 'g:' + gname
                    tree.insert('', 'end', iid=iid, open=EXPAND_BY_DEFAULT,
                                image=group_img(kids), text='', tags=('grp',),
                                values=('%s（%d）' % (group_title(gname), len(kids)),))
                    for gi in kids:
                        r = rows[gi]
                        tree.insert(iid, 'end', iid='r:%d' % gi,
                                    image=img_of(r), text='',
                                    values=_group_values(r, gname))
            else:
                for gi in idxs:
                    r = rows[gi]
                    if not match(r, f):
                        continue
                    tree.insert('', 'end', iid='r:%d' % gi, image=img_of(r),
                                values=row_values(r)[1:])
        refresh_status()

    def refresh_status():
        n = sum(1 for r in rows if r.selected and not getattr(r, 'frozen', False))
        status_var.set('已选 %d 项' % n)

    def toggle_iid(tree, iid):
        if iid.startswith('g:'):
            kids = [int(x[2:]) for x in tree.get_children(iid)]
            live = [rows[gi] for gi in kids if not getattr(rows[gi], 'frozen', False)]
            if not live:
                return
            want = not all(r.selected for r in live)
            for r in live:
                r.selected = want
        else:
            try:
                gi = int(iid[2:])
            except ValueError:
                return
            r = rows[gi]
            if getattr(r, 'frozen', False):
                return
            r.selected = not r.selected
        fill()

    def on_click(e, tree, cb_col='#1'):
        # 点展开箭头只折叠，不改变勾选
        try:
            if tree.identify_element(e.x, e.y) == 'Treeitem.indicator':
                return
        except Exception:
            pass
        if tree.identify_region(e.x, e.y) not in ('cell', 'tree'):
            return
        # 只有「选择」列（分组时是 #0，平铺时是 #1）响应点击
        if tree.identify_column(e.x) != cb_col:
            return
        iid = tree.identify_row(e.y)
        if iid:
            # ★ **立即生效**，不加任何延迟（用户实测"240ms 都太长"）。
            #   单击与双击靠"点在哪一列"区分：勾选列单击切换；名称/说明列
            #   双击展开折叠分组。手感不能靠等。
            toggle_iid(tree, iid)

    def on_double(e, tree, cb_col):
        """双击名称/说明列 = 展开折叠分组；勾选列不处理。

        勾选列上的双击 = 两次切换（净效果不变），不会误改什么。
        """
        try:
            if tree.identify_column(e.x) == cb_col:
                return 'break'
        except Exception:
            pass
        iid = tree.identify_row(e.y)
        if iid and iid.startswith('g:'):
            tree.item(iid, open=not bool(tree.item(iid, 'open')))
        return 'break'

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

    for tree, _idxs, _gb in trees:
        cb_col = '#0' if _gb else '#1'      # 勾选列：分组树是 #0，平铺是 #1
        try:
            tree.tag_configure('grp', font=('TkDefaultFont', 11, 'bold'))
        except Exception:
            pass
        tree.bind('<Button-1>', lambda e, t=tree, c=cb_col: on_click(e, t, c))
        tree.bind('<space>', lambda e, t=tree: (
            t.selection() and toggle_iid(t, t.selection()[0]), 'break')[1])
        tree.bind('<Double-1>', lambda e, t=tree, c=cb_col: on_double(e, t, c))

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
