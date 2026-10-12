# -*- coding: utf-8 -*-
"""像素数据 → PNG 图像还原工具（CTF misc 常见题型）。

用法:
    python3 pixels_to_png.py <数据文件> <输出.png> [--width N] [--scale K]
    python3 pixels_to_png.py <数据文件> <输出.png> --auto     # 自动宽度检测（推荐）
    python3 pixels_to_png.py <数据文件> <输出.png> --width 111 --rot90ccw --flip

输入数据格式：每行 "R, G, B"（或空格/逗号分隔的 3 个 0-255 数值）。
- --auto: 枚举因子候选宽度并打分（列错位越小、笔画连通性越好分越高），
  输出 top3 候选 PNG 供人工挑选。**关键经验：宽度差 1 像素会制造"文字
  斜排/波浪"的假象**（每行错位 1px ≈ 1px/行 的漂移）——先怀疑宽度。
- --rot90cw / --rot90ccw / --flip: 方向修正（旋转后镜像的组合能救回
  "镜像旋转"存储的图）。
- 纯标准库实现（zlib + struct 手写 PNG），无需 PIL。
"""
import argparse
import math
import re
import struct
import sys
import zlib


def load_pixels(path):
    rows = []
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            parts = re.findall(r'\d+', line.strip())
            if len(parts) >= 3:
                rows.append((int(parts[0]), int(parts[1]), int(parts[2])))
    return rows


def make_png(w, h, get_black, outpath):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw += b'\x00\x00\x00' if get_black(x, y) else b'\xff\xff\xff'

    def chunk(typ, data):
        c = struct.pack('>I', len(data)) + typ + data
        c += struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff)
        return c
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 6))
    png += chunk(b'IEND', b'')
    with open(outpath, 'wb') as f:
        f.write(png)
    print('已生成: %s (%dx%d)' % (outpath, w, h))


def divisor_candidates(n, lo=8, hi=2000):
    cands = []
    for w in range(lo, hi + 1):
        if n % w == 0:
            h = n // w
            if h >= lo:
                cands.append(w)
    return cands


def score_width(px, W, thr):
    """候选宽度打分：列错位漂移越小 + 笔画横向连通性越好 → 分越高。"""
    H = len(px) // W
    if H < 4:
        return -1.0

    def black(i):
        r, g, b = px[i]
        return r < thr or g < thr or b < thr

    # 每行黑色像素重心（只有非空行参与）
    drift, cnt, prev = 0.0, 0, None
    for y in range(H):
        xs = [x for x in range(W) if black(y * W + x)]
        if xs:
            c = sum(xs) / float(len(xs))
            if prev is not None:
                drift += abs(c - prev)
                cnt += 1
            prev = c
    if cnt == 0:
        return -1.0
    mean_drift = drift / cnt

    # 横向 run 的均方长度（正确宽度笔画连续，run 更长）
    sq, tot = 0.0, 0
    for y in range(H):
        run = 0
        base = y * W
        for x in range(W):
            if black(base + x):
                run += 1
            else:
                if run:
                    sq += float(run * run)
                    tot += run
                    run = 0
        if run:
            sq += float(run * run)
            tot += run
    mean_sq_run = sq / max(tot, 1)
    return mean_sq_run / (1.0 + mean_drift)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('out')
    ap.add_argument('--width', type=int, default=None)
    ap.add_argument('--auto', action='store_true', help='自动枚举因子宽度并输出 top3')
    ap.add_argument('--scale', type=int, default=1)
    ap.add_argument('--rotate', type=float, default=0)
    ap.add_argument('--rot90cw', action='store_true')
    ap.add_argument('--rot90ccw', action='store_true')
    ap.add_argument('--flip', action='store_true', help='水平镜像')
    ap.add_argument('--threshold', type=int, default=200)
    args = ap.parse_args()

    px = load_pixels(args.data)
    if not px:
        print('未读到像素数据')
        return 1
    print('像素总数: %d' % len(px))

    def is_black(i):
        if i >= len(px):
            return False
        r, g, b = px[i]
        return r < args.threshold or g < args.threshold or b < args.threshold

    def render_one(W, outpath):
        H = (len(px) + W - 1) // W
        # 基础矩阵
        m = [[1 if is_black(y * W + x) and (y * W + x) < len(px) else 0
              for x in range(W)] for y in range(H)]

        # 旋转（先 90° 快捷，后任意角）
        if args.rot90cw:
            m = [[m[H - 1 - x][y] for x in range(H)] for y in range(W)]
        elif args.rot90ccw:
            m = [[m[x][W - 1 - y] for x in range(H)] for y in range(W)]
        if args.flip:
            m = [row[::-1] for row in m]

        MH, MW = len(m), len(m[0])

        if args.rotate:
            ang = math.radians(args.rotate)
            cos, sin = math.cos(ang), math.sin(ang)
            rw = int(abs(MW * cos) + abs(MH * sin)) + 2
            rh = int(abs(MW * sin) + abs(MH * cos)) + 2
            w2, h2 = rw * args.scale, rh * args.scale

            def get_black(x2, y2):
                dx = x2 / args.scale - rw / 2.0
                dy = y2 / args.scale - rh / 2.0
                x = cos * dx + sin * dy + MW / 2.0
                y = -sin * dx + cos * dy + MH / 2.0
                xi, yi = int(x), int(y)
                if 0 <= xi < MW and 0 <= yi < MH:
                    return m[yi][xi]
                return 0
            make_png(w2, h2, get_black, outpath)
        else:
            w2, h2 = MW * args.scale, MH * args.scale

            def get_black(x2, y2):
                return m[y2 // args.scale][x2 // args.scale]
            make_png(w2, h2, get_black, outpath)

    if args.auto and not args.width:
        cands = divisor_candidates(len(px))
        if not cands:
            print('无因子候选，回退 isqrt 宽度')
            W = int(math.isqrt(len(px))) or 1
            render_one(W, args.out)
            return 0
        scored = sorted(((score_width(px, W, args.threshold), W) for W in cands),
                        reverse=True)
        print('候选宽度评分（从高到低）:')
        for s, W in scored[:8]:
            print('  W=%-5d 得分 %.3f  (%dx%d)' % (W, s, W, len(px) // W))
        top = [W for _s, W in scored[:3]]
        for rank, W in enumerate(top, 1):
            out = args.out if rank == 1 else '%s_w%d.png' % (
                args.out.rsplit('.', 1)[0], W)
            print('--- 渲染候选 #%d ---' % rank)
            render_one(W, out)
        return 0

    W = args.width or int(math.isqrt(len(px))) or 1
    render_one(W, args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
