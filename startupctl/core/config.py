# -*- coding: utf-8 -*-
"""配置读取（KEY=value，与 jtool / ptool / CtfSweep 同规）。

查找顺序：$STARTUPCTL_CONFIG → <数据根>/startupctl.conf → 安装目录 config/startupctl.conf。
优先级（高→低）：命令行参数 > 环境变量 > 本文件 > 内置默认值。

⚠️ 解析必须容错：配置文件是给人手改的，一个拼错的键不该让工具整个起不来。
   未知键忽略，坏值回退默认值，并记进 warnings 由 config 子命令显示。
"""
import os

from . import paths

CONF_ENV = 'STARTUPCTL_CONFIG'

DEFAULTS = {
    'SCAN_SYSTEM': True,
    'PROC_ENABLED': True,
    'SCAN_SLOW_TASK_SCHEDULER': True,
    'SHOW_SYSTEM': False,
    'SHOW_WHITELISTED': True,
    'WIDTH': 0,
    'MIN_CONFIDENCE': 'high',
    'EXTRA_VENDORS': '',
    'TRUST_UNKNOWN': False,
    'DRY_RUN': False,
    'CONFIRM': True,
    'BACKUP_KEEP': 20,
    'BACKUP_MIN_DAYS': 7,
    'TERM_FIRST': True,
    'WATCH_INTERVAL': 5,
}

_BOOL_TRUE = ('1', 'true', 'yes', 'on', 'y', '是', '真')
_BOOL_FALSE = ('0', 'false', 'no', 'off', 'n', '否', '假')


class Config(object):
    def __init__(self, values=None, path=None, warnings=None):
        self.values = dict(DEFAULTS)
        if values:
            self.values.update(values)
        self.path = path
        self.warnings = list(warnings or [])

    def get(self, key, default=None):
        return self.values.get(key, DEFAULTS.get(key, default))

    def getbool(self, key):
        return bool(self.get(key))

    def getint(self, key):
        try:
            return int(self.get(key))
        except (TypeError, ValueError):
            return int(DEFAULTS.get(key, 0))

    def getlist(self, key):
        raw = self.get(key) or ''
        if isinstance(raw, (list, tuple)):
            return [str(x).strip() for x in raw if str(x).strip()]
        return [p.strip() for p in str(raw).split(',') if p.strip()]


def find_path():
    """定位配置文件；都不存在返回 None（全部走内置默认值）。"""
    env = os.environ.get(CONF_ENV)
    if env:
        return os.path.expanduser(env)
    cand = os.path.join(paths.data_root(), 'startupctl.conf')
    if os.path.isfile(cand):
        return cand
    # 安装目录里的模板（只读回退）
    try:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # <root>/lib
        for rel in ('config/startupctl.conf', '../config/startupctl.conf'):
            p = os.path.normpath(os.path.join(here, rel))
            if os.path.isfile(p):
                return p
    except Exception:
        pass
    return None


def _parse_bool(raw):
    s = str(raw).strip().strip('"').strip("'").lower()
    if s in _BOOL_TRUE:
        return True
    if s in _BOOL_FALSE:
        return False
    return None


def load(path=None):
    """读取配置。永不抛异常——坏文件按"全部默认"处理并记 warning。"""
    p = path if path is not None else find_path()
    values = {}
    warnings = []
    if not p or not os.path.isfile(p):
        return Config(values, p, warnings)

    try:
        with open(p, 'r', encoding='utf-8', errors='replace') as fh:
            for lineno, line in enumerate(fh, 1):
                s = line.strip()
                if not s or s.startswith('#') or s.startswith(';'):
                    continue
                if '=' not in s:
                    continue
                key, _, val = s.partition('=')
                key = key.strip().upper()
                # 只去掉一对包裹引号，不 tr 掉所有空格（路径里的空格要留住）
                val = val.strip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                    val = val[1:-1]
                if key not in DEFAULTS:
                    continue                      # 未知键忽略（手工加注释不会报错）
                if isinstance(DEFAULTS[key], bool):
                    b = _parse_bool(val)
                    if b is None:
                        warnings.append('%s:%d %s 的值 %r 不是布尔，按默认 %s'
                                        % (os.path.basename(p), lineno, key, val, DEFAULTS[key]))
                        continue
                    values[key] = b
                elif isinstance(DEFAULTS[key], int):
                    try:
                        values[key] = int(val)
                    except ValueError:
                        warnings.append('%s:%d %s 的值 %r 不是整数，按默认 %s'
                                        % (os.path.basename(p), lineno, key, val, DEFAULTS[key]))
                else:
                    values[key] = val
    except OSError as e:
        warnings.append('读取配置失败（%s），按内置默认值运行' % e)
        return Config({}, p, warnings)
    return Config(values, p, warnings)


def env_dry_run():
    """STARTUPCTL_DRY_RUN=1 强制全局 dry-run（CI 的安全带）。"""
    v = os.environ.get('STARTUPCTL_DRY_RUN')
    if v is None:
        return None
    return _parse_bool(v)
