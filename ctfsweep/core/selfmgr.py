# -*- coding: utf-8 -*-
"""自管理子命令：update / install / uninstall 的指引与清理，及运行方式探测（供 config 使用）。

设计说明（源码直跑模式，2026-10 调整）：
  · 本项目采用「源码直跑」：功能完整存在于项目目录，不安装外部副本；
    用户数据（数据集/模型/缓存）统一放 ~/.devtools/ctfsweep/；
  · update / install 已改为指引输出（更新 = git pull；不再下载或安装外部副本）；
  · uninstall 用于清理历史遗留的旧版安装残留（bin/lib/completions 等），
    用户数据目录（~/.devtools/ctfsweep/ 下的数据集/模型/缓存）始终保留；
  · self_info() 依旧探测运行布局（repo / installed / unknown），供 config 显示。
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

from .. import __version__

MIRROR_DEFAULT = 'http://101.132.165.98/dist/ctfsweep'
GITHUB_TARBALL = 'https://github.com/CK627/MyProject/archive/refs/heads/CtfSweep.tar.gz'

# 安装产物清单（不含的文件/目录不参与指纹；与 installer/install-from-source.sh 的部署一致）
_PAYLOAD_FILES = ('bin/ctfsweep', 'config/ctfsweep.conf',
                  'completions/ctfsweep.zsh', 'completions/ctfsweep.bash',
                  'VERSION')
_SKIP_NAMES = ('.DS_Store',)
_SKIP_DIRS = ('__pycache__',)


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


def _walk_files(base):
    out = []
    for root, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)
        for fn in sorted(files):
            if fn in _SKIP_NAMES or fn.endswith('.pyc'):
                continue
            out.append(os.path.join(root, fn))
    return out


def _payload_items(root, pkg_rel):
    """收集载荷清单：键统一为「安装空间」里的相对路径（lib/ctfsweep/… / bin/ctfsweep / …）。

    root + pkg_rel：快照为 (快照根, 'ctfsweep')；安装版为 (安装根, 'lib/ctfsweep')。
    """
    items = {}
    pkg = os.path.join(root, pkg_rel)
    if os.path.isdir(pkg):
        for fp in _walk_files(pkg):
            rel = os.path.relpath(fp, pkg).replace(os.sep, '/')
            items['lib/ctfsweep/' + rel] = fp
    for rel in _PAYLOAD_FILES:
        fp = os.path.join(root, rel)
        if os.path.isfile(fp):
            items[rel] = fp
    # 卸载脚本也纳入比对：快照里在 installer/uninstall.sh，安装版里是 <root>/uninstall
    for cand in (os.path.join(root, 'installer', 'uninstall.sh'),
                 os.path.join(root, 'uninstall')):
        if os.path.isfile(cand):
            items['uninstall'] = cand
            break
    return items


def _file_md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


def payload_digest(items):
    """对载荷清单算聚合指纹（键排序后逐项摘要）。任一文件增减/改动都会改变指纹。"""
    h = hashlib.md5()
    for key in sorted(items):
        h.update(key.encode('utf-8'))
        h.update(b'\0')
        h.update(_file_md5(items[key]).encode('ascii'))
        h.update(b'\n')
    return h.hexdigest()


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


def _fetch_snapshot(mirror, workdir):
    """下载并解压源码快照；成功返回快照根目录（顶层 MyProject-<分支>），失败返回 None。"""
    tgz = os.path.join(workdir, 'ctfsweep-src.tar.gz')
    urls = []
    if mirror and mirror != 'none':
        urls.append((mirror.rstrip('/') + '/ctfsweep-src.tar.gz', 6, 30))
    urls.append((GITHUB_TARBALL, 10, 180))
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


def cmd_update(argv):
    """ctfsweep update：更新指引（源码直跑模式下不再从网络更新外部副本）。"""
    for a in argv:
        if a != '--check':
            print('未知参数: %s（用法: ctfsweep update）' % a)
            return 2

    mode, root, _devtools = self_info()
    print('提示: 本项目采用「源码直跑」模式 —— 代码只存在于项目目录，不安装外部副本。')
    if mode == 'repo':
        print('  更新源码: 在项目目录执行  git pull')
        print('  项目目录: %s' % root)
    else:
        print('  检测到旧版 devtools 安装布局；建议运行  ctfsweep uninstall  清理旧副本'
              '（用户数据会保留）。')
    return 0


def cmd_install(argv):
    """ctfsweep install：已弃用 —— 本工具改为「源码直跑」，不再安装外部副本。"""
    if argv:
        print('未知参数: %s（用法: ctfsweep install）' % argv[0])
        return 2
    print('提示: install 已弃用 —— 本项目采用「源码直跑」模式，不做外部拓展。')
    print('  · 代码只存在于项目目录（功能完整），不在 ~/.devtools 等外部位置安装副本；')
    print('  · 用户数据（数据集/模型/缓存）统一放在 ~/.devtools/ctfsweep/；')
    print('  · 命令行使用: 把项目的 bin 目录加入 PATH（见项目 README「快速开始」）。')
    mode, root, _devtools = self_info()
    if mode != 'repo':
        print('  · 检测到旧版安装布局；可运行  ctfsweep uninstall  清理旧副本（数据保留）。')
    else:
        print('  · 当前已在源码仓库: %s' % root)
    return 0


def cmd_uninstall(argv):
    """ctfsweep uninstall [-y]：清理旧版安装残留（保留用户数据；-y 跳过确认）。"""
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
            ans = input('确定要卸载 ctfsweep 吗？(y/n): ')
        except EOFError:
            ans = ''
        if ans.strip().lower() not in ('y', 'yes'):
            print('已取消')
            return 0

    print('ctfsweep 卸载程序')
    print('')
    return subprocess.call(['bash', script])
