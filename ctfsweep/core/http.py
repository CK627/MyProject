# -*- coding: utf-8 -*-
"""HTTP 深度分析：请求序列 / POST 字段（含 JSON 体）/ JWT 解码 / 请求↔响应事务配对
+ 响应体解码链（chunked 分块 → gzip/deflate 解压；用于下载文件提取）"""
import json
import re
import zlib
from urllib.parse import unquote_plus

from .blobscan import add
from .capture import merge_stream
from .utils import printable_ratio, try_b64

HTTP_REQ_RE = re.compile(rb'(?<![A-Za-z])(GET|POST|HEAD|PUT|OPTIONS|DELETE|PATCH) (\S{1,300}) HTTP/1\.[01]')


def _dechunk_prefix(data, pos=0):
    """从 pos 解析 chunked 编码：返回 (decoded, new_pos)；无有效分块返回 (None, pos)。"""
    chunks, n, p = [], len(data), pos
    while p < n:
        m = re.match(rb'\s*([0-9a-fA-F]{1,8})\r?\n', data[p:p + 14])
        if not m:
            break
        size = int(m.group(1), 16)
        p += m.end()
        if size == 0:
            break
        chunk = data[p:p + size]
        if len(chunk) < size:
            p = pos
            chunks = []
            break
        chunks.append(chunk)
        p += size
        if data[p:p + 2] == b'\r\n':
            p += 2
    if chunks:
        return b''.join(chunks), p
    return None, pos


def http_body_decode(body):
    """HTTP 响应体解码链：chunked 拼接 → gzip/zlib 解压（自动循环，最多 3 层）。

    返回 (decoded, notes)；notes 记录应用的变换（如 ['chunked', 'gzip']）。
    """
    notes = []
    cur = body
    for _ in range(3):
        changed = False
        d, _np = _dechunk_prefix(cur)
        if d is not None and d != cur:
            cur = d
            notes.append('chunked')
            changed = True
        if cur[:2] == b'\x1f\x8b':                     # gzip
            try:
                dobj = zlib.decompressobj(31)
                out = dobj.decompress(cur) + dobj.flush()
                if out:
                    cur = out
                    notes.append('gzip')
                    changed = True
            except Exception:
                pass
        elif cur[:2] in (b'x\x9c', b'x\xda', b'x\x01'):  # zlib
            try:
                cur = zlib.decompress(cur)
                notes.append('zlib')
                changed = True
            except Exception:
                pass
        if not changed:
            break
    return cur, notes


# ---------------------------------------------------------------- Web 攻击载荷
# ⚠️ 必须**先百分号解码**再匹配：真实流量里的 SQLi 载荷是
# `id=1%20AND%209418%3D3822%20UNION%20ALL%20SELECT`（sqlmap 的标准编码），
# 直接对原始 URI 匹配会一条不漏地全部错过——实测 山东.pcapng 的 106 条请求里
# 有 5 条是攻击载荷（UNION SELECT / 布尔盲注 / XSS），修复前零输出。
_WEB_ATTACKS = (
    # `union [all] select` 中间允许注释/关键字噪音（union/**/all/**/select）
    (re.compile(r'\bunion\b[\s/*!+-]*(?:all\b[\s/*!+-]*)?\bselect\b'), 'SQL注入（UNION SELECT）'),
    (re.compile(r"(?:\band\b|\bor\b)\s*[('\"]?\s*\d+\s*=\s*\d+"), 'SQL注入（布尔盲注）'),
    # exp( 单独出现太常见（表达式接口/JS），必须跟着 select 才算报错注入
    (re.compile(r'\b(?:sleep|benchmark|extractvalue|updatexml|load_file)\s*\('
                r'|\bexp\s*\([^)]{0,40}\bselect\b|\bfloor\s*\(\s*rand\s*\('),
     'SQL注入（时间/报错盲注函数）'),
    (re.compile(r'\binformation_schema\b|@@version|\bwaitfor\s+delay\b|\bconcat_ws\s*\('),
     'SQL注入（库表探测）'),
    (re.compile(r'<\s*script\b|\bon(?:error|load|mouseover)\s*=|\bjavascript\s*:|\balert\s*\('),
     'XSS 跨站脚本载荷'),
    (re.compile(r'(?:\.\./){2,}|/etc/passwd|/proc/self/environ|php://(?:filter|input)|data://text'),
     '路径穿越 / 本地文件包含'),
    (re.compile(r'(?:^|[;&|])\s*(?:cat|whoami|id|uname|wget|curl|nc)\s+[/\-\w]|cmd\.exe|powershell\s+-'),
     '命令注入'),
    (re.compile(r'=\s*(?:system|exec|shell_exec|passthru|popen|eval|assert|preg_replace)\s*\('),
     'Webshell 参数执行'),
)


