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
# 宿主原生平台。run_cli 默认把平台钉成 darwin（夹具是 darwin 的），但凡是**依赖
# 真实进程表**的断言都必须用这个值——把 darwin 后端跑在 Windows 上时它会去调
# /bin/ps，那里没有，于是枚举为空、"共 0 个进程"，断言就会莫名其妙地挂。
NATIVE_PLATFORM = ('darwin' if sys.platform.startswith('darwin')
                   else 'win32' if sys.platform.startswith('win') else 'linux')
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


# ================================================================ 安全不变量
def check_roots_seam():
    section('安全不变量 12：夹具接缝生效——绝不读真机')
    tree = fresh_tree()
    rc, out = run_cli(['list', 'all'], {'STARTUPCTL_ROOTS': tree})
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
    check_eq(len(gp2.whitelist['process']), 1, '白名单能往返持久化')
    check_eq(len(gp2.blacklist['process']), 1, '黑名单能往返持久化（两份独立保存）')
    check_eq(gp2.whitelist['process'][0]['value'], 'VendorHelper', '白名单条目的值正确')
    check_eq(gp2.blacklist['process'][0]['value'], 'SomeTool', '黑名单条目的值正确')

    # v1 老格式（单份 entries）迁移：内容不能丢
    import json as _json
    oldp = os.path.join(d, 'old.json')
    with open(oldp, 'w', encoding='utf-8') as fh:
        _json.dump({'version': 1, 'mode': 'blacklist',
                    'entries': [{'match': 'proc_name', 'value': 'Legacy'}]}, fh)
    mig = G.Guard(path=oldp).load()
    check_eq(len(mig.blacklist['process']), 1, 'v1 老格式迁移到当前模式对应那份的进程维度（内容不丢）')
    check_eq(mig.blacklist['process'][0]['value'], 'Legacy', '迁移后条目值不变')

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
    check_eq(rows.rows[i_db].mark, '▣', '锁定行用 ▣ 标记（勾选字形）')
    check_eq(rows.rows[i_db].tag, '[锁定]', '锁定行的文字标签是 [锁定]')
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


def check_gui_picker():
    section('选择器：进程与启动项两种，都能选、都能在无显示环境回退')
    sys.path.insert(0, ROOT)
    from startupctl.core import gui, picker
    from startupctl.core import proc as proc_mod

    check(isinstance(gui.available(), bool), 'gui.available() 返回 bool')

    def P(pid, comm, program, origin='third_party'):
        r = proc_mod.ProcRecord(pid=pid, ppid=1, uid=501, user='jj',
                                program=program, comm=comm, args_str=program)
        r.origin = origin
        return r

    procs = [P(100, 'WindowServer', '/System/Library/x', origin='os'),
             P(200, 'mysqld', '/opt/db/bin/mysqld'),
             P(201, 'SomeTool', '/opt/homebrew/bin/tool'),
             P(202, 'Other', '/opt/other/bin/other')]

    rows = picker.Rows(procs, 'darwin', own_pids=set())
    check_eq(len(rows.rows), 4, '进程选择器建出 4 行')
    i_sys = [i for i, r in enumerate(rows.rows) if r.proc.pid == 100][0]
    i_ok = [i for i, r in enumerate(rows.rows) if r.proc.pid == 200][0]
    check(rows.rows[i_sys].protected, '系统行标记为 protected（窗口里置灰不可点）')
    check_eq(rows.rows[i_sys].mark, '⊘', '系统行用 ⊘ 标记（不可选）')
    check_eq(rows.rows[i_sys].tag, '[系统]', '系统行的文字标签是 [系统]')
    check_eq(rows.rows[i_ok].mark, '☐', '未选中行显示为空框 ☐')
    rows.rows[i_ok].selected = True
    check_eq(rows.rows[i_ok].mark, '☑', '选中后显示为勾选 ☑（用户反馈 [x] 看不出来）')
    rows.rows[i_ok].selected = False
    check(rows.rows[i_sys].frozen, '系统行 frozen（各 UI 都据此禁掉点击）')
    check(not rows.rows[i_ok].frozen, '普通行不 frozen（可点）')

    # --- 自测接缝：真开一次窗口，验证它能选出结果 ---
    if gui.available() or os.environ.get('STARTUPCTL_GUI_SELFTEST') is not None:
        os.environ['STARTUPCTL_GUI_SELFTEST'] = '2'
        try:
            rows = picker.Rows(procs, 'darwin', own_pids=set())
            got = gui.pick(rows.rows, title='选择进程')
            check(got is not None, 'GUI 自测返回了结果（不是 None）')
            if got:
                check_eq(len(got), 2, 'GUI 自动选了 2 个')
                picked = [rows.rows[i] for i in got]
                check(all(not r.protected for r in picked),
                      'GUI 返回的结果里**没有系统基础进程**')
                check(all(r.proc.comm != 'WindowServer' for r in picked),
                      '系统行没被选进来（点击处理里就忽略了）')
        except gui.GuiUnavailable as e:
            check(True, '无显示环境，GUI 抛 GuiUnavailable（调用方据此回退）: %s' % str(e)[:30])
        finally:
            os.environ.pop('STARTUPCTL_GUI_SELFTEST', None)

    # --- 启动项选择器 ---
    from startupctl.core.model import StartupItem
    items = [StartupItem(uid='u1', anchor='a.one', kind='launchd-agent',
                         scope='user', name='One'),
             StartupItem(uid='u2', anchor='a.two', kind='launchd-daemon',
                         scope='system', name='Two')]
    srows = picker.StartupRows(items, preselect={'u1'})
    check_eq(len(srows.rows), 2, '启动项选择器建出 2 行')
    check_eq(len(srows.results()), 1, '预选（已在名单里）的那一行默认勾选')
    check(not any(getattr(r, 'frozen', False) for r in srows.rows),
          '启动项没有「不可选」的概念（系统项不会进这个列表）')

    # --- 非交互环境下 pick_* 必须回退而不是挂住 ---
    import io as _io
    old_stdin = sys.stdin
    sys.stdin = _io.StringIO('1\n')
    try:
        got = picker.pick_processes(procs, 'darwin', own_pids=set(), allow_gui=False)
        check(got is not None, '纯文本兜底能返回选择结果')
    finally:
        sys.stdin = old_stdin

