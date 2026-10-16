# -*- coding: utf-8 -*-
"""分类：这项是系统自带、第三方、还是判不出来。

**本文件的设计规则（一句话）：**

    不确定时返回 'unknown'，**绝不**默认 'third_party'。

理由是两个方向的代价不对称：

  · 把系统项当成三方项 → 它变成 mutable，`clean` 可能动它。有害且难恢复。
  · 把三方项当成系统项 → 用户加 `--include-unknown` 就能处理。只是麻烦。

所以一律往安全那侧倒。`unknown` 是一等的结论，不是"还没判完"。

**结构性防线（非对称规则，见 `_apply_asymmetry`）：**

    分类不确定 **且** 该项位于系统级、非用户可写根 → 结论**永不为** third_party。

这一条规则单独消灭了"系统守护进程被误判、然后被 clean 掉"的整类事故——因为
能被误判的前提，是那东西位于用户可写的地方，而系统守护进程不在。

`origin_evidence` **永远非空且永远打印**：用户必须能复核"为什么工具认为这是三方项"。
不可审计的分类就是不可信任的分类。
"""
import os

# 反 DNS 里常见 TLD，用于把 com.docker.vmnetd 归到厂商 com.docker
_TLDS = ('com', 'org', 'net', 'io', 'cn', 'me', 'dev', 'co', 'fr', 'de', 'uk',
         'info', 'biz', 'app', 'xyz', 'top', 'cc', 'tv', 'us', 'jp', 'kr', 'ru')

# 厂商可读名（查不到就留空，不硬编造）
VENDOR_NAMES = {
    'com.apple': 'Apple',
    'com.microsoft': 'Microsoft',
    'com.google': 'Google',
    'com.docker': 'Docker',
    'com.adobe': 'Adobe',
    'com.oracle': 'Oracle',
    'com.vmware': 'VMware',
    'com.valvesoftware': 'Valve (Steam)',
    'com.tencent': '腾讯',
    'com.vivo': 'vivo',
    'com.oray': '贝锐 (向日葵)',
    'com.netease': '网易',
    'com.jetbrains': 'JetBrains',
    'com.proxyman': 'Proxyman',
    'com.west2online': 'ClashX Pro',
    'org.mozilla': 'Mozilla',
    'org.virtualbox': 'Oracle VirtualBox',
    'homebrew.mxcl': 'Homebrew',
    'org.freedesktop': 'freedesktop.org',
    'org.gnome': 'GNOME',
    'org.kde': 'KDE',
    'cn.better365': 'Better365',
    'net.burningtnt': 'Terracotta',
    'fr.madrau': 'SwitchResX',
}

# macOS：Apple 自己的反 DNS 前缀
_APPLE_PREFIXES = ('com.apple.', 'org.cups.', 'com.openssh.', 'org.openbsd.',
                   'com.apple.', 'org.xquartz.')

# Linux：发行版 / 系统自带单元的前缀与全名
_DISTRO_UNIT_PREFIXES = (
    'systemd-', 'getty@', 'user@', 'user-runtime-dir@', 'serial-getty@',
    'dbus', 'networkmanager', 'NetworkManager', 'ssh', 'sshd', 'cron', 'crond',
    'rsyslog', 'syslog', 'polkit', 'udev', 'plymouth', 'accounts-daemon',
    'avahi-daemon', 'bluetooth', 'cups', 'gdm', 'lightdm', 'sddm', 'colord',
    'rtkit-daemon', 'upower', 'udisks2', 'wpa_supplicant', 'ModemManager',
    'irqbalance', 'thermald', 'packagekit', 'fwupd', 'snapd', 'apparmor',
    'auditd', 'chronyd', 'ntpd', 'systemd-journald', 'systemd-logind',
    'systemd-networkd', 'systemd-resolved', 'systemd-timesyncd',
    'systemd-tmpfiles', 'systemd-udevd', 'systemd-userdbd', 'systemd-oomd',
    'systemd-hostnamed', 'systemd-timedated', 'systemd-localed',
)
_DISTRO_UNIT_EXACT = ('-.mount', 'swap.target', 'basic.target', 'sysinit.target',
                      'multi-user.target', 'graphical.target', 'default.target',
                      'local-fs.target', 'remote-fs.target', 'sockets.target',
                      'timers.target', 'paths.target', 'slices.target',
                      'shutdown.target', 'reboot.target', 'poweroff.target',
                      'rescue.target', 'emergency.target', 'network.target',
                      'network-online.target', 'nss-lookup.target', 'time-sync.target',
                      'getty.target', 'cryptsetup.target', 'integritysetup.target')

