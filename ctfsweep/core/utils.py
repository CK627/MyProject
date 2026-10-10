# -*- coding: utf-8 -*-
"""基础工具：共享正则、编码尝试、置信度分级、时间格式化"""
import base64
import re
import time

FLAG_RE = re.compile(rb'(?i)(flag|ctf|key|sec|solar|admin)[A-Za-z0-9_\-]{0,8}\{[^}\r\n\x00]{4,160}\}')
HEX_RUN = re.compile(rb'(?<![0-9a-fA-F])[0-9a-fA-F]{16,}(?![0-9a-fA-F])')
B64_RUN = re.compile(rb'[A-Za-z0-9+/]{16,}={0,2}')
BRACE_CORE = re.compile(rb'\{[a-z0-9_\-]{4,}\}')
JWT_RE = re.compile(rb'eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{6,}')
SECRET_LINE_RE = re.compile(rb'(?m)^[ \t]*([A-Za-z][A-Za-z0-9_]{1,40})=([^\r\n\x00<>]{2,180})')
SENSITIVE_NAME_RE = re.compile(rb'(?i)(^|_)sk$|key|token|secret|pass|pwd|api|auth|cred')


def level_of(score):
    return '高' if score >= 0.85 else ('中' if score >= 0.55 else '低')


def try_hex(tok):
    try:
        return bytes.fromhex(tok.decode('ascii'))
    except Exception:
        return None


def try_b64(tok):
    s = tok.strip(b'=')
    s = s.replace(b'-', b'+').replace(b'_', b'/')
    pad = b'=' * ((4 - len(s) % 4) % 4)
    try:
        return base64.b64decode(s + pad, validate=False)
    except Exception:
        return None


def printable_ratio(b):
    if not b:
        return 0.0
    return sum(32 <= c < 127 or c in (9, 10, 13) for c in b) / len(b)


def decode_score(dec, keywords):
    if FLAG_RE.search(dec):
        return 0.95
    low = dec.lower()
    has_kw = any(k.encode() in low for k in keywords)
    has_brace = b'{' in dec and b'}' in dec and BRACE_CORE.search(dec)
    if has_kw and has_brace:
        return 0.70
    if has_brace:
        return 0.65
    return 0.60


def ts_str(ts):
    try:
        return time.strftime('%m/%d/%Y %H:%M:%S', time.localtime(ts))
    except Exception:
        return '?'