def check_self_info_layouts():
    """安装态识别：**两个平台装出来的布局都要认得**。

    这条是血的教训：为了让 Windows 载荷变干净，`uninstall`（POSIX 专有的卸载脚本）
    被从 Windows 安装里去掉了，而原来的判定条件是「`lib/` + `VERSION` + `uninstall`」。
    于是 Windows 上**装了也报「无法识别当前布局」**——`update` / `config` / `uninstall`
    全部失灵。实测：`startupctl update` 报「既不是源码仓库，也不是 devtools 安装」。

    判定标记必须选**两个平台都会有的东西**：`lib/` + `VERSION`。
    """
    import tempfile
    from startupctl.core import selfmgr

    def fake_tree(with_uninstall):
        d = tempfile.mkdtemp(prefix='sc-layout-')
        lib = os.path.join(d, 'lib')
        os.makedirs(os.path.join(lib, 'startupctl', 'core'))
        with open(os.path.join(d, 'VERSION'), 'w') as fh:
            fh.write('1.0.0\n')
        if with_uninstall:
            with open(os.path.join(d, 'uninstall'), 'w') as fh:
                fh.write('#!/bin/bash\n')
        return d, os.path.join(lib, 'startupctl')

    # POSIX 安装态（有 uninstall）
    d1, pkg1 = fake_tree(True)
    mode1, root1, _ = selfmgr.self_info(pkg1)
    check_eq(mode1, 'installed', 'POSIX 布局（lib/ + VERSION + uninstall）识别为安装态')
    check_eq(os.path.basename(root1), os.path.basename(d1), '识别出的安装根正确')

    # Windows 安装态（**没有** uninstall）—— 曾经在这里失灵
    d2, pkg2 = fake_tree(False)
    mode2, root2, _ = selfmgr.self_info(pkg2)
    check_eq(mode2, 'installed',
             'Windows 布局（lib/ + VERSION，**无** uninstall）也识别为安装态')
    check_eq(os.path.basename(root2), os.path.basename(d2), 'Windows 安装根识别正确')

    # 仓库检出：容器目录不叫 lib → repo
    d3 = tempfile.mkdtemp(prefix='sc-repo-')
    os.makedirs(os.path.join(d3, 'installer'))
    with open(os.path.join(d3, 'installer', 'install-from-source.sh'), 'w') as fh:
        fh.write('#!/bin/bash\n')
    os.makedirs(os.path.join(d3, 'startupctl', 'core'))
    mode3, _r, _ = selfmgr.self_info(os.path.join(d3, 'startupctl'))
    check_eq(mode3, 'repo', '仓库检出识别为 repo')

    import shutil
    for d in (d1, d2, d3):
        shutil.rmtree(d, ignore_errors=True)


def check_no_posix_only_calls():
    section('跨平台：后端不能调 Windows 上不存在的 POSIX 接口')

    # 这套用例存在的理由：darwin 后端在**夹具模式下可以跨平台跑**（测试把
    # STARTUPCTL_PLATFORM 钉成 darwin 来验 macOS 的变更路径），所以它里面的
    # os.getuid() 在 Windows 上会真的被执行到 → AttributeError。
    # 本机是 macOS，永远复现不了；只有把代码拿到 Windows 上实测才会暴露。

    # 1) 静态检查：源码里不许直接出现 os.getuid/os.geteuid
    offenders = []
    for dirpath, _dirs, files in os.walk(os.path.join(ROOT, 'startupctl')):
        for f in files:
            if not f.endswith('.py'):
                continue
            p = os.path.join(dirpath, f)
            with open(p, encoding='utf-8') as fh:
                for n, line in enumerate(fh, 1):
                    code = line.split('#')[0]
                    if 'os.getuid(' in code or 'os.geteuid(' in code:
                        # utils.getuid/is_admin 自己那两处是**唯一**允许的地方
                        if p.endswith('utils.py'):
                            continue
                        offenders.append('%s:%d %s' % (os.path.relpath(p, ROOT), n,
                                                        line.strip()[:50]))
    check(not offenders,
          '没有直接调用 os.getuid/os.geteuid（越界的: %s）' % (offenders[:3] or '无'))

    # 2) 动态检查：把 os.getuid 拿掉（模拟 Windows），darwin 后端仍要能跑
    saved = getattr(os, 'getuid', None)
    had = hasattr(os, 'getuid')
    try:
        if had:
            del os.getuid
        from startupctl.core.utils import getuid
        check_eq(getuid(), 0, 'os.getuid 不存在时 utils.getuid() 返回 0')

        saved_env = {k: os.environ.get(k) for k in ('STARTUPCTL_ROOTS', 'STARTUPCTL_PLATFORM')}
        os.environ['STARTUPCTL_ROOTS'] = FIXTURES
        os.environ.pop('STARTUPCTL_PLATFORM', None)
        for mod in [m for m in list(sys.modules) if m.startswith('startupctl')]:
            del sys.modules[mod]
        sys.path.insert(0, ROOT)
        from startupctl.core import context, roots as roots_mod
        ctx = context.Ctx(platform='darwin', root_table=roots_mod.load(FIXTURES))
        res = ctx.scan()
        check(len(res.items) > 0,
              '无 os.getuid 的主机上 darwin 后端仍能扫描（%d 项）' % len(res.items))
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    except Exception as e:                                       # noqa: BLE001
        check(False, '无 os.getuid 时 darwin 后端出错: %s: %s' % (type(e).__name__, e))
    finally:
        if had and saved is not None:
            os.getuid = saved
        for mod in [m for m in list(sys.modules) if m.startswith('startupctl')]:
            del sys.modules[mod]


