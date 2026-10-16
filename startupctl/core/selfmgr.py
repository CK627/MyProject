# -*- coding: utf-8 -*-
"""自管理子命令：update（拉快照重装）/ install 指引 / uninstall，及运行方式探测。

设计说明（2026-10 调整为 devtools 安装形态，与 jtool / ptool 同规）：
  · 代码装成 devtools 副本（**默认系统级** /Library/devtools/startupctl，与 jtool / ptool 一致；
    STARTUPCTL_USER=1 走用户级 ~/.devtools/startupctl）；
    PATH 上只挂安装目录的 bin/，里面只有**一个无后缀的软链** startupctl。仓库 bin/ 是
    素材目录（startupctl.sh + startupctl.bat），整体进 PATH 会让 zsh 的命令名补全同时列出
    startupctl 与 startupctl.bat —— 命令名补全走 $commands 哈希，而它不检查可执行位。
  · update = 读远端 VERSION 比对 → 下载源码快照 → 交给快照里的 installer/deploy.sh 重装。
    部署只删功能项，**永不 rm -rf 安装根**：用户级安装下那里还住着数据目录
    （~/.devtools/startupctl/：白名单 · 备份 · 快照），
    硬契约是「永不自动删除，uninstall 也保留」。
  · 数据目录 <数据根>（用户级安装下 == 安装根）住着三样东西，语义各不相同：
      whitelist.json  白名单（安全产物，永不自动删除）
      backups/        备份（唯一的后悔药，永不自动删除）
      scans/          扫描快照（纯缓存，clear 只清这个）
  · 环境变量：STARTUPCTL_USER（1 = 装用户级而非系统级）、
    STARTUPCTL_MIRROR（镜像地址；none = 只走 GitHub）、
    STARTUPCTL_GITHUB（none = 完全不走 GitHub，只认镜像）、
    STARTUPCTL_GITHUB_TARBALL（覆盖 GitHub 快照地址）。
"""
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

from .. import __version__
from . import paths

MIRROR_DEFAULT = 'http://101.132.165.98/dist/startupctl'
GITHUB_TARBALL = 'https://github.com/CK627/MyProject/archive/refs/heads/StartupItemManagement.tar.gz'
GITHUB_BRANCH = 'StartupItemManagement'
GITHUB_REPO = 'CK627/MyProject'

_SKIP_NAMES = ('.DS_Store',)
_SKIP_DIRS = ('__pycache__',)

# 载荷映射：仓库/快照相对路径 → 安装空间相对路径。
# 两边的**键**必须一致，_verify_deploy 才能逐文件比对源与落盘结果。
_PAYLOAD_REPO = (
    ('startupctl', 'lib/startupctl'),              # Python 包（含 core/ 与 backends/）
    ('bin/startupctl.sh', 'lib/startupctl.sh'),    # 启动器：仓库里是素材，安装后住 lib/
    ('VERSION', 'VERSION'),
    ('config/startupctl.conf', 'config/startupctl.conf'),
    ('completions/startupctl.zsh', 'completions/startupctl.zsh'),
    ('completions/startupctl.bash', 'completions/startupctl.bash'),
    ('installer/uninstall.sh', 'uninstall'),
    ('installer/deploy.sh', 'deploy.sh'),
    ('installer/shell-setup.sh', 'shell-setup.sh'),
)
# clear 时**一律保留**的顶层项。
#
# ⚠️ 这里比母本（CtfSweep）更要紧：CtfSweep 的数据根只装扫描缓存，清了无所谓；
#    本项目的数据根住着两样**删了就有真实损失**的东西：
#      · whitelist.json —— 用户逐条确认过的允许清单，是安全产物
#      · backups/       —— 唯一的后悔药：remove 之所以敢做，就靠它
#    所以 clear **只清 scans/**（快照，纯缓存），并把这两项显式列进保留清单。
#    它们各自有专属的清除入口（whitelist remove / backup prune），绝不借道 clear。
_CLEAR_KEEP = (
    # 功能项：用户级安装下数据根 == 安装根，整目录清空等于把 startupctl 自己删掉
    'bin', 'lib', 'completions', 'config', 'VERSION',
    'uninstall', 'deploy.sh', 'shell-setup.sh', 'startupctl.conf',
    # 用户数据（有真实损失，只能由专属命令清）
    paths.WHITELIST_NAME, 'backups',
)

# 安装态应有的组件（键即安装空间相对路径），用于「版本号已最新但装残了」的探测
_INSTALLED_ITEMS = (
    'lib/startupctl', 'lib/startupctl.sh', 'VERSION',
    'config/startupctl.conf', 'completions/startupctl.zsh', 'completions/startupctl.bash',
    'uninstall', 'deploy.sh', 'shell-setup.sh',
)


