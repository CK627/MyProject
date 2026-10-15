# -*- coding: utf-8 -*-
"""用户数据目录布局（单点定义，cli / 测试共用）。

数据根 = $CTFSWEEP_DATA_DIR 或 ~/.devtools/ctfsweep，**下面只有 cache/**：

    <数据根>/cache/<运行名>-<路径哈希6位>/
        1.txt（高置信）/ 2.txt（中置信）/ 3.txt（低置信）
            ——本次运行全部文件的命中合在一起，目录扫描时每行带 `← <相对路径>`
        <运行名>_cache.txt（本次运行的完整报告，含本次运行汇总尾段）

**一次运行一个目录**（不是「一个文件一个目录」）：运行名取扫描根目录名
（`-F 项目/` → `项目`；单文件取文件名去扩展名），哈希取完整路径的 short sha1，
所以同名不同目录的两次运行各成一份、互不覆盖。

每次扫描（默认模式与 -q 都是）写入这份缓存——跑完就能回看，不必重扫。
缓存**只增不减**：装/卸/更新都不会碰它；清空只有用户显式发起的 `ctfsweep clear`
（清数据根下的内容，保留目录本身与 ctfsweep.conf），`ctfsweep config` 报占用与路径。

⚠️ 布局契约改这里一处即可，不要在别处再拼 `cache` 路径或另写一份数据根解析。
"""
import os

DATA_DIR_ENV = 'CTFSWEEP_DATA_DIR'


def data_root():
    """用户数据根目录（默认 ~/.devtools/ctfsweep）。

    环境变量 CTFSWEEP_DATA_DIR 可覆盖（测试隔离与多环境用）；语义是**根**，
    缓存落在其下的 cache/。
    """
    root = os.environ.get(DATA_DIR_ENV)
    if root:
        return os.path.expanduser(root)
    return os.path.join(os.path.expanduser('~'), '.devtools', 'ctfsweep')


def cache_root():
    """扫描缓存根目录（<数据根>/cache）。目录不存在时不创建，调用方按需 makedirs。"""
    return os.path.join(data_root(), 'cache')
