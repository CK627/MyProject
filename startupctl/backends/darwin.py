# -*- coding: utf-8 -*-
"""macOS 后端：launchd plist · 登录项 · BTM · cron。

本机（macOS 27.0.1）实测要点，全部体现在下面的实现里：

1. **`plistlib` 在真实文件上有失败**：Apple 自己的
   `/System/Library/LaunchAgents/com.apple.familycircled.plist` 的 XML 声明里属性
   **没加引号**（`<?xml version=1.0 encoding=UTF-8?>`），Expat 报错而 Apple 的解析器
   宽容。**"去掉 prolog 重试"无效**（`<plist version=1.0>` 仍不合法）。有效回退是
   `/usr/bin/plutil -convert xml1 -o -`（系统自带，不算第三方依赖）。不做这步就静默
   少 1 个文件——"静默少一个"正是本工具最该避免的失败形态。

2. **存在解析为空 dict 的 plist**：`com.google.keystone.agent.plist` 等是 181 字节
   的占位文件，没有 Label 也没有 Program。缺 Label 时必须回落到**文件名词干**。

3. **必须跟随符号链接**：`/Library/LaunchAgents/com.oracle.java.Java-Updater.plist`
   指向 `.plugin` 目录内的真文件；`/System/Library/LaunchAgents` 里有 11 个。

4. **`enabled` 是三态**：`launchctl print-disabled` 只列**有覆盖记录**的标签，
   `=> enabled` 的意思是"被显式重新启用"。**标签不在表里 = 没有覆盖 = 回落到 plist
   自身的 `Disabled` 键**。把"在表里"当成"已禁用"会把结论整个弄反。

5. **`launchctl print` 无需 root**（实测 uid 501 可读 `system` 域与 `gui/501` 域），
   所以系统守护进程的关联是**可用**的——只有*变更*才需要 root。

6. **`sfltool dumpbtm` 绝不调用**：实测非交互下挂起超过 120 秒（授权/性能双重问题），
   耗时在 15 秒到 300 秒以上剧烈波动。改为直读 BTM 数据库（见 `_scan_btm`）。
"""
import os
import plistlib
import re

from ..core import classify, proc as proc_mod, roots as roots_mod
from ..core.model import (KIND_BTM, KIND_CRON, KIND_LAUNCHD_AGENT,
                          KIND_LAUNCHD_DAEMON, KIND_LOGIN_ITEM, ORIGIN_OS,
                          SCOPE_SYSTEM, SCOPE_USER, StartupItem, make_fingerprint)
from ..core.safety import Refused
from ..core.utils import run, realpath_soft
from .base import Backend, iter_scan_files

PLUTIL = '/usr/bin/plutil'
LAUNCHCTL = '/bin/launchctl'
OSASCRIPT = '/usr/bin/osascript'

# 授权失败：TCC 未授予"自动化"权限时 osascript 的报错号
TCC_DENIED = '-1743'


# ---------------------------------------------------------------- plist 读取
def load_plist(path):
    """读 plist，带 plutil 回退。返回 (data, error)。

    不用 `plistlib.load(fh)` 而用 `loads(raw)`：我们要先看一眼原始字节才能判断
    该不该走 plutil 回退（二进制格式 bplist 不需要）。"""
    import plistlib
    try:
        with open(path, 'rb') as fh:
            raw = fh.read()
    except OSError as e:
        return None, '读取失败: %s' % e
    try:
        return plistlib.loads(raw), None
    except Exception as first_err:
        if raw[:6] == b'bplist':
            # 二进制 plist 解析失败说明文件真的坏了，plutil 也救不了
            return None, 'plist 解析失败（二进制格式）: %s' % first_err
    # XML 回退：Apple 会写出属性不加引号的 plist，Expat 不认而 plutil 认
    res = run([PLUTIL, '-convert', 'xml1', '-o', '-', path], timeout=10)
    if not res.ok:
        return None, 'plist 解析失败且 plutil 转换失败: %s' % (res.err or first_err)
    try:
        return plistlib.loads(res.out.encode('utf-8')), None
    except Exception as e:
        return None, 'plist 解析失败（plutil 转换后仍失败）: %s' % e


def _plist_program(data):
    """从 plist 里解析「到底会执行什么」。返回 (program, args)。

    `Program` 与 `ProgramArguments` 可以同时存在：此时 `ProgramArguments[0]` 是
    argv[0]，真正 exec 的是 `Program`（本机 com.docker.socket.plist 就是这个形态）。
    """
    prog = data.get('Program') or ''
    args = data.get('ProgramArguments') or []
    if isinstance(args, str):
        args = [args]
    args = [str(a) for a in args]
    if not prog and args:
        prog = args[0]
    # 相对 argv[0]（如 ["sh","-c",...]）不是可执行文件路径，作展示用但没有 program
    if prog and not prog.startswith('/'):
        # 常见 wrapper：sh -c "..."，真身藏在字符串里
        if prog in ('sh', 'bash', 'zsh', 'dash', 'ksh') and len(args) >= 3 and args[1] == '-c':
            return '', args
        return '', args
    return prog, args


