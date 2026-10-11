# -*- coding: utf-8 -*-
"""判断核（judge）：轻量本地"判断网络"——对扫描候选做答案相关性打分。

设计：
- 纯 Python 手写 MLP（默认 28 维特征 → 16 → 8 → 1，约 600 个参数），零依赖；
- 特征 = 候选自身统计 + 源文件上下文（前一字符、空白密度等），现场可算；
- 训练数据 = 本机积累的解题标注 dataset.jsonl（候选 + 真/假标签）；
- 留一组评估（leave-one-group-out）：每组轮流当测试集，评估泛化后再全量重训；
- 权重为 JSON（约 8KB），完全离线；**无模型时工具行为与之前完全一致**。

CLI:
    ctfsweep train [--data F] [--model-out F] [--epochs N]
    ctfsweep <文件> --judge        # 扫描时给出 p= 分与【判断核·重点候选】
"""
import hashlib
import json
import math
import os
import random

# ---------------------------------------------------------------- 特征
FEATURES = (
    'score',
    'kind_flag', 'kind_decode', 'kind_frag_open', 'kind_frag_close', 'kind_keyword',
    'kind_jwt', 'kind_echo', 'kind_dns', 'kind_other',
    'val_len', 'brace_open', 'brace_close', 'brace_pair',
    'digit_ratio', 'alpha_ratio', 'upper_ratio', 'hex_ratio',
    'entropy', 'space_density', 'colon_density', 'slash_density',
    'prev_space', 'prev_dotslash', 'ctx_ws', 'ctx_printable',
    'file_capture', 'file_raw',
)

_KNOWN_KINDS = ('明文flag', 'hex', 'base64', '片段(前)', '片段(尾)', '关键词',
                'JWT', '命令回显', '环境/配置', '短文本响应', 'DNS查询',
                '加壳候选', '明文')


def normalize_val(val):
    if isinstance(val, bytes):
        val = val.decode('utf-8', 'replace')
    return ' '.join(str(val).split())


def sample_key(kind, val):
    return hashlib.sha1(('%s|%s' % (kind, normalize_val(val)[:120])).encode('utf-8', 'replace')).hexdigest()[:16]


def _entropy(s):
    if not s:
        return 0.0
    cnt = {}
    for c in s:
        cnt[c] = cnt.get(c, 0) + 1
    n = float(len(s))
    return -sum((v / n) * math.log(v / n, 2) for v in cnt.values())


def _win_stats(buf, i, ln):
    prev = buf[i - 1:i] if i else b''
    lo = max(0, i - 40)
    hi = min(len(buf), i + ln + 40)
    ws = 0
    for j in range(lo, hi):
        if buf[j] in (32, 9, 13, 10):
            ws += 1
    plo = max(0, i - 30)
    phi = min(len(buf), i + ln + 40)
    pr_win = buf[plo:phi]
    pr = sum(32 <= c < 127 or c in (9, 10, 13) for c in pr_win) / max(1, len(pr_win))
    return {'prev_space': 1.0 if prev == b' ' else 0.0,
            'prev_dotslash': 1.0 if prev and prev[0:1] in (b'.', b'\\', b'/') else 0.0,
            'ctx_ws': min(1.0, ws / 8.0),
            'ctx_printable': pr,
            'found': 1.0}


class ContextFinder:
    """在源文件字节中定位候选并提取上下文统计（紧凑视图惰性缓存）。"""

    def __init__(self, data):
        self.data = data or b''
        self._compact = None

    def _compact_view(self):
        if self._compact is None:
            self._compact = self.data.replace(b'\x00', b'')
        return self._compact

    def stats(self, needles):
        if not self.data:
            return {}
        for needle in needles:
            if not needle:
                continue
            ns = needle if isinstance(needle, str) else needle.decode('utf-8', 'replace')
            encs = []
            for enc in ('utf-8', 'latin-1'):
                try:
                    encs.append(ns.encode(enc))
                except Exception:
                    pass
            b16 = ns.encode('utf-16-le', 'ignore')
            for view, buf in (('raw', self.data), ('compact', None)):
                if view == 'compact':
                    buf = self._compact_view()
                for b in encs:
                    i = buf.find(b)
                    if i >= 0:
                        return _win_stats(buf, i, len(b))
                i = buf.find(b16)
                if i >= 0:
                    return _win_stats(buf, i, len(b16))
        return {}


