# -*- coding: utf-8 -*-
"""进程选择器：一个可以多选的窗口。

用户要求「需要有一个窗口选择器来选择进程【系统基础进程要禁用不给选择】」。
本模块实现它，并且——**系统基础进程在这里是真的选不了，不是只是显示成灰的**：
`toggle()` 会拒绝任何 `guard.is_protected()` 为真的行。UI 上的灰与 `[系统]` 标记
是提示，真正的防线在 guard.is_protected()，而执行器（enforce.py）动手前会**再查一次**。
两层都要有：只在 UI 拦，策略文件是可以手改的；只在执行器拦，用户会以为自己选中了。

两种实现，自动挑：
  · curses 窗口（POSIX 且有 tty）—— 方向键/空格/jk/筛选，真正的"窗口选择器"
  · 纯文本兜底（Windows 无 stdlib curses、或没有 tty）—— 编号清单 + `1,3,5-8`
两者都走同一份 `Rows` 状态，所以"能不能选"的规则只有一处。
"""
import sys

from . import guard as guard_mod


class Row(object):
    __slots__ = ('proc', 'protected', 'why', 'selected', 'locked')

    def __init__(self, proc, protected, why, selected=False, locked=False):
        self.proc = proc
        self.protected = protected
        self.why = why
        self.selected = selected
        # 锁定 = 用户自己钉住的条目。表现与系统基础进程一样：置灰、选不动。
        # 区别是它能被解锁（按 L），而系统进程永远不行。
        self.locked = locked

    @property
    def frozen(self):
        """选不动：系统基础进程，或已锁定。"""
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
        comm = p.comm or p.program or '?'
        return comm

    @property
    def detail(self):
        p = self.proc
        return '%s  pid=%s  %s' % (p.comm or '?', p.pid, p.program or p.args_str or '')


class Rows(object):
    """选择器的状态。**可选性只由这里决定**，两个 UI 共用。"""

    def __init__(self, procs, platform='', own_pids=(), preselect=None,
                 locked_matcher=None):
        self.platform = platform
        self.rows = []
        for p in sorted(procs, key=lambda x: (x.comm or x.program or '', x.pid)):
            prot, why = guard_mod.is_protected(p, platform, own_pids)
            locked = bool(locked_matcher(p)) if (locked_matcher and not prot) else False
            r = Row(p, prot, why, locked=locked)
            # 锁定必然在集合里（锁定 = "留着它"，不能同时不在清单里）
            if locked:
                r.selected = True
            elif preselect and not prot and p.pid in preselect:
                r.selected = True
            self.rows.append(r)
        self.filter = ''

    def visible(self):
        if not self.filter:
            return list(range(len(self.rows)))
        f = self.filter.lower()
        out = []
        for i, r in enumerate(self.rows):
            hay = '%s %s' % (r.proc.comm or '', r.proc.program or '')
            if f in hay.lower():
                out.append(i)
        return out

    def toggle(self, idx):
        """切换选中。**系统进程与已锁定行都返回 (False, 原因)**——真的拒绝。"""
        r = self.rows[idx]
        if r.protected:
            return False, r.why
        if r.locked:
            return False, '已锁定——先按 L 解锁再改（要删用 guard unlock）'
        r.selected = not r.selected
        return True, ''

    def toggle_lock(self, idx):
        """锁定/解锁。系统进程不可锁定（它本来就动不了）。

        锁定隐含"在集合里"；解锁后仍留在集合里（只是重新可选了），
        要移除得再按空格取消。
        """
        r = self.rows[idx]
        if r.protected:
            return False, r.why
        r.locked = not r.locked
        if r.locked:
            r.selected = True
        return True, ('已锁定: 任何模式下都不结束它' if r.locked else '已解锁')

    def selected_procs(self):
        return [r.proc for r in self.rows if r.selected and not r.protected]

    def locked_procs(self):
        return [r.proc for r in self.rows if r.locked and not r.protected]

    def results(self):
        """返回 [(proc, locked)]：清单最终该长什么样。"""
        return [(r.proc, bool(r.locked)) for r in self.rows
                if (r.selected or r.locked) and not r.protected]

    def counts(self):
        sel = sum(1 for r in self.rows if r.selected and not r.protected)
        prot = sum(1 for r in self.rows if r.protected)
        lock = sum(1 for r in self.rows if r.locked and not r.protected)
        return sel, prot, len(self.rows), lock