def _plist_trigger(data):
    if data.get('StartCalendarInterval'):
        return 'schedule'
    if data.get('StartInterval'):
        return 'periodic'
    if data.get('WatchPaths') or data.get('QueueDirectories'):
        return 'demand'
    if data.get('Sockets'):
        return 'socket'
    if data.get('RunAtLoad'):
        return 'boot'
    return 'demand'


# ---------------------------------------------------------------- 后端
class DarwinBackend(Backend):
    platform = 'darwin'
    name = 'launchd'

    # ------------------------------------------------------------ 扫描
    def scan(self, ctx):
        res = self.new_result(ctx)
        roots = self.roots
        disabled = self._disabled_map(ctx, res)

        launchd_roots = [
            ('darwin.sys.daemons', KIND_LAUNCHD_DAEMON, SCOPE_SYSTEM),
            ('darwin.sys.agents', KIND_LAUNCHD_AGENT, SCOPE_SYSTEM),
            ('darwin.daemons', KIND_LAUNCHD_DAEMON, SCOPE_SYSTEM),
            ('darwin.agents', KIND_LAUNCHD_AGENT, SCOPE_SYSTEM),
            ('darwin.user.agents', KIND_LAUNCHD_AGENT, SCOPE_USER),
        ]
        for root_name, kind, scope in launchd_roots:
            d = roots.get(root_name, '')
            if not d:
                continue
            if not os.path.isdir(d):
                continue
            res.roots_scanned.append(root_name)
            for path, err in iter_scan_files(d, suffixes=('.plist',)):
                if err is not None:
                    res.errors.append(proc_mod.scan_error(root_name, d, err))
                    continue
                if not os.path.isfile(path):
                    continue
                item = self._item_from_plist(path, root_name, kind, scope, disabled)
                if isinstance(item, str):
                    res.errors.append(proc_mod.scan_error(root_name, path, item))
                elif item is not None:
                    res.items.append(item)

        # ⚠️ 下面三项读的是**系统自己的数据库/服务**（osascript、BTM 文件、crontab），
        #    不是路径可重定向的目录，所以 STARTUPCTL_ROOTS 对它们无效。夹具模式下
        #    必须整段跳过——否则测试会去读**真机**的登录项与 crontab，而
        #    "测试绝不碰真机"是这套安全断言成立的前提。
        #    （安全不变量第 12 条会断言输出里没有夹具之外的路径，正是它抓出了这里。）
        if not roots_mod.remapped():
            # 登录项（AppleScript，需 TCC 授权）
            self._scan_login_items(ctx, res)
            # BTM（直读数据库）—— 必须在 plist 扫描**之后**：它对同一个 plist 而言是
            # **属性来源**而不是第二个启动项，要按源路径折进已扫到的项，不能另发一条。
            self._scan_btm(ctx, res)
            # cron（只能看到自己的 tab，除非 root）
            self._scan_cron(ctx, res)
        # 遗留 StartupItems：只作信息展示（纯路径扫描，夹具下也可跑）
        self._scan_legacy_startupitems(ctx, res)

        return res

    # -- launchd 单项 --
    def _item_from_plist(self, path, root_name, kind, scope, disabled):
        data, err = load_plist(path)
        if err:
            return err
        if not isinstance(data, dict):
            return 'plist 顶层不是字典（%s）' % type(data).__name__

        # ★ 空 plist（Google keystone 的 181 字节占位文件）：没有 Label 也没有
        #   Program。回落到文件名词干，绝不 KeyError，也绝不静默丢掉。
        base = os.path.basename(path)
        for suf in ('.plist',):
            if base.endswith(suf):
                base = base[:-len(suf)]
        anchor = str(data.get('Label') or base)
        warnings = []
        if not data.get('Label'):
            warnings.append('plist 未声明 Label，按文件名词干 %r 处理' % base)

        prog, args = _plist_program(data)
        run_at_load = bool(data.get('RunAtLoad'))

        # enabled 三态
        enabled, reason = self._enabled_state(anchor, data, disabled)

        it = StartupItem(
            platform='darwin', kind=kind, scope=scope, anchor=anchor,
            name=str(data.get('Label') or base),
            program=prog, args=tuple(args),
            run_at_load=run_at_load, enabled=enabled, enabled_reason=reason,
            trigger=_plist_trigger(data),
            source=path, source_kind='file', root=root_name,
            raw='', warnings=tuple(warnings),
        )
        it.raw = _render_plist_summary(data)
        it.fingerprint = make_fingerprint(prog, args, it.raw)
        return classify.classify(it, self.ctx)

    def _enabled_state(self, label, data, disabled):
        """三态 enabled。依据优先级：显式覆盖 > plist 自身 > 未知。

        `launchctl print-disabled` 的语义很容易搞反：它**只列有覆盖记录的标签**，
        且 `=> enabled` 表示"被显式重新启用"。不在表里 = 没有覆盖。
        """
        if label in disabled:
            v = disabled[label]
            if v is True:
                return False, 'override:disabled'
            if v is False:
                return True, 'override:enabled'
        if 'Disabled' in data:
            return (not bool(data.get('Disabled'))), 'Disabled'
        if 'RunAtLoad' in data:
            return bool(data.get('RunAtLoad')), 'RunAtLoad'
        return None, ''          # 无覆盖、文件也没写 → 未知（不是"已启用"）

    def _disabled_map(self, ctx, res):
        """读两个域的 print-disabled。非 root 可读（实测）。"""
        out = {}
        for domain in ('system', 'gui/%d' % os.getuid()):
            r = run([LAUNCHCTL, 'print-disabled', domain], timeout=10)
            if not r.ok:
                if r.reason == 'denied':
                    res.errors.append(proc_mod.scan_error(
                        'launchctl', domain, '权限不足，禁用状态未知', needs_root=True))
                continue
            for m in re.finditer(r'"([^"]+)"\s*=>\s*(disabled|enabled)', r.out):
                out[m.group(1)] = (m.group(2) == 'disabled')
        return out

    # -- 登录项 --
    def _scan_login_items(self, ctx, res):
        """AppleScript 读登录项。**首次调用会弹 TCC 授权框**，无头环境下失败。

        这不是异常情况，是一等公民的预期失败——必须给出可操作的提示，绝不崩。
        （此前观测到的 >120 秒挂起就是授权框在等人点；脚本本身只要 0.2–0.4 秒。）
        """
        script = ('tell application "System Events" to get the name of every login item '
                  '& linefeed & (get the path of every login item)')
        r = run([OSASCRIPT, '-e', script], timeout=15)
        if not r.ok:
            if TCC_DENIED in (r.err or '') or TCC_DENIED in (r.out or '') or r.reason == 'denied':
                res.errors.append(proc_mod.scan_error(
                    'login-items', 'System Events',
                    '未获「自动化」授权（AppleScript 错误 %s）' % TCC_DENIED,
                    detail='到 系统设置 → 隐私与安全性 → 自动化 允许终端控制「系统事件」'))
            elif r.reason == 'timeout':
                res.errors.append(proc_mod.scan_error(
                    'login-items', 'System Events', '读取超时（可能有授权弹窗在等待确认）'))
            return
        lines = r.out.split('\n')
        names = [s.strip() for s in lines[0].split(',') if s.strip()] if lines else []
        paths = [s.strip() for s in lines[1].split(',') if s.strip()] if len(lines) > 1 else []
        for idx, nm in enumerate(names):
            p = paths[idx] if idx < len(paths) else ''
            anchor = self._login_item_anchor(nm, p)
            it = StartupItem(
                platform='darwin', kind=KIND_LOGIN_ITEM, scope=SCOPE_USER,
                anchor=anchor, name=nm, program=p, args=(),
                enabled=True, enabled_reason='login-item',
                trigger='login', source=p or ('loginitem:%s' % nm),
                source_kind='db', root='login-items',
            )
            # 登录项按定义就是"会随登录启动"的；分类照常跑（/Applications 下 → 三方）
            it.raw = '登录项: %s\n路径: %s' % (nm, p or '(未提供)')
            classify.classify(it, self.ctx)
            # 登录项无法由本工具直接改（需 System Settings 或私有 API），标记为不可改
            it.mutable = False
            it.origin_evidence = (it.origin_evidence or '') + '；登录项需在系统设置中管理'
            res.items.append(it)

    def _login_item_anchor(self, name, path):
        """登录项的稳定身份：优先 bundle id，其次 app 路径基名。"""
        if path and '.app' in path:
            base = os.path.basename(path.rstrip('/'))
            if base.endswith('.app'):
                base = base[:-4]
            return 'loginitem:%s' % base
        return 'loginitem:%s' % (name or 'unnamed')

    # -- BTM --
    def _scan_btm(self, ctx, res):
        """直读 BTM 数据库（**绝不调用 sfltool**）。

        已实测：`BackgroundItems-v18-*.btm` 是 NSKeyedArchiver 的 plist，权限 644
        root:wheel，`plistlib` 可解析（`$objects` 上千条），能取出真实记录。
        这是系统设置里「登录项与扩展」那一屏的来源。

        schema 未公开文档化 → **尽力而为**：任何一步失败都降级为 warning，
        绝不崩、绝不静默当没这回事。
        """
        d = self.root('darwin.btm')
        if not d or not os.path.isdir(d):
            return
        try:
            names = [n for n in os.listdir(d)
                     if n.startswith('BackgroundItems-v') and n.endswith('.btm')]
        except OSError as e:
            res.errors.append(proc_mod.scan_error('darwin.btm', d, str(e)))
            return
        if not names:
            return
        res.roots_scanned.append('darwin.btm')

        # 取版本号最大的那一批（v18 里还有每用户一个 UUID 后缀文件）
        def vkey(n):
            m = re.search(r'-v(\d+)', n)
            return int(m.group(1)) if m else 0
        top_v = max(vkey(n) for n in names)
        files = [os.path.join(d, n) for n in sorted(names) if vkey(n) == top_v]

        # 已扫到的**文件型**项，按 realpath 索引 —— BTM 记录若指向同一个 plist，
        # 就是同一个启动项，只是多了一份"系统设置里的开关状态"。
        by_source = {}
        for it in res.items:
            if it.source_kind == 'file' and it.source:
                by_source[realpath_soft(it.source)] = it

        seen = set()
        warn_once = False
        for f in files:
            try:
                recs = _btm_records(f)
            except Exception as e:                                # noqa: BLE001
                if not warn_once:
                    res.errors.append(proc_mod.scan_error(
                        'darwin.btm', f, 'BTM 解析失败（schema 可能已变）: %s' % e))
                    warn_once = True
                continue
            for r in recs:
                ident = r.get('identifier') or ''
                if not ident or ident in seen:
                    continue
                seen.add(ident)

                # ---- 折叠：BTM 指向已扫到的 plist → 只补状态，不另发一条 ----
                target = self._btm_target_item(r, by_source)
                if target is not None:
                    self._fold_btm_into(target, r)
                    continue

                it = StartupItem(
                    platform='darwin', kind=KIND_BTM, scope=SCOPE_USER,
                    anchor=ident.strip(), name=r.get('name') or ident,
                    program=r.get('executable') or '', args=(),
                    enabled=r.get('enabled'), enabled_reason='btm',
                    trigger='login', source=r.get('url') or ('btm:%s' % ident),
                    source_kind='db', root='darwin.btm',
                )
                it.raw = ('BTM 记录（来自系统设置「登录项与扩展」的同一份数据库）\n'
                          '  标识: %s\n  数据库原始标识: %s\n  名称: %s\n'
                          '  开发者: %s\n  类型: %s\n  Flags: %s\n'
                          '  Disposition: %s\n  URL: %s\n  可执行: %s'
                          % (ident, r.get('raw_identifier', ''), r.get('name', ''),
                             r.get('developer', ''), r.get('type', ''),
                             r.get('flags', ''), r.get('disposition', ''),
                             r.get('url', ''), r.get('executable', '') or '(未记录)'))
                it.fingerprint = make_fingerprint(it.program, (), it.raw)
                classify.classify(it, self.ctx)
                # BTM 的启用态由系统数据库管理，本工具不改（改要靠系统设置）
                it.mutable = False
                res.items.append(it)

    def _btm_target_item(self, rec, by_source):
        """BTM 记录指向一个已扫到的 plist 吗？是则返回那一项。

        BTM 的 url 有两种形态：绝对 `file:///Library/LaunchDaemons/x.plist`
        （对应一个 launchd 项）与相对 `Contents/PlugIns/X.appex`
        （app 扩展，确实是**独立**的东西，不该折叠）。
        """
        raw = rec.get('url') or ''
        if not raw:
            return None
        path = raw
        if path.startswith('file://'):
            path = path[len('file://'):]
        if not path.startswith('/'):
            return None                      # 相对路径 = app 扩展，独立项
        try:
            from urllib.parse import unquote
            path = unquote(path)
        except Exception:
            pass
        return by_source.get(realpath_soft(path))

    def _fold_btm_into(self, item, rec):
        """把 BTM 的状态折进已有项。

        BTM 是「系统设置 → 登录项与扩展」那一屏的真实来源，所以它的 disposition
        是用户视角的权威状态。但**只在 launchd 自己判不出来时才用它覆盖**：
        两边都有明确结论且不一致时，加一条 warning 让人去看，而不是替用户裁决
        —— 位域语义只有一个对照样本（bit0），拿它去推翻已有结论风险太大。
        """
        btm_enabled = rec.get('enabled')
        note = 'BTM: %s' % (rec.get('disposition') or '?')
        if item.enabled is None and btm_enabled is not None:
            item.enabled = btm_enabled
            item.enabled_reason = 'btm（launchd 自身未声明，取系统设置的状态）'
        elif btm_enabled is not None and item.enabled is not None \
                and btm_enabled != item.enabled:
            w = ('系统设置里的状态（%s）与 plist 的声明（%s）不一致——'
                 '以系统设置为准的是"实际会不会跑"，建议人工确认'
                 % ('已启用' if btm_enabled else '已禁用', item.enabled_text()))
            if w not in item.warnings:
                item.warnings = tuple(list(item.warnings) + [w])
        if rec.get('developer'):
            item.vendor_name = item.vendor_name or rec['developer']
        item.raw = (item.raw or '') + '\n\n— BTM（系统设置「登录项与扩展」的同一份记录）—\n' \
            + '  %s\n  Type: %s\n  Flags: %s\n  开发者: %s' % (
                note, rec.get('type', ''), rec.get('flags', ''), rec.get('developer', ''))

    # -- cron --
    def _scan_cron(self, ctx, res):
        """只能看自己的 crontab。别人家的 tab 在 /var/at/tabs 且 0700 root，需 root。

        ⚠️ 这必须作为**覆盖率局限**如实报出，而不是静默给出一个短列表——
        "我只看了一个用户"和"这台机器上只有这些"是两件事。
        """
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
                sched, cmd = ' '.join(parts[:5]), parts[5]
                anchor = 'cron:%s|%s' % (sched, cmd.strip())
                it = StartupItem(
                    platform='darwin', kind=KIND_CRON, scope=SCOPE_USER,
                    anchor=anchor, name=(cmd.strip()[:60] or 'cron 作业'),
                    program=cmd.strip().split()[0] if cmd.strip() else '',
                    args=tuple(cmd.strip().split()[1:]),
                    enabled=(sched.startswith('@reboot')), enabled_reason='crontab',
                    trigger='boot' if sched.startswith('@reboot') else 'schedule',
                    source='crontab:%s' % sched, source_kind='db', root='cron.user',
                )
                it.raw = 'crontab 行:\n%s' % line
                classify.classify(it, self.ctx)
                it.mutable = False
                res.items.append(it)
        # 他人 tab 读不到：如实报出，但**不**标 needs_root。
        #
        # 取舍理由：needs_root=True 会让整次扫描判为不完整，而 `clean` 在扫描不完整时
        # 拒绝运行。/var/at/tabs 在 macOS 上是恒定的 0700，于是 clean 会**永远**拒绝
        # 执行——这不是更安全，而是把一个用不了的命令推给用户去绕过。
        # 这条盲区不影响任何决策：里面装的是**别人的** crontab，用户本来就改不了
        # （系统级项需要 root，clean 会跳过并提示）。所以报为信息项。
        tabs = self.root('darwin.cron.tabs')
        if tabs and os.path.isdir(tabs) and not os.access(tabs, os.R_OK):
            res.errors.append(proc_mod.scan_error(
                'darwin.cron.tabs', tabs,
                '权限不足，其他用户的 crontab 未扫描（不影响本用户的清理）',
                detail='这些作业属于其他用户，需要 root 才能读；本工具不会改动它们'))

    # -- 遗留 --
    def _scan_legacy_startupitems(self, ctx, res):
        for name in ('darwin.startupitems', 'darwin.sys.startupitems'):
            d = self.root(name)
            if not d or not os.path.isdir(d):
                continue
            try:
                entries = [e for e in os.listdir(d) if not e.startswith('.')]
            except OSError:
                continue
            if not entries:
                continue
            # macOS 27 上 SystemStarter 早已移除：目录存在也不生效。
            res.errors.append(proc_mod.scan_error(
                name, d, '遗留 StartupItems 目录非空，但系统已不再读取它（仅供参考）',
                detail='条目: %s' % ', '.join(entries[:5])))

    # ------------------------------------------------------------ 关联
    def corr_table(self, ctx):
        """PID → Label 权威表。**无需 root**（实测），所以系统守护进程也能关联上。"""
        out = {}
        r = run([LAUNCHCTL, 'list'], timeout=10)
        if not r.ok:
            return out
        for line in r.out.splitlines():
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            pid_s, _, label = parts[0].strip(), parts[1], parts[2].strip()
            if pid_s.isdigit():
                out[int(pid_s)] = label
        return out

    def service_state(self, label):
        """`launchctl print <domain>/<label>` 取单个服务的状态。

        实测无需 root，能拿到 state / pid / program（**已解析**的可执行路径）。
        """
        for domain in ('system', 'gui/%d' % os.getuid()):
            r = run([LAUNCHCTL, 'print', '%s/%s' % (domain, label)], timeout=10)
            if not r.ok:
                continue
            state = ''
            pid = None
            prog = ''
            m = re.search(r'^\s*state = (.+)$', r.out, re.M)
            if m:
                state = m.group(1).strip()
            m = re.search(r'^\s*pid = (\d+)$', r.out, re.M)
            if m:
                pid = int(m.group(1))
            m = re.search(r'^\s*program = (.+)$', r.out, re.M)
            if m:
                prog = m.group(1).strip()
            return {'domain': domain, 'state': state, 'pid': pid, 'program': prog}
        return None

    # ------------------------------------------------------------ 变更
    def _rebuild(self, item, ctx):
        """从活源重建（TOCTOU 防线）。plist 必须重读——文件内容可能已被替换。"""
        if item.kind in (KIND_LAUNCHD_DAEMON, KIND_LAUNCHD_AGENT):
            fresh = self._item_from_plist(item.source, item.root, item.kind,
                                          item.scope, {})
            if isinstance(fresh, str) or fresh is None:
                return None
            return fresh
        return super(DarwinBackend, self)._rebuild(item, ctx)

    def plan(self, op, item, ctx):
        needs_root = item.scope == SCOPE_SYSTEM and not self.is_admin()
        tail = '（需要管理员权限）' if needs_root else ''
        src = item.source or item.anchor
        if op == 'disable':
            return ['  · 禁用 %s：改 plist 加 Disabled=true 并移走 RunAtLoad，'
                    '再 launchctl bootout %s%s' % (item.key, src, tail)]
        if op == 'enable':
            return ['  · 启用 %s：去掉 Disabled / 恢复 RunAtLoad，'
                    '再 launchctl bootstrap %s%s' % (item.key, src, tail)]
        if op == 'remove':
            return ['  · 移除 %s：**移入备份目录**（不删除）%s，再 bootout%s'
                    % (item.key, src, tail)]
        if op == 'add':
            return ['  · 新增自启项（用户级 ~/Library/LaunchAgents）']
        return super(DarwinBackend, self).plan(op, item, ctx)

    def _require_root_for(self, item):
        """改不动就别假装能做到。判断依据是**实际可写性**（见 base._needs_root）。"""
        if self._needs_root(item):
            return ('需要管理员权限：%s。请执行: sudo startupctl disable %s'
                    % (item.source or item.anchor, item.key))
        return ''

    def _do_disable(self, item, ctx, backup=None, entry=None):
        self._guard(item, 'disable')
        why = self._require_root_for(item)
        if why:
            raise Refused(why, hint='本工具不会在变更中途弹密码；请显式用 sudo 重跑')
        data, err = load_plist(item.source)
        if err:
            raise RuntimeError(err)
        data['Disabled'] = True
        data.pop('RunAtLoad', None)
        self._write_plist_preserving(item.source, data)
        self._bootout(item)
        return '已禁用（Disabled=true，RunAtLoad 已移除）'

    def _do_enable(self, item, ctx, backup=None, entry=None):
        self._guard(item, 'enable')
        why = self._require_root_for(item)
        if why:
            raise Refused(why)
        data, err = load_plist(item.source)
        if err:
            raise RuntimeError(err)
        data.pop('Disabled', None)
        data['RunAtLoad'] = True
        self._write_plist_preserving(item.source, data)
        self._bootstrap(item)
        return '已启用（Disabled 已移除，RunAtLoad=true）'

    def _do_remove(self, item, ctx, backup=None, entry=None):
        self._guard(item, 'remove')
        why = self._require_root_for(item)
        if why:
            raise Refused(why)
        self._bootout(item)
        dst = self._move_aside(item, backup, entry)
        return '已移入备份: %s' % (dst or '(源不存在)')

    def _do_add(self, item, ctx, backup=None, entry=None):
        self._guard(item, 'add')
        import plistlib
        label = item.anchor or item.key
        dest_dir = os.path.expanduser('~/Library/LaunchAgents')
        if item.scope == SCOPE_SYSTEM:
            raise Refused('默认只写用户级自启项（~/Library/LaunchAgents）；'
                          '写系统级需 root 且显式指定 --scope system')
        dest = os.path.join(dest_dir, '%s.plist' % label)
        if os.path.exists(dest):
            raise Refused('目标已存在，拒绝覆盖: %s' % dest)
        payload = {
            'Label': label,
            'ProgramArguments': [item.program] + list(item.args),
            'RunAtLoad': bool(item.run_at_load),
        }
        os.makedirs(dest_dir, exist_ok=True)
        with open(dest, 'wb') as fh:
            plistlib.dump(payload, fh)
        r = run([LAUNCHCTL, 'bootstrap', 'gui/%d' % os.getuid(), dest], timeout=15)
        return '已写入 %s%s' % (dest, '' if r.ok else '（bootstrap 未成功，下次登录仍会加载）')

    def _write_plist_preserving(self, path, data):
        """回写 plist。原来是什么格式就尽量写回什么格式（XML in → XML out）。"""
        import plistlib
        fmt = plistlib.FMT_XML
        try:
            with open(path, 'rb') as fh:
                if fh.read(6) == b'bplist':
                    fmt = plistlib.FMT_BINARY
        except OSError:
            pass
        tmp = path + '.startupctl-tmp'
        with open(tmp, 'wb') as fh:
            plistlib.dump(data, fh, fmt=fmt)
        os.replace(tmp, path)

    def _bootout(self, item):
        for domain in ('gui/%d' % os.getuid(), 'system'):
            run([LAUNCHCTL, 'bootout', '%s/%s' % (domain, item.anchor)], timeout=10)

    def _bootstrap(self, item):
        domain = 'system' if item.scope == SCOPE_SYSTEM else 'gui/%d' % os.getuid()
        run([LAUNCHCTL, 'bootstrap', domain, item.source], timeout=15)