def _mirror():
    return os.environ.get('STARTUPCTL_MIRROR', MIRROR_DEFAULT)


def _github_off():
    """STARTUPCTL_GITHUB=none 时完全不走 GitHub（离线可复现，也是镜像-only 的开关）。"""
    return os.environ.get('STARTUPCTL_GITHUB', '').strip().lower() == 'none'


def _github_tarball():
    return os.environ.get('STARTUPCTL_GITHUB_TARBALL') or GITHUB_TARBALL


def _system_root():
    """默认（系统级）安装根。

    ⚠️ **Windows 上没有系统级安装**：没有 sudo / rc 的概念，装法是纯用户级拷贝 +
    HKCU 里的 PATH。所以这里必须先判 Windows 并返回用户级路径——原来直接落到
    `/usr/local/devtools/startupctl`，于是 `print-install-dir` 在一台 Windows 机器上
    打印出一个根本不存在的 POSIX 路径，而 `install` 实际装到了 `%USERPROFILE%`。
    两者说的不是一回事，脚本据此判断就会错。
    """
    if sys.platform == 'win32' or os.name == 'nt':
        return _win_install_root()
    if sys.platform == 'darwin':
        return '/Library/devtools/startupctl'
    return '/usr/local/devtools/startupctl'


def self_info():
    """探测运行方式，返回 (mode, root, devtools)。

    mode:
      'installed' —— devtools 安装版；root 为安装目录（如 ~/.devtools/startupctl），
                     devtools 为其父目录（如 ~/.devtools）
      'repo'      —— 源码仓库；root 为仓库根
      'unknown'   —— 其他（如 pip 安装）
    """
    core_dir = os.path.dirname(os.path.abspath(__file__))   # .../startupctl/core
    pkg_dir = os.path.dirname(core_dir)                     # .../startupctl
    container = os.path.dirname(pkg_dir)                    # .../lib 或 仓库根
    if os.path.basename(container) == 'lib':
        root = os.path.normpath(os.path.join(container, os.pardir))
        if (os.path.isfile(os.path.join(root, 'VERSION'))
                and os.path.isfile(os.path.join(root, 'uninstall'))):
            return 'installed', root, os.path.dirname(root)
    if os.path.isfile(os.path.join(container, 'installer', 'install-from-source.sh')):
        return 'repo', container, None
    return 'unknown', container, None


def _read_version(root):
    try:
        with open(os.path.join(root, 'VERSION'), encoding='utf-8') as f:
            return f.read().strip()
    except OSError:
        return ''


def _ver_key(v):
    """版本号比较键：1.9.0 → (1, 9, 0)；非数字段当 0，避免脏版本号抛异常。"""
    out = []
    for part in re.split(r'[.\-+]', (v or '').strip()):
        digits = ''.join(c for c in part if c.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out) or (0,)


def _walk_files(base):
    out = []
    for root, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)
        for fn in sorted(files):
            if fn in _SKIP_NAMES or fn.endswith('.pyc'):
                continue
            out.append(os.path.join(root, fn))
    return out


def _payload_items(root, table):
    """按映射表收集载荷清单：键统一为「安装空间」里的相对路径。"""
    items = {}
    for src_rel, key in table:
        src = os.path.join(root, src_rel)
        if os.path.isdir(src):
            for fp in _walk_files(src):
                rel = os.path.relpath(fp, src).replace(os.sep, '/')
                items[key + '/' + rel] = fp
        elif os.path.isfile(src):
            items[key] = src
    # 兼容重命名前的启动器名（老快照里是 bin/startupctl）
    if 'lib/startupctl.sh' not in items:
        legacy = os.path.join(root, 'bin', 'startupctl')
        if os.path.isfile(legacy):
            items['lib/startupctl.sh'] = legacy
    return items


def _file_md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


def _missing_artifacts(root):
    """列出安装目录里缺失/退化的组件。

    ⚠️ bin/startupctl 是软链，_walk_files 只收普通文件，它**不参与**载荷清单 ——
    软链缺失或退化成旧布局只能在这里发现。
    """
    missing = []
    for key in _INSTALLED_ITEMS:
        if not os.path.exists(os.path.join(root, key)):
            missing.append(key)
    if os.name == 'nt':
        # Windows 没有软链，入口是 bin\startupctl.bat
        if not os.path.isfile(os.path.join(root, 'bin', 'startupctl.bat')):
            missing.append('bin\\startupctl.bat（启动器）')
        return missing
    entry = os.path.join(root, 'bin', 'startupctl')
    if not os.path.islink(entry) or os.path.exists(os.path.join(root, 'bin', 'startupctl.sh')):
        missing.append('bin/startupctl（软链）')
    return missing


