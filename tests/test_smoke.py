# -*- coding: utf-8 -*-
"""单元冒烟：域契约 + **安全不变量**。

纯标准库，不用 pytest（与 jtool / ptool / CtfSweep 同规），线性脚本、失败聚合。

**贯穿全篇的一条纪律：绝不碰真机。** 每个用例都设 `STARTUPCTL_ROOTS` 指向夹具树，
需要真跑的少数用例操作的是夹具树的**临时副本**。安全不变量第 12 条专门断言
"夹具模式生效、输出里没有夹具之外的路径"——它是前 11 条可信的前提：少了它，
一个"因为静默扫了 ~/Library 而不是夹具"而通过的套件，看起来一模一样。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, 'tests', 'fixtures', 'roots')

FAILS = []
PASSES = [0]


def check(cond, msg):
    if cond:
        PASSES[0] += 1
        print('[ok  ] %s' % msg)
    else:
        FAILS.append(msg)
        print('[FAIL] %s' % msg)


def check_eq(got, want, msg):
    check(got == want, '%s（得到 %r，期望 %r）' % (msg, got, want))


def section(title):
    print('')
    print('--- %s ---' % title)


def run_cli(args, env_extra=None, stdin_null=True):
    """在子进程里跑 CLI。环境完全隔离，且默认夹具模式。"""
    env = dict(os.environ)
    # ⚠️ 先清掉**继承来的**值，再设我们自己的。
    #    check_domain / scan_with 会在本进程里改 os.environ 来切平台，而 dict(os.environ)
    #    会把它带进子进程——于是 `disable com.docker.vmnetd` 会跑在 Windows 后端上、
    #    找不到该项、退 2，看起来像"解析失败"，实际是环境串味。这类 bug 极难从输出看出来。
    for k in ('STARTUPCTL_DRY_RUN', 'STARTUPCTL_PLATFORM', 'STARTUPCTL_ROOTS',
              'STARTUPCTL_DATA_DIR', 'STARTUPCTL_NO_GUI'):
        env.pop(k, None)

    # 每个用例一个全新的数据目录与夹具树源——用例之间不共享任何状态
    env['STARTUPCTL_ROOTS'] = FIXTURES
    env['STARTUPCTL_DATA_DIR'] = tempfile.mkdtemp(prefix='startupctl-data-')
    env['PYTHONPATH'] = ROOT
    # ★ **把平台钉死成 darwin**。做变更的夹具测试针对的是
    #   darwin_user_agents/com.apple.useragent.plist 这类条目；若不钉平台，
    #   在 Linux/Windows 上跑时后端会去扫 linux/win 根，那些 anchor 根本不存在，
    #   resolve 失败 → 退出 2，用例看到的是"解析失败"而不是它要验的东西。
    #   本机是 macOS，所以这个坑只在别的平台上暴露——正是 CI 矩阵存在的意义。
    env['STARTUPCTL_PLATFORM'] = 'darwin'
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, '-B', '-c',
                        'import sys; from startupctl.cli import main; sys.exit(main())'] + args,
                       cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       stdin=subprocess.DEVNULL if stdin_null else None)
    return p.returncode, p.stdout.decode('utf-8', 'replace')


def dir_hash(path):
    """目录内容指纹（相对路径 + 大小 + 内容）。用来断言"一个字节都没动"。"""
    import hashlib
    h = hashlib.sha1()
    for dp, dn, fn in os.walk(path):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, path)
            h.update(rel.encode('utf-8'))
            if os.path.islink(p):
                h.update(b'LINK')
                h.update(os.readlink(p).encode('utf-8'))
                continue
            try:
                with open(p, 'rb') as fh:
                    h.update(fh.read())
            except OSError:
                h.update(b'ERR')
    return h.hexdigest()


def fresh_tree():
    """夹具树的**临时副本**——需要真跑的用例只在这个副本里动手。"""
    d = tempfile.mkdtemp(prefix='startupctl-test-')
    dst = os.path.join(d, 'roots')
    shutil.copytree(FIXTURES, dst, symlinks=True)
    return dst


def scan_with(roots_dir, platform='darwin'):
    """在进程内扫一次夹具（不走子进程，方便断言）。

    用 try/finally 恢复 os.environ：这些进程内的平台切换如果泄漏，会让后面
    **子进程**用例跑在错误的平台上（见 run_cli 里的同类注释）。
    """
    saved = {k: os.environ.get(k) for k in ('STARTUPCTL_ROOTS', 'STARTUPCTL_PLATFORM')}
    try:
        os.environ['STARTUPCTL_ROOTS'] = roots_dir
        os.environ['STARTUPCTL_PLATFORM'] = platform
        for mod in [m for m in list(sys.modules) if m.startswith('startupctl')]:
            del sys.modules[mod]
        sys.path.insert(0, ROOT)
        from startupctl.core import context
        ctx = context.Ctx(platform=platform)
        return ctx, ctx.scan()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ================================================================ 域契约
def check_domain():
    section('域契约：解析 / 分类 / uid 稳定性')

    os.environ['STARTUPCTL_ROOTS'] = FIXTURES
    os.environ['STARTUPCTL_PLATFORM'] = 'darwin'
    sys.path.insert(0, ROOT)
    from startupctl.core import context, model
    from startupctl.core.model import ORIGIN_OS, ORIGIN_THIRD, ORIGIN_UNKNOWN

    ctx = context.Ctx(platform='darwin')
    res = ctx.scan()
    by_anchor = {}
    for it in res.items:
        by_anchor.setdefault(it.anchor, it)

    # --- 分类 ---
    it = by_anchor.get('com.docker.vmnetd')
    check(it is not None, '夹具里的 docker.vmnetd 被扫到')
    if it:
        check_eq(it.origin, ORIGIN_THIRD, 'PrivilegedHelperTools 下的项判为第三方')
        check_eq(it.confidence, 'high', '第三方判定置信度 high')
        check(it.mutable, '第三方项 mutable=True')

    # --- 空 plist 回落到文件名，且不崩 ---
    empty = [i for i in res.items if i.source.endswith('empty.plist')]
    check(len(empty) == 1, '空 plist 被扫到（没有 KeyError）')
    if empty:
        check_eq(empty[0].anchor, 'empty', '空 plist 的 anchor 回落到文件名词干')
        check(any('未声明 Label' in w for w in empty[0].warnings),
              '空 plist 记了"未声明 Label"的警告')

    # --- 畸形 plist 必须被**报出**，不能静默消失 ---
    bad = [e for e in res.errors if 'broken.plist' in (e.path or '')]
    check(len(bad) == 1, '畸形 plist 记为 ScanError（不是静默跳过）')

    # --- Label 与文件名不一致 → 只警告、不改判定 ---
    evil = [i for i in res.items if i.source.endswith('evil.plist')]
    check(len(evil) == 1, 'evil.plist 被扫到')
    if evil:
        check(any('身份与文件名不一致' in w for w in evil[0].warnings),
              'Label≠文件名 记了警告（可写位置）')
        # 一个写着 com.apple.* 的 plist 会被判成**系统项**而永不被本工具改动——
        # 即便它是伪装的。这是刻意的 fail-closed 方向：改不动真系统项 vs 可能动到
        # 伪装项，前者代价小得多；真正的信号交给上面那条警告让人去看。
        check_eq(evil[0].origin, ORIGIN_OS,
                 '声称 Apple 身份的项按系统项处理（fail-closed），靠警告提示人来复核')

    # --- 同机不同平台 ---
    for plat, expect_anchor in (('linux', 'nginx.service'), ('win32', None)):
        try:
            _, r2 = scan_with(FIXTURES, plat)
            check(True, '%s 平台能扫描夹具而不报错' % plat)
        except Exception as e:                                  # noqa: BLE001
            check(False, '%s 平台扫描夹具出错: %s: %s' % (plat, type(e).__name__, e))

    # --- uid 稳定性：同一个 anchor 必须永远得到同一个 uid ---
    u1 = model.make_uid('darwin', 'launchd-daemon', 'system', 'com.docker.vmnetd')
    u2 = model.make_uid('darwin', 'launchd-daemon', 'system', 'com.docker.vmnetd')
    check_eq(u1, u2, 'uid 对同一 anchor 稳定')
    u3 = model.make_uid('darwin', 'launchd-daemon', 'user', 'com.docker.vmnetd')
    check(u1 != u3, '不同 scope 得到不同 uid（同名不同域是两项）')

    # --- 分隔符不可歧义 ---
    a = model.make_uid('p', 'k', 's', 'a:b')
    b = model.make_uid('p', 'k', 's' + '', 'a')
    check(model.make_uid('p', 'k', 'a:b', 'c') != model.make_uid('p', 'k', 'a', 'b:c'),
          '用 \\x1f 连接，冒号不会造成歧义碰撞')

    # --- 指纹：身份不变但载荷变了 ---
    f1 = model.make_fingerprint('/bin/x', ('--a',))
    f2 = model.make_fingerprint('/bin/x', ('--b',))
    check(f1 != f2, '载荷指纹随参数变化（uid 不变而指纹变 → 可报漂移）')
    check_eq(model.make_uid('p', 'k', 's', 'x'), model.make_uid('p', 'k', 's', 'x'),
             '相同输入指纹/uid 可复现')

    # --- resolve：歧义必须报出来，不许替用户猜 ---
    items = [
        model.StartupItem(platform='darwin', kind='k', scope='s', anchor='com.a.one', key='a.one'),
        model.StartupItem(platform='darwin', kind='k', scope='s', anchor='com.a.two', key='a.two'),
    ]
    model.ensure_unique_keys(items)
    try:
        model.resolve(items, 'com.a.one')
        check(True, 'resolve 精确 anchor 命中')
    except Exception as e:                                      # noqa: BLE001
        check(False, 'resolve 精确 anchor 应当命中: %s' % e)
    try:
        model.resolve(items, 'com.a')
        check(False, 'resolve 歧义时应抛 AmbiguousRef')
    except model.AmbiguousRef:
        check(True, 'resolve 歧义时抛 AmbiguousRef（不替用户猜）')
    except Exception as e:                                      # noqa: BLE001
        check(False, 'resolve 歧义时抛了别的异常: %s' % e)

    # --- XDG 遮蔽必须被表示 ---
    try:
        os.environ['STARTUPCTL_PLATFORM'] = 'linux'
        _, r3 = scan_with(FIXTURES, 'linux')
        shadowed = [i for i in r3.items if i.shadowed_by]
        check(len(shadowed) >= 1, 'XDG 遮蔽被表示为 shadowed_by（不是装作系统那份启用）')
        xdg = [i for i in r3.items if i.kind == 'xdg-autostart']
        hidden = [i for i in xdg if i.anchor == 'foo.desktop' and i.enabled is False]
        check(len(hidden) >= 1, 'Hidden=true 的项 enabled=False')
        ng = [i for i in r3.items if i.anchor == 'nginx.service']
        check(len(ng) == 1, 'nginx.service 被扫到')
        if ng:
            check_eq(ng[0].origin, ORIGIN_THIRD, '/etc/systemd/system 下的真文件判为第三方(medium)')
            check_eq(ng[0].confidence, 'medium', '该系统判定为 medium（不确定就降级）')
        dbus = [i for i in r3.items if i.anchor == 'dbus.service']
        if dbus:
            check_eq(dbus[0].origin, ORIGIN_OS, '指向发行版单元的软链判为系统项')
    except Exception as e:                                      # noqa: BLE001
        check(False, 'Linux 夹具扫描出错: %s: %s' % (type(e).__name__, e))

    # --- Windows 夹具（注册表走 JSON shim）---
    try:
        _, r4 = scan_with(FIXTURES, 'win32')
        runs = [i for i in r4.items if i.kind == 'registry-run']
        check(len(runs) >= 4, 'Windows Run 键被解析出多项（得到 %d）' % len(runs))
        steam = [i for i in runs if i.anchor.endswith('\\Steam')]
        if steam:
            check_eq(steam[0].enabled, False,
                     'StartupApproved byte0=3 → 已禁用（不是"表里没有就启用")')
            check_eq(steam[0].enabled_reason, 'StartupApproved:disabled',
                     '禁用理由标明来自 StartupApproved')
        onedrive = [i for i in runs if i.anchor.endswith('\\OneDrive')]
        if onedrive:
            check_eq(onedrive[0].enabled, True, '无 StartupApproved 记录 → 默认启用')
            check('OneDrive.exe' in (onedrive[0].program or ''),
                  '带引号的命令行被正确拆出 program')
        svcs = [i for i in r4.items if i.kind == 'win-service']
        names = set(i.anchor for i in svcs)
        check('VendorSvc' in names, 'Start=2 的服务被列出')
        check('SomeDriver' not in names, 'Start=0 的驱动**不**出现在启动项里')
        vendor = [i for i in svcs if i.anchor == 'VendorSvc']
        if vendor:
            check_eq(vendor[0].origin, ORIGIN_THIRD, 'Program Files 下的服务判为第三方')
        wsvc = [i for i in svcs if i.anchor == 'WinSvc']
        if wsvc:
            check_eq(wsvc[0].origin, ORIGIN_OS, '%SystemRoot% 下的服务判为系统项')
        tasks = [i for i in r4.items if i.kind == 'task-scheduler']
        tn = set(i.anchor for i in tasks)
        check(any('VendorUpdate' in t for t in tn), '三方计划任务被列出')
        check(any('Defrag' in t for t in tn), '系统计划任务也被列出（供对照）')
        for t in tasks:
            if 'Defrag' in t.anchor:
                check_eq(t.origin, ORIGIN_OS, '\\Microsoft\\Windows\\ 下的任务判为系统项')
            if 'VendorUpdate' in t.anchor:
                check_eq(t.origin, ORIGIN_THIRD, '非 Microsoft 命名空间的任务判为第三方')
        w32 = [i for i in runs if 'Wow6432Node' in (i.source or '')]
        check(len(w32) >= 1, 'Wow6432Node（32 位视图）被单独枚举——否则漏掉一半')
    except Exception as e:                                      # noqa: BLE001
        check(False, 'Windows 夹具扫描出错: %s: %s' % (type(e).__name__, e))

    # --- 白名单：匹配与"只收窄" ---
    from startupctl.core import whitelist as wl_mod
    wl = wl_mod.Whitelist(entries=[
        {'match': 'anchor_glob', 'value': 'homebrew.mxcl.*'},
        {'match': 'vendor', 'value': 'com.docker'},
    ])
    mk = lambda **kw: model.StartupItem(platform='darwin', kind='k', scope='s', **kw)
    check(wl.matches(mk(anchor='homebrew.mxcl.redis', vendor='homebrew.mxcl')),
          'glob 规则命中')
    check(wl.matches(mk(anchor='com.docker.vmnetd', vendor='com.docker')),
          'vendor 规则命中')
    check(not wl.matches(mk(anchor='com.vivo.pcsuite', vendor='com.vivo')),
          '无关项不被命中')

    # id 条目的 anchor 回退：uid 变了（UID_VER 递增/单元改名）仍认得出来
    wl2 = wl_mod.Whitelist(entries=[
        {'match': 'id', 'value': 'deadbeefcafe', 'anchor': 'com.example.mine'}])
    check(wl2.matches(mk(anchor='com.example.mine', uid='0123456789ab')),
          'id 匹配不上时回退到存下的 anchor（抗 uid 变化）')

    # --- 白名单 doctor 不自动清理 ---
    before = len(wl2.entries)
    unmatched = wl2.unmatched([mk(anchor='com.other.thing')])
    check_eq(len(wl2.entries), before, 'unmatched() **不动**条目（只报告不清理）')
    check_eq(len(unmatched), 1, 'unmatched() 报出未命中的条目')


# ================================================================ 安全不变量
def check_reflective_guard():
    section('安全不变量 2：反射——每个后端 × 每个 mutator 遇系统项必拒')
    os.environ['STARTUPCTL_ROOTS'] = FIXTURES
    sys.path.insert(0, ROOT)
    from startupctl import backends
    from startupctl.core import context
    from startupctl.core.model import (KIND_LAUNCHD_DAEMON, ORIGIN_OS, SCOPE_SYSTEM,
                                       StartupItem)
    from startupctl.core.safety import Refused

    ctx = context.Ctx(platform='darwin')
    os_item = StartupItem(platform='darwin', kind=KIND_LAUNCHD_DAEMON, scope=SCOPE_SYSTEM,
                          anchor='com.apple.Finder', program='/System/Library/x',
                          source='/System/Library/LaunchAgents/com.apple.Finder.plist',
                          origin=ORIGIN_OS, confidence='high', origin_evidence='测试用',
                          mutable=False)

    total = 0
    for plat, cls in backends.all_backends():
        be = cls(ctx)
        for op in backends.MUTATORS:
            method = getattr(be, '_do_' + op, None)
            if method is None:
                check(False, '%s 后端缺少 _do_%s' % (plat, op))
                continue
            total += 1
            try:
                method(os_item, ctx, backup=None, entry=None)
                check(False, '%s.%s 对系统项**没有拒绝**（危险）' % (plat, op))
            except Refused:
                check(True, '%s.%s 对系统项抛 Refused' % (plat, op))
            except Exception as e:                              # noqa: BLE001
                check(False, '%s.%s 抛的不是 Refused 而是 %s: %s'
                      % (plat, op, type(e).__name__, e))
    check(total >= 12, '覆盖了 %d 个 后端×mutator 组合' % total)


def check_gate_order():
    section('安全不变量 9：白名单只能收窄，永远不能放宽')
    os.environ['STARTUPCTL_ROOTS'] = FIXTURES
    sys.path.insert(0, ROOT)
    from startupctl.core import context, manage, whitelist as wl_mod
    from startupctl.core.model import ORIGIN_OS, StartupItem
    from startupctl.core.safety import Refused

    ctx = context.Ctx(platform='darwin')
    ctx.scan()
    os_item = StartupItem(platform='darwin', kind='launchd-daemon', scope='system',
                          anchor='com.apple.Finder', source='/System/Library/x.plist',
                          origin=ORIGIN_OS, confidence='high')
    ctx.scanned_uids.add(os_item.uid)

    # 即便把它写进白名单，也**不能**变得可改
    ctx.whitelist = wl_mod.Whitelist(entries=[
        {'match': 'id', 'value': os_item.uid, 'anchor': os_item.anchor}])
    check(ctx.whitelist.matches(os_item), '系统项确实被白名单命中了')
    try:
        manage.check_gates(os_item, ctx, 'disable')
        check(False, '白名单让系统项通过了闸门（不变量被打破）')
    except Refused:
        check(True, '白名单命中后系统项**仍然**被拒绝（不变量成立）')

    # 候选集里也不会出现它
    res = ctx.scan()
    ctx.whitelist.apply(res.items)
    cands = manage.clean_candidates(res, ctx)
    check(all(c.origin == 'third_party' for c in cands),
          'clean 候选集里只有第三方项')
    check(all(c.mutable for c in cands), 'clean 候选集里都是可改的项')


def check_dry_run_and_confirm():
    section('安全不变量 3/4/11：预览、非交互拒绝、dry-run 零改动')

    # 3) 非交互且无 -y → 拒绝、零改动
    tree = fresh_tree()
    h0 = dir_hash(tree)
    rc, out = run_cli(['clean', '-y', '--dry-run'], {'STARTUPCTL_ROOTS': tree})
    check_eq(dir_hash(tree), h0, 'dry-run 后夹具树字节不变')
    check('--dry-run' in out, 'dry-run 输出里明说了未改动')

    rc, out = run_cli(['disable', 'com.docker.vmnetd'],
                      {'STARTUPCTL_ROOTS': tree, 'STARTUPCTL_DRY_RUN': '1'})
    check_eq(dir_hash(tree), h0, '环境变量 DRY_RUN=1 下 disable 也零改动')
    check_eq(rc, 0, 'DRY_RUN=1 时返回 0（CI 安全带）')

    # 4) 预览与执行的计划必须一致：dry-run 的计划行 == 真跑时的计划行
    tree2 = fresh_tree()
    rc_dry, out_dry = run_cli(['disable', 'homebrew.mxcl.mysql', '--dry-run'],
                              {'STARTUPCTL_ROOTS': tree2})
    plan_dry = [l for l in out_dry.splitlines() if l.strip().startswith('·')]
    rc_no, out_no = run_cli(['disable', 'homebrew.mxcl.mysql'],
                            {'STARTUPCTL_ROOTS': tree2})
    plan_no = [l for l in out_no.splitlines() if l.strip().startswith('·')]
    check(plan_dry == plan_no,
          'dry-run 的计划行与真跑时**逐字相同**（证明预览与执行共用 plan()）')
    check('非交互环境' in out_no and rc_no == 1,
          '非交互且无 -y 时拒绝执行并退 1')
    check_eq(dir_hash(tree2), dir_hash(fresh_tree()),
             '被拒绝的那次运行没有改动任何文件')


def check_system_item_untouched():
    section('安全不变量 1/10：系统项拒绝且字节不变；clean 只动第三方')
    tree = fresh_tree()
    sys_item_src = os.path.join(tree, 'darwin_user_agents', 'com.apple.useragent.plist')
    h_before = open(sys_item_src, 'rb').read()

    # 1) 直接 disable 系统项 → 退出 3，文件字节不变
    rc, out = run_cli(['disable', 'com.apple.useragent'],
                      {'STARTUPCTL_ROOTS': tree, 'STARTUPCTL_DRY_RUN': ''})
    check_eq(rc, 3, 'disable 系统项 → 退出码 3（因安全理由被拒绝）')
    check('拒绝' in out, '输出里明确写了"拒绝"')
    check_eq(open(sys_item_src, 'rb').read(), h_before,
             '被拒绝后系统项文件**字节不变**')

    # 10) clean -y 只动第三方，系统项字节不变
    tree2 = fresh_tree()
    tp_src = os.path.join(tree2, 'darwin_user_agents', 'com.example.mine.plist')
    sys2 = os.path.join(tree2, 'darwin_user_agents', 'com.apple.useragent.plist')
    h_sys = open(sys2, 'rb').read()
    h_tp_before = open(tp_src, 'rb').read()

    env = {'STARTUPCTL_ROOTS': tree2, 'STARTUPCTL_DRY_RUN': '0'}
    env.pop('STARTUPCTL_DRY_RUN', None)
    rc, out = run_cli(['clean', '-y'], {'STARTUPCTL_ROOTS': tree2})
    check_eq(open(sys2, 'rb').read(), h_sys, 'clean 后系统项字节不变')
    check(open(tp_src, 'rb').read() != h_tp_before or not os.path.exists(tp_src),
          'clean 后第三方项确实被改了（对照，证明 clean 真的动了手）')


def check_backup_and_restore():
    section('安全不变量 5/6/7：remove 只搬不删；restore 往返且拒绝覆盖')
    tree = fresh_tree()
    data = tempfile.mkdtemp(prefix='startupctl-data-')
    env = {'STARTUPCTL_ROOTS': tree, 'STARTUPCTL_DATA_DIR': data}

    src = os.path.join(tree, 'darwin_agents', 'homebrew.mxcl.mysql.plist')
    orig = open(src, 'rb').read()
    h0 = dir_hash(tree)

    # 5) remove → 原位置消失 + 备份里有一份内容相同的
    rc, out = run_cli(['remove', 'homebrew.mxcl.mysql', '-y'], env)
    check(not os.path.exists(src), 'remove 后源文件已不在原位')
    # 备份落到 <data>/backups/<ts>-remove/files/...
    found = []
    for dp, dn, fn in os.walk(os.path.join(data, 'backups')):
        for f in fn:
            if f == 'homebrew.mxcl.mysql.plist':
                found.append(os.path.join(dp, f))
    check(len(found) == 1, '备份目录里存了一份（找到 %d 份）' % len(found))
    if found:
        check_eq(open(found[0], 'rb').read(), orig, '备份内容与原文件一致（不是空壳）')
    mfs = []
    for dp, dn, fn in os.walk(os.path.join(data, 'backups')):
        if 'manifest.json' in fn:
            mfs.append(os.path.join(dp, 'manifest.json'))
    check(len(mfs) >= 1, 'manifest.json 已落盘')
    if mfs:
        m = json.load(open(mfs[0], encoding='utf-8'))
        check_eq(m.get('op'), 'remove', 'manifest 记录了操作类型')
        st = [i.get('status') for i in m.get('items', [])]
        check('done' in st, 'manifest 里该项状态为 done')

    # 6) restore → 内容回来
    rc, out = run_cli(['restore', 'last', '-y'], env)
    check(os.path.exists(src), 'restore 后文件回到原位')
    if os.path.exists(src):
        check_eq(open(src, 'rb').read(), orig, 'restore 后内容与原始一致（往返无损）')
    check_eq(dir_hash(tree), h0, 'restore 后夹具树指纹回到原值')

    # 7) restore 拒绝覆盖：先 remove，再手工重建一个内容不同的文件
    tree2 = fresh_tree()
    data2 = tempfile.mkdtemp(prefix='startupctl-data-')
    env2 = {'STARTUPCTL_ROOTS': tree2, 'STARTUPCTL_DATA_DIR': data2}
    src2 = os.path.join(tree2, 'darwin_agents', 'homebrew.mxcl.mysql.plist')
    run_cli(['remove', 'homebrew.mxcl.mysql', '-y'], env2)
    with open(src2, 'wb') as fh:
        fh.write(b'USER REWROTE THIS')
    rc, out = run_cli(['restore', 'last', '-y'], env2)
    check_eq(open(src2, 'rb').read(), b'USER REWROTE THIS',
             'restore 默认**拒绝**覆盖用户后来重写的文件')
    check('--force' in out, '拒绝时提示了 --force')


def check_incomplete_scan_refused():
    section('安全不变量 8：扫描不完整时 clean 拒绝运行（绝不在残缺视图上动手）')
    tree = fresh_tree()
    os.environ['STARTUPCTL_ROOTS'] = tree
    os.environ.pop('STARTUPCTL_PLATFORM', None)
    for mod in [m for m in list(sys.modules) if m.startswith('startupctl')]:
        del sys.modules[mod]
    sys.path.insert(0, ROOT)
    from startupctl.cli import cmd_clean
    from startupctl.core import context, manage
    from startupctl.core.model import ScanError

    ctx = context.Ctx(platform='darwin', dry_run=False, assume_yes=True)
    res = ctx.scan()
    base_cands = manage.clean_candidates(res, ctx)
    check(len(base_cands) > 0, '（前提）夹具上确实有可清理项 %d 个' % len(base_cands))

    h0 = dir_hash(tree)
    # 注入一个"读不到是因为权限"的根 → 整次扫描判为不完整
    res.errors.append(ScanError(root='darwin.daemons', path='/x', reason='权限不足',
                                needs_root=True))
    res.recompute_complete()
    check(not res.complete, '注入了 needs_root 错误后 complete=False')

    rc = cmd_clean(ctx, {'--yes': True})
    check_eq(rc, 3, '扫描不完整时 clean 因安全理由拒绝（退出 3）')
    check_eq(dir_hash(tree), h0, '被拒绝的 clean **一个字节都没改**')


def check_candidates_are_actionable():
    section('契约：clean 候选集 == 真的动得了的项')
    tree = fresh_tree()
    os.environ['STARTUPCTL_ROOTS'] = tree
    os.environ.pop('STARTUPCTL_PLATFORM', None)
    for mod in [m for m in list(sys.modules) if m.startswith('startupctl')]:
        del sys.modules[mod]
    sys.path.insert(0, ROOT)
    from startupctl.core import context, manage

    ctx = context.Ctx(platform='darwin')
    res = ctx.scan()
    ctx.wl().apply(res.items)
    cands = manage.clean_candidates(res, ctx)
    check(all(c.origin == 'third_party' for c in cands), '候选全是第三方项')
    check(all(c.mutable for c in cands), '候选全是 mutable（点了头就能真做成）')
    check(not any(c.whitelisted for c in cands), '候选里没有被白名单保护的项')

    # 白名单加一条 → 候选数必须**减少**（收窄），且不会多出任何项
    from startupctl.core import whitelist as wl_mod
    if cands:
        target = cands[0]
        ctx.whitelist = wl_mod.Whitelist(entries=[
            {'match': 'id', 'value': target.uid, 'anchor': target.anchor}])
        ctx.whitelist.apply(res.items)
        cands2 = manage.clean_candidates(res, ctx)
        check_eq(len(cands2), len(cands) - 1, '加一条白名单后候选数减少 1（只做减法）')
        check(all(c.uid != target.uid for c in cands2), '被白名单保护的那项确实不在候选里')


def check_roots_seam():
    section('安全不变量 12：夹具接缝生效——绝不读真机')
    tree = fresh_tree()
    rc, out = run_cli(['list', '--all'], {'STARTUPCTL_ROOTS': tree})
    check('夹具模式' in out, '输出里明说了处于夹具模式（不会被人当真机结果）')

    # 输出里不得出现夹具树之外的真实启动项路径
    leaked = []
    for needle in ('/System/Library/LaunchDaemons', '/Library/LaunchDaemons/',
                   '/Library/LaunchAgents/', '~/Library/LaunchAgents'):
        if needle in out:
            leaked.append(needle)
    check(not leaked, '输出里没有真机路径（泄漏: %s）' % (leaked or '无'))

    # 真正的断言：扫描到的每一项，其 source 都在夹具树里
    _, res = scan_with(tree, 'darwin')
    outside = [i.source for i in res.items
               if i.source and i.source.startswith('/') and not i.source.startswith(tree)]
    check(not outside, '所有扫到的项都来自夹具树（越界的: %s）' % (outside[:3] or '无'))


def check_guard_modes():
    section('进程守护：三种模式 + 系统基础进程的硬保护')
    sys.path.insert(0, ROOT)
    from startupctl.core import enforce, guard as G, picker
    from startupctl.core import proc as proc_mod

    def P(pid, comm, program, origin='third_party', uid=501, user='jj'):
        r = proc_mod.ProcRecord(pid=pid, ppid=1, uid=uid, user=user,
                                program=program, comm=comm, args_str=program)
        r.origin = origin
        return r

    sys_proc = P(100, 'WindowServer', '/System/Library/Frameworks/WindowServer',
                 origin='os', uid=88, user='_windowserver')
    third_proc = P(200, 'VendorHelper', '/Library/PrivilegedHelperTools/VendorHelper')
    other_proc = P(201, 'SomeTool', '/opt/homebrew/bin/sometool')

    # --- is_protected 的判据 ---
    check(G.is_protected(sys_proc, 'darwin')[0], '系统账户 + /System 路径 → 受保护')
    check(not G.is_protected(third_proc, 'darwin')[0], '第三方的 helper 不受保护（可管）')
    check(G.is_protected(P(1, 'launchd', '/sbin/launchd', 'os'), 'darwin')[0],
          'pid<=1 → 受保护')
    check(G.is_protected(P(300, 'MyShell', '/bin/zsh', 'third_party'),
                         'darwin', own_pids={300})[0],
          '本工具自身的 pid 链 → 受保护（否则等于锯自己脚下的地板）')
    check(G.is_protected(P(301, 'kworker/0:1', '', 'os', uid=0, user='root'), 'linux')[0],
          'Linux 内核线程 → 受保护')

    # --- ★ 三种模式都保留系统基础进程（用户明确要求）---
    procs = [sys_proc, third_proc, other_proc]
    for mode in (G.MODE_OFF, G.MODE_DENY_ALL, G.MODE_BLACKLIST, G.MODE_WHITELIST):
        g = G.Guard(mode=mode)
        deny, protect, allow = enforce.decide(procs, g, 'darwin', own_pids=set())
        sys_actions = [d.action for d in deny + protect + allow if d.proc.pid == 100]
        check_eq(sys_actions, [G.PROTECTED],
                 '%s 模式下系统基础进程被判为 PROTECTED（不会被结束）' % mode)

    # --- 各模式的语义 ---
    g = G.Guard(mode=G.MODE_OFF)
    deny, _p, allow = enforce.decide(procs, g, 'darwin', own_pids=set())
    check_eq(len(deny), 0, 'off 模式：不结束任何进程')

    g = G.Guard(mode=G.MODE_DENY_ALL)
    deny, protect, allow = enforce.decide(procs, g, 'darwin', own_pids=set())
    check_eq(len(deny), 2, '全部拒绝 + 空豁免清单：两个非系统进程都要结束')
    check_eq(len(protect), 1, '全部拒绝：系统进程受保护')

    g = G.Guard(mode=G.MODE_BLACKLIST,
                blacklist=[{'match': G.M_PROC_NAME, 'value': 'VendorHelper'}])
    deny, _p, allow = enforce.decide(procs, g, 'darwin', own_pids=set())
    check_eq(len(deny), 1, '黑名单：只结束命中的那一个')
    check_eq(deny[0].proc.pid, 200, '黑名单结束的是命中的那个 pid')

    g = G.Guard(mode=G.MODE_WHITELIST,
                whitelist=[{'match': G.M_PROC_NAME, 'value': 'SomeTool'}])
    deny, _p, allow = enforce.decide(procs, g, 'darwin', own_pids=set())
    check_eq(len(deny), 1, '白名单：只结束**没**命中的那一个')
    check_eq(deny[0].proc.pid, 200, '白名单结束的是未放行的 pid')

    # 全部拒绝模式下白名单清单是"豁免"
    g = G.Guard(mode=G.MODE_DENY_ALL,
                whitelist=[{'match': G.M_PROC_NAME, 'value': 'VendorHelper'}])
    deny, _p, allow = enforce.decide(procs, g, 'darwin', own_pids=set())
    check_eq(len(allow), 1, '全部拒绝模式下白名单条目作为**豁免**（放行）')
    check_eq(len(deny), 1, '全部拒绝：豁免之外仍要结束')

    # ★ 两份清单**互相独立**：黑名单模式**不看**白名单
    g = G.Guard(mode=G.MODE_BLACKLIST,
                whitelist=[{'match': G.M_PROC_NAME, 'value': 'VendorHelper'}],
                blacklist=[])
    deny, _p, _a = enforce.decide(procs, g, 'darwin', own_pids=set())
    check_eq(len(deny), 0,
             '黑名单模式下白名单里那条**不起任何作用**（两份清单独立）')

    # --- 匹配方式 ---
    g = G.Guard(mode=G.MODE_BLACKLIST,
                blacklist=[{'match': G.M_EXEC_PREFIX, 'value': '/opt/homebrew/'}])
    deny, _p, _a = enforce.decide(procs, g, 'darwin', own_pids=set())
    check_eq(len(deny), 1, 'exec_prefix 匹配命中 /opt/homebrew 下的进程')

    # --- 选择器：受保护的行**真的**选不了 ---
    rows = picker.Rows(procs + [sys_proc], 'darwin', own_pids=set())
    idx_sys = [i for i, r in enumerate(rows.rows) if r.proc.pid == 100][0]
    ok, why = rows.toggle(idx_sys)
    check(not ok, '选择器拒绝选中系统基础进程（不是只画成灰的）')
    check(bool(why), '拒绝时给出了原因: %s' % why[:36])
    check(not any(r.selected for r in rows.rows if r.proc.pid == 100),
          '系统进程没有被选中')
    idx_tp = [i for i, r in enumerate(rows.rows) if r.proc.pid == 200][0]
    ok2, _ = rows.toggle(idx_tp)
    check(ok2, '普通第三方进程可以选中')
    check_eq(len(rows.selected_procs()), 1, '选中集合里只有那一个')

    # --- 执行器：受保护进程绝不进入 kill 路径 ---
    g = G.Guard(mode=G.MODE_DENY_ALL)
    deny, protect, _a = enforce.decide([sys_proc], g, 'darwin', own_pids=set())
    check_eq(len(deny), 0, '系统进程不会出现在待结束列表里（执行器拿不到它）')

    # --- guard 持久化 ---
    d = tempfile.mkdtemp(prefix='sc-guard-')
    gp = G.Guard(mode=G.MODE_WHITELIST, path=os.path.join(d, 'guard.json'))
    gp.add(third_proc, reason='测试')
    gp.add(other_proc, name=G.LIST_BLACKLIST, reason='测试黑名单')
    gp.save()
    gp2 = G.Guard(path=os.path.join(d, 'guard.json')).load()
    check_eq(gp2.mode, G.MODE_WHITELIST, '模式能往返持久化')
    check_eq(len(gp2.whitelist), 1, '白名单能往返持久化')
    check_eq(len(gp2.blacklist), 1, '黑名单能往返持久化（两份独立保存）')
    check_eq(gp2.whitelist[0]['value'], 'VendorHelper', '白名单条目的值正确')
    check_eq(gp2.blacklist[0]['value'], 'SomeTool', '黑名单条目的值正确')

    # v1 老格式（单份 entries）迁移：内容不能丢
    import json as _json
    oldp = os.path.join(d, 'old.json')
    with open(oldp, 'w', encoding='utf-8') as fh:
        _json.dump({'version': 1, 'mode': 'blacklist',
                    'entries': [{'match': 'proc_name', 'value': 'Legacy'}]}, fh)
    mig = G.Guard(path=oldp).load()
    check_eq(len(mig.blacklist), 1, 'v1 老格式迁移到当前模式对应的那份清单（内容不丢）')
    check_eq(mig.blacklist[0]['value'], 'Legacy', '迁移后条目值不变')

    # 坏文件按"不干预"处理，且**不覆盖**
    with open(os.path.join(d, 'guard.json'), 'w') as fh:
        fh.write('{ this is not json')
    gp3 = G.Guard(path=os.path.join(d, 'guard.json')).load()
    check_eq(gp3.mode, G.MODE_OFF, '策略文件损坏时按「不干预」跑（不是乱杀）')


def check_guard_session_safety():
    section('进程守护：全部拒绝**绝不含你自己**（否则没法敲命令关掉它）')
    sys.path.insert(0, ROOT)
    from startupctl.core import enforce, guard as G, picker
    from startupctl.core import proc as proc_mod

    def P(pid, comm, program, origin='third_party', uid=501, user='jj'):
        r = proc_mod.ProcRecord(pid=pid, ppid=1, uid=uid, user=user,
                                program=program, comm=comm, args_str=program)
        r.origin = origin
        return r

    # shell / 终端 / 会话都必须受保护——即使它们的 origin 是 third_party
    for comm, prog in (('-zsh', '/bin/zsh'), ('bash', '/bin/bash'),
                       ('Terminal', '/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal'),
                       ('iTerm2', '/Applications/iTerm.app/Contents/MacOS/iTerm2'),
                       ('tmux', '/opt/homebrew/bin/tmux'), ('sshd', '/usr/sbin/sshd'),
                       ('pwsh', 'C:\\Program Files\\PowerShell\\pwsh.exe')):
        ok, why = G.is_protected(P(500, comm, prog), 'darwin', set())
        check(ok, '%s 受保护（%s）' % (comm, why[:26]))

    # 关键：**全部拒绝模式下**这些也不会被结束
    procs = [P(500, '-zsh', '/bin/zsh'), P(501, 'iTerm2', '/Applications/iTerm.app/x'),
             P(200, 'VendorHelper', '/Library/PrivilegedHelperTools/VendorHelper')]
    g = G.Guard(mode=G.MODE_DENY_ALL)
    deny, protect, allow = enforce.decide(procs, g, 'darwin', own_pids=set())
    check_eq(len(deny), 1, '全部拒绝：只结束那个真正的第三方进程')
    check_eq(deny[0].proc.comm, 'VendorHelper', '被结束的是厂商 helper，不是 shell/终端')
    check_eq(len(protect), 2, 'shell 与终端都在受保护之列')
    sess = [d for d in protect if '还能操作' in d.reason]
    check_eq(len(sess), 2, '两者的保护理由都是「还能操作」保障')


def check_guard_locked_entries():
    section('进程守护：锁定条目在任何模式下都不结束（且选不动）')
    sys.path.insert(0, ROOT)
    from startupctl.core import enforce, guard as G, picker
    from startupctl.core import proc as proc_mod

    def P(pid, comm, program, origin='third_party'):
        r = proc_mod.ProcRecord(pid=pid, ppid=1, uid=501, user='jj',
                                program=program, comm=comm, args_str=program)
        r.origin = origin
        return r

    db = P(200, 'mysqld', '/opt/db/bin/mysqld')
    tool = P(201, 'SomeTool', '/opt/homebrew/bin/tool')

    # 锁定条目在**每种模式**下都 PROTECTED
    for mode in (G.MODE_OFF, G.MODE_DENY_ALL, G.MODE_BLACKLIST, G.MODE_WHITELIST):
        # 锁定条目分别放进两份清单，验证"跨清单都受保护"
        g = G.Guard(mode=mode,
                    whitelist=[{'match': G.M_PROC_NAME, 'value': 'mysqld',
                                'locked': True}])
        deny, protect, allow = enforce.decide([db, tool], g, 'darwin', own_pids=set())
        check(not any(d.proc.pid == 200 for d in deny),
              '%s 模式下锁定条目不被结束' % mode)
        check(any(d.proc.pid == 200 for d in protect),
              '%s 模式下锁定条目落在受保护里' % mode)

    # 锁定的语义**与模式无关**：白名单模式下它是"放行"，但更准确说是"别碰"
    g = G.Guard(mode=G.MODE_WHITELIST,
                whitelist=[{'match': G.M_PROC_NAME, 'value': 'mysqld', 'locked': True}])
    d200 = [d for d in sum(enforce.decide([db], g, 'darwin', own_pids=set()), [])
            if d.proc.pid == 200][0]
    check_eq(d200.action, G.PROTECTED,
             '锁定条目是 PROTECTED 而不是 ALLOW（锁定=别动它，与在哪个清单无关）')

    # ★ 锁定跨清单生效：锁在黑名单里的条目，白名单模式下也受保护
    g = G.Guard(mode=G.MODE_WHITELIST,
                blacklist=[{'match': G.M_PROC_NAME, 'value': 'mysqld', 'locked': True}])
    d200 = [d for d in sum(enforce.decide([db], g, 'darwin', own_pids=set()), [])
            if d.proc.pid == 200][0]
    check_eq(d200.action, G.PROTECTED,
             '锁在黑名单里的条目，在白名单模式下同样受保护（锁定跨清单）')

    # 未锁定 vs 锁定：同样在白名单里，前者放行、后者受保护
    g = G.Guard(mode=G.MODE_WHITELIST,
                whitelist=[{'match': G.M_PROC_NAME, 'value': 'mysqld', 'locked': False}])
    d200 = [d for d in sum(enforce.decide([db], g, 'darwin', own_pids=set()), [])
            if d.proc.pid == 200][0]
    check_eq(d200.action, G.ALLOW, '未锁定的白名单条目是 ALLOW')

    # set_locked / is_locked_value 往返（跨两份清单）
    g = G.Guard(mode=G.MODE_OFF,
                blacklist=[{'match': G.M_PROC_NAME, 'value': 'mysqld'}])
    check(not g.is_locked_value('mysqld'), '新条目默认未锁定')
    check_eq(g.set_locked('mysqld', True), 1, 'set_locked 改了 1 条')
    check(g.is_locked_value('mysqld'), '锁定后 is_locked_value 为真')
    g.set_locked('mysqld', False)
    check(not g.is_locked_value('mysqld'), '解锁后恢复')
    check_eq(g.set_locked('nosuch', True), 0, '锁定不存在的值返回 0（不凭空造条目）')

    # 选择器：锁定行与系统进程一样选不动，但可以解锁
    rows = picker.Rows([db, tool], 'darwin', own_pids=set(),
                       locked_matcher=lambda p: p.comm == 'mysqld')
    i_db = [i for i, r in enumerate(rows.rows) if r.proc.pid == 200][0]
    i_tool = [i for i, r in enumerate(rows.rows) if r.proc.pid == 201][0]
    check(rows.rows[i_db].locked, '已锁定条目在选择器里被标为 locked')
    check_eq(rows.rows[i_db].mark, '[锁定]', '锁定行显示为 [锁定]')
    ok, why = rows.toggle(i_db)
    check(not ok, '锁定行选不动（空格被拒绝）')
    check('解锁' in why, '拒绝时提示了解锁办法')
    ok2, _ = rows.toggle_lock(i_db)
    check(ok2, 'L 键可以解锁')
    check(not rows.rows[i_db].locked, '解锁后不再是 locked')
    check(rows.rows[i_db].selected, '解锁后仍留在集合里（只是重新可选了）')
    ok3, _ = rows.toggle(i_tool)
    check(ok3, '普通行仍可正常选中')
    check_eq(len(rows.results()), 2, 'results 返回集合里全部条目（含未锁定的）')

    # 系统进程不可锁定
    sysp = P(100, 'WindowServer', '/System/Library/x', origin='os')
    rows2 = picker.Rows([sysp], 'darwin', own_pids=set())
    ok4, why4 = rows2.toggle_lock(0)
    check(not ok4, '系统基础进程不可锁定（它本来就动不了）')


def check_guard_lock_cli():
    section('进程守护 CLI：lock / unlock')
    shared = tempfile.mkdtemp(prefix='sc-guard-lock-')
    env = {'STARTUPCTL_DATA_DIR': shared}
    rc, out = run_cli(['guard', 'mode', 'deny_all'], env)
    # 用 --value 预先下规则：**不依赖真机上恰好有同名进程**（这正是 --value 的用途）
    rc, out = run_cli(['guard', 'add', '--value', 'VendorHelper', '--reason', '测试'], env)
    check_eq(rc, 0, 'guard add --value 退出 0（可为没在跑的东西预先立规矩）')
    check('出现时生效' in out, '预下规则时提示它会在进程出现时生效')

    # --lock 一步到位
    rc, out = run_cli(['guard', 'add', '--value', 'OtherThing', '--lock'], env)
    check_eq(rc, 0, 'guard add --lock 退出 0')
    check('已锁定' in out, 'add --lock 直接锁定')

    rc, out = run_cli(['guard', 'lock', 'VendorHelper'], env)
    check_eq(rc, 0, 'guard lock 退出 0')
    check('任何模式下都不会被结束' in out, 'lock 说明它会受保护')

    rc, out = run_cli(['guard', 'list'], env)
    check('锁定' in out, 'guard list 显示锁定状态')

    rc, out = run_cli(['guard', 'lock', 'nosuchentry'])
    check_eq(rc, 2, 'lock 不存在的值退出 2')

    rc, out = run_cli(['guard', 'unlock', 'VendorHelper'], env)
    check_eq(rc, 0, 'guard unlock 退出 0')

    rc, out = run_cli(['guard', 'check'], env)
    check('还能操作' in out, 'guard check 说明 shell/终端受「还能操作」保障')


def check_guard_cli():
    section('进程守护 CLI：模式切换与结构性拒绝')
    rc, out = run_cli(['guard', 'status'])
    check_eq(rc, 0, 'guard status 退出 0')
    check('不干预' in out, '默认模式为「不干预」（不会一装上就开始杀进程）')

    rc, out = run_cli(['guard', 'mode'])
    check_eq(rc, 0, 'guard mode（无参数）列出可选模式')
    for m in ('deny_all', 'blacklist', 'whitelist', 'off'):
        check(m in out, '模式列表含 %s' % m)

    # ⚠️ 这一组用例必须**共用一个数据目录**：run_cli 默认每次给一个全新的
    #    STARTUPCTL_DATA_DIR（用例间互不干扰是有意的），但"设了模式再 arm"是一条
    #    有状态的流程，各跑各的目录会让模式根本没被持久化，arm 于是报"当前为不干预"。
    shared = tempfile.mkdtemp(prefix='sc-guard-cli-')
    env = {'STARTUPCTL_DATA_DIR': shared}

    rc, out = run_cli(['guard', 'mode', 'deny_all'], env)
    check_eq(rc, 0, 'guard mode deny_all 退出 0')
    check('系统基础进程' in out, '切换模式时明说系统基础进程不受影响')

    rc, out = run_cli(['guard', 'mode', 'nosuchmode'], env)
    check_eq(rc, 2, '未知模式退出 2（用法错）')

    rc, out = run_cli(['guard', 'check'], env)
    check('模式:' in out, 'guard check 打印当前模式')

    # --dry-run 必须中和 arm（绝不为预览而结束任何进程）
    rc, out = run_cli(['guard', 'arm', '-y', '--dry-run'], env)
    check('--dry-run' in out, 'guard arm 在 --dry-run 下只预览')
    check_eq(rc, 0, 'guard arm --dry-run 退出 0')

    # arm 不带 -y 且在非交互环境 → 拒绝执行
    rc, out = run_cli(['guard', 'arm'], env)
    check_eq(rc, 1, 'guard arm 非交互无 -y → 拒绝并退 1')
    check('非交互环境' in out, 'guard arm 拒绝时说明了原因')


def check_gui_picker():
    section('图形选择器：能开、能选、能在无显示环境优雅回退')
    sys.path.insert(0, ROOT)
    from startupctl.core import gui, guard as G, picker
    from startupctl.core import proc as proc_mod

    ok, why = gui.available()
    check(isinstance(ok, bool), 'gui.available() 返回 (bool, 原因)')
    if not ok:
        check(bool(why), '不可用时给出原因: %s' % why[:44])

    def P(pid, comm, program, origin='third_party'):
        r = proc_mod.ProcRecord(pid=pid, ppid=1, uid=501, user='jj',
                                program=program, comm=comm, args_str=program)
        r.origin = origin
        return r

    procs = [P(100, 'WindowServer', '/System/Library/x', origin='os'),
             P(200, 'mysqld', '/opt/db/bin/mysqld'),
             P(201, 'SomeTool', '/opt/homebrew/bin/tool'),
             P(202, 'Other', '/opt/other/bin/other')]

    # --- 非交互环境：必须回退，且**说明原因**（不许静默换个界面）---
    # Rows 供三个 UI 共用，所以"能不能选"的规则只需在这里验一次。
    # ⚠️ Rows 按名字排序，**别假定某一行的下标**——按 pid 找。
    rows = picker.Rows(procs, 'darwin', own_pids=set())
    check_eq(len(rows.rows), 4, 'Rows 建出 4 行')
    i_sys = [i for i, r in enumerate(rows.rows) if r.proc.pid == 100][0]
    i_ok = [i for i, r in enumerate(rows.rows) if r.proc.pid == 200][0]
    check(rows.rows[i_sys].protected, '系统行标记为 protected（GUI 里会置灰不可点）')
    check_eq(rows.rows[i_sys].mark, '[系统]', '系统行显示标记为 [系统]')
    check(rows.rows[i_sys].frozen, '系统行 frozen（GUI/TUI 都据此禁掉点击）')
    check(not rows.rows[i_ok].frozen, '普通行不 frozen（可点）')

    # --- 自测接缝：真开一次窗口，验证它能选出结果 ---
    if ok or os.environ.get('STARTUPCTL_GUI_SELFTEST') is not None:
        os.environ['STARTUPCTL_GUI_SELFTEST'] = '2'
        try:
            rows = picker.Rows(procs, 'darwin', own_pids=set())
            got = gui.pick(rows, 'darwin', set())
            check(got is not None, 'GUI 自测返回了结果（不是 None）')
            if got:
                check_eq(len(got), 2, 'GUI 自动选了 2 个')
                check(all(not G.is_protected(p, 'darwin', set())[0] for p, _lk in got),
                      'GUI 返回的结果里**没有系统基础进程**')
                check(all(p.comm != 'WindowServer' for p, _lk in got),
                      '系统行没被选进来（点击处理里就忽略了）')
        except gui.GuiUnavailable as e:
            check(True, '无显示环境，GUI 抛 GuiUnavailable（调用方据此回退）: %s' % str(e)[:30])
        finally:
            os.environ.pop('STARTUPCTL_GUI_SELFTEST', None)

    # --- 纯文本选择器：非法输入必须**出声**，不能静默跳过 ---
    import io as _io
    rows = picker.Rows(procs, 'darwin', own_pids=set())
    buf = _io.StringIO()
    real_stdin, sys.stdin = sys.stdin, _io.StringIO('99,abc\n')
    try:
        picked = picker._pick_plain(rows, out=buf)
    except Exception as e:                                       # noqa: BLE001
        picked = 'ERR:%s' % e
    finally:
        sys.stdin = real_stdin
    text = buf.getvalue()
    check('没有生效' in text, '纯文本模式对非法编号明确报「没有生效」')
    check('1-' in text, '报错时给出可用编号范围')
    check(picked is None, '全是非法输入时视为取消（不清空清单）')

    # 合法输入正常生效
    buf2 = _io.StringIO()
    real_stdin, sys.stdin = sys.stdin, _io.StringIO('1,2!\n')
    try:
        picked2 = picker._pick_plain(rows, out=buf2)
    finally:
        sys.stdin = real_stdin
    check(picked2 is not None and len(picked2) == 2, '合法输入 1,2! 选中 2 项')
    if picked2:
        check_eq(picked2[0][1], False, '第 1 项未锁定')
        check_eq(picked2[1][1], True, '第 2 项（带 !）被锁定')


def check_writeback_verified():
    section('写回核对：改动没生效时**必须报错**，不许静默通过')
    shared = tempfile.mkdtemp(prefix='sc-verify-')
    env = {'STARTUPCTL_DATA_DIR': shared}

    rc, out = run_cli(['guard', 'add', '--value', 'VerifyMe'], env)
    check_eq(rc, 0, 'guard add 退出 0')
    check('已写入并核对无误' in out, '添加后报告「已写入并核对无误」')

    # 核对不是嘴上一说：真的读回来比对
    gpath = os.path.join(shared, 'guard.json')
    check(os.path.isfile(gpath), 'guard.json 真的落盘了')
    if os.path.isfile(gpath):
        with open(gpath, encoding='utf-8') as fh:
            disk = json.load(fh)
        # 新 schema 是两份独立清单
        check('whitelist' in disk and 'blacklist' in disk,
              '磁盘上是两份独立清单（whitelist / blacklist）')
        vals = [e.get('value') for e in disk.get('whitelist', [])] + \
               [e.get('value') for e in disk.get('blacklist', [])]
        check('VerifyMe' in vals, '磁盘上的内容与命令输出一致（核对是真的）')
        check_eq(disk.get('version'), 2, 'schema 版本为 2')

    # 独立进程再读一次：确认不是"内存里看着有、磁盘上没有"
    rc, out = run_cli(['guard', 'list'], env)
    check('VerifyMe' in out, '另一个进程读得到同一条（跨进程持久化成立）')

    # 写不进去时必须报错并返回非零。
    #
    # ⚠️ 用 "把数据目录指到一个**普通文件**底下" 来制造失败，而不是 chmod 0500：
    #    root 有 CAP_DAC_OVERRIDE，会**绕过**权限检查，0500 的目录照样能写。
    #    在 root 下跑（CI 容器、root 登录的测试机）时，chmod 那招会让这条用例
    #    失败得莫名其妙——看着像产品 bug，其实是测试环境的前提不成立。
    #    ENOTDIR（在文件下面建目录）谁都绕不过，root 也不行。
    not_a_dir = os.path.join(ROOT, 'VERSION')          # 仓库里一个确定的普通文件
    check(os.path.isfile(not_a_dir), '（前提）用于制造写失败的路径确实是个普通文件')
    rc, out = run_cli(['guard', 'add', '--value', 'Nope'],
                      {'STARTUPCTL_DATA_DIR': os.path.join(not_a_dir, 'sub')})
    check(rc != 0, '写盘失败时返回非零（不谎报成功）')
    check(('失败' in out) or ('错误' in out), '写盘失败时给出明确错误信息')
    check('核对' not in out or '不一致' in out,
          '写盘失败时**不会**打出「已写入并核对无误」')


def check_guard_mode_vs_choice():
    section('进程守护：模式与选择分开 + 只有选择过才生效')
    shared = tempfile.mkdtemp(prefix='sc-mc-')
    env = {'STARTUPCTL_DATA_DIR': shared}

    # 1) 切模式不改动任何清单内容 —— 两份都原样留着
    run_cli(['guard', 'mode', 'whitelist'], env)
    run_cli(['guard', 'add', '--value', 'AllowedThing'], env)
    run_cli(['guard', 'mode', 'blacklist'], env)
    rc, out = run_cli(['guard', 'add', '--value', 'BannedThing'], env)
    check_eq(rc, 0, '黑名单里加一条')
    run_cli(['guard', 'mode', 'whitelist'], env)
    rc, out = run_cli(['guard', 'list'], env)
    check('AllowedThing' in out, '切回白名单：白名单内容还在')
    check('BannedThing' in out, '切回白名单：**黑名单内容也还在**（两份独立）')
    check('← 当前模式在用' in out, 'list 标出当前模式在用哪一份')

    # 2) 空清单不许执行 —— 「只有选择的时候才生效」
    empty = tempfile.mkdtemp(prefix='sc-empty-')
    e2 = {'STARTUPCTL_DATA_DIR': empty}
    run_cli(['guard', 'mode', 'whitelist'], e2)
    rc, out = run_cli(['guard', 'arm', '-y'], e2)
    check_eq(rc, 3, '白名单为空时 arm 被拒绝（退出 3）')
    check('白名单是空的' in out, '拒绝时点明白名单是空的')
    check('guard choose' in out, '拒绝时指路到 guard choose')

    rc, out = run_cli(['guard', 'mode', 'blacklist'], e2)
    run_cli(['guard', 'mode', 'blacklist'], e2)
    rc, out = run_cli(['guard', 'arm', '-y'], e2)
    check_eq(rc, 3, '黑名单为空时 arm 也被拒绝（没有要结束的对象）')

    # off 模式下 arm 同样拒绝（没有可执行的策略）
    rc, out = run_cli(['guard', 'mode', 'off'], e2)
    rc, out = run_cli(['guard', 'arm', '-y'], e2)
    check_eq(rc, 3, 'off 模式 arm 被拒绝')

    # 3) 有内容之后就允许执行了（用 deny_all 免去挑进程）
    run_cli(['guard', 'mode', 'deny_all'], e2)
    rc, out = run_cli(['guard', 'arm', '--dry-run'], e2)
    check_eq(rc, 0, '全部拒绝模式可执行（--dry-run 下退出 0）')
    check('--dry-run' in out, 'arm 在 dry-run 下只预览')

    # 4) guard choose 在非交互环境下优雅拒绝（不弹窗、不崩）
    rc, out = run_cli(['guard', 'choose', '--plain'], e2)
    check(rc in (0, 1, 2), 'guard choose --plain 非交互下正常返回（rc=%d）' % rc)

    # 5) off 模式下 choose 无处可写 → 明确指路
    run_cli(['guard', 'mode', 'off'], e2)
    rc, out = run_cli(['guard', 'choose'], e2)
    check_eq(rc, 2, 'off 模式下 choose 退出 2（没有对应清单）')
    check('先选模式' in out, '提示先选模式')


def check_gui_only_via_choose():
    section('图形窗口只在 guard choose 时启动（不是常态）')
    sys.path.insert(0, ROOT)
    import inspect
    from startupctl.core import picker
    src = inspect.getsource(picker.pick)
    check('allow_gui' in src, 'picker.pick 有 allow_gui 参数')
    check('allow_gui=True' in src or 'allow_gui and' in src,
          'picker.pick 只在 allow_gui 为真时才走图形窗口')

    # 默认必须是 False —— 日常命令不该突然弹窗
    sig = inspect.signature(picker.pick)
    check_eq(sig.parameters['allow_gui'].default, False,
             'allow_gui 默认 False（GUI 不是常态）')

    # CLI：只有 choose/pick 会传 allow_gui
    from startupctl import cli as cli_mod
    csrc = inspect.getsource(cli_mod._do_choose)
    check('allow_gui=use_gui' in csrc, 'guard choose 才会请求图形窗口')
    check('--tui' in csrc and '--plain' in csrc, 'choose 支持 --tui/--plain 强制别的界面')


def check_cli_contracts():
    section('CLI 契约：HELP 行数 / 对齐 / 退出码')
    sys.path.insert(0, ROOT)
    from startupctl import help as H

    check(H.help_lines() <= 50, 'HELP 行数 %d <= 50' % H.help_lines())
    for anchor in ('用法:', '子命令:', '选项:', '示例:', '说明:'):
        check(any(l.strip() == anchor for l in H.HELP.splitlines()),
              'HELP 含分节 %s' % anchor)
    probs = H.align_report()
    check(not probs, 'HELP 各节描述列对齐一致（问题: %s）' % (probs[:2] or '无'))
    check(max(__import__('startupctl.core.output', fromlist=['dw']).dw(l)
              for l in H.HELP.splitlines()) <= 100, 'HELP 最宽行 <= 100 列')
    for sub in ('list', 'clean', 'whitelist', 'add', 'restore'):
        check(H.sub_help(sub) is not None, '子命令 %s 有专属帮助' % sub)

    rc, out = run_cli(['--version'])
    check_eq(rc, 0, '--version 退出 0')
    check('startupctl' in out and '1.0.0' in out, '--version 打印版本号')
    rc, out = run_cli(['help'])
    check_eq(rc, 0, 'help 退出 0')
    rc, out = run_cli(['nosuchcmd'])
    check_eq(rc, 2, '未知子命令退出 2（用法错）')


def check_version_sync():
    section('版本一致性：VERSION 文件 vs 包 __version__')
    sys.path.insert(0, ROOT)
    from startupctl import __version__
    vf = open(os.path.join(ROOT, 'VERSION'), encoding='utf-8').read().strip()
    check_eq(vf, __version__, 'VERSION 文件与 startupctl.__version__ 一致')


def main():
    print('startupctl 单元冒烟')
    print('仓库: %s' % ROOT)
    check_version_sync()
    check_domain()
    check_gate_order()
    check_reflective_guard()
    check_dry_run_and_confirm()
    check_system_item_untouched()
    check_backup_and_restore()
    check_incomplete_scan_refused()
    check_candidates_are_actionable()
    check_roots_seam()
    check_guard_modes()
    check_guard_session_safety()
    check_guard_locked_entries()
    check_guard_cli()
    check_guard_lock_cli()
    check_guard_mode_vs_choice()
    check_gui_only_via_choose()
    check_gui_picker()
    check_writeback_verified()
    check_cli_contracts()

    print('')
    print('=' * 60)
    if FAILS:
        print('失败 %d 项 / 通过 %d 项' % (len(FAILS), PASSES[0]))
        for f in FAILS:
            print('  [FAIL] %s' % f)
        return 1
    print('全部通过（%d 项断言）' % PASSES[0])
    return 0


if __name__ == '__main__':
    sys.exit(main())
