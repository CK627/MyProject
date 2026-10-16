# -*- coding: utf-8 -*-
"""Windows 后端：注册表 Run/RunOnce · 启动文件夹 · 服务 · 计划任务。

**贯穿全篇的一条原则：绝不解析本地化的命令行输出。**

`tasklist` / `sc query` / `schtasks /fo CSV` 的输出在中文 Windows 上是本地化的
（`tasklist` 打「映像名称」，列偏移都不同）——用它们写出的后端会在英文系统上"正常
工作"、在中文系统上**静默误解析**，而那正是本项目用户所处的环境。所以：

  · 服务  → 读注册表 `HKLM\\SYSTEM\\CurrentControlSet\\Services\\<name>`
             （`Start` 是普通 DWORD：2=自动 3=手动 4=禁用 0=boot 1=system），
             这是**最可靠的自动启动判据**且跨版本一致。
  · 计划任务 → 读 `%SystemRoot%\\System32\\Tasks\\<path>` 的 XML，
             用 `xml.etree` 解析——版本无关、语言无关。
  · 进程   → PowerShell CIM + ConvertTo-Json（见 core/proc.py）。

另外三处必须处理、否则静默漏一半：

  · **WOW64 只影响 HKLM。** `HKCU\\...\\Run` 在**共享列表**上、**不被重定向**，
    所以只有 HKLM 的 Run/RunOnce 需要枚举 64/32 两个视图。
  · **`StartupApproved` 是「任务管理器 → 启动」那一栏开关的真实存储**
    （本后端里 macOS `print-disabled` 的对偶）：Run 项可以"存在但已禁用"，
    只有这张表能告诉你。它的值是二进制，**byte0 == 0x03 表示已禁用**；
    项不存在 = 默认启用。
  · **`Start=0/1` 是驱动不是启动项**（boot/system start）→ 从启动项列表里过滤掉。

测试接缝：`_reg()` 在非 Windows（或设了 STARTUPCTL_ROOTS）时改读夹具 JSON，
于是注册表解析逻辑能在 Linux CI 上被真正执行，而不是只在 windows runner 上跑一次。
"""
import json
import os
import re

from ..core import classify
from ..core.model import (KIND_REGISTRY_RUN, KIND_STARTUP_FOLDER, KIND_TASK_SCHEDULER,
                          KIND_WIN_SERVICE, SCOPE_SYSTEM, SCOPE_USER, StartupItem,
                          make_fingerprint)
from ..core.safety import Refused
from ..core.utils import run
from .base import Backend, iter_scan_files

# registry views
KEY_WOW64_64KEY = 0x0100
KEY_WOW64_32KEY = 0x0200

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
RUNONCE_KEY = r'Software\Microsoft\Windows\CurrentVersion\RunOnce'
RUN_KEY_32 = r'Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Run'
RUNONCE_KEY_32 = r'Software\Wow6432Node\Microsoft\Windows\CurrentVersion\RunOnce'
APPROVED_RUN = r'Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run'
APPROVED_RUN32 = r'Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32'
APPROVED_FOLDER = r'Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder'
WINLOGON_KEY = r'Software\Microsoft\Windows NT\CurrentVersion\Winlogon'
SERVICES_KEY = r'SYSTEM\CurrentControlSet\Services'


