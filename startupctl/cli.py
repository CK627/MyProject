# -*- coding: utf-8 -*-
"""命令行入口与子命令分发。

分工：`cli` 只负责解析参数、组装 `Ctx`、渲染输出。**一切破坏性判断都在
`core/manage.py`**，一切平台差异都在 `backends/`。本文件里没有一处
`if platform == ...`，也没有一处直接改系统状态。

退出码：0 成功 · 1 失败 · 2 用法错 · 3 **因安全理由被拒绝**（见 core/safety.py）。
"""
import json
import os
import sys

from . import help as help_mod
from .core import config as config_mod
from .core import context, manage, output, proc as proc_mod, safety, whitelist as wl_mod
from .core import classify
from .core.model import (ORIGIN_CN, KIND_CN, RefError, resolve, ensure_unique_keys)
from .core.output import c, dw, pad, render_table
from .core.safety import EXIT_FAIL, EXIT_OK, EXIT_REFUSED, EXIT_USAGE, Refused

EXIT_MISSING_PKG = 4


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


# ---------------------------------------------------------------- 参数解析
BOOL_FLAGS = {
    '--all', '--system', '--third-party', '--running', '--long', '--json',
    '--errors', '--raw', '--resolve', '--save', '--diff', '--force', '--purge',
    '--strict', '--include-unknown', '--i-know', '--remove', '--pin',
    '--orphans', '--run-at-load', '--check', '--deep', '--no-color',
    '--all-unmatched', '--version', '--help',
    '--dry-run', '--sudo', '--yes',
    '--watch', '--plain', '--arm', '--lock', '--tui', '--gui',
    '--whitelist', '--blacklist',
}
VALUE_FLAGS = {
    '--config', '--vendor', '--kind', '--scope', '--confidence', '--name',
    '--reason', '--glob', '--exec-prefix', '--color', '--limit',
    '--match', '--value', '--interval', '--rounds',
}
SHORT = {'-y': '--yes', '-h': '--help', '-n': '--dry-run'}


