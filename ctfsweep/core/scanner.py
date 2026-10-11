# -*- coding: utf-8 -*-
"""扫描编排：抓包扫描（scan_capture）与原始文件扫描（scan_rawfile）"""
import io
import os
import zipfile

from .blobscan import add, scan_blob
from .capture import LINKNAMES, dns_qname, l4_parse, load_packets
from .decode import decode_chain, flagify, fragments
from .extract import PWD_POOL, carve_files, collect_pwds_from_blob, extract_scan
from .http import build_http_transactions, http_summary, jwt_summary
from .utils import (FLAG_RE, JWT_RE, SECRET_LINE_RE, SENSITIVE_NAME_RE,
                    decode_score, kw_boundary_ok, printable_ratio, try_b64, ts_str)


def scan_capture(data, keywords, do_decode, depth, extract=None):
    fmt, pkts = load_packets(data)
    lts = sorted(set(lt for _n, lt, _p, _t in pkts))
    lt_names = ', '.join(str(LINKNAMES.get(lt, lt)) for lt in lts[:4])
    print('  格式: %s  链路类型: %s   数据包: %d 个' % (fmt, lt_names, len(pkts)))
    findings, seen = [], set()
    tcp_streams, udp_payloads = {}, []
    http_reqs, form_fields = [], []
    for num, lt, pkt, ts in pkts:
        r = l4_parse(lt, pkt)
        if not r:
            continue
        proto, src, dst, sport, dport, payload = r
        if not payload:
            continue
        locp = '%s:%d->%s:%d 包#%d' % (src, sport, dst, dport, num)
        if proto == 'tcp':
            tcp_streams.setdefault((src, sport, dst, dport), []).append((num, ts, payload))
            add_loc = locp
            for m in FLAG_RE.finditer(payload):
                add((0.97, '明文flag', b'', m.group(0), add_loc), findings, seen)
            fragments(payload, keywords, findings, seen, add_loc)
            if do_decode:
                hits = []
                decode_chain(payload, keywords, depth, hits, seen)
                for score, name, tok, dec in hits:
                    findings.append((score, name, tok, dec, add_loc))
        else:
            udp_payloads.append((num, src, sport, dst, dport, payload))

    dns_seen = set()
    for num, src, sport, dst, dport, payload in udp_payloads:
        if 53 not in (sport, dport):
            continue
        q = dns_qname(payload)
        if not q or q in dns_seen:
            continue
        dns_seen.add(q)
        add((0.45, 'DNS查询', b'', q, '%s -> %s' % (src, dst)), findings, seen)
        for label in q.split(b'.'):
            if len(label) >= 12:
                dec = try_b64(label)
                if dec and printable_ratio(dec) > 0.8 and (b'{' in dec or any(k.encode() in dec.lower() for k in keywords)):
                    add((decode_score(dec, keywords), 'base64', label, dec, 'DNS子域名 %s -> %s' % (src, dst)), findings, seen)

    for dirkey, segs in tcp_streams.items():
        blob = b''.join(p for _n, _t, p in segs)
        if len(blob) < 16:
            continue
        if extract:
            collect_pwds_from_blob(blob)          # 采集候选口令（供加密压缩包尝试）
        loc = '%s:%d -> %s:%d (会话拼接 %dB)' % (dirkey[0], dirkey[1], dirkey[2], dirkey[3], len(blob))
        scan_blob(blob, keywords, do_decode, depth, findings, seen, loc)
        http_summary(blob, segs[0][1], http_reqs, form_fields)
        if len(blob) <= 3 * 1024 * 1024:
            for m in JWT_RE.finditer(blob):              # JWT 令牌（伪造身份/认证题）
                desc = jwt_summary(m.group(0))
                if desc:
                    add((0.72, 'JWT', b'', desc, loc), findings, seen)
        if printable_ratio(blob[:4096]) > 0.75:          # 环境变量/密钥回显（WEBUI_SK、PWD 等）
            for m in SECRET_LINE_RE.finditer(blob):
                if SENSITIVE_NAME_RE.search(m.group(1)):
                    line = m.group(0).decode('utf-8', 'replace').strip()
                    if len(line) >= 6:
                        add((0.62, '环境/配置', b'', line[:180], loc), findings, seen)
        if (blob[:5] == b'HTTP/' or b'HTTP/1.' in blob[:600]) and b'\r\n\r\n' in blob:
            body = blob[blob.find(b'\r\n\r\n') + 4:]
            sug = flagify(body)
            if sug:
                print('            [响应体] 加壳建议：%s' % sug)
                add((0.75, '加壳候选', b'', sug.encode('utf-8', 'replace'), loc + ' [HTTP响应体]'), findings, seen)

    for num, src, sport, dst, dport, payload in udp_payloads:
        if 53 in (sport, dport) or len(payload) < 12:
            continue
        loc = 'UDP %s:%d->%s:%d 包#%d' % (src, sport, dst, dport, num)
        scan_blob(payload, keywords, do_decode, depth, findings, seen, loc)

    if extract:
        os.makedirs(extract['outdir'], exist_ok=True)
        saved, idx, carved = set(), 0, 0
        pwds = list(PWD_POOL)
        blobs = []
        for dirkey, segs in tcp_streams.items():
            blobs.append(('%s:%d->%s:%d' % dirkey, b''.join(p for _n, _t, p in segs)))
        for num, src, sport, dst, dport, payload in udp_payloads:
            if 53 not in (sport, dport) and len(payload) >= 80:
                blobs.append(('UDP %s:%d->%s:%d 包#%d' % (src, sport, dst, dport, num), payload))
        for tag, blob in blobs:
            if len(blob) < 80:
                continue
            for ext, off, seg in carve_files(blob):
                if ext == '.zip':
                    try:
                        zipfile.ZipFile(io.BytesIO(seg)).namelist()
                    except Exception:
                        continue
                idx += 1
                if extract_scan(ext, seg, extract['outdir'], extract['stem'], idx,
                                '%s (偏移 %d)' % (tag, off), keywords, do_decode, depth,
                                findings, seen, saved, pwds):
                    carved += 1
        if carved:
            print('  [提取] 共保存 %d 个文件 → %s' % (carved, extract['outdir']))
        else:
            try:
                os.rmdir(extract['outdir'])
            except OSError:
                pass

    if http_reqs:
        print('  [HTTP请求序列] 共 %d 条（按时间）：' % len(http_reqs))
        for i, (ts, method, uri) in enumerate(http_reqs[:60], 1):
            print('    %3d. %s %s   @%s' % (i, method, uri[:90], ts_str(ts)))
        if len(http_reqs) > 60:
            print('    ...（其余 %d 条省略）' % (len(http_reqs) - 60))
    if form_fields:
        print('  [POST字段摘录]（去重，含登录凭证/参数/上传文件名）：')
        seen_ff, shown = set(), 0
        for uri, kvs in form_fields:
            key = (uri, tuple(kvs))
            if key in seen_ff:
                continue
            seen_ff.add(key)
            shown += 1
            if shown > 25:
                print('    ...（其余省略）')
                break
            note = ' & '.join('%s=%s' % (k, v) for k, v in kvs[:12])
            print('    %s : %s' % (uri[:70], note[:240]))
    txns = build_http_transactions(tcp_streams, findings, seen)
    if txns:
        print('  [HTTP事务摘要] 请求 → 响应正文（RCE回显/接口返回/短文本，直接可读）：')
        shown, seen_t = 0, set()
        for loc, method, uri, code, txt in txns:
            key = (uri, txt[:100])
            if key in seen_t:
                continue
            seen_t.add(key)
            shown += 1
            if shown > 30:
                print('    ...（其余省略）')
                break
            print('    %s %s  →  [%d] %s' % (method, uri[:80], code, ' '.join(txt.split())[:170]))
    return findings