def extract_features(sample):
    """从候选样例提取特征向量（与 FEATURES 等长）。

    sample 键：score / kind / val / tok(可选) / file_type('capture'|'raw')
              上下文来源三选一：ctx(显式 dict) > finder(ContextFinder) > data(bytes)
    """
    val = sample.get('val') or ''
    if isinstance(val, bytes):
        val = val.decode('utf-8', 'replace')
    val = str(val)
    kind = str(sample.get('kind') or '')
    try:
        score = float(sample.get('score') or 0.0)
    except Exception:
        score = 0.0
    ftype = str(sample.get('file_type') or '')

    ctx = sample.get('ctx')
    if ctx is None:
        finder = sample.get('finder')
        if finder is None:
            data = sample.get('data')
            finder = ContextFinder(data) if data else None
        needles = []
        if kind in ('hex', 'base64') and sample.get('tok'):
            tok = sample['tok']
            needles.append(tok if isinstance(tok, str) else tok.decode('utf-8', 'replace'))
        needles.append(val)
        ctx = finder.stats(needles) if finder is not None else {}

    v = normalize_val(val)
    n = max(1, len(v))
    digits = sum(c.isdigit() for c in v) / float(n)
    alpha = sum(1 for c in v if c.isascii() and c.isalpha()) / float(n)
    upper = sum(1 for c in v if c.isascii() and c.isupper()) / float(n)
    hexr = sum(1 for c in v if c in '0123456789abcdefABCDEF') / float(n)
    ent = min(1.0, _entropy(v) / 6.0)
    kinds = {
        'kind_flag': kind == '明文flag',
        'kind_decode': kind in ('hex', 'base64'),
        'kind_frag_open': kind == '片段(前)',
        'kind_frag_close': kind == '片段(尾)',
        'kind_keyword': kind == '关键词',
        'kind_jwt': kind == 'JWT',
        'kind_echo': kind in ('命令回显', '环境/配置', '短文本响应'),
        'kind_dns': kind == 'DNS查询',
        'kind_other': bool(kind) and kind not in _KNOWN_KINDS,
    }
    feats = [
        score,
        kinds['kind_flag'], kinds['kind_decode'], kinds['kind_frag_open'],
        kinds['kind_frag_close'], kinds['kind_keyword'], kinds['kind_jwt'],
        kinds['kind_echo'], kinds['kind_dns'], kinds['kind_other'],
        min(1.0, len(v) / 120.0),
        1.0 if '{' in v else 0.0,
        1.0 if '}' in v else 0.0,
        1.0 if ('{' in v and '}' in v) else 0.0,
        digits, alpha, upper, hexr, ent,
        min(1.0, v.count(' ') / 16.0),
        min(1.0, v.count(':') / 4.0),
        min(1.0, (v.count('/') + v.count('\\')) / 4.0),
        float(ctx.get('prev_space', 0.0)),
        float(ctx.get('prev_dotslash', 0.0)),
        float(ctx.get('ctx_ws', 0.0)),
        float(ctx.get('ctx_printable', 0.0)),
        1.0 if ftype == 'capture' else 0.0,
        1.0 if ftype == 'raw' else 0.0,
    ]
    return feats


