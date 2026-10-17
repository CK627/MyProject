# -*- coding: utf-8 -*-
"""进程守护策略：三种模式 + 系统基础进程的硬保护。

**三种模式**（用户要求的形态）：

    off        不干预，只报告（默认）
    deny_all   **全部拒绝**：除系统基础进程外一律结束
    blacklist  黑名单：只结束**被挑中**的那些，其余放行
    whitelist  白名单：只放行**被挑中**的那些，其余结束

    ★ 三种模式**一律保留系统基础进程** —— 没有任何一个模式能杀掉它们。
      「全部拒绝」不是"什么都杀"：它和另外两个模式一样，系统基础进程动不了。
      这不是每个模式各自实现的规则，而是 `verdict()` 里**先于模式判断**的一道硬闸，
      所以将来新增模式也自动继承它。

挑选通过 `core/picker.py` 的窗口选择器完成；**系统基础进程在选择器里不可选**
（见 picker.py），而且——更要紧的是——**在本文件里也不可杀**：UI 只是提示，
真正的防线是 `is_protected()`，它在每一条 kill 路径上都会被调用（见 enforce.py）。

⚠️ 「系统基础进程」的定义必须**往保护那侧倒**：判不准就当作受保护。
   杀错一个用户进程是烦人，杀错 WindowServer / systemd / csrss 是**把机器弄挂**。
   两个方向的代价不对称，所以宁可少杀。

**决策只有一个入口**：`verdict(proc, guard)`。别在别处再写一套 if 判断——
策略与执行分开，才谈得上"预览"（预览就是把 verdict 的结果打出来而不执行）。
"""
import json
import os
from datetime import datetime, timezone

from . import paths

GUARD_NAME = 'guard.json'
SCHEMA_VERSION = 3

MODE_OFF = 'off'
MODE_DENY_ALL = 'deny_all'
MODE_BLACKLIST = 'blacklist'
MODE_WHITELIST = 'whitelist'

MODES = (MODE_OFF, MODE_DENY_ALL, MODE_BLACKLIST, MODE_WHITELIST)

MODE_CN = {
    MODE_OFF: '不干预（只报告）',
    MODE_DENY_ALL: '全部拒绝：除系统基础进程外一律结束',
    MODE_BLACKLIST: '黑名单：只结束挑中的',
    MODE_WHITELIST: '白名单：只放行挑中的（+系统基础进程）',
}

# 判定结果
ALLOW = 'allow'
DENY = 'deny'
PROTECTED = 'protected'

# 匹配方式
LIST_WHITELIST = 'whitelist'
LIST_BLACKLIST = 'blacklist'
LIST_CN = {LIST_WHITELIST: '白名单', LIST_BLACKLIST: '黑名单'}

# ★ 名单的两个维度。
#   启动项是"该不该开机起来"，进程是"现在该不该活着"。Windows 上大量自启
#   根本不出现在启动项列表里（组策略 / 服务 / 注册表 / 启动文件夹各有各的存储），
#   所以只看启动项会漏；反过来只看进程又分不清"这是开机自己起的"还是"你刚手敲的"。
#   两个维度都收，且**互不替代**。
DIM_STARTUP = 'startup'
DIM_PROCESS = 'process'
DIMS = (DIM_STARTUP, DIM_PROCESS)
DIM_CN = {DIM_STARTUP: '启动项', DIM_PROCESS: '进程'}

M_PROC_NAME = 'proc_name'      # 进程名（comm）
M_EXEC_PATH = 'exec_path'      # 可执行文件完整路径
M_EXEC_PREFIX = 'exec_prefix'  # 可执行文件路径前缀
MATCH_KINDS = (M_PROC_NAME, M_EXEC_PATH, M_EXEC_PREFIX)

MATCH_CN = {
    M_PROC_NAME: '进程名',
    M_EXEC_PATH: '可执行文件路径',
    M_EXEC_PREFIX: '可执行文件路径前缀',
}

