# -*- coding: utf-8 -*-
"""扫描编排：抓包扫描（scan_capture）与原始文件扫描（scan_rawfile）"""
import collections
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
                    SERVICE_DISCOVERY_REASON, base_domain, decode_score,
                    dns_lead_reason, kw_boundary_ok, kw_hit_bounded,
                    printable_ratio, readable_window, try_b64, ts_str,
                    under_known_infra)


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


def _ip_list(ips, limit=3):
    """把一组 IP 压成一段短文本，供 [TLS SNI] / [HTTP服务端] 的聚合行使用。

    一台机器连 `login.microsoftonline.com` 会落到 10 个不同 IP 上，
    逐行列出就把席位吃光了——聚合行只需要说清"解析到了几个地址"。
    """
    ips = sorted(set(ips))
    if len(ips) <= limit:
        return ', '.join(ips)
    return '%d 个 IP（%s, …）' % (len(ips), ', '.join(ips[:limit]))


def tls_sni(blob):
    """从 TLS ClientHello 里取 SNI（Server Name Indication），取不到返回 ''。

    为什么必须有：HTTPS 已是绝大多数 C2/投递流量的载体，正文全加密，
    唯一留在**明文**里的身份信息就是 SNI。实测 2020-09-25 那道题，报告能给出
    受害主机 / MAC / 账号 / 投递的 `jojo.exe`，却给不出 `paste.nrecom.net`
    与 `37.120.174.218`——因为域名只存在于 SNI 里。2021-09-10 那道题的
    BazarLoader C2 同理。
    """
    pos = 0
    while pos + 6 <= len(blob):
        if blob[pos] != 0x16 or blob[pos + 1] != 0x03:
            pos += 1
            continue
        rec_len = int.from_bytes(blob[pos + 3:pos + 5], 'big')
        end = min(pos + 5 + rec_len, len(blob))
        if blob[pos + 5] != 0x01:            # 不是 ClientHello，跳到下一个记录
            pos = end if end > pos else pos + 1
            continue
        hs = blob[pos + 5:end]               # 握手消息（含 4 字节头）
        p = 4 + 2 + 32                       # 跳过 handshake header / version / random
        if p >= len(hs):
            return ''
        p += 1 + hs[p]                       # session_id
        if p + 2 > len(hs):
            return ''
        p += 2 + int.from_bytes(hs[p:p + 2], 'big')   # cipher_suites
        if p + 1 > len(hs):
            return ''
        p += 1 + hs[p]                       # compression_methods
        if p + 2 > len(hs):
            return ''
        ext_end = min(p + 2 + int.from_bytes(hs[p:p + 2], 'big'), len(hs))
        p += 2
        while p + 4 <= ext_end:
            etype = int.from_bytes(hs[p:p + 2], 'big')
            elen = int.from_bytes(hs[p + 2:p + 4], 'big')
            if etype == 0x0000 and p + 9 <= ext_end:
                body = hs[p + 4:p + 4 + elen]
                nl = int.from_bytes(body[3:5], 'big')     # list_len(2)+type(1)+name_len(2)
                name = body[5:5 + nl]
                if name:
                    return name.decode('latin-1', 'replace')
            p += 4 + elen
        return ''
    return ''


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
    http_reqs, form_fields, web_hits = [], [], []
    tls_names = collections.Counter()          # (SNI, 服务端 IP) → 出现次数
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
    dns_routine = []
    dns_discovery = []
    for num, src, sport, dst, dport, payload in udp_payloads:
        if 53 not in (sport, dport):
            continue
        q = dns_qname(payload)
        if not q or q in dns_seen:
            continue
        dns_seen.add(q)
        loc = '%s -> %s' % (src, dst)
        # 逐条列出所有查询名会把常规上网域名刷满屏幕（中文流量的 CDN/门户一条都不
        # 在"厂商白名单"里），真正的外带/DGA/动态DNS/AD发现线索反而被挤下去。
        # 所以只逐条列出结构异常的，其余折叠成一行——折叠**不丢信息**，base64 外带
        # 检测对所有域名照跑（长标签里塞数据才是线索，域名本身不是）。
        reason = dns_lead_reason(q)
        if reason is None:
            dns_routine.append(q)
        elif reason == SERVICE_DISCOVERY_REASON:
            # 服务发现查询单独归组，循环后**折叠成一行**（见下方渲染）。这里不能逐条 add：
            # 域渗透题里 `_ldap._tcp.…` 会成片出现，逐条列出就等于让报告前 6 行全是
            # 同一台主机的域内 SRV 查询——实测 2024-09-04 那道题正是如此，而该题四个
            # 答案（主机名 / IP / MAC / 账号）与域名一个字都不沾。
            dns_discovery.append(q)
        else:
            add((0.45, 'DNS查询', b'', q, '%s（%s）' % (loc, reason)), findings, seen)
        for label in q.split(b'.'):
            if len(label) >= 12:
                dec = try_b64(label)
                if dec and printable_ratio(dec) > 0.8 and (b'{' in dec or kw_hit_bounded(dec, keywords)):
                    add((decode_score(dec, keywords), 'base64', label, dec, 'DNS子域名 %s -> %s' % (src, dst)), findings, seen)

    if dns_routine:
        uniq = sorted(set(dns_routine))
        # 0.42 是"折叠后仍然可见"的最低档：低于默认 --min-score(0.40) 就会被静默
        # 滤掉，等于把整批查询藏起来——折叠的目的是少占屏，不是隐瞒。
        # 只举 6 个样例：渲染层对非具名 kind 收 v[:230]，多列会被拦腰截断且没有省略号。
        add((0.42, 'DNS查询（常规域名，已折叠）', b'',
             '%d 个：%s%s' % (len(uniq), ' '.join(x.decode('latin-1') for x in uniq[:6]),
                              ' …' if len(uniq) > 6 else ''),
             '共 %d 条 UDP/53 查询' % len(dns_routine)), findings, seen)

    if dns_discovery:
        # 服务发现查询折叠成**一行、按域名计数**。逐条列出是纯噪音：名字里只有域内
        # 拓扑（哪台 DC、哪个站点），且每个域环境都长这样。
        # 但折叠不能埋掉真线索——`_ldap._tcp.pdc._msdcs.enemywatch.net` 这类**域外**
        # 域名的 SRV 查询是有效的（可能是攻击者控制的域/投毒目标），
        # 所以这一行按域名归组：域外域名一出现，"涉及 N 个域"立刻会变成 ≥2。
        groups = collections.OrderedDict()
        for q in dns_discovery:
            d = base_domain(q)
            groups[d] = groups.get(d, 0) + 1
        ranked = sorted(groups.items(), key=lambda kv: (-kv[1], kv[0]))
        detail = '、'.join('%s×%d' % (d, c) for d, c in ranked[:4])
        if len(ranked) > 4:
            detail += '、…'
        if len(ranked) == 1:
            val = '%d 条，均属 %s（域内 SRV/WPAD 常态查询，与答案无关）' % (
                len(dns_discovery), ranked[0][0])
        else:
            val = '%d 条，涉及 %d 个域: %s（域外域名的 SRV 查询值得追）' % (
                len(dns_discovery), len(ranked), detail)
        add((0.45, 'DNS查询（服务发现类，已折叠）', b'', val,
             '共 %d 条 UDP/53 查询' % len(dns_discovery)), findings, seen)

    for dirkey, segs, blob in ctx.stream_blobs():
        if len(blob) < 16:
            continue
        if extract:
            collect_pwds_from_blob(blob)          # 采集候选口令（供加密压缩包尝试）
        loc = '%s:%d -> %s:%d (会话拼接 %dB)' % (dirkey[0], dirkey[1], dirkey[2], dirkey[3], len(blob))
        scan_blob(blob, keywords, do_decode, depth, findings, seen, loc)
        # dirkey 是 (src, sport, dst, dport)：正向流的目的地址就是 HTTP 服务端
        web_hits += http_summary(blob, segs[0][1], http_reqs, form_fields, dirkey[2])
        if 443 in (dirkey[1], dirkey[3]) or _is_tls_stream(blob[:4096]):
            sni = tls_sni(blob)
            if sni:
                tls_names[(sni, dirkey[2])] += 1
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

    # Web 攻击载荷：按**攻击类型**聚合成一条，不按请求条数刷屏——sqlmap 一次扫描
    # 就是几百条载荷，逐条列出会让真正要看的东西（用了哪些手法、打了哪个参数）淹掉。
    if web_hits:
        by_reason = {}
        for reason, uri in web_hits:
            by_reason.setdefault(reason, [])
            if uri not in by_reason[reason]:
                by_reason[reason].append(uri)
        print('  [Web攻击载荷] %d 类（共 %d 条请求，URI 已百分号解码）：'
              % (len(by_reason), len(web_hits)))
        for reason, uris in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
            print('    %s ×%d  例: %s' % (reason, len(uris), uris[0][:150]))
            add((0.85, 'Web攻击载荷', b'', '%s ×%d；例: %s' % (reason, len(uris), uris[0][:200]),
                 'HTTP 请求'), findings, seen)

    if tls_names:
        # HTTPS 正文不可读，SNI 是唯一留在明文里的名字。不给这一块，
        # 全 HTTPS 的 C2/投递域名在报告里一个字都不会出现。
        #
        # 三条渲染约定，全部来自 2025-01-22 那道题（答案是两个域名：
        # `google-authenticator.burleson-appliance.net` 与 `authenticatoor.org`）：
        # ① **按域名聚合**，不再一行一个 (域名, IP)——旧版 `login.microsoftonline.com`
        #    一台机器就占 10 行，15 个席位里 14 个是同一家的遥测；
        # ② **域名不截断**。旧版 `sni[:38]` 把 41 字符的
        #    `google-authenticator.burleson-appliance.net` 印成 `…burleson-applianc`：
        #    看起来像答案、照抄却核验不了，比不印更坏；
        # ③ 已知厂商/CDN 折叠成一行计数，不占逐条席位（旧版把它们和真域名混排，
        #    只靠排序分前后，数量一多真域名照样被挤出去）。
        by_name = collections.OrderedDict()
        for (sni, ip), c in tls_names.items():
            e = by_name.setdefault(sni, {'ips': [], 'n': 0})
            e['ips'].append(ip)
            e['n'] += c
        plain = sorted([(s, e) for s, e in by_name.items() if not under_known_infra(s)],
                       key=lambda kv: -kv[1]['n'])
        infra = sorted([(s, e) for s, e in by_name.items() if under_known_infra(s)],
                       key=lambda kv: -kv[1]['n'])
        print('  [TLS SNI]（HTTPS 握手明文里的服务名；已知厂商/CDN 折叠在末尾）：')
        for s, e in plain[:20]:
            print('    %-38s %-18s ×%d' % (s, _ip_list(e['ips']), e['n']))
        if len(plain) > 20:
            print('    ...（其余 %d 个域名省略）' % (len(plain) - 20))
        if infra:
            names = ' '.join(s for s, _e in infra[:10])
            print('    已知厂商/CDN %d 个（遥测/CDN，通常不是答案）: %s%s'
                  % (len(infra), names, ' …' if len(infra) > 10 else ''))

    if http_reqs:
        # 服务端汇总（host → IP ×次数）。请求行里只有路径没有主机名，
        # 不给这一块，`GET /bmdff/...` 这类投递请求就完全看不出打到了哪台服务器。
        srv = collections.OrderedDict()
        for _ts, _m, _u, host, ip in http_reqs:
            if host or ip:
                key = (host or '?', ip or '?')
                srv[key] = srv.get(key, 0) + 1
        if srv:
            # 与 [TLS SNI] 同理：按 Host 聚合、**不截断**。旧版 `host[:38]` 把
            # `msedge.b.tlu.dl.delivery.mp.microsoft.com` 印成 `…mp.microsoft.`，
            # 尾部的真实域名被切掉——域名截断后就不再是 IOC。
            by_host = collections.OrderedDict()
            for (host, ip), c in srv.items():
                e = by_host.setdefault(host, {'ips': [], 'n': 0})
                e['ips'].append(ip)
                e['n'] += c
            print('  [HTTP服务端]（Host → IP ×请求数）：')
            ranked = sorted(by_host.items(), key=lambda kv: -kv[1]['n'])
            for host, e in ranked[:12]:
                print('    %-38s %-18s ×%d' % (host, _ip_list(e['ips']), e['n']))
            if len(ranked) > 12:
                print('    ...（其余 %d 个服务端省略）' % (len(ranked) - 12))
        print('  [HTTP请求序列] 共 %d 条（按时间）：' % len(http_reqs))
        for i, (ts, method, uri, host, _ip) in enumerate(http_reqs[:60], 1):
            tgt = (host + uri) if host else uri
            print('    %3d. %s %s   @%s' % (i, method, tgt[:100], ts_str(ts)))
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
        # 先净化再入库：`isprintable()` 拦不住二进制按 UTF-16 解码出来的乱码
        # （Ā Ѐ ఀ ᄀ ⨀ 全是 printable），见 utils.readable_window 的说明。
        # 净化放在**源头**：val 干净了，下游的 report()/MetaJudge 证据行自动干净。
        seg = ' '.join(''.join(ch if ch.isprintable() or ch in '\r\n\t' else '.' for ch in seg).split())
        seg = readable_window(seg)
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