class WindowsBackend(Backend):
    platform = 'win32'
    name = 'windows'

    # ------------------------------------------------------------ 扫描
    def scan(self, ctx):
        res = self.new_result(ctx)
        self._scan_run_keys(ctx, res)
        self._scan_startup_folder(ctx, res)
        self._scan_services(ctx, res)
        self._scan_tasks(ctx, res)
        if ctx.conf.getbool('SCAN_SLOW_TASK_SCHEDULER') is False:
            pass
        return res

    # -- 注册表 Run / RunOnce --
    def _scan_run_keys(self, ctx, res):
        """HKCU 单视图 + HKLM 双视图。

        HKCU\\...\\Run 处于 WOW64 的**共享列表**上、不被重定向，所以对它枚举两个
        视图只会得到重复项；HKLM 则必须两个视图都看，否则漏掉一半持久化。
        """
        approved = self._approved_map(ctx)
        plans = [
            ('HKCU', RUN_KEY, SCOPE_USER, 'win.run.hkcu', None),
            ('HKCU', RUNONCE_KEY, SCOPE_USER, 'win.runonce.hkcu', None),
            ('HKLM', RUN_KEY, SCOPE_SYSTEM, 'win.run.hklm64', KEY_WOW64_64KEY),
            ('HKLM', RUN_KEY_32, SCOPE_SYSTEM, 'win.run.hklm32', KEY_WOW64_32KEY),
            ('HKLM', RUNONCE_KEY, SCOPE_SYSTEM, 'win.runonce.hklm64', KEY_WOW64_64KEY),
            ('HKLM', RUNONCE_KEY_32, SCOPE_SYSTEM, 'win.runonce.hklm32', KEY_WOW64_32KEY),
        ]
        for hive, key, scope, root, view in plans:
            vals, err = self._reg(hive, key, view=view)
            if err:
                continue
            if not vals:
                continue
            res.roots_scanned.append(root)
            for name, (value, vtype) in sorted(vals.items()):
                # ★ 默认值的名字是空串——极易被顺手丢掉，所以显式给它一个展示名
                disp = name if name else '(默认值)'
                anchor = '%s\\%s' % (key, name)
                prog, args = _split_command(value)
                state = approved.get(name)
                enabled, reason = _approved_state(state, is_runonce='RunOnce' in key)
                it = StartupItem(
                    platform='win32', kind=KIND_REGISTRY_RUN, scope=scope,
                    anchor=anchor, name=disp, program=prog, args=tuple(args),
                    run_at_load=True, enabled=enabled, enabled_reason=reason,
                    trigger='boot' if scope == SCOPE_SYSTEM else 'login',
                    source='%s\\%s\\%s' % (hive, key, name),
                    source_kind='registry', root=root,
                )
                it.raw = ('注册表: %s\\%s\n  名称: %s\n  类型: %s\n  数据: %s\n'
                          'StartupApproved: %s'
                          % (hive, key, disp, vtype, value,
                             '无记录（默认启用）' if state is None else repr(state)))
                it.fingerprint = make_fingerprint(prog, args, value)
                classify.classify(it, self.ctx)
                res.items.append(it)

        self._scan_winlogon(ctx, res)

    def _scan_winlogon(self, ctx, res):
        """Winlogon 的 Shell/Userinit 被改动过是**强持久化信号**。

        正常机器上它们是固定值；任何偏差都值得报出来。默认值：
          Shell    = explorer.exe
          Userinit = C:\\Windows\\system32\\userinit.exe,
        """
        vals, err = self._reg('HKLM', WINLOGON_KEY)
        if err or not vals:
            return
        defaults = {'Shell': 'explorer.exe',
                    'Userinit': r'C:\Windows\system32\userinit.exe,'}
        for k, default in defaults.items():
            if k not in vals:
                continue
            value = vals[k][0]
            if (value or '').strip().lower() == default.strip().lower():
                continue
            anchor = '%s\\%s' % (WINLOGON_KEY, k)
            it = StartupItem(
                platform='win32', kind=KIND_REGISTRY_RUN, scope=SCOPE_SYSTEM,
                anchor=anchor, name='Winlogon\\%s' % k,
                program=_split_command(value)[0], args=tuple(_split_command(value)[1]),
                enabled=True, enabled_reason='winlogon',
                trigger='login', source=r'HKLM\%s\%s' % (WINLOGON_KEY, k),
                source_kind='registry', root='win.winlogon',
            )
            it.raw = ('注册表: HKLM\\%s\n  %s = %s\n  默认值应为: %s'
                      % (WINLOGON_KEY, k, value, default))
            classify.classify(it, self.ctx)
            # 非默认值一律强制按第三方并加警告——这是持久化的经典位置
            it.origin = 'third_party'
            it.confidence = 'high'
            it.origin_evidence = 'Winlogon\\%s 非默认值（正常应为 %s）' % (k, default)
            it.mutable = True
            it.warnings = tuple(list(it.warnings) +
                                ['Winlogon 非默认值：这是恶意持久化的经典位置，请人工确认'])
            res.items.append(it)

    # -- 启动文件夹 --
    def _scan_startup_folder(self, ctx, res):
        approved = self._approved_map(ctx)
        for root_name, scope in (('win.startup.user', SCOPE_USER),
                                 ('win.startup.common', SCOPE_SYSTEM)):
            d = self.root(root_name)
            if not d or not os.path.isdir(d):
                continue
            res.roots_scanned.append(root_name)
            for path, err in iter_scan_files(d):
                if err is not None:
                    from ..core.model import scan_error
                    res.errors.append(scan_error(root_name, d, str(err)))
                    continue
                base = os.path.basename(path)
                if base.lower() in ('desktop.ini',):
                    continue
                state = approved.get(base)
                enabled, reason = _approved_state(state, is_runonce=False)
                target = ''
                if base.lower().endswith('.lnk'):
                    # ⚠️ .lnk 的目标要靠 COM IShellLink 才能可靠解析，标准库做不到。
                    #    这里只做**尽力而为**的字符串提取，并明确标注是推测。
                    target = _lnk_guess(path)
                it = StartupItem(
                    platform='win32', kind=KIND_STARTUP_FOLDER, scope=scope,
                    anchor=base, name=base, program=target, args=(),
                    enabled=enabled, enabled_reason=reason,
                    trigger='login', source=path, source_kind='dir-entry',
                    root=root_name,
                )
                it.raw = ('启动文件夹项: %s\n推测目标: %s%s'
                          % (path, target or '(未能提取)',
                             '\n（.lnk 目标为推测值，精确解析需 COM，本工具不做）'
                             if target else ''))
                classify.classify(it, self.ctx)
                res.items.append(it)

    # -- 服务 --
    def _scan_services(self, ctx, res):
        subs, err = self._reg_enum_subkeys('HKLM', SERVICES_KEY)
        if err:
            return
        res.roots_scanned.append('win.services')
        for name in subs:
            vals, verr = self._reg('HKLM', '%s\\%s' % (SERVICES_KEY, name))
            if verr or not vals:
                continue
            start = _dword(vals.get('Start'))
            stype = _dword(vals.get('Type'))
            # ★ Start=0/1 是**驱动**不是启动项；Type 里的 0x2 是文件系统驱动位
            if start in (0, 1):
                continue
            if stype is not None and (stype & 0x2):
                continue
            image = vals.get('ImagePath', ('', ''))[0] or ''
            display = vals.get('DisplayName', ('', ''))[0] or name
            enabled, reason = _service_enabled(start)
            prog, args = _split_command(image)
            anchor = name
            it = StartupItem(
                platform='win32', kind=KIND_WIN_SERVICE, scope=SCOPE_SYSTEM,
                anchor=anchor, name=display, program=prog, args=tuple(args),
                enabled=enabled, enabled_reason=reason,
                trigger='boot', source=r'HKLM\%s\%s' % (SERVICES_KEY, name),
                source_kind='registry', root='win.services',
            )
            it.raw = ('服务: %s\n  DisplayName: %s\n  Start: %s (%s)\n'
                      '  Type: %s\n  ImagePath: %s\n  ObjectName: %s'
                      % (name, display, start, reason, stype, image,
                         vals.get('ObjectName', ('', ''))[0]))
            it.fingerprint = make_fingerprint(prog, args, image)
            classify.classify(it, self.ctx)
            res.items.append(it)

    # -- 计划任务 --
    def _scan_tasks(self, ctx, res):
        d = self.root('win.tasks')
        if not d or not os.path.isdir(d):
            return
        res.roots_scanned.append('win.tasks')
        import xml.etree.ElementTree as ET
        # ⚠️ 计划任务在磁盘上是**嵌套目录树**，镜像任务路径：
        #    \Microsoft\Windows\Defrag\Defrag → System32\Tasks\Microsoft\Windows\Defrag\Defrag
        #    iter_scan_files 是非递归的，用它只能扫到根目录下那几个任务，
        #    \Microsoft\Windows\ 下面成百上千个系统任务会**全部漏掉**。
        for path, err in _walk_files(d):
            if err is not None or not os.path.isfile(path):
                continue
            try:
                with open(path, 'rb') as fh:
                    raw = fh.read()
            except OSError:
                continue
            try:
                root = ET.fromstring(raw)
            except ET.ParseError as e:
                from ..core.model import scan_error
                res.errors.append(scan_error('win.tasks', path, '任务 XML 解析失败: %s' % e))
                continue
            task_path = _task_path_from_file(d, path)
            info = _parse_task_xml(root)
            if not info['is_startup']:
                continue
            it = StartupItem(
                platform='win32', kind=KIND_TASK_SCHEDULER, scope=SCOPE_SYSTEM,
                anchor=task_path, name=task_path,
                program=info['exec'], args=tuple(info['args']),
                enabled=info['enabled'], enabled_reason='task:%s' % info['trigger'],
                trigger='boot' if info['trigger'] == 'boot' else 'login',
                source=path, source_kind='file', root='win.tasks',
            )
            it.raw = raw.decode('utf-8', 'replace')[:4000]
            it.fingerprint = make_fingerprint(info['exec'], info['args'], it.raw)
            if info['hidden']:
                it.warnings = tuple(list(it.warnings) + ['任务被标记为隐藏（Hidden）'])
            classify.classify(it, self.ctx)
            res.items.append(it)

    # ------------------------------------------------------------ 注册表访问
    def _fixture_path(self):
        """夹具模式：STARTUPCTL_ROOTS 下的 registry.json。"""
        base = os.environ.get('STARTUPCTL_ROOTS')
        if not base:
            return None
        p = os.path.join(base, 'registry.json')
        return p if os.path.isfile(p) else None

    def _fixture(self):
        p = self._fixture_path()
        if not p:
            return None
        if getattr(self, '_fixture_cache', None) is None:
            try:
                with open(p, 'r', encoding='utf-8') as fh:
                    self._fixture_cache = json.load(fh)
            except (OSError, ValueError):
                self._fixture_cache = {}
        return self._fixture_cache

    def _reg(self, hive, key, view=None):
        """读一个键的所有值。返回 (dict name→(value,type), error)。

        **在非 Windows 或夹具模式下走 JSON 夹具**——这是让注册表解析逻辑能在
        Linux CI 上被真正执行的唯一办法。别把它当"测试用的临时代码"简化掉：
        少了它，Windows 后端（三个平台里风险最高的一个）在 3 个 runner 里只有
        1 个会跑到。
        """
        fx = self._fixture()
        if fx is not None:
            full = '%s\\%s' % (hive, key)
            for cand in (full, '%s\\Wow6432Node\\%s' % (hive, key)):
                if cand in fx:
                    return dict((k, (v.get('value', ''), v.get('type', 'REG_SZ')))
                                for k, v in fx[cand].items()), None
            return {}, None

        if os.name != 'nt':
            return {}, 'not-windows'
        try:
            import winreg
        except ImportError:
            return {}, 'no-winreg'
        try:
            flags = winreg.KEY_READ | (view or KEY_WOW64_64KEY)
            k = winreg.OpenKey(getattr(winreg, 'HKEY_' + hive), key, 0, flags)
        except OSError as e:
            return {}, str(e)
        out = {}
        try:
            i = 0
            while True:
                try:
                    name, value, typ = winreg.EnumValue(k, i)
                except OSError:
                    break
                out[name] = (value, _type_name(typ))
                i += 1
        finally:
            try:
                winreg.CloseKey(k)
            except Exception:
                pass
        return out, None

    def _reg_enum_subkeys(self, hive, key):
        fx = self._fixture()
        if fx is not None:
            full = '%s\\%s\\' % (hive, key)
            subs = set()
            for k in fx:
                if k.startswith(full):
                    subs.add(k[len(full):].split('\\')[0])
            return sorted(subs), None
        if os.name != 'nt':
            return [], 'not-windows'
        try:
            import winreg
        except ImportError:
            return [], 'no-winreg'
        try:
            k = winreg.OpenKey(getattr(winreg, 'HKEY_' + hive), key, 0,
                              winreg.KEY_READ | KEY_WOW64_64KEY)
        except OSError as e:
            return [], str(e)
        subs = []
        try:
            i = 0
            while True:
                try:
                    subs.append(winreg.EnumKey(k, i))
                except OSError:
                    break
                i += 1
        finally:
            try:
                winreg.CloseKey(k)
            except Exception:
                pass
        return subs, None

    def _approved_map(self, ctx):
        """StartupApproved 表：name → byte0。

        ⚠️ byte0 的语义随版本略有差异（Win10 vs Win11）→ **按已知值尽力判定，
        其余原样呈现**，不假装理解。
        """
        out = {}
        for hive, keys in (('HKCU', (APPROVED_RUN, APPROVED_RUN32, APPROVED_FOLDER)),
                           ('HKLM', (APPROVED_RUN, APPROVED_FOLDER))):
            for key in keys:
                vals, err = self._reg(hive, key)
                if err:
                    continue
                for name, (value, _t) in (vals or {}).items():
                    b0 = _byte0(value)
                    if b0 is not None:
                        out.setdefault(name, b0)
        return out

    def _registry_write(self, hive, key_path, name, value, view=None):
        fx = self._fixture()
        if fx is not None:
            full = '%s\\%s' % (hive, key_path)
            fx.setdefault(full, {})[name] = {'value': value, 'type': 'REG_SZ'}
            p = self._fixture_path()
            if p:
                with open(p, 'w', encoding='utf-8') as fh:
                    json.dump(fx, fh, ensure_ascii=False, indent=2)
            return True
        if os.name != 'nt':
            raise Refused('当前平台不支持注册表写入')
        import winreg
        flags = winreg.KEY_SET_VALUE | (view or KEY_WOW64_64KEY)
        k = winreg.CreateKeyEx(getattr(winreg, 'HKEY_' + hive), key_path, 0, flags)
        try:
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
        finally:
            try:
                winreg.CloseKey(k)
            except Exception:
                pass
        return True

    # ------------------------------------------------------------ 关联
    def corr_table(self, ctx):
        """服务的权威 PID 表：`Win32_Service` 的 ProcessId。

        取不到就返回空，让 proc.py 退回路径匹配并**如实标注**关联方式。
        """
        cmd = ('Get-CimInstance Win32_Service | '
               'Select-Object Name,ProcessId | ConvertTo-Json -Compress')
        r = run(['powershell', '-NoProfile', '-NonInteractive', '-Command', cmd], timeout=25)
        if not r.ok:
            return {}
        try:
            data = json.loads(r.out or '[]')
        except ValueError:
            return {}
        if isinstance(data, dict):
            data = [data]
        out = {}
        for d in data:
            try:
                pid = int(d.get('ProcessId') or 0)
            except (TypeError, ValueError):
                continue
            if pid > 0:
                out[pid] = d.get('Name') or ''
        return out

    # ------------------------------------------------------------ 变更
    def _rebuild(self, item, ctx):
        """重读活源。注册表项按值名重读；文件项走基类。"""
        if item.source_kind == 'registry':
            return self._rebuild_registry(item)
        return super(WindowsBackend, self)._rebuild(item, ctx)

    def _rebuild_registry(self, item):
        src = item.source or ''
        parts = src.split('\\')
        if len(parts) < 3:
            return None
        hive, key, name = parts[0], '\\'.join(parts[1:-1]), parts[-1]
        vals, err = self._reg(hive, key)
        if err or not vals:
            return None
        if name not in vals and name != '(默认值)':
            return None
        import copy
        fresh = copy.copy(item)
        if name in vals:
            value = vals[name][0]
            prog, args = _split_command(value)
            fresh.program = prog
            fresh.args = tuple(args)
            fresh.fingerprint = make_fingerprint(prog, args, value)
        return fresh

    def plan(self, op, item, ctx):
        needs_root = item.scope == SCOPE_SYSTEM and not self.is_admin()
        tail = '（需要管理员权限）' if needs_root else ''
        if op == 'disable':
            if item.kind == KIND_WIN_SERVICE:
                return ['  · 禁用服务 %s：注册表 Start 2→4（可逆）%s' % (item.key, tail)]
            if item.kind == KIND_TASK_SCHEDULER:
                return ['  · 禁用任务 %s：schtasks /Change /DISABLE%s' % (item.key, tail)]
            if item.kind == KIND_REGISTRY_RUN:
                return ['  · 禁用 %s：值名改名为 StartupctlDisabled-%s（不删除）%s'
                        % (item.key, item.key, tail)]
            return ['  · 禁用 %s：移入同级 disabled/ 目录%s' % (item.key, tail)]
        if op == 'enable':
            return ['  · 启用 %s：还原为原先的值名 / Start / 文件位置%s' % (item.key, tail)]
        if op == 'remove':
            if item.kind == KIND_WIN_SERVICE:
                return ['  · 移除服务 %s：**默认只置 Start=4**（不删服务）；'
                        '真删需 --purge 且先导出整棵服务键%s' % (item.key, tail)]
            return ['  · 移除 %s：导出后删除注册表值 / 移入备份%s' % (item.key, tail)]
        if op == 'add':
            return ['  · 新增用户级启动项 HKCU\\...\\Run']
        return super(WindowsBackend, self).plan(op, item, ctx)

    def _require_root_for(self, item):
        """判断依据是**实际可写性**（见 base._needs_root），不只看 scope。"""
        if self._needs_root(item):
            return ('需要管理员权限：%s。请以管理员身份运行本工具'
                    % (item.source or item.anchor))
        return ''

    def _do_disable(self, item, ctx, backup=None, entry=None):
        self._guard(item, 'disable')
        why = self._require_root_for(item)
        if why:
            raise Refused(why)
        if item.kind == KIND_REGISTRY_RUN:
            return self._disable_run_value(item)
        if item.kind == KIND_WIN_SERVICE:
            return self._set_service_start(item, 4)
        if item.kind == KIND_TASK_SCHEDULER:
            r = run(['schtasks', '/Change', '/TN', item.anchor, '/DISABLE'], timeout=25)
            if not r.ok:
                raise RuntimeError('schtasks 失败: %s' % (r.err or r.out).strip())
            return '任务已禁用'
        if item.kind == KIND_STARTUP_FOLDER:
            return self._move_startup_entry(item, backup, entry, to_disabled=True)
        raise Refused('不支持禁用的类型: %s' % item.kind)

    def _do_enable(self, item, ctx, backup=None, entry=None):
        self._guard(item, 'enable')
        why = self._require_root_for(item)
        if why:
            raise Refused(why)
        if item.kind == KIND_REGISTRY_RUN:
            return self._enable_run_value(item)
        if item.kind == KIND_WIN_SERVICE:
            return self._set_service_start(item, 2)
        if item.kind == KIND_TASK_SCHEDULER:
            r = run(['schtasks', '/Change', '/TN', item.anchor, '/ENABLE'], timeout=25)
            if not r.ok:
                raise RuntimeError('schtasks 失败: %s' % (r.err or r.out).strip())
            return '任务已启用'
        if item.kind == KIND_STARTUP_FOLDER:
            return self._move_startup_entry(item, backup, entry, to_disabled=False)
        raise Refused('不支持启用的类型: %s' % item.kind)

    def _do_remove(self, item, ctx, backup=None, entry=None):
        self._guard(item, 'remove')
        why = self._require_root_for(item)
        if why:
            raise Refused(why)
        if item.kind == KIND_WIN_SERVICE:
            # ★ 默认**不**调 sc delete：Start=4 被 SCM 认作"已禁用"、反转只需一次
            #   注册表写入；sc delete 是本工具里唯一没有干净撤销手段的操作。
            if not getattr(ctx, 'purge', False):
                return (self._set_service_start(item, 4) +
                        '（未删除服务——真删需 --purge；本工具默认保留可逆性）')
            return self._set_service_start(item, 4)
        if item.kind == KIND_REGISTRY_RUN:
            return self._delete_run_value(item, backup, entry)
        if item.kind == KIND_TASK_SCHEDULER:
            r = run(['schtasks', '/Delete', '/TN', item.anchor, '/F'], timeout=25)
            if not r.ok:
                raise RuntimeError('schtasks 失败: %s' % (r.err or r.out).strip())
            return '任务已删除'
        if item.kind == KIND_STARTUP_FOLDER:
            return self._move_startup_entry(item, backup, entry, to_disabled=True)
        raise Refused('不支持移除的类型: %s' % item.kind)

    def _do_add(self, item, ctx, backup=None, entry=None):
        self._guard(item, 'add')
        if item.scope == SCOPE_SYSTEM:
            raise Refused('默认只写用户级启动项（HKCU\\...\\Run）')
        self._registry_write('HKCU', RUN_KEY, item.anchor,
                             '%s %s' % (item.program, ' '.join(item.args)).strip())
        return '已写入 HKCU\\%s\\%s' % (RUN_KEY, item.anchor)

    # -- 注册表变更原语 --
    def _disable_run_value(self, item):
        """Run 值改名而不是删除——**可逆**，且不需要备份整把键。"""
        src = item.source or ''
        parts = src.split('\\')
        if len(parts) < 3:
            raise RuntimeError('无法解析注册表来源: %s' % src)
        hive, key, name = parts[0], '\\'.join(parts[1:-1]), parts[-1]
        vals, err = self._reg(hive, key)
        if err or name not in (vals or {}):
            raise RuntimeError('注册表值不存在: %s' % src)
        value = vals[name][0]
        new_name = 'StartupctlDisabled-%s' % name
        self._registry_write(hive, key, new_name, value)
        self._delete_reg_value(hive, key, name)
        return '已改名为 %s（原值保留，可用 enable 还原）' % new_name

    def _enable_run_value(self, item):
        src = item.source or ''
        parts = src.split('\\')
        hive, key, name = parts[0], '\\'.join(parts[1:-1]), parts[-1]
        vals, err = self._reg(hive, key)
        disabled_name = 'StartupctlDisabled-%s' % name
        if err or disabled_name not in (vals or {}):
            raise RuntimeError('未找到被禁用的值 %s' % disabled_name)
        value = vals[disabled_name][0]
        self._registry_write(hive, key, name, value)
        self._delete_reg_value(hive, key, disabled_name)
        return '已还原为 %s' % name

    def _delete_run_value(self, item, backup, entry):
        src = item.source or ''
        parts = src.split('\\')
        hive, key, name = parts[0], '\\'.join(parts[1:-1]), parts[-1]
        vals, err = self._reg(hive, key)
        if err or name not in (vals or {}):
            raise RuntimeError('注册表值不存在: %s' % src)
        if backup is not None:
            from ..core import safety
            safety.backup_registry(item, backup,
                                   {name: {'value': vals[name][0], 'type': vals[name][1]}})
        self._delete_reg_value(hive, key, name)
        return '已删除注册表值（备份在 backups/ 的 registry/ 下）'

    def _delete_reg_value(self, hive, key, name):
        fx = self._fixture()
        if fx is not None:
            full = '%s\\%s' % (hive, key)
            if full in fx and name in fx[full]:
                del fx[full][name]
                p = self._fixture_path()
                if p:
                    with open(p, 'w', encoding='utf-8') as fh:
                        json.dump(fx, fh, ensure_ascii=False, indent=2)
            return True
        if os.name != 'nt':
            raise Refused('当前平台不支持注册表删除')
        import winreg
        try:
            k = winreg.OpenKey(getattr(winreg, 'HKEY_' + hive), key, 0,
                               winreg.KEY_SET_VALUE | KEY_WOW64_64KEY)
        except OSError as e:
            raise RuntimeError(str(e))
        try:
            winreg.DeleteValue(k, name)
        except OSError as e:
            raise RuntimeError('删除值失败: %s' % e)
        finally:
            try:
                winreg.CloseKey(k)
            except Exception:
                pass
        return True

    def _set_service_start(self, item, start):
        vals, err = self._reg('HKLM', item.source.split('\\', 2)[-1] if False
                              else '%s\\%s' % (SERVICES_KEY, item.anchor))
        if err:
            raise RuntimeError(err)
        if os.name != 'nt':
            raise Refused('当前平台不支持服务注册表写入')
        import winreg
        path = '%s\\%s' % (SERVICES_KEY, item.anchor)
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0,
                           winreg.KEY_SET_VALUE | KEY_WOW64_64KEY)
        try:
            winreg.SetValueEx(k, 'Start', 0, winreg.REG_DWORD, int(start))
        finally:
            try:
                winreg.CloseKey(k)
            except Exception:
                pass
        return '服务 Start 已设为 %d（2=自动 3=手动 4=禁用）' % start

    def _move_startup_entry(self, item, backup, entry, to_disabled=True):
        src = item.source or ''
        if not src or not os.path.exists(src):
            raise RuntimeError('源不存在: %s' % src)
        d = os.path.dirname(src)
        if to_disabled:
            dst_dir = os.path.join(d, 'disabled')
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, os.path.basename(src))
            if os.path.exists(dst):
                raise Refused('目标已存在，拒绝覆盖: %s' % dst)
            os.replace(src, dst)
            return '已移入 %s' % dst
        # 还原：从 disabled/ 移回
        parent = os.path.dirname(d)
        dst = os.path.join(parent, os.path.basename(src))
        if os.path.exists(dst):
            raise Refused('目标已存在，拒绝覆盖: %s' % dst)
        os.replace(src, dst)
        return '已移回 %s' % dst