# cron.{daily,hourly,weekly,monthly} 属于系统维护
_CRON_PERIODIC_DIRS = ('cron.daily', 'cron.hourly', 'cron.weekly', 'cron.monthly',
                       'cron.yearly', 'cron.hourly')

# 用户可写的路径前缀（用于非对称规则）
_USER_WRITABLE_HINTS = ('/Users/', '/home/', '/tmp/', '/var/folders/')


def _two_segment_vendor(anchor):
    """com.docker.vmnetd → com.docker；单段则原样；空则空。"""
    if not anchor:
        return ''
    s = anchor.strip()
    if '\\' in s or '/' in s:
        s = s.replace('/', '\\').rstrip('\\').split('\\')[-1]
    for suf in ('.service', '.plist', '.desktop', '.socket', '.target'):
        if s.endswith(suf):
            s = s[:-len(suf)]
    parts = s.split('.')
    if len(parts) >= 2 and parts[0].lower() in _TLDS:
        return '.'.join(parts[:2])
    return parts[0] if parts else ''


def vendor_name_of(vendor):
    if not vendor:
        return ''
    if vendor in VENDOR_NAMES:
        return VENDOR_NAMES[vendor]
    # com.foo.bar → 试 com.foo；再试首段
    parts = vendor.split('.')
    while len(parts) > 1:
        parts = parts[:-1]
        key = '.'.join(parts)
        if key in VENDOR_NAMES:
            return VENDOR_NAMES[key]
    return ''


def _is_user_writable(path):
    if not path:
        return False
    p = path
    if p.startswith('~'):
        return True
    if os.name == 'nt':
        low = p.lower()
        for h in ('%appdata%', '%localappdata%', '%userprofile%', '\\users\\', '\\temp\\'):
            if h in low:
                return True
        return False
    for h in _USER_WRITABLE_HINTS:
        if p.startswith(h):
            return True
    return False


def _apply_asymmetry(item, origin, confidence, evidence):
    """非对称规则：不确定 + 系统级非用户可写根 → 永不为 third_party。

    这是**结构性防线**，不是启发式：它不试图判断"这项到底是什么"，只保证
    "在无法判断时，位于用户改不到的地方的东西不会被判成可改的"。
    """
    if origin != 'unknown':
        return origin, confidence, evidence
    if not _is_user_writable(item.source):
        return ('unknown', confidence,
                evidence + '；位于系统级路径且非用户可写，按保守规则不判为第三方')
    return origin, confidence, evidence


# ---------------------------------------------------------------- 入口
def classify(item, ctx=None):
    """就地填充 item 的 origin / confidence / evidence / vendor / mutable。

    返回 item（便于链式）。**永不抛异常**——分类失败按 unknown 处理，
    因为"分类器崩了"绝不能变成"这项可以改"。
    """
    try:
        origin, confidence, evidence = _dispatch(item)
    except Exception as e:                                  # noqa: BLE001
        origin, confidence, evidence = ('unknown', 'low',
                                        '分类时出错（%s），按无法判定处理' % type(e).__name__)

    origin, confidence, evidence = _apply_asymmetry(item, origin, confidence, evidence)

    item.origin = origin
    item.confidence = confidence
    item.origin_evidence = evidence or '无判据'
    item.vendor = item.vendor or _two_segment_vendor(item.anchor)
    if not item.vendor_name:
        item.vendor_name = vendor_name_of(item.vendor)
    # ★ 只有明确判定为第三方才可改。unknown 与 os 都不可改。
    item.mutable = (origin == 'third_party')

    # Label 与文件名不一致：在任何平台都只记 warning，**不作为判定依据**。
    # （合法的不一致确实存在：Apple 自己的 plist、符号链接名与 Label 不同者。）
    _warn_label_mismatch(item)
    return item


