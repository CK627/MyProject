# -*- coding: utf-8 -*-
"""扫描编排：抓包扫描（scan_capture）与原始文件扫描（scan_rawfile）"""
import io
import os
import zipfile

from .ad import print_ad_info, scan_ad
from .blobscan import add, scan_blob
from .capture import CaptureContext, LINKNAMES, dns_qname
from .decode import decode_chain, flagify, fragments
from .extract import (PWD_POOL, carve_base64_blobs, carve_files,
                      collect_pwds_from_blob, extract_scan)
from .http import build_http_transactions, http_summary, jwt_summary
from .utils import (FLAG_RE, JWT_RE, SECRET_LINE_RE, SENSITIVE_NAME_RE,
                    decode_score, kw_boundary_ok, printable_ratio, try_b64, ts_str)


def _is_tls_stream(blob):
    """判定方向流是否 TLS 加密（用于文件雕刻前跳过——密文中的文件签名必然是误报）。

    - 流从 TLS 记录开始（0x14/0x15/0x16/0x17 + 版本 03 0x）→ 是；
    - 否则在前 256KB 找结构合理的握手记录（16 03 0x + 长度 + 握手消息类型）。
    """
    if len(blob) < 6:
        return False
    if blob[0] in (0x14, 0x15, 0x16, 0x17) and blob[1] == 0x03 and blob[2] <= 4:
        return True
    window = blob[:262144]
    for magic in (b'\x16\x03\x01', b'\x16\x03\x03'):
        pos = window.find(magic)
        while pos >= 0 and pos + 6 <= len(window):
            rec_len = int.from_bytes(window[pos + 3:pos + 5], 'big')
            msg_type = window[pos + 5]
            if 32 <= rec_len <= 0x4400 and msg_type in (0x01, 0x02, 0x0b):
                return True
            pos = window.find(magic, pos + 3)
    return False


def analyze(filepath, ctx=None, opts=None):
    """流扫描统一入口（Router 的 stream 阶段调用）。

    - 抓包文件 → `scan_capture`（pcap/pcapng 解析 + 各协议线索）
    - 其它文件 → `scan_rawfile`（原始字节扫描）

    ⚠️ 这两个函数会**自行打印**过程信息（`格式:` / `【主机表】` / `【AD / 域渗透线索】` /
    `[交互会话]` / `[提取]` / `[HTTP事务摘要]`），它们与分带报告交错，位置是报告契约的一部分，
    不要搬到调用方。

    返回的 `Finding` 携带原始候选（`tok`/`val`/`loc`），调用方用 `to_tuple()`
    换回 5 元组 ABI（`report()` / `judge.predict_finding` 都按元组解包）。
    """
    from .router import AnalysisResult, Finding, ScanOptions

    opts = opts or ScanOptions()
    if ctx is None:
        with open(filepath, 'rb') as f:
            data = f.read()
        from .capture import CaptureContext
        ctx = CaptureContext(data)

    result = AnalysisResult("scanner")
    if ctx.is_capture:
        findings = scan_capture(
            ctx.data, opts.keywords, opts.decode, opts.depth,
            extract=opts.extract, ctx=ctx)
    else:
        findings = scan_rawfile(
            ctx.data, opts.keywords, opts.decode, opts.depth, opts.limit)
    result.findings = [Finding.from_tuple(t, module="scanner") for t in findings]
    return result


