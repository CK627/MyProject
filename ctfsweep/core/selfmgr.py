# -*- coding: utf-8 -*-
"""自管理子命令：update（拉快照重装）/ install 指引 / uninstall，及运行方式探测。

设计说明（2026-10 调整为 devtools 安装形态，与 jtool / ptool 同规）：
  · 代码装成 devtools 副本（**默认系统级** /Library/devtools/ctfsweep，与 jtool / ptool 一致；
    CTFSWEEP_USER=1 走用户级 ~/.devtools/ctfsweep）；
    PATH 上只挂安装目录的 bin/，里面只有**一个无后缀的软链** ctfsweep。仓库 bin/ 是
    素材目录（ctfsweep.sh + ctfsweep.bat），整体进 PATH 会让 zsh 的命令名补全同时列出
    ctfsweep 与 ctfsweep.bat —— 命令名补全走 $commands 哈希，而它不检查可执行位。
  · update = 读远端 VERSION 比对 → 下载源码快照 → 交给快照里的 installer/deploy.sh 重装。
    部署只删功能项，**永不 rm -rf 安装根**：用户级安装下那里还住着数据目录
    （~/.devtools/ctfsweep/：扫描结果缓存 cache/ 与各题图片缓存），
    硬契约是「永不自动删除，uninstall 也保留」。
  · models 随安装部署到 <安装根>/lib/models —— judge.project_dir() 在安装态解析为
    <安装根>/lib，不装的话 --judge 会**静默**退化成「未训练」。
  · 环境变量：CTFSWEEP_USER（1 = 装用户级而非系统级）、
    CTFSWEEP_MIRROR（镜像地址；none = 只走 GitHub）、
    CTFSWEEP_GITHUB（none = 完全不走 GitHub，只认镜像）、
    CTFSWEEP_GITHUB_TARBALL（覆盖 GitHub 快照地址）。
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

MIRROR_DEFAULT = 'http://101.132.165.98/dist/ctfsweep'
GITHUB_TARBALL = 'https://github.com/CK627/MyProject/archive/refs/heads/CtfSweep.tar.gz'
GITHUB_BRANCH = 'CtfSweep'
GITHUB_REPO = 'CK627/MyProject'

_SKIP_NAMES = ('.DS_Store',)
_SKIP_DIRS = ('__pycache__',)

# 载荷映射：仓库/快照相对路径 → 安装空间相对路径。
# 两边的**键**必须一致，_verify_deploy 才能逐文件比对源与落盘结果。
_PAYLOAD_REPO = (
    ('ctfsweep', 'lib/ctfsweep'),                  # Python 包
    ('models', 'lib/models'),                      # 判断核模型（不装 → --judge 静默退化）
    ('bin/ctfsweep.sh', 'lib/ctfsweep.sh'),        # 启动器：仓库里是素材，安装后住 lib/
    ('VERSION', 'VERSION'),
    ('config/ctfsweep.conf', 'config/ctfsweep.conf'),
    ('completions/ctfsweep.zsh', 'completions/ctfsweep.zsh'),
    ('completions/ctfsweep.bash', 'completions/ctfsweep.bash'),
    ('installer/uninstall.sh', 'uninstall'),
    ('installer/deploy.sh', 'deploy.sh'),
    ('installer/shell-setup.sh', 'shell-setup.sh'),
)
# 安装态应有的组件（键即安装空间相对路径），用于「版本号已最新但装残了」的探测
_INSTALLED_ITEMS = (
    'lib/ctfsweep', 'lib/models', 'lib/ctfsweep.sh', 'VERSION',
    'config/ctfsweep.conf', 'completions/ctfsweep.zsh', 'completions/ctfsweep.bash',
    'uninstall', 'deploy.sh', 'shell-setup.sh',
)


def _mirror():
    return os.environ.get('CTFSWEEP_MIRROR', MIRROR_DEFAULT)


def _github_off():
    """CTFSWEEP_GITHUB=none 时完全不走 GitHub（离线可复现，也是镜像-only 的开关）。"""
    return os.environ.get('CTFSWEEP_GITHUB', '').strip().lower() == 'none'


def _github_tarball():
    return os.environ.get('CTFSWEEP_GITHUB_TARBALL') or GITHUB_TARBALL


def _system_root():
    if sys.platform == 'darwin':
        return '/Library/devtools/ctfsweep'
    return '/usr/local/devtools/ctfsweep'


def self_info():
    """探测运行方式，返回 (mode, root, devtools)。

    mode:
      'installed' —— devtools 安装版；root 为安装目录（如 ~/.devtools/ctfsweep），
                     devtools 为其父目录（如 ~/.devtools）
      'repo'      —— 源码仓库；root 为仓库根
      'unknown'   —— 其他（如 pip 安装）
    """
    core_dir = os.path.dirname(os.path.abspath(__file__))   # .../ctfsweep/core
    pkg_dir = os.path.dirname(core_dir)                     # .../ctfsweep
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
    # 兼容重命名前的启动器名（老快照里是 bin/ctfsweep）
    if 'lib/ctfsweep.sh' not in items:
        legacy = os.path.join(root, 'bin', 'ctfsweep')
        if os.path.isfile(legacy):
            items['lib/ctfsweep.sh'] = legacy
    return items


def _file_md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


def _missing_artifacts(root):
    """列出安装目录里缺失/退化的组件。

    ⚠️ bin/ctfsweep 是软链，_walk_files 只收普通文件，它**不参与**载荷清单 ——
    软链缺失或退化成旧布局只能在这里发现。
    """
    missing = []
    for key in _INSTALLED_ITEMS:
        if not os.path.exists(os.path.join(root, key)):
            missing.append(key)
    entry = os.path.join(root, 'bin', 'ctfsweep')
    if not os.path.islink(entry) or os.path.exists(os.path.join(root, 'bin', 'ctfsweep.sh')):
        missing.append('bin/ctfsweep（软链）')
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
                url, headers={'User-Agent': 'ctfsweep-update/%s' % __version__})
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
    tgz = os.path.join(workdir, 'ctfsweep-src.tar.gz')
    urls = []
    if mirror and mirror != 'none':
        urls.append((mirror.rstrip('/') + '/ctfsweep-src.tar.gz', 6, 60))
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
    if os.geteuid() == 0 or os.access(probe, os.W_OK):
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


def _shell_setup(action, root):
    """shell 接线：以**调用者**身份运行。

    这里刻意不走 sudo —— sudo 之后 HOME 会变成 root 的，rc 就写错地方了；
    shell-setup.sh 自己认 SUDO_USER 来决定写谁家的 rc。
    """
    script = os.path.join(root, 'shell-setup.sh')
    if not os.path.isfile(script):
        return 0
    return subprocess.call(['bash', script, action, root])


def cmd_update(argv):
    """ctfsweep update [--check]：拉取最新源码快照并重装（扫描缓存保留）。"""
    check_only = False
    for a in argv:
        if a == '--check':
            check_only = True
        else:
            print('未知参数: %s（用法: ctfsweep update [--check]）' % a)
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
    print('ctfsweep 更新检查（本地 v%s）' % (local_ver or '?'))

    workdir = tempfile.mkdtemp(prefix='ctfsweep-update-')
    try:
        remote_ver, tried = _fetch_remote_version(mirror, workdir)
        if not remote_ver:
            print('无法获取远端版本号（网络不可达，或镜像尚未发布 VERSION）。')
            for url, why in tried:
                print('  %s → %s' % (url, why))
            print('  可换镜像: CTFSWEEP_MIRROR=<url> ctfsweep update')
            print('  只走 GitHub: CTFSWEEP_MIRROR=none ctfsweep update')
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
            print('  --check：仅比对，未做任何改动；运行  ctfsweep update  执行更新。')
            return 0

        if _ver_key(remote_ver) <= _ver_key(local_ver):
            print('版本已是最新 (v%s)，但检测到缺失组件: %s' % (local_ver, '、'.join(missing)))
            print('  重新部署以补齐。')
        else:
            print('  本地 v%s → 远端 v%s' % (local_ver or '?', remote_ver))

        snapshot = _fetch_snapshot(mirror, workdir)
        if not snapshot:
            print('无法下载源码快照（镜像与 GitHub 都不可用）。')
            print('  可换镜像: CTFSWEEP_MIRROR=<url> ctfsweep update')
            return 1

        # 防镜像半发布：版本号已更新、快照还是旧的，装了等于没装
        snap_ver = _read_version(snapshot)
        if snap_ver != remote_ver:
            print('快照版本 (v%s) 与远端版本号 (v%s) 不一致，可能镜像正在发布中；'
                  '本次不落盘，请稍后重试。' % (snap_ver or '?', remote_ver))
            return 1

        try:
            rc = _deploy(snapshot, root)
        except RuntimeError as ex:
            print('部署失败: %s' % ex)
            return 1
        if rc != 0:
            print('部署失败（退出码 %d）。' % rc)
            return 1

        bad = _verify_deploy(snapshot, root)
        if bad:
            print('警告: 部署后校验不一致（%d 个文件未落全）: %s' % (len(bad), '、'.join(bad[:5])))
            return 1

        _shell_setup('install', root)

        if snap_ver == local_ver:
            print('已是最新版本 (v%s)，并补齐了缺失组件。' % snap_ver)
        else:
            print('更新完成: v%s → v%s' % (local_ver or '?', snap_ver))
        print('  重开终端或 source 配置文件后生效；扫描缓存（数据目录）未受影响。')
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def cmd_install(argv):
    """ctfsweep install：安装指引（真安装要 sudo 与交互，交给 installer/install.sh）。"""
    if argv:
        print('未知参数: %s（用法: ctfsweep install）' % argv[0])
        return 2
    mode, root, _devtools = self_info()
    if mode == 'installed':
        print('ctfsweep 已安装: %s（v%s）' % (root, _read_version(root) or '?'))
        print('  更新: ctfsweep update      卸载: ctfsweep uninstall')
        return 0
    print('安装 ctfsweep 到 devtools 目录（与 jtool / ptool 同规）：')
    print('  一键（推荐）: source <(curl -fsSL '
          'https://raw.githubusercontent.com/CK627/MyProject/CtfSweep/installer/install.sh)')
    print('  国内镜像:     source <(curl -fsSL %s/install.sh)' % MIRROR_DEFAULT)
    if mode == 'repo':
        print('  本地源码:     bash %s' % os.path.join(root, 'installer', 'install.sh'))
    print('  默认系统级 → %s（脚本内提示管理员密码）' % _system_root())
    print('  只想装给当前用户（无需密码）: CTFSWEEP_USER=1 加在上面命令前 → ~/.devtools/ctfsweep')
    print('  装完 PATH 上只多一个 ctfsweep；代码在安装目录，更新用 ctfsweep update。')
    return 0


def cmd_uninstall(argv):
    """ctfsweep uninstall [-y]：卸载安装副本并摘除 shell 接线（扫描缓存保留）。"""
    assume_yes = False
    for a in argv:
        if a in ('-y', '--yes'):
            assume_yes = True
        else:
            print('未知参数: %s（用法: ctfsweep uninstall [-y]）' % a)
            return 2
    if os.name == 'nt':
        print('ctfsweep uninstall 目前仅支持 macOS / Linux。')
        return 1

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
            print('检测到非交互环境，请加 -y 跳过确认: ctfsweep uninstall -y')
            return 1
        try:
            ans = input('确定要卸载 ctfsweep 吗？（扫描缓存会保留）(y/n): ')
        except EOFError:
            ans = ''
        if ans.strip().lower() not in ('y', 'yes'):
            print('已取消')
            return 0

    print('ctfsweep 卸载程序')
    print('')
    # 默认是系统级安装（目录属 root），落盘删除同样要过提权闸门
    try:
        return _run_root(['bash', script], root)
    except RuntimeError as ex:
        print('卸载失败: %s' % ex)
        return 1