# ---------------------------------------------------------------- 系统基础进程
# macOS：这些是登录会话 / 桌面赖以存在的东西，杀掉会直接让用户掉出图形界面。
# 清单**刻意短而保守**：只列"杀掉必然出大事"的。宁可漏列（那种进程通常也在
# /System 下、已被路径判据兜住），不可多列。
_DARWIN_CRITICAL = (
    'launchd', 'kernel_task', 'windowserver', 'loginwindow', 'dock', 'finder',
    'systemuiserver', 'coreaudiod', 'notifyd', 'opendirectoryd', 'securityd',
    'configd', 'distnoted', 'cfprefsd', 'runningboardd', 'logind', 'powerd',
    'diskarbitrationd', 'mds', 'mdworker', 'spotlight', 'tccd', 'syspolicyd',
    'endpointsecurityd', 'watchdogd', 'thermalmonitord', 'backboardd',
    'springboard', 'controlcenter', 'notificationcenter', 'universalaccessd',
)

# Windows：会话 0 的核心 + 这些名字的三方不会复用，按名判定是安全的
_WIN_CRITICAL = (
    'system', 'idle', 'registry', 'smss.exe', 'csrss.exe', 'wininit.exe',
    'services.exe', 'lsass.exe', 'winlogon.exe', 'fontdrvhost.exe', 'dwm.exe',
    'svchost.exe', 'explorer.exe', 'sihost.exe', 'ctfmon.exe', 'taskhostw.exe',
    'runtimebroker.exe', 'searchindexer.exe', 'audiodg.exe', 'conhost.exe',
    'memory compression', 'spoolsv.exe', 'lsaiso.exe',
)

# Linux：内核线程 + init 体系
_LINUX_CRITICAL = (
    'systemd', 'init', 'kthreadd', 'kworker', 'ksoftirqd', 'migration',
    'rcu_sched', 'rcu_gp', 'watchdog', 'systemd-journald', 'systemd-udevd',
    'systemd-logind', 'systemd-resolved', 'systemd-networkd', 'dbus-daemon',
    'dbus-broker', 'polkitd', 'udevd', 'rsyslogd', 'crond', 'sshd',
)

# 任何平台上都不该被本工具结束的东西（工具自身的进程树 / 终端）
_SELF_GUARD_NOTE = '本工具自身及其父进程链；结束它等于把自己脚下的地板锯了'

# ---------------------------------------------------------------- 还能操作保障
# ★ 「全部拒绝」模式必须**永远给你留一条能敲命令的路**。
#   否则第一次 arm 下去，shell 和终端一起没了，你连"关掉它"都做不到——
#   一个把自己锁在门外的工具，安全性是负的。
#
# 这些名字一律受保护，**任何模式**下都不会被结束。
# 代价要说清楚：恶意程序若把自己命名成 `bash`，就能躲过这一条。这是**刻意的取舍**——
# 宁可放过一个改名的恶意进程（它还有别的判据可能命中、且用户看得见），
# 也不能让工具把用户锁在门外。真要用全部拒绝模式清场，请先看清 `guard check`。
_SHELL_NAMES = (
    'zsh', 'bash', 'sh', 'fish', 'tcsh', 'csh', 'ksh', 'dash', 'ash', 'nu',
    'elvish', 'xonsh', 'pwsh', 'powershell', 'cmd', 'wsl', 'login', 'sudo', 'su',
)
_TERMINAL_NAMES = (
    'terminal', 'iterm2', 'itermserver', 'itermserver-display', 'wezterm',
    'wezterm-gui', 'alacritty', 'kitty', 'hyper', 'ghostty', 'tabby', 'warp',
    'konsole', 'gnome-terminal', 'xfce4-terminal', 'xterm', 'urxvt', 'st',
    'mate-terminal', 'tilix', 'roxterm', 'terminator', 'qterminal',
    'windowsterminal', 'conhost', 'openconsole', 'mintty',
)
_SESSION_NAMES = (
    'tmux', 'screen', 'sshd', 'sshd-session', 'sshd-auth', 'systemd-logind',
    'loginwindow', 'launchctl', 'systemd', 'systemd-user', 'userinit',
    'explorer', 'dwm', 'winlogon', 'services', 'lsass', 'csrss', 'wininit',
    'ssh-agent', 'gpg-agent', 'gnome-shell', 'plasmashell', 'xfwm4',
)
_SESSION_SAFETY = _SHELL_NAMES + _TERMINAL_NAMES + _SESSION_NAMES