# ---------------------------------------------------------------- evtx / 文本
def scan_rawfile(data, keywords, do_decode, depth, limit):
    findings, seen = [], set()

    def push(kw, seg, score):
        seg = ' '.join(''.join(ch if ch.isprintable() or ch in '\r\n\t' else '.' for ch in seg).split())
        if not seg:
            return
        add((score, '关键词', kw.encode(), seg.encode('utf-8', 'replace'), '(原始字节)'), findings, seen)

    # 1) UTF-16LE 字节模式（免对齐，适配 evtx 等混合二进制里嵌入的字符串）
    for kw in keywords:
        pat = kw.encode('utf-16-le')
        i, cnt = 0, 0
        while cnt < limit:
            i = data.find(pat, i)
            if i < 0:
                break
            nb = data[i + len(pat): i + len(pat) + 2]
            nxt_letter = len(nb) == 2 and nb[1] == 0 and (65 <= nb[0] <= 90 or 97 <= nb[0] <= 122)
            nxt_open = len(nb) == 2 and nb[1] == 0 and nb[0] == 0x7b
            pb = data[i - 2:i]
            prv_word = (len(pb) == 2 and pb[1] == 0
                        and (48 <= pb[0] <= 57 or 65 <= pb[0] <= 90 or 97 <= pb[0] <= 122 or pb[0] == 0x5f))
            if nxt_letter or (prv_word and not nxt_open):
                i += 2                # 词内误报（关键字后紧跟字母 / 标识符内部命中）
                cnt += 1
                continue
            seg = data[max(0, i - 80): i + 180].decode('utf-16-le', 'replace')
            push(kw, seg, 0.45 if '{' in seg else 0.40)
            i += 2
            cnt += 1
    # 2) ASCII/UTF-8 字节模式
    low = data.lower()
    for kw in keywords:
        pat = kw.encode()
        i, cnt = 0, 0
        while cnt < limit:
            i = low.find(pat, i)
            if i < 0:
                break
            nb = low[i + len(pat): i + len(pat) + 1]
            nxt_letter = bool(nb) and 97 <= nb[0] <= 122
            nxt_open = nb == b'{'
            pb = low[i - 1] if i else 0
            prv_word = 48 <= pb <= 57 or 97 <= pb <= 122 or pb == 0x5f
            if nxt_letter or (prv_word and not nxt_open):
                i += 1                # 词内误报
                cnt += 1
                continue
            seg = data[max(0, i - 80): i + 180].decode('latin-1', 'replace')
            push(kw, seg, 0.45 if '{' in seg else 0.40)
            i += 1
            cnt += 1
    # 3) 整体为 UTF-16 文本（.reg 等）时，给出按行上下文
    try:
        txt = data.decode('utf-16-le', 'replace')
    except Exception:
        txt = ''
    if txt and txt.count('\x00') < len(txt) * 0.05:
        lowt = txt.lower()
        for kw in keywords:
            i, cnt = 0, 0
            while cnt < limit:
                i = lowt.find(kw, i)
                if i < 0:
                    break
                if not kw_boundary_ok(lowt, i, kw):
                    i += len(kw)      # 词内误报
                    cnt += 1
                    continue
                seg = txt[max(0, i - 60): i + 160]
                push(kw, seg, 0.45 if '{' in seg else 0.40)
                i += len(kw)
                cnt += 1
    # 4) 明文 flag 正则 + 片段（剔 NUL 后统一匹配，兼容 UTF-16 内容）
    compact = data.replace(b'\x00', b'')
    for m in FLAG_RE.finditer(compact):
        add((0.97, '明文flag', b'', m.group(0), '(原始字节)'), findings, seen)
    for blob in (compact, data):
        fragments(blob, keywords, findings, seen, '(原始字节)', strict_text=True)
        if do_decode:
            hits = []
            decode_chain(blob, keywords, depth, hits, seen)
            for score, name, tok, dec in hits:
                findings.append((score, name, tok, dec, '(原始字节)'))
    return findings