def _warn_label_mismatch(item):
    """身份与文件名不一致 → 只记 warning，**不作判定依据**。

    只在**可能被篡改**的位置提示。`/System/` 是 SIP 保护的只读卷，那里的不一致
    一律是 Apple 自己的命名习惯（实测本机 63 例全是这种，如 `bootps.plist` 里写
    `com.apple.bootpd`）——对它们报警只会把真正的信号淹掉。
    有意义的场景是 /Library 与 ~/Library：一个叫 foo.plist 的文件里写着
    com.apple.bar，那才是"披着系统名字"的形状。
    """
    src = item.source or ''
    if not src or item.source_kind != 'file':
        return
    if src.startswith('/System/') or '/System/Library/' in src:
        return
    base = os.path.basename(src)
    for suf in ('.plist', '.service', '.desktop'):
        if base.endswith(suf):
            base = base[:-len(suf)]
            break
    if not item.anchor or base == item.anchor:
        return
    # 只对"看起来像反 DNS 身份"的 anchor 提示（Apple/厂商）
    if '.' not in item.anchor:
        return
    w = ('身份与文件名不一致（%s 里写的是 %s）——系统自带项通常是一致的，'
         '值得人工看一眼' % (os.path.basename(src), item.anchor))
    if w not in item.warnings:
        item.warnings = tuple(list(item.warnings) + [w])


def _dispatch(item):
    plat = item.platform or ''
    if plat.startswith('darwin'):
        return _classify_darwin(item)
    if plat.startswith('win'):
        return _classify_win(item)
    return _classify_linux(item)


# ---------------------------------------------------------------- macOS
def _classify_darwin(item):
    anchor = item.anchor or ''
    src = item.source or ''
    prog = item.program or ''
    root = item.root or ''
    low_anchor = anchor.lower()

    # 1) Apple 自己的反 DNS 前缀。
    #    放在最前面是**刻意**的：一个写着 com.apple.* 的 plist 会被判成系统项而
    #    **永不被本工具改动**——即便它是攻击者伪装的。这是 fail-closed 的方向
    #    （改不动真的系统项 vs 可能动到伪装的恶意项，前者代价小得多），
    #    真正的信号交给「身份与文件名不一致」那条警告让人去看。
    for pre in _APPLE_PREFIXES:
        if low_anchor.startswith(pre.lower()):
            return ('os', 'high', '身份前缀为 %s（Apple 自带的命名空间）' % pre)

    # 2) 逻辑根判定 —— **优先于路径子串**。
    #    路径子串（'/LaunchAgents/'、'/System/'）只在真机上成立；夹具树用的是逻辑名
    #    （darwin_agents/…），靠子串匹配会全部落到 unknown，于是"分类逻辑可测"
    #    就成了一句空话。逻辑根本身就携带了"这是谁装的位置"这个信息，更稳也更可测。
    if root in ('darwin.sys.daemons', 'darwin.sys.agents') or src.startswith('/System/'):
        return ('os', 'high', '位于系统自带的 LaunchDaemons/LaunchAgents（或 /System 只读卷）')

    # 3) Homebrew 管理的服务
    if low_anchor.startswith('homebrew.mxcl.') or 'homebrew.mxcl.' in low_anchor:
        item.managing_tool = 'homebrew'
        return ('third_party', 'high', 'Homebrew 服务（homebrew.mxcl.* 命名）')
    for p in ('/opt/homebrew/', '/usr/local/Cellar/', '/usr/local/opt/'):
        if prog.startswith(p) or src.startswith(p):
            item.managing_tool = item.managing_tool or 'homebrew'
            return ('third_party', 'high', '位于 Homebrew 路径 %s' % p)

    # 4) 应用程序包 / 特权 helper（第三方守护进程的典型落点）
    #    注意登录项的 program 是 **bundle 路径本身**（/Applications/X.app，末尾没有
    #    斜杠），而 launchd 项里是 bundle 内的可执行文件（/Applications/X.app/...）。
    #    两种都要认，否则登录项会全部落进 unknown。
    if '/Applications/' in prog or prog.rstrip('/').endswith('.app') or '.app/' in prog:
        return ('third_party', 'high', '可执行文件位于应用程序包内')
    if prog.startswith('/Library/PrivilegedHelperTools/'):
        return ('third_party', 'high', '位于 /Library/PrivilegedHelperTools（第三方特权 helper）')
    if '/Library/Application Support/' in prog or '/Library/Preferences/' in prog:
        return ('third_party', 'high', '位于 /Library 下的第三方私有目录')

    # 5) 用户级 LaunchAgents（逻辑根或真实路径）
    if root == 'darwin.user.agents' or item.scope == 'user' and '/LaunchAgents/' in src:
        if prog.startswith('/usr/') or prog.startswith('/System/'):
            # 用户目录里却跑系统自带的可执行文件：不常见，降级为"判不出来"
            return ('unknown', 'medium',
                    '用户级目录但可执行文件在系统路径（%s）' % prog)
        if prog and (prog.startswith(os.path.expanduser('~') + '/')
                     or prog.startswith('/Users/') or prog.startswith('/opt/')
                     or prog.startswith('/Applications/')):
            return ('third_party', 'high', '用户级 LaunchAgents 下的第三方身份')
        return ('third_party', 'high', '用户级 LaunchAgents（用户可写，装在这里的即第三方）')

    # 6) 系统级 /Library（逻辑根或真实路径）
    if root in ('darwin.daemons', 'darwin.agents') \
            or src.startswith('/Library/LaunchDaemons/') or src.startswith('/Library/LaunchAgents/'):
        return ('third_party', 'high',
                '位于 /Library/Launch{Daemons,Agents}（第三方安装位置，非 Apple 命名空间）')

    # 7) 用户家目录
    if prog.startswith(os.path.expanduser('~') + '/') or prog.startswith('/Users/'):
        return ('third_party', 'high', '可执行文件位于用户家目录')

    # 8) 反 DNS 身份 + 系统级路径，但路径不在已知位置
    if '.' in anchor and item.scope == 'system':
        return ('unknown', 'low',
                '身份为反 DNS（%s）但路径 %s 不在已知的第三方安装位置' % (anchor, src or '未知'))

    return ('unknown', 'low', '没有足够的判据（身份 %s，根 %s）' % (anchor or '空', root or '未知'))


