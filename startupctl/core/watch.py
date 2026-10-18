# -*- coding: utf-8 -*-
"""监视循环：按当前模式持续检查，出现该结束的进程就结束它。

用户的要求是「开启黑名单模式，自动开始检测进程，如果进程出现黑名单选择的东西，
那么就清理，启动项也是」。启动项的清理在这里表现为**结束它拉起的进程**——
2.0 起本工具不再改动启动项文件（那是用户明确砍掉的功能）。

安全约束（一条都不能少）：

  1. **先问保护，再问模式**——全部复用 `guard.verdict()`，与单次执行同一条路径。
     系统基础进程、shell / 终端 / 会话永远不动。
  2. **模式为 off 或名单为空时不动手**，只记一行日志。`ready_to_enforce()` 是闸。
  3. **每轮重新加载策略文件**：用户在另一个终端改了名单，下一轮就生效。
  4. **自己与父进程链永远受保护**（`guard.own_pid_chain()`）。
  5. 结束进程仍走 `enforce.apply_decisions()`（TERM 优先、带宽限）。

运行痕迹：`<数据根>/watch.pid`（单实例）与 `<数据根>/watch.log`（追加）。
"""

import os
import signal
import sys
import time

from . import context, enforce, paths
from . import guard as guard_mod
from . import proc as proc_mod

_STOP = {'flag': False}


def _now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def log(msg, also_stdout=None):
    """写一行日志。

    `also_stdout=None` 表示"只有前台（交互终端）才同时打印"。launchd / systemd
    已经把 stdout 重定向到同一个 watch.log，无条件 print 会让每行都出现两次。
    """
    if also_stdout is None:
        try:
            also_stdout = sys.stdout.isatty()
        except Exception:
            also_stdout = False
    line = '[%s] %s' % (_now(), msg)
    try:
        paths.ensure_dir(paths.data_root())
        with open(os.path.join(paths.data_root(), 'watch.log'), 'a', encoding='utf-8') as fh:
            fh.write(line + '\n')
    except OSError:
        pass
    if also_stdout:
        try:
            print(line, flush=True)
        except Exception:
            pass


def _on_signal(signum, _frame):
    _STOP['flag'] = True


def _scan_once(ctx, guard):
    """跑一轮：返回本轮结束的进程数。"""
    res = ctx.scan(force=True)
    items = list(res.items)
    procs, _errs = proc_mod.enumerate_procs(ctx, ctx.backend)
    for p in procs:
        proc_mod.classify_proc(p, ctx.platform)
    procs = [p for p in procs if p.pid > 1]
    try:
        table = ctx.backend.corr_table(ctx)
    except Exception:
        table = {}
    proc_mod.correlate(items, procs, table, ctx.platform)
    by_uid = dict((i.uid, i) for i in items)
    deny, _protect, _allow = enforce.plan(procs, guard, ctx.platform,
                                          items_by_uid=by_uid)
    if not deny:
        return 0
    # 只说「命中」不说「结束」：权限不足时结束不了（SYSTEM 服务、别的用户的进程），
    # 预先写「结束」就是在日志里谎报。成没成由下面这行汇总。
    for d in deny[:20]:
        log('命中 %s (pid=%s) — %s' % (d.proc.comm or '?', d.proc.pid, d.reason))
    ok, fail, refused = enforce.apply_decisions(deny, guard, term_first=True)
    log('本轮：结束 %d · 权限不足/失败 %d · 跳过（受保护）%d' % (ok, fail, refused),
        also_stdout=False)
    return ok


def run(interval=None, max_rounds=None):
    """前台跑监视循环。返回退出码。"""
    from . import config as config_mod
    conf = config_mod.load()
    if interval is None:
        interval = conf.getint('WATCH_INTERVAL') or 5
    interval = max(1, int(interval))

    pid_path = os.path.join(paths.data_root(), 'watch.pid')
    paths.ensure_dir(paths.data_root())
    # 单实例：launchd 重载、用户手滑、计划任务重叠时都可能起出第二个循环。
    # 两个循环同时杀进程既是双倍动作，也让「谁停了我」无从判断。
    try:
        with open(pid_path, encoding='utf-8') as fh:
            other = int((fh.read().strip() or '0'))
    except (OSError, ValueError):
        other = 0
    if other and other != os.getpid():
        from .utils import pid_alive
        if pid_alive(other):
            log('已有监视循环在跑（pid %d），本进程退出' % other, also_stdout=False)
            return 0
        # 陈旧 pid 文件：直接接管
    try:
        with open(pid_path, 'w', encoding='utf-8') as fh:
            fh.write(str(os.getpid()))
    except OSError as e:
        log('无法写 pid 文件: %s' % e, also_stdout=False)
        return 1

    for sig in (getattr(signal, 'SIGTERM', None), getattr(signal, 'SIGINT', None)):
        if sig is not None:
            try:
                signal.signal(sig, _on_signal)
            except Exception:
                pass

    log('监视循环启动 pid=%d 间隔=%ds' % (os.getpid(), interval))
    ctx = context.Ctx(conf=conf)
    rounds = 0
    last_note = ''
    try:
        while not _STOP['flag']:
            rounds += 1
            g = guard_mod.load()          # 每轮重读：用户改了名单下一轮生效
            note = ''
            if g.mode == guard_mod.MODE_OFF:
                note = '模式为不干预，跳过'
            else:
                ready, why = g.ready_to_enforce()
                if not ready:
                    note = '还不能执行: %s' % why
            if note:
                if note != last_note:      # 同一个原因只记一次，别刷屏
                    log(note, also_stdout=False)
                    last_note = note
            else:
                last_note = ''
                try:
                    _scan_once(ctx, g)
                except Exception as e:
                    log('本轮出错: %s: %s' % (type(e).__name__, e), also_stdout=False)
            if max_rounds is not None and rounds >= max_rounds:
                break
            # 分段睡，收到信号能及时退出
            for _ in range(interval * 10):
                if _STOP['flag']:
                    break
                time.sleep(0.1)
    finally:
        try:
            if os.path.isfile(pid_path):
                with open(pid_path, encoding='utf-8') as fh:
                    if fh.read().strip() == str(os.getpid()):
                        os.remove(pid_path)
        except OSError:
            pass
        log('监视循环退出 pid=%d' % os.getpid())
    return 0


def start_detached():
    """在后台起一个监视循环（`starting true` 用）。返回 (ok, 说明)。

    已经在跑就不再起第二个（单实例靠 watch.pid）。
    """
    from . import autostart
    if autostart.running():
        return True, '监视循环已在运行（pid %d）' % autostart.running()
    argv = [sys.executable or 'python3', '-B', '-m', 'startupctl', 'watch']
    logpath = os.path.join(paths.data_root(), 'watch.log')
    paths.ensure_dir(paths.data_root())
    try:
        out = open(logpath, 'a', encoding='utf-8')
    except OSError:
        out = subprocess_devnull()
    kwargs = {}
    if os.name == 'nt':
        kwargs['creationflags'] = 0x00000008 | 0x00000200   # DETACHED | NEW_GROUP
    else:
        kwargs['start_new_session'] = True
    env = dict(os.environ)
    env['PYTHONPATH'] = autostart._lib_dir() + os.pathsep + env.get('PYTHONPATH', '')
    try:
        import subprocess
        p = subprocess.Popen(argv, stdout=out, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, env=env, **kwargs)
    except Exception as e:
        return False, '启动监视循环失败: %s' % e
    return True, '已在后台启动监视循环（pid %d）' % p.pid


def subprocess_devnull():
    import subprocess
    return open(os.devnull, 'w')
