# -*- coding: utf-8 -*-
"""数据目录布局（单点定义，cli / selfmgr / safety / whitelist / 测试共用）。

数据根 = $STARTUPCTL_DATA_DIR 或 ~/.devtools/startupctl，**下面有三样东西**：

    <数据根>/whitelist.json        白名单（用户逐条确认过的允许清单）
    <数据根>/backups/<UTC ts>-<op>/  备份：manifest.json + plan.json + files/ + registry/
    <数据根>/scans/<UTC ts>.json   扫描快照（scan --save / --diff 用）

⚠️ 三个子项的契约各不相同，不要混为一谈：

  · whitelist.json —— 是**安全产物**，用户必须能审计（cat/grep/diff/git 都要能用，
    所以是 JSON 不是 SQLite）。永不自动删除。
  · backups/       —— 是**唯一的后悔药**：remove 之所以敢做，就是因为文件搬到了这里。
    永不自动删除（只有 `backup prune` 按保留策略清）。
  · scans/         —— 只是快照缓存，可以清（`clear` 只清这个）。

安装根与数据根的关系：
  · 用户级安装（STARTUPCTL_USER=1）下**安装根就是数据根**，所以 install / update /
    uninstall 一律**永不 `rm -rf` 数据根**，只删功能项（见 installer/deploy.sh）。
  · 系统级安装下安装根是 /Library/devtools/startupctl，数据根仍在 ~/.devtools/startupctl。

⚠️ 布局契约改这里一处即可，不要在别处再拼 'backups' / 'scans' 路径，也不要另写一份
   数据根解析——测试靠 STARTUPCTL_DATA_DIR 隔离整个环境，多一处拼路径就多一处隔离漏洞。
"""
import os

DATA_DIR_ENV = 'STARTUPCTL_DATA_DIR'
WHITELIST_NAME = 'whitelist.json'
BACKUPS_DIR = 'backups'
SCANS_DIR = 'scans'


def data_root():
    """用户数据根目录（默认 ~/.devtools/startupctl）。

    环境变量 STARTUPCTL_DATA_DIR 可覆盖（测试隔离与多环境用）；语义是**根**，
    下面才分 whitelist.json / backups/ / scans/。
    """
    root = os.environ.get(DATA_DIR_ENV)
    if root:
        return os.path.expanduser(root)
    return os.path.join(os.path.expanduser('~'), '.devtools', 'startupctl')


def whitelist_path():
    """白名单文件路径（不创建）。"""
    return os.path.join(data_root(), WHITELIST_NAME)


def backups_root():
    """备份根目录（不创建；调用方按需 makedirs）。"""
    return os.path.join(data_root(), BACKUPS_DIR)


def scans_root():
    """扫描快照根目录（不创建）。"""
    return os.path.join(data_root(), SCANS_DIR)


def ensure_dir(path):
    """确保目录存在（返回 path）。只按需创建，不在 import 时乱建目录。"""
    if path and not os.path.isdir(path):
        os.makedirs(path)
    return path