# ---------------------------------------------------------------- 辅助
def _walk_files(root):
    """递归列文件（跳过隐藏项）。计划的：任务树是嵌套的，非递归会漏掉绝大多数。"""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith('.'))
        for f in sorted(filenames):
            if f.startswith('.'):
                continue
            yield os.path.join(dirpath, f), None


def _type_name(typ):
    return {1: 'REG_SZ', 2: 'REG_EXPAND_SZ', 3: 'REG_BINARY', 4: 'REG_DWORD',
            7: 'REG_MULTI_SZ'}.get(typ, 'REG_%s' % typ)


def _dword(pair):
    if not pair:
        return None
    v = pair[0]
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _byte0(value):
    """从 StartupApproved 的值里取第 1 个字节。

    三种真实形态都要认：
      · 真 Windows 上 winreg 返回 `bytes`（REG_BINARY）
      · 夹具 JSON 里是 `[3, 0, 0, …]` 这样的整数数组（同一份数据的 JSON 表示）
      · 有的系统/工具写成十六进制字符串
    """
    if isinstance(value, (bytes, bytearray)):
        return value[0] if value else None
    if isinstance(value, (list, tuple)):
        return int(value[0]) if value else None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            if s.lower().startswith('0x'):
                return int(s, 16) & 0xFF
            return int(s, 16) & 0xFF if all(c in '0123456789abcdefABCDEF' for c in s) and len(s) <= 2 \
                else int(s) & 0xFF
        except ValueError:
            return None
    if isinstance(value, int):
        return value & 0xFF
    return None


