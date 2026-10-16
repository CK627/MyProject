# -*- coding: utf-8 -*-
"""变更的唯一咽喉。所有 `_do_*` 只从这里被调用。

**九道闸，顺序即安全属性：**

    1) 溯源     item.uid 必须在本次进程扫到的集合里 —— 挡住"构造一个 item 传进来"
    2) ★硬闸   origin != third_party → Refused（不是警告，是拒绝）
    3) 可改性   item.mutable（dataclass 默认 False，后端忘了设就落在安全那侧）
    4) 置信度   confidence 达阈值（默认只要 high）
    5) 白名单   ★**不在此处参与放行** —— 它只收窄 clean 的候选集，绝不参与放行
    6) TOCTOU   reclassify 重读活源；origin 或 uid 变了 → 中止
    7) 先备份   写盘 + sha1 校验；校验不过则中止该项
    8) dry-run  到此为止，只返回 planned
    9) 到这一步才 getattr(backend, '_do_' + op)

第 5 条是刻意的空位，它存在的意义就是**被指出**：白名单的不变量是
「只能收窄破坏性集合，永远不能放宽」。把 origin 硬闸放在白名单之前、且互不引用，
这条不变量才是结构性的，而不是靠代码审查记住的。
"""
import os

from . import classify, safety
from .safety import Refused, EXIT_OK, EXIT_FAIL, EXIT_REFUSED, EXIT_USAGE

# 变更操作名 ↔ 后端私有方法名。反射测试遍历本表，
# 于是将来新增一个 `_do_purge` 会被自动覆盖，漏写守卫会立刻失败。
MUTATORS = ('disable', 'enable', 'remove', 'add')


def _do_method(op):
    return '_do_' + op


class OpResult(object):
    def __init__(self, op, item, status, detail='', needs_root=False):
        self.op = op
        self.item = item
        self.status = status          # done | planned | skipped | failed | refused
        self.detail = detail
        self.needs_root = needs_root

    def __repr__(self):
        return '<OpResult %s %s %s>' % (self.op, self.item.key if self.item else '-', self.status)


# ---------------------------------------------------------------- 闸门
def check_gates(item, ctx, op='', allow_confidence=('high',)):
    """跑第 1–4 道闸。通过则返回 None，否则抛 Refused。

    独立成函数是为了让反射测试能对每个后端 × 每个 mutator 直接调它，
    而不必真的执行变更。
    """
    # 1) 溯源
    if item.uid not in ctx.scanned_uids:
        raise Refused(
            '拒绝操作 %s：该项不是本次扫描得到的（uid %s）' % (item.key, item.uid),
            hint='请重新扫描后再操作；本工具只允许操作它自己扫到的项')

    # 2) ★ 硬闸：系统项一律拒绝
    if item.origin != 'third_party':
        evidence = '（%s）' % item.origin_evidence if item.origin_evidence else ''
        raise Refused(
            '拒绝操作 %s：判定为「%s」%s' % (item.key, _origin_cn(item.origin), evidence),
            hint='系统项永不由本工具改动。若确认要处理，请用系统自带工具。')

    # 3) 后端声明的可改性
    if not item.mutable:
        raise Refused(
            '拒绝操作 %s：后端未将其标记为可改（mutable=False）' % item.key,
            hint='这通常意味着该项位于不应改动的路径。')

    # 4) 置信度
    if allow_confidence and item.confidence not in allow_confidence:
        raise Refused(
            '拒绝操作 %s：分类置信度为 %s，低于当前阈值（%s）' % (
                item.key, item.confidence, '/'.join(allow_confidence)),
            hint='确认无误可加 --confidence %s' % item.confidence)

    return None


def _origin_cn(origin):
    from .model import ORIGIN_CN
    return ORIGIN_CN.get(origin, origin)