# ---------------------------------------------------------------- 网络
class JudgeNet:
    """纯 Python MLP：全连接 + ReLU 隐层 + Sigmoid 输出，SGD(momentum) 训练。"""

    def __init__(self, sizes=None, seed=42):
        self.sizes = list(sizes) if sizes else [len(FEATURES), 16, 8, 1]
        rnd = random.Random(seed)
        self.W, self.b = [], []
        for li in range(len(self.sizes) - 1):
            fi, fo = self.sizes[li], self.sizes[li + 1]
            scale = math.sqrt(2.0 / fi)
            self.W.append([[rnd.gauss(0.0, scale) for _ in range(fi)] for _ in range(fo)])
            self.b.append([0.0] * fo)
        self._zs, self._acts = [], []

    @staticmethod
    def _sig(x):
        return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))

    def forward(self, x):
        a = [float(v) for v in x]
        self._zs, self._acts = [], [a]
        L = len(self.W)
        for li in range(L):
            z = []
            W, b = self.W[li], self.b[li]
            for row, bi in zip(W, b):
                s = bi
                for w, xj in zip(row, a):
                    s += w * xj
                z.append(s)
            self._zs.append(z)
            a = [self._sig(v) for v in z] if li == L - 1 else [(v if v > 0.0 else 0.0) for v in z]
            self._acts.append(a)
        return a[0]

    def predict(self, x):
        return self.forward(x)

    def train(self, X, y, epochs=300, lr=0.5, l2=0.0, mu=0.9, seed=13):
        """全批量梯度下降（对小样本最稳，且训练是确定性的）。

        逐样本 SGD 在小数据集上会被样本间的对抗梯度带进死区（ReLU 全灭）；
        全批量先把整个数据集的梯度加和后更新一次，方向稳定、结果可复现。
        """
        L = len(self.W)
        VW = [[[0.0] * len(r) for r in m] for m in self.W]
        Vb = [[0.0] * len(r) for r in self.b]
        n = max(1, len(X))
        losses = []
        for _ep in range(max(1, epochs)):
            gW = [[[0.0] * len(r) for r in m] for m in self.W]
            gb = [[0.0] * len(r) for r in self.b]
            tot = 0.0
            for xi, yi in zip(X, y):
                p = self.forward(xi)
                pc = min(1.0 - 1e-7, max(1e-7, p))
                tot += -(yi * math.log(pc) + (1.0 - yi) * math.log(1.0 - pc))
                ds = [None] * L
                ds[L - 1] = [p - yi]
                for li in range(L - 2, -1, -1):
                    nxt = ds[li + 1]
                    Wn = self.W[li + 1]
                    z = self._zs[li]
                    d = []
                    for j in range(len(self.W[li])):
                        s = 0.0
                        for k in range(len(nxt)):
                            s += Wn[k][j] * nxt[k]
                        d.append(s if z[j] > 0.0 else 0.0)
                    ds[li] = d
                for li in range(L):
                    a0 = self._acts[li]
                    for i in range(len(self.W[li])):
                        g = ds[li][i]
                        gi = gW[li][i]
                        for j in range(len(a0)):
                            gi[j] += g * a0[j]
                        gb[li][i] += g
            for li in range(L):
                for i in range(len(self.W[li])):
                    Wrow = self.W[li][i]
                    Vrow = VW[li][i]
                    grow = gW[li][i]
                    for j in range(len(Wrow)):
                        gr = grow[j] / n + (l2 * Wrow[j] if l2 else 0.0)
                        Vrow[j] = mu * Vrow[j] - lr * gr
                        Wrow[j] += Vrow[j]
                    vb = Vb[li]
                    vb[i] = mu * vb[i] - lr * (gb[li][i] / n)
                    self.b[li][i] += vb[i]
            losses.append(tot / n)
        return losses

    def save(self, path, meta=None):
        d = {'v': 1, 'sizes': self.sizes, 'features': list(FEATURES),
             'W': self.W, 'b': self.b, 'meta': meta or {}}
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)
        return path

    @classmethod
    def load(cls, path):
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        if d.get('features') and list(d['features']) != list(FEATURES):
            raise ValueError('模型特征版本不一致（请重新 ctfsweep train）')
        net = cls.__new__(cls)
        net.sizes = list(d['sizes'])
        net.W = d['W']
        net.b = d['b']
        net._zs, net._acts = [], []
        return net