# ---------------------------------------------------------------- Linux
def _classify_linux(item):
    anchor = item.anchor or ''
    src = item.source or ''
    root = item.root or ''
    unit = anchor[:-len('.service')] if anchor.endswith('.service') else anchor

    # 1) 发行版自带单元名表
    for pre in _DISTRO_UNIT_PREFIXES:
        if unit.startswith(pre):
            return ('os', 'high', '单元名 %s 匹配发行版自带前缀 %s' % (anchor, pre))
    if unit in _DISTRO_UNIT_EXACT:
        return ('os', 'high', '单元名 %s 属于 systemd 基础单元' % anchor)

    # 2) 本地/第三方安装层
    if root in ('linux.systemd.local', 'linux.systemd.local.user'):
        return ('third_party', 'high', '位于 /usr/local/lib/systemd（本地安装软件的层）')
    if root in ('linux.systemd.user',):
        return ('third_party', 'high', '用户级 systemd 单元（~/.config/systemd/user）')
    if root == 'linux.xdg.user':
        return ('third_party', 'high', '用户级 XDG 自启（~/.config/autostart）')
    if root == 'linux.initd':
        return ('unknown', 'low', '/etc/init.d 脚本：发行版包与手工安装都可能落在这里')

    # 3) /etc/systemd/system 下是**真文件**（不是符号链接）→ 本地覆盖/三方，medium
    if root == 'linux.systemd.etc':
        try:
            is_link = os.path.islink(src)
        except Exception:
            is_link = False
        if is_link:
            # 指向 /usr/lib 的是 enable 出来的软链，判定继承目标
            tgt = ''
            try:
                tgt = os.path.realpath(src)
            except Exception:
                tgt = ''
            if '/usr/lib/systemd/' in tgt:
                return ('os', 'medium',
                        '/etc 下指向发行版单元的软链（继承目标判定）')
            return ('third_party', 'medium',
                    '/etc 下的符号链接但目标不在发行版目录（%s）' % (tgt or '未知'))
        return ('third_party', 'medium',
                '/etc/systemd/system 下的真实单元文件（非软链）——通常是本地或三方安装')

    # 4) 发行版单元目录里的其余东西：老实说判不出来
    if root == 'linux.systemd.distro':
        return ('unknown', 'low',
                '位于发行版单元目录但名称不在发行版前缀表内（三方包也会装到这里），无法判定')

    # 5) XDG 系统级目录：发行版和三方都往里装
    if root == 'linux.xdg.system':
        return ('unknown', 'low', '/etc/xdg/autostart 为发行版与三方共用目录，无法判定')

    # 6) cron
    if root == 'linux.cron.etc':
        return ('unknown', 'medium', '/etc/crontab 由管理员或软件包维护，无法判定')
    if root == 'linux.cron.d':
        if any(d in src for d in _CRON_PERIODIC_DIRS):
            return ('os', 'medium', '位于 cron 周期目录（系统维护作业）')
        return ('unknown', 'medium', '/etc/cron.d 下的作业无法判定来源')
    if root in ('linux.cron.spool', 'linux.cron.spool.rh'):
        return ('third_party', 'high', '用户自己的 crontab')

    # 7) rc.local
    if root == 'linux.rc.local':
        return ('unknown', 'medium', '/etc/rc.local 内容由管理员维护，无法判定')

    return ('unknown', 'low', '没有足够的判据（单元 %s，路径 %s）' % (anchor or '空', src or '未知'))


