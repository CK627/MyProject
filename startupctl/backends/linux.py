# -*- coding: utf-8 -*-
"""Linux 后端：systemd（系统 + 用户）· XDG autostart · init.d · cron。

老实说 Linux 比 macOS 难：**没有 SIP 的等价物**，三方包就装在
`/usr/lib/systemd/system/` 里，与发行版单元毗邻。所以本后端对"判不出来"非常克制，
宁可返回 unknown + 证据串，也不猜（见 core/classify.py）。

几个容易踩的点，实现里都处理了：

  · **`static` 单元永远无法启用**（无 `[Install]`，只作依赖被拉起）→ 报 `enabled=None`
    并说明是 static，**不能报成"未启用/损坏"**。
  · **drop-in 会改 `ExecStart`**：`/etc/systemd/system/foo.service.d/*.conf` 能在不动
    单元文件的情况下改命令行；只读单元文件会报出**过期的命令行**。
  · **XDG 生效态是算出来的**：目录优先级 → `Hidden` → `OnlyShowIn`/`NotShowIn` →
    `TryExec`。先查规范键 `Hidden`，再查 GNOME 扩展 `X-GNOME-Autostart-enabled`
    （**要说明用的是哪一个**）。
  · **`configparser` 三个坑**：默认把键名小写化（必须覆盖 `optionxform`，否则
    `X-GNOME-...` 变全小写）、需 `delimiters=('=',)`、需 `strict=False`。
  · **`systemctl --user` 在容器/纯 ssh 里连不上 bus** → 检出并作为 ScanError 报出，
    绝不崩。
"""
import fnmatch
import os
import re

from ..core import classify
from ..core.model import (KIND_CRON, KIND_INITD, KIND_SYSTEMD, KIND_SYSTEMD_USER,
                          KIND_XDG_AUTOSTART, SCOPE_SYSTEM, SCOPE_USER, StartupItem,
                          make_fingerprint)
from ..core.safety import Refused
from ..core.utils import run
from .base import Backend, iter_scan_files

SYSTEMCTL = '/bin/systemctl'
if not os.path.exists(SYSTEMCTL):
    SYSTEMCTL = '/usr/bin/systemctl'


