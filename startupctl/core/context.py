# -*- coding: utf-8 -*-
"""运行上下文：把配置、扫描根、dry-run、提权状态、后端实例串在一起。

`Ctx` 是**所有破坏性判断的权威来源**：
  · `scanned_uids` 是本次进程真正扫到过的 uid 集合 —— manage._dispatch 的第一步
    就拿它挡「构造一个 item 传进来」这条路（见 manage.py）。
  · `dry_run` 一旦为真，任何变更都只打印计划。CI 用 STARTUPCTL_DRY_RUN=1 全局强制，
    所以即便有 bug 摸到了 mutator 也无法行动。
"""
import os
import sys

from . import config as config_mod
from . import output, roots as roots_mod
from .utils import is_admin


class Ctx(object):
    def __init__(self, conf=None, dry_run=False, assume_yes=False,
                 platform=None, root_table=None, backend=None):
        self.platform = platform or roots_mod.platform_key()
        self.roots = root_table if root_table is not None else roots_mod.load()
        self.conf = conf if conf is not None else config_mod.load()

        # dry-run 的三个来源，任一为真即生效：CLI 旗标 / 配置项 / 环境变量（CI）
        env_dry = config_mod.env_dry_run()
        self.dry_run = bool(dry_run or self.conf.getbool('DRY_RUN') or (env_dry is True))
        self.dry_run_from_env = (env_dry is True)

        # CONFIRM=false 等同全局 -y（配置里默认 true，不鼓励关）
        self.assume_yes = bool(assume_yes or not self.conf.getbool('CONFIRM'))
        self.trust_unknown = self.conf.getbool('TRUST_UNKNOWN')
        self.extra_vendors = self.conf.getlist('EXTRA_VENDORS')

        self._admin = None
        self._backend = backend

        # 本次扫描的结果与 uid 集合（manage 的溯源依据）
        self.scan_result = None
        self.scanned_uids = set()
        self.whitelist = None

        output.set_color_mode('auto')
        w = self.conf.getint('WIDTH')
        if w:
            os.environ.setdefault('COLUMNS', str(w))

    # -- 提权状态（只影响提示，绝不放宽判定）--
    @property
    def admin(self):
        if self._admin is None:
            self._admin = is_admin()
        return self._admin

    # -- 后端（懒加载，避免 cli 顶层就 import 平台模块）--
    @property
    def backend(self):
        if self._backend is None:
            from ..backends import get_backend
            self._backend = get_backend(self.platform, self)
        return self._backend

    # -- 扫描 --
    def scan(self, force=False):
        """跑一次扫描并缓存结果（同一进程内多次调用复用）。"""
        if self.scan_result is not None and not force:
            return self.scan_result
        res = self.backend.scan(self)
        res.recompute_complete()
        self.scan_result = res
        self.scanned_uids = set(i.uid for i in res.items)
        return res

    def items(self, force=False):
        return self.scan(force).items

    # -- 白名单（懒加载）--
    def wl(self):
        if self.whitelist is None:
            from . import whitelist as wl_mod
            self.whitelist = wl_mod.load()
        return self.whitelist

    # -- 输出辅助 --
    def warn(self, msg):
        sys.stderr.write(output.c('警告: ' + msg, 'yellow') + '\n')

    def note(self, msg):
        sys.stderr.write(msg + '\n')

    def fail(self, msg):
        sys.stderr.write(output.c('错误: ' + msg, 'red') + '\n')

    def is_fixture(self):
        """是否处于夹具重映射模式（测试/演示）——输出里要明说，免得被当真机结果。"""
        return roots_mod.remapped()
