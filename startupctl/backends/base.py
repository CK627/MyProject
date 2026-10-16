# -*- coding: utf-8 -*-
"""后端接口：每个平台实现这一份。

三条结构性约束（不是风格问题，是安全属性）：

1. **`plan` 与 `_do_*` 分离，且 `plan` 是纯函数。** 这才让"预览"与"执行"
   **结构上共用一份实现**，而不是两份会漂移的代码。`--dry-run` 调 `plan` 即止。

2. **`reclassify` 是变更路径上的强制项**（见 manage.mutate 第 6 道闸）：扫完到动手
   之间文件可能被换掉，变更前必须重读活源、重跑分类。

3. **每个 `_do_*` 自己再查一次 `_guard`。** 这是纵深防御：即便有人绕过 manage
   直接调后端方法，系统项依然改不动。反射测试（tests）会遍历 `manage.MUTATORS`
   对每个后端断言这一点——将来新增 `_do_purge` 会被自动覆盖。

`backends/*.py` **绝不**直接调 `os.remove` / `shutil.move` / `winreg.SetValue`：
文件搬移一律走 `self._move_aside()`（它走 safety 的备份目录），注册表写入走
`self._registry_write()`。这样"改了什么、备份在哪"永远只有一个来源。
"""
import os
import shutil

from ..core import safety
from ..core.safety import Refused
from ..core.model import ScanResult