def _approved_state(byte0, is_runonce=False):
    """StartupApproved 的 byte0 → 三态 enabled。

    ⚠️ 语义随 Windows 版本略有差异 → 只认已知值，其余返回 None（不猜）。
        0x02 / 0x06 → 启用；0x03 / 0x07 → 已禁用；不存在 → 默认启用。
    """
    if byte0 is None:
        if is_runonce:
            return True, 'RunOnce（运行后会自删）'
        return True, '无 StartupApproved 记录（默认启用）'
    try:
        b = int(byte0)
    except (TypeError, ValueError):
        return None, 'StartupApproved 值无法解析（%r）' % (byte0,)
    if b in (0x02, 0x06):
        return True, 'StartupApproved:enabled'
    if b in (0x03, 0x07):
        return False, 'StartupApproved:disabled'
    return None, 'StartupApproved 未知取值 0x%02x' % b


def _service_enabled(start):
    if start == 2:
        return True, 'Start=2（自动）'
    if start == 3:
        return True, 'Start=3（手动——不随开机启动，按需拉起）'
    if start == 4:
        return False, 'Start=4（已禁用）'
    if start in (0, 1):
        return None, 'Start=%s（驱动，非启动项）' % start
    return None, 'Start=%s' % start


def _split_command(cmdline):
    """把注册表值 / ImagePath 拆成 (program, args)。

    处理三种常见形态：
      "C:\\Program Files\\x\\a.exe" -silent    引号包裹的路径
      C:\\Windows\\system32\\svchost.exe -k netsvcs
      \\??\\C:\\path\\a.exe                      内核对象路径前缀
    """
    s = (cmdline or '').strip()
    if not s:
        return '', []
    s = re.sub(r'^\\\\\?\\', '', s)          # \??\ 前缀
    if s.startswith('"'):
        end = s.find('"', 1)
        if end > 0:
            prog = s[1:end]
            rest = s[end + 1:].strip()
            return prog, _args(rest)
        return s.strip('"'), []
    # 未加引号：按 .exe 切（Windows 上可执行文件必带扩展名）
    m = re.match(r'^(.*?\.exe)\s*(.*)$', s, re.I)
    if m:
        return m.group(1), _args(m.group(2))
    parts = s.split(' ', 1)
    return parts[0], _args(parts[1] if len(parts) > 1 else '')