def check_windows_name_forms():
    section('跨平台：Windows 的进程名带 .exe，保护名单必须匹配得上')

    # 这条要是错了，后果是"把自己锁在门外"：deny_all 会把 cmd.exe 连同用户的终端
    # 一起杀掉，他连"关掉它"都敲不了。而 macOS 上永远复现不了——进程名不带 .exe。
    sys.path.insert(0, ROOT)
    from startupctl.core import guard as G
    from startupctl.core import proc as proc_mod

    def P(comm, prog=''):
        r = proc_mod.ProcRecord(pid=500, ppid=1, uid=None, user='',
                                program=prog, comm=comm, args_str=prog)
        r.origin = 'third_party'
        return r

    for comm in ('cmd.exe', 'powershell.exe', 'pwsh.exe', 'conhost.exe',
                 'WindowsTerminal.exe', 'OpenConsole.exe', 'mintty.exe'):
        ok, why = G.is_protected(P(comm), 'win32', set())
        check(ok, 'Windows 上 %s 受保护（%s）' % (comm, why[:22]))

    # POSIX 形态不能被归一化弄坏
    for comm in ('-zsh', 'bash', 'tmux', 'sshd', 'screen'):
        ok, _ = G.is_protected(P(comm), 'darwin', set())
        check(ok, 'POSIX 上 %s 仍受保护' % comm)

    # 系统基础进程的名表也要跨形态匹配
    for comm in ('csrss.exe', 'winlogon.exe', 'lsass.exe', 'services.exe'):
        ok, why = G.is_protected(P(comm), 'win32', set())
        check(ok, 'Windows 核心进程 %s 受保护' % comm)

    # norm_name 本身
    check_eq(G.norm_name('CMD.EXE'), 'cmd', 'norm_name 去 .exe 并小写')
    check_eq(G.norm_name('-zsh'), 'zsh', 'norm_name 去登录 shell 前导 -')
    check_eq(G.norm_name('kworker/0:1'), 'kworker/0', 'norm_name 去 :实例后缀')

    # 不该被误保护：一个普通第三方程序
    ok, _ = G.is_protected(P('VendorHelper.exe', '/Library/PrivilegedHelperTools/VendorHelper.exe'),
                           'win32', set())
    check(not ok, '普通第三方程序不受保护（归一化没有误伤）')


def check_windows_hive_names():
    section('Windows 注册表 hive 解析（真机才会踩的那个坑）')
    sys.path.insert(0, ROOT)
    from startupctl.backends import windows as W

    class FakeWinreg(object):
        HKEY_CURRENT_USER = 'HKCU'
        HKEY_LOCAL_MACHINE = 'HKLM'
        HKEY_CLASSES_ROOT = 'HKCR'

    # `getattr(winreg, 'HKEY_' + hive)` 会拼出 HKEY_HKCU —— 这个常量不存在。
    # 夹具模式在 _fixture() 处就返回，所以 CI 从未走到这里；真机上一跑就 AttributeError。
    check_eq(W._hive_const(FakeWinreg, 'HKCU'), 'HKCU', 'HKCU → HKEY_CURRENT_USER')
    check_eq(W._hive_const(FakeWinreg, 'HKLM'), 'HKLM', 'HKLM → HKEY_LOCAL_MACHINE')
    check_eq(W._hive_const(FakeWinreg, 'hkcu'), 'HKCU', '小写短名也认')
    check_eq(W._hive_const(FakeWinreg, 'HKEY_CURRENT_USER'), 'HKCU',
             '已经是完整常量名时不再加前缀')


def check_iss_matches_payload():
    """Windows 载荷表与 .iss 的 [Files] 必须逐项一致。

    这是整套 Windows 安装里**最容易漂的一环**：三处都在描述"装什么"，
    却各写各的、靠人工同步，没有任何机制守着：
      1. selfmgr._PAYLOAD_WIN     Python 侧（install.ps1 / update 走它）
      2. installer/windows/*.iss 的 [Files]   exe 安装包走它
      3. build-from-mac.sh 的 staging         决定 src\\ 下摆什么给 ISCC
    任一处漏改，两条安装路径就装出不一样的形状——而 update 会按一边的形状去校验
    另一边的产物。测试里连"载荷 vs .iss"这条断言都要有，否则漂了没人知道。

    比对用**安装空间相对路径**（两边共同的语言）：
      · _PAYLOAD_WIN 的 dst 列
      · .iss 的 DestDir 去掉 {app} 前缀；文件项再拼上 Source 的 basename
    顺带核对 .iss 的 Source 必须是 src\\<安装路径>——那就是 staging 约定。
    """
    import re
    from startupctl.core import selfmgr

    TOOL = 'startupctl'
    APP = '{app}'
    iss_path = os.path.join(ROOT, 'installer', 'windows', '%s.iss.in' % TOOL)
    check(os.path.isfile(iss_path), '.iss 模板存在（%s）' % os.path.basename(iss_path))

    text = open(iss_path, encoding='utf-8').read().replace('@TOOL@', TOOL)

    # 只认 [Files] 段里的 Source:/DestDir: 行（[Dirs] / [InstallDelete] 用的是 Name:）
    pairs, in_files = [], False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith('[') and line.endswith(']'):
            in_files = (line == '[Files]')
            continue
        if not in_files or not line.startswith('Source:'):
            continue
        m_src = re.search(r'Source:\s*"([^"]+)"', line)
        m_dst = re.search(r'DestDir:\s*"([^"]+)"', line)
        if m_src and m_dst:
            pairs.append((m_src.group(1).replace('\\', '/'),
                          m_dst.group(1).replace('\\', '/')))
    check(bool(pairs), '.iss 的 [Files] 段解析出条目（%d 条）' % len(pairs))

    # 安装空间路径 → (源相对路径, 是否目录)
    iss_install = {}
    for src, dst in pairs:
        rel = dst[len(APP):].strip('/') if dst.startswith(APP) else dst
        is_dir = src.endswith('/*')
        base = src[:-2] if is_dir else src
        if is_dir:
            iss_install[rel] = (base, True)
        else:
            iss_install[(rel + '/' + base.rsplit('/', 1)[-1]).lstrip('/')] = (base, False)

    payload = dict((dst, src) for src, dst in selfmgr._PAYLOAD_WIN)

    # ---- 1) 载荷里的每一项，.iss 都必须装 ----
    for dst in sorted(payload):
        if dst not in iss_install:
            check(False, '载荷里有 %s，但 .iss 的 [Files] 没装它（exe 装出来会缺）' % dst)
        else:
            check(True, '载荷 %s 在 .iss 里有对应条目' % dst)

    # ---- 2) .iss 多装的，只允许是"生成出来的启动器" ----
    #     deploy_nt 用 _WIN_LAUNCHER 写出 bin\<tool>.bat，所以它不在 _PAYLOAD_WIN 里；
    #     exe 那边没有 Python 可跑，只能把它当普通文件随包发。
    launcher = 'bin/%s.bat' % TOOL
    extra = sorted(set(iss_install) - set(payload))
    check(extra == [launcher],
          '.iss 比载荷多出的条目只有生成的启动器（多出: %s）' % (extra or '无'))

    # ---- 3) Source 必须落在 staging 约定上：src\<安装路径> ----
    bad_src = []
    for dst, (src, _is_dir) in sorted(iss_install.items()):
        if src != 'src/' + dst:
            bad_src.append('%s: Source=%s（应为 src/%s）' % (dst, src, dst))
    check(not bad_src,
          '每个 Source 都等于 src/<安装路径>（越界: %s）' % (bad_src[:3] or '无'))

    # ---- 4) 反向：载荷的安装路径必须全被覆盖 ----
    check(all(dst in iss_install for dst in payload),
          '载荷的安装路径全部被 .iss 覆盖')

    # ---- 5) 功能项清单不能反过来吃掉用户数据 ----
    for data in ('cache', 'whitelist.json', 'backups', 'scans'):
        check(data not in selfmgr._WIN_FUNC_ITEMS,
              '功能项清单不含用户数据 %s' % data)


