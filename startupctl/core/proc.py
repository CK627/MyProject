# -*- coding: utf-8 -*-
"""进程枚举与「服务的聚合」：把运行中的进程关联回拉起它的启动项。

**关联是尽力而为的连接（best-effort join），不是地面真相。** 这句话必须写进文档
而不只是注释里：手工启的进程没有对应启动项，这应当**可见**（`proc --orphans`）
而不是被隐藏或硬凑一个关联。

四层关联，按权威性排序，每条记录都带 `corr_method` 说明"这是事实还是猜测"：

  1. `launchctl list`（macOS）—— 整表 PID→Label，精确。**实测无需 root**，
     所以系统守护进程也能关联上（只有*变更*才需要 root）。
  2. `/proc/<pid>/cgroup`（Linux）—— 四种里最好的一种。正则一次拿到**所有**进程的
     单元名、零子进程；而且 **cgroup 扛得住 double-fork 与 setsid**，这正是 argv
     匹配会丢失守护进程、而它不会的原因。
  3. 父链回溯 —— `pid → ppid → … → 1`，祖先 program 匹配才关联。
     陷阱：macOS 上 launchd 启的进程 `PPID == 1`，别的 launchd 进程也是，
     所以 `PPID == 1` 本身**毫无信息量**，必须同时有 program 匹配。
  4. 程序路径匹配 —— 两边 realpath。basename 匹配只给 low，**永不用于破坏性决定**。

**明确否决「只按名字匹配」**：两个不相干的工具都可能带一个叫 helper 的进程。
聚合视图里一个自信的错误关联比没有关联更糟——用户分不出来。
"""
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .model import ScanError, scan_error   # noqa: F401  (scan_error 供后端复用)
from .utils import realpath_soft, run

# 内核线程与系统进程的路径前缀（按平台）
_SYS_PREFIX_DARWIN = ('/System/', '/usr/libexec/', '/usr/sbin/', '/usr/bin/',
                      '/sbin/', '/bin/', '/Library/Apple/')
_THIRD_PREFIX_DARWIN = ('/Applications/', '/Library/PrivilegedHelperTools/',
                        '/opt/homebrew/', '/usr/local/',
                        # 用户家目录与 /Library 下的厂商私有目录：都是第三方的地盘。
                        # 少了 /Users/ 会让用户自己的工具落进 unknown（而在 guard 里
                        # unknown 曾经等于"不可杀"，等于用户管不了自己的进程）。
                        '/Users/', '/Library/Application Support/',
                        '/Library/Preferences/')
_SYS_PREFIX_LINUX = ('/lib/systemd/', '/usr/lib/systemd/', '/usr/libexec/',
                     '/sbin/', '/usr/sbin/', '/usr/bin/', '/lib/')
_THIRD_PREFIX_LINUX = ('/opt/', '/usr/local/', '/home/', '/var/lib/')

# Windows 上这组名字是短且封闭的，三方不会复用，所以按名判定是安全的
_WIN_SYSTEM_PROCS = ('system', 'idle', 'registry', 'smss.exe', 'csrss.exe',
                     'wininit.exe', 'services.exe', 'lsass.exe', 'winlogon.exe',
                     'fontdrvhost.exe', 'dwm.exe', 'memory compression')

_CGROUP_UNIT_RE = re.compile(r'([^/\s]+\.(?:service|scope|socket|timer|mount))')


@dataclass
class ProcRecord:
    pid: int = 0
    ppid: int = 0
    uid: Optional[int] = None
    user: str = ''
    program: str = ''          # 可执行路径（真实路径，非 basename）
    comm: str = ''             # 短名
    args_str: str = ''         # ⚠️ 展示用。macOS 上它是空格拼接的字符串，**不可还原 argv**
    cgroup: str = ''           # Linux: /proc/<pid>/cgroup 原文
    scope: str = 'unknown'     # system | user | unknown
    origin: str = 'unknown'    # os | third_party | unknown
    evidence: str = ''
    # 关联结果（由 correlate 填充）
    item_uid: str = ''
    item_key: str = ''
    corr_method: str = ''

    def to_dict(self):
        return dict(pid=self.pid, ppid=self.ppid, uid=self.uid, user=self.user,
                    program=self.program, comm=self.comm, args=self.args_str,
                    scope=self.scope, origin=self.origin, evidence=self.evidence,
                    item_uid=self.item_uid, item_key=self.item_key,
                    corr_method=self.corr_method)


