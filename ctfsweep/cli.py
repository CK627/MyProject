# -*- coding: utf-8 -*-
"""命令行入口：参数解析、配置文件加载、批量扫描与结果汇总"""
import os
import sys

from . import __version__
from .core.capture import PCAP_MAGICS, PCAPNG_MAGIC
from .core.decode import assemble_suggestion
from .core.extract import PWD_POOL, _pk, precollect_pwds
from .core import selfmgr
from .core.report import report
from .core.scanner import scan_capture, scan_rawfile

HELP = """ctfsweep — CTF 流量 / 日志 / 注册表 快速扫描器（零依赖，Python 3.8+）

用法:
  ctfsweep <文件或目录> [选项]           # 已安装（PATH 中）
  python3 -m ctfsweep <文件或目录> ...   # 免安装，项目目录内直接跑
  ./bin/ctfsweep <文件或目录> ...        # 仓库启动器（macOS / Linux）

管理子命令:
  ctfsweep update [--check]   检查并更新到最新版（镜像优先，回退 GitHub；--check 只检查）
  ctfsweep install            从源码仓库安装到 devtools
  ctfsweep uninstall [-y]     卸载（-y 跳过确认）
  ctfsweep config             显示配置与安装信息
  ctfsweep help               显示本帮助

支持输入: pcap / pcapng（抓包）、evtx（事件日志）、.reg / 任意文本

选项:
  -f, --file F      指定要扫描的文件（等同位置参数，两种写法都行）
  -F, --folder D    指定要扫描的文件夹（递归扫描其中全部文件，适合整个项目目录）
  -k, --keywords    额外关键词(逗号分隔)，默认仅 flag,ctf
  --min-score N     只显示置信度 >= N 的结果（默认 0.40，设 0 显示全部）
  --no-decode       关闭 hex / base64 自动解码
  --depth N         解码链最大深度（默认 3，即 hex/base64 可反复套娃）
  --limit N         每个文件最多输出条数（默认 50，按置信度排序后截取）
  --extract         从流量中提取文件（ZIP/PNG/JPG/GIF/PDF/GZ/RAR/7Z），
                    保存到 "<抓包名>_extracted/" 并自动解压/扫描其内容；
                    加密 zip 自动尝试：空口令→常用表→--pwd-file 字典→流量采集口令
  --extract-dir D   指定提取输出目录（默认与抓包同目录）
  --pwd-file F      附加口令字典文件（每行一个，用于加密压缩包）
  --config F        指定配置文件（默认读取 ~/.config/ctfsweep/ctfsweep.conf）
  --version         显示版本
  -h, --help        显示本帮助

置信度模型（每条结果带 [分数 级别]）:
  0.97 高   明文完整 flag（xxx{...} 直接可见）
  0.95 高   解码后得到完整 flag（hex/base64/DNS 子域名等）
  0.75 中   内容"加壳"候选（疑似 flag 本体、缺 flag{} 外壳）
  0.72 中   JWT 令牌（自动解码 header/payload，伪造身份类题）
  0.65 中   (flag|ctf)…{ 未闭合片段（典型的分段 flag 前半截）
  0.62 中   命令回显 / 环境变量密钥回显（webshell、取证题关键线索）
  0.60 中   裸花括号片段 {xxxx    0.55 中   裸闭合片段 xxxx}
  0.45 低   DNS 查询名（域名白名单一眼可辨）
  0.42 低   接口短文本响应（HTTP 事务配对结果）
  0.40 低   关键词上下文（普通字符串命中，需人工浏览）
"""


def _load_conf(path):
    """读取 KEY=value 配置文件（# / ; 注释，未知键忽略）"""
    conf = {}
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith(';') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                conf[k.strip().upper()] = v.strip()
    except Exception as ex:
        print('配置文件读取失败: %r' % ex)
    return conf


def _default_conf_path():
    """配置文件查找：环境变量 CTFSWEEP_CONF > ~/.config/ctfsweep/ctfsweep.conf"""
    env = os.environ.get('CTFSWEEP_CONF')
    if env:
        return env
    p = os.path.join(os.path.expanduser('~'), '.config', 'ctfsweep', 'ctfsweep.conf')
    return p if os.path.isfile(p) else None


