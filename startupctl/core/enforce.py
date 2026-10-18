# -*- coding: utf-8 -*-
"""执行器：按 guard 策略结束进程（含"监视新起来的进程"）。

**这是全项目唯一真的会杀进程的地方**，所以规矩比别处更硬：

1. **决策只来自 `guard.verdict()`**，本文件不写任何自己的判据。于是
   "策略是什么"与"怎么执行"分开，预览 (`plan`) 与执行 (`apply`) 共用同一份决策——
   不可能出现"预览说不会杀、执行却杀了"。
2. **动手前再查一次 `is_protected()`**。verdict 已经查过，这里再查一次是因为
   `plan` 与 `apply` 之间隔着时间（预览 → 用户确认 → 执行），进程表会变，
   而**别人可以手改 guard.json**。纵深防御在这里不是重复，是必须的。
3. **默认预览**。`arm()` 不带 `enforce=True` 只打印计划。
4. **TERM 优先**（给它机会收尾），超时才 KILL。
5. **绝不使用 sudo**：结束 root 进程会被拒绝并提示，而不是偷偷提权。
   在一个自动循环里提权 = 让工具替用户做它没批准的破坏。

⚠️ 「全部拒绝」模式会拒绝**任何**新起的非系统进程——包括你自己刚敲的那些命令。
   所以 `watch` 必须由用户显式启动（`guard arm --watch`），而且要能随时 Ctrl-C 停。
   这是它的设计意图（"保证一个开机启动的干净"），但它也确实会挡住你干活，
   这一点必须在使用前讲清楚，而不是等用户发现。
"""
import os
import signal
import sys
import time

from . import guard as guard_mod
from . import proc as proc_mod
from .guard import ALLOW, DENY, PROTECTED
from .utils import realpath_soft


class Decision(object):
    __slots__ = ('proc', 'action', 'reason')

    def __init__(self, proc, action, reason):
        self.proc = proc
        self.action = action
        self.reason = reason

    def __repr__(self):
        return '<Decision %s pid=%s %s>' % (self.action, self.proc.pid, self.reason)


def decide(procs, guard, platform='', own_pids=None, items_by_uid=None):
    """对一批进程给出决策。返回 (to_deny, to_protect, to_allow)。

    `items_by_uid` 是 {uid: 启动项}。进程由 `proc.correlate()` 填好 `item_uid` 后，
    这里把它翻译成"这个进程属于哪个启动项"，再交给 guard.verdict——于是名单里的
    **启动项维度**也能参与决策：钉住一个启动项，它拉起的进程同样受放行/结束约束。
    关联不上就传 None，退回纯进程维度的判断。
    """
    if own_pids is None:
        own_pids = guard_mod.own_pid_chain()
    deny, protect, allow = [], [], []
    for p in procs:
        startup = None
        uid = getattr(p, 'item_uid', None)
        if uid and items_by_uid:
            it = items_by_uid.get(uid)
            if it is not None:
                startup = {'uid': it.uid, 'anchor': it.anchor}
        action, why = guard.verdict(p, platform, own_pids, startup)
        d = Decision(p, action, why)
        if action == DENY:
            deny.append(d)
        elif action == PROTECTED:
            protect.append(d)
        else:
            allow.append(d)
    return deny, protect, allow


def plan(procs, guard, platform='', items_by_uid=None):
    """预览：返回 (要结束的决策列表, 受保护列表, 放行列表)。**不改动任何东西。**"""
    return decide(procs, guard, platform, items_by_uid=items_by_uid)


def format_plan(deny, protect, allow, guard, platform='', limit=25):
    lines = []
    lines.append('模式: %s' % guard_mod.MODE_CN.get(guard.mode, guard.mode))
    if guard.mode == guard_mod.MODE_OFF:
        lines.append('  当前模式为「不干预」：本工具不会结束任何进程。')
        lines.append('  改模式: startupctl mode deny_all|blacklist|whitelist')
    locked_n = len(guard.locked_entries())
    wl_n, bl_n = guard.count()
    act = guard.active_list_name()
    from . import guard as _gm
    lines.append('模式 / 清单: %s · 起作用的是 %s'
                 % (_gm.MODE_CN.get(guard.mode, guard.mode),
                    _gm.LIST_CN.get(act, '（无——off 模式）')))
    lines.append('清单: 白名单 %d 条 · 黑名单 %d 条%s'
                 % (wl_n, bl_n,
                    '（其中锁定 %d 条——任何模式下都不结束）' % locked_n if locked_n else ''))
    ready, why = guard.ready_to_enforce()
    if not ready:
        lines.append('⚠️  还不能执行: %s' % why)
    lines.append('进程总计: %d（将结束 %d · 受保护 %d · 放行 %d）'
                 % (len(deny) + len(protect) + len(allow), len(deny), len(protect), len(allow)))
    if protect:
        # 受保护里有一部分是"还能操作保障"（shell/终端/会话），说明白让人放心，
        # 也让人知道全部拒绝模式不会把他锁在门外。
        sess = [d for d in protect if '还能操作' in d.reason]
        if sess:
            lines.append('  其中 %d 个是 shell / 终端 / 会话——'
                         '**保证你还能操作**，任何模式下都不结束' % len(sess))
    if deny:
        lines.append('')
        lines.append('将要结束（%d）:' % len(deny))
        for d in deny[:limit]:
            lines.append('  · %-26s pid=%-7s %s' % (
                (d.proc.comm or '?')[:26], d.proc.pid, d.reason))
        if len(deny) > limit:
            lines.append('  … 另有 %d 个' % (len(deny) - limit))
    if protect:
        lines.append('')
        lines.append('受保护、**任何模式都不会结束**（%d，只列前 %d）:'
                     % (len(protect), min(len(protect), 8)))
        for d in protect[:8]:
            lines.append('  · %-26s pid=%-7s %s' % (
                (d.proc.comm or '?')[:26], d.proc.pid, d.reason))
    return lines