def web_attack_reason(uri):
    """URI（原始，未解码）是否含攻击载荷；返回中文原因，None = 常规请求。"""
    try:
        text = unquote_plus(uri, errors='replace')
    except Exception:
        text = uri
    low = text.lower()
    for pat, reason in _WEB_ATTACKS:
        if pat.search(low):
            return reason
    return None


def http_summary(blob, ts0, http_reqs, form_fields):
    """从 TCP 流中提取 HTTP 请求行与 POST 表单字段（服务目录扫描次序/登录凭证/上传路径类题目）。

    返回 [(攻击原因, 解码后的 URI)]（无攻击载荷时为空列表），供调用方汇总上报。
    """
    hits = []
    window = blob[:2 * 1024 * 1024]
    matches = list(HTTP_REQ_RE.finditer(window))
    if not matches:
        return hits
    for mi, m in enumerate(matches):
        method = m.group(1).decode()
        uri = m.group(2).decode('latin-1')
        http_reqs.append((ts0, method, uri))
        reason = web_attack_reason(uri)
        if reason:
            try:
                hits.append((reason, unquote_plus(uri, errors='replace')))
            except Exception:
                hits.append((reason, uri))
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
    return hits


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


def parse_http_responses(blob, nocl_cap=2048):
    """解析 HTTP 响应流：返回 [(状态码, content-type, 正文bytes)]（content-length 精确切分；
    chunked 响应自动解码拼接）。
    nocl_cap: 无 CL/chunked 时的正文上限（默认 2048，适合"短文本回显"配对；
    雕刻文件场景传 None 表示不设上限）"""
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
        te = re.search(rb'(?i)transfer-encoding:\s*[^\r\n]*chunked', head)
        if cl:
            ln = int(cl.group(1))
            body = blob[he + 4:he + 4 + ln]
            pos = he + 4 + ln
        elif te:
            nxt = blob.find(b'HTTP/1.', he + 4)
            raw = blob[he + 4:nxt if nxt >= 0 else n]
            body, _notes = http_body_decode(raw)
            pos = nxt if nxt >= 0 else n
        else:
            nxt = blob.find(b'HTTP/1.', he + 4)
            if nocl_cap:
                body = blob[he + 4:nxt if nxt >= 0 else min(n, he + 4 + nocl_cap)]
            else:
                body = blob[he + 4:nxt if nxt >= 0 else n]
            pos = nxt if nxt >= 0 else n
        out.append((int(m.group(1)), ctype, body))
    return out


def build_http_transactions(tcp_streams, findings, seen):
    """配对 HTTP 请求↔响应正文；webshell/RCE 命令回显、接口短文本并入置信度报告"""
    out, added = [], 0
    for k, segs in tcp_streams.items():
        blob = merge_stream(segs)
        if len(blob) < 40 or len(blob) > 3 * 1024 * 1024:
            continue
        reqs = list(HTTP_REQ_RE.finditer(blob))
        if not reqs:
            continue
        rsegs = tcp_streams.get((k[2], k[3], k[0], k[1]))
        if not rsegs:
            continue
        resps = parse_http_responses(merge_stream(rsegs))
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