def _cmd_config():
    """ctfsweep config：显示安装信息与生效配置。"""
    mode, root, _devtools = selfmgr.self_info()
    print('ctfsweep %s' % __version__)
    if mode == 'installed':
        tier = '系统级' if root.startswith(('/Library/devtools', '/usr/local/devtools')) else '用户级'
        print('运行模式: 已安装（%s，devtools 布局）' % tier)
    elif mode == 'repo':
        print('运行模式: 源码仓库（未安装）')
    else:
        print('运行模式: 未识别（可能不是 devtools 布局安装）')
    print('程序目录: %s' % root)
    if mode == 'installed':
        udir = os.path.join(os.path.expanduser('~'), '.devtools', 'ctfsweep')
        print('用户数据: %s（补全副本等）' % udir)

    env_conf = os.environ.get('CTFSWEEP_CONF')
    conv = os.path.join(os.path.expanduser('~'), '.config', 'ctfsweep', 'ctfsweep.conf')
    if env_conf:
        print('配置文件: %s（来自 CTFSWEEP_CONF）' % env_conf)
        conf_path = env_conf
    elif os.path.isfile(conv):
        print('配置文件: %s' % conv)
        conf_path = conv
    else:
        print('配置文件: %s（不存在，使用内置默认值）' % conv)
        conf_path = None
    conf = _load_conf(conf_path) if conf_path else {}

    kws = ['flag', 'ctf'] + [k.strip() for k in conf.get('KEYWORDS', '').split(',') if k.strip()]
    print('生效配置:')
    print('  KEYWORDS  = %s' % ','.join(kws))

    def _show(key, default):
        v = conf.get(key, '').strip()
        print('  %-9s = %s' % (key, v if v else default + '（默认）'))

    _show('MIN_SCORE', '0.40')
    _show('DEPTH', '3')
    _show('LIMIT', '50')
    _show('NO_DECODE', 'false')
    mirror = os.environ.get('CTFSWEEP_MIRROR', selfmgr.MIRROR_DEFAULT)
    print('镜像源: %s（CTFSWEEP_MIRROR 可覆盖；none = 只走 GitHub）' % mirror)
    return 0