# ---------------------------------------------------------------- 单次变更
def mutate(op, item, ctx, allow_confidence=('high',), extra_plan=None):
    """执行一次变更（或只预览）。返回 OpResult。

    调用方负责先 confirm()；本函数只管闸门 + 备份 + 执行。
    """
    check_gates(item, ctx, op, allow_confidence)

    # 6) TOCTOU：重读活源、重跑分类。扫描时的记录**不作为授权依据**。
    live = ctx.backend.reclassify(item, ctx)
    if live is None:
        raise Refused('源已不存在，已中止：%s' % (item.source or item.anchor))
    if live.uid != item.uid or live.origin != 'third_party':
        raise Refused(
            '源在扫描后已改变（%s），已中止，请重扫' % (item.source or item.anchor),
            hint='uid 或分类结果与扫描时不一致，出于安全考虑不继续')

    # 7) 先备份 → 校验 → 再变更
    bk = getattr(ctx, '_current_backup', None)
    entry = None
    if bk is not None:
        entry = safety.backup_file(live, bk, note='%s %s' % (op, live.key))
        ok, why = safety.verify_backup(entry)
        if not ok:
            # 备份不可用 → 这一项**不动**，继续下一项（绝不带着坏备份下手）
            return OpResult(op, live, 'failed', '备份失败：%s' % why)

    # 8) dry-run
    if ctx.dry_run:
        if entry is not None:
            safety.mark(entry, op, 'planned')
        return OpResult(op, live, 'planned')

    # 9) 执行
    method = getattr(ctx.backend, _do_method(op), None)
    if method is None:
        return OpResult(op, live, 'failed', '后端未实现 %s' % op)
    try:
        detail = method(live, ctx, backup=bk, entry=entry)
    except Refused:
        raise
    except Exception as e:                                   # noqa: BLE001
        if entry is not None:
            safety.mark(entry, op, 'failed', str(e))
        return OpResult(op, live, 'failed', '%s: %s' % (type(e).__name__, e))

    if entry is not None:
        safety.mark(entry, op, 'done', detail or '')
    return OpResult(op, live, 'done', detail or '')


def plan_for(op, item, ctx):
    """取后端的纯函数计划（预览与执行共用）。后端没实现就回退一句通用说明。"""
    try:
        lines = ctx.backend.plan(op, item, ctx)
        if lines:
            return list(lines)
    except Exception:                                        # noqa: BLE001
        pass
    return ['  · %s %s' % (op, item.key)]


# ---------------------------------------------------------------- 批量
def run_batch(op, items, ctx, what, allow_confidence=('high',), announce=None):
    """批量变更（clean / 多引用 disable 等）。

    返回 (results, exit_code)。**逐项独立**：一项失败不影响其余项，
    但失败的会被如实计数——绝不把"部分成功"报成成功。
    """
    if not items:
        print('没有需要处理的项。')
        return [], EXIT_OK

    # ★ 先过闸门、再问确认。
    #
    # 顺序反了会有两个后果，都很糟：
    #   1. 用户敲 `disable com.apple.Finder` 会被问"确定要执行吗"，答完才被告知
    #      "拒绝：系统项" —— 工具先征求了一个它根本不打算执行的许可。
    #   2. 非交互环境下这条命令会以"请加 -y"（退出 1）结束，把**安全拒绝**（退出 3）
    #      整个盖掉。脚本据此判断时会以为是用法问题，而不是"这东西不许动"。
    # 把必然被拒的挑出来放在确认之前，"拒绝"才是一种可被脚本识别的结果。
    actionable, pre_refused = [], []
    for it in items:
        try:
            check_gates(it, ctx, op, allow_confidence)
            actionable.append(it)
        except Refused as e:
            pre_refused.append(OpResult(op, it, 'refused', str(e)))

    if pre_refused:
        print('已拒绝 %d 项（安全判定，未执行也未询问）:' % len(pre_refused))
        for r in pre_refused:
            print('  · %s：%s' % (r.item.key, r.detail))

    if not actionable:
        return pre_refused, (EXIT_REFUSED if pre_refused else EXIT_OK)

    plan_lines = []
    for it in actionable:
        plan_lines.extend(plan_for(op, it, ctx))

    if not safety.confirm(what, plan_lines, ctx):
        return pre_refused, EXIT_OK if ctx.dry_run else EXIT_FAIL

    bk = safety.make_manifest(op, ctx)
    ctx._current_backup = bk
    results = []
    try:
        for it in items:
            try:
                results.append(mutate(op, it, ctx, allow_confidence=allow_confidence))
            except Refused as e:
                results.append(OpResult(op, it, 'refused', str(e)))
        safety.save_manifest(bk)
    finally:
        ctx._current_backup = None

    results = pre_refused + results
    return results, summarize(results, ctx, op, already_reported=bool(pre_refused))