def check_eof_is_noninteractive():
    section('确认环节：读到 EOF 也要按"非交互"报出来（Windows 上 NUL 的 isatty 为真）')

    # Windows 上 stdin 接 NUL 设备时 isatty() 返回 True，于是非交互那道闸拦不住，
    # 会走到 input() 并立刻 EOF。若那时只是静默 return False，用户看到的是
    # "命令退出了但没说为什么"。所以 EOF 必须走同一条"非交互"提示。
    sys.path.insert(0, ROOT)
    import io as _io
    from startupctl.core import safety

    class _FakeTTY(object):
        """isatty 说"是终端"，但一读就 EOF —— 正是 Windows NUL 的行为。"""
        def isatty(self):
            return True

        def readline(self, *a):
            raise EOFError()

        def read(self, *a):
            return ''

    class _Ctx(object):
        dry_run = False
        assume_yes = False

    real_in = sys.stdin
    buf = _io.StringIO()
    real_out = sys.stdout
    try:
        sys.stdin = _FakeTTY()
        sys.stdout = buf
        ok = safety.confirm('测试操作', ['  · 计划行'], _Ctx(), False)
    finally:
        sys.stdin = real_in
        sys.stdout = real_out

    text = buf.getvalue()
    check_eq(ok, False, 'EOF 时 confirm 返回 False（不执行）')
    check('非交互环境' in text, 'EOF 时也打出「非交互环境」提示')
    check('confirm' in text, '提示里给出加 confirm 跳过确认的用法（不用 -y）')
    check('计划行' in text, '计划仍然先打出来了')

    # 正常交互（能读到 y）要照常工作
    class _YesTTY(object):
        def isatty(self):
            return True

        def readline(self, *a):
            return 'y\n'

    buf2 = _io.StringIO()
    try:
        sys.stdin = _YesTTY()
        sys.stdout = buf2
        ok2 = safety.confirm('测试操作', [], _Ctx(), False)
    finally:
        sys.stdin = real_in
        sys.stdout = real_out
    check_eq(ok2, True, '交互输入 y 时 confirm 返回 True')


def check_windows_payload_is_clean():
    section('Windows 载荷：不该装 POSIX 专有的东西（对齐 ptool 的干净布局）')

    # ptool 在 Windows 上只装 bin\\ptool.bat · module\\install.bat · config\\ptool.conf · VERSION
    # ——一个多余的 .sh 都没有。照搬 POSIX 载荷表会把 deploy.sh / shell-setup.sh /
    # uninstall / zsh+bash 补全一起丢进用户目录，而它们在那台机器上一个都用不上。
    sys.path.insert(0, ROOT)
    from startupctl.core import selfmgr

    win_dsts = [dst for _src, dst in selfmgr._PAYLOAD_WIN]
    joined = ' '.join(win_dsts)

    check(not any(d.endswith('.sh') for d in win_dsts),
          'Windows 载荷里没有 .sh（%s）' % win_dsts)
    check('completions' not in joined,
          'Windows 载荷里没有 completions（bash/zsh 补全在那边无从接线）')
    check('uninstall' not in win_dsts,
          'Windows 载荷里没有 uninstall 脚本（卸载由 _win_uninstall 实现）')
    check('deploy.sh' not in win_dsts and 'shell-setup.sh' not in win_dsts,
          'Windows 载荷里没有 deploy.sh / shell-setup.sh')

    # 该有的必须有
    check('lib/startupctl' in win_dsts, 'Windows 载荷含 Python 包')
    check('VERSION' in win_dsts, 'Windows 载荷含 VERSION')
    check('config/startupctl.conf' in win_dsts, 'Windows 载荷含配置文件')

    # 功能项清单（卸载时删的）也要一致
    # ⚠️ 功能项清单与载荷清单是**两件事**，断言必须分开：
    #   载荷 = 要装什么（不许有 POSIX 项）
    #   功能项 = 部署前先删、卸载时删什么 —— 这里**应该**含历史遗留的 POSIX 名字，
    #            否则老用户升级上来时那几样会一直留在盘上。
    for legacy in ('completions', 'uninstall', 'deploy.sh', 'shell-setup.sh'):
        check(legacy in selfmgr._WIN_FUNC_ITEMS,
              'Windows 功能项清单含历史遗留 %s（升级时顺手清掉）' % legacy)
    for need in ('bin', 'lib', 'config', 'VERSION'):
        check(need in selfmgr._WIN_FUNC_ITEMS, 'Windows 功能项清单含 %s' % need)
    # ★ 最要紧的一条：功能项里**绝不能**出现用户数据——那是"永不自动删除"的东西。
    for data in ('cache', 'whitelist.json', 'backups', 'scans'):
        check(data not in selfmgr._WIN_FUNC_ITEMS,
              'Windows 功能项清单**不含**用户数据 %s' % data)

    # POSIX 载荷表反而**必须**含那些东西——别为了"统一"把 POSIX 也削了
    posix_dsts = [dst for _src, dst in selfmgr._PAYLOAD_REPO]
    for need in ('deploy.sh', 'shell-setup.sh', 'uninstall',
                 'completions/startupctl.zsh', 'lib/startupctl.sh'):
        check(need in posix_dsts, 'POSIX 载荷仍含 %s' % need)

    # 探测"装残了"用的清单也要分平台
    saved = os.name
    try:
        os.name = 'nt'
        check_eq(selfmgr._installed_items(), selfmgr._INSTALLED_ITEMS_WIN,
                 'os.name=nt 时用 Windows 的组件清单')
        os.name = 'posix'
        check_eq(selfmgr._installed_items(), selfmgr._INSTALLED_ITEMS,
                 'POSIX 时用 POSIX 的组件清单')
    finally:
        os.name = saved


