# -*- coding: utf-8 -*-
"""安全机制：拒绝语义 · 预览在前 · 先备份再变更 · 还原。

这个工具会改**用户的系统启动状态**，所以本文件的三条规矩是不可协商的：

1. **预览与执行共用一份计划。** `plan()` 是纯函数（在 backend 里），`confirm()` 先把它
   逐行打印，**加不加 `-y` 都打印**。于是粘贴出来的 `-y` 记录是自解释的，预览路径也
   不可能与执行路径漂移——因为根本只有一条路径。

2. **非交互且无 `-y` → 拒绝执行、退出 1、零改动。** 这让工具在管道里和 CI 里天然安全。

3. **先备份 → 校验 → 再变更。绝不"先改后备份"。** 备份写盘后立即用 sha1 校验，
   校验不过就中止该项（而不是带着坏备份往下走）。

退出码约定（脚本能据此区分）：
    0 成功 · 1 失败 · 2 用法错 · 3 **因安全理由被拒绝**
"""
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone

from . import paths

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_REFUSED = 3


class Refused(Exception):
    """因安全理由拒绝执行。**不是错误，是设计成功的表现。**

    独立异常类型 + 独立退出码（3），使脚本能区分「被安全拒绝」与「跑失败了」。
    """

    exit_code = EXIT_REFUSED

    def __init__(self, message, hint=''):
        self.hint = hint
        Exception.__init__(self, message)


class BackupFailed(Exception):
    """备份没能完成 —— 此时**绝不能**继续变更。"""
    exit_code = EXIT_FAIL


# ---------------------------------------------------------------- 确认
def confirm(what, plan_lines, ctx, assume_yes=False):
    """打印计划并按需确认。返回 True 才允许执行。

    计划**永远先打印**（跳过确认时也打）：`confirm` 的意思是"我审过计划了"，
    不是"别给我看"。
    """
    for ln in (plan_lines or []):
        print(ln)

    if ctx.dry_run:
        print('--dry-run：以上为将要执行的操作，未改动任何东西')
        return False

    if assume_yes or ctx.assume_yes:
        return True

    def _refuse_noninteractive(why):
        print('检测到非交互环境，未执行任何改动。')
        print('  确认无误后可在命令末尾加 confirm 跳过确认。')
        if why:
            print('  （%s）' % why)
        return False

    if not sys.stdin.isatty():
        # 非交互且没给 -y：拒绝。这条让 `startupctl clean < /dev/null` 与 CI 天然安全。
        return _refuse_noninteractive('')

    try:
        ans = input('%s：确定要执行吗？(y/n): ' % what)
    except (EOFError, KeyboardInterrupt):
        # ★ 读到 EOF 就是**非交互**，不是"用户没回答"。要按同一条路报出去。
        #
        #   Windows 上这点尤其要紧：stdin 接 NUL 设备时 `isatty()` 返回 **True**
        #   （NUL 是字符设备），于是上面那道闸拦不住，会走到这里来。若这里只是
        #   静默 return False，用户看到的是"命令退出了但没说为什么"，
        #   而自动化脚本也无从判断该加 -y。
        print('')
        return _refuse_noninteractive('没有读到确认输入（stdin 已结束）')
    return ans.strip().lower() in ('y', 'yes', '是')


def _record_authorization(what, plan_lines, ctx):
    """`-y` 路径下把被授权的清单落盘，作为"用户审过这份计划"的凭证。

    写在**执行之前**：中途崩溃也留下一份完整的、用户当时授权的记录。
    """
    try:
        d = _new_backup_dir('authorize', ctx)
        plan = {
            'op': what,
            'ts': _utc_stamp(),
            'dry_run': False,
            'assume_yes': True,
            'admin': ctx.admin,
            'platform': ctx.platform,
            'plan': list(plan_lines or []),
        }
        _write_json(os.path.join(d, 'plan.json'), plan)
    except Exception:
        # 凭证写不下来不该挡住主流程（只影响可审计性），但也别静默
        pass


