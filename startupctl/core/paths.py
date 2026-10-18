# -*- coding: utf-8 -*-
"""数据目录布局（单点定义，cli / guard / selfmgr / 测试共用）。

**数据跟着项目走**：默认放在**安装根下的 `data/`**，而不是用户主目录。

    <安装根>/data/guard.json     白名单 / 黑名单 / 当前模式

为什么不在 ~/.devtools 下另开一个目录（用户的明确要求）：

  · 装到哪儿、数据就在哪儿——`/Library/devtools/startupctl/data/`、仓库里的
    `data/`、Windows 的 `%USERPROFILE%\\.devtools\\startupctl\\data\\` 都是同一个规则；
  · 删掉项目目录 / 卸载，数据跟着一起没，不会在主目录里留一份无主的垃圾；
  · 升级**不碰** data/：deploy.sh 只删功能项（bin lib config completions VERSION
    uninstall deploy.sh shell-setup.sh），名单与模式原样保留。

`STARTUPCTL_DATA_DIR` 可整体覆盖（测试隔离与多环境用）。语义是**根**，
`guard.json` 在其下。

⚠️ 布局契约只在这里定义一次。别在别处拼 'data' / 'guard.json'——
   测试靠 STARTUPCTL_DATA_DIR 隔离整个环境，多一处拼路径就多一处隔离漏洞。
"""
import os

DATA_DIR_ENV = 'STARTUPCTL_DATA_DIR'
DATA_DIR_NAME = 'data'
GUARD_NAME = 'guard.json'

# 旧位置（2.1 之前）：数据在 ~/.devtools/<tool> 下。只用于一次性迁移。
LEGACY_ROOT = os.path.join(os.path.expanduser('~'), '.devtools', 'startupctl')


def install_root():
    """安装根：devtools 安装版是安装目录，仓库版是仓库根。

    用 selfmgr.self_info() 判断（它已经处理了「在 lib/ 下还是仓库根」）。
    放在函数里 import 是为了避开 paths ↔ selfmgr 的循环导入。
    """
    try:
        from .selfmgr import self_info
        _mode, root, _devtools = self_info()
        if root:
            return root
    except Exception:
        pass
    # 兜底：.../startupctl/core/paths.py → 上溯两级
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_root():
    """数据根目录（默认 <安装根>/data）。

    STARTUPCTL_DATA_DIR 优先；语义是**根**，guard.json 在其下。
    """
    root = os.environ.get(DATA_DIR_ENV)
    if root:
        return os.path.expanduser(root)
    return os.path.join(install_root(), DATA_DIR_NAME)


def guard_path():
    """策略文件路径（不创建）。"""
    return os.path.join(data_root(), GUARD_NAME)


def legacy_guard_path():
    """2.1 之前的策略文件路径（只用于迁移；不存在返回 None）。"""
    p = os.path.join(LEGACY_ROOT, GUARD_NAME)
    return p if os.path.isfile(p) else None


def backups_root():
    """（遗留）备份子系统的根目录。

    2.0 起 CLI 不再暴露任何备份/还原命令（用户要求「多余的备份没必要」），
    这条路径只被 core/safety.py 里**已不可达**的备份函数引用，永远不会被创建。
    保留它是为了让那批内部函数还能导入；彻底删除它们时一并删掉这个函数。
    """
    return os.path.join(data_root(), 'backups')


def ensure_dir(path):
    """确保目录存在（返回 path）。只按需创建，不在 import 时乱建目录。"""
    if path and not os.path.isdir(path):
        os.makedirs(path)
    return path