# ---------------------------------------------------------------- 辅助
def _render_plist_summary(data):
    """把 plist 摘要成可读文本（show --raw 用）。不 dump 完整 dict——
    有的 plist 带了巨大的 EnvironmentVariables，全打出来反而看不清重点。"""
    keys = ('Label', 'Program', 'ProgramArguments', 'RunAtLoad', 'KeepAlive',
            'Disabled', 'StartInterval', 'StartCalendarInterval', 'WatchPaths',
            'UserName', 'GroupName', 'LimitLoadToSessionType', 'StandardOutPath',
            'StandardErrorPath', 'ProcessType', 'MachServices', 'EnvironmentVariables')
    lines = []
    for k in keys:
        if k in data:
            v = data[k]
            if k == 'EnvironmentVariables' and isinstance(v, dict):
                v = ', '.join('%s=%s' % (a, b) for a, b in list(v.items())[:6])
            lines.append('  %s: %s' % (k, v))
    return '\n'.join(lines)


def _btm_objs(path):
    """解析 BTM 文件，返回 ($objects, $top)。"""
    import plistlib
    with open(path, 'rb') as fh:
        d = plistlib.load(fh)
    return d.get('$objects') or [], d.get('$top') or {}


def _btm_records(path):
    """从 BTM 的 NSKeyedArchiver plist 里抽出记录（**已实测的路径**）。

    实测（macOS 27.0.1）结构：

        $top['userStore']  → dict{records: UID → dict{NS.objects: [UID…]}}
        每条记录 dict 的字段：
            identifier / name / developerName / bundleIdentifier
            executablePath / url / disposition / flags / type
            generation / teamIdentifier / programArguments / sha256 …

    四个必须处理的细节（踩过才知道）：

    1. **`identifier` 本身是 UID，要二次解引用**（不是字符串）。`url` 同理，且是
       NSURL 形态 `{NS.base, NS.relative}`，要拼。
    2. **标识里的数字前缀是标志位、不是 generation**（实测只有 1/82 巧合相等；
       取值 2/4/8/64/2048 全是 2 的幂）。所以锚点要**剥掉前缀**取真正的 bundle id，
       前缀原样留在 raw 里供审计。
    3. **`disposition` 是位域，bit0 = 启用**（与 sfltool 的
       `[enabled, allowed, notified] (0xb)` / `[disabled, allowed, not notified]`
       对照吻合：0xb=1011 启用，0b0010 禁用）。
    4. **开发者容器记录要滤掉**：`Google LLC`、`Microsoft Corporation` 这类
       developer 条目没有 url、标识不含点，收进来只是噪声（真正的条目
       `com.google.GoogleUpdater.wake` 是单独一条）。

    失败由调用方降级成 warning —— 绝不崩。
    """
    objs, top = _btm_objs(path)
    if not objs:
        return []

    def deref(x, depth=0):
        while isinstance(x, plistlib.UID) and depth < 20:
            i = x.data
            if not (0 <= i < len(objs)):
                return None
            x = objs[i]
            depth += 1
        return x

    store = deref(top.get('userStore'))
    if not isinstance(store, dict):
        return []
    recs_obj = deref(store.get('records'))
    if isinstance(recs_obj, dict):
        arr = deref(recs_obj.get('NS.objects'))
    else:
        arr = deref(recs_obj)
    if not isinstance(arr, (list, tuple)):
        return []

    out = []
    for raw_rec in arr:
        rec = deref(raw_rec)
        if not isinstance(rec, dict):
            continue
        ident = deref(rec.get('identifier'))
        if not isinstance(ident, str) or not ident.strip():
            continue
        ident = ident.strip()
        url = _btm_url(deref(rec.get('url')), deref)
        # 滤掉开发者容器（无 url 且标识不像 bundle id）
        if not url and '.' not in ident:
            continue
        anchor = re.sub(r'^\d+\.', '', ident)
        if not anchor:
            continue
        prog = deref(rec.get('executablePath'))
        if not isinstance(prog, str) or prog == '$null':
            prog = ''
        disp = rec.get('disposition')
        flags = rec.get('flags')
        dev = deref(rec.get('developerName'))
        # ★ 开发者容器（type=0x20）：它们只有开发者/产品名、没有 url、也没有可执行
        #   文件，是 BTM 内部的分类节点而不是启动项。收进来只会让列表多出一堆
        #   "Adobe Acrobat Reader DC" 之类的噪声条目。
        if _btm_type_code(rec.get('type')) == 0x20:
            continue
        out.append({
            'identifier': anchor,
            'raw_identifier': ident,
            'name': (deref(rec.get('name')) or anchor),
            'developer': dev if isinstance(dev, str) else '',
            'type': _btm_type(rec.get('type')),
            'flags': str(flags if flags is not None else ''),
            'disposition': _disposition_text(disp),
            'executable': prog,
            'url': url,
            'enabled': _btm_enabled(disp),
        })
    return out