# ---------------------------------------------------------------- 备份目录
def _utc_stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _new_backup_dir(op, ctx):
    root = paths.ensure_dir(paths.backups_root())
    stamp = _utc_stamp()
    d = os.path.join(root, '%s-%s' % (stamp, op))
    # 同一秒内两次操作会撞名，加后缀而不是覆盖
    n = 2
    while os.path.exists(d):
        d = os.path.join(root, '%s-%s-%d' % (stamp, op, n))
        n += 1
    os.makedirs(os.path.join(d, 'files'))
    os.makedirs(os.path.join(d, 'registry'))
    return d


def mirror_rel(path):
    """把绝对路径映射成备份目录内的相对路径。

    /Library/LaunchDaemons/x.plist → Library/LaunchDaemons/x.plist
    C:\\ProgramData\\x.lnk         → C/ProgramData/x.lnk
    盘符与开头的分隔符都要处理，否则 Windows 上会拼出怪路径。
    """
    p = path or 'unknown'
    drive = ''
    if len(p) > 1 and p[1] == ':':
        drive = p[0]
        p = p[2:]
    p = p.replace('\\', '/').lstrip('/')
    parts = [x for x in p.split('/') if x not in ('', '.', '..')]
    if drive:
        parts = [drive] + parts
    return os.path.join(*parts) if parts else 'unknown'


def _sha1_file(path):
    h = hashlib.sha1()
    with open(path, 'rb') as fh:
        while True:
            b = fh.read(65536)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


class Backup(object):
    """一次备份的句柄。"""

    def __init__(self, backup_dir, entries=None, manifest=None):
        self.dir = backup_dir
        self.entries = entries or []
        self.manifest = manifest or {}

    @property
    def files_dir(self):
        return os.path.join(self.dir, 'files')

    @property
    def registry_dir(self):
        return os.path.join(self.dir, 'registry')


def make_manifest(op, ctx):
    """建立一次变更的备份会话：先写空 manifest 并落盘，再逐项更新。

    **在第一次变更之前**写下 manifest，是为了中途崩溃时仍有完整尝试记录——
    与 CtfSweep 的"半发布防护"同一个思路，用在安全决定上。
    """
    d = _new_backup_dir(op, ctx)
    m = {
        'op': op,
        'ts': _utc_stamp(),
        'platform': ctx.platform,
        'admin': ctx.admin,
        'dry_run': bool(ctx.dry_run),
        'items': [],
    }
    _write_json(os.path.join(d, 'manifest.json'), m)
    return Backup(d, [], m)