class Backend(object):
    platform = ''
    name = ''
    # 本后端支持的变更操作（与 manage.MUTATORS 对应）
    OPS = ('disable', 'enable', 'remove', 'add')

    def __init__(self, ctx=None):
        self.ctx = ctx

    # ------------------------------------------------------------ 上下文
    @property
    def roots(self):
        return self.ctx.roots if self.ctx else {}

    def root(self, name):
        return (self.roots or {}).get(name, '')

    def path_of(self, name):
        """逻辑根 → 路径（等价 root()，语义更清楚）。"""
        return self.root(name)

    def conf(self, key, default=None):
        return self.ctx.conf.get(key, default) if self.ctx else default

    # ------------------------------------------------------------ 只读（子类实现）
    def scan(self, ctx):
        raise NotImplementedError

    def raw_payload(self, item, ctx):
        """原始内容（show --raw 用）。默认重读源文件；注册表后端覆写。"""
        src = item.source or ''
        if src and os.path.isfile(src):
            try:
                with open(src, 'r', encoding='utf-8', errors='replace') as fh:
                    return fh.read()
            except OSError as e:
                return '(读取失败: %s)' % e
        return item.raw or '(无原始内容)'

    def reclassify(self, item, ctx):
        """重读活源、重跑分类，返回**新的** item；源已消失返回 None。

        默认实现：如果 source 还在，就按原样重建一次记录并重新分类。
        子类应当重写为"真的重读文件/键"，因为默认实现挡不住"文件内容被替换"。
        """
        from ..core import classify
        if item.source and item.source_kind == 'file' and not os.path.exists(item.source):
            return None
        fresh = self._rebuild(item, ctx)
        if fresh is None:
            return None
        return classify.classify(fresh, ctx)

    def _rebuild(self, item, ctx):
        """从活源重建记录。子类覆写。默认返回原对象的浅拷贝。"""
        import copy
        return copy.copy(item)

    def is_admin(self):
        from ..core.utils import is_admin
        return is_admin()

    # ------------------------------------------------------------ 计划（纯函数）
    def plan(self, op, item, ctx):
        """返回人话计划行。**必须是纯函数**——预览与执行共用它。"""
        return ['  · %s %s（%s）' % (op, item.key, item.source or item.anchor)]

    # ------------------------------------------------------------ 进程
    def procs(self, ctx):
        from ..core import proc
        return proc.enumerate_procs(ctx, self)

    def corr_table(self, ctx):
        """平台权威的 {pid: anchor} 表。取不到返回 {}（调用方据此降级并如实标注）。"""
        return {}

    # ------------------------------------------------------------ 守卫
    def _guard(self, item, op):
        """每个 `_do_*` 的第一行。系统项一律拒绝。

        与 manage.check_gates 的第 2 道闸**故意重复**：那是主闸，这是纵深防御。
        重复在这里是正确的——它让"绕过 manage 直接调后端"也改不动系统项。
        """
        if item is None:
            raise Refused('拒绝操作：目标为空')
        if item.origin != 'third_party':
            from ..core.manage import _origin_cn
            raise Refused(
                '拒绝操作 %s：判定为「%s」%s' % (
                    item.key, _origin_cn(item.origin),
                    ('（%s）' % item.origin_evidence) if item.origin_evidence else ''),
                hint='系统项永不由本工具改动。')
        return True

    # ------------------------------------------------------------ 变更原语
    def _needs_root(self, item):
        """改这一项需要管理员吗？—— **按实际可写性判断，不只看 scope**。

        与 installer 的 run_priv 同口径：目标可写就直接做，不可写才要求提权。
        只看 `scope` 会把"位于用户可写位置的系统级项"也判成需要 root，而
        **夹具测试正好全在这种位置上**——于是所有安全测试都只跑到"拒绝"，执行路径
        （备份、搬移、还原）一次都没被验证过。测试跑不到的路，等于没写。

        真实场景下这个判断也更准：`/Library/LaunchAgents/x.plist` 属 root、`os.access`
        为假 → 需要提权；管理员手工 chown 过的项则可直接改。
        """
        if item.source_kind == 'registry' or not item.source:
            # 注册表路径不是文件，无法探测可写性 → 保守按作用域判
            from ..core.model import SCOPE_SYSTEM
            return item.scope == SCOPE_SYSTEM and not self.is_admin()
        src = item.source
        if os.path.exists(src):
            return not os.access(src, os.W_OK)
        d = os.path.dirname(src)
        if d and os.path.isdir(d) and os.access(d, os.W_OK):
            return False
        return True

    def _move_aside(self, item, backup, entry, suffix=''):
        """把源文件**搬进**备份目录（不是删除）。

        `remove` 之所以敢做，就是因为文件搬到了这里。返回新位置或 None。
        """
        src = item.source or ''
        if not src or not os.path.exists(src):
            return None
        if backup is None:
            raise Refused('无备份会话，拒绝搬移文件（%s）' % src)
        rel = safety.mirror_rel(src)
        if suffix:
            rel = rel + suffix
        dst = os.path.join(backup.files_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        # 备份阶段可能已经拷过一份；这里把原件搬走，避免留下两份
        src_backup = entry.get('backup_path') if entry else ''
        if src_backup and os.path.abspath(src_backup) != os.path.abspath(dst):
            if os.path.exists(dst):
                os.remove(dst)
            shutil.move(src_backup, dst)
            if entry is not None:
                entry['backup_path'] = dst
        try:
            shutil.move(src, dst) if not os.path.exists(dst) else os.remove(src)
        except OSError as e:
            raise RuntimeError('搬移失败（%s）: %s' % (src, e))
        return dst

    def _write_file(self, path, content, mode=0o644):
        """写一个文件（先写临时文件再 rename，避免半截文件）。"""
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        tmp = path + '.startupctl-tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
        return path

    def _registry_write(self, hive, key_path, name, value, view=None):
        """注册表写入（Windows 覆写）。非 Windows 默认什么都不做——绝不假装成功。"""
        raise Refused('当前平台不支持注册表操作')

    # ------------------------------------------------------------ 结果辅助
    def new_result(self, ctx):
        from datetime import datetime, timezone
        return ScanResult(platform=self.platform,
                          started_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))


def iter_scan_files(directory, suffixes=None, follow=True):
    """列目录下符合条件的文件（**跟随符号链接**，跳过隐藏与 .DS_Store）。

    跟随符号链接是必须的：本机实测 /Library/LaunchAgents 下有指向 .app 插件目录
    内的符号链接 plist，/System/Library/LaunchAgents 里有 11 个。不跟随就少扫一批。
    返回 (path, error) 二元组序列——读不到的目录要能被记成 ScanError 而不是静默跳过。
    """
    if not directory or not os.path.isdir(directory):
        return
    try:
        names = sorted(os.listdir(directory))
    except OSError as e:
        yield None, e
        return
    for n in names:
        if n.startswith('.'):
            continue
        p = os.path.join(directory, n)
        if suffixes and not any(n.endswith(s) for s in suffixes):
            # 符号链接可能不带后缀名指向带后缀的目标，所以软链一律放行
            if not os.path.islink(p):
                continue
        if os.path.isdir(p) and not os.path.islink(p):
            continue
        yield p, None