# ---------------------------------------------------------------- 枚举
def enumerate_procs(ctx, backend=None):
    """枚举进程。返回 (procs, errors)。"""
    plat = ctx.platform if ctx else 'linux'
    errors = []
    if plat == 'darwin':
        procs = _procs_posix(platform='darwin')
    elif plat == 'win32':
        procs, werr = _procs_windows()
        errors.extend(werr)
    else:
        procs, perr = _procs_proc()
        if procs is None:
            procs = _procs_posix(platform='linux')
        errors.extend(perr)
    for p in procs:
        classify_proc(p, plat)
    return procs, errors


def _procs_posix(platform='darwin'):
    """`ps` 解析。

    两次调用而不是一次，是为了**避开歧义**：`comm=`（可执行路径）里可能有空格
    （如 "/Applications/Google Chrome.app/..."），若与 args 挤在同一行就没法切分。
       · 第一行集合: pid,ppid,uid,user,stat,comm  —— 用 maxsplit=5，comm 吃掉余下全部
       · 第二行集合: pid,args                        —— 用 maxsplit=1，args 吃掉余下全部
    在 macOS 上**任何"聪明地重新切分 args"都是 bug 工厂**（参数本身含空格）。
    """
    procs = []
    r1 = run(['/bin/ps', '-axo', 'pid=,ppid=,uid=,user=,stat=,comm='], timeout=10)
    if not r1.ok:
        return procs
    for line in r1.out.splitlines():
        parts = line.strip().split(None, 5)
        if len(parts) < 6:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
            uid = int(parts[2])
        except ValueError:
            continue
        comm = parts[5].strip()
        procs.append(ProcRecord(pid=pid, ppid=ppid, uid=uid, user=parts[3],
                                program=comm, comm=os.path.basename(comm),
                                args_str=''))

    # 补 args（纯展示）
    r2 = run(['/bin/ps', '-axo', 'pid=,args='], timeout=10)
    if r2.ok:
        by_pid = dict((p.pid, p) for p in procs)
        for line in r2.out.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) < 2:
                continue
            try:
                pid = int(parts[0])
            except ValueError:
                continue
            p = by_pid.get(pid)
            if p is not None:
                p.args_str = parts[1].strip()
    return procs


def _procs_proc():
    """Linux：走 /proc，**不用 ps**。

    `cmdline` 是 NUL 分隔 → **精确 argv**，零子进程；`cgroup` 同一次遍历顺带拿到。
    """
    import sys
    if not os.path.isdir('/proc'):
        return None, []
    procs = []
    errors = []
    try:
        entries = [e for e in os.listdir('/proc') if e.isdigit()]
    except OSError as e:
        return None, [scan_error('/proc', '/proc', '无法列出 /proc: %s' % e)]

    # hidepid=2 会让别人的 /proc/<pid> 整个不可见，进程列表**静默变成子集**。
    # 必须明说降级，否则用户会把短列表当成完整列表。
    hidden_pid = False
    try:
        with open('/proc/mounts', 'r', encoding='utf-8', errors='replace') as fh:
            for line in fh:
                if ' /proc ' in line and 'hidepid=' in line:
                    m = re.search(r'hidepid=(\d+)', line)
                    if m and int(m.group(1)) >= 2:
                        hidden_pid = True
    except OSError:
        pass
    if hidden_pid:
        errors.append(scan_error('/proc', '/proc',
                                 '挂载了 hidepid>=2，其他用户的进程不可见',
                                 detail='进程列表是子集，不是完整列表'))

    for e in entries:
        base = os.path.join('/proc', e)
        rec = ProcRecord(pid=int(e))
        try:
            with open(os.path.join(base, 'stat'), 'rb') as fh:
                stat = fh.read().decode('utf-8', 'replace')
            # ⚠️ comm 带括号且**自身可能含空格与括号**（如 "(tmux: server)"）→ 从最后一个 ')' 切
            close = stat.rfind(')')
            open_ = stat.find('(')
            if close > open_ >= 0:
                rec.comm = stat[open_ + 1:close]
                rest = stat[close + 2:].split()
                if rest:
                    rec.ppid = int(rest[1]) if len(rest) > 1 else 0
        except (OSError, ValueError, IndexError):
            continue

        try:
            with open(os.path.join(base, 'cmdline'), 'rb') as fh:
                raw = fh.read()
        except OSError:
            raw = b''
        argv = [a.decode('utf-8', 'replace') for a in raw.split(b'\x00') if a]
        # 内核线程：cmdline 为空是最强的判据（比 PPid==2 可靠）
        if not argv:
            rec.scope = 'system'
            rec.origin = 'os'
            rec.evidence = '内核线程（cmdline 为空）'
            rec.program = ''
            rec.args_str = '[%s]' % rec.comm
            procs.append(rec)
            continue
        rec.args_str = ' '.join(argv)
        try:
            rec.program = os.readlink(os.path.join(base, 'exe'))
        except OSError:
            # 非本用户进程 exe 读不到（EACCES）——退回 argv[0]，并如实标注
            rec.program = argv[0]
        rec.comm = rec.comm or os.path.basename(rec.program or '')
        try:
            with open(os.path.join(base, 'cgroup'), 'r', encoding='utf-8',
                      errors='replace') as fh:
                rec.cgroup = fh.read()
        except OSError:
            pass
        try:
            with open(os.path.join(base, 'status'), 'r', encoding='utf-8',
                      errors='replace') as fh:
                for line in fh:
                    if line.startswith('Uid:'):
                        rec.uid = int(line.split()[1])
                        break
        except (OSError, ValueError, IndexError):
            pass
        procs.append(rec)
    return procs, errors