def _system_prefixes(platform):
    if platform == 'darwin':
        return ('/System/', '/usr/libexec/', '/usr/sbin/', '/usr/bin/',
                '/sbin/', '/bin/', '/Library/Apple/')
    if platform == 'win32':
        return ('c:\\windows\\',)
    return ('/lib/systemd/', '/usr/lib/systemd/', '/usr/libexec/', '/sbin/',
            '/usr/sbin/', '/usr/bin/', '/lib/')


def norm_name(name):
    """进程名归一：小写 · 去登录 shell 的前导 '-' · 去 ':...' 后缀 · 去 '.exe'。

    ⚠️ **Windows 的进程名带 .exe**（`cmd.exe` / `powershell.exe` / `conhost.exe`），
       而名表里写的是裸名。不归一的话，在 Windows 上 **shell 与终端一个都匹配不上**：
       `deny_all` 会把 `cmd.exe` 连同用户的终端一起杀掉——用户连"关掉它"都敲不了，
       正是"把自己锁在门外"。本机是 macOS，这条路径永远走不到，只有实测才暴露。

       登录 shell 的 comm 是 `-zsh`，所以要去前导 '-'；`kworker/0:1` 这类在下面另有处理。
    """
    s = (name or '').strip().lower().lstrip('-')
    s = s.split(':')[0].strip()
    if s.endswith('.exe'):
        s = s[:-4]
    return s


_SESSION_SAFETY_NORM = frozenset(norm_name(x) for x in _SESSION_SAFETY)


def _critical_names(platform):
    if platform == 'darwin':
        return _DARWIN_CRITICAL
    if platform == 'win32':
        return _WIN_CRITICAL
    return _LINUX_CRITICAL