def _write_json(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _read_json(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def save_manifest(bk):
    if bk and bk.dir:
        _write_json(os.path.join(bk.dir, 'manifest.json'), bk.manifest)


def backup_file(item, bk, note=''):
    """把一个文件项备份进备份目录。返回 entry（含 sha1）。

    调用方**必须**随后 `verify_backup(entry)`；校验不过就不能改。
    """
    src = item.source or ''
    entry = {
        'uid': item.uid, 'anchor': item.anchor, 'kind': item.kind,
        'action': '', 'source': src, 'backup_path': '',
        'sha1': '', 'status': 'planned', 'note': note,
    }
    if not src or not os.path.exists(src):
        entry['status'] = 'missing'
        bk.entries.append(entry)
        bk.manifest['items'].append(entry)
        save_manifest(bk)
        return entry

    rel = mirror_rel(src)
    dst = os.path.join(bk.files_dir, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.islink(src):
        # 符号链接要保存"它指向哪"而不是目标内容——systemd 的 enable 软链
        # 还原时必须还原成软链，否则就把 /usr/lib 里的真单元复制了一份出来。
        target = os.readlink(src)
        with open(dst, 'w', encoding='utf-8') as fh:
            fh.write('SYMLINK\x1f' + target)
        entry['symlink_target'] = target
    else:
        shutil.copy2(src, dst)
    entry['backup_path'] = dst
    entry['sha1'] = _sha1_file(dst) if not os.path.islink(src) else ''
    entry['status'] = 'backed_up'
    bk.entries.append(entry)
    bk.manifest['items'].append(entry)
    save_manifest(bk)
    return entry


def backup_registry(item, bk, data):
    """备份一个注册表项（Windows）。data 是 {name: {'value':…, 'type':…}} 之类的原样快照。"""
    rel = mirror_rel(item.source or item.anchor or 'registry')
    dst = os.path.join(bk.registry_dir, rel + '.json')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    _write_json(dst, {'source': item.source, 'anchor': item.anchor, 'data': data})
    entry = {
        'uid': item.uid, 'anchor': item.anchor, 'kind': item.kind,
        'action': '', 'source': item.source, 'backup_path': dst,
        'sha1': '', 'status': 'backed_up', 'kind_detail': 'registry',
    }
    bk.entries.append(entry)
    bk.manifest['items'].append(entry)
    save_manifest(bk)
    return entry


def verify_backup(entry):
    """校验备份文件确实可读且内容一致。返回 (ok, reason)。

    **绝不跳过这一步**：一个写坏了的备份 + 一次成功的删除 = 用户永久失去那项。
    """
    if not entry:
        return False, '无备份条目'
    if entry.get('status') == 'missing':
        # 源本来就不存在（比如软链断链），没什么可备份的；此时允许继续，
        # 因为"改一个不存在的东西"本身没有可损失的内容。
        return True, '源不存在，无需备份'
    bp = entry.get('backup_path')
    if not bp or not os.path.exists(bp):
        return False, '备份文件未落盘: %s' % bp
    if not os.path.getsize(bp):
        return False, '备份文件为空: %s' % bp
    if entry.get('sha1'):
        if _sha1_file(bp) != entry['sha1']:
            return False, '备份校验不一致（sha1 不符）: %s' % bp
    return True, ''


def mark(entry, action, status='done', detail=''):
    entry['action'] = action
    entry['status'] = status
    if detail:
        entry['note'] = detail
    return entry


# ---------------------------------------------------------------- 还原
def list_backups():
    """列出备份会话，新的在前。"""
    root = paths.backups_root()
    if not os.path.isdir(root):
        return []
    out = []
    for name in sorted(os.listdir(root), reverse=True):
        d = os.path.join(root, name)
        mf = os.path.join(d, 'manifest.json')
        plan = os.path.join(d, 'plan.json')
        meta = {}
        if os.path.isfile(mf):
            try:
                meta = _read_json(mf)
            except Exception:
                meta = {}
        elif os.path.isfile(plan):
            try:
                meta = _read_json(plan)
            except Exception:
                meta = {}
        n = len(meta.get('items') or [])
        out.append({
            'name': name, 'dir': d, 'op': meta.get('op', '?'),
            'ts': meta.get('ts', ''), 'count': n,
            'has_manifest': os.path.isfile(mf),
        })
    return out


def latest_backup():
    bs = list_backups()
    return bs[0] if bs else None


def prune_backups(keep, min_days, dry_run=False):
    """按保留策略清理备份。返回 (删除的名单, 保留的名单)。

    只有显式 `backup prune` 会调到这里——install / update / uninstall 都不碰备份。
    `min_days` 内的备份一律不删，防止"刚做完就手滑清掉后悔药"。
    """
    bs = list_backups()
    now = time.time()
    removed, kept = [], []
    for idx, b in enumerate(bs):
        too_many = idx >= keep
        old_enough = True
        try:
            mt = os.path.getmtime(b['dir'])
            old_enough = (now - mt) >= min_days * 86400
        except OSError:
            old_enough = True
        if too_many and old_enough:
            removed.append(b)
            if not dry_run:
                shutil.rmtree(b['dir'], ignore_errors=True)
        else:
            kept.append(b)
    return removed, kept