def main():
    args = sys.argv[1:]
    # 管理子命令（update / install / uninstall / config / help）
    if args and args[0] in ('update', 'install', 'uninstall', 'config', 'help'):
        sub, rest = args[0], args[1:]
        if sub == 'help':
            print(HELP)
            return 0
        if sub == 'config':
            return _cmd_config()
        if sub == 'update':
            return selfmgr.cmd_update(rest)
        if sub == 'install':
            return selfmgr.cmd_install(rest)
        return selfmgr.cmd_uninstall(rest)
    if not args:
        print(HELP)
        return 1

    # 预扫描 --config：配置文件先加载，命令行参数随后覆盖
    cfg_path = None
    for i, a in enumerate(args):
        if a == '--config' and i + 1 < len(args):
            cfg_path = args[i + 1]
    if cfg_path is None:
        cfg_path = _default_conf_path()
    conf = _load_conf(cfg_path) if cfg_path else {}

    def _conf_int(key, default):
        try:
            return int(conf[key])
        except Exception:
            return default

    def _conf_float(key, default):
        try:
            return float(conf[key])
        except Exception:
            return default

    path = None
    keywords = ['flag', 'ctf']
    for k in conf.get('KEYWORDS', '').split(','):
        k = k.strip()
        if k and k not in keywords:
            keywords.append(k)
    do_decode = conf.get('NO_DECODE', '').lower() not in ('1', 'true', 'yes', 'on')
    depth = _conf_int('DEPTH', 3)
    limit = _conf_int('LIMIT', 50)
    min_score = _conf_float('MIN_SCORE', 0.40)
    do_extract, extract_dir = False, None
    i = 0
    while i < len(args):
        a = args[i]
        if a in ('-f', '--file') and i + 1 < len(args):
            path = args[i + 1]
            i += 2
        elif a in ('-F', '--folder') and i + 1 < len(args):
            path = args[i + 1]
            i += 2
        elif a in ('-k', '--keywords') and i + 1 < len(args):
            keywords += [k.strip() for k in args[i + 1].split(',') if k.strip()]
            i += 2
        elif a == '--no-decode':
            do_decode = False
            i += 1
        elif a == '--extract':
            do_extract = True
            i += 1
        elif a == '--extract-dir' and i + 1 < len(args):
            extract_dir = args[i + 1]
            do_extract = True
            i += 2
        elif a == '--pwd-file' and i + 1 < len(args):
            try:
                for ln in open(args[i + 1], encoding='utf-8', errors='replace'):
                    _pk(ln.strip())
            except Exception as ex:
                print('口令字典读取失败: %r' % ex)
            i += 2
        elif a == '--config' and i + 1 < len(args):
            i += 2
        elif a == '--depth' and i + 1 < len(args):
            depth = int(args[i + 1])
            i += 2
        elif a == '--limit' and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif a == '--min-score' and i + 1 < len(args):
            min_score = float(args[i + 1])
            i += 2
        elif a in ('-h', '--help'):
            print(HELP)
            return 0
        elif a == '--version':
            print('ctfsweep %s' % __version__)
            return 0
        else:
            path = a
            i += 1
    if not path:
        print(HELP)
        return 1
    if not os.path.exists(path):
        print('路径不存在: %s' % path)
        return 2

    if os.path.isdir(path):
        targets = []
        for root, _dirs, files in os.walk(path):
            for f in sorted(files):
                if f != '.DS_Store':
                    targets.append(os.path.join(root, f))
    else:
        targets = [path]

    if do_extract:
        n = 0
        for fp in targets:
            try:
                data = open(fp, 'rb').read()
            except Exception:
                continue
            if data[:4] in PCAP_MAGICS or data[:4] == PCAPNG_MAGIC:
                precollect_pwds(data)
                n += 1
        if PWD_POOL:
            print('[口令池] 预扫 %d 个抓包，采集 %d 个候选口令（用于加密压缩包尝试）' % (n, len(PWD_POOL)))

    highs, n_high, n_mid, n_low = {}, 0, 0, 0
    global_frags = []
    for fp in targets:
        print('=' * 78)
        print('[文件] %s (%.1f KB)' % (os.path.basename(fp), os.path.getsize(fp) / 1024))
        try:
            data = open(fp, 'rb').read()
        except Exception as ex:
            print('  读取失败: %r' % ex)
            continue
        try:
            if data[:4] in PCAP_MAGICS or data[:4] == PCAPNG_MAGIC:
                ctx = None
                if do_extract:
                    stem = os.path.splitext(os.path.basename(fp))[0]
                    od = extract_dir or os.path.join(os.path.dirname(os.path.abspath(fp)), stem + '_extracted')
                    ctx = {'outdir': od, 'stem': stem}
                findings = scan_capture(data, keywords, do_decode, depth, ctx)
            else:
                findings = scan_rawfile(data, keywords, do_decode, depth, limit)
        except Exception as ex:
            print('  扫描出错: %r' % ex)
            continue
        for score, kind, tok, val, loc in findings:
            if score >= 0.85:
                n_high += 1
                v = val if isinstance(val, str) else val.decode('utf-8', 'replace')
                highs.setdefault(' '.join(v.split())[:160], os.path.basename(fp))
            elif score >= 0.55:
                n_mid += 1
            else:
                n_low += 1
        report(findings, limit, min_score)
        frag_vals = []
        for f in findings:
            if f[1].startswith('片段'):
                v = f[3] if isinstance(f[3], str) else f[3].decode('utf-8', 'replace')
                if v and v not in frag_vals:
                    frag_vals.append(v)
        for v in frag_vals:
            if v not in global_frags:
                global_frags.append(v)
        if len(frag_vals) >= 2:
            print('  [拼接建议] 本文件检出 %d 个片段：%s' % (len(frag_vals), ' | '.join(frag_vals[:12])))
            s = assemble_suggestion(frag_vals)
            if s:
                print('             启发式拼接尝试（人工确认）：%s' % s[:200])
    print('=' * 78)
    if len(set(global_frags)) >= 2:
        print('【全局片段拼接建议】（跨文件收集到 %d 个片段，供人工确认）' % len(global_frags))
        print('  片段池：%s' % ' | '.join(global_frags[:24]))
        s = assemble_suggestion(global_frags)
        if s:
            print('  启发式拼接尝试：%s' % s[:240])
    if highs:
        print('【高置信候选汇总】（可直接核验/提交）')
        for v, src in highs.items():
            print('  * %s   (来自 %s)' % (v, src))
    print('统计: 高置信 %d 条 / 中(需人工) %d 条 / 低(线索) %d 条' % (n_high, n_mid, n_low))
    return 0