def param_count(sizes):
    return sum(sizes[i] * sizes[i + 1] + sizes[i + 1] for i in range(len(sizes) - 1))


# ---------------------------------------------------------------- 数据 / 评估
def user_dir():
    """判断核用户数据目录（数据集/模型）。

    放在 ~/.config/ctfsweep/judge/ —— 刻意独立于 devtools 安装目录：
    安装/update/卸载都不会触碰这里，训练数据（用户的解题标注）不会丢。
    """
    return os.path.join(os.path.expanduser('~'), '.config', 'ctfsweep', 'judge')


def default_dataset_path():
    return os.path.join(user_dir(), 'dataset.jsonl')


def model_path():
    env = os.environ.get('CTFSWEEP_JUDGE_MODEL')
    if env:
        return env
    return os.path.join(user_dir(), 'model.json')


def load_rows(path):
    rows = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def rows_to_xy(rows):
    X, y = [], []
    for r in rows:
        feats = r.get('feats')
        if not feats:
            continue
        X.append([float(v) for v in feats])
        y.append(1.0 if float(r.get('label') or 0) >= 0.5 else 0.0)
    return X, y


def predict_finding(net, finding, finder, file_type):
    """finding 为扫描器输出元组 (score, kind, tok, val, loc)。"""
    score, kind, tok, val, _loc = finding
    sample = {'score': score, 'kind': kind, 'tok': tok, 'val': val,
              'finder': finder, 'file_type': file_type}
    return net.predict(extract_features(sample))


def _mean(xs):
    return (sum(xs) / len(xs)) if xs else None


def _auc(ps, ys):
    pos = [p for p, y in zip(ps, ys) if y >= 0.5]
    neg = [p for p, y in zip(ps, ys) if y < 0.5]
    if not pos or not neg:
        return None
    wins = 0.0
    for a in pos:
        for b in neg:
            if a > b:
                wins += 1.0
            elif a == b:
                wins += 0.5
    return wins / (len(pos) * len(neg))


def _fmt(v):
    return ('%.2f' % v) if v is not None else '—'


DEFAULT_SEEDS = (1, 7, 13, 42, 2026)


class JudgePredictor:
    """判断核预测器：单模型或多模型集成（对成员预测取平均）。

    - 集成显著降低小样本下随机初始化的方差（实测：28→10→1 单模型 AUC 随种子
      波动大，5 种子集成后稳定在 0.92+）；
    - 保存格式 v2 = 全部成员权重 + 元信息；兼容读取 v1 单模型文件。
    """

    def __init__(self, nets, meta=None):
        self.nets = list(nets)
        self.meta = meta or {}

    @property
    def sizes(self):
        return self.nets[0].sizes

    def predict(self, x):
        if len(self.nets) == 1:
            return self.nets[0].predict(x)
        return sum(n.predict(x) for n in self.nets) / len(self.nets)

    def describe(self):
        base = ' → '.join(str(s) for s in self.sizes)
        if len(self.nets) == 1:
            return '单模型 (%s)，%d 参数' % (base, param_count(self.sizes))
        return '集成 %d × (%s)，%d 参数' % (len(self.nets), base,
                                          param_count(self.sizes) * len(self.nets))

    def save(self, path, meta=None):
        d = {'v': 2, 'features': list(FEATURES), 'sizes': self.sizes,
             'members': [{'W': n.W, 'b': n.b} for n in self.nets],
             'meta': meta if meta is not None else self.meta}
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)
        return path

    @classmethod
    def load(cls, path):
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        if d.get('features') and list(d['features']) != list(FEATURES):
            raise ValueError('模型特征版本不一致（请重新 ctfsweep train）')
        if d.get('v') == 2:
            nets = []
            for m in d.get('members', []):
                net = JudgeNet.__new__(JudgeNet)
                net.sizes = list(d['sizes'])
                net.W = m['W']
                net.b = m['b']
                net._zs, net._acts = [], []
                nets.append(net)
            return cls(nets, d.get('meta'))
        net = JudgeNet.__new__(JudgeNet)
        net.sizes = list(d['sizes'])
        net.W = d['W']
        net.b = d['b']
        net._zs, net._acts = [], []
        return cls([net], d.get('meta'))