# ---------------------------------------------------------------- curses 窗口
def _pick_curses(rows):
    import curses

    def _run(stdscr):
        curses.curs_set(0)
        try:
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)     # 受保护
            curses.init_pair(2, curses.COLOR_GREEN, -1)    # 已选中
            curses.init_pair(3, curses.COLOR_YELLOW, -1)   # 状态/提示
        except Exception:
            pass
        cur = 0
        top = 0
        msg = ('空格=选中/取消 · L=锁定/解锁 · a=全选可选 · n=清空 · '
               '/=筛选 · Enter=确认 · q=取消')
        while True:
            vis = rows.visible()
            if not vis:
                vis = [0] if rows.rows else []
            cur = max(0, min(cur, len(vis) - 1)) if vis else 0
            stdscr.erase()
            h, w = stdscr.getmaxyx()

            sel, prot, total, lock = rows.counts()
            title = ('选择进程 — 共 %d，已选 %d，系统 %d（不可选），锁定 %d'
                     % (total, sel, prot, lock))
            stdscr.addnstr(0, 0, title.ljust(w - 1), w - 1, curses.A_BOLD)
            stdscr.addnstr(1, 0, msg.ljust(w - 1), w - 1)
            if rows.filter:
                stdscr.addnstr(2, 0, ('筛选: ' + rows.filter).ljust(w - 1), w - 1,
                               curses.color_pair(3))
                list_top = 3
            else:
                list_top = 2
            avail = h - list_top - 1
            if cur < top:
                top = cur
            if cur >= top + avail:
                top = cur - avail + 1

            for n, ri in enumerate(vis[top:top + avail]):
                r = rows.rows[ri]
                y = list_top + n
                mark = r.mark
                line = '%s %-28s %s' % (mark, r.label[:28],
                                        (r.proc.program or r.proc.args_str or '')[:max(0, w - 40)])
                if r.protected:
                    attr = curses.A_DIM | curses.color_pair(1)
                elif r.locked:
                    # 锁定行与系统进程一样置灰；用黄色区分"这是你锁的、可以解锁"
                    attr = curses.A_DIM | curses.color_pair(3)
                elif r.selected:
                    attr = curses.color_pair(2)
                else:
                    attr = curses.A_NORMAL
                if top + n == cur:
                    attr |= curses.A_REVERSE
                stdscr.addnstr(y, 0, line.ljust(w - 1), w - 1, attr)

            if rows.rows and rows.rows[vis[cur]].frozen:
                r0 = rows.rows[vis[cur]]
                tip = ('系统基础进程，不可选：' + r0.why) if r0.protected \
                    else '已锁定，选不动（按 L 解锁）'
                stdscr.addnstr(h - 1, 0, tip[:w - 1], w - 1, curses.color_pair(1))
            else:
                stdscr.addnstr(h - 1, 0, ' ' * (w - 1), w - 1)
            stdscr.refresh()

            ch = stdscr.getch()
            if ch in (ord('q'), 27):
                return None
            elif ch in (curses.KEY_UP, ord('k')):
                cur -= 1
            elif ch in (curses.KEY_DOWN, ord('j')):
                cur += 1
            elif ch == curses.KEY_PPAGE:
                cur -= max(1, avail)
            elif ch == curses.KEY_NPAGE:
                cur += max(1, avail)
            elif ch in (curses.KEY_HOME,):
                cur = 0
            elif ch in (curses.KEY_END,):
                cur = len(vis) - 1
            elif ch == ord(' '):
                if vis:
                    rows.toggle(vis[cur])
            elif ch == ord('L'):
                if vis:
                    rows.toggle_lock(vis[cur])
            elif ch == ord('a'):
                for ri in vis:
                    if not rows.rows[ri].protected:
                        rows.rows[ri].selected = True
            elif ch == ord('n'):
                for r in rows.rows:
                    r.selected = False
            elif ch == ord('/'):
                curses.echo()
                stdscr.addnstr(h - 1, 0, '筛选: '.ljust(w - 1), w - 1)
                stdscr.refresh()
                try:
                    s = stdscr.getstr(h - 1, 6, 40).decode('utf-8', 'replace')
                except Exception:
                    s = ''
                curses.noecho()
                rows.filter = s.strip()
                cur = 0
            elif ch in (10, 13, curses.KEY_ENTER):
                return rows.results()
            cur = max(0, min(cur, len(vis) - 1)) if vis else 0

    return curses.wrapper(_run)


def curses_available():
    try:
        import curses                                        # noqa: F401
    except ImportError:
        return False
    try:
        return sys.stdout.isatty() and sys.stdin.isatty()
    except Exception:
        return False