def _verify_deploy(srcdir, root):
    """部署后逐文件比对源与落盘结果，返回不一致的键（软链不参与）。

    这是 R1（半安装残骸）的兜底：deploy.sh 已把 preflight 放在删除之前，
    这里再确认拷贝真的落全了。
    """
    bad = []
    for key, src in sorted(_payload_items(srcdir, _PAYLOAD_REPO).items()):
        dst = os.path.join(root, key)
        try:
            if not os.path.isfile(dst) or _file_md5(src) != _file_md5(dst):
                bad.append(key)
        except OSError:
            bad.append(key)
    return bad


def _download(url, out, connect_timeout, max_time):
    """下载 url 到 out。

    优先 curl：与安装脚本行为一致——只认环境变量代理（不会误用 macOS 系统代理），
    且自带 CA 证书（不受本机 Python 证书配置影响），能同时绕开两个真实环境坑。
    没有 curl 时回退 urllib（经 ProxyHandler 用「环境变量代理」，同样不碰系统代理）。
    """
    curl = shutil.which('curl')
    if curl:
        proc = subprocess.run(
            [curl, '-fsSL', '--connect-timeout', str(connect_timeout),
             '--max-time', str(max_time), '-o', out, url],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            msg = proc.stderr.decode('utf-8', 'replace').strip().splitlines()
            raise IOError(msg[-1] if msg else ('curl 退出码 %d' % proc.returncode))
    else:
        if url.startswith('file://'):
            req = url
        else:
            req = urllib.request.Request(
                url, headers={'User-Agent': 'startupctl-update/%s' % __version__})
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler(urllib.request.getproxies_environment()))
        with opener.open(req, timeout=max_time) as resp, open(out, 'wb') as f:
            shutil.copyfileobj(resp, f)
    if not os.path.getsize(out):
        raise IOError('下载内容为空')


def _fetch_remote_version(mirror, workdir):
    """读远端版本号，三级降级：镜像 → raw.githubusercontent → GitHub API。

    返回 (版本号 or None, [(地址, 失败原因)])。
    ⚠️ 超时必须短（连接 6s / 总计 15s）：这两处域名在国内不保证可达，
    「更新」卡在第一步读版本号上，用户看到的就是「命令挂了」。
    """
    tmp = os.path.join(workdir, 'VERSION.remote')
    urls = []
    if mirror and mirror != 'none':
        urls.append((mirror.rstrip('/') + '/VERSION', False))
    if not _github_off():
        urls.append(('https://raw.githubusercontent.com/%s/%s/VERSION'
                     % (GITHUB_REPO, GITHUB_BRANCH), False))
        urls.append(('https://api.github.com/repos/%s/contents/VERSION?ref=%s'
                     % (GITHUB_REPO, GITHUB_BRANCH), True))
    tried = []
    for url, is_api in urls:
        try:
            _download(url, tmp, 6, 15)
            with open(tmp, encoding='utf-8', errors='replace') as f:
                raw = f.read()
            if is_api:
                # contents API 回的是 JSON，版本号在 base64 的 content 字段里
                try:
                    raw = base64.b64decode(json.loads(raw)['content']).decode('utf-8', 'replace')
                except Exception:
                    pass
            ver = raw.strip()
            if ver:
                return ver, tried
            tried.append((url, '内容为空'))
        except Exception as ex:
            tried.append((url, str(ex)))
    return None, tried


def _fetch_snapshot(mirror, workdir):
    """下载并解压源码快照；成功返回快照根目录（顶层 MyProject-<分支>），失败返回 None。"""
    tgz = os.path.join(workdir, 'startupctl-src.tar.gz')
    urls = []
    if mirror and mirror != 'none':
        urls.append((mirror.rstrip('/') + '/startupctl-src.tar.gz', 6, 60))
    if not _github_off():
        urls.append((_github_tarball(), 10, 180))
    ok = False
    for url, ct, mt in urls:
        try:
            print('  下载: %s' % url)
            _download(url, tgz, ct, mt)
            ok = True
            break
        except Exception as ex:
            print('  失败: %s' % ex)
    if not ok:
        return None
    dest = os.path.join(workdir, 'src')
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(tgz, 'r:gz') as tf:
        try:
            tf.extractall(dest, filter='data')   # Python >= 3.11.4 支持 filter 参数
        except TypeError:
            tf.extractall(dest)
    for name in sorted(os.listdir(dest)):
        cand = os.path.join(dest, name)
        if os.path.isfile(os.path.join(cand, 'installer', 'install-from-source.sh')):
            return cand
    return None


