# -*- coding: utf-8 -*-
"""字节块扫描原语：findings 去重入库（add）与单块多策略扫描（scan_blob）"""
from .decode import decode_chain, fragments
from .utils import FLAG_RE, kw_boundary_ok, text_like_window


def add(finding, findings, seen):
    """去重：解码/片段按内容，关键词按文本，其余按**内容**（不再带位置）。

    ⚠️ 通用分支**刻意不把 `loc` 放进去重键**。历史上键是 `(kind, v, loc)`，
    于是"同一条结论在不同会话里各报一次"会全部活下来——实测 dump.pcapng 是
    50 条 FTP 会话连同一台 vsftpd 2.3.4，`漏洞利用：笑脸后门（CVE-2011-2523）`
    被原样印了 **50 行**，证据逐字相同，只有端口不同。这正是"与答案无关的噪音
    会增加解题难度"：真正该看的 [FTP会话] 爆破序列被顶出屏幕。
    同值即同结论，留第一条（带它的位置）即可；会话级的差异由 [FTP会话]/[交互会话]
    这类**块**按会话逐条呈现，本来就不该由 findings 承担。

    反例检查（这些 kind 的重复**不是**噪音，故各自单独处理，不走本分支）：
    `明文flag` 同值跨视图合并（双份抓包）、`DNS查询` 的域名在循环内已按 `dns_seen`
    去重、`域账号`/`Kerberos票据` 在 ad.py 内已各自去重。
    """
    score, kind, tok, val, loc = finding
    v = val if isinstance(val, str) else val.decode('utf-8', 'replace')
    if kind in ('hex', 'base64'):
        k = ('dec', kind, v[:100])
    elif kind.startswith('片段'):
        k = ('frag', v[:100])
    elif kind == '关键词':
        k = ('kw', v[:140])
    elif kind == '明文flag':
        k = ('flag', v[:160])
    elif kind in ('JWT', '命令回显', '环境/配置', '短文本响应'):
        k = ('ctx', kind, v[:220])                       # 同值跨视图合并（双份抓包常见）
    else:
        k = (kind, v[:140])
    if k in seen:
        return
    seen.add(k)
    findings.append(finding)


def scan_blob(blob, keywords, do_decode, depth, findings, seen, loc):
    """字节块扫描：明文 flag / 片段 / 关键词上下文 / 自动解码"""
    for m in FLAG_RE.finditer(blob):
        add((0.97, '明文flag', b'', m.group(0), loc), findings, seen)
    fragments(blob, keywords, findings, seen, loc)
    for enc in ('ascii', 'utf-16'):
        if enc == 'utf-16':
            if blob.count(b'\x00') < len(blob) * 0.2:
                continue
            try:
                text = blob.decode('utf-16-le', 'replace')
            except Exception:
                continue
        else:
            try:
                text = blob.decode('latin-1')
            except Exception:
                continue
        hay = text.lower()
        for kw in keywords:
            i, cnt = 0, 0
            while cnt < 6:
                i = hay.find(kw, i)
                if i < 0:
                    break
                if not kw_boundary_ok(text, i, kw):
                    i += len(kw)          # 词内误报（FolderValueFlags / create_pdo_flag 等）
                    cnt += 1
                    continue
                if enc == 'ascii':
                    # ascii 通道的 `text` 是 latin-1 解出来的，1 字节 ↔ 1 字符，
                    # 所以 i 同时也是 blob 的下标，直接用原始字节做严格文本判定
                    win = blob[max(0, i - 40): i + 110]
                    if not text_like_window(win):
                        i += len(kw)
                        cnt += 1
                        continue
                raw_seg = text[max(0, i - 40): i + 110]
                if enc == 'utf-16':
                    # utf-16 通道的 i 是解码后文本的下标，只能回到 raw_seg 上判
                    ok_chars = sum(ch.isprintable() or ch in '\r\n\t' for ch in raw_seg)
                    if ok_chars < len(raw_seg) * 0.7:
                        i += len(kw)
                        cnt += 1
                        continue
                seg = raw_seg.replace('\x00', '')
                seg = ''.join(ch if ch.isprintable() or ch in '\r\n\t' else '.' for ch in seg)
                seg = ' '.join(seg.split())
                if seg:
                    score = 0.45 if '{' in seg else 0.40
                    add((score, '关键词', kw.encode(), seg.encode('utf-8', 'replace'), loc), findings, seen)
                i += len(kw)
                cnt += 1
    if do_decode:
        hits = []
        decode_chain(blob, keywords, depth, hits, seen)
        for score, name, tok, dec in hits:
            findings.append((score, name, tok, dec, loc))
