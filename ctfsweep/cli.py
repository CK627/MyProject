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
from .core import selfmgr
from .core.router import Router, Finding, ScanOptions
from .core.meta_judge import MetaJudge
from .core.report import report
from .core.utils import BAND_HIGH, BAND_MID, FLAG_RE, level_of

HELP = """ctfsweep — CTF 流量 / 日志 / 注册表 快速扫描器（零依赖，Python 3.8+）

用法:
  ctfsweep <文件或目录> [选项]           # 已安装（PATH 中）
  python3 -m ctfsweep <文件或目录> ...   # 未安装，项目目录内直接跑
  ./bin/ctfsweep.sh <文件或目录> ...     # 仓库启动器（macOS / Linux）

管理子命令:
  ctfsweep update [--check]   拉取最新源码快照并重装（--check 只比对版本，不落盘）
  ctfsweep install            显示安装方式（装到 devtools 目录）
  ctfsweep uninstall [-y]     卸载安装副本并摘除 shell 接线（用户数据保留；-y 跳过确认）
  ctfsweep config             显示运行信息与生效配置
  ctfsweep train [--data F]   训练本地判断核模型（超参数读训练配置；--epochs N / --model-out F 可覆盖）
  ctfsweep label              交互式标注未标注候选（确认/否定/跳过）
  ctfsweep auto-label         自动标注未标注候选（强模型规则验证 → 正/负样本）
  ctfsweep mark <路径> <flag> 用真实答案回填一道题（文件/文件夹均可）：匹配候选→正样本，
                              同题其他高分候选→负样本（难负样本）；无记录时自动先扫描
  ctfsweep learning [opts]    自主学习：先逐题复核留存区（题目；答案：<真实flag>），再训练
                              （带收敛判断；超参数读训练配置；--min-auc N --min-samples N 可覆盖）
  ctfsweep gen-data [-o F]    生成 CTF 取证训练数据集（覆盖 PCAP/内存/浏览器/日志/邮件/数据库/配置/压缩/DNS/编码；默认输出到用户数据目录）
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
  -q, --brief       精简输出：控制台只打「分档统计块」（高/中/低 + 缓存文件路径），
                    完整报告与各档明细写入 <数据目录>/cache/<文件名>-<哈希>/：
                    1.txt（高）/ 2.txt（中）/ 3.txt（低）/ <文件名>_cache.txt（完整输出）
  --extract         从流量中提取文件（ZIP/PNG/JPG/GIF/PDF/GZ/RAR/7Z/PE/OLE2/ELF，
                    以及 HTML 载荷页内嵌的 base64 文件），
                    保存到 "<抓包名>_extracted/" 并自动解压/扫描其内容；
                    加密 zip 自动尝试：空口令→常用表→--pwd-file 字典→流量采集口令
  --extract-dir D   指定提取输出目录（默认与抓包同目录）
  --pwd-file F      附加口令字典文件（每行一个，用于加密压缩包）
  --judge           用本地判断核模型对候选打分（p=…，并列出重点候选；需先 ctfsweep train）
  --config F        指定配置文件（默认读取 ~/.devtools/ctfsweep/ctfsweep.conf）
  --version         显示版本
  -h, --help        显示本帮助

置信度模型（每条结果带 [分数 级别]）:
  0.97 高   明文完整 flag（xxx{...} 直接可见）
  0.95 高   解码后得到完整 flag（hex/base64/DNS 子域名等）
  0.75 中   内容"加壳"候选（疑似 flag 本体、缺 flag{} 外壳）
  0.72 中   JWT 令牌（自动解码 header/payload，伪造身份类题）
  0.65 中   (flag|ctf)…{ 未闭合片段（典型的分段 flag 前半截）
  0.62 中   命令回显 / 环境变量密钥回显（webshell、取证题关键线索）
  0.60 中   裸花括号片段 {xxxx
  0.55 中   裸闭合片段 xxxx}
            （evtx / reg 等原始文件自动剔除噪音：GUID / 路径后缀拼贴 / 乱码区巧合）
  0.45 低   DNS 查询名（域名白名单一眼可辨）
  0.42 低   接口短文本响应（HTTP 事务配对结果）
  0.40 低   关键词上下文（普通字符串命中，需人工浏览）

判断核（--judge）:
  本地训练的轻量判断网络（纯 Python MLP 集成，二进制 .ctfj 模型），对候选输出 p 分并按"答案相关性"排序；
  模型与配置在项目内 models/（model.ctfj + train_config.json，随项目版本管理）；
  训练数据在缓存区 ~/.devtools/ctfsweep/judge/（dataset.jsonl 累积标注 / pending.jsonl 扫描候选池）；
  训练: ctfsweep train；超参数: 编辑 models/train_config.json（网络结构/学习率/种子等，改参数无需改代码）

留存区（每次扫描自动记录）:
  每次扫描的候选快照记入 ~/.devtools/ctfsweep/judge/retention.jsonl；
  有答案: ctfsweep mark <路径> <真实flag>（立即回填正/负样本）；
  没答案: ctfsweep learning 时逐题询问（题目；答案：<真实flag>，一个接一个，处理完再训练）
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
        print('运行模式: devtools 安装（ctfsweep update 可更新，用户数据保留）')
    else:
        print('运行模式: 未识别')
    print('程序目录: %s' % root)
    print('模型: %s（项目内；%s）' % (judge.model_path(),
                                   '已就绪' if os.path.isfile(judge.model_path()) else '未训练'))
    tc_path = judge.train_config_path()
    print('训练配置: %s（项目内；%s）' % (tc_path, '已就绪' if os.path.isfile(tc_path)
                                        else '不存在，首次训练时自动生成'))
    print('扫描缓存: %s（候选池 pending.jsonl / 数据集 dataset.jsonl）' % judge.user_dir())

    # -q/--brief 的缓存只增不减（用户数据目录内的文件永不自动删除），
    # 这里把占用与可删路径一并报出来，作为唯一的清理入口。
    croot = brief_cache_root()
    if os.path.isdir(croot):
        cnum, csize = _dir_usage(croot)
        print('精简缓存: %s（%d 个文件，%.1f MB；-q 生成，确认不需要后可整体删除）'
              % (croot, cnum, csize / 1048576.0))
    else:
        print('精简缓存: %s（尚未使用；-q/--brief 会把明细写在这里）' % croot)

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
        print('判断核模型: %s（不存在；ctfsweep train 可训练）' % mp)
    return 0


def _cmd_train(args):
    """ctfsweep train：训练本地判断核（留一组评估 + 保存模型）。

    超参数默认读取训练配置（judge/train_config.json）；--epochs 可临时覆盖。
    """
    data_path, model_out, epochs = None, None, None
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--data' and i + 1 < len(args):
            data_path = args[i + 1]
            i += 2
        elif a in ('--model-out', '--model') and i + 1 < len(args):
            model_out = args[i + 1]
            i += 2
        elif a == '--epochs' and i + 1 < len(args):
            try:
                epochs = int(args[i + 1])
            except Exception:
                pass
            i += 2
        else:
            i += 1
    data_path = data_path or judge.default_dataset_path()
    model_out = model_out or judge.model_path()
    if not os.path.isfile(data_path):
        print('未找到数据集: %s' % data_path)
        print('提示: 数据集 = 本机解题标注（每行一条候选 + 真/假标签），积累后即可训练。')
        return 2
    rows = judge.load_rows(data_path)
    if len(rows) < 8:
        print('数据太少（%d 条），至少需要 8 条标注样本。' % len(rows))
        return 2
    judge.run_training(rows, model_out=model_out, epochs=epochs)   # epochs=None → 读训练配置
    return 0


def _cmd_label(args):
    """ctfsweep label：交互式标注未标注候选。"""
    batch_size = 10
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--batch' and i + 1 < len(args):
            try:
                batch_size = int(args[i + 1])
            except Exception:
                pass
            i += 2
        else:
            i += 1
    return judge.interactive_label(batch_size=batch_size)


def _cmd_auto_label(args):
    """ctfsweep auto-label：自动标注未标注候选（强模型规则验证）。"""
    pos_count, neg_count, fail_reasons = judge.auto_annotate_pending()
    return 0


def _scan_for_candidates(path, keywords=None):
    """扫描文件或文件夹，收集候选快照（供留存区记录 / mark 自动补扫）。

    返回 (candidates, files_count)。文件与文件夹一视同仁（目录递归展开，
    路径取名随意无影响——如 flag.pacpng/ 这种"名字像文件实为目录"也照常处理）。
    """
    keywords = keywords or ['flag', 'ctf']
    if os.path.isdir(path):
        targets = []
        for root, _dirs, files in os.walk(path):
            for f in sorted(files):
                if f != '.DS_Store':
                    targets.append(os.path.join(root, f))
    else:
        targets = [path]
    cands = []
    for fp in targets:
        try:
            data = open(fp, 'rb').read()
        except Exception:
            continue
        fname = os.path.basename(fp)
        try:
            # 与主扫描同一入口：抓包/原始字节的判别在 CaptureContext 里，不再自己嗅魔数
            ctx = CaptureContext(data)
            findings, _meta = Router(fp).run_stream(
                ctx, ScanOptions(keywords=keywords, decode=True, depth=3, limit=50))
        except Exception:
            continue
        for score, kind, _tok, val, _loc in findings:
            if score >= judge.RETENTION_MIN_SCORE:
                v = val if isinstance(val, str) else val.decode('utf-8', 'replace')
                cands.append({'score': score, 'kind': kind, 'val': v, 'file': fname})
    return cands, len(targets)


def _cmd_mark(args):
    """ctfsweep mark <文件或文件夹> <真实flag>：用真实答案回填一道题。

    正样本 = 与答案匹配的候选；负样本 = 同题其他高分候选（难负样本）。
    无扫描记录时自动先扫描一次（文件/文件夹均可）。
    """
    if len(args) < 2:
        print('用法: ctfsweep mark <文件或文件夹> <真实flag>')
        print('  示例: ctfsweep mark ./logs "flag{windows-log-answer}"')
        print('  回填规则: 与答案匹配的候选 → 正样本；')
        print('            同题其他高分候选 → 负样本（难负样本，最有学习价值）')
        return 2
    path, real_flag = args[0], args[1]
    if not os.path.exists(path):
        print('路径不存在: %s' % path)
        return 2
    rec = judge.find_retention_for(path)
    if rec is None:
        print('[留存区] 未找到该路径的扫描记录，自动扫描一次...')
        cands, n_files = _scan_for_candidates(path)
        if cands:
            print('  扫描完成: %d 个文件 / %d 条候选' % (n_files, len(cands)))
            judge.record_scan(path, cands, files_count=n_files)
        else:
            print('  扫描未产出候选（答案将直接作为正样本回填）')
    res = judge.mark_answers(path, real_flag)
    if res is None:
        print('回填写入失败（留存区记录异常）')
        return 1
    pos, neg, dedup, matched, rec2 = res
    print('[mark] 题目: %s' % rec2.get('path'))
    print('  答案: %s' % real_flag)
    print('  回填: 正样本 %d 条 / 负样本 %d 条（与已有数据重复跳过 %d）' % (pos, neg, dedup))
    if not matched:
        print('  [注] 候选未匹配到答案——答案已作为正样本直接入库；请确认答案与题目对应')
    elif pos == 0:
        print('  （答案命中但样本已在数据集中——重复跳过；负样本已补充）')
    print('  提示: 运行 ctfsweep learning 将新数据纳入训练')
    return 0


def _cmd_gen_data(args):
    """ctfsweep gen-data：生成 CTF 取证训练数据集（默认输出到用户数据目录）。"""
    from ctfsweep.core import data_generator
    # 默认输出到用户数据目录（与"数据集中放 .devtools"原则一致）
    if '-o' not in args and '--output' not in args:
        args = list(args) + ['-o', os.path.join(judge.user_dir(), 'generated_data.jsonl')]
    _old_argv = sys.argv
    try:
        sys.argv = ['ctfsweep gen-data'] + list(args)
        data_generator.main()
    except SystemExit as e:
        return e.code or 0
    finally:
        sys.argv = _old_argv
    return 0


def _cmd_learning(args):
    """ctfsweep learning：自主学习（带收敛判断）。

    超参数默认读取训练配置（judge/train_config.json）；命令行选项可临时覆盖。
    """
    min_auc, min_samples, max_epochs, epochs_per_run = None, None, None, None
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--min-auc' and i + 1 < len(args):
            try:
                min_auc = float(args[i + 1])
            except Exception:
                pass
            i += 2
        elif a == '--min-samples' and i + 1 < len(args):
            try:
                min_samples = int(args[i + 1])
            except Exception:
                pass
            i += 2
        elif a == '--max-epochs' and i + 1 < len(args):
            try:
                max_epochs = int(args[i + 1])
            except Exception:
                pass
            i += 2
        elif a == '--epochs' and i + 1 < len(args):
            try:
                epochs_per_run = int(args[i + 1])
            except Exception:
                pass
            i += 2
        else:
            i += 1
    return judge.learning_loop(
        min_auc=min_auc,
        min_samples=min_samples,
        max_epochs=max_epochs,
        epochs_per_run=epochs_per_run,
    )


# ---------------------------------------------------------------- 精简输出（-q / --brief）
# 控制台只打「分档统计块」；完整报告与各档明细写入 <数据目录>/cache/<文件名>-<哈希>/：
#   1.txt / 2.txt / 3.txt     高/中/低置信候选明细（分数 | 级别 | 类型 | 值 | 位置）
#   <文件名>_cache.txt        该文件的完整扫描输出（与详细模式控制台所见一致）
#
# 数据根跟随 CTFSWEEP_DATA_DIR（`judge.user_dir()` 的父目录），测试隔离天然生效。
_BRIEF_LEVELS = (('高', '1.txt'), ('中', '2.txt'), ('低', '3.txt'))
_BRIEF_TITLES = {'高': '高置信（可直接核验）',
                 '中': '中置信（需人工确认）',
                 '低': '低置信（线索参考）'}


def brief_cache_root():
    """精简输出缓存根目录（跟随 CTFSWEEP_DATA_DIR，便于测试与多环境隔离）。"""
    return os.path.join(os.path.dirname(judge.user_dir()), 'cache')


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


def brief_emit(fp, fname, run_buf, findings, written, multi=False):
    """写出 1/2/3.txt 与 <名>_cache.txt，并打印该文件的分档统计块。"""
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
        print('[精简输出] 缓存写入失败: %r' % ex)
        return
    written.append(cache_path)
    if multi:
        print('[文件] %s' % fname)
    print('【扫描统计】')
    for lv, fn in _BRIEF_LEVELS:
        line = '%s，具体信息：%s' % (_BRIEF_TITLES[lv], os.path.join(cdir, fn))
        if lv == '高' and tiers['高']:
            line += ' ' + '/'.join(_brief_text(f)[:60] for f in tiers['高'][:10])[:240]
        print(line)
    print('扫描结果（缓存），具体信息：%s' % cache_path)


def brief_append_tail(tail_text, written, files_total):
    """把运行汇总区（留存区/元判断核/汇总统计）追加到各缓存文件尾部。"""
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
    # 管理子命令（update / install / uninstall / config / train / label / auto-label / mark / learning / gen-data / help）
    if args and args[0] in ('update', 'install', 'uninstall', 'config', 'train', 'label',
                            'auto-label', 'mark', 'learning', 'gen-data', 'help'):
        sub, rest = args[0], args[1:]
        if sub == 'help':
            print(HELP)
            return 0
        if sub == 'config':
            return _cmd_config()
        if sub == 'train':
            return _cmd_train(rest)
        if sub == 'label':
            return _cmd_label(rest)
        if sub == 'auto-label':
            return _cmd_auto_label(rest)
        if sub == 'mark':
            return _cmd_mark(rest)
        if sub == 'learning':
            return _cmd_learning(rest)
        if sub == 'gen-data':
            return _cmd_gen_data(rest)
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
            print('[判断核] 未找到模型（%s），请先运行: ctfsweep train' % mpath)

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
    scan_cands = []   # 本次扫描的候选快照（写入留存区，供答案回填）

    # 元判断核：聚合所有模块的结构化输出
    meta = MetaJudge()
    # 旧版判断核（保留兼容）
    judge_net = judge_net  # 前面已加载

    brief_written = []                              # 精简输出：本次运行已写出的缓存报告
    _brief_stack = ExitStack() if brief else None   # 精简输出：逐文件捕获 stdout（详细输出只进缓存）

    for fp in targets:
        fname = os.path.basename(fp)
        if brief:
            _brief_buf = io.StringIO()
            _brief_stack.enter_context(redirect_stdout(_brief_buf))
        print('=' * 78)
        print('[文件] %s (%.1f KB)' % (fname, os.path.getsize(fp) / 1024))
        try:
            data = open(fp, 'rb').read()
        except Exception as ex:
            print('  读取失败: %r' % ex)
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

        # =========================================================================
        # 5b. 数据收集：候选 → 留存区（每次扫描都记录）；--judge 时同步写 pending 池
        # =========================================================================
        for f in stream_findings:
            if f.confidence >= judge.RETENTION_MIN_SCORE:
                v = f.val if isinstance(f.val, str) else f.val.decode('utf-8', 'replace')
                scan_cands.append({
                    'score': f.confidence,
                    'kind': f.kind,
                    'val': v,
                    'file': fname,
                })
                if do_judge:
                    candidate = {
                        'score': f.confidence,
                        'kind': f.kind,
                        'val': v,
                        'tok': f.tok,
                        'file_type': 'capture' if ctx.is_capture else 'raw',
                        'module_scores': {},
                        'meta_score': 0.0,
                    }
                    judge.save_pending(candidate)

        if brief:
            # 本文件详细输出捕获完毕 → 写缓存文件 + 打「分档统计块」（控制台只留结论）
            _brief_stack.close()
            brief_emit(fp, fname, _brief_buf, stream_findings, brief_written,
                       multi=len(targets) > 1)
            _brief_stack = ExitStack()
    if brief:
        _brief_stack.close()   # 兜底：最后一轮若走 continue，上面的关闭不会执行

    _brief_tail = None
    if brief:
        _brief_tail = io.StringIO()
        _brief_stack.enter_context(redirect_stdout(_brief_tail))

    # =========================================================================
    # 5c. 留存区：记录本次扫描（供答案回填与 learning 复核）
    # =========================================================================
    try:
        _rec = judge.record_scan(path, scan_cands, files_count=len(targets))
        if _rec:
            print('\n[留存区] 已记录本次扫描（%d 条候选）：%s'
                  % (len(_rec.get('candidates') or []), path))
            print('  已知答案可回填: ctfsweep mark "%s" <真实flag>' % path)
    except Exception as _ex:
        print('\n[留存区] 记录失败: %r' % _ex)

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

    if brief:
        _brief_stack.close()
        brief_append_tail(_brief_tail.getvalue(), brief_written, len(targets))
    return 0
