# -*- coding: utf-8 -*-
"""白名单：用户确认要保留的启动项/进程。

**存储用单文件 JSON，不用 SQLite。** 决定性理由：允许清单是用户必须能**审计**的
安全产物——`cat` / `grep` / `diff` / `git` 对 JSON 都能用，对 SQLite 二进制全都无效。
何况它单写者、几十条、需要人手改，这三点 SQLite 都更差。

**不变量（有专门的测试）：**

    白名单只能**收窄**破坏性集合，永远不能放宽它。

`manage.check_gates` 里的 origin 硬闸**独立于白名单、且先于白名单**求值，
所以任何白名单条目都无法让一个系统项变得可改。本模块因此**只读地**参与判定：
它设置 `item.whitelisted`，而 `whitelisted` 只在 `clean_candidates` 里做减法。

**抗 id 变化：** 每个 `id` 条目都存下当时的 `anchor`；uid 匹配不上就回退锚点匹配。
这一个字段同时兜住了 uid 函数自身的 schema 演进（UID_VER 递增后老条目仍有效）。

**匹配方式刻意不用正则**（用户给的正则是脚枪：灾难性回溯，且 `re` 的语义与用户敲
`homebrew.mxcl.*` 的预期不符——`fnmatch` 的 `*` 跨 `.`，正则不跨）。
也**刻意不支持厂商名子串**：匹配"名字里含 Apple"的规则会静默放行名为 AppleHelper
的恶意软件。每条规则都必须 key 在用户不可能被诱骗去创建的东西上。
"""
import fnmatch
import json
import os
from datetime import datetime, timezone

from . import paths

SCHEMA_VERSION = 1

MATCH_ID = 'id'
MATCH_ANCHOR = 'anchor'
MATCH_ANCHOR_GLOB = 'anchor_glob'
MATCH_VENDOR = 'vendor'
MATCH_EXEC_PREFIX = 'exec_prefix'
MATCH_PROC_NAME = 'proc_name'

MATCH_KINDS = (MATCH_ID, MATCH_ANCHOR, MATCH_ANCHOR_GLOB, MATCH_VENDOR,
               MATCH_EXEC_PREFIX, MATCH_PROC_NAME)

MATCH_CN = {
    MATCH_ID: '稳定 id（最精确，跨扫描稳定）',
    MATCH_ANCHOR: '平台原始身份（Label / 单元名 / 值名）',
    MATCH_ANCHOR_GLOB: '锚点通配（fnmatch，如 homebrew.mxcl.*）',
    MATCH_VENDOR: '厂商前缀（如 com.docker）',
    MATCH_EXEC_PREFIX: '可执行路径前缀',
    MATCH_PROC_NAME: '进程名（仅用于没有启动项的进程，最弱）',
}


