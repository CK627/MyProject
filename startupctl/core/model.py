# -*- coding: utf-8 -*-
"""数据契约：StartupItem / ScanResult / 稳定 id / 引用解析 / 折叠。

**本文件最重要的两个决定：**

1. `make_uid` —— 白名单的键。必须扛得住重扫、`brew upgrade` 重写 plist、文件搬移、
   mtime 变化、重启。所以 **PID / mtime / size / inode / 路径一律不参与**，只由
   「平台自己的身份」决定（launchd 的 Label、systemd 的单元名、注册表的值名……）。
   按路径做键的白名单会在每次 brew upgrade 后静默失效——那是安全相关的惊吓。

2. `enabled` 是**三态**（Optional[bool]），不是布尔。macOS 的
   `launchctl print-disabled` 与 Windows 的 `StartupApproved` 都是**覆盖数据库**，
   两者都是「不在表里 = 没有覆盖 = 继承文件自身的默认值」，而不是「已启用」。
   用布尔会在这两个平台上都必然猜错一半。
"""
import hashlib
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

# uid 函数的 schema 版本。改动 make_uid 的算法/字段时递增它——
# 白名单条目里存了 anchor 作回退（见 whitelist.py），所以递增不会让老条目失效。
UID_VER = '1'

# ---------------------------------------------------------------- 枚举值
# 启动项类型。取值刻意与平台术语对齐，便于用户对照系统工具。
KIND_LAUNCHD_DAEMON = 'launchd-daemon'
KIND_LAUNCHD_AGENT = 'launchd-agent'
KIND_LOGIN_ITEM = 'login-item'
KIND_BTM = 'btm'
KIND_SYSTEMD = 'systemd'
KIND_SYSTEMD_USER = 'systemd-user'
KIND_XDG_AUTOSTART = 'xdg-autostart'
KIND_INITD = 'initd'
KIND_CRON = 'cron'
KIND_REGISTRY_RUN = 'registry-run'
KIND_STARTUP_FOLDER = 'startup-folder'
KIND_WIN_SERVICE = 'win-service'
KIND_TASK_SCHEDULER = 'task-scheduler'

ALL_KINDS = (
    KIND_LAUNCHD_DAEMON, KIND_LAUNCHD_AGENT, KIND_LOGIN_ITEM, KIND_BTM,
    KIND_SYSTEMD, KIND_SYSTEMD_USER, KIND_XDG_AUTOSTART, KIND_INITD, KIND_CRON,
    KIND_REGISTRY_RUN, KIND_STARTUP_FOLDER, KIND_WIN_SERVICE, KIND_TASK_SCHEDULER,
)

KIND_CN = {
    KIND_LAUNCHD_DAEMON: 'launchd 守护进程',
    KIND_LAUNCHD_AGENT: 'launchd 用户代理',
    KIND_LOGIN_ITEM: '登录项',
    KIND_BTM: '后台项(BTM)',
    KIND_SYSTEMD: 'systemd 系统单元',
    KIND_SYSTEMD_USER: 'systemd 用户单元',
    KIND_XDG_AUTOSTART: 'XDG 自启',
    KIND_INITD: 'init.d 脚本',
    KIND_CRON: 'cron 作业',
    KIND_REGISTRY_RUN: '注册表启动项',
    KIND_STARTUP_FOLDER: '启动文件夹',
    KIND_WIN_SERVICE: 'Windows 服务',
    KIND_TASK_SCHEDULER: '计划任务',
}

SCOPE_SYSTEM = 'system'
SCOPE_USER = 'user'

ORIGIN_OS = 'os'
ORIGIN_THIRD = 'third_party'
ORIGIN_UNKNOWN = 'unknown'

ORIGIN_CN = {
    ORIGIN_OS: '系统自带',
    ORIGIN_THIRD: '第三方',
    ORIGIN_UNKNOWN: '无法判定',
}

CONF_HIGH = 'high'
CONF_MEDIUM = 'medium'
CONF_LOW = 'low'
_CONF_RANK = {CONF_HIGH: 3, CONF_MEDIUM: 2, CONF_LOW: 1}


def conf_rank(c):
    return _CONF_RANK.get(c, 0)


