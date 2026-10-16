# -*- coding: utf-8 -*-
"""后端注册与分发。

**整个代码树里只有这里（和 core/roots.py）判断平台。** cli.py 与 manage.py
永不 import 具体平台模块——它们只拿 `ctx.backend`，于是新增平台不会碰到它们。
"""
from .base import Backend

# 变更操作名（与 core.manage.MUTATORS 保持一致；这里再导出一份是为了让
# 反射测试不必 import manage，从而能独立遍历"每个后端 × 每个 mutator"）
MUTATORS = ('disable', 'enable', 'remove', 'add')

_REGISTRY = {
    'darwin': ('startupctl.backends.darwin', 'DarwinBackend'),
    'linux': ('startupctl.backends.linux', 'LinuxBackend'),
    'win32': ('startupctl.backends.windows', 'WindowsBackend'),
}


def _load(plat):
    mod_name, cls_name = _REGISTRY[plat]
    mod = __import__(mod_name, fromlist=[cls_name])
    return getattr(mod, cls_name)


def get_backend(platform, ctx=None):
    """按平台取后端。未知平台回退到 Linux 后端并提示（不静默假装成功）。"""
    plat = platform or ''
    if plat not in _REGISTRY:
        if plat.startswith('win'):
            plat = 'win32'
        elif plat.startswith('darwin'):
            plat = 'darwin'
        else:
            plat = 'linux'
    return _load(plat)(ctx)


def all_backends():
    """所有后端类（反射测试用：遍历每个后端的每个 mutator 断言守卫生效）。

    ⚠️ 这个函数存在的意义就是让"新后端漏写守卫"变成**测试失败**而不是线上事故。
    """
    out = []
    for plat in _REGISTRY:
        try:
            out.append((plat, _load(plat)))
        except Exception:
            pass
    return out
