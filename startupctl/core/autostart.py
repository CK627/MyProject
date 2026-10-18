# -*- coding: utf-8 -*-
"""开机自启：让监视循环在登录后自动跑起来。

三个平台各用各的注册方式，都**只做用户级**（不需要管理员）：

    macOS    ~/Library/LaunchAgents/cn.ck627.startupctl.watch.plist
             launchctl bootstrap gui/<uid>
    Linux    ~/.config/systemd/user/startupctl-watch.service
             systemctl --user enable --now
    Windows  计划任务 startupctl-watch（登录时触发）
             用 wscript 跑一个隐藏的 .vbs，避免每次登录闪一个黑窗口

`starting` 不带参数 = 看状态（是否注册、循环是否在跑、当前模式）。
"""

import os
import subprocess
import sys

from . import paths
from .utils import getuid, pid_alive

LABEL = 'cn.ck627.startupctl.watch'
PLIST_NAME = LABEL + '.plist'
UNIT_NAME = 'startupctl-watch.service'
TASK_NAME = 'startupctl-watch'


# ---------------------------------------------------------------- 通用
def watch_pid_path():
    return os.path.join(paths.data_root(), 'watch.pid')


def _read_pid():
    try:
        with open(watch_pid_path(), encoding='utf-8') as fh:
            return int(fh.read().strip() or 0) or None
    except (OSError, ValueError):
        return None


def running():
    """监视循环现在是否在跑（pid 存在且进程还活着）。"""
    pid = _read_pid()
    if not pid:
        return None
    return pid if pid_alive(pid) else None


def stop_running(timeout=5.0):
    """停掉正在跑的循环。返回 (是否停掉, 说明)。"""
    pid = running()
    if not pid:
        try:
            os.remove(watch_pid_path())
        except OSError:
            pass
        return False, '监视循环没有在运行'
    try:
        os.kill(pid, 15)         # POSIX: SIGTERM；Windows: TerminateProcess
    except (OSError, SystemError) as e:
        return False, '结束进程失败: %s' % e
    import time
    end = time.time() + timeout
    while time.time() < end:
        if running() is None:
            return True, '已停止监视循环（pid %d）' % pid
        time.sleep(0.2)
    return False, '进程 %d 没有在 %d 秒内退出' % (pid, timeout)


def _run(argv):
    try:
        r = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=15)
        return r.returncode, (r.stdout or b'').decode('utf-8', 'replace')
    except Exception as e:                       # 命令不存在 / 超时
        return 127, str(e)


def _watch_argv():
    """监视循环的启动命令行（绝对路径，登录时 PATH 不可靠）。"""
    py = sys.executable or 'python3'
    if os.name == 'nt':
        pyw = os.path.join(os.path.dirname(py), 'pythonw.exe')
        if os.path.isfile(pyw):
            py = pyw
    return [py, '-B', '-m', 'startupctl', 'watch']


# ---------------------------------------------------------------- macOS
def _plist_path():
    return os.path.join(os.path.expanduser('~'), 'Library', 'LaunchAgents', PLIST_NAME)


def _plist_body():
    args = ''.join('        <string>%s</string>\n' % a for a in _watch_argv())
    log = os.path.join(paths.data_root(), 'watch.log')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n<dict>\n'
        '    <key>Label</key><string>%s</string>\n'
        '    <key>ProgramArguments</key>\n    <array>\n%s    </array>\n'
        '    <key>RunAtLoad</key><true/>\n'
        '    <key>KeepAlive</key><false/>\n'
        '    <key>StandardOutPath</key><string>%s</string>\n'
        '    <key>StandardErrorPath</key><string>%s</string>\n'
        '    <key>EnvironmentVariables</key>\n'
        '    <dict>'
        '<key>PYTHONPATH</key><string>%s</string>'
        '<key>STARTUPCTL_DATA_DIR</key><string>%s</string>'
        '</dict>\n'
        '</dict>\n</plist>\n' % (LABEL, args, log, log, _lib_dir(),
                                   paths.data_root())
    )


def _lib_dir():
    """`python -m startupctl` 需要的 PYTHONPATH。

    安装态：包在 `<安装根>/lib/startupctl` → 用 `<安装根>/lib`。
    仓库态：包就在仓库根 → 用仓库根本身（没有 lib/ 这一层）。
    """
    from .selfmgr import self_info
    _mode, root, _dev = self_info()
    lib = os.path.join(root, 'lib')
    return lib if os.path.isdir(os.path.join(lib, 'startupctl')) else root


# ---------------------------------------------------------------- Linux
def _unit_path():
    return os.path.join(os.path.expanduser('~'), '.config', 'systemd', 'user', UNIT_NAME)