# ---------------------------------------------------------------- 稳定 id
def make_uid(platform, kind, scope, anchor):
    """稳定 id：**只**由「平台自己的身份」决定，不含路径 / 时间 / 大小。

    anchor 按 kind 选取（这是全项目最关键的一张表）：

      launchd     → plist 的 Label。**不是路径**：brew 重生成 plist 时 Label 不变、
                    mtime 必变，按路径做键的白名单每次 brew upgrade 就失效。
      systemd     → 单元名（nginx.service）
      xdg         → .desktop 文件基名（XDG 规范里它就是身份）
      cron        → sha1(规范化后的作业五元组+命令)。cron 没有名字，只能内容寻址。
      registry    → 值名（HKCU\\...\\Run 下的 ValueName 就是身份）
      win-service → ServiceName。**不是 DisplayName**——后者可改且会撞。
      task        → 任务全路径
      login-item  → bundle id，没有则 app 路径基名
      btm         → 条目自身的 bundle id

    用 '\\x1f'（单元分隔符）连接而不是 ':'：Label 与 Windows 任务路径本来就能含
    ':' 和 '\\'，用冒号会让 ('a:b','c') 与 ('a','b:c') 撞成同一个 uid。
    """
    raw = '\x1f'.join((UID_VER, platform or '', kind or '', scope or '', anchor or ''))
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]


def make_fingerprint(program, args, raw=''):
    """载荷指纹：**「它干什么」**，与 uid 的「它是什么」分开。

    保留 Label 却换掉 ProgramArguments，正是本工具要抓的持久化手法：uid 不变、
    指纹变。`scan --save` / `--diff` 靠它报载荷漂移；`whitelist add --pin` 用它
    把豁免钉在"就是这个形态"上。
    """
    parts = [program or '']
    parts.extend(list(args or ()))
    h = hashlib.sha1('\x1f'.join(parts).encode('utf-8'))
    if raw:
        h.update(b'\x1e')
        h.update(raw.encode('utf-8', 'replace'))
    return h.hexdigest()[:16]


def derive_key(anchor, kind=''):
    """人类句柄：把平台身份压成一个能敲的短名。

    纯展示用——**绝不参与匹配、绝不持久化**。它的推导规则将来可能变，而 uid 与
    anchor 是稳定的；让白名单或快照依赖 key 就等于把稳定性扔掉。
    """
    s = (anchor or '').strip()
    if not s:
        return '(unnamed)'
    # Windows 任务路径 \\Microsoft\\Windows\\Foo → 取最后一段
    if '\\' in s or '/' in s:
        s = s.replace('/', '\\').rstrip('\\').split('\\')[-1]
    # 反 DNS：com.docker.vmnetd → docker.vmnetd（首段是 TLD 时去掉）
    if '.' in s:
        head, rest = s.split('.', 1)
        if head.lower() in ('com', 'org', 'net', 'io', 'cn', 'me', 'dev', 'co', 'fr', 'de', 'uk'):
            s = rest
    # systemd 的 .service 后缀
    for suf in ('.service', '.plist', '.desktop', '.socket', '.target'):
        if s.endswith(suf):
            s = s[:-len(suf)]
    out = ''.join(ch if (ch.isalnum() or ch in '._-') else '-' for ch in s)
    out = out.strip('-')
    return out or '(unnamed)'