def _btm_url(u, deref, depth=0):
    """解 NSURL：{NS.base, NS.relative} → 可读路径。

    NS.relative 可能是 file:// 绝对 URL（普通项），也可能是相对片段（插件，
    相对于所属 app，如 `Contents/PlugIns/X.appex`）；NS.base 是指向另一个
    NSURL 的 UID。两者都要**再解一层引用**——不解就只能拿到 UID 而丢掉路径。

    ⚠️ 空值在归档里是字符串 `'$null'`（**真值**！）而不是 None。不显式判它，
    "无 url"的判断就会全部失效——开发者容器正是靠这一条漏进来的。
    """
    if depth > 6:
        return ''
    u = deref(u)
    if isinstance(u, str):
        return '' if u == '$null' else u
    if not isinstance(u, dict):
        return ''
    rel = deref(u.get('NS.relative'))
    base = deref(u.get('NS.base'))
    rel_s = rel if isinstance(rel, str) else ''
    base_s = _btm_url(base, deref, depth + 1) if isinstance(base, dict) else ''
    if '://' in rel_s or rel_s.startswith('/'):
        return rel_s
    if base_s and rel_s:
        return base_s.rstrip('/') + '/' + rel_s.lstrip('/')
    return rel_s or base_s


def _btm_type_code(v):
    """type 的整数值（解不出返回 None）。"""
    try:
        if hasattr(v, 'data'):
            return int(v.data)
        return int(v)
    except (TypeError, ValueError):
        return None


