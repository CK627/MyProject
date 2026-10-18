# -*- coding: utf-8 -*-
"""命令行入口与子命令分发。

**全部是子命令，不用 `--` 旗标**（与 ptool 同形）：

    startupctl list [all|system]
    startupctl mode [off|deny_all|blacklist|whitelist]
    startupctl whitelist [startup|process] [selector]
    startupctl blacklist [startup|process] [selector]
    startupctl config | version | help | update | install | uninstall

退出码：0 成功 · 1 失败 · 2 用法错 · 3 **因安全理由被拒绝**。
"""
import os
import sys

from . import help as help_mod
from .core import config as config_mod
from .core import context, enforce, output, proc as proc_mod
from .core import guard as guard_mod
from .core.model import ORIGIN_CN, KIND_CN, RefError, ensure_unique_keys
from .core.output import c, dw, render_table
from .core.safety import EXIT_FAIL, EXIT_OK, EXIT_REFUSED, EXIT_USAGE, Refused


# ---------------------------------------------------------------- 控制台编码
def _console_utf8():
    """Windows 控制台默认不是 UTF-8，直接 print 中文会 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, 'reconfigure'):
                if getattr(stream, 'isatty', lambda: False)():
                    stream.reconfigure(errors='replace')
                else:
                    stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass


def _platform_cn(p):
    return {'darwin': 'macOS', 'linux': 'Linux', 'win32': 'Windows'}.get(p, p)


# ---------------------------------------------------------------- 渲染
def _fmt_item(it, g=None):
    flags = []
    if g is not None:
        probe = {'uid': it.uid, 'anchor': it.anchor}
        if g.matches_in(guard_mod.LIST_WHITELIST, startup=probe):
            flags.append('[白]')
        if g.matches_in(guard_mod.LIST_BLACKLIST, startup=probe):
            flags.append('[黑]')
    if it.shadowed_by:
        flags.append('[被遮蔽]')
    if it.pid is not None:
        flags.append('[运行中 %d]' % it.pid)
    return [
        it.key,
        KIND_CN.get(it.kind, it.kind),
        it.enabled_text(),
        ORIGIN_CN.get(it.origin, it.origin),
        (it.program or it.source or ''),
        ' '.join(flags),
    ]


def _print_items(items, g=None):
    if not items:
        print('（没有匹配的项）')
        return
    rows = [_fmt_item(i, g) for i in items]
    fixed = dw('名称') + dw('类型') + dw('状态') + dw('来源判定') + dw('标记') + 12
    avail = max(24, output.term_width() - fixed)
    print(render_table(rows,
                       headers=['名称', '类型', '状态', '来源判定', '可执行文件/出处', '标记'],
                       max_col={4: avail}))


def _print_scan_errors(errors):
    if not errors:
        return
    need_root = [e for e in errors if e.needs_root]
    print('')
    print(c('扫描提示 %d 条%s' % (len(errors), '（含需管理员权限的根）' if need_root else ''),
            'dim'))
    for e in errors[:5]:
        print('  · %s: %s' % (e.root, e.reason))
    if len(errors) > 5:
        print('  … 另有 %d 条' % (len(errors) - 5))


def _scan_items(ctx):
    res = ctx.scan()
    items = list(res.items)
    ensure_unique_keys(items)
    return items, res


# ---------------------------------------------------------------- list
def cmd_list(ctx, args):
    scope = (args[0].lower() if args else 'third')
    if scope not in ('third', 'all', 'system'):
        sys.stderr.write('错误: list 的取值只能是 all 或 system\n')
        return EXIT_USAGE

    items, res = _scan_items(ctx)
    g = guard_mod.load()

    if scope == 'system':
        items = [i for i in items if i.origin == 'os']
    elif scope == 'third':
        items = [i for i in items if i.origin == 'third_party']
        items = [i for i in items if not i.shadowed_by]

    print(c('扫描: %s · %d 项（第三方 %d）' % (
        _platform_cn(ctx.platform), len(res.items),
        sum(1 for i in res.items if i.origin == 'third_party')), 'dim'))
    if ctx.is_fixture():
        print(c('注意: 当前处于夹具模式（STARTUPCTL_ROOTS），读的不是真机', 'yellow'))
    print('')
    _print_items(items, g)

    wl_n, bl_n = g.count()
    if wl_n or bl_n:
        print('')
        print(c('名单: 白名单 %d 条 · 黑名单 %d 条（标记列的 [白]/[黑] 是启动项维度的命中）'
                % (wl_n, bl_n), 'dim'))
    _print_scan_errors(res.errors)
    return EXIT_OK


# ---------------------------------------------------------------- 策略上下文
def _guard_ctx(ctx):
    """取策略 + 进程表 + 启动项表（已互相关联）。"""
    g = guard_mod.load()
    items, _res = _scan_items(ctx)
    procs, errs = proc_mod.enumerate_procs(ctx, ctx.backend)
    for p in procs:
        proc_mod.classify_proc(p, ctx.platform)
    procs = [p for p in procs if p.pid > 1]
    try:
        table = ctx.backend.corr_table(ctx)
    except Exception:
        table = {}
    proc_mod.correlate(items, procs, table, ctx.platform)
    return g, procs, items, errs


def _items_by_uid(items):
    return dict((i.uid, i) for i in items)


# ---------------------------------------------------------------- mode
MODE_ALIASES = {
    'off': guard_mod.MODE_OFF,
    'deny_all': guard_mod.MODE_DENY_ALL,
    'blacklist': guard_mod.MODE_BLACKLIST,
    'whitelist': guard_mod.MODE_WHITELIST,
}


def _mode_status(ctx, g, procs, items):
    deny, protect, allow = enforce.plan(procs, g, ctx.platform,
                                        items_by_uid=_items_by_uid(items))
    print('模式:     %s' % guard_mod.MODE_CN.get(g.mode, g.mode))
    act = g.active_list_name()
    print('起作用:   %s' % (guard_mod.LIST_CN.get(act, '（无——不干预）')))
    wl_n, bl_n = g.count()
    print('白名单:   %d 条（启动项 %d · 进程 %d）' % (
        wl_n, g.count_dim(guard_mod.LIST_WHITELIST, guard_mod.DIM_STARTUP),
        g.count_dim(guard_mod.LIST_WHITELIST, guard_mod.DIM_PROCESS)))
    print('黑名单:   %d 条（启动项 %d · 进程 %d）' % (
        bl_n, g.count_dim(guard_mod.LIST_BLACKLIST, guard_mod.DIM_STARTUP),
        g.count_dim(guard_mod.LIST_BLACKLIST, guard_mod.DIM_PROCESS)))
    print('策略文件: %s' % g.path)
    ready, why = g.ready_to_enforce()
    if g.mode != guard_mod.MODE_OFF and not ready:
        print('')
        print(c('还不能执行: %s' % why, 'yellow'))
    print('')
    print('进程: 总计 %d · 将结束 %d · 受保护 %d · 放行 %d'
          % (len(procs), len(deny), len(protect), len(allow)))
    if g.mode == guard_mod.MODE_OFF:
        print(c('（不干预：本工具不会结束任何进程）', 'dim'))
    return EXIT_OK


def cmd_mode(ctx, args):
    from .core import guard as guard_mod
    # 先在**不扫描**的情况下判能不能执行：名单为空时直接拒绝。
    # 扫描在 Windows 上要几秒，先扫再拒会让用户以为"没反应"（用户实测反馈）。
    if args and args[0].lower() in MODE_ALIASES and args[0].lower() != 'off':
        early = guard_mod.load()
        early.mode = MODE_ALIASES[args[0].lower()]
        ok, why = early.ready_to_enforce()
        if not ok:
            sys.stderr.write('拒绝: %s\n' % why)
            return EXIT_REFUSED
    g, procs, items, _errs = _guard_ctx(ctx)
    if not args:
        return _mode_status(ctx, g, procs, items)
    # `mode <x> confirm`：跳过确认（脚本用）。与 `uninstall confirm` 同一套写法。
    assume_yes = False
    if args and args[-1].lower() == 'confirm':
        assume_yes = True
        args = args[:-1]
    if len(args) != 1:
        sys.stderr.write('错误: mode 需要一个取值（可再加 confirm）\n')
        return EXIT_USAGE

    want = MODE_ALIASES.get(args[0].lower())
    if want is None:
        sys.stderr.write('错误: 未知模式 %s（可选: off deny_all blacklist whitelist）\n'
                         % args[0])
        return EXIT_USAGE

    if want == guard_mod.MODE_OFF:
        g.set_mode(guard_mod.MODE_OFF)
        g.save()
        print('模式已设为「不干预」：不再结束任何进程。')
        # ★ 不碰监视循环：开机自启是**独立属性**，换模式不该把它关掉。
        from .core import autostart
        if autostart.running():
            print('监视循环: 仍在运行（空转，不会动手）。要停掉请用 startupctl starting false')
        return EXIT_OK

    # 先在**旧状态**上换上新模式判断能不能执行——名单空着就不许动。
    old_mode = g.mode
    g.mode = want
    ready, why = g.ready_to_enforce()
    if not ready:
        g.mode = old_mode
        sys.stderr.write('拒绝: %s\n' % why)
        return EXIT_REFUSED

    deny, protect, allow = enforce.plan(procs, g, ctx.platform,
                                        items_by_uid=_items_by_uid(items))
    print('模式: %s' % guard_mod.MODE_CN[want])
    print('进程: 总计 %d · 将结束 %d · 受保护 %d · 放行 %d'
          % (len(procs), len(deny), len(protect), len(allow)))
    if deny:
        print('')
        print('将要结束（%d）:' % len(deny))
        for d in deny[:25]:
            print('  · %-26s pid=%-7s %s'
                  % ((d.proc.comm or '?')[:26], d.proc.pid, d.reason))
        if len(deny) > 25:
            print('  … 另有 %d 个' % (len(deny) - 25))
    if protect:
        print('')
        print('受保护、任何模式下都不会结束: %d 个（含系统基础进程与你仍能操作的 shell/终端）'
              % len(protect))

    if ctx.dry_run:
        print('')
        print(c('STARTUPCTL_DRY_RUN=1：以上为将要执行的操作，未改动任何东西', 'dim'))
        return EXIT_OK

    from .core import safety
    if not safety.confirm('按该模式结束进程', [], ctx,
                          assume_yes or ctx.assume_yes):
        print('已取消，模式未改变。')
        return EXIT_FAIL

    ok_n, fail_n, refused_n = enforce.apply_decisions(deny, g, term_first=True)
    g.set_mode(want)
    g.save()
    print('')
    print('模式已设为 %s；本次结束 %d 个进程%s。'
          % (want, ok_n,
             ('（失败 %d · 跳过 %d）' % (fail_n, refused_n))
             if (fail_n or refused_n) else ''))
    # 用户要的是「开了模式就自动盯着」——不必再记得去敲 starting true。
    _ensure_watcher()
    return EXIT_OK


# ---------------------------------------------------------------- 名单
DIM_ALIASES = {
    'startup': guard_mod.DIM_STARTUP,
    'process': guard_mod.DIM_PROCESS,
}


def _policy_entries(g, name, dim):
    """把某份名单的某个维度渲染成 (左, 右) 供管理窗口显示。"""
    out = []
    for e in g.entries_of(name, dim):
        if dim == guard_mod.DIM_STARTUP:
            out.append((e.get('label') or e.get('anchor') or e.get('uid') or '?',
                        '%s  %s  %s' % (e.get('kind', ''), e.get('anchor', ''),
                                        '已锁定' if e.get('locked') else '')))
        else:
            out.append((e.get('value') or '?',
                        '%s  %s' % (guard_mod.MATCH_CN.get(e.get('match'), ''),
                                    '已锁定' if e.get('locked') else '')))
    return out


def _print_policy(g, name):
    for dim in guard_mod.DIMS:
        rows = _policy_entries(g, name, dim)
        print('')
        print('%s · %s（%d 条）' % (guard_mod.LIST_CN[name], guard_mod.DIM_CN[dim], len(rows)))
        if not rows:
            print('  （空）')
            continue
        for i, (left, right) in enumerate(rows, 1):
            print('  %3d. %-34s %s' % (i, left, right))


def _policy_add(ctx, g, name, dim):
    """打开对应维度的选择器，把选中的条目加进名单。"""
    from .core import picker as picker_mod

    if dim == guard_mod.DIM_STARTUP:
        items, _res = _scan_items(ctx)
        # 系统项不动：它们永远受保护，加进名单只是噪声。所以选择器只列第三方。
        items = [i for i in items
                 if i.origin == 'third_party' and not i.shadowed_by]
        if not items:
            print('（本机没有第三方启动项）')
            return EXIT_OK
        existing = set(e.get('uid') for e in g.entries_of(name, dim))
        picked = picker_mod.pick_startup(
            items, preselect=existing,
            allow_gui=not ctx.conf.getbool('NO_GUI'))
    else:
        procs, _errs = proc_mod.enumerate_procs(ctx, ctx.backend)
        for p in procs:
            proc_mod.classify_proc(p, ctx.platform)
        procs = [p for p in procs if p.pid > 1]
        existing = set(e.get('value') for e in g.entries_of(name, dim))
        picked = picker_mod.pick_processes(
            procs, ctx.platform, guard_mod.own_pid_chain(),
            preselect=None,
            locked_matcher=lambda p: (p.comm or '') in existing,
            allow_gui=not ctx.conf.getbool('NO_GUI'))

    if picked is None:
        print('已取消。')
        return EXIT_OK
    before = len(g.entries_of(name, dim))
    n = 0
    for obj in picked:
        try:
            if dim == guard_mod.DIM_STARTUP:
                g.add_startup(name, obj, reason='%s selector' % name)
            else:
                # pick_processes 返回 (proc, locked) 二元组：locked 表达的是
                # "这一条在选择器里被钉住了"，要跟着一起写进条目。
                proc, locked = obj
                g.add_process(name, proc, reason='%s selector' % name,
                              locked=locked)
            n += 1
        except (ValueError, TypeError) as e:
            label = getattr(obj, 'comm', None) or (
                getattr(obj[0], 'comm', '?') if isinstance(obj, tuple) else '?')
            print(c('跳过 %s: %s' % (label, e), 'yellow'))
    total = len(g.entries_of(name, dim))
    added = total - before
    if added:
        try:
            g.save()
        except ValueError as e:
            sys.stderr.write('错误: %s\n' % e)
            return EXIT_FAIL
    note = ''
    if len(picked) != added:
        # 同名的多个进程共用一条规则（匹配方式就是进程名），必须说出来，
        # 否则用户会以为"选了 8 个只进去 4 条"是丢了。
        note = '（选中 %d 个，同名的合并为一条）' % len(picked)
    print('新增 %d 条，%s · %s 现有 %d 条%s'
          % (added, guard_mod.LIST_CN[name], guard_mod.DIM_CN[dim], total, note))
    return EXIT_OK


def _policy_manage(g, name, dims):
    """管理窗口：列出条目，删除。无 GUI 时打印清单并说明。"""
    from .core import gui as gui_mod

    if gui_mod.available():
        tabs = []
        for dim in dims:
            def _remove(i, _dim=dim):
                try:
                    e = g.remove_at(name, _dim, i)
                except IndexError:
                    return
                g.save()
                label = e.get('label') or e.get('value') or ''
                print('已删除: %s' % label)
            tabs.append({
                'name': guard_mod.DIM_CN[dim],
                'provider': (lambda _d=dim: _policy_entries(g, name, _d)),
                'on_remove': _remove,
            })
        try:
            gui_mod.manage(tabs, title='%s管理' % guard_mod.LIST_CN[name])
            return EXIT_OK
        except gui_mod.GuiUnavailable:
            pass

    _print_policy(g, name)
    print('')
    print(c('（当前环境不能弹窗，只能查看。策略文件可直接编辑: %s）' % g.path, 'dim'))
    return EXIT_OK


def cmd_policy(ctx, which, args):
    name = guard_mod.LIST_WHITELIST if which == 'whitelist' else guard_mod.LIST_BLACKLIST
    g = guard_mod.load()

    dim = None
    selector = False
    rest = list(args)
    if rest and rest[0].lower() in DIM_ALIASES:
        dim = DIM_ALIASES[rest.pop(0).lower()]
    if rest and rest[0].lower() in ('selector', 'select', 'pick'):
        selector = True
        rest.pop(0)
    if rest:
        sys.stderr.write('错误: 多余的参数 %s\n' % ' '.join(rest))
        return EXIT_USAGE

    if selector:
        if dim is None:
            sys.stderr.write('错误: selector 前面要说明是 startup 还是 process\n'
                             '      例: startupctl %s startup selector\n' % which)
            return EXIT_USAGE
        return _policy_add(ctx, g, name, dim)

    dims = [dim] if dim else list(guard_mod.DIMS)
    return _policy_manage(g, name, dims)


# ---------------------------------------------------------------- 自启 / 监视
def _ensure_watcher():
    """模式从 off 切到别的之后，若循环没在跑就在后台起一个。"""
    from .core import autostart, watch
    pid = autostart.running()
    if pid:
        print('监视循环: 已在运行（pid %d）' % pid)
        return
    _ok, msg = watch.start_detached()
    print('监视循环: %s' % msg)
    print(c('（要开机也自动运行，再执行: startupctl starting true）', 'dim'))


def cmd_starting(args):
    """startupctl starting [true|false] —— 开机自启开关。

    不带参数 = 看状态（与 mode / config 同一套习惯：**问就是显示当前状态**）。
    """
    from .core import autostart, watch
    from .core import guard as guard_mod
    from .core import config as config_mod

    if len(args) > 1:
        sys.stderr.write('错误: starting 只接受一个取值（true / false）\n')
        return EXIT_USAGE
    arg = args[0].lower() if args else None

    if arg is None:
        st = autostart.status()
        g = guard_mod.load()
        conf = config_mod.load()
        print('开机自启: %s' % ('已启用' if st['enabled'] else '未启用'))
        print('监视循环: %s' % (('运行中（pid %d）' % st['pid']) if st['pid'] else '未运行'))
        print('当前模式: %s' % guard_mod.MODE_CN.get(g.mode, g.mode))
        print('检查间隔: %d 秒' % (conf.getint('WATCH_INTERVAL') or 5))
        print('策略文件: %s' % g.path)
        print('运行日志: %s' % os.path.join(os.path.dirname(g.path), 'watch.log'))
        if g.mode == guard_mod.MODE_OFF:
            print('')
            print(c('（不干预模式下循环会空转——先 startupctl mode blacklist）', 'dim'))
        return EXIT_OK

    if arg in ('true', 'on', '1', 'yes'):
        ok, msg = autostart.install()
        print(msg)
        if not ok:
            return EXIT_FAIL
        # launchd / systemd / 计划任务都会**自己**把循环拉起来，别再另起一个
        # （否则会有两个循环同时杀进程）。
        pid = autostart.wait_running()
        print('开机自启已开启。监视循环: %s'
              % (('运行中（pid %d）' % pid) if pid else '还没起来（看 watch.log）'))
        return EXIT_OK

    if arg in ('false', 'off', '0', 'no'):
        stopped, msg = autostart.stop_running()
        print(msg)
        ok, msg2 = autostart.remove()
        print(msg2)
        print('开机自启已关闭。')
        return EXIT_OK if ok else EXIT_FAIL

    sys.stderr.write('错误: starting 只接受 true 或 false\n')
    return EXIT_USAGE


# ---------------------------------------------------------------- config
def cmd_config(ctx):
    from . import __version__
    from .core import paths
    from .core.selfmgr import self_info

    mode, root, _devtools = self_info()
    d = paths.data_root()
    mode_cn = {'installed': 'devtools 安装', 'repo': '仓库检出',
               'unknown': '未知'}.get(mode, mode)
    g = guard_mod.load()
    wl_n, bl_n = g.count()

    print('startupctl %s' % __version__)
    print('运行模式: %s' % mode_cn)
    print('安装根:   %s' % root)
    print('平台:     %s (%s)' % (_platform_cn(ctx.platform), ctx.platform))
    print('管理员:   %s' % ('是' if ctx.admin else '否'))
    print('dry-run:  %s' % ctx.dry_run)
    print('')
    print('数据目录: %s' % d)
    print('  策略:   %s（%s）' % (g.path, _size(g.path)))
    print('  名单:   白名单 %d 条 · 黑名单 %d 条' % (wl_n, bl_n))
    print('  模式:   %s' % guard_mod.MODE_CN.get(g.mode, g.mode))
    print('')
    print('配置文件: %s' % (ctx.conf.path or '(未找到，全部走内置默认值)'))
    for w in ctx.conf.warnings:
        print('  %s %s' % (c('警告:', 'yellow'), w))
    return EXIT_OK


def _size(p):
    try:
        return '%.1f KB' % (os.path.getsize(p) / 1024.0)
    except OSError:
        return '(未创建)'


# ---------------------------------------------------------------- 自管理
def _selfmgr():
    from .core import selfmgr
    return selfmgr


SUBCOMMANDS = ('list', 'mode', 'whitelist', 'blacklist', 'starting', 'watch',
               'config', 'version',
               'help', 'update', 'install', 'uninstall', 'print-install-dir')


def main(argv=None):
    _console_utf8()
    argv = list(sys.argv[1:] if argv is None else argv)

    # 本工具**只用子命令**：任何 `-` 开头的东西都是用法错，而不是被静默忽略。
    for a in argv:
        if a.startswith('-') and a != '-':
            sys.stderr.write('错误: 不支持选项 %s（本工具只用子命令，见 startupctl help）\n' % a)
            return EXIT_USAGE

    if not argv:
        print(help_mod.HELP, end='')
        return EXIT_OK

    # 「这个位置能填什么」：`startupctl <命令> ?`。
    # cmd / Windows PowerShell 5.1 都没有可用的补全，这是给它们的显式替代：
    # 打印的内容与 Tab 补全的层级完全一致。
    # `help` 作为最后一个词时同义（zsh 会把未加引号的 `?` 当通配符，用 help 更稳）。
    if argv[-1] in ('?', '？'):
        text = help_mod.hint_text(argv[:-1])
        if text is None:
            sys.stderr.write('错误: 不知道该位置有哪些取值（试试 startupctl help）\n')
            return EXIT_USAGE
        print(text, end='')
        return EXIT_OK
    if len(argv) >= 2 and argv[-1].lower() == 'help':
        text = help_mod.hint_text(argv[:-1])
        if text is not None:
            print(text, end='')
            return EXIT_OK

    sub = argv[0].lower()
    rest = argv[1:]

    if sub in ('help', 'version'):
        if sub == 'help':
            target = rest[0].lower() if rest else None
            if target:
                text = help_mod.sub_help(target)
                if text is None:
                    sys.stderr.write('错误: 没有子命令 %s 的帮助（可用: startupctl help）\n'
                                     % target)
                    return EXIT_USAGE
                print(text, end='')
                return EXIT_OK
            print(help_mod.HELP, end='')
            return EXIT_OK
        from . import __version__
        print('startupctl %s' % __version__)
        return EXIT_OK

    # 自管理子命令（不建 Ctx：update 时数据目录可能还不存在）
    # ★ 先把参数校验完再转交：原来 `rest` 里多出来的词会被**静默丢弃**
    #   （`startupctl update bad` 会当成 `update` 跑），用户敲错了也看不出来。
    _ARITY = {
        'update': ((), ('check',)),
        'uninstall': ((), ('confirm',)),
        'install': ((), ()),
    }
    if sub in _ARITY:
        plain, words = _ARITY[sub]
        if rest and not (len(rest) == 1 and rest[0].lower() in words):
            allowed = ' / '.join(list(plain) + list(words)) or '（无参数）'
            sys.stderr.write('错误: %s 不接受参数 %s\n' % (sub, ' '.join(rest)))
            sys.stderr.write('      可用: %s\n' % allowed)
            return EXIT_USAGE
        if sub == 'update':
            return _selfmgr().cmd_update(['--check'] if rest else [])
        if sub == 'install':
            return _selfmgr().cmd_install([])
        if sub == 'uninstall':
            return _selfmgr().cmd_uninstall(['-y'] if rest else [])
    if sub == 'print-install-dir':
        return _selfmgr().cmd_print_install_dir([])
    if sub == 'starting':
        return cmd_starting(rest)
    if sub == 'watch':
        from .core import watch
        return watch.run()

    if sub not in SUBCOMMANDS:
        sys.stderr.write('错误: 未知子命令 %s（可用: startupctl help）\n' % sub)
        return EXIT_USAGE

    conf = config_mod.load()
    ctx = context.Ctx(conf=conf)

    try:
        if sub == 'list':
            return cmd_list(ctx, rest)
        if sub == 'mode':
            return cmd_mode(ctx, rest)
        if sub in ('whitelist', 'blacklist'):
            return cmd_policy(ctx, sub, rest)
        if sub == 'config':
            return cmd_config(ctx)
    except Refused as e:
        ctx.fail(str(e))
        if getattr(e, 'hint', ''):
            print('  %s' % e.hint)
        return EXIT_REFUSED
    except RefError as e:
        ctx.fail(str(e))
        return EXIT_USAGE
    except KeyboardInterrupt:
        print('')
        return EXIT_FAIL
    except Exception as e:                     # 兜底：不把 traceback 甩给用户
        if os.environ.get('STARTUPCTL_DEBUG'):
            raise
        sys.stderr.write('内部错误: %s: %s\n' % (type(e).__name__, e))
        sys.stderr.write('  （设 STARTUPCTL_DEBUG=1 可看完整堆栈）\n')
        return EXIT_FAIL

    return EXIT_USAGE