# ---------------------------------------------------------------- 记录
@dataclass
class StartupItem:
    """一个启动项。字段按「身份 / 展示 / 干什么 / 出处 / 分类 / 运行时 / 完整性」分组。"""

    # ── 身份 ──
    uid: str = ''
    key: str = ''
    anchor: str = ''            # 平台原始身份（Label / unit / ValueName / TaskPath）
    kind: str = ''
    scope: str = SCOPE_USER
    platform: str = ''

    # ── 展示 ──
    name: str = ''
    description: str = ''
    vendor: str = ''            # 反 DNS 派生的厂商前缀，如 'com.docker'
    vendor_name: str = ''       # 厂商可读名，查表得到则为空

    # ── 干什么 ──
    program: str = ''
    args: Tuple[str, ...] = ()
    run_at_load: bool = False
    # ★ 三态：True/False = 有明确依据；None = 无覆盖记录、由文件自身决定而文件没写。
    enabled: Optional[bool] = None
    enabled_reason: str = ''    # 'RunAtLoad' | 'Disabled' | 'override:disabled' | ...
    trigger: str = 'unknown'    # boot|login|schedule|demand|socket|periodic|unknown

    # ── 出处 ──
    source: str = ''            # plist 路径 / 注册表路径 / 目录项
    source_kind: str = 'file'   # file|registry|dir-entry|db
    root: str = ''              # 由哪个扫描根产出（roots.py 的逻辑名）

    # ── 分类 ──
    origin: str = ORIGIN_UNKNOWN
    origin_evidence: str = ''   # 人话，**永远非空**：用户必须能复核判定依据
    confidence: str = CONF_LOW
    managing_tool: str = ''     # ''|'homebrew'|'docker'|'vendor'|'systemd'|…
    # ★ 默认 False —— 后端忘了设就是安全的那一边（不会被改）。
    mutable: bool = False

    # ── 运行时（proc 填充）──
    pid: Optional[int] = None
    related_pids: Tuple[int, ...] = ()
    proc_state: str = 'unknown'  # running|loaded|stopped|unknown
    corr_method: str = ''        # 'launchctl'|'cgroup'|'service-mgr'|'path'|''

    # ── 完整性 ──
    fingerprint: str = ''
    raw: str = ''
    shadowed_by: str = ''        # 被哪个 uid 遮蔽（XDG 的 Hidden / 同名覆盖）
    whitelisted: bool = False
    warnings: Tuple[str, ...] = ()

    def __post_init__(self):
        if self.args is None:
            self.args = ()
        elif not isinstance(self.args, tuple):
            self.args = tuple(self.args)
        if self.warnings is None:
            self.warnings = ()
        elif not isinstance(self.warnings, tuple):
            self.warnings = tuple(self.warnings)
        if self.related_pids is None:
            self.related_pids = ()
        elif not isinstance(self.related_pids, tuple):
            self.related_pids = tuple(self.related_pids)
        if not self.uid:
            self.uid = make_uid(self.platform, self.kind, self.scope, self.anchor)
        if not self.key:
            self.key = derive_key(self.anchor, self.kind)
        if not self.fingerprint:
            self.fingerprint = make_fingerprint(self.program, self.args, self.raw)
        # ★ 结构性默认：凡不是明确判定为第三方的，一律不可改。
        #   后端即便忘了设 mutable，也不会造出一个可被 clean 命中的系统项。
        if self.origin != ORIGIN_THIRD:
            self.mutable = False

    # -- 展示辅助 --
    @property
    def running(self):
        return self.pid is not None

    def enabled_text(self):
        if self.enabled is True:
            return '已启用'
        if self.enabled is False:
            return '已禁用'
        return '未知'

    def to_dict(self):
        d = {}
        for k in self.__dataclass_fields__:
            v = getattr(self, k)
            d[k] = list(v) if isinstance(v, tuple) else v
        return d

    @classmethod
    def from_dict(cls, d):
        allowed = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in (d or {}).items() if k in allowed})


# ---------------------------------------------------------------- 扫描结果
@dataclass
class ScanError:
    """一次读不到的根/文件。**必须如实呈现**——权限错误被渲染成"没有启动项"，
    正是"工具报告了一台它根本没看过的干净机器"那种事故。"""
    root: str = ''
    path: str = ''
    reason: str = ''
    needs_root: bool = False
    detail: str = ''

    def to_dict(self):
        return dict(root=self.root, path=self.path, reason=self.reason,
                    needs_root=self.needs_root, detail=self.detail)


def scan_error(root, path, reason, needs_root=False, detail=''):
    """构造一个 ScanError 的小工厂（后端各处都要用，省得每次写全字段）。

    `needs_root=True` 会让整次扫描被判为**不完整**，从而让 `clean` 拒绝运行——
    所以它只该用在"这个根没读到是因为权限"这种情况上。
    """
    return ScanError(root=root, path=path, reason=reason,
                     needs_root=needs_root, detail=detail)


@dataclass
class ScanResult:
    items: List[StartupItem] = field(default_factory=list)
    errors: List[ScanError] = field(default_factory=list)
    roots_scanned: List[str] = field(default_factory=list)
    platform: str = ''
    started_at: str = ''
    # ★ complete=False 是**载重字段**：clean 拒绝在残缺视图上运行
    #   （有任何 needs_root 的错误就置 False）。这是"半发布防护"用在安全决定上。
    complete: bool = True

    def recompute_complete(self):
        self.complete = not any(e.needs_root for e in self.errors)
        return self.complete

    def by_uid(self):
        return {i.uid: i for i in self.items}

    def filtered(self, third_only=True, include_os=False, **kw):
        return [i for i in self.items if True]


