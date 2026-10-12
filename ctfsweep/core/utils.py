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


# 置信度分档阈值（全项目唯一口径：报告、元判断核、统计都走这里）
BAND_HIGH = 0.85
BAND_MID = 0.55


def level_of(score):
    return '高' if score >= BAND_HIGH else ('中' if score >= BAND_MID else '低')


def text_like_window(b, ascii_thresh=0.8):
    """判断字节窗口是否像"真实文本"（剔除二进制区里的关键词字节巧合）。

    场景：图片/压缩/加密数据里，`flag`、`ctf` 这类关键词会以**字节巧合**出现，
    而它的上下文在 latin-1 视角下"貌似可打印"——0x80-0xFF 里的高位字节被当成字母
    （JPEG 数据实测可打印率约 75%，`scan_blob` 原来的 0.7 闸门挡不住）。

    判定（满足任一即为文本）：
      1) 可打印 ASCII（含 \\t\\n\\r）占比 >= `ascii_thresh`；
      2) 能**严格** UTF-8 解码，且解码后字符可打印率 >= 0.9（中文文本页面）。
    其余 → 视为二进制区，丢弃该关键词命中。
    """
    if not b:
        return False
    ascii_ok = sum(1 for c in b if 32 <= c < 127 or c in (9, 10, 13))
    if ascii_ok >= len(b) * ascii_thresh:
        return True
    try:
        s = b.decode('utf-8')
    except Exception:
        return False
    if not s:
        return False
    ok = sum(1 for ch in s if ch.isprintable() or ch in '\r\n\t')
    return ok >= len(s) * 0.9


def kw_boundary_ok(text, i, kw):
    """关键词命中位置边界检查（str 文本）：区分独立词与词内误报。

    返回 False 的两种噪音形态：
      1) 关键字后紧跟 ASCII 字母：FolderValueFlags、MsCtfMonitor
      2) 关键字处于标识符内部（前一位是字母/数字/下划线）且后一位不是 '{'：
         create_pdo_flag、msctf_31bf
    真实线索（flag{ / flag1 / flag2 / \\flag3 / the flag is）不受影响。
    """
    nxt = text[i + len(kw): i + len(kw) + 1]
    if nxt and nxt.isascii() and nxt.isalpha():
        return False
    if nxt != '{':
        prv = text[i - 1: i] if i else ''
        if prv and prv.isascii() and (prv.isalnum() or prv == '_'):
            return False
    return True


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
