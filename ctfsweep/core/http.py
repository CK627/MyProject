# -*- coding: utf-8 -*-
"""HTTP 深度分析：请求序列 / POST 字段（含 JSON 体）/ JWT 解码 / 请求↔响应事务配对"""
import json
import re
from urllib.parse import unquote_plus

from .blobscan import add
from .utils import printable_ratio, try_b64

HTTP_REQ_RE = re.compile(rb'(?<![A-Za-z])(GET|POST|HEAD|PUT|OPTIONS|DELETE|PATCH) (\S{1,300}) HTTP/1\.[01]')


def http_summary(blob, ts0, http_reqs, form_fields):
    """从 TCP 流中提取 HTTP 请求行与 POST 表单字段（服务目录扫描次序/登录凭证/上传路径类题目）"""
    window = blob[:2 * 1024 * 1024]
    matches = list(HTTP_REQ_RE.finditer(window))
    if not matches:
        return
    for mi, m in enumerate(matches):
        method = m.group(1).decode()
        uri = m.group(2).decode('latin-1')
        http_reqs.append((ts0, method, uri))
        if method != 'POST':
            continue
        seg_end = matches[mi + 1].start() if mi + 1 < len(matches) else min(len(window), m.end() + 20000)
        hdr_end = window.find(b'\r\n\r\n', m.end())
        if hdr_end < 0 or hdr_end > seg_end:
            continue
        body = window[hdr_end + 4:seg_end][:8000]
        ctm = re.search(rb'(?i)content-type:\s*([^\r\n;]+)', window[m.end():hdr_end])
        ctype = ctm.group(1).strip().lower() if ctm else b''
        kvs = []
        if b'multipart/form-data' in ctype:
            filenames = re.findall(rb'(?i)filename="([^"]{0,120})"', body)
            kvs = [('(multipart/form-data)', ', '.join(f.decode('latin-1', 'replace') for f in filenames[:5]) or '无文件名')]
        else:
            try:
                body_txt = body.decode('utf-8', 'replace')
            except Exception:
                body_txt = ''
            for kv in body_txt.split('&')[:24]:
                if '=' in kv and len(kv) <= 300:
                    k, v = kv.split('=', 1)
                    try:
                        k = unquote_plus(k)
                        v = unquote_plus(v)
                    except Exception:
                        pass
                    kvs.append((k[:40], v[:80]))
        if not kvs and body.lstrip()[:1] == b'{':
            try:
                obj = json.loads(body.decode('utf-8', 'replace'))
                if isinstance(obj, dict):
                    kvs = [(str(k)[:40], str(v)[:80]) for k, v in list(obj.items())[:12]]
            except Exception:
                pass
        if kvs:
            form_fields.append((uri, kvs))


def jwt_summary(tok):
    """解码 JWT（base64url）的 header/payload 摘要（认证伪造类题：payload 里的 username 往往就是答案）"""
    try:
        parts = tok.split(b'.')
        if len(parts) != 3:
            return None
        hdr, pld = try_b64(parts[0]), try_b64(parts[1])
        if not hdr or not pld or printable_ratio(hdr) < 0.8 or printable_ratio(pld) < 0.8:
            return None
        hs = hdr.decode('utf-8', 'replace')[:90]
        ps = pld.decode('utf-8', 'replace')[:180]
        return 'header=%s payload=%s' % (hs, ps)
    except Exception:
        return None


def parse_http_responses(blob):
    """解析 HTTP 响应流：返回 [(状态码, content-type, 正文bytes)]（优先按 content-length 精确切分）"""
    out = []
    resp_re = re.compile(rb'HTTP/1\.[01] (\d{3})')
    pos, n = 0, len(blob)
    while pos < n:
        m = resp_re.search(blob, pos)
        if not m:
            break
        he = blob.find(b'\r\n\r\n', m.end())
        if he < 0:
            break
        head = blob[m.end():he]
        cl = re.search(rb'(?i)content-length:\s*(\d+)', head)
        ctm = re.search(rb'(?i)content-type:\s*([^\r\n;]+)', head)
        ctype = ctm.group(1).strip().lower() if ctm else b''
        if cl:
            ln = int(cl.group(1))
            body = blob[he + 4:he + 4 + ln]
            pos = he + 4 + ln
        else:
            nxt = blob.find(b'HTTP/1.', he + 4)
            body = blob[he + 4:nxt if nxt >= 0 else min(n, he + 4 + 2048)]
            pos = nxt if nxt >= 0 else n
        out.append((int(m.group(1)), ctype, body))
    return out


def build_http_transactions(tcp_streams, findings, seen):
    """配对 HTTP 请求↔响应正文；webshell/RCE 命令回显、接口短文本并入置信度报告"""
    out, added = [], 0
    for k, segs in tcp_streams.items():
        blob = b''.join(p for _n, _t, p in segs)
        if len(blob) < 40 or len(blob) > 3 * 1024 * 1024:
            continue
        reqs = list(HTTP_REQ_RE.finditer(blob))
        if not reqs:
            continue
        rsegs = tcp_streams.get((k[2], k[3], k[0], k[1]))
        if not rsegs:
            continue
        resps = parse_http_responses(b''.join(p for _n, _t, p in rsegs))
        loc = '%s:%d -> %s:%d' % k
        for m, (code, ctype, body) in zip(reqs, resps):
            uri = m.group(2).decode('latin-1')
            if not body or len(body) > 1500 or uri.endswith('/favicon.ico'):
                continue
            if any(t in ctype for t in (b'javascript', b'css', b'image/', b'font', b'octet-stream')):
                continue
            j = body[:220].lower()
            if j.lstrip()[:1] == b'<' or b'<!doctype' in j or b'<html' in j:
                continue
            if printable_ratio(body) < 0.9:
                continue
            txt = body.decode('utf-8', 'replace').strip()
            if not txt:
                continue
            head_j = txt[:300].lower()
            if head_j.startswith('http/') or ('http/1.' in head_j and 'content-type' in head_j):
                continue                                     # 解析错位（正文=下一个响应头）→ 丢弃
            if len(txt) % 2 == 0 and txt[:len(txt) // 2] == txt[len(txt) // 2:]:
                txt = txt[:len(txt) // 2].strip()            # 抓包重复导致的双份正文 → 合并
            if not txt:
                continue
            method = m.group(1).decode()
            out.append((loc, method, uri, code, txt))
            if added < 40:
                val = '%s %s => %s' % (method, uri, txt[:200])
                if re.search(r'(?i)cmd=|/cmd|exec|shell|popen|system|whoami|run=', uri):
                    add((0.62, '命令回显', b'', val, loc), findings, seen)
                else:
                    add((0.42, '短文本响应', b'', val[:260], loc), findings, seen)
                added += 1
    return out