def _btm_type(v):
    """type 位域 → 可读名（取值来自本机 sfltool 实测输出）。"""
    n = _btm_type_code(v)
    if n is None:
        return str(v if v is not None else '')
    names = {0x20: 'developer', 0x10: 'daemon', 0x8: 'agent', 0x2: 'app',
             0x10010: 'legacy daemon', 0x10008: 'legacy agent'}
    if n in names:
        return '%s (0x%x)' % (names[n], n)
    return '0x%x' % n


def _first_str(d, keys):
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ''


def _disposition_int(v):
    try:
        import plistlib
        if isinstance(v, plistlib.UID):
            v = v.data
        return int(v)
    except (TypeError, ValueError):
        return None


def _disposition_text(v):
    """disposition 位域 → 文本。

    **只断言我们有对照样本的位**：bit0=启用/禁用（与 sfltool 的
    `[enabled, allowed, notified] (0xb)` 及 `[disabled, allowed, not notified]`
    对照吻合），bit1=allowed。其余位原样以十六进制给出——只有一个样本时
    硬编位名就是编造，宁可承认不知道。
    """
    n = _disposition_int(v)
    if n is None:
        return str(v if v is not None else '')
    words = ['enabled' if (n & 0x1) else 'disabled']
    if n & 0x2:
        words.append('allowed')
    return '[%s] (0x%x)' % (', '.join(words), n)


def _btm_enabled(v):
    """enabled = bit0。判不了返回 None（三态），不猜。"""
    n = _disposition_int(v)
    if n is None:
        return None
    return bool(n & 0x1)