def scan_capture(data, keywords, do_decode, depth, extract=None, ctx=None):
    if ctx is None:
        ctx = CaptureContext(data)
    fmt, pkts = ctx.fmt, ctx.pkts
    print('  格式: %s  链路类型: %s   数据包: %d 个'
          % (fmt, ctx.linktype_names(), len(pkts)))
    findings, seen = [], set()

    # USB 键盘流量（USBPcap）：HID 逐键解码（CTF 常见题型，键入文本常直接是 flag）
    try:
        from .usb import decode_usb_keyboard, is_usbpcap
        if is_usbpcap(pkts):
            kb_text, n_rep = decode_usb_keyboard(pkts)
            if kb_text:
                loc = 'USB HID 键盘解码（%d 个报告）' % n_rep
                print('  [USB键盘] 键入文本: %s' % kb_text[:200])
                score = 0.97 if ('flag' in kb_text.lower() or 'ctf' in kb_text.lower()) else 0.75
                add((score, 'USB键盘输入', b'', kb_text, loc), findings, seen)
    except Exception as _ex:
        print('  [USB] 键盘解码出错: %r' % _ex)

    # 解析结果来自 ctx（tcp_streams / udp_payloads / unknown_pkts 已在里面建好）；
    # 这里仍按包序重放 l4 以产出 findings，顺序与原先逐包交错时完全一致
    tcp_streams, udp_payloads = ctx.tcp_streams, ctx.udp_payloads
    http_reqs, form_fields = [], []
    unknown_pkts = ctx.unknown_pkts
    for num, lt, pkt, ts, r in ctx.l4:
        if not r:
            continue
        proto, src, dst, sport, dport, payload = r
        if not payload:
            continue
        locp = '%s:%d->%s:%d 包#%d' % (src, sport, dst, dport, num)
        if proto == 'tcp':
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

    for dirkey, segs, blob in ctx.stream_blobs():
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

    # 未支持链路类型兜底：原始字节扫描（无线 / 物联网 / USB 等无 IP 结构）
    # ——此前这类包被直接跳过（"连过程都没有"）；现在按原始字节扫描 + 拼接扫描
    if unknown_pkts:
        unsup = sorted(set(lt for _n, lt, _p in unknown_pkts))
        names = ', '.join(str(LINKNAMES.get(lt, '链路类型 %d' % lt)) for lt in unsup[:4])
        print('  [兜底] %d/%d 个包为非 IP 链路（%s），按原始字节扫描：'
              % (len(unknown_pkts), len(pkts), names))
        budget, used, scanned = 4 * 1024 * 1024, 0, 0
        for num, lt, pkt in unknown_pkts:
            if not pkt:
                continue
            if used >= budget:
                print('           （达到字节预算，其余 %d 个包跳过）'
                      % (len(unknown_pkts) - scanned))
                break
            used += len(pkt)
            scanned += 1
            loc = '包#%d（%s）' % (num, LINKNAMES.get(lt, '链路类型 %d' % lt))
            scan_blob(pkt, keywords, do_decode, depth, findings, seen, loc)
        if len(unknown_pkts) > 1:                    # 跨包拼接（分段数据可能分散在多个包）
            cat = b''.join(p for _n, _l, p in unknown_pkts)[:budget]
            scan_blob(cat, keywords, do_decode, depth, findings, seen,
                      '拼接（%d 个非 IP 包）' % len(unknown_pkts))

    # 主机表：IP ↔ MAC（ARP/Ethernet）+ 主机名线索（DHCP/NBNS）
    # 恶意流量分析经典三问（感染主机 IP/MAC/主机名）直接可答；CTF 也常问"攻击者 MAC"
    try:
        from .hosts import collect_hosts, print_hosts
        _im, _mn, _inm = collect_hosts(pkts)
        print_hosts(_im, _mn, _inm)
    except Exception as _ex:
        print('  [主机] 分析出错: %r' % _ex)

    # AD / 域协议（Kerberos / NTLMSSP / LDAP）：这类流量没有 flag 明文，
    # 靠字符串扫描必然零命中，这里解票据与凭据（hashcat 可直接用）
    try:
        ad_info = scan_ad(tcp_streams, udp_payloads,
                          lambda f: add(f, findings, seen))
    except Exception:
        ad_info = None
    if ad_info:
        print_ad_info(ad_info)

    # 交互会话提取（FTP 登录/爆破命令序列、反弹 shell/交互 shell 命令记录）
    # 对应"入侵行为分析"类取证题：直接输出可回答"第 N 条命令/成功凭据/系统版本"
    try:
        from .session import analyze_sessions
        for line in analyze_sessions(tcp_streams, lambda f: add(f, findings, seen)):
            print(line)
    except Exception as _ex:
        print('  [会话] 分析出错: %r' % _ex)

    if extract:
        os.makedirs(extract['outdir'], exist_ok=True)
        saved, idx, carved, tls_skipped = set(), 0, 0, 0
        pwds = list(PWD_POOL)
        blobs = [('%s:%d->%s:%d' % dirkey, blob)
                 for dirkey, _segs, blob in ctx.stream_blobs()]
        for num, src, sport, dst, dport, payload in udp_payloads:
            if 53 not in (sport, dport) and len(payload) >= 80:
                blobs.append(('UDP %s:%d->%s:%d 包#%d' % (src, sport, dst, dport, num), payload))
        for tag, blob in blobs:
            if len(blob) < 80:
                continue
            # TLS 加密流：应用数据为密文，文件签名雕刻必然误报（如 FFD8FF 巧合出"大图"），
            # 直接跳过（明文 HTTP over 443 的流不以 TLS 记录开头，不受影响）
            if _is_tls_stream(blob):
                tls_skipped += 1
                continue
            # HTTP 响应流：按"逐响应体"雕刻（Content-Length 精确切分 / chunked 自动解码）
            # —— 避免响应连读、流尾填充字节混进文件（否则大小/哈希与真实文件不符）
            variants = [(blob, '')]
            if blob[:5] == b'HTTP/':
                from .http import http_body_decode, parse_http_responses
                vb = []
                for i, (_code, _ct, rbody) in enumerate(parse_http_responses(blob, nocl_cap=None)):
                    if len(rbody) < 80:
                        continue
                    vb.append((rbody, 'HTTP响应体%d' % (i + 1)))
                    dec2, notes2 = http_body_decode(rbody)
                    if notes2:
                        vb.append((dec2, 'HTTP体%d[%s]' % (i + 1, '+'.join(notes2))))
                if vb:
                    variants = vb
                he = blob.find(b'\r\n\r\n')
                if he > 0:
                    body_dec, notes = http_body_decode(blob[he + 4:])
                    if notes:
                        print('  [HTTP体] %s：%s 解码 %d → %d 字节'
                              % ('+'.join(notes), tag.split(':')[0], len(blob) - he - 4, len(body_dec)))
                        for m2 in FLAG_RE.finditer(body_dec[:4 * 1024 * 1024]):
                            add((0.97, '明文flag', b'', m2.group(0),
                                 '%s [HTTP体解码]' % tag), findings, seen)
            for vblob, vtag in variants:
                for ext, off, seg in carve_files(vblob):
                    if ext == '.zip':
                        try:
                            zipfile.ZipFile(io.BytesIO(seg)).namelist()
                        except Exception:
                            continue
                    idx += 1
                    loc_tag = '%s%s (偏移 %d)' % (tag, (' ' + vtag) if vtag else '', off)
                    if extract_scan(ext, seg, extract['outdir'], extract['stem'], idx,
                                    loc_tag, keywords, do_decode, depth,
                                    findings, seen, saved, pwds):
                        carved += 1
                # 页面内嵌 base64 载荷（HTML/JS "saveAs" 下载页藏 Word/EXE/ZIP）
                for ext, off, seg in carve_base64_blobs(vblob):
                    idx += 1
                    loc_tag = '%s%s (base64 @%d)' % (tag, (' ' + vtag) if vtag else '', off)
                    if extract_scan(ext, seg, extract['outdir'], extract['stem'], idx,
                                    loc_tag, keywords, do_decode, depth,
                                    findings, seen, saved, pwds):
                        carved += 1
        if carved:
            print('  [提取] 共保存 %d 个文件 → %s' % (carved, extract['outdir']))
        if tls_skipped:
            print('  [提取] 跳过 %d 个 TLS 加密流（密文不做文件雕刻，避免签名巧合误报）' % tls_skipped)
        if not carved:
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