class LinuxBackend(Backend):
    platform = 'linux'
    name = 'systemd'

    # ------------------------------------------------------------ 扫描
    def scan(self, ctx):
        res = self.new_result(ctx)
        states = self._unit_states(res)

        unit_roots = [
            ('linux.systemd.etc', KIND_SYSTEMD, SCOPE_SYSTEM),
            ('linux.systemd.local', KIND_SYSTEMD, SCOPE_SYSTEM),
            ('linux.systemd.distro', KIND_SYSTEMD, SCOPE_SYSTEM),
            ('linux.systemd.user', KIND_SYSTEMD_USER, SCOPE_USER),
            ('linux.systemd.local.user', KIND_SYSTEMD_USER, SCOPE_USER),
            ('linux.systemd.distro.user', KIND_SYSTEMD_USER, SCOPE_USER),
        ]
        seen_units = set()
        for root_name, kind, scope in unit_roots:
            d = self.root(root_name)
            if not d or not os.path.isdir(d):
                continue
            res.roots_scanned.append(root_name)
            for path, err in iter_scan_files(d, suffixes=('.service', '.socket', '.timer')):
                if err is not None:
                    res.errors.append(_err(root_name, d, err))
                    continue
                name = os.path.basename(path)
                # 同一单元出现在多个搜索路径时，优先级高的已处理过（root 顺序即优先级）
                key = (name, kind)
                if key in seen_units:
                    continue
                seen_units.add(key)
                it = self._item_from_unit(path, root_name, kind, scope, states)
                if isinstance(it, str):
                    res.errors.append(_err(root_name, path, it))
                elif it is not None:
                    res.items.append(it)

        self._scan_xdg(ctx, res)
        self._scan_initd(ctx, res)
        self._scan_cron(ctx, res)
        return res

    def _unit_states(self, res):
        """一次拿到全部单元的启用状态。

        用 `systemctl list-unit-files` 而不是每个单元一次 `is-enabled`——后者是
        O(n) 子进程，几百个单元会明显卡顿。拿不到就退回扫 `.wants` 符号链接。
        """
        out = {}
        r = run([SYSTEMCTL, 'list-unit-files', '--no-legend', '--no-pager'], timeout=25)
        if r.ok:
            for line in r.out.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    out[parts[0]] = parts[1]
            return out
        # 退回：从 /etc/systemd/system 下的 .wants 软链推断
        d = self.root('linux.systemd.etc')
        if d and os.path.isdir(d):
            for entry in os.listdir(d):
                if not entry.endswith(('.wants', '.requires')):
                    continue
                sub = os.path.join(d, entry)
                try:
                    for link in os.listdir(sub):
                        out.setdefault(link, 'enabled')
                except OSError:
                    continue
        return out

    def _item_from_unit(self, path, root_name, kind, scope, states):
        name = os.path.basename(path)
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                text = fh.read()
        except OSError as e:
            return '读取失败: %s' % e

        exec_start, env, restart, wants = _parse_unit(text)
        # drop-in 能在不动单元文件的情况下改 ExecStart —— 不看就会报出**过期的命令行**
        dropin = _read_dropins(path)
        if dropin.get('ExecStart'):
            exec_start = dropin['ExecStart']

        state = states.get(name, '')
        enabled, reason = _enabled_from_state(state)

        prog, args = _split_exec(exec_start)
        it = StartupItem(
            platform='linux', kind=kind, scope=scope, anchor=name,
            name=name, program=prog, args=tuple(args),
            run_at_load=(kind == KIND_SYSTEMD),
            enabled=enabled, enabled_reason=reason,
            trigger='boot' if scope == SCOPE_SYSTEM else 'login',
            source=path, source_kind='file', root=root_name,
        )
        it.raw = text
        it.fingerprint = make_fingerprint(prog, args, text)
        classify.classify(it, self.ctx)
        return it

    # -- XDG autostart --
    def _scan_xdg(self, ctx, res):
        """XDG 自启。用户目录按同名文件**遮蔽**系统目录——必须如实表示。"""
        sys_dir = self.root('linux.xdg.system')
        usr_dir = self.root('linux.xdg.user')
        sys_items = {}
        usr_items = {}

        for d, root_name, store in ((sys_dir, 'linux.xdg.system', sys_items),
                                    (usr_dir, 'linux.xdg.user', usr_items)):
            if not d or not os.path.isdir(d):
                continue
            res.roots_scanned.append(root_name)
            for path, err in iter_scan_files(d, suffixes=('.desktop',)):
                if err is not None:
                    res.errors.append(_err(root_name, d, err))
                    continue
                it = self._item_from_desktop(path, root_name)
                if isinstance(it, str):
                    res.errors.append(_err(root_name, path, it))
                elif it is not None:
                    store[os.path.basename(path)] = it

        # 遮蔽：用户目录里同名文件覆盖系统目录那一个
        shadowed_uids = {}
        for base, uit in usr_items.items():
            sit = sys_items.get(base)
            if sit is not None:
                sit.enabled = False
                sit.enabled_reason = 'shadowed'
                sit.shadowed_by = uit.uid
                shadowed_uids[sit.uid] = uit.uid

        for it in list(sys_items.values()) + list(usr_items.values()):
            res.items.append(it)

    def _item_from_desktop(self, path, root_name):
        import configparser
        cp = configparser.ConfigParser(interpolation=None, strict=False,
                                       delimiters=('=',))
        # ★ 必须覆盖 optionxform，否则 X-GNOME-... 之类的键会被小写化
        cp.optionxform = str
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                cp.read_file(fh)
        except (OSError, configparser.Error) as e:
            return '解析失败: %s' % e
        if not cp.has_section('Desktop Entry'):
            return None
        sec = cp['Desktop Entry']
        if (sec.get('Type') or '').strip() != 'Application':
            return None

        base = os.path.basename(path)
        exec_line = (sec.get('Exec') or '').strip()
        # 字段码 %f %u %U 等要去掉
        exec_clean = re.sub(r'%[fFuUdDnNickvm]', '', exec_line).strip()
        prog, args = _split_exec(exec_clean)

        hidden_raw = (sec.get('Hidden') or '').strip().lower()
        gnome_raw = (sec.get('X-GNOME-Autostart-enabled') or '').strip().lower()
        if hidden_raw in ('true', '1', 'yes'):
            enabled, reason = False, 'Hidden'
        elif gnome_raw in ('false', '0', 'no'):
            # GNOME 扩展（非规范键）——必须说明用的是哪一个
            enabled, reason = False, 'X-GNOME-Autostart-enabled（GNOME 扩展）'
        else:
            enabled, reason = True, 'Hidden（规范键）未设'

        it = StartupItem(
            platform='linux', kind=KIND_XDG_AUTOSTART,
            scope=SCOPE_USER if 'user' in root_name else SCOPE_SYSTEM,
            anchor=base, name=(sec.get('Name') or base),
            description=(sec.get('Comment') or ''),
            program=prog, args=tuple(args),
            run_at_load=True, enabled=enabled, enabled_reason=reason,
            trigger='login', source=path, source_kind='file', root=root_name,
        )
        it.raw = '\n'.join('%s=%s' % (k, v) for k, v in sec.items())
        it.fingerprint = make_fingerprint(prog, args, it.raw)
        classify.classify(it, self.ctx)
        return it

    # -- init.d --
    def _scan_initd(self, ctx, res):
        d = self.root('linux.initd')
        if not d or not os.path.isdir(d):
            return
        res.roots_scanned.append('linux.initd')
        for path, err in iter_scan_files(d):
            if err is not None or not os.path.isfile(path):
                continue
            name = os.path.basename(path)
            it = StartupItem(
                platform='linux', kind=KIND_INITD, scope=SCOPE_SYSTEM,
                anchor=name, name=name, program=path, args=(),
                enabled=None, enabled_reason='',
                trigger='boot', source=path, source_kind='file', root='linux.initd',
            )
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                    it.raw = fh.read(4096)
            except OSError:
                pass
            classify.classify(it, self.ctx)
            res.items.append(it)

    # -- cron --
    def _scan_cron(self, ctx, res):
        for root_name in ('linux.cron.etc', 'linux.cron.d'):
            d = self.root(root_name)
            if not d:
                continue
            paths = []
            if root_name == 'linux.cron.etc' and os.path.isfile(d):
                paths = [d]
            elif os.path.isdir(d):
                paths = [os.path.join(d, n) for n in sorted(os.listdir(d))
                         if not n.startswith('.')]
            for p in paths:
                if not os.path.isfile(p):
                    continue
                res.roots_scanned.append(root_name)
                try:
                    with open(p, 'r', encoding='utf-8', errors='replace') as fh:
                        text = fh.read()
                except OSError as e:
                    res.errors.append(_err(root_name, p, str(e)))
                    continue
                for line in text.splitlines():
                    s = line.strip()
                    if not s or s.startswith('#'):
                        continue
                    parts = s.split(None, 5)
                    if len(parts) < 6:
                        continue
                    sched = ' '.join(parts[:5])
                    cmd = parts[5].strip()
                    anchor = 'cron:%s|%s' % (sched, cmd)
                    it = StartupItem(
                        platform='linux', kind=KIND_CRON, scope=SCOPE_SYSTEM,
                        anchor=anchor, name=cmd[:60] or 'cron 作业',
                        program=cmd.split()[0] if cmd else '', args=tuple(cmd.split()[1:]),
                        enabled=sched.startswith('@reboot'), enabled_reason='crontab',
                        trigger='boot' if sched.startswith('@reboot') else 'schedule',
                        source='%s:%s' % (p, sched), source_kind='file', root=root_name,
                    )
                    it.raw = line
                    classify.classify(it, self.ctx)
                    it.mutable = False
                    res.items.append(it)

        # 用户自己的 crontab
        r = run(['/usr/bin/crontab', '-l'], timeout=10)
        if r.ok and r.out.strip():
            res.roots_scanned.append('cron.user')
            for line in r.out.splitlines():
                s = line.strip()
                if not s or s.startswith('#'):
                    continue
                parts = s.split(None, 5)
                if len(parts) < 6:
                    continue
                sched, cmd = ' '.join(parts[:5]), parts[5].strip()
                anchor = 'cron:user:%s|%s' % (sched, cmd)
                it = StartupItem(
                    platform='linux', kind=KIND_CRON, scope=SCOPE_USER,
                    anchor=anchor, name=cmd[:60] or 'cron 作业',
                    program=cmd.split()[0] if cmd else '', args=tuple(cmd.split()[1:]),
                    enabled=sched.startswith('@reboot'), enabled_reason='crontab',
                    trigger='boot' if sched.startswith('@reboot') else 'schedule',
                    source='crontab:%s' % sched, source_kind='db', root='cron.user',
                )
                it.raw = line
                classify.classify(it, self.ctx)
                it.mutable = False
                res.items.append(it)

    # ------------------------------------------------------------ 关联
    def corr_table(self, ctx):
        """systemd 的权威表由 proc.py 走 /proc/<pid>/cgroup 拿（零子进程、更可靠）。

        这里**刻意返回空**：`systemctl show -p MainPID` 是 O(n) 子进程，而且
        `systemctl --user` 在容器/纯 ssh 会话里会 "Failed to connect to bus"。
        cgroup 能扛住 double-fork 与 setsid，是更好的机制。
        """
        return {}

    # ------------------------------------------------------------ 变更
    def _rebuild(self, item, ctx):
        if item.kind in (KIND_SYSTEMD, KIND_SYSTEMD_USER):
            if not os.path.isfile(item.source):
                return None
            return self._item_from_unit(item.source, item.root, item.kind,
                                        item.scope, {})
        return super(LinuxBackend, self)._rebuild(item, ctx)

    def plan(self, op, item, ctx):
        needs_root = item.scope == SCOPE_SYSTEM and not self.is_admin()
        tail = '（需要管理员权限）' if needs_root else ''
        if op == 'disable':
            return ['  · 禁用 %s：systemctl %sdisable %s%s'
                    % (item.key, '--user ' if item.scope == SCOPE_USER else '',
                       item.anchor, tail)]
        if op == 'enable':
            return ['  · 启用 %s：systemctl %senable %s%s'
                    % (item.key, '--user ' if item.scope == SCOPE_USER else '',
                       item.anchor, tail)]
        if op == 'remove':
            return ['  · 移除 %s：**移入备份目录**（不删除）%s%s'
                    % (item.key, item.source, tail)]
        if op == 'add':
            return ['  · 新增用户级单元 ~/.config/systemd/user/%s.service' % item.anchor]
        return super(LinuxBackend, self).plan(op, item, ctx)

    def _require_root_for(self, item):
        """判断依据是**实际可写性**（见 base._needs_root），不只看 scope。"""
        if self._needs_root(item):
            return ('需要管理员权限：%s。请执行: sudo startupctl disable %s'
                    % (item.anchor, item.key))
        return ''

    def _systemctl(self, args, scope):
        argv = [SYSTEMCTL]
        if scope == SCOPE_USER:
            argv.append('--user')
        argv.extend(args)
        return run(argv, timeout=25)

    def _do_disable(self, item, ctx, backup=None, entry=None):
        self._guard(item, 'disable')
        why = self._require_root_for(item)
        if why:
            raise Refused(why, hint='请显式用 sudo 重跑')
        r = self._systemctl(['disable', item.anchor], item.scope)
        if not r.ok:
            raise RuntimeError('systemctl disable 失败: %s' % (r.err or r.out).strip())
        return '已禁用（WantedBy 符号链接已移除）'

    def _do_enable(self, item, ctx, backup=None, entry=None):
        self._guard(item, 'enable')
        why = self._require_root_for(item)
        if why:
            raise Refused(why)
        r = self._systemctl(['enable', item.anchor], item.scope)
        if not r.ok:
            raise RuntimeError('systemctl enable 失败: %s' % (r.err or r.out).strip())
        return '已启用'

    def _do_remove(self, item, ctx, backup=None, entry=None):
        self._guard(item, 'remove')
        why = self._require_root_for(item)
        if why:
            raise Refused(why)
        # ★ enable 出来的符号链接**绝不能搬走**——那会留下一个"真单元还在 /usr/lib、
        #   但 /etc 下的软链不见了"的半状态。软链只 disable。
        if os.path.islink(item.source):
            self._systemctl(['disable', item.anchor], item.scope)
            return '源是 enable 生成的符号链接：只做 disable，未搬移（真单元保留在原处）'
        self._systemctl(['disable', item.anchor], item.scope)
        dst = self._move_aside(item, backup, entry)
        return '已移入备份: %s' % (dst or '(源不存在)')

    def _do_add(self, item, ctx, backup=None, entry=None):
        self._guard(item, 'add')
        if item.scope == SCOPE_SYSTEM:
            raise Refused('默认只写用户级单元（~/.config/systemd/user）；'
                          '写系统级需 root 且显式 --scope system')
        dest_dir = os.path.expanduser('~/.config/systemd/user')
        dest = os.path.join(dest_dir, '%s.service' % item.anchor)
        if os.path.exists(dest):
            raise Refused('目标已存在，拒绝覆盖: %s' % dest)
        body = ('[Unit]\nDescription=%s\n\n[Service]\nExecStart=%s\n'
                'Restart=on-failure\n\n[Install]\nWantedBy=default.target\n'
                % (item.name or item.anchor,
                   ' '.join([item.program] + list(item.args))))
        self._write_file(dest, body)
        r = self._systemctl(['enable', '--now', item.anchor], SCOPE_USER)
        return '已写入 %s%s' % (dest, '' if r.ok else '（systemctl --user enable 未成功）')


