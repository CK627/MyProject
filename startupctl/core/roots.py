# -*- coding: utf-8 -*-
"""扫描根表：所有"去哪儿找启动项"都从这里取，**后端绝不硬编码路径**。

为什么要有这一层（不是为了好看，是三条硬需求）：

1. **可测**：`STARTUPCTL_ROOTS=<dir>` 把所有根重映射到该目录下（逻辑名作相对路径），
   于是 CI 能在 ubuntu/macos/windows 上跑通全流程，而**不读真机、不动真机**。
   没有这个接缝，安全不变量测试就只能靠"希望它没真跑"，而那证明不了任何事。
2. **可审**：后端问 `ctx.roots['darwin.daemons']`，硬编码就是在 review 里一眼可见。
   重映射只发生在本文件一处，多一处拼路径就多一个隔离漏洞。
3. **可扩**：新平台/新根只改这张表。

对应测试：安全不变量第 12 条断言「不设 STARTUPCTL_ROOTS 时，输出里不得出现夹具树
之外的路径」——它是前 11 条可信的前提。少了它，一个"因为静默扫了 ~/Library 而不是
夹具"而通过的套件，看起来与正确的一模一样。
"""
import os

ROOTS_ENV = 'STARTUPCTL_ROOTS'

# 逻辑名 → 绝对路径（'~' 开头表示相对登录用户家目录，由 expand 展开）
DEFAULTS = {
    'darwin': {
        # 系统自带（SIP 保护，本来也改不动，但必须列出来才能"看全"）
        'darwin.sys.daemons': '/System/Library/LaunchDaemons',
        'darwin.sys.agents': '/System/Library/LaunchAgents',
        # 第三方安装位置
        'darwin.daemons': '/Library/LaunchDaemons',
        'darwin.agents': '/Library/LaunchAgents',
        'darwin.user.agents': '~/Library/LaunchAgents',
        # 遗留（macOS 27 上 SystemStarter 早已移除，仅作信息展示）
        'darwin.startupitems': '/Library/StartupItems',
        'darwin.sys.startupitems': '/System/Library/StartupItems',
        # BTM（登录项与扩展的权威来源）
        'darwin.btm': '/private/var/db/com.apple.backgroundtaskmanagement',
        # 系统 cron 的 spool（他人 tab 需 root）
        'darwin.cron.tabs': '/var/at/tabs',
    },
    'linux': {
        # systemd：发行版层 vs 本地/第三方层
        'linux.systemd.distro': '/usr/lib/systemd/system',
        'linux.systemd.local': '/usr/local/lib/systemd/system',
        'linux.systemd.etc': '/etc/systemd/system',
        'linux.systemd.run': '/run/systemd/system',
        'linux.systemd.user': '~/.config/systemd/user',
        'linux.systemd.distro.user': '/usr/lib/systemd/user',
        'linux.systemd.local.user': '/usr/local/lib/systemd/user',
        # XDG autostart
        'linux.xdg.user': '~/.config/autostart',
        'linux.xdg.system': '/etc/xdg/autostart',
        # 遗留
        'linux.initd': '/etc/init.d',
        'linux.rc.local': '/etc/rc.local',
        'linux.cron.d': '/etc/cron.d',
        'linux.cron.etc': '/etc/crontab',
        'linux.cron.spool': '/var/spool/cron/crontabs',
        'linux.cron.spool.rh': '/var/spool/cron',
    },
    'win32': {
        # 注册表根不是文件路径，但同样走这张表，便于夹具注入
        'win.registry': 'REGISTRY',
        'win.startup.user': '~/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup',
        'win.startup.common': '%ProgramData%/Microsoft/Windows/Start Menu/Programs/Startup',
        'win.tasks': '%SystemRoot%/System32/Tasks',
    },
}


def platform_key():
    """当前平台键（可被 STARTUPCTL_PLATFORM 强制覆盖，测试用）。"""
    forced = os.environ.get('STARTUPCTL_PLATFORM')
    if forced:
        return forced
    import sys
    if sys.platform.startswith('darwin'):
        return 'darwin'
    if sys.platform.startswith('win'):
        return 'win32'
    return 'linux'


def load(env_value=None):
    """返回 {逻辑名: 实际路径}。

    未设 STARTUPCTL_ROOTS：'~' 展开为真实家目录，'%VAR%' 展开环境变量。
    设了 STARTUPCTL_ROOTS=<dir>：**每个逻辑名映射到 <dir>/<逻辑名去点>**，
    并保留逻辑名的形状，于是夹具树与真机树同构、测试断言可读。
    """
    base = env_value if env_value is not None else os.environ.get(ROOTS_ENV)
    out = {}
    for plat, table in DEFAULTS.items():
        for name, path in table.items():
            if base:
                out[name] = os.path.join(base, name.replace('.', '_'))
            else:
                out[name] = _expand(path)
    return out


def _expand(path):
    if not path:
        return path
    if os.name == 'nt':
        path = os.path.expandvars(path)
    return os.path.expanduser(path)


def remapped():
    """当前是否处于夹具重映射模式（测试与 cli 用来提示"这不是真机"）。"""
    return bool(os.environ.get(ROOTS_ENV))


def get(name, table=None):
    """取某个逻辑根的路径（取不到返回空串，让调用方按"这个平台没这个根"处理）。"""
    t = table if table is not None else load()
    return t.get(name, '')