def _now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class Whitelist(object):
    def __init__(self, entries=None, path=None):
        self.entries = list(entries or [])
        self.path = path or paths.whitelist_path()
        self._dirty = False

    # ---------------- 匹配 ----------------
    def matches(self, item):
        """item 是否被白名单覆盖。任一规则命中即为真。"""
        for e in self.entries:
            if self._entry_matches(e, item):
                return True
        return False

    def _entry_matches(self, e, item):
        kind = e.get('match')
        val = e.get('value') or ''
        if not val:
            return False

        if kind == MATCH_ID:
            if item.uid and item.uid == val:
                return True
            # ★ 回退：uid 变了（单元改名 / UID_VER 递增）就用存下的 anchor 认
            saved_anchor = e.get('anchor') or ''
            return bool(saved_anchor) and saved_anchor == (item.anchor or '')

        if kind == MATCH_ANCHOR:
            return val == (item.anchor or '')
        if kind == MATCH_ANCHOR_GLOB:
            return fnmatch.fnmatchcase(item.anchor or '', val)
        if kind == MATCH_VENDOR:
            return (item.vendor or '') == val
        if kind == MATCH_EXEC_PREFIX:
            prog = item.program or ''
            return bool(prog) and prog.startswith(val)
        if kind == MATCH_PROC_NAME:
            base = os.path.basename(item.program or '')
            return base == val or (item.anchor or '') == val
        return False

    def matches_proc(self, proc):
        """进程侧匹配：只用 proc_name / exec_prefix 这两类规则。

        ⚠️ 这里刻意**不**用 id / anchor 规则去匹配进程——一个启动项对应哪个进程
        本来就是"尽力而为的连接"（见 proc.py 的关联局限），拿它当 kill 的许可
        等于把猜测当事实。
        """
        for e in self.entries:
            kind = e.get('match')
            val = e.get('value') or ''
            if not val:
                continue
            if kind == MATCH_EXEC_PREFIX and (proc.program or '').startswith(val):
                return True
            if kind == MATCH_PROC_NAME:
                if (proc.comm or '') == val or os.path.basename(proc.program or '') == val:
                    return True
        return False

    def apply(self, items):
        """给每一项打上 whitelisted 标记（**只标记，不过滤**）。

        会隐藏东西的白名单，是用户会忘记自己写过的白名单——所以 list 里
        白名单项照样出现，只是带 [白] 标记。"""
        for it in items:
            it.whitelisted = self.matches(it)
        return items

    # ---------------- 变更 ----------------
    def add(self, item, match=MATCH_ID, value=None, reason='', pin=False):
        if match not in MATCH_KINDS:
            raise ValueError('未知的匹配方式: %s' % match)
        if value is None:
            value = self._default_value(item, match)
        e = {
            'match': match,
            'value': value,
            # 存下 anchor：id 条目靠它做回退；其余条目靠它供人审计
            'anchor': item.anchor or '',
            'platform': item.platform or '',
            'pinned_fingerprint': (item.fingerprint or '') if pin else '',
            'reason': reason or '',
            'added': _now(),
            'seen_name': item.name or item.key or '',
            'source_at_add': item.source or '',
        }
        self.entries.append(e)
        self._dirty = True
        return e

    def _default_value(self, item, match):
        if match == MATCH_ID:
            return item.uid
        if match in (MATCH_ANCHOR, MATCH_ANCHOR_GLOB):
            return item.anchor
        if match == MATCH_VENDOR:
            return item.vendor
        if match == MATCH_EXEC_PREFIX:
            return os.path.dirname(item.program or '') + os.sep if item.program else ''
        if match == MATCH_PROC_NAME:
            return os.path.basename(item.program or '')
        return ''

    def remove_index(self, idx):
        if 0 <= idx < len(self.entries):
            e = self.entries.pop(idx)
            self._dirty = True
            return e
        return None

    def remove_matching(self, item):
        """移出所有命中该项的条目。返回移除的条数。"""
        keep, removed = [], []
        for e in self.entries:
            if self._entry_matches(e, item):
                removed.append(e)
            else:
                keep.append(e)
        if removed:
            self.entries = keep
            self._dirty = True
        return len(removed)

    def unmatched(self, items):
        """本次扫描中一条都没命中的条目。

        ⚠️ **绝不自动清理**——静默删掉一条允许清单条目，正是本工具要防的那类
        安全惊吓。只报告，由用户显式 `whitelist prune` 决定。"""
        out = []
        for e in self.entries:
            hit = any(self._entry_matches(e, it) for it in items)
            if not hit:
                out.append(e)
        return out

    def prune_unmatched(self, items):
        bad = self.unmatched(items)
        if not bad:
            return 0
        ids = set(id(e) for e in bad)
        self.entries = [e for e in self.entries if id(e) not in ids]
        self._dirty = True
        return len(bad)

    # ---------------- 持久化 ----------------
    def load(self):
        p = self.path
        if not p or not os.path.isfile(p):
            return self
        try:
            with open(p, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            self.entries = list(data.get('entries') or [])
        except (OSError, ValueError):
            # 坏文件不能让工具起不来，但也**绝不**覆盖它——用户可能是手改错了，
            # 覆盖掉就把他的允许清单弄丢了。保留原文件，本次按空白名单跑。
            self.entries = []
            self._broken = True
        return self

    def save(self):
        p = self.path
        d = os.path.dirname(p)
        if d:
            paths.ensure_dir(d)
        data = {
            'version': SCHEMA_VERSION,
            'updated': _now(),
            'entries': self.entries,
        }
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
        self._dirty = False
        return p

    def is_empty(self):
        return not self.entries


def load():
    wl = Whitelist()
    return wl.load()