# ★ Windows 没有 signal.SIGKILL。直接引用会让"TERM 没杀掉"的那条路径
#   抛 AttributeError（用户真机踩到）。Windows 上任意信号号都会走 TerminateProcess，
#   所以 9 就是硬杀。
_SIGTERM = getattr(signal, 'SIGTERM', 15)
_SIGKILL = getattr(signal, 'SIGKILL', 9)


def apply_decisions(deny, guard, term_first=True, grace=3.0, out=None):
    """真的结束进程。返回 (成功数, 失败数, 跳过的受保护数)。

    ⚠️ 调用方必须先让用户确认过（见 cli 的 guard arm / guard enforce）。
    """
    if os.name == 'nt':
        # 结束 SYSTEM 服务前先把 SeDebugPrivilege 打开（管理员令牌默认不启用它）。
        from .utils import enable_debug_privilege
        enable_debug_privilege()
    out = out or sys.stdout
    if out is None:
        # pythonw / 计划任务里没有 stdout：直接 write 会 AttributeError，
        # 而这恰好发生在"已经杀了进程、正要报告"的时刻。
        import io as _io
        out = _io.StringIO()
    ok = fail = refused = 0
    platform = _platform_for(guard)
    for d in deny:
        p = d.proc
        # ★ 动手前再查一次：预览到执行之间进程表会变，guard.json 也可能被人改过
        prot, why = guard_mod.is_protected(p, platform, guard_mod.own_pid_chain())
        if prot:
            out.write('  跳过 pid=%s（%s）：%s\n' % (p.pid, p.comm, why))
            refused += 1
            continue
        try:
            if term_first:
                os.kill(p.pid, _SIGTERM)
                deadline = time.time() + grace
                while time.time() < deadline:
                    if not _alive(p.pid):
                        break
                    time.sleep(0.15)
                if _alive(p.pid):
                    os.kill(p.pid, _SIGKILL)
                    out.write('  已结束 pid=%-7s %s（先 TERM 未退出，已 KILL）\n'
                              % (p.pid, p.comm))
                else:
                    out.write('  已结束 pid=%-7s %s（TERM）\n' % (p.pid, p.comm))
            else:
                os.kill(p.pid, _SIGKILL)
                out.write('  已结束 pid=%-7s %s（KILL）\n' % (p.pid, p.comm))
            ok += 1
        except ProcessLookupError:
            ok += 1                      # 已经自己退了，算成功
        except PermissionError:
            out.write('  跳过 pid=%-7s %s：权限不足（属于其他用户/root；'
                      '本工具不会为此提权）\n' % (p.pid, p.comm))
            fail += 1
        except OSError as e:
            out.write('  失败 pid=%-7s %s: %s\n' % (p.pid, p.comm, e))
            fail += 1
    return ok, fail, refused


def _platform_for(guard):
    from . import roots as roots_mod
    return roots_mod.platform_key()


def _alive(pid):
    # ★ 不能直接 os.kill(pid, 0)：Windows 上那是 TerminateProcess(0)，会真的杀掉进程。
    from .utils import pid_alive
    return pid_alive(pid)


def enforce_once(ctx, guard, out=None, term_first=None):
    """扫一次进程表 → 决策 → 执行。返回 (ok, fail, refused, deny_count)。"""
    out = out or sys.stdout
    if term_first is None:
        term_first = bool(ctx.conf.get('TERM_FIRST', True))
    procs, _errs = proc_mod.enumerate_procs(ctx, ctx.backend)
    # 先分类，否则 is_protected 的第 7 条判据（origin）拿不到值
    for p in procs:
        proc_mod.classify_proc(p, ctx.platform)
    deny, protect, allow = decide(procs, guard, ctx.platform)
    if not deny:
        return 0, 0, 0, 0
    ok, fail, refused = apply_decisions(deny, guard, term_first=term_first, out=out)
    return ok, fail, refused, len(deny)


def watch(ctx, guard, interval=2.0, out=None, max_rounds=None, term_first=None):
    """持续监视：按策略结束**新起来的**进程。

    这是「全部拒绝」模式真正落地的地方——启动项清干净之后，还得有个东西盯着
    "谁又偷偷起来了"。Ctrl-C 停。

    ⚠️ 它会拒绝任何新起的非系统进程，**包括用户自己刚敲的命令**。所以：
      · 必须由用户显式启动；
      · 每轮都打印统计，让人看得见它在干什么；
      · 绝不提权。
    """
    out = out or sys.stdout
    rounds = 0
    total_ok = total_fail = total_refused = 0
    out.write('开始监视（间隔 %.1fs，模式 %s）。Ctrl-C 停止。\n'
              % (interval, guard_mod.MODE_CN.get(guard.mode, guard.mode)))
    try:
        while True:
            ok, fail, refused, n = enforce_once(ctx, guard, out=out, term_first=term_first)
            rounds += 1
            total_ok += ok
            total_fail += fail
            total_refused += refused
            if n == 0:
                out.write('  [第 %d 轮] 无需要结束的进程\n' % rounds)
            out.flush()
            if max_rounds is not None and rounds >= max_rounds:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        out.write('\n已停止监视。\n')
    out.write('共 %d 轮：结束 %d · 失败 %d · 因保护跳过 %d\n'
              % (rounds, total_ok, total_fail, total_refused))
    return total_ok, total_fail