def is_protected(proc, platform='', own_pids=()):
    """这个进程是否**绝对不可杀**？返回 (bool, 原因)。

    ★ 这是硬防线，不是 UI 提示。enforce / kill 的**每一条**路径都必须先问它。
      它在两个地方被用到：选择器（让系统进程不可选）与执行器（动手前再查一次）。
      只在选择器里拦是不够的——策略文件是可以手改的。

    判据顺序：自己的进程树 > pid<=1 > 系统账户 > 权威名表 > 系统路径。
    全部走"判不准就当受保护"的方向。
    """
    plat = platform or ''
    pid = getattr(proc, 'pid', None)

    # 1) 本工具自己 + 父进程链：杀了它，watch 循环当场消失（或者更糟：
    #    把自己的 shell 干掉，用户以为机器被搞坏了）
    if own_pids and pid in own_pids:
        return True, '本工具自身的进程链（%s）' % _SELF_GUARD_NOTE

    # 2) pid 0/1：内核与 init/launchd
    if pid is not None and pid <= 1:
        return True, 'pid<=1（内核 / init / launchd）'

    comm = (getattr(proc, 'comm', '') or '').strip()
    low_comm = comm.lower()
    prog = (getattr(proc, 'program', '') or '')

    # 3.5) ★ 还能操作保障：shell / 终端 / 会话。**任何模式下都保护。**
    #      比较用归一后的名字（去前导 '-'、去 ':...'、去 '.exe'）——见 norm_name。
    bare = norm_name(comm)
    if bare in _SESSION_SAFETY_NORM:
        return True, 'shell / 终端 / 会话（保证你还能操作，否则无法改回来）'

    # 3) 系统账户：macOS 的 _windowserver 之类，杀掉会掉图形界面
    user = (getattr(proc, 'user', '') or '')
    if plat == 'darwin' and user.startswith('_'):
        return True, '系统账户 %s' % user

    # 4) 权威名表（短而保守）。两边都归一，Windows 的 .exe 才匹配得上。
    crit = frozenset(norm_name(x) for x in _critical_names(plat))
    if bare in crit:
        return True, '系统基础进程（%s）' % comm
    # kworker/0:1、ksoftirqd/0 这类带实例后缀的
    base = low_comm.split('/')[0]
    if plat not in ('darwin', 'win32') and norm_name(base) in crit:
        return True, '内核线程（%s）' % comm

    # 5) 可执行文件在系统目录
    if prog:
        low_prog = prog.lower().replace('/', '\\') if plat == 'win32' else prog
        for pre in _system_prefixes(plat):
            if low_prog.startswith(pre):
                # Windows 上 C:\Windows\Temp 之类是投放位置，不算系统
                if plat == 'win32' and any(
                        bad in low_prog for bad in ('\\temp\\', '\\tasks\\', '\\debug\\')):
                    continue
                return True, '可执行文件位于系统路径（%s）' % pre

    # 6) 内核线程（Linux）：无可执行文件、也无命令行 —— 判不准就当受保护。
    #
    #    ⚠️ 必须要求 `pid is not None`：这条判据只在**真的从进程表里枚举出来的**
    #    记录上成立。`guard add --value X` 给一个当前没在跑的进程预先立规矩时，
    #    造的是 pid=None 的占位记录（同样没有 program/args），不加这道判断就会
    #    被当成内核线程而**拒绝添加**——在 Linux 上表现为 `guard add` 恒返回 3，
    #    本机（macOS）却复现不了，因为这条规则根本不走 darwin 分支。
    if plat not in ('darwin', 'win32') and pid is not None:
        if not prog and not (getattr(proc, 'args_str', '') or '').strip('[] '):
            return True, '内核线程（无可执行文件与命令行）'

    # 7) 分类结论为系统自带 → 保护
    origin = getattr(proc, 'origin', '')
    if origin == 'os':
        return True, '分类判定为系统自带'

    # 8) ★ "判不准"的收敛版：**root 拥有 + 可执行文件不在用户可写处 +
    #    也不在已知第三方前缀** → 保护。
    #
    #    前一条本来写的是「origin in ('os','unknown') 一律保护」，那太宽了：
    #    实测本机 906 个进程里 808 个落进保护，连用户自己 ~/bin 里的工具都杀不了，
    #    「全部拒绝」就成了废功能。而用户要的是"除了系统的都能管"。
    #
    #    真正需要兜住的是"以 root 跑、又说不清是谁的家伙"——那才可能是系统服务
    #    或厂商守护进程。普通用户拥有的进程，用户本来就有权结束它。
    try:
        uid = getattr(proc, 'uid', None)
    except Exception:
        uid = None
    if uid == 0 and origin == 'unknown':
        low_prog = (prog or '').lower() if plat != 'win32' else (prog or '').lower()
        third = ('/opt/', '/usr/local/', '/applications/', '/library/application support/',
                 '/library/privilegedhelpertools/', 'c:\\program files')
        if not any(t in low_prog for t in third):
            return True, 'root 拥有且出处无法判定（保守起见保护）'

    return False, ''


def _ppid_of(pid):
    """取某个 pid 的父 pid。Linux 走 /proc（零子进程），其余平台走 ps。"""
    try:
        with open('/proc/%d/stat' % pid, 'rb') as fh:
            s = fh.read().decode('utf-8', 'replace')
        # comm 带括号且可能含空格/括号 → 从**最后一个** ')' 切
        close = s.rfind(')')
        return int(s[close + 2:].split()[1])
    except (OSError, ValueError, IndexError):
        pass
    from .utils import run
    r = run(['/bin/ps', '-o', 'ppid=', '-p', str(pid)], timeout=5)
    if not r.ok:
        return None
    try:
        return int(r.out.strip().split()[0])
    except (ValueError, IndexError):
        return None