def _run_root(argv, probe):
    """需要写系统目录时提权执行（对齐 jtool 的 run_root）。

    已是 root、或目标本身可写，就直接跑；否则才 sudo —— 用户级安装不该弹密码。
    """
    # 用 utils.getuid() 而不是 os.geteuid()：Windows 上没有后者，会 AttributeError。
    # 这条路径在 Windows 上走不到（那边用 deploy_nt），但一个会在别的平台上
    # 直接崩的写法不该留在代码里——它迟早会被走到。
    from .utils import getuid
    if getuid() == 0 or os.access(probe, os.W_OK):
        return subprocess.call(argv)
    sudo = shutil.which('sudo')
    if not sudo:
        raise RuntimeError('需要写权限但找不到 sudo；请手动运行: sudo %s' % ' '.join(argv))
    # 非交互环境下 sudo 只会抛 "a terminal is required"，先探一次再决定
    if not sys.stdin.isatty() and subprocess.call([sudo, '-n', 'true'],
                                                  stdout=subprocess.DEVNULL,
                                                  stderr=subprocess.DEVNULL) != 0:
        raise RuntimeError('需要管理员权限但当前没有终端可输入密码；'
                           '请手动运行: sudo %s' % ' '.join(argv))
    print('  需要管理员权限，可能提示输入密码。')
    return subprocess.call([sudo] + argv)


def _deploy(srcdir, root):
    """用 srcdir 里的部署脚本重装到 root（布局只在 deploy.sh 里实现一份）。"""
    script = os.path.join(srcdir, 'installer', 'deploy.sh')
    if not os.path.isfile(script):
        script = os.path.join(root, 'deploy.sh')      # 老快照：退回安装目录里的副本
    if not os.path.isfile(script):
        raise RuntimeError('找不到 deploy.sh（快照与安装目录里都没有）')
    return _run_root(['bash', script, srcdir, root], root)


# ============================================================================
# Windows（nt）：没有 bash、也没有 rc 文件，安装形态换成
#   安装根 = %USERPROFILE%\\.devtools\\startupctl（与数据目录同址，和 macOS/Linux
#            用户级安装一致），PATH 上挂 <根>\\bin\\startupctl.bat。
# PATH 走 HKCU\Environment（用户级，不需要管理员）——不用 setx：它会把超过 1024
# 字符的 PATH 截断，是老牌事故。
# ============================================================================
_WIN_FUNC_ITEMS = ('bin', 'lib', 'completions', 'config', 'VERSION',
                   'uninstall', 'deploy.sh', 'shell-setup.sh')

# ⚠️ 纯 ASCII：无 BOM 的 UTF-8 .bat 会被 cmd 按 ANSI 代码页（简中是 GBK）解析，
#    中文会被从中间劈开、cmd 转头去执行文本碎片（ptool 的 build-remote.bat 踩过）。
#    所有面向用户的文案都在 Python 侧，那里有 _console_utf8() 兜底。
_WIN_LAUNCHER = (
    '@echo off\r\n'
    'rem startupctl launcher (Windows): put <install>\\lib on PYTHONPATH, then run python\r\n'
    'setlocal\r\n'
    'set "ROOT=%~dp0.."\r\n'
    'set "PYTHONPATH=%ROOT%\\lib;%PYTHONPATH%"\r\n'
    'python -B -m startupctl %*\r\n'
)


def _win_install_root():
    return os.path.join(os.path.expanduser('~'), '.devtools', 'startupctl')


def win_path_join(cur, entry):
    """把 entry 并进 PATH 串（大小写不敏感去重；空串/分隔符残留都收拾干净）。"""
    parts = [p.strip() for p in (cur or '').split(';')]
    parts = [p for p in parts if p]
    want = entry.rstrip('\\')
    for p in parts:
        if p.rstrip('\\').lower() == want.lower():
            return ';'.join(parts), False
    parts.insert(0, want)
    return ';'.join(parts), True


def win_path_drop(cur, entry):
    """从 PATH 串里摘掉 entry（大小写不敏感），返回 (新串, 是否改动了)。"""
    parts = [p.strip() for p in (cur or '').split(';')]
    parts = [p for p in parts if p]
    want = entry.rstrip('\\').lower()
    keep = [p for p in parts if p.rstrip('\\').lower() != want]
    return ';'.join(keep), len(keep) != len(parts)


