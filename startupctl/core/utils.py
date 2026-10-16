# -*- coding: utf-8 -*-
"""外部命令调用的**唯一**包装（超时 · 不抛异常 · 结构化失败原因）。

为什么必须统一走这里：本工具要调 `launchctl` / `ps` / `plutil` / `systemctl` /
`osascript` / `sc` / `schtasks` / `powershell` 等一堆系统命令，而它们的失败形态是
**四类**，混在一起就没法给用户有用的提示：

  · 命令不存在（老系统 / 精简镜像 / PATH 异常）
  · 超时（`ps` 卡在挂死的 NFS 上、`sfltool` 卡在等人点授权框）
  · 权限不足（读别人的 crontab、`systemctl --user` 连不上 bus）
  · 命令跑了但报错（参数不对、服务不存在）

若各处直接 `subprocess.run` 且不设 timeout，一次挂死就是**工具整个卡住**——
用户看到的是"startupctl 没反应"，无从排查。所以：

  ⚠️ 一律 `timeout=`，且**绝不向外抛**：失败返回 `CmdResult(ok=False, reason=...)`，
     由调用方决定是跳过该项、还是记成 ScanError（见 model.ScanError）。

3.8 兼容：不用 `subprocess.run(capture_output=)` 之外的新特性，不用 `:=`。
"""
import os
import shutil
import subprocess
import sys

# 语义化的失败原因。调用方按它决定输出文案与退化路径。
REASON_OK = ''
REASON_MISSING = 'missing'      # 命令不存在
REASON_TIMEOUT = 'timeout'      # 超时被杀（可能挂死）
REASON_DENIED = 'denied'        # 权限不足
REASON_ERROR = 'error'          # 跑了但非零退出
REASON_UNSUPPORTED = 'unsupported'  # 本平台没有这个概念


class CmdResult(object):
    """一次外部命令调用的结果。永不抛异常，失败信息都在字段里。"""

    __slots__ = ('argv', 'rc', 'out', 'err', 'reason')

    def __init__(self, argv, rc, out='', err='', reason=REASON_OK):
        self.argv = argv
        self.rc = rc
        self.out = out
        self.err = err
        self.reason = reason

    @property
    def ok(self):
        return self.reason == REASON_OK and self.rc == 0

    @property
    def unavailable(self):
        """命令根本没能给我们有效信息（不存在 / 超时 / 权限不足）。"""
        return self.reason in (REASON_MISSING, REASON_TIMEOUT, REASON_DENIED)

    def lines(self):
        return [ln for ln in self.out.splitlines()]

    def __repr__(self):
        return '<CmdResult rc=%s reason=%r argv=%r>' % (self.rc, self.reason, self.argv)


def _classify_denied(err_text):
    """把各语言的权限报错归一。宁可漏判成 error，也不要误判成 denied——
    误判会让用户以为"加 sudo 就行"，而实际上加了也没用。"""
    low = (err_text or '').lower()
    needles = (
        'permission denied', 'operation not permitted', 'access is denied',
        'not permitted', 'must be root', 'requires root', 'are you root',
        'failed to connect to bus', 'not authorized', 'authorization denied',
        '拒绝访问', '权限不足', '不允许',
    )
    for n in needles:
        if n in low:
            return True
    return False


def run(argv, timeout=10, input_text=None, env=None):
    """跑一条外部命令。**永不抛异常**，失败以 CmdResult.reason 表达。

    timeout 默认 10 秒：卡住的 NFS 挂载能让 `ps` 无限挂起，而枚举进程这条路上
    任何一次挂起都会让整个工具看起来是坏的。
    """
    if not argv:
        return CmdResult(argv, -1, reason=REASON_ERROR)
    exe = argv[0]
    if os.path.sep not in exe and shutil.which(exe) is None:
        return CmdResult(argv, -1, err='命令不存在: %s' % exe, reason=REASON_MISSING)

    kwargs = {}
    if sys.version_info[0] == 3:
        kwargs['stdin'] = subprocess.PIPE if input_text is not None else subprocess.DEVNULL
    try:
        p = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            **kwargs
        )
    except (OSError, ValueError) as e:
        return CmdResult(argv, -1, err=str(e), reason=REASON_MISSING)

    try:
        out_b, err_b = p.communicate(
            input=input_text.encode('utf-8') if input_text is not None else None,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        # 超时必须杀掉子进程，否则它会一直挂着（并可能拖着管道不放）
        try:
            p.kill()
            p.communicate(timeout=5)
        except Exception:
            pass
        return CmdResult(argv, -1, err='命令超时（%ss）: %s' % (timeout, ' '.join(argv)),
                         reason=REASON_TIMEOUT)

    out = _decode(out_b)
    err = _decode(err_b)
    rc = p.returncode
    if rc == 0:
        return CmdResult(argv, 0, out, err, REASON_OK)
    reason = REASON_DENIED if _classify_denied(err) else REASON_ERROR
    return CmdResult(argv, rc, out, err, reason)


def _decode(raw):
    """系统命令输出解码。用 replace 而不是严格模式：一个坏字节不该让整条命令的结果作废。"""
    if raw is None:
        return ''
    if isinstance(raw, str):
        return raw
    for enc in ('utf-8', 'gbk', 'latin-1'):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('utf-8', 'replace')


def which(name):
    return shutil.which(name)


def is_admin():
    """当前是否 root / 管理员。

    ⚠️ 这个值**只用来决定"要不要如实告诉用户需要提权"**，绝不用来放宽任何安全判定。
    """
    if os.name == 'nt':
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False


def home_dir():
    return os.path.expanduser('~')


def realpath_soft(path):
    """realpath，但路径不存在时返回原值而不是抛异常。

    关联进程与启动项时要 realpath 两边（解析符号链接），可执行文件可能已被删掉
    （升级中的二进制），此时 `os.path.realpath` 仍能返回一个字符串，但防御一下更稳。
    """
    if not path:
        return path
    try:
        return os.path.realpath(path)
    except (OSError, ValueError):
        return path