# ---------------------------------------------------------------- 纯文本兜底
def _pick_plain(rows, out=None):
    """编号清单。系统进程与已锁定行**连编号都不给**——这样就没法误选。

    语法：`1,3,5-8` = 选中；编号后加 `!`（如 `2!`）= 选中并**锁定**；
    `all` / `none` / 空行 = 全选 / 清空 / 取消。
    """
    out = out or sys.stdout
    out.write('可选择的进程（编号选择；编号后加 ! 表示锁定，如 2!）\n')
    out.write('  `1,3,5-8` 选中 · `2!` 选中并锁定 · all 全选 · none 清空 · 空行取消\n')
    out.write('=' * 78 + '\n')
    numbered = []
    frozen = []
    for r in rows.rows:
        if r.frozen:
            frozen.append(r)
            continue
        numbered.append(r)
        mark = '[x]' if r.selected else '[ ]'
        out.write('  %3d  %s %-24s %s\n' % (len(numbered), mark, r.label[:24],
                                            (r.proc.program or r.proc.args_str or '')[:40]))
    out.write('\n')
    if frozen:
        prot = [r for r in frozen if r.protected]
        lock = [r for r in frozen if r.locked and not r.protected]
        if lock:
            out.write('以下 %d 个是**你锁定**的条目，选不动（要改先 guard unlock）：\n' % len(lock))
            for r in lock[:20]:
                out.write('  [锁定]  %-24s %s\n' % (r.label[:24],
                                                   (r.proc.program or '')[:40]))
            out.write('\n')
        if prot:
            out.write('以下 %d 个是系统基础进程，**不可选**（不在上面的编号里）：\n' % len(prot))
            for r in prot[:20]:
                out.write('  --    %-26s %s\n' % (r.label[:26], r.why[:40]))
            if len(prot) > 20:
                out.write('  … 另有 %d 个\n' % (len(prot) - 20))
            out.write('\n')
    if not numbered:
        out.write('（没有可选的进程）\n')
        return []

    try:
        raw = input('编号: ').strip()
    except (EOFError, KeyboardInterrupt):
        out.write('\n')
        return None
    if not raw:
        return None
    if raw.lower() == 'none':
        return []
    if raw.lower() == 'all':
        return [(r.proc, False) for r in numbered]
    picked = []
    seen = set()
    bad = []          # 记下看不懂的输入，最后**一起报出来**
    for part in raw.replace(' ', ',').split(','):
        if not part:
            continue
        want_lock = part.endswith('!')
        if want_lock:
            part = part[:-1]
        if '-' in part:
            a, _, b = part.partition('-')
            try:
                lo, hi = int(a), int(b)
            except ValueError:
                bad.append(part)
                continue
            hit = False
            for n in range(lo, hi + 1):
                if 1 <= n <= len(numbered):
                    hit = True
                    if n not in seen:
                        seen.add(n)
                        picked.append((numbered[n - 1].proc, want_lock))
            if not hit:
                bad.append(part)
        else:
            try:
                n = int(part)
            except ValueError:
                bad.append(part)
                continue
            if 1 <= n <= len(numbered):
                if n not in seen:
                    seen.add(n)
                    picked.append((numbered[n - 1].proc, want_lock))
            else:
                bad.append(part)

    # ★ 看不懂的输入一律报出来再返回。静默跳过 = 用户以为选上了、其实没有——
    #   这正是"输入出错导致没起作用"的根源，必须让它出声。
    if bad:
        out.write('\n%s\n' % ('!' * 70))
        out.write('以下输入看不懂或超出范围，**没有生效**（可用编号 1-%d）：\n'
                  % len(numbered))
        out.write('  %s\n' % ', '.join(str(b) for b in bad))
        if not picked:
            out.write('没有任何有效选择 —— 视为取消，策略清单不会改动。\n')
            return None
        out.write('其余 %d 项照常选中。\n' % len(picked))
        out.write('%s\n' % ('!' * 70))
    return picked


# ---------------------------------------------------------------- 入口
def pick(procs, platform='', own_pids=(), preselect=None, locked_matcher=None,
         force_plain=False, force_tui=False, allow_gui=False, note=None):
    """弹出选择器。返回 `[(proc, locked)]`；用户取消返回 None。

    **图形窗口不是常态**：只有 `allow_gui=True`（即显式跑 `guard choose`）才会弹窗。
    其余命令走终端界面/纯文本——一个日常命令突然弹出窗口是很唐突的，
    而且会挡住脚本化使用。

    `allow_gui=True` 时的回退链：**图形窗口 → 终端界面 → 纯文本**，
    每一步不可用都会说明原因（`note` 回调），绝不静默换界面。

    ⚠️ 返回的列表**必定不含系统基础进程**：三道 UI 共用同一份 `Rows`
    （受保护的行在 toggle / toggle_lock 里就被拒），返回前再过一遍 is_protected。
    """
    rows = Rows(procs, platform, own_pids, preselect, locked_matcher=locked_matcher)
    if not rows.rows:
        return []
    note = note or (lambda m: None)

    def _sanitize(picked):
        if picked is None:
            return None
        return [(p, bool(lk)) for (p, lk) in picked
                if not guard_mod.is_protected(p, platform, own_pids)[0]]

    # ---- 1) 图形窗口（只在显式 choose 时）----
    if allow_gui and not force_plain and not force_tui:
        from . import gui as gui_mod
        ok, why = gui_mod.available()
        if ok:
            try:
                return _sanitize(gui_mod.pick(rows, platform, own_pids))
            except gui_mod.GuiUnavailable as e:
                note('图形选择器打不开（%s），改用终端界面' % e)
            except Exception as e:                              # noqa: BLE001
                note('图形选择器出错（%s: %s），改用终端界面' % (type(e).__name__, e))
        else:
            note('图形选择器不可用（%s），改用终端界面' % why)

    # ---- 2) 终端界面 ----
    if not force_plain and curses_available():
        try:
            return _sanitize(_pick_curses(rows))
        except Exception as e:                                  # noqa: BLE001
            note('终端界面出错（%s: %s），改用纯文本' % (type(e).__name__, e))

    # ---- 3) 纯文本兜底 ----
    return _sanitize(_pick_plain(rows))