def _procs_windows():
    """Windows：PowerShell CIM 取 JSON。

    不用 `tasklist`：它的输出**本地化**（中文 Windows 上是「映像名称」，列偏移都不同，
    解析必错）。`wmic` 已被 Windows 11 24H2 移除。CIM + ConvertTo-Json 给出精确的
    命令行且不依赖列格式。
    """
    cmd = ('Get-CimInstance Win32_Process | '
           'Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,Name | '
           'ConvertTo-Json -Compress')
    r = run(['powershell', '-NoProfile', '-NonInteractive', '-Command', cmd], timeout=25)
    procs = []
    if not r.ok:
        return procs, [scan_error('win.procs', 'Win32_Process',
                                  'PowerShell 查询失败: %s' % (r.err or r.reason))]
    import json
    try:
        data = json.loads(r.out or '[]')
    except ValueError as e:
        return procs, [scan_error('win.procs', 'Win32_Process', 'JSON 解析失败: %s' % e)]
    if isinstance(data, dict):
        data = [data]
    for d in data:
        try:
            procs.append(ProcRecord(
                pid=int(d.get('ProcessId') or 0),
                ppid=int(d.get('ParentProcessId') or 0),
                program=d.get('ExecutablePath') or '',
                comm=d.get('Name') or '',
                args_str=d.get('CommandLine') or '',
            ))
        except (TypeError, ValueError):
            continue
    return procs, []


# ---------------------------------------------------------------- 分类
def classify_proc(rec, plat):
    """进程的 系统 vs 第三方 判定。

    **关键：启动项的关联结论优先于路径判据。** 因为 `/usr/bin/docker` 既是包管理的
    （路径像系统）又是第三方，此时关联说三方就以三方为准。
    """
    if rec.origin == 'os' and rec.evidence:
        return rec      # 内核线程等已在内核层判过

    prog = rec.program or ''
    low_comm = (rec.comm or '').lower()

    if plat == 'darwin':
        # pid 0/1 永远是系统，不列
        if rec.pid <= 1:
            rec.origin, rec.scope = 'os', 'system'
            rec.evidence = 'pid<=1（内核/launchd）'
            return rec
        # '_' 前缀是 Apple 的系统账户
        if (rec.user or '').startswith('_'):
            rec.origin, rec.scope = 'os', 'system'
            rec.evidence = '系统账户 %s' % rec.user
            return rec
        if prog.startswith(_THIRD_PREFIX_DARWIN):
            rec.origin, rec.scope = 'third_party', 'user'
            rec.evidence = '可执行文件位于第三方安装位置'
            return rec
        if prog.startswith(_SYS_PREFIX_DARWIN):
            rec.origin, rec.scope = 'os', 'system'
            rec.evidence = '可执行文件位于系统路径'
            return rec
        rec.origin, rec.evidence = 'unknown', '路径不在已知的系统或三方位置'
        return rec

    if plat == 'win32':
        if low_comm in _WIN_SYSTEM_PROCS:
            rec.origin, rec.scope = 'os', 'system'
            rec.evidence = 'Windows 核心进程（%s）' % rec.comm
            return rec
        low_prog = prog.lower().replace('/', '\\')
        if low_prog.startswith('c:\\windows\\'):
            rec.origin, rec.scope = 'os', 'system'
            rec.evidence = '可执行文件位于 %SystemRoot% 下'
            return rec
        for p in ('c:\\program files', 'c:\\program files (x86)', 'c:\\users\\',
                  'c:\\programdata\\'):
            if low_prog.startswith(p):
                rec.origin, rec.scope = 'third_party', 'user'
                rec.evidence = '可执行文件位于 %s' % p
                return rec
        rec.origin, rec.evidence = 'unknown', '路径不在已知的系统或三方位置'
        return rec

    # Linux
    if rec.pid <= 1:
        rec.origin, rec.scope = 'os', 'system'
        rec.evidence = 'pid<=1'
        return rec
    if not prog:
        rec.origin, rec.evidence = 'unknown', '无法取得可执行路径'
        return rec
    if prog.startswith(_THIRD_PREFIX_LINUX):
        rec.origin, rec.scope = 'third_party', 'user'
        rec.evidence = '可执行文件位于 /opt 或 /usr/local（本地/三方安装）'
        return rec
    if prog.startswith(_SYS_PREFIX_LINUX):
        rec.origin, rec.scope = 'os', 'system'
        rec.evidence = '可执行文件位于系统路径'
        return rec
    rec.origin, rec.evidence = 'unknown', '路径不在已知的系统或三方位置'
    return rec