# ---------------------------------------------------------------- 引用解析
class RefError(Exception):
    """引用解析失败的基类（cli 会转成退出码 2）。"""
    pass


class NotFound(RefError):
    pass


class AmbiguousRef(RefError):
    def __init__(self, ref, matches):
        self.ref = ref
        self.matches = matches
        names = ', '.join(sorted(m.key for m in matches)[:8])
        more = '' if len(matches) <= 8 else ' 等 %d 项' % len(matches)
        RefError.__init__(
            self, '「%s」匹配到 %d 项，无法确定是哪一项: %s%s' % (ref, len(matches), names, more))


def resolve(items, ref):
    """把用户敲的引用解析成一个 StartupItem。

    依次尝试：精确 uid → 精确 anchor → 精确 key → 唯一前缀/子串。
    撞了就抛 AmbiguousRef 并列出候选——**绝不替用户猜**。
    顺序即优先级：uid 最精确，子串最模糊。
    """
    if not ref:
        raise NotFound('未指定启动项')
    items = list(items)

    for attr in ('uid', 'anchor', 'key'):
        hits = [i for i in items if getattr(i, attr, '') == ref]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise AmbiguousRef(ref, hits)

    low = ref.lower()
    hits = [i for i in items
            if low in (i.uid or '').lower()
            or low in (i.anchor or '').lower()
            or low in (i.key or '').lower()
            or low in (i.name or '').lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise NotFound('未找到匹配「%s」的启动项（用 list 看有哪些）' % ref)
    raise AmbiguousRef(ref, hits)


# ---------------------------------------------------------------- 折叠
_SCOPE_RANK = {SCOPE_SYSTEM: 2, SCOPE_USER: 1}


def merge(items):
    """按 uid 折叠。

    同一逻辑项可能被多个来源看到（如 launchd 文件 + brew services 的属性）。
    规矩：**属性源只补属性，不另发一条记录**——一个后端因为 `brew services list`
    就多发一条，是后端写错了，由这里兜住。

    优先级：系统级文件 > 用户级文件 > 属性源。warnings 取并集，confidence 取最高。
    """
    out = {}
    order = []
    for it in items:
        cur = out.get(it.uid)
        if cur is None:
            out[it.uid] = it
            order.append(it.uid)
            continue
        # 选"主记录"
        if _SCOPE_RANK.get(it.scope, 0) > _SCOPE_RANK.get(cur.scope, 0):
            primary, secondary = it, cur
        else:
            primary, secondary = cur, it
        # 合并属性：空的被非空的补上
        for f in ('program', 'description', 'name', 'vendor', 'vendor_name',
                  'managing_tool', 'source', 'root', 'raw', 'enabled_reason',
                  'shadowed_by'):
            if not getattr(primary, f, '') and getattr(secondary, f, ''):
                setattr(primary, f, getattr(secondary, f))
        if not primary.args and secondary.args:
            primary.args = secondary.args
        if primary.enabled is None and secondary.enabled is not None:
            primary.enabled = secondary.enabled
        if primary.pid is None and secondary.pid is not None:
            primary.pid = secondary.pid
            primary.corr_method = secondary.corr_method
            primary.proc_state = secondary.proc_state
        if conf_rank(secondary.confidence) > conf_rank(primary.confidence):
            primary.confidence = secondary.confidence
        # origin 取更保守的那个：只要有一边说 os，就按 os 收（倒向安全）
        if secondary.origin == ORIGIN_OS and primary.origin != ORIGIN_OS:
            primary.origin = ORIGIN_OS
            primary.origin_evidence = secondary.origin_evidence
            primary.mutable = False
        ws = list(primary.warnings)
        for w in secondary.warnings:
            if w not in ws:
                ws.append(w)
        primary.warnings = tuple(ws)
        out[it.uid] = primary
    return [out[u] for u in order]


def ensure_unique_keys(items):
    """给同一次扫描内撞车的 key 加 -2 / -3 后缀。

    key 只是展示句柄，但它会出现在命令行里，所以同一个 key 指两项是会误导人的。
    （uid 不会撞——它包含完整的 anchor。）
    """
    seen = {}
    for it in items:
        base = it.key
        n = seen.get(base, 0)
        seen[base] = n + 1
        if n:
            it.key = '%s-%d' % (base, n + 1)
    return items