def _parse(argv):
    """极简参数解析：返回 (positional, opts)。不用 argparse 是为了控制帮助文案。"""
    pos, opts = [], {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in SHORT:
            a = SHORT[a]
        if a == '--':
            pos.extend(argv[i + 1:])
            break
        if a.startswith('--') and '=' in a:
            k, _, v = a.partition('=')
            opts[k] = v
        elif a in BOOL_FLAGS:
            opts[a] = True
        elif a in VALUE_FLAGS:
            if i + 1 >= len(argv):
                raise ValueError('%s 需要一个值' % a)
            opts[a] = argv[i + 1]
            i += 1
        elif a.startswith('-') and a != '-':
            raise ValueError('未知选项: %s' % a)
        else:
            pos.append(a)
        i += 1
    return pos, opts


def _want_help(opts, sub):
    if opts.get('--help'):
        text = help_mod.sub_help(sub)
        print(text if text else help_mod.HELP, end='')
        return True
    return False


# ---------------------------------------------------------------- 渲染
def _fmt_item(it, long=False):
    flags = []
    if it.whitelisted:
        flags.append('[白]')
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


def _print_items(items, long=False, show_origin=True, errors=None, total=None):
    if not items:
        print('（没有匹配的项）')
    else:
        rows = [_fmt_item(i) for i in items]
        # 最后一列（可执行文件/出处）吃掉剩余宽度：命令行可以很长，不截断就会
        # 把整张表撑到几百列，前面的列全被挤出屏幕。
        fixed = dw('名称') + dw('类型') + dw('状态') + dw('来源判定') + dw('标记') + 12
        avail = max(24, output.term_width() - fixed)
        print(render_table(rows,
                           headers=['名称', '类型', '状态', '来源判定', '可执行文件/出处', '标记'],
                           max_col={4: avail}))
    if long:
        print('')
        for it in items:
            if it.origin_evidence:
                print('  %s → %s' % (c(it.key, 'bold'), it.origin_evidence))
            for w in it.warnings:
                print('  %s %s' % (c('警告:', 'yellow'), w))


def _print_scan_errors(errors, expand=False, total=None):
    if not errors:
        return
    need_root = [e for e in errors if e.needs_root]
    print('')
    print(c('扫描提示 %d 条%s' % (len(errors), '（含需管理员权限的根）' if need_root else ''),
            'dim'))
    if expand:
        for e in errors:
            tag = '需root' if e.needs_root else '信息'
            print('  [%s] %s: %s' % (tag, e.root, e.reason))
            if e.detail:
                print('        %s' % e.detail)
    else:
        for e in errors[:5]:
            print('  · %s: %s' % (e.root, e.reason))
        if len(errors) > 5:
            print('  … 另有 %d 条（--errors 展开）' % (len(errors) - 5))


def _load_and_filter(ctx, opts):
    """扫描 + 应用筛选 + 打白名单标记。返回 (items, res)。"""
    res = ctx.scan()
    items = list(res.items)
    ctx.wl().apply(items)
    ensure_unique_keys(items)

    if opts.get('--running'):
        items = [i for i in items if i.pid is not None]
    if opts.get('--vendor'):
        v = opts['--vendor']
        items = [i for i in items if (i.vendor or '').startswith(v)]
    if opts.get('--kind'):
        items = [i for i in items if i.kind == opts['--kind']]
    if opts.get('--scope'):
        items = [i for i in items if i.scope == opts['--scope']]

    show_system = opts.get('--all') or opts.get('--system') or ctx.conf.getbool('SHOW_SYSTEM')
    if opts.get('--third-party'):
        show_system = False
    if opts.get('--system'):
        items = [i for i in items if i.origin == 'os']
    elif not show_system:
        items = [i for i in items if i.origin == 'third_party']
    # 被遮蔽的默认不列（--all 时列出，并带 [被遮蔽] 标记）
    if not opts.get('--all'):
        items = [i for i in items if not i.shadowed_by]
    return items, res


# ---------------------------------------------------------------- 子命令
def cmd_list(ctx, opts):
    items, res = _load_and_filter(ctx, opts)
    if opts.get('--json'):
        print(json.dumps([i.to_dict() for i in items], ensure_ascii=False, indent=2))
        return EXIT_OK

    print(c('扫描: %s · %d 项（第三方 %d）' % (
        _platform_cn(ctx.platform), len(res.items),
        sum(1 for i in res.items if i.origin == 'third_party')), 'dim'))
    if ctx.is_fixture():
        print(c('注意: 当前处于夹具模式（STARTUPCTL_ROOTS），读的不是真机', 'yellow'))
    print('')

    _print_items(items, long=bool(opts.get('--long')))

    wl_n = sum(1 for i in items if i.whitelisted)
    if wl_n:
        print('')
        print(c('（其中白名单 %d 项——白名单只让 clean 少动它们，不隐藏）' % wl_n, 'dim'))
    if ctx.conf.getbool('SHOW_WHITELISTED') is False:
        print(c('提示: SHOW_WHITELISTED=false 时白名单项仍会列出（这是刻意的）', 'dim'))
    _print_scan_errors(res.errors, expand=bool(opts.get('--errors')))
    return EXIT_OK


def _platform_cn(p):
    return {'darwin': 'macOS', 'linux': 'Linux', 'win32': 'Windows'}.get(p, p)


# ---------------------------------------------------------------- 进程守护
def _guard_ctx(ctx):
    """取 guard 策略 + 当前进程表（已分类）。"""
    from .core import guard as guard_mod, proc as proc_mod
    g = guard_mod.load()
    procs, errs = proc_mod.enumerate_procs(ctx, ctx.backend)
    for p in procs:
        proc_mod.classify_proc(p, ctx.platform)
    # 去掉 pid<=1，它们在任何模式里都是受保护的，列出来只是噪声
    procs = [p for p in procs if p.pid > 1]
    return g, procs, errs


def cmd_guard(ctx, opts, pos):
    """进程守护。**模式与选择是分开的两件事**：

        guard mode <m>     选策略模式（不管清单内容）
        guard choose       打开选择器，往**当前模式对应的那份清单**里填
        guard list         分别看两份清单
    """
    from .core import enforce, guard as guard_mod, picker
    action = pos[0] if pos else 'status'
    rest = pos[1:]

    def _want_list():
        """这次操作针对哪份清单：--whitelist/--blacklist 显式指定，否则取当前模式的。"""
        if opts.get('--whitelist'):
            return guard_mod.LIST_WHITELIST
        if opts.get('--blacklist'):
            return guard_mod.LIST_BLACKLIST
        return g.active_list_name() or guard_mod.LIST_WHITELIST

    if action == 'status':
        g, procs, errs = _guard_ctx(ctx)
        deny, protect, allow = enforce.plan(procs, g, ctx.platform)
        wl_n, bl_n = g.count()
        print('守护模式:   %s' % guard_mod.MODE_CN.get(g.mode, g.mode))
        print('起作用的是: %s' % (guard_mod.LIST_CN.get(g.active_list_name(), '（无——off 模式）')))
        print('白名单:     %d 条' % wl_n)
        print('黑名单:     %d 条' % bl_n)
        print('策略文件:   %s' % g.path)
        ready, why = g.ready_to_enforce()
        if not ready and g.mode != guard_mod.MODE_OFF:
            print('')
            print(c('还不能执行: %s' % why, 'yellow'))
        print('')
        locked_n = len(g.locked_entries())
        print('当前进程: 总计 %d · 将结束 %d · 受保护 %d · 放行 %d'
              % (len(procs), len(deny), len(protect), len(allow)))
        if locked_n:
            print('          其中受保护包含你锁定的 %d 条条目' % locked_n)
        if g.mode == guard_mod.MODE_OFF:
            print('')
            print('（「不干预」模式：本工具不会结束任何进程）')
            print('  切换: startupctl guard mode whitelist | blacklist | deny_all')
        if opts.get('--json'):
            print(json.dumps({
                'mode': g.mode, 'active': g.active_list_name(),
                'whitelist': g.whitelist, 'blacklist': g.blacklist,
                'ready': ready, 'ready_reason': why,
                'counts': {'total': len(procs), 'deny': len(deny),
                           'protected': len(protect), 'allow': len(allow)},
            }, ensure_ascii=False, indent=2))
        return EXIT_OK

    if action == 'mode':
        g, procs, _e = _guard_ctx(ctx)
        if not rest:
            print('当前模式: %s' % guard_mod.MODE_CN.get(g.mode, g.mode))
            print('')
            # 按**显示宽度**对齐（CJK 计 2 列）——用 %-34s 是按字符数补空格，
            # 中文描述会长短不齐，"（用黑名单）"那一列歪掉。
            mw = max(dw(m) for m in guard_mod.MODES)
            cw = max(dw(guard_mod.MODE_CN[m]) for m in guard_mod.MODES)
            for m in guard_mod.MODES:
                mark = '→' if m == g.mode else ' '
                uses = {'off': '（不用任何清单）', 'deny_all': '（用白名单作豁免）',
                        'blacklist': '（用黑名单）', 'whitelist': '（用白名单）'}.get(m, '')
                print('  %s %s  %s  %s'
                      % (mark, pad(m, mw), pad(guard_mod.MODE_CN[m], cw), uses))
            print('')
            print('模式只决定"用哪份清单"，不改动清单内容——两份清单互相独立，')
            print('所以切模式不会把你之前挑的东西变成另一套语义。')
            print('选完模式后用 guard choose 往对应清单里挑进程。')
            return EXIT_OK
        want = rest[0]
        try:
            from .core import guard as _gm
            if want == 'choose':                    # 便捷写法: guard mode choose
                return _do_choose(ctx, opts, _gm)
            g.set_mode(want)
        except ValueError as e:
            ctx.fail(str(e))
            return EXIT_USAGE
        ok_saved, back = _save_and_verify(g, ctx, '模式')
        if not ok_saved:
            return EXIT_FAIL
        print('模式已设为: %s' % guard_mod.MODE_CN.get(g.mode, g.mode))
        n = g.active_list_name()
        wl_n, bl_n = g.count()
        print('  现在起作用的是: %s（当前 %d 条）'
              % (guard_mod.LIST_CN.get(n, '（无）'), len(g.entries_of(n)) if n else 0))
        print('  两份清单都原样保留: 白名单 %d 条 · 黑名单 %d 条' % (wl_n, bl_n))
        ready, why = g.ready_to_enforce()
        if not ready and g.mode != guard_mod.MODE_OFF:
            print('')
            print(c('还不能执行: %s' % why, 'yellow'))
        else:
            print('  下一步: startupctl guard check / guard arm')
        return EXIT_OK

    if action in ('choose', 'pick'):
        # --- 选择：唯一会启动图形窗口的入口 ---
        return _do_choose(ctx, opts, guard_mod, legacy_no_gui=(action == 'pick'))

    if action == 'list':
        g, procs, _e = _guard_ctx(ctx)
        wl_n, bl_n = g.count()
        if not wl_n and not bl_n:
            print('两份清单都是空的。')
            print('  挑进程: startupctl guard choose   （图形窗口；系统进程不可选）')
            print('  按名字: startupctl guard add <名称|pid>')
            return EXIT_OK
        act = g.active_list_name()
        for name, entries in g.lists():
            mark = '← 当前模式在用' if name == act else ''
            print('%s（%d 条）%s' % (guard_mod.LIST_CN[name], len(entries), mark))
            if entries:
                _print_guard_entries(entries)
            else:
                print('  （空）')
            print('')
        print('两份清单互相独立；锁定条目在任何模式下都不结束。')
        return EXIT_OK

    if action == 'add':
        g, procs, _e = _guard_ctx(ctx)
        ref = rest[0] if rest else None
        explicit = opts.get('--value')
        if not ref and not explicit:
            ctx.fail('用法: startupctl guard add <名称|pid> [--value V] '
                     '[--whitelist|--blacklist] [--lock]')
            return EXIT_USAGE
        target = _find_proc(procs, ref) if ref else None
        if target is None and not explicit:
            ctx.fail('没有找到匹配「%s」的进程（用 guard choose 或 proc 看有哪些）；'
                     '想给还没跑起来的东西预先立规矩，用 --value 显式指定' % ref)
            return EXIT_USAGE
        if target is None:
            target = _synthetic_proc(explicit)
        if guard_mod.is_protected(target, ctx.platform, guard_mod.own_pid_chain())[0]:
            ctx.fail('拒绝加入: %s 是系统基础进程，任何模式下都不会被结束'
                     % (target.comm or target.pid))
            return EXIT_REFUSED
        match = opts.get('--match') or guard_mod.M_PROC_NAME
        lname = _want_list()
        try:
            e = g.add(target, name=lname, match=match, value=explicit,
                      reason=opts.get('--reason', ''), locked=bool(opts.get('--lock')))
        except ValueError as ex:
            ctx.fail(str(ex))
            return EXIT_USAGE
        ok_saved, back = _save_and_verify(g, ctx, '%s清单' % guard_mod.LIST_CN[lname])
        if not ok_saved:
            return EXIT_FAIL
        print('已加入%s: %s = %s%s'
              % (guard_mod.LIST_CN[lname], e['match'], e['value'],
                 '（已锁定）' if e.get('locked') else ''))
        print('  当前模式 %s；%s现有 %d 条'
              % (guard_mod.MODE_CN.get(g.mode, g.mode), guard_mod.LIST_CN[lname],
                 len(g.entries_of(lname))))
        if target.pid is None:
            print('  注意: 该进程当前没有在跑，这条规则会在它出现时生效。')
        ready, why = g.ready_to_enforce()
        if not ready and g.mode != guard_mod.MODE_OFF:
            print('  %s' % c('还不能执行: %s' % why, 'yellow'))
        return EXIT_OK

    if action in ('lock', 'unlock'):
        g, _p, _e = _guard_ctx(ctx)
        if not rest:
            ctx.fail('用法: startupctl guard %s <值>（guard list 看有哪些）' % action)
            return EXIT_USAGE
        want = (action == 'lock')
        n = g.set_locked(rest[0], want)
        if n == 0:
            ctx.fail('两份清单里都没有值为「%s」的条目' % rest[0])
            return EXIT_USAGE
        ok_saved, back = _save_and_verify(g, ctx)
        if not ok_saved:
            return EXIT_FAIL
        print('已%s %d 条: %s' % ('锁定' if want else '解锁', n, rest[0]))
        if want:
            print('  锁定后它**在任何模式下都不会被结束**，且在选择器里选不动。')
            print('  要改回来: startupctl guard unlock %s' % rest[0])
        return EXIT_OK

    if action in ('remove', 'del'):
        g, _p, _e = _guard_ctx(ctx)
        if opts.get('--all'):
            lname = _want_list()
            plan = ['  · 清空%s（%d 条），其它不动'
                    % (guard_mod.LIST_CN[lname], len(g.entries_of(lname)))]
            if not safety.confirm('清空%s' % guard_mod.LIST_CN[lname], plan, ctx,
                                  opts.get('--yes')):
                return EXIT_OK if ctx.dry_run else EXIT_FAIL
            if ctx.dry_run:
                return EXIT_OK
            n = g.clear(lname)
            ok_saved, _b = _save_and_verify(g, ctx)
            if not ok_saved:
                return EXIT_FAIL
            print('已清空%s（%d 条）' % (guard_mod.LIST_CN[lname], n))
            return EXIT_OK
        if not rest:
            ctx.fail('用法: startupctl guard remove <值> [--all]')
            return EXIT_USAGE
        n = g.remove_value(rest[0])
        if n == 0:
            ctx.fail('两份清单里都没有值为「%s」的条目（guard list 看有哪些）' % rest[0])
            return EXIT_USAGE
        ok_saved, _b = _save_and_verify(g, ctx)
        if not ok_saved:
            return EXIT_FAIL
        print('已移除 %d 条' % n)
        return EXIT_OK

    if action == 'check':
        g, procs, _e = _guard_ctx(ctx)
        deny, protect, allow = enforce.plan(procs, g, ctx.platform)
        for line in enforce.format_plan(deny, protect, allow, g, ctx.platform):
            print(line)
        if opts.get('--json'):
            print('')
            print(json.dumps({'mode': g.mode, 'active': g.active_list_name(),
                              'deny': [{'pid': d.proc.pid, 'comm': d.proc.comm,
                                        'reason': d.reason} for d in deny]},
                             ensure_ascii=False, indent=2))
        return 0 if not deny else 1

    if action == 'arm':
        g, procs, _e = _guard_ctx(ctx)
        # ★「只有选择的时候才生效」——清单是空的就不许执行
        ready, why = g.ready_to_enforce()
        if not ready:
            ctx.fail('拒绝执行：%s' % why)
            if g.mode == guard_mod.MODE_WHITELIST:
                print('  白名单模式下空清单等于"除系统外全杀"，所以这里先拦住你。')
                print('  选好要放行的进程: startupctl guard choose')
            return EXIT_REFUSED
        deny, protect, allow = enforce.plan(procs, g, ctx.platform)
        watch_mode = bool(opts.get('--watch'))
        plan_lines = enforce.format_plan(deny, protect, allow, g, ctx.platform)
        plan_lines.append('')
        if watch_mode:
            plan_lines.append('  · **持续监视**：每 %.1fs 扫一次，'
                              '按策略结束新起来的进程（Ctrl-C 停止）'
                              % float(opts.get('--interval') or 2.0))
            plan_lines.append('  · 注意：它也会拒绝**你自己刚敲的命令**'
                              '（全部拒绝模式下尤甚）')
        else:
            plan_lines.append('  · 执行一轮：结束上面列出的进程')
        plan_lines.append('  · 系统基础进程、shell/终端、锁定条目在任何模式下都不结束')
        plan_lines.append('  · 绝不使用 sudo；root/他人的进程会被跳过并提示')

        if not safety.confirm('启用进程守护（%s）' % guard_mod.MODE_CN.get(g.mode, g.mode),
                              plan_lines, ctx, opts.get('--yes')):
            return EXIT_OK if ctx.dry_run else EXIT_FAIL

        term_first = bool(ctx.conf.get('TERM_FIRST', True))
        if watch_mode:
            try:
                interval = float(opts.get('--interval') or 2.0)
            except ValueError:
                interval = 2.0
            rounds = None
            if opts.get('--rounds'):
                try:
                    rounds = int(opts['--rounds'])
                except ValueError:
                    rounds = None
            ok, fail = enforce.watch(ctx, g, interval=interval, max_rounds=rounds,
                                     term_first=term_first)
            return EXIT_FAIL if fail else EXIT_OK
        ok, fail, refused, n = enforce.enforce_once(ctx, g, term_first=term_first)
        print('')
        print('结束 %d 个 · 失败 %d · 因保护跳过 %d' % (ok, fail, refused))
        return EXIT_FAIL if fail else EXIT_OK

    ctx.fail('用法: startupctl guard '
             '<status|mode|choose|list|add|remove|lock|unlock|check|arm>')
    return EXIT_USAGE


def _do_choose(ctx, opts, guard_mod, legacy_no_gui=False):
    """`guard choose`：**唯一会启动图形窗口的入口**。

    模式与选择分开：本命令只往"当前模式对应的那份清单"里填，不动模式、
    也不动另一份清单。
    """
    from .core import picker
    g, procs, _e = _guard_ctx(ctx)
    lname = g.active_list_name()
    if not lname:
        ctx.fail('当前模式是「不干预」，没有对应的清单可选。先选模式:')
        print('  startupctl guard mode whitelist    # 选要放行的')
        print('  startupctl guard mode blacklist    # 选要结束的')
        print('  startupctl guard mode deny_all     # 全拒绝（白名单作豁免）')
        return EXIT_USAGE

    preselect = set()
    for e in g.entries_of(lname):
        for p in procs:
            if g._entry_matches(e, p):
                preselect.add(p.pid)

    print('正在为「%s」选择进程（模式: %s）'
          % (guard_mod.LIST_CN[lname], guard_mod.MODE_CN.get(g.mode, g.mode)))
    print('（系统基础进程与已锁定条目都选不动——它们在任何模式下都不会被结束）')
    print('')

    use_gui = (not legacy_no_gui) and not opts.get('--tui') and not opts.get('--plain')

    def _note(msg):
        print(c(msg, 'yellow'))

    picked = picker.pick(procs, ctx.platform, guard_mod.own_pid_chain(),
                         preselect=preselect, locked_matcher=g.matches_locked,
                         allow_gui=use_gui,
                         force_plain=bool(opts.get('--plain')),
                         force_tui=bool(opts.get('--tui')), note=_note)
    if picked is None:
        print('已取消，未做任何改动（%s保持原样）。' % guard_mod.LIST_CN[lname])
        return EXIT_OK
    if not picked:
        print('没有选中任何进程。')
        print('  要清空请明确执行: startupctl guard remove --all -y')
        print('  %s保持原样。' % guard_mod.LIST_CN[lname])
        return EXIT_OK

    n = g.replace_list(lname, picked)
    ok_saved, back = _save_and_verify(g, ctx, guard_mod.LIST_CN[lname])
    if not ok_saved:
        return EXIT_FAIL
    print('')
    print('现在生效的%s（共 %d 条）:' % (guard_mod.LIST_CN[lname], n))
    _print_guard_entries(back.entries_of(lname))
    print('')
    print('  模式未变: %s；另一份清单未动（白名单 %d · 黑名单 %d）'
          % (guard_mod.MODE_CN.get(back.mode, back.mode), back.count()[0], back.count()[1]))
    ready, why = back.ready_to_enforce()
    if not ready:
        print('  %s' % c('还不能执行: %s' % why, 'yellow'))
    else:
        print('  下一步: startupctl guard check    看会结束哪些')
        print('          startupctl guard arm      真的执行一轮')
    return EXIT_OK


def _print_guard_entries(entries):
    """打印**一份**清单（两份清单各自调一次，所以接收的是 entries 而不是 Guard）。"""
    from .core import guard as guard_mod
    rows = []
    for i, e in enumerate(entries):
        rows.append([str(i), guard_mod.MATCH_CN.get(e.get('match'), e.get('match', '')),
                     e.get('value', ''), '锁定' if e.get('locked') else '',
                     (e.get('reason') or '')[:22],
                     (e.get('seen_program') or '')[:30]])
    print(render_table(rows, headers=['#', '匹配方式', '值', '状态', '备注', '添加时的路径']))


def _save_and_verify(g, ctx, what='策略清单'):
    """写盘后**重新读回来核对**，并如实报告。

    为什么非要多这一步：这份东西的失败形态是"看起来成了、其实没生效"——
    用户选了半天，命令打出「已更新」，可下次 `check` 还是老样子。这种静默失败
    比报错难查得多（本项目就出过一次：选择器返回了错的对象类型，于是写进去 0 条，
    而提示照样说「已更新」）。

    所以：保存 → 从磁盘重新加载 → 逐条比对 value/match/locked → 不一致就**大声报错**
    并返回非零。宁可现在报错，也不要让用户带着"我明明选过了"的错觉离开。
    """
    from .core import guard as guard_mod
    try:
        path = g.save()
    except OSError as e:
        ctx.fail('写入失败: %s（%s）' % (e, g.path))
        return False, None

    try:
        back = guard_mod.Guard(path=g.path).load()
    except Exception as e:                                      # noqa: BLE001
        ctx.fail('写回核对失败：读不回 %s（%s: %s）' % (g.path, type(e).__name__, e))
        return False, None

    def _sig(entries):
        return sorted((e.get('match'), e.get('value'), bool(e.get('locked')))
                      for e in entries)

    # ★ **两份清单都要核对**。只核一份的话，一次误改另一份的 bug 会静默通过——
    #   而"另一份被悄悄改了"恰恰是最难发现的（你正在看的是当前那份）。
    for name in (guard_mod.LIST_WHITELIST, guard_mod.LIST_BLACKLIST):
        mine, theirs = g.entries_of(name), back.entries_of(name)
        if len(mine) != len(theirs):
            ctx.fail('写回核对不一致：%s 内存里 %d 条、磁盘上 %d 条 —— 改动**没有生效**'
                     % (guard_mod.LIST_CN[name], len(mine), len(theirs)))
            print('  文件: %s' % g.path)
            print('  请检查磁盘权限与剩余空间后重试。')
            return False, back
        if _sig(mine) != _sig(theirs):
            ctx.fail('写回核对不一致：%s 磁盘上的条目与预期不符 —— 改动**没有生效**'
                     % guard_mod.LIST_CN[name])
            for a, b in zip(_sig(mine), _sig(theirs)):
                if a != b:
                    print('  预期 %s，磁盘 %s' % (a, b))
            return False, back

    if back.mode != g.mode:
        ctx.fail('写回核对不一致：模式期望 %s、磁盘上是 %s'
                 % (g.mode, back.mode))
        return False, back

    wl_n, bl_n = back.count()
    locked_n = len(back.locked_entries())
    print('%s已写入并核对无误（白名单 %d 条 · 黑名单 %d 条%s）'
          % (what, wl_n, bl_n,
             ' · 锁定 %d' % locked_n if locked_n else ''))
    print('  文件: %s' % path)
    return True, back


def _synthetic_proc(value):
    """为一个当前没在跑的进程造一条占位记录（供预先下规则用）。

    pid 留空是关键：`is_protected` 与 `add` 都不依赖 pid，而调用方据此知道
    "这不是从进程表里捞出来的"，于是能给出"该规则会在它出现时生效"的提示。
    """
    from .core.proc import ProcRecord
    return ProcRecord(pid=None, ppid=None, comm=value, program='', args_str='')


def _find_proc(procs, ref):
    """按 pid 或名字/路径片段找进程；多个命中返回第一个并提示。"""
    if ref.isdigit():
        for p in procs:
            if p.pid == int(ref):
                return p
        return None
    low = ref.lower()
    exact = [p for p in procs if (p.comm or '').lower() == low]
    if exact:
        return exact[0]
    part = [p for p in procs if low in (p.comm or '').lower()
            or low in (p.program or '').lower()]
    if not part:
        return None
    if len(part) > 1:
        print(c('提示: 「%s」匹配到 %d 个进程，取第一个 (%s pid=%s)'
                % (ref, len(part), part[0].comm, part[0].pid), 'yellow'))
    return part[0]


def cmd_show(ctx, opts, pos):
    items, res = _load_and_filter(ctx, dict(opts, **{'--all': True}))
    ctx.wl().apply(items)
    if not pos:
        ctx.fail('用法: startupctl show <项>')
        return EXIT_USAGE
    items = [i for i in items if not i.shadowed_by]
    try:
        it = resolve(items, pos[0])
    except RefError as e:
        ctx.fail(str(e))
        return EXIT_USAGE

    if opts.get('--json'):
        print(json.dumps(it.to_dict(), ensure_ascii=False, indent=2))
        return EXIT_OK

    rows = [
        ('名称', it.key), ('稳定 id', it.uid), ('平台身份', it.anchor),
        ('类型', '%s (%s)' % (KIND_CN.get(it.kind, it.kind), it.kind)),
        ('作用域', it.scope), ('状态', it.enabled_text()),
        ('状态依据', it.enabled_reason or '(无)'),
        ('触发时机', it.trigger), ('可执行文件', it.program or '(无)'),
        ('参数', ' '.join(it.args) or '(无)'),
        ('出处', it.source),
        ('来源判定', '%s / %s' % (ORIGIN_CN.get(it.origin, it.origin), it.confidence)),
        ('判定依据', it.origin_evidence or '(无)'),
        ('厂商', '%s %s' % (it.vendor or '', it.vendor_name or '')),
        ('管理工具', it.managing_tool or '(无)'),
        ('可被本工具改动', '是' if it.mutable else '否'),
        ('白名单', '是' if it.whitelisted else '否'),
        ('载荷指纹', it.fingerprint),
        ('运行状态', it.proc_state + (' pid=%s' % it.pid if it.pid else '')),
    ]
    if it.shadowed_by:
        rows.append(('被遮蔽于', it.shadowed_by))
    width = max(dw(k) for k, _ in rows)
    for k, v in rows:
        print('%s  %s' % (c(pad(k, width), 'bold'), v))
    if it.warnings:
        print('')
        for w in it.warnings:
            print('%s %s' % (c('警告:', 'yellow'), w))

    if opts.get('--resolve') and it.program:
        print('')
        print(c('解析可执行文件:', 'bold'))
        print('  realpath: %s' % os.path.realpath(it.program))
        if ctx.platform == 'darwin':
            from .core.utils import run
            r = run(['/usr/bin/codesign', '-dv', '--verbose=2', it.program], timeout=15)
            for line in (r.err or r.out or '').splitlines()[:6]:
                print('  %s' % line.strip())

    if opts.get('--raw'):
        print('')
        print(c('原始内容:', 'bold'))
        raw = ctx.backend.raw_payload(it, ctx)
        for line in (raw or '').splitlines()[:60]:
            print('  %s' % line)
    return EXIT_OK


def cmd_check(ctx, opts):
    items, res = _load_and_filter(ctx, {'--all': False})
    cands = manage.clean_candidates(res, ctx, confidence=('high',))
    wl_n = sum(1 for i in res.items if i.whitelisted)
    if opts.get('--json'):
        print(json.dumps({
            'complete': res.complete,
            'third_party': sum(1 for i in res.items if i.origin == 'third_party'),
            'cleanable': len(cands),
            'whitelisted': wl_n,
            'errors': [e.to_dict() for e in res.errors],
        }, ensure_ascii=False, indent=2))
        return EXIT_OK if not cands else 1

    print('启动项: %d 项（第三方 %d，其中白名单 %d）' % (
        len(res.items), sum(1 for i in res.items if i.origin == 'third_party'), wl_n))
    if not res.complete:
        print(c('⚠️ 扫描不完整——clean 会拒绝运行，请按提示用 --sudo 重扫', 'yellow'))
        for e in res.errors:
            if e.needs_root:
                print('   %s: %s' % (e.root, e.reason))
    if cands:
        print('')
        print('有 %d 项第三方启动项可清理（clean 默认只禁用，不删除）:' % len(cands))
        for i in cands[:15]:
            print('  · %-40s %s' % (i.key, (i.program or i.source or '')[:50]))
        if len(cands) > 15:
            print('  … 另有 %d 项（startupctl list 查看）' % (len(cands) - 15))
        print('')
        print('先看计划: startupctl clean --dry-run')
        return 1
    print('干净：没有可清理的第三方启动项。')
    return EXIT_OK


def cmd_scan(ctx, opts):
    from .core import paths
    res = ctx.scan()
    if opts.get('--save'):
        d = paths.ensure_dir(paths.scans_root())
        import datetime
        ts = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
        p = os.path.join(d, '%s.json' % ts)
        data = {'ts': ts, 'platform': ctx.platform,
                'items': [i.to_dict() for i in res.items]}
        with open(p, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print('已存快照: %s（%d 项）' % (p, len(res.items)))
        return EXIT_OK
    if opts.get('--diff'):
        return _scan_diff(ctx, res)
    print('扫描完成: %d 项（第三方 %d）' % (
        len(res.items), sum(1 for i in res.items if i.origin == 'third_party')))
    print('用 --save 存快照、--diff 比对上次快照')
    return EXIT_OK


def _scan_diff(ctx, res):
    from .core import paths
    d = paths.scans_root()
    files = sorted([f for f in os.listdir(d) if f.endswith('.json')]) if os.path.isdir(d) else []
    if not files:
        print('还没有快照。先跑一次: startupctl scan --save')
        return EXIT_FAIL
    with open(os.path.join(d, files[-1]), 'r', encoding='utf-8') as fh:
        old = json.load(fh)
    old_by_uid = {i['uid']: i for i in old.get('items', [])}
    new_by_uid = {i.uid: i for i in res.items}

    added = [u for u in new_by_uid if u not in old_by_uid]
    removed = [u for u in old_by_uid if u not in new_by_uid]
    changed = []
    for u, n in new_by_uid.items():
        o = old_by_uid.get(u)
        if o and o.get('fingerprint') != n.fingerprint:
            changed.append((n, o))

    print('对比快照: %s' % files[-1])
    print('新增 %d · 消失 %d · 载荷变化 %d' % (len(added), len(removed), len(changed)))
    if changed:
        print('')
        print(c('载荷漂移（身份没变，但「要执行什么」变了）:', 'yellow'))
        for n, o in changed:
            print('  · %-36s' % n.key)
            print('      旧: %s' % (o.get('program') or '')[:70])
            print('      新: %s' % (n.program or '')[:70])
        print('')
        print('这正是持久化植入的典型形态，建议逐条核对: startupctl show <项> --raw')
    for u in added[:10]:
        print('  + %s' % new_by_uid[u].key)
    for u in removed[:10]:
        print('  - %s' % (old_by_uid[u].get('key') or u))
    return EXIT_OK


def _resolve_items(ctx, pos, all_items=True):
    """把命令行引用解析成 item 列表（先扫描）。"""
    res = ctx.scan()
    items = list(res.items)
    ctx.wl().apply(items)
    ensure_unique_keys(items)
    out, errs = [], []
    for ref in pos:
        try:
            out.append(resolve(items, ref))
        except RefError as e:
            errs.append(str(e))
    return out, errs


def cmd_mutate(ctx, opts, pos, op):
    if not pos:
        ctx.fail('用法: startupctl %s <项>...' % op)
        return EXIT_USAGE
    items, errs = _resolve_items(ctx, pos)
    for e in errs:
        ctx.fail(e)
    if errs:
        return EXIT_USAGE
    if not items:
        return EXIT_USAGE

    ctx.purge = bool(opts.get('--purge'))
    conf = (opts.get('--confidence'),) if opts.get('--confidence') else ('high',)
    _, rc = manage.run_batch(op, items, ctx, '%s %d 项' % (op, len(items)),
                             allow_confidence=conf)
    return rc


def cmd_add(ctx, opts, pos):
    if len(pos) < 2:
        ctx.fail('用法: startupctl add <名称> <命令> [--args ...]')
        return EXIT_USAGE
    name, command = pos[0], pos[1]
    extra = pos[2:]
    label = opts.get('--name') or name
    from .core.model import KIND_LAUNCHD_AGENT, SCOPE_USER, StartupItem
    kind = {'darwin': KIND_LAUNCHD_AGENT, 'linux': 'systemd-user',
            'win32': 'registry-run'}.get(ctx.platform, KIND_LAUNCHD_AGENT)
    it = StartupItem(
        platform=ctx.platform, kind=kind, scope=SCOPE_USER,
        anchor=label, name=label, program=command, args=tuple(extra),
        run_at_load=True, enabled=True, enabled_reason='new',
        trigger='login', source='(新建)', source_kind='db', root='new',
    )
    # 新建项由我们自己的参数决定，直接放行（但仍走同一套闸门与预览）
    it.origin = 'third_party'
    it.confidence = 'high'
    it.origin_evidence = '用户显式新建的自启项'
    it.mutable = True
    ctx.scanned_uids.add(it.uid)

    plan = ctx.backend.plan('add', it, ctx)
    if not safety.confirm('新增自启项 %s' % label, plan, ctx, opts.get('--yes')):
        return EXIT_OK if ctx.dry_run else EXIT_FAIL
    bk = safety.make_manifest('add', ctx)
    ctx._current_backup = bk
    try:
        if ctx.dry_run:
            print('--dry-run：未写入任何文件')
            return EXIT_OK
        detail = ctx.backend._do_add(it, ctx, backup=bk, entry=None)
        print('已新增: %s' % detail)
        print('  %s' % (' '.join([it.program] + list(it.args))))
        return EXIT_OK
    except Refused as e:
        ctx.fail(str(e))
        if getattr(e, 'hint', ''):
            print('  %s' % e.hint)
        return EXIT_REFUSED
    except Exception as e:                                   # noqa: BLE001
        ctx.fail('%s: %s' % (type(e).__name__, e))
        return EXIT_FAIL
    finally:
        ctx._current_backup = None
        safety.save_manifest(bk)


def cmd_restore(ctx, opts, pos):
    bs = safety.list_backups()
    if not bs:
        print('没有可还原的备份。')
        return EXIT_OK
    want = pos[0] if pos and (pos[0] == 'last' or not pos[0].startswith('-')) else 'last'
    targets = pos[1:] if pos and pos[0] == want else pos
    bk = None
    if want == 'last':
        bk = bs[0]
    else:
        for b in bs:
            if want in b['name']:
                bk = b
                break
    if bk is None:
        ctx.fail('找不到备份: %s' % want)
        return EXIT_USAGE

    mf = os.path.join(bk['dir'], 'manifest.json')
    if not os.path.isfile(mf):
        ctx.fail('该备份没有 manifest，无法还原（只有 prune/authorize 记录）: %s' % bk['name'])
        return EXIT_FAIL
    with open(mf, 'r', encoding='utf-8') as fh:
        manifest = json.load(fh)

    entries = []
    for e in manifest.get('items', []):
        if e.get('status') not in ('done', 'backed_up'):
            continue
        if targets and not any(t in (e.get('anchor') or '') or t in (e.get('uid') or '')
                               for t in targets):
            continue
        if e.get('backup_path'):
            entries.append(e)

    if not entries:
        print('该备份里没有可还原的项。')
        return EXIT_OK

    plan = ['  · 还原 %s → %s' % (e.get('anchor') or e['uid'], e.get('source'))
            for e in entries]
    plan.append('  · 还原后**重新启用**（否则是"半还原"）')
    if not safety.confirm('还原 %d 项' % len(entries), plan, ctx, opts.get('--yes')):
        return EXIT_OK if ctx.dry_run else EXIT_FAIL
    if ctx.dry_run:
        return EXIT_OK

    ok, fail = 0, 0
    for e in entries:
        src, dst = e['backup_path'], e.get('source')
        try:
            if not os.path.exists(src):
                raise RuntimeError('备份文件不存在: %s' % src)
            if os.path.exists(dst) and not opts.get('--force'):
                # 默认**拒绝覆盖**：用户可能后来自己重写过那个文件
                print('  跳过 %s：目标已存在且未加 --force（%s）' % (e.get('anchor'), dst))
                fail += 1
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            import shutil
            shutil.copy2(src, dst)
            ok += 1
            print('  已还原: %s' % dst)
        except Exception as ex:                              # noqa: BLE001
            print('  失败 %s: %s' % (e.get('anchor'), ex))
            fail += 1
    print('')
    print('还原完成: 成功 %d · 失败/跳过 %d' % (ok, fail))
    print('提示: 文件已放回，但**启用态**需按平台重新拉起'
          '（macOS: launchctl bootstrap / Linux: systemctl enable / Windows: 还原值名）')
    return EXIT_FAIL if fail else EXIT_OK


def cmd_backup(ctx, opts, pos):
    action = pos[0] if pos else 'list'
    if action == 'list':
        bs = safety.list_backups()
        if not bs:
            print('没有备份。')
            return EXIT_OK
        rows = [[b['name'], b['op'], str(b['count']),
                 '有' if b['has_manifest'] else '无(仅授权记录)']
                for b in bs]
        print(render_table(rows, headers=['备份', '操作', '项数', '可还原']))
        print('')
        print('数据目录: %s' % safety.paths.backups_root())
        return EXIT_OK
    if action == 'prune':
        keep = ctx.conf.getint('BACKUP_KEEP')
        days = ctx.conf.getint('BACKUP_MIN_DAYS')
        bs = safety.list_backups()
        plan = ['  · 保留最近 %d 份，且不足 %d 天的一律不删' % (keep, days),
                '  · 当前共 %d 份备份' % len(bs)]
        if not safety.confirm('清理备份', plan, ctx, opts.get('--yes')):
            return EXIT_OK if ctx.dry_run else EXIT_FAIL
        removed, kept = safety.prune_backups(keep, days, dry_run=ctx.dry_run)
        if ctx.dry_run:
            print('--dry-run：将删除 %d 份，保留 %d 份' % (len(removed), len(kept)))
            return EXIT_OK
        print('已删除 %d 份，保留 %d 份' % (len(removed), len(kept)))
        for r in removed:
            print('  - %s' % r['name'])
        return EXIT_OK
    ctx.fail('用法: startupctl backup list | backup prune')
    return EXIT_USAGE


def cmd_clean(ctx, opts):
    res = ctx.scan()
    ctx.wl().apply(res.items)
    ensure_unique_keys(res.items)

    if not res.complete:
        ctx.fail('扫描不完整，拒绝在残缺视图上做安全决定')
        for e in res.errors:
            if e.needs_root:
                print('  未能读取: %s（%s）' % (e.path or e.root, e.reason))
        print('  请先用管理员权限重扫: sudo startupctl clean')
        return EXIT_REFUSED

    include_unknown = bool(opts.get('--include-unknown'))
    if include_unknown and not ctx.trust_unknown:
        print(c('⚠️ --include-unknown：将把"判不出来"的项也纳入处理范围。', 'yellow'))
        print('   这些项无法确定是系统还是第三方，误判可能影响系统功能。')
        print('   本模式下**只允许禁用、不允许移除**，且需要你逐条确认。')
        if not opts.get('--i-know'):
            if not sys.stdin.isatty():
                ctx.fail('非交互环境下使用 --include-unknown 还必须加 --i-know')
                return EXIT_REFUSED
            ans = input('   确认继续？(yes/no): ').strip().lower()
            if ans != 'yes':
                print('已取消。')
                return EXIT_OK

    conf = (opts.get('--confidence'),) if opts.get('--confidence') else ('high',)
    cands = manage.clean_candidates(res, ctx, confidence=conf,
                                    include_unknown=include_unknown)
    high, other = manage.partition_by_confidence(cands)

    wl_skipped = [i for i in res.items
                  if i.whitelisted and i.origin == 'third_party' and not i.shadowed_by]
    if wl_skipped:
        print('跳过 %d 项（白名单）:' % len(wl_skipped))
        for i in wl_skipped:
            print('  · %s' % i.key)

    if not cands:
        print('没有需要清理的项。')
        return EXIT_OK

    # 中置信度那批要单独确认（--confidence medium 时才出现）
    if other:
        print('')
        print(c('以下 %d 项分类置信度为 medium，需要你逐条确认：' % len(other), 'yellow'))
        for i in other:
            print('  · %-38s %s' % (i.key, i.origin_evidence[:60]))
        if not opts.get('--confidence'):
            print('  默认不处理它们。确认无疑请加 --confidence medium 重跑。')
            other = []

    op = 'remove' if opts.get('--remove') else 'disable'
    if include_unknown:
        op = 'disable'                     # ★ unknown 只允许禁用，绝不允许移除
    ctx.purge = False
    _, rc = manage.run_batch(op, high + other, ctx,
                             'clean（%s %d 项）' % ('移除' if op == 'remove' else '禁用',
                                                   len(high + other)),
                             allow_confidence=conf)
    return rc


def cmd_proc(ctx, opts):
    res = ctx.scan()
    ctx.wl().apply(res.items)
    ensure_unique_keys(res.items)
    procs, errs = proc_mod.enumerate_procs(ctx, ctx.backend)
    table = {}
    try:
        table = ctx.backend.corr_table(ctx)
    except Exception:
        table = {}
    stats = proc_mod.correlate(res.items, procs, table, ctx.platform)

    if opts.get('--orphans'):
        procs = proc_mod.orphans(procs)
    elif opts.get('--system'):
        procs = [p for p in procs if p.origin == 'os']
    elif opts.get('--third-party') or not opts.get('--all'):
        procs = [p for p in procs if p.origin == 'third_party']

    procs = [p for p in procs if p.pid > 1]

    if opts.get('--json'):
        print(json.dumps([p.to_dict() for p in procs], ensure_ascii=False, indent=2))
        return EXIT_OK

    rows = []
    for p in sorted(procs, key=lambda x: x.pid):
        rows.append([str(p.pid), (p.program or p.comm or '')[:52],
                     p.item_key or c('(无对应启动项)', 'dim'),
                     p.corr_method or '-'])
    print(render_table(rows, headers=['PID', '可执行文件', '关联启动项', '关联方式']))
    print('')
    print('关联方式说明: launchctl=平台权威表 · cgroup=Linux cgroup · parent=父进程链 · '
          'path=路径匹配 · "-"=未关联上（**不是**"没有启动项"，只是没能确定）')
    if stats:
        print('本次关联统计: %s' % ', '.join('%s=%d' % kv for kv in sorted(stats.items())))
    if errs:
        print('')
        _print_scan_errors(errs, expand=True)
    return EXIT_OK


def cmd_kill(ctx, opts, pos):
    if not pos:
        ctx.fail('用法: startupctl kill <pid|项>')
        return EXIT_USAGE
    res = ctx.scan()
    ctx.wl().apply(res.items)
    ensure_unique_keys(res.items)
    procs, _ = proc_mod.enumerate_procs(ctx, ctx.backend)
    table = {}
    try:
        table = ctx.backend.corr_table(ctx)
    except Exception:
        pass
    proc_mod.correlate(res.items, procs, table, ctx.platform)
    by_pid = {p.pid: p for p in procs}

    targets, errs = [], []
    for ref in pos:
        if ref.isdigit():
            p = by_pid.get(int(ref))
            if p is None:
                errs.append('没有 pid %s 的进程' % ref)
            else:
                targets.append(p)
        else:
            try:
                it = resolve(res.items, ref)
            except RefError as e:
                errs.append(str(e))
                continue
            if it.pid is None:
                errs.append('%s 没有正在运行的进程（关联是尽力而为，可能没配上）' % it.key)
                continue
            p = by_pid.get(it.pid)
            if p is None:
                errs.append('%s 关联到 pid %s，但该进程已不存在' % (it.key, it.pid))
                continue
            targets.append(p)
    for e in errs:
        ctx.fail(e)
    if not targets:
        return EXIT_USAGE

    # 白名单里的进程拒绝结束
    wl = ctx.wl()
    targets = [p for p in targets if not wl.matches_proc(p)] or targets
    blocked = [p for p in targets if wl.matches_proc(p)]
    targets = [p for p in targets if p not in blocked]
    for p in blocked:
        print('已跳过（白名单）: %s (pid %s)' % (p.comm, p.pid))
    if not targets:
        return EXIT_OK

    force = bool(opts.get('--force'))
    plan = ['  · %s pid %s %s' % ('KILL' if force else 'TERM', p.pid, p.comm)
            for p in targets]
    plan.append('  · 不会使用 sudo；root 进程会被拒绝')
    if not safety.confirm('结束 %d 个进程' % len(targets), plan, ctx, opts.get('--yes')):
        return EXIT_OK if ctx.dry_run else EXIT_FAIL
    if ctx.dry_run:
        return EXIT_OK

    import signal
    rc = EXIT_OK
    for p in targets:
        try:
            if os.geteuid() == 0 or _same_user(p):
                os.kill(p.pid, signal.SIGKILL if force else signal.SIGTERM)
                print('已发送 %s → pid %s (%s)' % ('KILL' if force else 'TERM', p.pid, p.comm))
            else:
                print('已跳过 pid %s（属于其他用户；本工具不会为此提权）' % p.pid)
                rc = EXIT_FAIL
        except OSError as e:
            print('失败 pid %s: %s' % (p.pid, e))
            rc = EXIT_FAIL
    return rc


def _same_user(p):
    try:
        return p.uid is None or p.uid == os.getuid()
    except AttributeError:
        return True


def cmd_whitelist(ctx, opts, pos):
    action = pos[0] if pos else 'list'
    wl = ctx.wl()
    rest = pos[1:]

    if action == 'list':
        if opts.get('--json'):
            print(json.dumps({'entries': wl.entries}, ensure_ascii=False, indent=2))
            return EXIT_OK
        if wl.is_empty():
            print('白名单为空。')
            print('  加一条: startupctl whitelist add <项> --reason "为什么留着"')
            return EXIT_OK
        rows = []
        for idx, e in enumerate(wl.entries):
            rows.append([str(idx), e.get('match', ''), e.get('value', ''),
                         (e.get('reason') or '')[:30], (e.get('anchor') or '')[:34]])
        print(render_table(rows, headers=['#', '匹配方式', '值', '备注', '锚点(回退用)']))
        print('')
        print('文件: %s' % wl.path)
        print('匹配方式: %s' % wl_mod.MATCH_CN.get(wl.entries[0].get('match'), ''))
        return EXIT_OK

    if action == 'doctor':
        res = ctx.scan()
        bad = wl.unmatched(res.items)
        if not bad:
            print('白名单 %d 条全部命中。' % len(wl.entries))
            return EXIT_OK
        print('%d 条白名单本次扫描未命中:' % len(bad))
        for e in bad:
            print('  · %s = %s（原路径 %s）' % (e.get('match'), e.get('value'),
                                              e.get('source_at_add') or '?'))
        print('')
        print('**不会自动清理**——静默删掉允许清单条目是安全惊吓。')
        print('确认无用再执行: startupctl whitelist prune')
        return EXIT_OK

    if action == 'prune':
        res = ctx.scan()
        bad = wl.unmatched(res.items)
        if not bad:
            print('没有未命中的条目。')
            return EXIT_OK
        plan = ['  · 移除 %d 条未命中的白名单条目:' % len(bad)]
        plan += ['    - %s = %s' % (e.get('match'), e.get('value')) for e in bad]
        if not safety.confirm('清理白名单', plan, ctx, opts.get('--yes')):
            return EXIT_OK if ctx.dry_run else EXIT_FAIL
        if ctx.dry_run:
            return EXIT_OK
        n = wl.prune_unmatched(res.items)
        wl.save()
        print('已移除 %d 条' % n)
        return EXIT_OK

    if action in ('add', 'remove'):
        if not rest:
            ctx.fail('用法: startupctl whitelist %s <项>' % action)
            return EXIT_USAGE
        res = ctx.scan()
        items = list(res.items)
        ensure_unique_keys(items)
        try:
            it = resolve(items, rest[0])
        except RefError as e:
            ctx.fail(str(e))
            return EXIT_USAGE
        if action == 'add':
            match = wl_mod.MATCH_ID
            value = None
            if opts.get('--glob'):
                match, value = wl_mod.MATCH_ANCHOR_GLOB, opts['--glob']
            elif opts.get('--vendor'):
                match, value = wl_mod.MATCH_VENDOR, opts['--vendor']
            elif opts.get('--exec-prefix'):
                match, value = wl_mod.MATCH_EXEC_PREFIX, opts['--exec-prefix']
            e = wl.add(it, match=match, value=value,
                       reason=opts.get('--reason', ''), pin=bool(opts.get('--pin')))
            wl.save()
            print('已加入白名单: %s = %s' % (e['match'], e['value']))
            print('  影响范围: %s' % it.key)
            if e.get('pinned_fingerprint'):
                print('  已钉住载荷指纹（命令被换掉时豁免失效）')
            print('  白名单只让 clean 少动它，**不会**让它变成"可改"')
            return EXIT_OK
        n = 1 if (rest or opts.get('--all-unmatched')) else 0
        if opts.get('--all-unmatched'):
            res2 = ctx.scan()
            bad = wl.unmatched(res2.items)
            ids = set(id(e) for e in bad)
            wl.entries = [e for e in wl.entries if id(e) not in ids]
            wl.save()
            print('已移除 %d 条未命中条目' % len(bad))
            return EXIT_OK
        n = wl.remove_matching(it)
        wl.save()
        print('已从白名单移除 %d 条（匹配 %s）' % (n, it.key))
        return EXIT_OK

    ctx.fail('用法: startupctl whitelist <add|remove|list|doctor|prune>')
    return EXIT_USAGE


def cmd_config(ctx, opts):
    from . import __version__
    from .core import paths
    from .core.selfmgr import self_info

    mode, root, devtools = self_info()
    d = paths.data_root()
    mode_cn = {'installed': 'devtools 安装', 'repo': '仓库检出', 'unknown': '未知'}.get(mode, mode)
    wl = ctx.wl()
    bs = safety.list_backups()

    def _size(p):
        if not os.path.isdir(p):
            return '(未创建)'
        total = 0
        for dirpath, _dirs, files in os.walk(p):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except OSError:
                    pass
        return '%.1f KB' % (total / 1024.0)

    print('startupctl %s' % __version__)
    print('运行模式: %s' % mode_cn)
    print('安装根:   %s' % root)
    print('平台:     %s (%s)' % (_platform_cn(ctx.platform), ctx.platform))
    print('管理员:   %s' % ('是' if ctx.admin else '否'))
    print('dry-run:  %s%s' % (ctx.dry_run, '（由 STARTUPCTL_DRY_RUN 强制）'
                              if getattr(ctx, 'dry_run_from_env', False) else ''))
    print('')
    print('数据目录: %s' % d)
    print('  白名单: %s（%d 条，%s）' % (paths.WHITELIST_NAME, len(wl.entries), _size(d)))
    print('  备份:   %d 份（%s）' % (len(bs), _size(paths.backups_root())))
    print('  快照:   %d 个（%s）' % (
        len(os.listdir(paths.scans_root())) if os.path.isdir(paths.scans_root()) else 0,
        _size(paths.scans_root())))
    print('')
    print('配置文件: %s' % (ctx.conf.path or '(未找到，全部走内置默认值)'))
    for w in ctx.conf.warnings:
        print('  %s %s' % (c('警告:', 'yellow'), w))
    print('')
    print('分类分布: %s' % ', '.join(
        '%s=%d' % (ORIGIN_CN.get(o, o), sum(1 for i in ctx.scan().items if i.origin == o))
        for o in ('os', 'third_party', 'unknown')))
    return EXIT_OK


# ---------------------------------------------------------------- 自管理
def _selfmgr():
    from .core import selfmgr
    return selfmgr


def cmd_sudo_reexec(ctx, opts):
    """--sudo：把整条命令交给 sudo **跑一次**，而不是在循环中途反复弹密码。

    在 clean 循环里逐项弹密码，正是训练用户条件反射输密码的模式。所以这里：
    先打印完整命令、要一次确认、然后整条重跑。dry-run 时**绝不提权**。
    """
    if ctx.dry_run:
        ctx.fail('--dry-run 与 --sudo 互斥（绝不为预览提权）')
        return EXIT_USAGE
    if ctx.admin:
        return None
    from .core.utils import run, which
    if not which('sudo'):
        ctx.fail('找不到 sudo；请以管理员身份运行本工具')
        return EXIT_FAIL
    argv = ['sudo', 'startupctl'] + [a for a in sys.argv[1:] if a != '--sudo']
    print('需要管理员权限，将执行:')
    print('  %s' % ' '.join(argv))
    print('（整条命令只提权一次，不会在循环中途反复要密码）')
    if not safety.confirm('提权执行', [], ctx, True):
        return EXIT_FAIL
    r = run(argv, timeout=600)
    sys.stdout.write(r.out)
    sys.stderr.write(r.err)
    return r.rc


# ---------------------------------------------------------------- 主入口
SUBCOMMANDS = ('list', 'show', 'check', 'scan', 'disable', 'enable', 'remove',
               'add', 'restore', 'backup', 'clean', 'proc', 'kill', 'whitelist',
               'guard', 'update', 'install', 'uninstall', 'config', 'help',
               'print-install-dir')


def main(argv=None):
    _console_utf8()
    argv = list(sys.argv[1:] if argv is None else argv)

    try:
        pos, opts = _parse(argv)
    except ValueError as e:
        sys.stderr.write('错误: %s\n' % e)
        return EXIT_USAGE

    # --version / --help 是**旗标**，会落进 opts 而不是 pos，所以必须先于「无位置参数」
    # 的早返回检查——否则 `startupctl --version` 会打印整屏帮助并以用法错退出。
    if opts.get('--version'):
        from . import __version__
        print('startupctl %s' % __version__)
        return EXIT_OK
    if not pos:
        if opts.get('--help'):
            print(help_mod.HELP, end='')
            return EXIT_OK
        print(help_mod.HELP, end='')
        return EXIT_OK if not argv else EXIT_USAGE

    sub = pos[0]
    rest = pos[1:]

    if sub in ('help', 'version', '--version', '--help'):
        print(help_mod.HELP if sub in ('help', '--help') else '', end='')
        if sub in ('version', '--version'):
            from . import __version__
            print('startupctl %s' % __version__)
        return EXIT_OK
    if sub not in SUBCOMMANDS:
        sys.stderr.write('错误: 未知子命令 %s（可用: startupctl help）\n' % sub)
        return EXIT_USAGE

    # 自管理子命令（不建 Ctx：update 时数据目录可能还不存在）
    if sub == 'update':
        return _selfmgr().cmd_update(argv[1:])
    if sub == 'install':
        return _selfmgr().cmd_install(argv[1:])
    if sub == 'uninstall':
        return _selfmgr().cmd_uninstall(argv[1:])
    if sub == 'print-install-dir':
        return _selfmgr().cmd_print_install_dir(argv[1:])

    if _want_help(opts, sub):
        return EXIT_OK

    conf = config_mod.load(opts.get('--config'))
    if opts.get('--color'):
        output.set_color_mode(opts['--color'])
    ctx = context.Ctx(conf=conf, dry_run=bool(opts.get('--dry-run')),
                      assume_yes=bool(opts.get('--yes')))

    if opts.get('--sudo') and sub in ('disable', 'enable', 'remove', 'clean', 'add'):
        rc = cmd_sudo_reexec(ctx, opts)
        if rc is not None:
            return rc

    try:
        if sub == 'list':
            return cmd_list(ctx, opts)
        if sub == 'show':
            return cmd_show(ctx, opts, rest)
        if sub == 'check':
            return cmd_check(ctx, opts)
        if sub == 'scan':
            return cmd_scan(ctx, opts)
        if sub == 'clean':
            return cmd_clean(ctx, opts)
        if sub == 'proc':
            return cmd_proc(ctx, opts)
        if sub == 'kill':
            return cmd_kill(ctx, opts, rest)
        if sub == 'whitelist':
            return cmd_whitelist(ctx, opts, rest)
        if sub == 'guard':
            return cmd_guard(ctx, opts, rest)
        if sub == 'backup':
            return cmd_backup(ctx, opts, rest)
        if sub == 'restore':
            return cmd_restore(ctx, opts, rest)
        if sub == 'add':
            return cmd_add(ctx, opts, rest)
        if sub == 'config':
            return cmd_config(ctx, opts)
        if sub in ('disable', 'enable', 'remove'):
            return cmd_mutate(ctx, opts, rest, sub)
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

    return EXIT_USAGE
