# -*- coding: utf-8 -*-
"""命令行入口：参数解析、配置文件加载、批量扫描与结果汇总。

集成路由调度（Router）与元判断核（MetaJudge）：
- 文件类型匹配 → 模块调度 → 结构化输出 → 综合评分
- 保留旧版扫描器作为基础能力（流量/原始文件），新增取证模块通过 Router 分派
"""
import hashlib
import io
import os
import sys
from contextlib import ExitStack, redirect_stdout

from . import __version__
from .core.capture import CaptureContext, PCAP_MAGICS, PCAPNG_MAGIC
from .core.decode import assemble_suggestion
from .core.extract import PWD_POOL, _pk, precollect_pwds
from .core import judge
from .core import paths
from .core import selfmgr
from .core.router import Router, Finding, ScanOptions
from .core.meta_judge import MetaJudge
from .core.report import report
from .core.utils import BAND_HIGH, BAND_MID, FLAG_RE, level_of

# 帮助文本是**薄索引**（形态对齐同仓库的 jtool / ptool）：
# 标题 / 用法 / 子命令 / 选项 / 示例 / 说明，六个部分各司其职，散文细节回流 README。
# 两条排版约定（改动时别破坏）：
#   · 每个选项、每个子命令、每条示例**严格一行**——多行续写正是"帮助太乱"的来源；
#   · 各段的描述列按**显示宽度**对齐（CJK 占两列，与 ptool 的 `用法` 段同一算法）。
# ⚠️ README 不随安装载荷发布（见 installer/deploy.sh 白名单），装机用户手上只有这一份，
#    所以末尾「说明」三条必须自足，不能写成"详见 README"。
# 改这里要同步：tests/test_smoke.py 的两条锚点断言 + 「≤50 行」上限反向断言。
HELP = """ctfsweep - CTF / 应急响应取证扫描器（零依赖，Python 3.8+）

用法:
  ctfsweep <文件或目录> [选项]          扫描（pcap · evtx · reg · 文本 · 内存镜像 …）
  ctfsweep <子命令> [参数]              管理子命令（见下）
  python3 -m ctfsweep <文件或目录> ...  未安装时在项目目录内直接跑
  ./bin/ctfsweep.sh <文件或目录> ...    仓库启动器（macOS / Linux）

子命令:
  ctfsweep update [--check]   拉取最新源码快照并重装（--check 只比对版本，不落盘）
  ctfsweep install            显示安装方式（装到 devtools 目录）
  ctfsweep uninstall [-y]     卸载安装副本并摘除 shell 接线（扫描缓存保留；-y 跳过确认）
  ctfsweep config             显示运行信息与生效配置（含扫描缓存占用）
  ctfsweep help               显示本帮助

选项:
  -f --file F       指定要扫描的文件（等同位置参数）
  -F --folder D     指定要扫描的文件夹（递归其中全部文件）
  -k --keywords L   追加关键词（逗号分隔，默认 flag,ctf）
  --min-score N     只显示置信度 >= N 的结果（默认 0.40，0 显示全部）
  --no-decode       关闭 hex / base64 自动解码
  --depth N         解码链最大深度（默认 3）
  --limit N         每个文件最多输出条数（默认 50，按置信度排序后截取）
  -q --brief        精简输出：控制台只打分档统计块（两种模式都写缓存）
  --extract         提取流量中的文件并扫其内容（加密 zip 自动尝试口令）
  --extract-dir D   提取输出目录（默认 "<抓包名>_extracted/"，与抓包同目录）
  --pwd-file F      附加口令字典文件（每行一个，用于加密压缩包）
  --judge           用判断核模型对候选打分（p=…，模型随版本发布）
  --config F        指定配置文件（默认 ~/.devtools/ctfsweep/ctfsweep.conf）
  --version         显示版本
  -h --help         显示本帮助

示例:
  ctfsweep capture.pcap                  扫描一个抓包
  ctfsweep ./logs/ -k flag1,flag2        扫整个目录并追加关键词
  ctfsweep capture.pcap --min-score 0.85 只看高置信（直接要答案）
  ctfsweep capture.pcap --extract        提取流量中的文件
  ctfsweep capture.pcap --judge          判断核打分排序
  ctfsweep update                        更新到最新版

说明:
  结果按置信度分档: >= 0.85 高（可直接核验）/ >= 0.55 中（需人工确认）/ 其余低
  每次扫描都写缓存: ~/.devtools/ctfsweep/cache/（只增不减，占用见 ctfsweep config）
  判断核为轻量 MLP，加 --judge 才跑；模型随版本发布，离线训练见仓库 lab/train.py
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
    """配置文件查找：环境变量 CTFSWEEP_CONF > ~/.devtools/ctfsweep/ctfsweep.conf"""
    env = os.environ.get('CTFSWEEP_CONF')
    if env:
        return env
    p = os.path.join(os.path.expanduser('~'), '.devtools', 'ctfsweep', 'ctfsweep.conf')
    return p if os.path.isfile(p) else None


def _dir_usage(path):
    """统计目录下的文件数与总字节数（不存在的目录返回 (0, 0)）。"""
    files = total = 0
    for dirpath, _dirs, names in os.walk(path):
        for n in names:
            try:
                total += os.path.getsize(os.path.join(dirpath, n))
                files += 1
            except OSError:
                pass
    return files, total


def _cmd_config():
    """ctfsweep config：显示运行信息与生效配置。"""
    mode, root, _devtools = selfmgr.self_info()
    print('ctfsweep %s' % __version__)
    if mode == 'repo':
        print('运行模式: 源码仓库（未安装；ctfsweep install 可装成 devtools 副本）')
    elif mode == 'installed':
        print('运行模式: devtools 安装（ctfsweep update 可更新，扫描缓存保留）')
    else:
        print('运行模式: 未识别')
    print('程序目录: %s' % root)
    print('模型: %s（项目内；%s）' % (judge.model_path(),
                                   '已就绪' if os.path.isfile(judge.model_path()) else '未训练'))

    # 扫描缓存只增不减（装/卸/更新都不碰用户数据），
    # 这里把占用与可删路径一并报出来，作为唯一的清理入口。
    croot = brief_cache_root()
    if os.path.isdir(croot):
        cnum, csize = _dir_usage(croot)
        print('扫描缓存: %s（%d 个文件，%.1f MB；每次扫描自动写入，确认不需要后可整体删除）'
              % (croot, cnum, csize / 1048576.0))
    else:
        print('扫描缓存: %s（尚未使用；每次扫描会自动写入）' % croot)

    env_conf = os.environ.get('CTFSWEEP_CONF')
    conv = os.path.join(os.path.expanduser('~'), '.devtools', 'ctfsweep', 'ctfsweep.conf')
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

    mp = judge.model_path()
    if os.path.isfile(mp):
        try:
            pred = judge.JudgePredictor.load(mp)
            print('判断核模型: %s（已就绪，%s）' % (mp, pred.describe()))
        except Exception as ex:
            print('判断核模型: %s（加载失败: %r）' % (mp, ex))
    else:
        print('判断核模型: %s（不存在；模型随版本发布，重装或离线训练后替换）' % mp)
    return 0


# ---------------------------------------------------------------- 扫描缓存（每次都写）
# 每个文件一份：<缓存根>/<文件名>-<路径哈希>/：
#   1.txt / 2.txt / 3.txt     高/中/低置信候选明细（分数 | 级别 | 类型 | 值 | 位置）
#   <文件名>_cache.txt        该文件的完整扫描输出（**两种模式内容相同**）
#
# **默认模式也写缓存**（用户实测反馈"跑完看不到任何结果文件"）：默认模式用 tee 把
# 报告同时送上屏与缓存；-q 只改变控制台是否上屏，缓存文件逐字节相同。
# 缓存根由 core/paths.py 单点定义（跟随 CTFSWEEP_DATA_DIR，测试隔离天然生效）。
_BRIEF_LEVELS = (('高', '1.txt'), ('中', '2.txt'), ('低', '3.txt'))
_BRIEF_TITLES = {'高': '高置信（可直接核验）',
                 '中': '中置信（需人工确认）',
                 '低': '低置信（线索参考）'}


class _TeeStream(object):
    """stdout 替身：把输出同时送往控制台与「当前文件」的缓存缓冲。

    - 缓冲**逐文件替换**（`bind`），所以 redirect 只在最外层进出一次——
      循环里的 `continue` 不会再让捕获挂住、把后续输出写进上一个缓冲区
      （旧实现逐文件 enter_context 的锐边）；
    - `passthrough=False`（-q）时只写缓冲，控制台看不到详细报告；
    - 两个模式捕获到的是**同一份文本**，所以缓存文件内容不因模式而异。
    """

    def __init__(self, primary, passthrough=True):
        self._primary = primary
        self._passthrough = passthrough
        self._buffer = None

    def bind(self, buffer):
        """换绑当前文件的缓存缓冲。"""
        self._buffer = buffer

    def write(self, s):
        if self._buffer is not None:
            self._buffer.write(s)
        if self._passthrough:
            self._primary.write(s)
        return len(s)

    def flush(self):
        try:
            self._primary.flush()
        except Exception:
            pass

    def __getattr__(self, name):
        # encoding / isatty / fileno 等一律委托给真实 stdout
        return getattr(self._primary, name)


def brief_cache_root():
    """扫描缓存根目录（<数据根>/cache；数据根由 core/paths.py 单点解析）。"""
    return paths.cache_root()


def brief_cache_dir(fp):
    """该文件的缓存子目录：`<缓存根>/<文件名>-<路径哈希6位>/`。

    目录名带**完整路径**的短哈希，而不是只用文件名：`a/capture.pcap` 与
    `b/capture.pcap`（以及 `capture.pcap` 与 `capture.pcapng`）各自成目录、
    不会互相覆盖；同一文件重复扫描仍写回自己那一份。
    """
    base = os.path.basename(fp)
    stem = os.path.splitext(base)[0] or base
    digest = hashlib.sha1(os.path.realpath(fp).encode('utf-8', 'replace')).hexdigest()[:6]
    return os.path.join(brief_cache_root(), '%s-%s' % (stem, digest))


def _brief_text(f):
    v = f.val if isinstance(f.val, str) else f.val.decode('utf-8', 'replace')
    return ' '.join(v.split())


def brief_write_files(fp, fname, run_buf, findings, written):
    """写出 1/2/3.txt 与 <名>_cache.txt；返回 (cache_path, tiers)，失败返回 (None, tiers)。

    只落盘、不上屏——分档统计块由 `brief_print_tiers` 单独负责，
    这样默认模式（tee）能复用同一份落盘逻辑而**不**多打统计块。
    """
    stem = os.path.splitext(fname)[0] or fname
    cdir = brief_cache_dir(fp)
    tiers = {'高': [], '中': [], '低': []}
    for f in findings:
        tiers[level_of(f.confidence)].append(f)
    for lv in tiers:
        tiers[lv].sort(key=lambda it: -it.confidence)
    try:
        os.makedirs(cdir, exist_ok=True)
        for lv, fn in _BRIEF_LEVELS:
            with open(os.path.join(cdir, fn), 'w', encoding='utf-8') as fh:
                fh.write('# 来源: %s\n' % fp)
                fh.write('# 级别: %s  条数: %d\n\n' % (_BRIEF_TITLES[lv], len(tiers[lv])))
                for f in tiers[lv]:
                    fh.write('[%.2f %s] %s: %s   @%s\n'
                             % (f.confidence, lv, f.kind, _brief_text(f)[:300], f.loc))
        cache_path = os.path.join(cdir, stem + '_cache.txt')
        with open(cache_path, 'w', encoding='utf-8') as fh:
            fh.write(run_buf.getvalue())
    except Exception as ex:
        print('[扫描缓存] 写入失败: %r' % ex)
        return None, tiers
    written.append(cache_path)
    return cache_path, tiers


def brief_print_tiers(fname, cdir, cache_path, tiers, multi=False, stream=None):
    """打印该文件的「分档统计块」（仅 -q 用；默认模式的详细报告已经上屏）。

    ⚠️ `stream` 必须传**真实 stdout**：调用时 sys.stdout 仍指着捕获用的替身，
    默认 `print()` 会把统计块也写进缓存文件，控制台上反而一片空白。
    """
    def _p(s):
        print(s, file=stream) if stream is not None else print(s)

    if multi:
        _p('[文件] %s' % fname)
    _p('【扫描统计】')
    for lv, fn in _BRIEF_LEVELS:
        line = '%s，具体信息：%s' % (_BRIEF_TITLES[lv], os.path.join(cdir, fn))
        if lv == '高' and tiers['高']:
            line += ' ' + '/'.join(_brief_text(f)[:60] for f in tiers['高'][:10])[:240]
        _p(line)
    _p('扫描结果（缓存），具体信息：%s' % cache_path)


def brief_append_tail(tail_text, written, files_total):
    """把运行汇总区（元判断核/汇总统计）追加到各缓存文件尾部。"""
    if not tail_text.strip() or not written:
        return
    for p in written:
        try:
            with open(p, 'a', encoding='utf-8') as fh:
                if not tail_text.startswith('\n'):
                    fh.write('\n')
                if files_total > 1:
                    fh.write('# ↓↓↓ 本次运行汇总（共 %d 个文件，含跨文件统计）↓↓↓\n' % files_total)
                fh.write(tail_text)
        except Exception:
            pass


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
    do_judge = False
    brief = False
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
        elif a == '--judge':
            do_judge = True
            i += 1
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
        elif a in ('-q', '--brief'):
            brief = True
            i += 1
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

    judge_net = None
    if do_judge:
        mpath = judge.model_path()
        if os.path.isfile(mpath):
            try:
                judge_net = judge.JudgePredictor.load(mpath)
                print('[判断核] 已加载模型: %s（%s）' % (mpath, judge_net.describe()))
            except Exception as ex:
                print('[判断核] 模型加载失败: %r' % ex)
        else:
            print('[判断核] 未找到模型（%s）；模型随版本发布，重装或离线训练后替换' % mpath)

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
    global_frags, global_frag_src = [], {}

    # 元判断核：聚合所有模块的结构化输出
    meta = MetaJudge()

    brief_written = []          # 本次运行已写出的缓存报告路径
    brief_dirs = []             # 本次运行各文件的缓存子目录（默认模式的 [缓存] 行要用）
    # 捕获区：默认模式 tee（上屏 + 缓存），-q 只进缓存。**只进出一次**，逐文件换缓冲。
    _real_stdout = sys.stdout
    _sink = _TeeStream(_real_stdout, passthrough=not brief)
    _brief_stack = ExitStack()
    _brief_stack.enter_context(redirect_stdout(_sink))

    def _emit_cache(fp, fname, buf, findings):
        """把本文件的扫描缓存落盘（-q 额外打「分档统计块」；默认模式报告已上屏）。"""
        cache_path, tiers = brief_write_files(fp, fname, buf, findings, brief_written)
        if cache_path is None:
            return
        cdir = brief_cache_dir(fp)
        brief_dirs.append(cdir)
        if brief:
            brief_print_tiers(fname, cdir, cache_path, tiers,
                              multi=len(targets) > 1, stream=_real_stdout)

    for fp in targets:
        fname = os.path.basename(fp)
        _brief_buf = io.StringIO()
        _sink.bind(_brief_buf)
        print('=' * 78)
        print('[文件] %s (%.1f KB)' % (fname, os.path.getsize(fp) / 1024))
        try:
            data = open(fp, 'rb').read()
        except Exception as ex:
            print('  读取失败: %r' % ex)
            _emit_cache(fp, fname, _brief_buf, [])
            continue

        # 解析一次，两个阶段共用（过去 Router 与旧版扫描器各解析一遍）
        ctx = CaptureContext(data)
        extract_ctx = None
        if do_extract:
            stem = os.path.splitext(os.path.basename(fp))[0]
            od = extract_dir or os.path.join(os.path.dirname(os.path.abspath(fp)), stem + '_extracted')
            extract_ctx = {'outdir': od, 'stem': stem}
        opts = ScanOptions(keywords=keywords, decode=do_decode, depth=depth,
                           limit=limit, extract=extract_ctx)

        # =========================================================================
        # 1. 路由调度（阶段一）：文件类型模块 → 【模块名】块
        # =========================================================================
        router_inst = Router(fp)
        try:
            router_inst.run_filetype(ctx)
            filetype_findings = router_inst.get_all_findings()

            if filetype_findings:
                print('\n【路由匹配模块】%s' % ' → '.join(router_inst.modules))
                router_inst.print_filetype_report()

                # 交给元判断核聚合
                for f in filetype_findings:
                    meta.add_finding(f.to_dict())
        except Exception as ex:
            print('  路由调度出错: %r' % ex)

        # =========================================================================
        # 2. 路由调度（阶段二）：流扫描 → 分带报告
        #    过程输出（格式:/主机表/[交互会话]/[提取]）由 scanner 自己打印，
        #    必须排在文件类型块之后——`【dns】` 在 `格式:` 之前是测试断言过的契约
        # =========================================================================
        stream_findings = []
        try:
            stream_findings = router_inst.run_stream(ctx, opts)
            # 只有抓包的结构化输出进元判断核（历史口径）：非抓包走 scan_rawfile，
            # 它的候选今天只进分带报告，不进聚合——放开会让每个 .evtx/.txt/.mem
            # 凭空多出一个【元判断核综合评分】块。
            if ctx.is_capture:
                for f in stream_findings:
                    meta.add_finding(f.to_meta_dict())
        except Exception as ex:
            print('  扫描出错: %r' % ex)
            _emit_cache(fp, fname, _brief_buf, [])
            continue

        # =========================================================================
        # 3. 结果统计
        # =========================================================================
        for f in stream_findings:
            if f.confidence >= BAND_HIGH:
                n_high += 1
                v = f.val if isinstance(f.val, str) else f.val.decode('utf-8', 'replace')
                # 值 → (kind, 来源文件)：汇总区要按 kind 区分 flag 候选与非 flag 证据
                highs.setdefault(' '.join(v.split())[:160], (f.kind, os.path.basename(fp)))
            elif f.confidence >= BAND_MID:
                n_mid += 1
            else:
                n_low += 1

        # =========================================================================
        # 4. 判断核打分与分带报告
        #    `report()` 与 `judge.predict_finding` 都按 5 元组解包，边界上转一次
        # =========================================================================
        _pfunc = None
        if judge_net is not None:
            finder = judge.ContextFinder(data)
            ftype = 'capture' if ctx.is_capture else 'raw'
            _pcache = {}

            def _pfunc(t, _finder=finder, _ft=ftype, _cache=_pcache):
                key = (t[1], str(t[3])[:120])
                if key not in _cache:
                    _cache[key] = judge.predict_finding(judge_net, t, _finder, _ft)
                return _cache[key]

        report([f.to_tuple() for f in stream_findings], limit, min_score, pfunc=_pfunc)
        if judge_net is not None:
            pool = sorted([f for f in stream_findings if f.confidence >= min_score],
                          key=lambda f: -f.confidence)[:max(limit, 60)]
            pool.sort(key=lambda f: -_pfunc(f.to_tuple()))
            top = pool[:6]
            if top:
                print('  【判断核·重点候选】（模型排序，优先核验）')
                for f in top:
                    v = f.val if isinstance(f.val, str) else f.val.decode('utf-8', 'replace')
                    v = ' '.join(v.split())
                    print('    p=%.2f  %s   @%s' % (_pfunc(f.to_tuple()), v[:110], f.loc))

        # =========================================================================
        # 5. 片段收集（跨文件拼接用）
        # =========================================================================
        frag_vals = []
        for f in stream_findings:
            if f.kind.startswith('片段'):
                v = f.val if isinstance(f.val, str) else f.val.decode('utf-8', 'replace')
                if v and v not in frag_vals:
                    frag_vals.append(v)
        for v in frag_vals:
            if v not in global_frag_src:
                global_frags.append(v)
                global_frag_src[v] = []
            if fname not in global_frag_src[v]:
                global_frag_src[v].append(fname)
        if len(frag_vals) >= 2:
            print('  [拼接建议] 本文件检出 %d 个片段（供人工确认）：' % len(frag_vals))
            print('    %s' % ' | '.join(frag_vals[:12]))
            s = assemble_suggestion(frag_vals)
            if s:
                print('    启发式拼接尝试（人工确认）：%s' % s[:200])

        # 本文件报告捕获完毕 → 落盘扫描缓存（-q 另打「分档统计块」）
        _emit_cache(fp, fname, _brief_buf, stream_findings)

    # 汇总区（元判断核 / 全局片段 / 汇总统计）也要进缓存：换成汇总缓冲，
    # 默认模式仍 tee 上屏。两种模式的缓存文件因此都带汇总尾段。
    _brief_tail = io.StringIO()
    _sink.bind(_brief_tail)

    # =========================================================================
    # 6. 元判断核综合报告
    # =========================================================================
    if meta.findings:
        print('\n' + '=' * 78)
        meta.score()
        meta.print_report(min_score)

    print('=' * 78)
    if len(global_frags) >= 2:
        print('【全局片段拼接建议】（跨文件收集到 %d 个片段，供人工确认）' % len(global_frags))
        print('  片段池（按文件标注来源）：')
        for v in global_frags[:24]:
            print('    %s   ← %s' % (v, '、'.join(global_frag_src.get(v, [])[:4])))
        if len(global_frags) > 24:
            print('    ...（其余 %d 个省略）' % (len(global_frags) - 24))
        s = assemble_suggestion(global_frags)
        if s:
            print('  启发式拼接尝试（人工确认）：%s' % s[:240])
    def _flag_shaped(s):
        """候选值是否呈 flag 形状——用来把「flag 候选」与「非 flag 类证据」分开。

        高置信不等于"是答案"：FTP 凭据、交互会话记录、系统版本这些同样是高置信，
        但把它们列进"可直接提交的候选"会误导（用户实测反馈"得出来的根本不是 flag"）。
        """
        try:
            return bool(FLAG_RE.search(s.encode('utf-8', 'replace')))
        except Exception:
            return False

    if highs:
        _fl = [(v, k, src) for v, (k, src) in highs.items() if _flag_shaped(v)]
        _ev = [(v, k, src) for v, (k, src) in highs.items() if not _flag_shaped(v)]
        if _fl:
            print('【flag 候选汇总】（可直接核验/提交）')
            for v, _k, src in _fl:
                print('  * %s   (来自 %s)' % (v, src))
        if _ev:
            if _fl:
                print('【证据汇总】（非 flag 类，按题目要求核实）')
            else:
                print('【证据汇总】（未发现 flag 形状候选；以下为 ≥%s 的非 flag 证据）' % BAND_HIGH)
            for v, k, src in _ev:
                print('  * [%s] %s   (来自 %s)' % (k, v, src))
    else:
        # 分带报告一条高置信都没有——但模块块（【config】/【dns】…）可能仍有高置信发现，
        # 那类不进 `highs`。两者都空才明确说"没找到"，避免把"有发现"误报成"无"。
        _meta_high = 0
        try:
            if meta.findings:
                _meta_high = meta.get_summary(min_score).get('high', 0)
        except Exception:
            _meta_high = 0
        if not _meta_high:
            print('【重点候选】未发现高（≥%s）候选' % BAND_HIGH)
    print('【扫描统计】')
    # 两条管线分别报，且**不给合计**：线路（分带报告）与模块（【dns】/【logs】等类型块）
    # 常常是同一批证据的两个视角，加起来会重复计数；只报线路那一半又会自相矛盾
    # （"统计说高 0 条"，而上面的【logs】块明明有一条 0.97），用户据此以为没找到东西。
    _m = {'high': 0, 'medium': 0, 'low': 0}
    try:
        if meta.findings:
            _m = meta.get_summary(min_score)
    except Exception:
        pass
    print('  线路报告（抓包/原始文件）：高 %d 条 / 中 %d 条 / 低 %d 条'
          % (n_high, n_mid, n_low))
    print('  模块报告（类型块）：高 %d 条 / 中 %d 条 / 低 %d 条'
          % (_m['high'], _m['medium'], _m['low']))

    # 汇总区捕获结束 → 追加到各缓存文件尾部；恢复真实 stdout 后再打缓存路径
    _brief_stack.close()
    brief_append_tail(_brief_tail.getvalue(), brief_written, len(targets))

    # 默认模式新增的一行（-q 已有「扫描结果（缓存），具体信息：…」四行，保持逐字节不变）：
    # 用户实测反馈"跑完看不到任何结果文件"——路径必须出现在控制台上。
    if not brief and brief_written:
        print('\n【扫描缓存】本次 %d 个文件，报告与分档明细已写入:' % len(brief_written))
        for d in brief_dirs:
            # 末尾带分隔符：读起来是"写进这个目录"，也让 golden 的归一化
            # （`/<名>-<6位哈希>/` → `/<名>-<哈希>/`）能覆盖这一行
            print('  %s%s' % (d, os.sep))
        print('  完整报告见各目录下的 <文件名>_cache.txt；占用与清理见 ctfsweep config')
    return 0