def summarize(results, ctx, op, already_reported=False):
    """汇总并返回退出码。报告口径必须诚实：跳过就是跳过，绝不报成功。

    退出码优先级：失败(1) > 拒绝(3) > 成功(0)。**拒绝要能被脚本识别出来**——
    它是"这东西不许动"，不是"命令没用对"。
    """
    done = [r for r in results if r.status == 'done']
    planned = [r for r in results if r.status == 'planned']
    skipped = [r for r in results if r.status in ('skipped',)]
    refused = [r for r in results if r.status == 'refused']
    failed = [r for r in results if r.status == 'failed']
    need_root = [r for r in results if r.needs_root]

    print('')
    if planned:
        print('--dry-run：计划处理 %d 项，未改动任何东西' % len(planned))
    if done:
        print('已%s %d 项' % (_op_cn(op), len(done)))
    if skipped:
        print('已跳过 %d 项' % len(skipped))
        for r in skipped:
            print('  · %s：%s' % (r.item.key, r.detail))
    if need_root:
        print('已跳过 %d 项（需要管理员权限）:' % len(need_root))
        for r in need_root:
            print('  %s' % (r.item.source or r.item.anchor))
        print('  → 需要时: sudo startupctl %s' % op)
    if refused and not already_reported:
        print('已拒绝 %d 项（安全判定）:' % len(refused))
        for r in refused[:10]:
            print('  · %s：%s' % (r.item.key, r.detail))
        if len(refused) > 10:
            print('  … 另有 %d 项' % (len(refused) - 10))
    if failed:
        print('失败 %d 项:' % len(failed))
        for r in failed:
            print('  · %s：%s' % (r.item.key, r.detail))

    if failed:
        return EXIT_FAIL
    if ctx.conf.getbool('STRICT') and (skipped or need_root):
        return EXIT_FAIL
    # 有拒绝、且没有任何一项真的被处理 → 用"因安全理由被拒绝"(3) 收尾
    if refused and not done and not planned:
        return EXIT_REFUSED
    return EXIT_OK


def _op_cn(op):
    return {'disable': '禁用', 'enable': '启用', 'remove': '移除', 'add': '新增'}.get(op, op)


# ---------------------------------------------------------------- 候选集
def clean_candidates(scan, ctx, confidence=('high',), include_unknown=False):
    """选出 clean 会处理的项。

    **白名单只在这里出现，且只做减法**——
    `origin == 'third_party'` 这个条件与白名单无关、也不受它影响，
    所以任何白名单条目都无法让一个系统项进入候选集。
    """
    out = []
    for it in scan.items:
        if it.shadowed_by:
            continue
        if include_unknown:
            if it.origin not in ('third_party', 'unknown'):
                continue
        elif it.origin != 'third_party':
            continue
        if it.confidence not in confidence:
            continue
        if it.whitelisted:
            continue
        # ★ 只收**我们真的动得了**的项。登录项、BTM 记录这类由系统自己的数据库
        #   管理，mutable=False（改它们要走系统设置）。把它们算进"可清理"会让
        #   check 报出一个虚高的数字、clean 打出一份做不到的计划——然后逐项被闸门
        #   拒绝。候选集必须等于"点了头就能真做成的事"。
        if not it.mutable:
            continue
        out.append(it)
    return out


def partition_by_confidence(items):
    high = [i for i in items if i.confidence == 'high']
    other = [i for i in items if i.confidence != 'high']
    return high, other