def run_training(rows, model_out=None, epochs=300, lr=0.5, l2=0.0,
                 seeds=DEFAULT_SEEDS, sizes=None):
    """留一组评估（集成） + 全量重训（集成） + 保存。返回 (predictor, info)。"""
    seeds = list(seeds) if seeds else [13]
    sizes = list(sizes) if sizes else [len(FEATURES), 10, 1]
    n_pos = sum(1 for r in rows if float(r.get('label') or 0) >= 0.5)
    n_neg = len(rows) - n_pos
    groups = []
    for r in rows:
        g = str(r.get('group') or r.get('file') or '?')
        if g not in groups:
            groups.append(g)
    print('判断核训练')
    print('  样本: %d 条（正 %d / 负 %d）· 组 %d 个: %s'
          % (len(rows), n_pos, n_neg, len(groups), ', '.join(groups[:10])))
    print('  网络: 集成 %d × (%s)（%d 参数，纯 Python）'
          % (len(seeds), ' → '.join(str(s) for s in sizes),
             param_count(sizes) * len(seeds)))

    def _fit(X, y):
        nets = []
        for sd in seeds:
            net = JudgeNet(sizes, seed=sd)
            net.train(X, y, epochs=epochs, lr=lr, l2=l2)
            nets.append(net)
        return JudgePredictor(nets)

    pooled_p, pooled_y = [], []
    if len(groups) >= 2:
        print('')
        print('留一组评估（每组轮流当测试集，集成为多模型平均）:')
        for g in groups[:12]:
            train_rows = [r for r in rows if str(r.get('group') or r.get('file') or '?') != g]
            test_rows = [r for r in rows if str(r.get('group') or r.get('file') or '?') == g]
            Xtr, ytr = rows_to_xy(train_rows)
            Xte, yte = rows_to_xy(test_rows)
            if not Xtr or not Xte:
                continue
            pred = _fit(Xtr, ytr)
            ps = [pred.predict(x) for x in Xte]
            auc = _auc(ps, yte)
            mp = _mean([p for p, y in zip(ps, yte) if y >= 0.5])
            mn = _mean([p for p, y in zip(ps, yte) if y < 0.5])
            pooled_p.extend(ps)
            pooled_y.extend(yte)
            print('  %-9s n=%-4d 正 %-3d / 负 %-3d   AUC %s   均值 正 %s / 负 %s'
                  % (g[:9], len(yte), sum(1 for y in yte if y >= 0.5),
                     sum(1 for y in yte if y < 0.5), _fmt(auc), _fmt(mp), _fmt(mn)))
        overall = _auc(pooled_p, pooled_y)
        print('  汇总 AUC（池化）: %s' % _fmt(overall))
    else:
        print('')
        print('  （样本分组不足 2 个，跳过留一组评估）')
        overall = None

    X, y = rows_to_xy(rows)
    pred = _fit(X, y)
    info = {'n': len(rows), 'n_pos': n_pos, 'n_neg': n_neg, 'groups': groups,
            'auc': overall, 'params': param_count(sizes) * len(seeds), 'epochs': epochs,
            'seeds': seeds, 'sizes': sizes}
    if model_out:
        pred.save(model_out, meta={'n': len(rows), 'auc': overall, 'epochs': epochs,
                                   'seeds': seeds})
        print('')
        print('已保存模型: %s（%s）' % (model_out, pred.describe()))
    return pred, info