def own_pid_chain():
    """本工具自身的 pid 与其祖先链 —— 永不结束。

    ⚠️ 必须**跨平台**：早先只读 /proc，而 macOS 上没有 /proc，于是这个集合
    退化成"只有自己"，用户的登录 shell 不再受保护、在选择器里可以被选中。
    在 macOS 上用 ps 回退（与本项目的进程枚举同一套做法）。
    """
    out = set()
    try:
        pid = os.getpid()
        while pid and pid > 1 and len(out) < 32:
            out.add(pid)
            nxt = _ppid_of(pid)
            if not nxt or nxt in out:
                break
            pid = nxt
    except Exception:
        pass
    return out


# ---------------------------------------------------------------- 策略
def _now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class Guard(object):
    """启动项 / 进程的放行策略。

    **模式与选择分开**（用户明确要求）：

        mode        选哪种策略：off / deny_all / blacklist / whitelist
        whitelist   白名单 ─┐
        blacklist   黑名单 ─┘ 两份**各自独立**，互不影响

    每份名单又分**两个维度**（`DIM_STARTUP` / `DIM_PROCESS`）：

        startup     启动项条目（uid + anchor）——"这些允许/禁止开机自启"
        process     进程条目（进程名 / 可执行路径）——"这些允许/禁止活着"

    两个维度**互不替代**：Windows 上组策略、服务、注册表、启动文件夹都能自启，
    只看启动项会漏；而只看进程又分不清"开机自己起的"和"你刚手敲的"。
    判定时两个维度都查，命中任一即算命中（见 `verdict`）。

    哪份名单在起作用由 mode 决定（`active_list_name()`）：

        off        不干预，两份都不用
        deny_all   用 whitelist 作**豁免**（"这些也留着"）
        blacklist  用 blacklist：命中即结束
        whitelist  用 whitelist：只放行命中的

    **锁定的条目在两份名单里都受保护**（锁定 = 别动它，与它在哪份名单无关）。
    """

    def __init__(self, mode=MODE_OFF, whitelist=None, blacklist=None,
                 options=None, path=None):
        self.mode = mode if mode in MODES else MODE_OFF
        self.whitelist = self._norm(whitelist)
        self.blacklist = self._norm(blacklist)
        self.options = dict(options or {})
        self.path = path or os.path.join(paths.data_root(), GUARD_NAME)

    @staticmethod
    def _norm(v):
        """把一份名单规整成 {startup: [], process: []}。

        兼容两种输入：v3 的 dict，以及 v2/更早的**扁平 list**（那时只有进程维度）。
        """
        out = {DIM_STARTUP: [], DIM_PROCESS: []}
        if isinstance(v, dict):
            out[DIM_STARTUP] = list(v.get(DIM_STARTUP) or [])
            out[DIM_PROCESS] = list(v.get(DIM_PROCESS) or [])
        elif isinstance(v, list):
            out[DIM_PROCESS] = list(v)
        return out

    # ---------------- 两份名单 × 两个维度 ----------------
    def lists(self):
        return ((LIST_WHITELIST, self.whitelist), (LIST_BLACKLIST, self.blacklist))

    def entries_of(self, name, dim):
        if name == LIST_WHITELIST:
            return self.whitelist[dim]
        if name == LIST_BLACKLIST:
            return self.blacklist[dim]
        raise ValueError('未知名单: %s' % name)

    def active_list_name(self):
        """当前模式下**起作用**的那份名单；off 返回 ''。"""
        if self.mode == MODE_WHITELIST or self.mode == MODE_DENY_ALL:
            return LIST_WHITELIST
        if self.mode == MODE_BLACKLIST:
            return LIST_BLACKLIST
        return ''

    def active_entries(self, dim):
        n = self.active_list_name()
        return self.entries_of(n, dim) if n else []

    def count(self):
        """(白名单条数, 黑名单条数)，两个维度合计。"""
        return (len(self.whitelist[DIM_STARTUP]) + len(self.whitelist[DIM_PROCESS]),
                len(self.blacklist[DIM_STARTUP]) + len(self.blacklist[DIM_PROCESS]))

    def count_dim(self, name, dim):
        return len(self.entries_of(name, dim))

    # ---------------- 匹配 ----------------
    def _proc_matches(self, e, proc):
        kind = e.get('match')
        val = e.get('value') or ''
        if not val:
            return False
        comm = (getattr(proc, 'comm', '') or '')
        prog = (getattr(proc, 'program', '') or '')
        if kind == M_PROC_NAME:
            return comm == val or os.path.basename(prog) == val
        if kind == M_EXEC_PATH:
            return prog == val
        if kind == M_EXEC_PREFIX:
            return bool(prog) and prog.startswith(val)
        return False

    @staticmethod
    def _startup_matches(e, startup):
        if not startup:
            return False
        if e.get('uid') and startup.get('uid') and e['uid'] == startup['uid']:
            return True
        # uid 会随 UID_VER 演进；anchor（Label / 单元名 / 值名 / 任务路径）是
        # 平台自己的身份，留着它当回退，升级后用户的条目不会静默失配。
        return bool(e.get('anchor')) and e.get('anchor') == startup.get('anchor')

    def matches_in(self, name, proc=None, startup=None):
        """是否命中指定名单（任一维度）。"""
        for e in self.entries_of(name, DIM_PROCESS):
            if proc is not None and self._proc_matches(e, proc):
                return True
        for e in self.entries_of(name, DIM_STARTUP):
            if self._startup_matches(e, startup):
                return True
        return False

    def matches(self, proc, startup=None):
        """是否命中**当前模式起作用的那份**名单。"""
        n = self.active_list_name()
        return self.matches_in(n, proc, startup) if n else False

    def matches_locked(self, proc=None, startup=None):
        """是否命中**任一份名单里已锁定**的条目。

        锁定 = 比普通条目更强的豁免：任何模式下都不结束，且要改必须先解锁。
        故意跨两份名单查：锁定表达的是"别动它"，与它在哪份名单里无关。
        """
        for _name, lists in self.lists():
            for e in lists[DIM_PROCESS]:
                if e.get('locked') and proc is not None and self._proc_matches(e, proc):
                    return True
            for e in lists[DIM_STARTUP]:
                if e.get('locked') and self._startup_matches(e, startup):
                    return True
        return False

    def locked_entries(self):
        out = []
        for name, lists in self.lists():
            for dim in DIMS:
                for e in lists[dim]:
                    if e.get('locked'):
                        out.append((name, dim, e))
        return out

    # ---------------- 决策 ----------------
    def verdict(self, proc, platform='', own_pids=(), startup=None):
        """唯一的决策入口。返回 (action, 原因)。

        `startup` 是这个进程关联到的启动项（dict，含 uid/anchor），没有就传 None。
        两个维度**命中任一即算命中**：白名单里钉了一个启动项，它拉起的进程
        自然该放行；黑名单里钉了一个启动项，它拉起的进程自然该结束。

        action ∈ {protected, allow, deny}。**先问保护，再问锁定，最后才问模式**——
        这个顺序就是"三种模式都保留系统基础进程"与"锁定条目不随模式变化"的实现本身，
        而不是巧合：将来新增模式会自动继承这两条保证。
        """
        protected, why = is_protected(proc, platform, own_pids)
        if protected:
            return PROTECTED, why

        if self.matches_locked(proc, startup):
            return PROTECTED, '已锁定（你钉住的条目，任何模式下都不结束）'

        if self.mode == MODE_OFF:
            return ALLOW, '模式为不干预'

        hit = self.matches(proc, startup)
        if self.mode == MODE_DENY_ALL:
            # 全部拒绝模式下，白名单的作用是**豁免**（"这些也留着"）
            if hit:
                return ALLOW, '在白名单豁免清单中'
            return DENY, '全部拒绝模式：不在豁免清单中'
        if self.mode == MODE_BLACKLIST:
            return (DENY, '命中黑名单') if hit else (ALLOW, '未命中黑名单')
        if self.mode == MODE_WHITELIST:
            return (ALLOW, '命中白名单') if hit else (DENY, '白名单模式：未在放行清单中')
        return ALLOW, '未知模式，按放行处理'

    def ready_to_enforce(self):
        """现在这套策略**真的可以执行**吗？返回 (bool, 原因)。

        「只有选择的时候才生效」——这条就是它的实现：**名单是空的就不许执行**。
        否则白名单模式下"一份空名单"等于"除了系统全杀"，用户什么都没选，
        工具却按最激进的解释动手了。宁可拒绝并让他先去选。

        两个维度**合计**为空才算空：只选了启动项、没选进程，白名单模式照样会
        把没关联到那些启动项的进程全杀掉——那同样不是用户想要的。
        """
        if self.mode == MODE_OFF:
            return False, '模式为「不干预」，不会结束任何进程'
        n = self.active_list_name()
        total = sum(len(self.entries_of(n, d)) for d in DIMS)
        if not total:
            if self.mode == MODE_WHITELIST:
                return False, ('白名单是空的 —— 此时白名单模式等于"除系统外全杀"。'
                               '请先选择: startupctl whitelist')
            if self.mode == MODE_DENY_ALL:
                return True, ('全部拒绝 + 空豁免清单：除系统基础进程外**全部**结束'
                              '（这正是全部拒绝的语义；想留什么请先 startupctl whitelist）')
            return False, ('黑名单是空的 —— 没有要结束的对象。'
                           '请先选择: startupctl blacklist')
        return True, ''

    # ---------------- 变更 ----------------
    def add_startup(self, name, item, reason='', locked=False):
        """往名单的**启动项**维度加一条。item 需有 uid / anchor / kind / scope / name。"""
        entries = self.entries_of(name, DIM_STARTUP)
        uid = getattr(item, 'uid', '') or (item.get('uid') if isinstance(item, dict) else '')
        anchor = getattr(item, 'anchor', '') or (item.get('anchor') if isinstance(item, dict) else '')
        for e in entries:
            if e.get('uid') == uid or (anchor and e.get('anchor') == anchor):
                if locked:
                    e['locked'] = True
                return e
        e = {
            'uid': uid, 'anchor': anchor,
            'kind': getattr(item, 'kind', '') or '',
            'scope': getattr(item, 'scope', '') or '',
            'label': getattr(item, 'name', '') or anchor,
            'reason': reason or '',
            'added': _now(),
            'locked': bool(locked),
        }
        entries.append(e)
        return e

    def add_process(self, name, proc, match=M_PROC_NAME, value=None, reason='', locked=False):
        """往名单的**进程**维度加一条。"""
        if match not in MATCH_KINDS:
            raise ValueError('未知的匹配方式: %s' % match)
        if value is None:
            value = self._default_value(proc, match)
        if not value:
            raise ValueError('无法从该进程推断匹配值')
        entries = self.entries_of(name, DIM_PROCESS)
        for e in entries:
            if e.get('match') == match and e.get('value') == value:
                if locked:
                    e['locked'] = True
                return e
        e = {
            'match': match, 'value': value,
            'reason': reason or '',
            'added': _now(),
            'locked': bool(locked),
            'seen_comm': getattr(proc, 'comm', '') or '',
            'seen_program': getattr(proc, 'program', '') or '',
        }
        entries.append(e)
        return e

    # ---- 进程维度的便捷别名（旧调用点与测试用）----
    def add(self, proc, name=None, match=M_PROC_NAME, value=None,
            reason='', locked=False):
        name = name or self.active_list_name() or LIST_WHITELIST
        return self.add_process(name, proc, match, value, reason, locked)

    def set_locked(self, value, locked=True, name=None):
        names = [name] if name else [LIST_WHITELIST, LIST_BLACKLIST]
        n = 0
        for nm in names:
            for e in self.entries_of(nm, DIM_PROCESS):
                if e.get('value') == value:
                    e['locked'] = bool(locked)
                    n += 1
        return n

    def is_locked_value(self, value):
        for _name, lists in self.lists():
            for e in lists[DIM_PROCESS]:
                if e.get('value') == value:
                    return bool(e.get('locked'))
        return False

    def _default_value(self, proc, match):
        if match == M_PROC_NAME:
            return getattr(proc, 'comm', '') or os.path.basename(
                getattr(proc, 'program', '') or '')
        if match == M_EXEC_PATH:
            return getattr(proc, 'program', '') or ''
        if match == M_EXEC_PREFIX:
            prog = getattr(proc, 'program', '') or ''
            return os.path.dirname(prog) + os.sep if prog else ''
        return ''

    def replace_dim(self, name, dim, entries):
        """整体替换某名单的某个维度。entries 已经是条目 dict。"""
        self.entries_of(name, dim)[:] = list(entries)
        return len(entries)

    def remove_at(self, name, dim, index):
        """按序号删一条（GUI 管理窗口用）。返回被删的条目。"""
        entries = self.entries_of(name, dim)
        if index < 0 or index >= len(entries):
            raise IndexError('序号越界: %s' % index)
        return entries.pop(index)

    def set_locked_at(self, name, dim, index, locked=True):
        entries = self.entries_of(name, dim)
        if index < 0 or index >= len(entries):
            raise IndexError('序号越界: %s' % index)
        entries[index]['locked'] = bool(locked)
        return entries[index]

    def clear(self, name=None, dim=None):
        names = [name] if name else [LIST_WHITELIST, LIST_BLACKLIST]
        dims = [dim] if dim else list(DIMS)
        n = 0
        for nm in names:
            for d in dims:
                entries = self.entries_of(nm, d)
                n += len(entries)
                del entries[:]
        return n

    def set_mode(self, mode):
        if mode not in MODES:
            raise ValueError('未知模式: %s（可选: %s）' % (mode, '|'.join(MODES)))
        self.mode = mode

    # ---------------- 持久化 ----------------
    def load(self):
        p = self.path
        if not p or not os.path.isfile(p):
            return self
        try:
            with open(p, 'r', encoding='utf-8') as fh:
                d = json.load(fh)
            self.mode = d.get('mode') if d.get('mode') in MODES else MODE_OFF
            if 'whitelist' in d or 'blacklist' in d:
                self.whitelist = self._norm(d.get('whitelist'))
                self.blacklist = self._norm(d.get('blacklist'))
            elif 'entries' in d:
                # v1 老格式：一份 entries、含义随模式。迁到**当前模式对应的那份**的
                # 进程维度，而不是丢掉——用户挑过的条目不该因为升级就消失。
                old = list(d.get('entries') or [])
                if self.mode == MODE_BLACKLIST:
                    self.blacklist[DIM_PROCESS] = old
                else:
                    self.whitelist[DIM_PROCESS] = old
            self.options = dict(d.get('options') or {})
        except (OSError, ValueError):
            # 坏文件绝不覆盖（可能是手改错了）：按"不干预"跑，并留痕
            self.mode = MODE_OFF
            self.whitelist = self._norm(None)
            self.blacklist = self._norm(None)
            self._broken = True
        return self

    def save(self):
        d = os.path.dirname(self.path)
        if d:
            paths.ensure_dir(d)
        data = {
            'version': SCHEMA_VERSION,
            'updated': _now(),
            'mode': self.mode,
            'options': self.options,
            'whitelist': self.whitelist,
            'blacklist': self.blacklist,
            '_note': '每份名单分两个维度：startup（启动项）与 process（进程），'
                     '判定时命中任一即算命中。mode 决定用哪份名单：off 不用 · '
                     'deny_all 用 whitelist 作豁免 · blacklist 用 blacklist · '
                     'whitelist 用 whitelist。锁定条目（locked=true）在任何模式下都不结束。',
        }
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)
        return self.path


def load():
    return Guard().load()