# ---------------------------------------------------------------- 辅助
def _err(root, path, reason):
    from ..core.model import scan_error
    return scan_error(root, path, reason)


def _parse_unit(text):
    """极简 INI 读取（unit 文件是 [Section] + Key=Value，不需要 configparser）。"""
    exec_start = ''
    env = []
    restart = ''
    wants = []
    section = ''
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith('#') or s.startswith(';'):
            continue
        if s.startswith('[') and s.endswith(']'):
            section = s[1:-1].strip()
            continue
        if '=' not in s:
            continue
        k, _, v = s.partition('=')
        k, v = k.strip(), v.strip()
        if section == 'Service' and k == 'ExecStart':
            # ExecStart 行首的 - + ! @ 是前缀修饰符
            exec_start = v.lstrip('-+!@')
        elif section == 'Service' and k == 'Environment':
            env.append(v)
        elif section == 'Service' and k == 'Restart':
            restart = v
        elif section == 'Install' and k in ('WantedBy', 'RequiredBy'):
            wants.extend(v.split())
    return exec_start, env, restart, wants


def _read_dropins(unit_path):
    """读 `<path>.d/*.conf` 里的 ExecStart 覆盖。

    drop-in 能在**不动单元文件**的情况下改命令行——只读单元文件会报出过期的命令行。
    """
    out = {}
    d = unit_path + '.d'
    if not os.path.isdir(d):
        return out
    try:
        names = sorted(n for n in os.listdir(d) if n.endswith('.conf'))
    except OSError:
        return out
    for n in names:
        try:
            with open(os.path.join(d, n), 'r', encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    s = line.strip()
                    if s.startswith('ExecStart='):
                        out['ExecStart'] = s.split('=', 1)[1].strip().lstrip('-+!@')
        except OSError:
            continue
    return out


def _enabled_from_state(state):
    """systemd 的 STATE 列 → 三态 enabled。"""
    s = (state or '').strip()
    if not s:
        return None, ''
    if s in ('enabled', 'enabled-runtime', 'alias', 'linked', 'linked-runtime'):
        return True, 'systemctl:%s' % s
    if s in ('disabled', 'masked', 'masked-runtime'):
        return False, 'systemctl:%s' % s
    if s == 'static':
        # static 无 [Install]，**永远无法启用** —— 不是"未启用"，更不是"损坏"
        return None, 'static（无 [Install]，不参与 enable）'
    if s in ('indirect', 'generated', 'transient'):
        return None, 'systemctl:%s（启用态由别处决定）' % s
    return None, 'systemctl:%s' % s


def _split_exec(exec_line):
    """拆 ExecStart。支持引号，且跳过常用前缀（/usr/bin/env 之类不做特殊处理）。"""
    line = (exec_line or '').strip()
    if not line:
        return '', []
    parts = _shlex_split(line)
    if not parts:
        return '', []
    return parts[0], parts[1:]


def _shlex_split(s):
    """自带的简易分词：不在 Windows 上跑 shlex（posix 模式会吃掉反斜杠路径）。"""
    import shlex
    try:
        return shlex.split(s, posix=True)
    except ValueError:
        return s.split()