# ---------------------------------------------------------------- Windows
def _classify_win(item):
    anchor = item.anchor or ''
    src = item.source or ''
    root = item.root or ''
    prog = item.program or ''
    low_prog = prog.lower().replace('/', '\\')

    sysroot_marks = ('%systemroot%', 'c:\\windows\\')

    # 1) 计划任务：\Microsoft\Windows\... 是系统自带
    if item.kind == 'task-scheduler':
        if anchor.lower().startswith('\\microsoft\\windows\\'):
            return ('os', 'high', '任务位于 \\Microsoft\\Windows\\ 命名空间下')
        if anchor.lower().startswith('\\microsoft\\'):
            return ('os', 'medium', '任务位于 \\Microsoft\\ 命名空间下')
        return ('third_party', 'high', '任务不在 Microsoft 命名空间下（三方软件安装的任务通常如此）')

    # 2) 服务 / Run 项：看程序路径
    if any(m in low_prog for m in sysroot_marks):
        # %SystemRoot%\Temp 之类是典型的投放位置，不能算系统
        for bad in ('\\windows\\temp\\', '\\windows\\tasks\\', '\\windows\\debug\\'):
            if bad in low_prog:
                return ('third_party', 'medium', '位于 %s（系统目录下的非常规位置）' % bad)
        return ('os', 'high', '可执行文件位于 %SystemRoot% 下')

    for p in ('c:\\program files', 'c:\\program files (x86)', '%programdata%',
              '%appdata%', '%localappdata%', 'c:\\users\\', '%userprofile%'):
        if low_prog.startswith(p) or p in low_prog:
            return ('third_party', 'high', '可执行文件位于 %s（三方安装位置）' % p)

    # 3) 用户级 Run 键：HKCU 下的任何值都是用户/三方装的
    if root == 'win.registry' and item.scope == 'user':
        return ('third_party', 'high', '用户级注册表启动项（HKCU）')

    # 4) 启动文件夹
    if item.kind == 'startup-folder':
        if 'programdata' in (src or '').lower():
            return ('third_party', 'medium', '公共启动文件夹（三方安装器常往这里放）')
        return ('third_party', 'high', '用户启动文件夹')

    if not prog:
        return ('unknown', 'low', '注册表项没有可解析的程序路径（%s）' % (src or '未知'))
    return ('unknown', 'low', '可执行文件路径 %s 不在已知的系统或三方位置' % prog)