def _args(rest):
    if not rest:
        return []
    import shlex
    try:
        return shlex.split(rest, posix=False)
    except ValueError:
        return rest.split()


def _task_path_from_file(tasks_dir, path):
    rel = os.path.relpath(path, tasks_dir).replace('/', '\\')
    return '\\' + rel


def _parse_task_xml(root):
    """从任务 XML 里提取我们关心的东西（不依赖 schtasks、与语言无关）。"""
    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag[:root.tag.index('}') + 1]

    def find_all(tag):
        return root.iter(ns + tag)

    enabled = True
    el = root.find('.//%sEnabled' % ns)
    if el is not None and (el.text or '').strip().lower() == 'false':
        enabled = False

    hidden = False
    el = root.find('.//%sHidden' % ns)
    if el is not None and (el.text or '').strip().lower() == 'true':
        hidden = True

    trigger = ''
    for t in find_all('Triggers'):
        for child in list(t):
            tag = child.tag.replace(ns, '')
            if tag in ('LogonTrigger', 'BootTrigger', 'RegistrationTrigger'):
                trigger = {'LogonTrigger': 'login', 'BootTrigger': 'boot',
                           'RegistrationTrigger': 'register'}[tag]
                break
        if trigger:
            break

    exec_ = ''
    args = []
    for a in find_all('Exec'):
        c = a.find('%sCommand' % ns)
        if c is not None and (c.text or '').strip():
            exec_ = c.text.strip()
        ar = a.find('%sArguments' % ns)
        if ar is not None and (ar.text or '').strip():
            args = _args(ar.text.strip())
        break

    return {
        'enabled': enabled,
        'hidden': hidden,
        'trigger': trigger,
        'exec': exec_,
        'args': args,
        'is_startup': bool(trigger),
    }


def _lnk_guess(path):
    """从 .lnk 里**尽力**提取目标路径。

    ⚠️ .lnk 是真实的二进制结构（Shell Link Binary Format），完整解析需要 COM
    `IShellLink`——标准库做不到。这里只在文件里搜 UTF-16LE 的盘符前缀串，
    是**推测**而不是解析，调用方必须如实标注。
    决策上无所谓：disable/remove 对 .lnk 就是同一个文件搬移，与目标无关。
    """
    try:
        with open(path, 'rb') as fh:
            raw = fh.read()
    except OSError:
        return ''
    # UTF-16LE 里 "C:\..." → b'C\x00:\x00\\\x00'
    import re as _re
    m = _re.search(rb'([A-Za-z])\x00:\x00\\\x00((?:[\x20-\x7e]\x00){3,200})', raw)
    if not m:
        return ''
    drive = m.group(1).decode('ascii')
    tail = m.group(2).decode('utf-16-le', 'replace')
    # 去掉尾部控制字符
    tail = ''.join(ch for ch in tail if ch >= ' ' or ch == '\\')
    cand = '%s:\\%s' % (drive, tail)
    return cand.split('\x00')[0]