def _win_path_read():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as k:
            v, _t = winreg.QueryValueEx(k, 'Path')
            return v or ''
    except OSError:
        return ''


def _win_path_write(value):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0,
                        winreg.KEY_SET_VALUE) as k:
        # REG_EXPAND_SZ：PATH 里常有 %USERPROFILE% 这类变量，写成 REG_SZ 就不再展开
        winreg.SetValueEx(k, 'Path', 0, winreg.REG_EXPAND_SZ, value)


def _win_path_ensure(entry):
    """把 entry 加进用户 PATH，返回 True 表示这次真的改了。"""
    cur = _win_path_read()
    new, changed = win_path_join(cur, entry)
    if changed:
        _win_path_write(new)
    return changed


def _win_path_remove(entry):
    cur = _win_path_read()
    new, changed = win_path_drop(cur, entry)
    if changed:
        _win_path_write(new)
    return changed


def deploy_nt(srcdir, root):
    """Windows 部署：按 _PAYLOAD_REPO 拷功能文件 + 写 bin\\startupctl.bat（不用 bash）。

    只删功能项，数据（cache/ 等）永不动——与 deploy.sh 的契约逐条对齐。
    """
    os.makedirs(root, exist_ok=True)
    for rel in _WIN_FUNC_ITEMS:
        p = os.path.join(root, rel)
        if os.path.isdir(p) and not os.path.islink(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.exists(p) or os.path.islink(p):
            try:
                os.remove(p)
            except OSError:
                pass
    for src_rel, dst_rel in _PAYLOAD_REPO:
        src = os.path.join(srcdir, src_rel)
        dst = os.path.join(root, dst_rel)
        if not os.path.exists(src):
            raise RuntimeError('源码快照缺少 %s' % src_rel)
        parent = os.path.dirname(dst)
        if parent:
            os.makedirs(parent, exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dst,
                            ignore=shutil.ignore_patterns('__pycache__', *_SKIP_NAMES))
        else:
            shutil.copy2(src, dst)
    bindir = os.path.join(root, 'bin')
    os.makedirs(bindir, exist_ok=True)
    with open(os.path.join(bindir, 'startupctl.bat'), 'w', encoding='utf-8', newline='') as fh:
        fh.write(_WIN_LAUNCHER)
    return 0


def _shell_setup(action, root):
    """shell 接线：以**调用者**身份运行。

    这里刻意不走 sudo —— sudo 之后 HOME 会变成 root 的，rc 就写错地方了；
    shell-setup.sh 自己认 SUDO_USER 来决定写谁家的 rc。
    """
    if os.name == 'nt':
        return 0        # Windows 没有 rc 接线：PATH 走注册表，由 cmd_install / deploy_nt 管
    script = os.path.join(root, 'shell-setup.sh')
    if not os.path.isfile(script):
        return 0
    return subprocess.call(['bash', script, action, root])


def cmd_update(argv):
    """startupctl update [--check]：拉取最新源码快照并重装（白名单与备份保留）。"""
    check_only = False
    for a in argv:
        if a == '--check':
            check_only = True
        else:
            print('未知参数: %s（用法: startupctl update [--check]）' % a)
            return 2

    mode, root, _devtools = self_info()
    if mode == 'repo':
        print('当前在源码仓库（%s），不在此处安装副本。' % root)
        print('  更新源码: git pull')
        print('  装成 devtools 副本: bash installer/install.sh（系统级加 sudo）')
        return 0
    if mode != 'installed':
        print('无法识别当前布局（既不是源码仓库，也不是 devtools 安装）。')
        print('  手动安装: 见 README「安装」')
        return 1

    local_ver = _read_version(root)
    mirror = _mirror()
    print('startupctl 更新检查（本地 v%s）' % (local_ver or '?'))

    workdir = tempfile.mkdtemp(prefix='startupctl-update-')
    try:
        remote_ver, tried = _fetch_remote_version(mirror, workdir)
        if not remote_ver:
            print('无法获取远端版本号（网络不可达，或镜像尚未发布 VERSION）。')
            for url, why in tried:
                print('  %s → %s' % (url, why))
            print('  可换镜像: STARTUPCTL_MIRROR=<url> startupctl update')
            print('  只走 GitHub: STARTUPCTL_MIRROR=none startupctl update')
            print('  手动安装: 见 README「安装」')
            return 1

        missing = _missing_artifacts(root)
        if _ver_key(remote_ver) <= _ver_key(local_ver) and not missing:
            print('已是最新版本 (v%s)。' % (local_ver or remote_ver))
            if check_only:
                print('  --check：仅比对，未做任何改动。')
            return 0

        if check_only:
            print('  远端 v%s 可用。' % remote_ver)
            if missing:
                print('  另外检测到缺失组件: %s' % '、'.join(missing))
            print('  --check：仅比对，未做任何改动；运行  startupctl update  执行更新。')
            return 0

        if _ver_key(remote_ver) <= _ver_key(local_ver):
            print('版本已是最新 (v%s)，但检测到缺失组件: %s' % (local_ver, '、'.join(missing)))
            print('  重新部署以补齐。')
        else:
            print('  本地 v%s → 远端 v%s' % (local_ver or '?', remote_ver))

        snapshot = _fetch_snapshot(mirror, workdir)
        if not snapshot:
            print('无法下载源码快照（镜像与 GitHub 都不可用）。')
            print('  可换镜像: STARTUPCTL_MIRROR=<url> startupctl update')
            return 1

        # 防镜像半发布：版本号已更新、快照还是旧的，装了等于没装
        snap_ver = _read_version(snapshot)
        if snap_ver != remote_ver:
            print('快照版本 (v%s) 与远端版本号 (v%s) 不一致，可能镜像正在发布中；'
                  '本次不落盘，请稍后重试。' % (snap_ver or '?', remote_ver))
            return 1

        try:
            # Windows 没有 bash：走同一份载荷清单的 Python 版部署（deploy_nt）
            rc = deploy_nt(snapshot, root) if os.name == 'nt' else _deploy(snapshot, root)
        except RuntimeError as ex:
            print('部署失败: %s' % ex)
            return 1
        except Exception as ex:
            print('部署失败: %s' % ex)
            return 1
        if rc != 0:
            print('部署失败（退出码 %d）。' % rc)
            return 1

        bad = _verify_deploy(snapshot, root)
        if bad:
            print('警告: 部署后校验不一致（%d 个文件未落全）: %s' % (len(bad), '、'.join(bad[:5])))
            return 1

        _shell_setup('install', root)      # nt 上直接返回 0（PATH 在注册表，安装时已处理）

        if snap_ver == local_ver:
            print('已是最新版本 (v%s)，并补齐了缺失组件。' % snap_ver)
        else:
            print('更新完成: v%s → v%s' % (local_ver or '?', snap_ver))
        # 「要不要重开终端」由 shell-setup.sh 按 rc 是否真被改动自己报（就是上面那行，
        # 升级时通常是「shell 配置未变」）——这里不再复述：一句提示只留一处，别让同一次
        # 更新把同样的话说三遍。命令本体本来也不需要刷新（启动器每次重新执行）。
        print('  数据目录未受影响（白名单与备份都保留）。')
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _win_install(mode, src):
    """Windows 用户级安装：拷到 %USERPROFILE%\\.devtools\\startupctl 并把 bin 挂进用户 PATH。

    与 macOS/Linux 用户级的形态逐条对齐：安装根就是数据目录（cache/ 等住在同一层），
    所以只删/写功能项；PATH 走注册表（不需要管理员），不用 setx（会截断长 PATH）。
    """
    dest = _win_install_root()
    if mode == 'installed' and os.path.normcase(os.path.abspath(src)) == os.path.normcase(os.path.abspath(dest)):
        print('startupctl 已安装: %s（v%s）' % (dest, _read_version(dest) or '?'))
        print('  更新: startupctl update      卸载: startupctl uninstall')
        return 0
    if mode not in ('repo', 'installed'):
        print('无法识别当前布局，找不到要安装的源码（在源码目录里运行 install.bat）。')
        return 1
    print('startupctl 安装（Windows · 用户级）')
    print('  源码: %s' % src)
    print('  目标: %s' % dest)
    try:
        deploy_nt(src, dest)
    except Exception as ex:
        print('安装失败: %s' % ex)
        return 1
    changed = _win_path_ensure(os.path.join(dest, 'bin'))
    print('已安装: %s（v%s）' % (dest, _read_version(dest) or '?'))
    print('  PATH: %s' % ('已加入用户 PATH' if changed else '用户 PATH 里已有'))
    print('  数据目录: %s（白名单 · 备份 · 快照；卸载不删）' % paths.data_root())
    print('  重开一个终端后可直接敲 startupctl（当前终端的 PATH 还是旧的）。')
    return 0


def _win_uninstall(argv):
    """Windows 卸载：摘 PATH 项 + 删功能文件，**保留数据**（与 POSIX 契约一致）。"""
    assume_yes = False
    for a in argv:
        if a in ('-y', '--yes'):
            assume_yes = True
        else:
            print('未知参数: %s（用法: startupctl uninstall [-y]）' % a)
            return 2
    dest = _win_install_root()
    if not os.path.isdir(dest):
        print('未安装: %s（无需卸载）' % dest)
        return 0
    if not assume_yes:
        if not sys.stdin.isatty():
            print('检测到非交互环境，请加 -y 跳过确认: startupctl uninstall -y')
            return 1
        try:
            ans = input('确定要卸载 startupctl 吗？（白名单与备份会保留）(y/n): ')
        except EOFError:
            ans = ''
        if ans.strip().lower() not in ('y', 'yes'):
            print('已取消')
            return 0

    print('startupctl 卸载程序（Windows）')
    print('安装目录: %s' % dest)
    if _win_path_remove(os.path.join(dest, 'bin')):
        print('已从用户 PATH 摘除: %s' % os.path.join(dest, 'bin'))
    else:
        print('用户 PATH 里没有这一项（可能已摘除）')
    removed = []
    for rel in _WIN_FUNC_ITEMS:
        p = os.path.join(dest, rel)
        if os.path.isdir(p) and not os.path.islink(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.exists(p) or os.path.islink(p):
            try:
                os.remove(p)
            except OSError:
                continue
        if not os.path.exists(p):
            removed.append(rel)
    print('已删除功能项: %s' % '、'.join(removed))
    left = sorted(os.listdir(dest)) if os.path.isdir(dest) else []
    if left:
        print('保留: %s（白名单 · 备份 · 快照；clear 只清快照）' % '、'.join(left))
    else:
        print('安装目录已空: %s' % dest)
    print('清理完成。重开一个终端后 PATH 才彻底刷新。')
    return 0


def cmd_install(argv):
    """startupctl install：安装指引（真安装要 sudo 与交互，交给 installer/install.sh）。

    Windows 上是**真装**（没有 sudo 与 rc 的概念，纯用户级拷贝 + 注册表 PATH），
    见 _win_install()。
    """
    if argv:
        print('未知参数: %s（用法: startupctl install）' % argv[0])
        return 2
    mode, root, _devtools = self_info()
    if os.name == 'nt':
        return _win_install(mode, root)
    if mode == 'installed':
        print('startupctl 已安装: %s（v%s）' % (root, _read_version(root) or '?'))
        print('  更新: startupctl update      卸载: startupctl uninstall')
        return 0
    print('安装 startupctl 到 devtools 目录（与 jtool / ptool 同规）：')
    print('  一键（推荐）: source <(curl -fsSL '
          'https://raw.githubusercontent.com/CK627/MyProject/StartupItemManagement/installer/install.sh)')
    print('  国内镜像:     source <(curl -fsSL %s/install.sh)' % MIRROR_DEFAULT)
    if mode == 'repo':
        print('  本地源码:     bash %s' % os.path.join(root, 'installer', 'install.sh'))
    print('  默认系统级 → %s（脚本内提示管理员密码）' % _system_root())
    print('  只想装给当前用户（无需密码）: STARTUPCTL_USER=1 加在上面命令前 → ~/.devtools/startupctl')
    print('  装完 PATH 上只多一个 startupctl；代码在安装目录，更新用 startupctl update。')
    return 0


def cmd_print_install_dir(argv):
    """startupctl print-install-dir：只打印解析出的安装根，**不落盘、不联网、不提权**。

    冒烟测试靠它断言层级解析（默认系统级 / STARTUPCTL_USER=1 用户级 /
    STARTUPCTL_DEVROOT 自定义），而不必真的安装一次。与 installer/install-from-source.sh
    的 print-install-dir 同一口径，两处必须给出同一个答案。
    """
    if argv and argv[0] not in ('-h', '--help'):
        print('未知参数: %s（用法: startupctl print-install-dir）' % argv[0])
        return 2
    devroot = os.environ.get('STARTUPCTL_DEVROOT')
    if devroot:
        root = os.path.join(os.path.expanduser(devroot), 'startupctl')
    elif os.environ.get('STARTUPCTL_USER') == '1':
        root = os.path.join(os.path.expanduser('~'), '.devtools', 'startupctl')
    else:
        # Windows 上这一步会返回用户级路径（那边没有系统级安装）——见 _system_root。
        root = _system_root()
    print(root)
    return 0


def cmd_uninstall(argv):
    """startupctl uninstall [-y]：卸载安装副本并摘除 shell 接线（白名单与备份保留）。"""
    assume_yes = False
    for a in argv:
        if a in ('-y', '--yes'):
            assume_yes = True
        else:
            print('未知参数: %s（用法: startupctl uninstall [-y]）' % a)
            return 2
    if os.name == 'nt':
        return _win_uninstall(argv)

    mode, root, _devtools = self_info()
    if mode == 'installed':
        script = os.path.join(root, 'uninstall')
    elif mode == 'repo':
        script = os.path.join(root, 'installer', 'uninstall.sh')
    else:
        print('无法识别当前布局，找不到卸载脚本。')
        return 1
    if not os.path.isfile(script):
        print('卸载脚本不存在: %s' % script)
        return 1

    if not assume_yes:
        if not sys.stdin.isatty():
            print('检测到非交互环境，请加 -y 跳过确认: startupctl uninstall -y')
            return 1
        try:
            ans = input('确定要卸载 startupctl 吗？（白名单与备份会保留）(y/n): ')
        except EOFError:
            ans = ''
        if ans.strip().lower() not in ('y', 'yes'):
            print('已取消')
            return 0

    print('startupctl 卸载程序')
    print('')
    # 默认是系统级安装（目录属 root），落盘删除同样要过提权闸门
    try:
        return _run_root(['bash', script], root)
    except RuntimeError as ex:
        print('卸载失败: %s' % ex)
        return 1


def cmd_clear(argv):
    """startupctl clear [-y]：只清**扫描快照**（scans/）。

    ⚠️ 本项目刻意**不**照搬母本（CtfSweep）的 clear 语义。母本的数据根只装扫描缓存，
    整目录清空无所谓；本项目的数据根住着两样删了就有真实损失的东西：

        whitelist.json   用户逐条确认过的允许清单（安全产物）
        backups/         唯一的后悔药——remove 之所以敢做，就靠它

    所以这里把删除范围**硬编码为 `<数据根>/scans` 一个目录**，而不是"遍历数据根、
    跳过一张保留清单"。两者看着等价，但失效模式不同：保留清单漏写一项就会误删，
    而写死一个目录**不可能**删到别处。这类"删除范围"的代码，白名单不如白名单都不需要。

    快照本身是纯缓存（scan --save 的产物，随时可重建），清了没有损失。
    白名单与备份各有专属入口：startupctl whitelist remove / backup prune。
    """
    assume_yes = False
    for a in argv:
        if a in ('-y', '--yes'):
            assume_yes = True
        elif a.startswith('-'):
            print('未知参数: %s（用法: startupctl clear [-y]）' % a)
            return 2
        else:
            print('clear 不接受参数（白名单与备份请用 whitelist remove / backup prune）: %s' % a)
            return 2

    root = paths.data_root()
    scans = paths.scans_root()
    if not os.path.isdir(scans):
        print('没有扫描快照需要清理（%s 不存在）' % scans)
        return 0

    try:
        names = sorted(os.listdir(scans))
    except OSError as e:
        print('无法读取 %s: %s' % (scans, e))
        return 1
    if not names:
        print('没有扫描快照需要清理（%s 已是空的）' % scans)
        return 0

    targets = [os.path.join(scans, n) for n in names]
    total_files = total_size = 0
    for p in targets:
        f, b = _usage(p) if os.path.isdir(p) and not os.path.islink(p) else (1, _filesize(p))
        total_files += f
        total_size += b

    print('将清空扫描快照: %s（%d 个快照，共 %d 个文件，%.1f KB）'
          % (scans, len(targets), total_files, total_size / 1024.0))
    print('  **不动** 白名单（%s）与备份（%s）'
          % (paths.WHITELIST_NAME, paths.backups_root()))
    if not assume_yes:
        if not sys.stdin.isatty():
            print('检测到非交互环境，请加 -y 跳过确认: startupctl clear -y')
            return 1
        try:
            ans = input('确定要删除吗？(y/n): ')
        except EOFError:
            ans = ''
        if ans.strip().lower() not in ('y', 'yes'):
            print('已取消')
            return 0

    removed = 0
    for p in targets:
        try:
            if os.path.isdir(p) and not os.path.islink(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
            removed += 1
        except OSError as ex:
            print('删除失败: %s (%r)' % (p, ex))
    print('已清空扫描快照（删除 %d 项）。下次 scan --save 会重新写入。' % removed)
    return 0


def _filesize(path):
    """单个文件的字节数（取不到按 0 计）。"""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _usage(path):
    """目录内全部文件的 (个数, 总字节)；路径不存在返回 (0, 0)。

    与 cli._dir_usage 同义但各留一份：cli 已经 import 了 selfmgr，反向 import 会成环。
    """
    files = total = 0
    for dirpath, _dirs, names in os.walk(path):
        for n in names:
            try:
                total += os.path.getsize(os.path.join(dirpath, n))
                files += 1
            except OSError:
                pass
    return files, total