# ---------------------------------------------------------------- 关联
def correlate(items, procs, corr_table=None, platform='darwin'):
    """把进程关联回启动项。就地填充 proc 的 item_uid/item_key 与 item 的 pid/proc_state。

    返回 (matched_by_method 统计)。调用方**必须**把"没关联上"如实呈现为
    `--orphans`，而不是让它们凭空消失。
    """
    stats = {}
    by_uid = dict((i.uid, i) for i in items)
    by_anchor = dict((i.anchor, i) for i in items)
    # program realpath → item（路径匹配用）
    by_prog = {}
    for it in items:
        if it.program:
            by_prog.setdefault(realpath_soft(it.program), it)

    corr_table = corr_table or {}
    procs_by_pid = dict((p.pid, p) for p in procs)

    def attach(p, item, method):
        p.item_uid = item.uid
        p.item_key = item.key
        p.corr_method = method
        stats[method] = stats.get(method, 0) + 1
        if item.pid is None:
            item.pid = p.pid
            item.corr_method = method
        else:
            item.related_pids = tuple(list(item.related_pids) + [p.pid])

    # 1) 平台权威表
    for pid, anchor in corr_table.items():
        p = procs_by_pid.get(pid)
        it = by_anchor.get(anchor)
        if p is not None and it is not None:
            attach(p, it, 'launchctl' if platform == 'darwin' else 'service-mgr')

    # 2) cgroup（Linux）
    if platform == 'linux':
        for p in procs:
            if p.item_uid or not p.cgroup:
                continue
            m = _CGROUP_UNIT_RE.search(p.cgroup)
            if not m:
                continue
            unit = m.group(1)
            it = by_anchor.get(unit)
            if it is not None:
                attach(p, it, 'cgroup')

    # 3) 父链回溯（要求祖先 program 匹配——单看 PPID==1 没有信息量）
    for p in procs:
        if p.item_uid:
            continue
        cur, hops = p, 0
        while cur is not None and hops < 12:
            parent = procs_by_pid.get(cur.ppid)
            if parent is None:
                break
            if parent.program:
                it = by_prog.get(realpath_soft(parent.program))
                if it is not None:
                    attach(p, it, 'parent')
                    break
            cur, hops = parent, hops + 1

    # 4) 程序路径匹配
    for p in procs:
        if p.item_uid or not p.program:
            continue
        it = by_prog.get(realpath_soft(p.program))
        if it is not None:
            attach(p, it, 'path')

    # 反向：把没跑起来的项标成 loaded（而不是 running）
    for it in items:
        if it.pid is not None:
            it.proc_state = 'running'
        elif it.enabled is True:
            it.proc_state = 'loaded'
        else:
            it.proc_state = it.proc_state if it.proc_state != 'unknown' else 'unknown'

    return stats


def orphans(procs):
    """没有对应启动项的三方进程——"有人手工把它启起来了"那一批。

    它们**按构造不可关联**，所以必须能被单独列出来（`proc --orphans`），
    而不是混在列表里让人误以为"没有归属的都不重要"。
    """
    return [p for p in procs if not p.item_uid and p.origin == 'third_party']