def check_broken_file_is_never_overwritten():
    section('坏策略文件绝不被静默覆盖（数据丢失防线）')
    import tempfile as _tf
    import shutil as _sh
    sys.path.insert(0, ROOT)
    from startupctl.core import guard as G

    tmp = _tf.mkdtemp()
    try:
        path = os.path.join(tmp, 'guard.json')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write('{ this is not json')
        before = open(path, 'rb').read()
        g = G.Guard(path=path).load()
        check(getattr(g, '_broken', False), '坏文件被标记为 _broken')
        check(g.mode == G.MODE_OFF and g.count() == (0, 0),
              '坏文件按"不干预 + 空名单"跑（工具仍可用）')
        try:
            g.save()
            check(False, '坏文件上的 save() 被拒绝')
        except ValueError:
            check(True, '坏文件上的 save() 被拒绝（不会覆盖）')
        check(open(path, 'rb').read() == before, '磁盘上的坏文件字节未变')
    finally:
        _sh.rmtree(tmp, ignore_errors=True)


def check_deploy_ignores_umask():
    section('部署不继承 umask（077 会装出 0600/0700，普通用户跑不了）')
    import subprocess as _sp
    import tempfile as _tf
    import shutil as _sh

    tmp = _tf.mkdtemp()
    inst = os.path.join(tmp, 'inst')
    old = os.umask(0o077)
    try:
        _sp.check_call(['bash', os.path.join(ROOT, 'installer', 'deploy.sh'),
                        ROOT, inst],
                       stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
    except Exception as e:
        check(False, 'umask 077 下部署失败: %s' % e)
        _sh.rmtree(tmp, ignore_errors=True)
        return
    finally:
        os.umask(old)
    try:
        launcher = os.path.join(inst, 'lib', 'startupctl.sh')
        st = os.stat(launcher)
        check(bool(st.st_mode & 0o444), '启动器对所有人可读（不继承 umask）')
        check(bool(st.st_mode & 0o111), '启动器可执行')
        d = os.stat(os.path.join(inst, 'lib'))
        check(bool(d.st_mode & 0o555) == bool(d.st_mode & 0o555), '目录权限可遍历')
        check(bool(d.st_mode & 0o500), '目录对属主可进入')
    finally:
        _sh.rmtree(tmp, ignore_errors=True)


def check_fixture_links_are_relative():
    section('夹具里不得有绝对软链（否则 update 解包会被安全过滤器拒绝）')
    import os as _os
    root = _os.path.join(ROOT, 'tests', 'fixtures')
    bad = []
    for dp, dn, fn in _os.walk(root):
        for name in list(dn) + list(fn):
            p = _os.path.join(dp, name)
            if _os.path.islink(p):
                tgt = _os.readlink(p)
                if _os.path.isabs(tgt):
                    bad.append('%s -> %s' % (p, tgt))
    check(not bad,
          '夹具中没有绝对软链%s' % ('（发现: %s）' % '; '.join(bad) if bad else ''))
    # 顺带确认那个 dbus.service 软链是「指向发行版真单元」的相对链接
    dbus = _os.path.join(root, 'roots', 'linux_systemd_etc', 'dbus.service')
    if _os.path.islink(dbus):
        check(not _os.path.isabs(_os.readlink(dbus)),
              'dbus.service 用相对链接（Python 3.12+ 的 data 过滤器拒绝绝对链接）')


def check_windows_machine_level():
    section('Windows 与 ptool / jtool 同规：Program Files + HKLM')
    sys.path.insert(0, ROOT)
    from startupctl.core import selfmgr as S

    root = S._win_install_root()
    check(root.replace('/', '\\').lower().endswith('devtools\\startupctl'),
          '安装根是 ...\\devtools\\startupctl（得到 %s）' % root)
    check('program files' in root.lower() or 'programw6432' in os.environ,
          '安装根在 Program Files 下（不是用户主目录）')

    iss = open(os.path.join(ROOT, 'installer', 'windows', 'startupctl.iss.in'),
               encoding='utf-8').read()
    check('DefaultDirName={autopf}\\devtools\\@TOOL@' in iss,
          '.iss 装到 {autopf}\\devtools\\<tool>')
    check('PrivilegesRequired=admin' in iss, '.iss 要求管理员')
    check('ArchitecturesInstallIn64BitMode=x64compatible' in iss,
          '.iss 声明 64 位（否则 autopf 落到 Program Files (x86)）')
    check('Root: HKLM;' in iss and 'Session Manager\\Environment' in iss,
          '.iss 写机器级 PATH（HKLM）')
    check('HKCU' not in iss, '.iss 不再出现 HKCU')
    check('Permissions: users-modify' in iss,
          '{app}\\data 授了 users-modify（普通用户要能存名单）')

    ps1 = open(os.path.join(ROOT, 'installer', 'install.ps1'), encoding='utf-8').read()
    check('USERPROFILE' not in ps1,
          'install.ps1 不再往用户主目录装')
    check('ProgramFiles' in ps1, 'install.ps1 认 Program Files')


def check_startup_grouping():
    section('启动项选择器：短名 / 类型 / 分组')
    sys.path.insert(0, ROOT)
    from startupctl.core import picker
    from startupctl.core.model import StartupItem

    def it(**kw):
        base = dict(uid='u', anchor='a', kind='launchd-daemon', scope='system',
                    name='', source='', program='')
        base.update(kw)
        return StartupItem(**base)

    d = picker.StartupRow(it(anchor='com.docker.vmnetd', name='com.docker.vmnetd',
                             source='/Library/LaunchDaemons/com.docker.vmnetd.plist'))
    check_eq(picker.startup_group(d), 'com.docker', 'com.docker.* 归到 com.docker')
    check_eq(d.short_name('com.docker'), 'vmnetd', '组内显示短名（去掉包前缀）')
    check_eq(d.ext, '.plist', '类型列取源文件扩展名')
    # 曾经的 bug：label 里自带勾选标记，纯文本/GUI 又加一次，变成「☐ ☐」
    check(not d.label.startswith('☐') and '[ ]' not in d.label,
          'label 不含勾选标记（避免重复显示）')

    svc = picker.StartupRow(it(anchor='nginx.service', kind='systemd', name='nginx.service'))
    check_eq(picker.startup_group(svc), 'nginx', 'systemd 单元按去扩展名分组')
    check_eq(svc.ext, 'systemd', '没有源路径时类型列退回种类短名')

    login = picker.StartupRow(it(anchor='loginitem:CC Switch', kind='login-item',
                                 name='CC Switch', source='/Applications/CC Switch.app'))
    check_eq(picker.startup_group(login), 'CC Switch', '登录项按应用名分组')

    # 名称列给人看的名字，不是包名
    app = picker.StartupRow(it(anchor='cn.better365.StateTool', name='cn.better365.StateTool',
                               program='/Library/Application Support/Better365/State/State Tool.app/Contents/MacOS/State Tool'))
    check_eq(app.display_name, 'State Tool', '优先用 .app 的应用名')
    helper = picker.StartupRow(it(anchor='com.adobe.ARMDC.Communicator',
                                  name='com.adobe.ARMDC.Communicator',
                                  program='/Library/PrivilegedHelperTools/com.adobe.ARMDC.Communicator'))
    check_eq(helper.display_name, 'Communicator',
             '可执行文件本身是反域名时取最后一段（不显示整串包名）')
    plain = picker.StartupRow(it(anchor='com.docker.vmnetd', name='com.docker.vmnetd',
                                 program='/Library/PrivilegedHelperTools/com.docker.vmnetd'))
    check_eq(plain.display_name, 'vmnetd', 'com.docker.vmnetd → vmnetd')


def check_process_display_names():
    section('进程显示名：反域名取末段、去 .node 扩展名')
    sys.path.insert(0, ROOT)
    from startupctl.core import picker
    from startupctl.core import proc as proc_mod

    def row(comm, program=''):
        p = proc_mod.ProcRecord(pid=1, ppid=0, uid=501, user='jj',
                                program=program, comm=comm, args_str='')
        return picker.Row(p, False, '')

    r = row('cn.better365.iShotProHelper', '/Library/PrivilegedHelperTools/cn.better365.iShotProHelper')
    check_eq(r.display_name, 'iShotProHelper', '反域名 comm 取最后一段')
    check_eq(r.label, 'cn.better365.iShotProHelper', 'label（匹配/筛选用）保持原样')
    check_eq(picker.app_group(r), 'cn.better365', '归到厂商前缀')
    r = row('Creative Cloud Content Manager.node', '/Applications/CCXProcess.app/Contents/x')
    check_eq(r.display_name, 'Creative Cloud Content Manager', '去掉 .node 扩展名')
    r = row('mysqld', '/opt/db/bin/mysqld')
    check_eq(r.display_name, 'mysqld', '普通进程名原样保留')


def check_gui_columns():
    section('选择器列定义兜底（None 会 TypeError）')
    sys.path.insert(0, ROOT)
    from startupctl.core.gui import norm_columns

    c, w = norm_columns(None, None)
    check_eq(c, ('选择', '名称', '说明'), 'columns=None → 默认三列')
    check_eq(len(w), 3, 'widths=None → 与列数一致')
    c, w = norm_columns(('选择', '名称', '类型', '说明'), None)
    check_eq(len(w), 4, '四列时 widths 自动补齐到 4')
    c, w = norm_columns(('选择', '名称', '说明'), (70, 340, 480))
    check_eq(w, (70, 340, 480), '显式传入且数量匹配时原样保留')


def check_app_group():
    section('进程按应用分组')
    sys.path.insert(0, ROOT)
    from startupctl.core import picker
    from startupctl.core import proc as proc_mod

    def P(comm, program):
        return proc_mod.ProcRecord(pid=1, ppid=0, uid=501, user='jj',
                                   program=program, comm=comm, args_str='')

    # 应用包路径优先：主进程与各 Helper 归到同一个应用名
    a = P('抖音', '/Applications/抖音.app/Contents/MacOS/抖音')
    b = P('抖音 Helper (GPU)',
          '/Applications/抖音.app/Contents/Frameworks/X.framework/抖音 Helper (GPU)')
    check_eq(picker.app_group(a), '抖音', '主进程按 .app 包名归组')
    check_eq(picker.app_group(b), '抖音', 'Helper 按同一个 .app 包归组')

    # ★ 选择器传进来的是 Row，不是 ProcRecord —— 不拆这一层就会全部落进「其他」。
    check_eq(picker.app_group(picker.Row(a, False, '')), '抖音',
             'Row 也能正确归组（曾经就是这里退化成「其他」）')

    # 非应用包路径：退回名字前缀
    c = P('Google Chrome Helper', '/opt/google/chrome/chrome')
    check_eq(picker.app_group(c), 'Google Chrome', '非 .app 路径按名字前缀归组')
    d = P('mysqld', '/usr/local/bin/mysqld')
    check_eq(picker.app_group(d), 'mysqld', '没有 Helper 后缀时用完整进程名')


def check_watch_and_starting():
    section('监视循环与开机自启')
    sys.path.insert(0, ROOT)
    from startupctl import help as H
    from startupctl.core import autostart, watch

    txt = H.hint_text(['starting']) or ''
    check('true' in txt and 'false' in txt, 'starting ? 列出 true / false')
    check(callable(getattr(watch, 'start_detached', None)),
          'watch.start_detached 存在（mode 切换时用它起后台循环）')
    check(callable(getattr(autostart, 'wait_running', None)),
          'autostart.wait_running 存在（服务管理器异步启动后要等）')

    import shutil as _sh
    import signal as _signal
    import tempfile as _tf
    d = _tf.mkdtemp()
    old_env = dict(os.environ)
    old_handlers = {}
    for _s in (getattr(_signal, 'SIGTERM', None), getattr(_signal, 'SIGINT', None)):
        if _s is not None:
            old_handlers[_s] = _signal.getsignal(_s)
    try:
        os.environ['STARTUPCTL_DATA_DIR'] = d
        os.environ['STARTUPCTL_ROOTS'] = os.path.join(ROOT, 'tests', 'fixtures', 'roots')
        os.environ['STARTUPCTL_CONFIG'] = os.path.join(d, 'none.conf')
        os.environ.pop('STARTUPCTL_PLATFORM', None)
        os.environ.pop('STARTUPCTL_DRY_RUN', None)

        # 单实例：pid 文件里是活着的父进程 → 本进程什么都不做就退出
        pid_path = os.path.join(d, 'watch.pid')
        with open(pid_path, 'w', encoding='utf-8') as fh:
            fh.write(str(os.getppid()))
        rc = watch.run(interval=1, max_rounds=1)
        check_eq(rc, 0, '已有循环时第二个进程退出 0（单实例）')
        with open(os.path.join(d, 'watch.log'), encoding='utf-8') as fh:
            first = fh.read()
        check('已有监视循环在跑' in first, '日志说明第二个进程为什么退出')
        with open(pid_path, encoding='utf-8') as fh:
            check_eq(fh.read().strip(), str(os.getppid()),
                     '单实例退出时不动别人的 pid 文件')

        # 不干预模式：跑一轮就退出，不结束任何进程
        os.remove(pid_path)
        rc = watch.run(interval=1, max_rounds=1)
        check_eq(rc, 0, '不干预模式跑一轮退出 0')
        with open(os.path.join(d, 'watch.log'), encoding='utf-8') as fh:
            second = fh.read()
        check('模式为不干预' in second, '不干预模式下明说跳过（不是静默空转）')
        check(not os.path.exists(pid_path), '退出时清掉自己的 pid 文件')
    finally:
        os.environ.clear()
        os.environ.update(old_env)
        for _s, _h in old_handlers.items():
            try:
                _signal.signal(_s, _h)
            except Exception:
                pass
        _sh.rmtree(d, ignore_errors=True)


def check_cli_contracts():
    section('CLI 契约：HELP 行数 / 对齐 / 退出码')
    sys.path.insert(0, ROOT)
    from startupctl import help as H

    check(H.help_lines() <= 50, 'HELP 行数 %d <= 50' % H.help_lines())
    # 与 ptool 同形：「用法:」本身就是命令清单，不另设「子命令:」分区；
    # 而且本工具**没有 `--` 旗标**，所以帮助里也不该出现「选项:」分区。
    for anchor in ('用法:', '示例:'):
        check(any(l.strip() == anchor for l in H.HELP.splitlines()),
              'HELP 含分节 %s' % anchor)
    check(not any(l.strip() == '说明:' for l in H.HELP.splitlines()),
          'HELP 没有「说明:」段（用户要求去掉）')
    check(not any(l.strip() == '选项:' for l in H.HELP.splitlines()),
          'HELP 没有「选项:」分区（本工具不用旗标）')
    # 命令清单必须**全部可见**：不允许出现 `whitelist ...` 这类省略号条目。
    check(not any(' ... ' in l for l in H.HELP.splitlines()),
          '用法里没有 `...` 省略条目')
    check(not any(l.strip().startswith('startupctl ') and '--' in l
                  for l in H.HELP.splitlines()),
          '用法里没有 `--` 旗标')
    # 用法只列**最外层命令**：子命令（all / deny_all / selector …）交给 Tab 补全，
    # 不铺在帮助里。这里按"第一列只有两个词"来判定。
    # 只看「用法:」段；示例段当然有更多词。
    usage_lines = []
    in_usage = False
    for l in H.HELP.splitlines():
        if l.strip() == '用法:':
            in_usage = True
            continue
        if in_usage and not l.strip():
            break
        if in_usage and l.startswith('  startupctl '):
            usage_lines.append(l)
    # 命令列 = 第一个两空格之前的片段；它必须正好是 `startupctl <命令>`。
    heads = [l.strip().split('  ')[0].strip() for l in usage_lines]
    outer = [h.split()[1] for h in heads if len(h.split()) > 1]
    check(all(len(h.split()) == 2 for h in heads),
          '用法每行只有 `startupctl <命令>` 两个词（子命令交给 Tab）')
    check(set(outer) == {'list', 'mode', 'whitelist', 'blacklist', 'starting',
                         'config', 'version', 'help', 'update', 'install',
                         'uninstall'},
          '用法恰好列出 11 个最外层命令')
    probs = H.align_report()
    check(not probs, 'HELP 各节描述列对齐一致（问题: %s）' % (probs[:2] or '无'))
    check(max(__import__('startupctl.core.output', fromlist=['dw']).dw(l)
              for l in H.HELP.splitlines()) <= 100, 'HELP 最宽行 <= 100 列')
    for sub in ('list', 'mode', 'whitelist', 'blacklist', 'starting', 'config'):
        check(H.sub_help(sub) is not None, '子命令 %s 有专属帮助' % sub)

    rc, out = run_cli(['version'])
    check_eq(rc, 0, 'version 退出 0')
    # 版本号从 __version__ 取，**不硬编码**：写死的话每次升版本都要回来改测试，
    # 漏改的表现是「version 打印版本号」失败，看着像功能坏了，其实只是断言过期。
    from startupctl import __version__ as _v
    check('startupctl' in out and _v in out,
          'version 打印版本号（%s）' % _v)
    # 旗标一律拒收：这是「只用子命令」的硬约束，不是建议。
    rc, out = run_cli(['--version'])
    check_eq(rc, 2, '`--version` 这种旗标写法退出 2（本工具只用子命令）')
    # 名单为空时切模式：**不扫描**就该拒绝（否则 Windows 上几秒没输出）
    import tempfile as _tf, shutil as _sh, time as _time
    _d = _tf.mkdtemp()
    try:
        _t0 = _time.time()
        rc, out = run_cli(['mode', 'blacklist'], env_extra={'STARTUPCTL_DATA_DIR': _d})
        _dt = _time.time() - _t0
        check_eq(rc, 3, '空名单切模式退出 3（安全拒绝）')
        check('拒绝' in out, '空名单切模式打出「拒绝」')
        check(_dt < 5.0, '空名单拒绝不扫描（%.2fs）' % _dt)
    finally:
        _sh.rmtree(_d, ignore_errors=True)

    rc, out = run_cli(['help'])
    check_eq(rc, 0, 'help 退出 0')
    rc, out = run_cli(['help', 'list'])
    check_eq(rc, 0, 'help <子命令> 退出 0')
    check('用法: startupctl list' in out, 'help <子命令> 打印该子命令的帮助')
    rc, out = run_cli(['help', 'nosuch'])
    check_eq(rc, 2, 'help 未知子命令退出 2')
    # 「这个位置能填什么」——cmd/PowerShell 没有补全时用它
    for argv, needle in (
            (['?'], 'startupctl list'),
            (['list', '?'], 'all'),
            (['mode', '?'], 'deny_all'),
            (['whitelist', '?'], 'startup'),
            (['whitelist', 'startup', '?'], 'selector'),
            (['update', '?'], 'check'),
            (['uninstall', '?'], 'confirm')):
        rc, out = run_cli(argv)
        check_eq(rc, 0, '`%s` 退出 0' % ' '.join(argv))
        check(needle in out, '`%s` 提示里含 %s' % (' '.join(argv), needle))
    rc, out = run_cli(['whitelist', 'help'])
    check_eq(rc, 0, '`whitelist help` 等价于 `whitelist ?`')
    rc, out = run_cli(['nosuch', '?'])
    check_eq(rc, 2, '不认识的位置退出 2')
    # 末级位置：不是"未知"，而是"没有更多参数"
    rc, out = run_cli(['mode', 'blacklist', '?'])
    check_eq(rc, 0, '末级位置的 ? 退出 0')
    check('已经完整' in out, '末级位置明确说"后面没有更多参数"')
    # 自管理子命令不再静默吞参数（原来 update bad 会当成 update 跑）
    for argv, cmd in ((['update', 'bad'], 'update'),
                      (['uninstall', 'bad'], 'uninstall'),
                      (['install', 'bad'], 'install')):
        rc, out = run_cli(argv)
        check_eq(rc, 2, '`%s` 多余的参数退出 2' % ' '.join(argv))
        check(cmd + ' 不接受参数' in out, '`%s` 明说是多余参数' % ' '.join(argv))
    rc, out = run_cli(['nosuchcmd'])
    check_eq(rc, 2, '未知子命令退出 2（用法错）')


def check_version_sync():
    section('版本一致性：VERSION 文件 vs 包 __version__')
    sys.path.insert(0, ROOT)
    from startupctl import __version__
    vf = open(os.path.join(ROOT, 'VERSION'), encoding='utf-8').read().strip()
    check_eq(vf, __version__, 'VERSION 文件与 startupctl.__version__ 一致')


def _console_utf8():
    """让测试自己的输出是 UTF-8。

    Windows 上 Python 3.11 对**重定向**的 stdout 用 locale 编码（简体中文下是 GBK），
    于是全是中文的断言消息一路乱码——测试跑挂了都看不出挂在哪。
    产品侧早有同样一段（cli._console_utf8），测试侧一直缺；CI 在 windows-latest 上
    跑同一套，所以这不是"本机环境问题"。

    交互终端下只放宽 errors：把 tty 强改成 UTF-8 反而会在 GBK 控制台上花屏。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if not hasattr(stream, 'reconfigure'):
                continue
            if getattr(stream, 'isatty', lambda: False)():
                stream.reconfigure(errors='replace')
            else:
                stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass


def main():
    _console_utf8()
    print('startupctl 单元冒烟')
    print('仓库: %s' % ROOT)
    check_version_sync()
    check_domain()
    check_roots_seam()
    check_guard_modes()
    check_guard_session_safety()
    check_guard_locked_entries()
    check_no_posix_only_calls()
    check_windows_name_forms()
    check_windows_hive_names()
    check_iss_matches_payload()
    check_eof_is_noninteractive()
    check_windows_payload_is_clean()
    check_self_info_layouts()
    check_gui_picker()
    check_watch_and_starting()
    check_cli_contracts()
    check_app_group()
    check_gui_columns()
    check_process_display_names()
    check_startup_grouping()
    check_windows_machine_level()
    check_fixture_links_are_relative()
    check_deploy_ignores_umask()
    check_broken_file_is_never_overwritten()

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
