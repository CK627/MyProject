#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判断核离线训练（仓库内实验脚本，**不随安装提供**）。

运行时工具只做推理打分（`ctfsweep <文件> --judge`），模型随版本发布；
训练/数据构建整体留在这里，装到本机后命令行看不到任何训练入口。

用法:
  python3 lab/train.py                                  # 默认 lab/dataset.jsonl → models/model.ctfj
  python3 lab/train.py --data lab/dataset.jsonl --out models/model.ctfj [--epochs N]
  python3 lab/train.py --config lab/train_config.json   # 覆盖训练超参（网络结构/学习率/种子）

超参数默认读 models/train_config.json（随版本发布；不存在则生成默认值并回写）；
优先级：命令行 > 训练配置 > 内置默认。
留一组评估（leave-one-group-out）+ 全量重训 + 保存 .ctfj，与历史口径一致。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ctfsweep.core import model_io  # noqa: E402
from ctfsweep.core.judge import (  # noqa: E402
    FEATURES, JudgeNet, JudgePredictor, models_dir, param_count,
)

DEFAULT_DATA = os.path.join(ROOT, 'lab', 'dataset.jsonl')
DEFAULT_MODEL = os.path.join(ROOT, 'models', 'model.ctfj')


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
    """样本行 → (X, y)。特征版本不符的样本静默跳过（防旧版数据污染训练）。"""
    X, y = [], []
    for r in rows:
        feats = r.get('feats')
        if not feats:
            continue
        if len(feats) != len(FEATURES):
            continue
        X.append([float(v) for v in feats])
        y.append(1.0 if float(r.get('label') or 0) >= 0.5 else 0.0)
    return X, y


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


# ================================================================= 训练配置（独立于代码）
# 训练超参数集中放配置文件（models/train_config.json），
# 调整模型结构 / 学习率 / 种子 / 训练轮数等**无需修改代码**：
#   · 编辑该文件后重跑 lab/train.py 生效；
#   · 删除该文件会重新生成默认配置；
#   · 优先级：命令行参数 > 配置文件 > 内置默认。
DEFAULT_TRAIN_CONFIG = {
    'sizes': [len(FEATURES), 32, 16, 1],   # 网络层结构
    'seeds': list(DEFAULT_SEEDS),          # 集成种子（每种子一个成员）
    'lr': 0.1,                             # 学习率
    'l2': 0.0,                             # L2 正则
    'mu': 0.9,                             # 动量
    'epochs_per_run': 200,                 # 每轮训练 epochs
    'max_epochs': 500,                     # 最大累计 epochs
    'min_auc': 0.85,                       # 收敛目标 AUC
    'min_samples': 16,                     # 最低样本数
}


def train_config_path():
    """训练配置文件路径（项目内 models/train_config.json，随项目版本管理）。

    环境变量 CTFSWEEP_TRAIN_CONFIG 可显式指定（测试隔离用）。
    """
    env = os.environ.get('CTFSWEEP_TRAIN_CONFIG')
    if env:
        return env
    return os.path.join(models_dir(), 'train_config.json')


def load_train_config():
    """读取训练配置：修改超参数（网络结构/学习率/种子/轮数）无需改代码。

    · 文件不存在 → 生成默认配置并返回默认值；
    · 缺失键自动回退默认值（兼容旧版配置文件）；
    · 优先级：配置文件 > 内置默认。
    """
    cfg = dict(DEFAULT_TRAIN_CONFIG)
    path = train_config_path()
    if os.path.isfile(path):
        try:
            with open(path, encoding='utf-8') as f:
                user_cfg = json.load(f)
            if isinstance(user_cfg, dict):
                cfg.update({k: v for k, v in user_cfg.items() if k in cfg})
        except Exception as ex:
            print('训练配置读取失败（使用默认值）: %r' % ex)
    else:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            print('训练配置: %s（首次生成默认配置；调整参数直接编辑此文件，无需改代码）' % path)
        except Exception:
            pass
    # 空值回退
    if not cfg.get('sizes'):
        cfg['sizes'] = [len(FEATURES), 32, 16, 1]
    if not cfg.get('seeds'):
        cfg['seeds'] = list(DEFAULT_SEEDS)
    return cfg