def _unit_body():
    return (
        '[Unit]\nDescription=startupctl watch (startup item / process policy)\n'
        'After=default.target\n\n'
        '[Service]\nType=simple\nExecStart=%s\n'
        'Environment=PYTHONPATH=%s\nEnvironment=STARTUPCTL_DATA_DIR=%s\n'
        'Restart=on-failure\nRestartSec=5\n\n'
        '[Install]\nWantedBy=default.target\n'
        % (' '.join(_watch_argv()), _lib_dir(), paths.data_root())
    )


# ---------------------------------------------------------------- Windows
def _task_xml_or_vbs():
    """计划任务不直接跑 .bat（会闪窗），写一个 .vbs 让 wscript 隐藏启动。"""
    root = os.path.dirname(_lib_dir())
    vbs = os.path.join(root, 'watch-hidden.vbs')
    bat = os.path.join(root, 'bin', 'startupctl.bat')
    body = ('Set sh = CreateObject("WScript.Shell")\r\n'
            'sh.Run """%s"" watch", 0, False\r\n' % bat)
    return vbs, body


# ---------------------------------------------------------------- 对外
def enabled():
    """自启项是否已注册。"""
    if sys.platform == 'darwin':
        return os.path.isfile(_plist_path())
    if os.name == 'nt':
        rc, _out = _run(['schtasks', '/query', '/tn', TASK_NAME])
        return rc == 0
    return os.path.isfile(_unit_path())


def wait_running(timeout=4.0):
    """等一会儿看循环有没有起来（服务管理器是异步启动的）。"""
    import time
    end = time.time() + timeout
    while time.time() < end:
        pid = running()
        if pid:
            return pid
        time.sleep(0.2)
    return None


def status():
    return {
        'enabled': enabled(),
        'pid': running(),
        'pid_file': watch_pid_path(),
    }


def install():
    """注册自启。返回 (ok, 说明)。幂等。"""
    if sys.platform == 'darwin':
        p = _plist_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        paths.ensure_dir(paths.data_root())
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(_plist_body())
        rc, out = _run(['launchctl', 'bootout', 'gui/%d/%s' % (getuid(), LABEL)])
        rc, out = _run(['launchctl', 'bootstrap', 'gui/%d' % getuid(), p])
        if rc != 0:
            # 老系统（< 10.10）没有 bootstrap，退回 load
            rc, out = _run(['launchctl', 'load', '-w', p])
        return (rc == 0), (out.strip() or '已注册 LaunchAgent: %s' % p)

    if os.name == 'nt':
        vbs, body = _task_xml_or_vbs()
        with open(vbs, 'w', encoding='utf-8', newline='') as fh:
            fh.write(body)
        tr = 'wscript.exe "%s"' % vbs
        # /RL HIGHEST：以最高权限运行。Windows 上大量启动项是服务（SYSTEM 身份），
        # 普通令牌结束不了它们——用户实测「明明不是系统项也动不了」就是这个原因。
        rc, out = _run(['schtasks', '/create', '/tn', TASK_NAME, '/tr', tr,
                        '/sc', 'onlogon', '/rl', 'HIGHEST', '/f'])
        if rc == 0:
            _run(['schtasks', '/run', '/tn', TASK_NAME])   # 立即起一次
        return (rc == 0), (out.strip() or '已注册计划任务: %s' % TASK_NAME)

    p = _unit_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(_unit_body())
    _run(['systemctl', '--user', 'daemon-reload'])
    rc, out = _run(['systemctl', '--user', 'enable', UNIT_NAME])
    rc2, out2 = _run(['systemctl', '--user', 'restart', UNIT_NAME])
    ok = (rc == 0 and rc2 == 0)
    return ok, (out + out2).strip() or '已注册 systemd user 单元: %s' % p


def remove():
    """摘除自启（不负责停止正在跑的循环）。返回 (ok, 说明)。"""
    if sys.platform == 'darwin':
        p = _plist_path()
        _run(['launchctl', 'bootout', 'gui/%d/%s' % (getuid(), LABEL)])
        try:
            os.remove(p)
        except OSError:
            return True, '自启项本来就不存在'
        return True, '已移除 LaunchAgent: %s' % p

    if os.name == 'nt':
        rc, out = _run(['schtasks', '/delete', '/tn', TASK_NAME, '/f'])
        try:
            vbs, _body = _task_xml_or_vbs()
            os.remove(vbs)
        except OSError:
            pass
        return True, ('已删除计划任务: %s' % TASK_NAME) if rc == 0 else out.strip()

    p = _unit_path()
    _run(['systemctl', '--user', 'disable', '--now', UNIT_NAME])
    try:
        os.remove(p)
    except OSError:
        return True, '自启项本来就不存在'
    _run(['systemctl', '--user', 'daemon-reload'])
    return True, '已移除 systemd user 单元: %s' % p