def run_training(rows, model_out=None, epochs=None, lr=None, l2=None, mu=None,
                 seeds=None, sizes=None, config=None):
    """留一组评估（集成） + 全量重训（集成） + 保存。返回 (predictor, info)。

    超参数默认读取训练配置（models/train_config.json）；
    显式传参可覆盖（命令行参数 > 配置文件 > 内置默认）。
    """
    cfg = config or load_train_config()
    epochs = epochs if epochs is not None else cfg['epochs_per_run']
    lr = lr if lr is not None else cfg['lr']
    l2 = l2 if l2 is not None else cfg['l2']
    mu = mu if mu is not None else cfg['mu']
    seeds = list(seeds) if seeds else list(cfg['seeds'])
    sizes = list(sizes) if sizes else list(cfg['sizes'])
    n_pos = sum(1 for r in rows if float(r.get('label') or 0) >= 0.5)
    n_neg = len(rows) - n_pos
    n_stale = sum(1 for r in rows if len(r.get('feats') or []) != len(FEATURES))
    groups = []
    for r in rows:
        g = str(r.get('group') or r.get('file') or '?')
        if g not in groups:
            groups.append(g)
    print('判断核训练')
    print('  样本: %d 条（正 %d / 负 %d）· 组 %d 个: %s'
          % (len(rows), n_pos, n_neg, len(groups), ', '.join(groups[:10])))
    if n_stale:
        print('  [警告] %d 条样本特征版本不符（当前 %d 维），本次训练将跳过它们'
              % (n_stale, len(FEATURES)))
    print('  网络: 集成 %d × (%s)（%d 参数，纯 Python）'
          % (len(seeds), ' → '.join(str(s) for s in sizes),
             param_count(sizes) * len(seeds)))

    def _fit(X, y):
        nets = []
        for sd in seeds:
            net = JudgeNet(sizes, seed=sd)
            net.train(X, y, epochs=epochs, lr=lr, l2=l2, mu=mu)
            nets.append(net)
        return JudgePredictor(nets)

    pooled_p, pooled_y = [], []
    if len(groups) >= 2:
        print('')
        print('留一组评估（每组轮流当测试集，集成为多模型平均）:')
        g_aucs = []
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
            if auc is not None:
                g_aucs.append(auc)
            mp = _mean([p for p, y in zip(ps, yte) if y >= 0.5])
            mn = _mean([p for p, y in zip(ps, yte) if y < 0.5])
            pooled_p.extend(ps)
            pooled_y.extend(yte)
            print('  %-9s n=%-4d 正 %-3d / 负 %-3d   AUC %s   均值 正 %s / 负 %s'
                  % (g[:9], len(yte), sum(1 for y in yte if y >= 0.5),
                     sum(1 for y in yte if y < 0.5), _fmt(auc), _fmt(mp), _fmt(mn)))
        overall = _auc(pooled_p, pooled_y)
        if g_aucs:
            macro = sum(g_aucs) / len(g_aucs)
            print('  组内 AUC 均值: %s（%d 组可评估）—— 【实用指标】实际使用为组内排序（同一题候选排队）'
                  % (_fmt(macro), len(g_aucs)))
        print('  汇总 AUC（池化，仅供参考；组间分数尺度不同，偏低属正常）: %s' % _fmt(overall))
    else:
        print('')
        print('  （样本分组不足 2 个，跳过留一组评估）')
        overall = None

    X, y = rows_to_xy(rows)
    pred = _fit(X, y)
    info = {'n': len(rows), 'n_pos': n_pos, 'n_neg': n_neg, 'groups': groups,
            'auc': overall, 'params': param_count(sizes) * len(seeds), 'epochs': epochs,
            'seeds': seeds, 'sizes': sizes, 'lr': lr, 'mu': mu, 'l2': l2}
    if model_out:
        model_io.save_binary(pred, model_out)
        print('')
        print('已保存模型: %s（%s）' % (model_out, pred.describe()))
    return pred, info


def main():
    ap = argparse.ArgumentParser(description='判断核离线训练（仓库实验脚本）')
    ap.add_argument('--data', default=DEFAULT_DATA, help='训练语料 jsonl（默认 lab/dataset.jsonl）')
    ap.add_argument('--out', '--model-out', dest='out', default=DEFAULT_MODEL,
                    help='模型输出路径（默认 models/model.ctfj）')
    ap.add_argument('--epochs', type=int, default=None, help='每轮 epochs（覆盖训练配置）')
    ap.add_argument('--config', default=None, help='训练配置 json（默认 models/train_config.json）')
    args = ap.parse_args()

    if not os.path.isfile(args.data):
        print('未找到训练语料: %s' % args.data)
        print('提示: 先跑 lab/build_dataset.py 从题库构建，或用 lab/data_generator.py 合成。')
        return 2
    rows = load_rows(args.data)
    if len(rows) < 8:
        print('样本太少（%d 条），至少需要 8 条标注样本。' % len(rows))
        return 2
    cfg = None
    if args.config:
        os.environ['CTFSWEEP_TRAIN_CONFIG'] = args.config
    else:
        cfg = load_train_config()
    run_training(rows, model_out=args.out, epochs=args.epochs, config=cfg)
    return 0


if __name__ == '__main__':
    sys.exit(main())
