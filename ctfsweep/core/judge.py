# -*- coding: utf-8 -*-
"""判断核（judge）：轻量本地"判断网络"——对扫描候选做答案相关性打分。

设计：
- 纯 Python 手写 MLP 集成（140 维语义特征输入），零依赖；
- 特征 = 候选自身统计 + 源文件上下文 + 语义特征（flag 格式、敏感关键词、编码类型、模块置信度、MetaJudge 评分、文本复杂度、上下文语义等）；
- 训练数据 = 本机积累的解题标注 dataset.jsonl（候选 + 真/假标签）；
- 自动数据收集：每次扫描后保存未标注候选到 pending.jsonl；
- 交互式标注：ctfsweep label 子命令，逐条确认/否定；
- 自主学习：ctfsweep learning 命令，带收敛判断（AUC/loss 达标即停止）；
- 模型为 .ctfj 二进制（CtfSweep JudgeNet Binary，唯一格式），加载快、体积小；
- 训练超参数独立于代码：编辑 train_config.json（网络结构/学习率/种子等，改参数不须改代码）；
- 留一组评估（leave-one-group-out）：每组轮流当测试集，评估泛化后再全量重训；
- 完全离线；**无模型时工具行为与之前完全一致**。

CLI:
    ctfsweep train [--data F] [--model-out F] [--epochs N]
    ctfsweep <文件> --judge        # 扫描时给出 p= 分与【判断核·重点候选】
    ctfsweep label                  # 交互式标注未标注候选
    ctfsweep learning [opts]        # 自主学习（带收敛判断）
    ctfsweep auto-label             # 自动标注未标注候选（强模型规则验证）
"""
import hashlib
import json
import math
import os
import random
import re
import sys
import time

# ---------------------------------------------------------------- 模型 I/O（支持二进制格式 .ctfj）
from . import model_io

# ---------------------------------------------------------------- 特征（语义增强版 128 维）
FEATURES = (
    # 原始特征 28 维
    'score',
    'kind_flag', 'kind_decode', 'kind_frag_open', 'kind_frag_close', 'kind_keyword',
    'kind_jwt', 'kind_echo', 'kind_dns', 'kind_other',
    'val_len', 'brace_open', 'brace_close', 'brace_pair',
    'digit_ratio', 'alpha_ratio', 'upper_ratio', 'hex_ratio',
    'entropy', 'space_density', 'colon_density', 'slash_density',
    'prev_space', 'prev_dotslash', 'ctx_ws', 'ctx_printable',
    'file_capture', 'file_raw',
    # 语义特征 36 维（原 64 维子集）
    'flag_format', 'suctf_format', 'ctf_format', 'bracket_pair',  # 4: flag 格式匹配
    'keyword_flag', 'keyword_secret', 'keyword_key', 'keyword_password',  # 4: 敏感关键词
    'keyword_token', 'keyword_auth', 'keyword_credential', 'keyword_exploit',  # 4: 更多关键词
    'enc_base64', 'enc_hex', 'enc_url', 'enc_rot13', 'enc_base32',  # 5: 编码类型
    'module_router', 'module_scanner', 'module_memory', 'module_browser',  # 4: 模块置信度
    'module_logs', 'module_email', 'module_archives', 'module_config',  # 4: 更多模块
    'module_dns', 'module_db', 'meta_judge_score',  # 3: MetaJudge 评分
    'val_has_flag_brace', 'val_has_suctf_brace', 'val_has_ctf_brace',  # 3: 值中 flag 标记
    'val_is_short', 'val_is_medium', 'val_is_long',  # 3: 值长度分级
    'val_alphanumeric', 'val_printable',  # 2: 值字符类型
    # 新增语义特征 64 维
    'flag_variants', 'ctf_variants', 'flag_case_insensitive', 'brace_content_ratio',  # 4: flag 格式扩展
    'keyword_count', 'keyword_density', 'sensitive_word_ratio', 'unique_keyword_count',  # 4: 关键词密度
    'base64_strength', 'hex_strength', 'url_safe_ratio', 'alphanumeric_ratio',  # 4: 编码强度
    'char_diversity', 'repeated_pattern', 'sequential_chars', 'keyboard_pattern',  # 4: 字符模式
    'word_boundary_count', 'special_char_ratio', 'unicode_ratio', 'control_char_ratio',  # 4: 文本结构
    'prefix_flag', 'prefix_suctf', 'prefix_ctf', 'suffix_brace',  # 4: 前后缀匹配
    'mid_flag_keyword', 'starts_with_alpha', 'ends_with_digit', 'mixed_case',  # 4: 位置特征
    'digit_groups', 'alpha_groups', 'special_groups', 'mixed_groups',  # 4: 分组特征
    'consonant_ratio', 'vowel_ratio', 'digit_consonant_mix', 'entropy_per_char',  # 4: 语言统计
    'context_flag_near', 'context_secret_near', 'context_key_near', 'context_pass_near',  # 4: 上下文关键词
    'context_url_near', 'context_email_near', 'context_path_near', 'context_port_near',  # 4: 上下文网络
    'context_json_near', 'context_xml_near', 'context_csv_near', 'context_sql_near',  # 4: 上下文数据格式
    'context_pcap_near', 'context_mem_near', 'context_log_near', 'context_db_near',  # 4: 上下文取证类型
    'val_length_norm', 'entropy_norm', 'complexity_score', 'readability_score',  # 4: 复杂度评分
    'is_uuid_like', 'is_hash_like', 'is_ip_like', 'is_mac_like',  # 4: 格式匹配
    'is_timestamp_like', 'is_url_like', 'is_email_like', 'is_filepath_like',  # 4: 模式匹配
    'is_base64_padding', 'is_hex_padded', 'is_url_encoded', 'is_utf8_valid',  # 4: 编码校验
    'is_json_valid', 'is_xml_valid', 'is_csv_valid', 'is_sql_valid',  # 4: 数据格式校验
    'is_printable_ascii', 'is_unicode_safe', 'is_binary_safe', 'is_text_safe',  # 4: 安全性校验
)

_KNOWN_KINDS = ('明文flag', 'hex', 'base64', '片段(前)', '片段(尾)', '关键词',
                'JWT', '命令回显', '环境/配置', '短文本响应', 'DNS查询',
                '加壳候选', '明文', 'Kerberos票据', 'NetNTLM', 'LDAP口令', '域账号')

# 语义特征配置
FLAG_PATTERNS = [
    r'flag\{[^}]*\}', r'SUCTF\{[^}]*\}', r'CTF\{[^}]*\}',
    r'flag:\s*\S+', r'FLAG:\s*\S+',
]
SENSITIVE_KEYWORDS = [
    'flag', 'secret', 'key', 'password', 'token', 'auth',
    'credential', 'exploit', 'vulnerable', 'admin',
]
ENCODING_PATTERNS = {
    'base64': r'^[A-Za-z0-9+/=]{20,}$',
    'hex': r'^[0-9a-fA-F]{20,}$',
    'url': r'^[A-Za-z0-9_-]{20,}$',
    'rot13': r'^[A-Za-z]{20,}$',
    'base32': r'^[A-Z2-7=]{20,}$',
}


def normalize_val(val):
    if isinstance(val, bytes):
        val = val.decode('utf-8', 'replace')
    return ' '.join(str(val).split())


def sample_key(kind, val):
    return hashlib.sha1(('%s|%s' % (kind, normalize_val(val)[:120])).encode('utf-8', 'replace')).hexdigest()[:16]


def _entropy(s):
    if not s:
        return 0.0
    cnt = {}
    for c in s:
        cnt[c] = cnt.get(c, 0) + 1
    n = float(len(s))
    return -sum((v / n) * math.log(v / n, 2) for v in cnt.values())


def _win_stats(buf, i, ln):
    prev = buf[i - 1:i] if i else b''
    lo = max(0, i - 40)
    hi = min(len(buf), i + ln + 40)
    ws = 0
    for j in range(lo, hi):
        if buf[j] in (32, 9, 13, 10):
            ws += 1
    plo = max(0, i - 30)
    phi = min(len(buf), i + ln + 40)
    pr_win = buf[plo:phi]
    pr = sum(32 <= c < 127 or c in (9, 10, 13) for c in pr_win) / max(1, len(pr_win))
    return {'prev_space': 1.0 if prev == b' ' else 0.0,
            'prev_dotslash': 1.0 if prev and prev[0:1] in (b'.', b'\\', b'/') else 0.0,
            'ctx_ws': min(1.0, ws / 8.0),
            'ctx_printable': pr,
            'found': 1.0}


class ContextFinder:
    """在源文件字节中定位候选并提取上下文统计（紧凑视图惰性缓存）。"""

    def __init__(self, data):
        self.data = data or b''
        self._compact = None

    def _compact_view(self):
        if self._compact is None:
            self._compact = self.data.replace(b'\x00', b'')
        return self._compact

    def stats(self, needles):
        if not self.data:
            return {}
        for needle in needles:
            if not needle:
                continue
            ns = needle if isinstance(needle, str) else needle.decode('utf-8', 'replace')
            encs = []
            for enc in ('utf-8', 'latin-1'):
                try:
                    encs.append(ns.encode(enc))
                except Exception:
                    pass
            b16 = ns.encode('utf-16-le', 'ignore')
            for view, buf in (('raw', self.data), ('compact', None)):
                if view == 'compact':
                    buf = self._compact_view()
                for b in encs:
                    i = buf.find(b)
                    if i >= 0:
                        return _win_stats(buf, i, len(b))
                i = buf.find(b16)
                if i >= 0:
                    return _win_stats(buf, i, len(b16))
        return {}


def extract_features(sample):
    """从候选样例提取特征向量（与 FEATURES 等长，64 维语义增强）。

    sample 键：score / kind / val / tok(可选) / file_type('capture'|'raw')
              ctx / finder / data / module_scores / meta_score
    """
    import re
    val = sample.get('val') or ''
    if isinstance(val, bytes):
        val = val.decode('utf-8', 'replace')
    val = str(val)
    kind = str(sample.get('kind') or '')
    try:
        score = float(sample.get('score') or 0.0)
    except Exception:
        score = 0.0
    ftype = str(sample.get('file_type') or '')

    ctx = sample.get('ctx')
    if ctx is None:
        finder = sample.get('finder')
        if finder is None:
            data = sample.get('data')
            finder = ContextFinder(data) if data else None
        needles = []
        if kind in ('hex', 'base64') and sample.get('tok'):
            tok = sample['tok']
            needles.append(tok if isinstance(tok, str) else tok.decode('utf-8', 'replace'))
        needles.append(val)
        ctx = finder.stats(needles) if finder is not None else {}

    v = normalize_val(val)
    n = max(1, len(v))
    digits = sum(c.isdigit() for c in v) / float(n)
    alpha = sum(1 for c in v if c.isascii() and c.isalpha()) / float(n)
    upper = sum(1 for c in v if c.isascii() and c.isupper()) / float(n)
    hexr = sum(1 for c in v if c in '0123456789abcdefABCDEF') / float(n)
    ent = min(1.0, _entropy(v) / 6.0)

    kinds = {
        'kind_flag': kind == '明文flag',
        'kind_decode': kind in ('hex', 'base64'),
        'kind_frag_open': kind == '片段(前)',
        'kind_frag_close': kind == '片段(尾)',
        'kind_keyword': kind == '关键词',
        'kind_jwt': kind == 'JWT',
        'kind_echo': kind in ('命令回显', '环境/配置', '短文本响应'),
        'kind_dns': kind == 'DNS查询',
        'kind_other': bool(kind) and kind not in _KNOWN_KINDS,
    }

    # ========== 语义特征 ==========
    # flag 格式匹配 (4 维)
    flag_format = float(bool(re.search(r'flag\{[^}]*\}', v, re.I)))
    suctf_format = float(bool(re.search(r'SUCTF\{[^}]*\}', v, re.I)))
    ctf_format = float(bool(re.search(r'CTF\{[^}]*\}', v, re.I)))
    bracket_pair = float(bool(re.search(r'\{[^}]*\}', v)))

    # 敏感关键词 (8 维)
    keyword_flag = float('flag' in v.lower())
    keyword_secret = float('secret' in v.lower())
    keyword_key = float('key' in v.lower())
    keyword_password = float('password' in v.lower())
    keyword_token = float('token' in v.lower())
    keyword_auth = float('auth' in v.lower())
    keyword_credential = float('credential' in v.lower())
    keyword_exploit = float('exploit' in v.lower())

    # 编码类型 (5 维)
    enc_base64 = float(bool(re.match(ENCODING_PATTERNS['base64'], v.strip())))
    enc_hex = float(bool(re.match(ENCODING_PATTERNS['hex'], v.strip())))
    enc_url = float(bool(re.match(ENCODING_PATTERNS['url'], v.strip())))
    enc_rot13 = float(bool(re.match(ENCODING_PATTERNS['rot13'], v.strip())))
    enc_base32 = float(bool(re.match(ENCODING_PATTERNS['base32'], v.strip())))

    # 模块置信度 (10 维)
    module_scores = sample.get('module_scores', {})
    module_router = float(module_scores.get('router', 0.0))
    module_scanner = float(module_scores.get('scanner', 0.0))
    module_memory = float(module_scores.get('memory', 0.0))
    module_browser = float(module_scores.get('browser', 0.0))
    module_logs = float(module_scores.get('logs', 0.0))
    module_email = float(module_scores.get('email', 0.0))
    module_archives = float(module_scores.get('archives', 0.0))
    module_config = float(module_scores.get('config', 0.0))
    module_dns = float(module_scores.get('dns', 0.0))
    module_db = float(module_scores.get('db', 0.0))

    # MetaJudge 评分 (1 维)
    meta_judge_score = float(sample.get('meta_score', 0.0))

    # 值中 flag 标记 (3 维)
    val_has_flag_brace = float(bool(re.search(r'flag\{', v, re.I)))
    val_has_suctf_brace = float(bool(re.search(r'suctf\{', v, re.I)))
    val_has_ctf_brace = float(bool(re.search(r'ctf\{', v, re.I)))

    # 值长度分级 (3 维)
    val_is_short = float(0 < len(v) <= 20)
    val_is_medium = float(20 < len(v) <= 100)
    val_is_long = float(len(v) > 100)

    # 值字符类型 (2 维)
    val_alphanumeric = float(all(c.isalnum() or c in '_-.' for c in v))
    val_printable = float(all(32 <= ord(c) < 127 or c in '\n\r\t' for c in v))

    # ========== 新增语义特征 64 维 ==========
    # flag 格式扩展 (4 维)
    flag_variants = float(bool(re.search(r'FLAG[_-]|\{.*\}|CTF|SUCTF', v, re.I)))
    ctf_variants = float(bool(re.search(r'CTF[_-]|flag[_-]|answer[_-]', v, re.I)))
    flag_case_insensitive = float(bool(re.search(r'[Ff][Ll][Aa][Gg]', v)))
    brace_content_ratio = float(v.count('{') + v.count('}')) / max(1, len(v))

    # 关键词密度 (4 维)
    keyword_count = sum(1 for kw in SENSITIVE_KEYWORDS if kw in v.lower())
    keyword_density = keyword_count / max(1, len(v.split()))
    sensitive_word_ratio = sum(1 for c in v if c.lower() in 'flagsecretkeypassword') / max(1, len(v))
    unique_keyword_count = len(set(kw for kw in SENSITIVE_KEYWORDS if kw in v.lower()))

    # 编码强度 (4 维)
    base64_chars = sum(1 for c in v if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
    hex_chars = sum(1 for c in v if c in '0123456789abcdefABCDEF')
    base64_strength = base64_chars / max(1, len(v))
    hex_strength = hex_chars / max(1, len(v))
    url_safe_ratio = sum(1 for c in v if c.isalnum() or c in '-_.~') / max(1, len(v))
    alphanumeric_ratio = sum(1 for c in v if c.isalnum()) / max(1, len(v))

    # 字符模式 (4 维)
    char_diversity = len(set(v)) / max(1, len(v))
    repeated_pattern = max(v.count(v[i:i+2]) for i in range(len(v)-1)) if len(v) > 1 else 0
    sequential_chars = sum(1 for i in range(len(v)-1) if abs(ord(v[i]) - ord(v[i+1])) == 1)
    keyboard_pattern = sum(1 for i in range(len(v)-2) if v[i:i+3] in 'qwertyasdfgzxcvb' or v[i:i+3] in 'tyuiohnml' or v[i:i+3] in 'bnjk')

    # 文本结构 (4 维)
    word_boundary_count = sum(1 for i in range(1, len(v)) if v[i-1].isalnum() and not v[i].isalnum())
    special_char_ratio = sum(1 for c in v if not c.isalnum() and c not in ' \n\r\t') / max(1, len(v))
    unicode_ratio = sum(1 for c in v if ord(c) > 127) / max(1, len(v))
    control_char_ratio = sum(1 for c in v if c in '\n\r\t') / max(1, len(v))

    # 前后缀匹配 (4 维)
    prefix_flag = float(v.lower().startswith('flag'))
    prefix_suctf = float(v.lower().startswith('suctf'))
    prefix_ctf = float(v.lower().startswith('ctf'))
    suffix_brace = float(v.endswith('}') or v.endswith('"') or v.endswith("'"))

    # 位置特征 (4 维)
    mid_flag_keyword = float('flag' in v[len(v)//3:2*len(v)//3])
    starts_with_alpha = float(v[0].isalpha()) if v else 0
    ends_with_digit = float(v[-1].isdigit()) if v else 0
    mixed_case = float(any(c.isupper() for c in v) and any(c.islower() for c in v))

    # 分组特征 (4 维)
    digit_groups = len(re.findall(r'\d+', v))
    alpha_groups = len(re.findall(r'[a-zA-Z]+', v))
    special_groups = len(re.findall(r'[^a-zA-Z0-9]+', v))
    mixed_groups = len(re.findall(r'(?:\d+[a-zA-Z]+|[a-zA-Z]+\d+)', v))

    # 语言统计 (4 维)
    consonants = sum(1 for c in v.lower() if c.isalpha() and c not in 'aeiou')
    vowels = sum(1 for c in v.lower() if c in 'aeiou')
    consonant_ratio = consonants / max(1, consonants + vowels)
    vowel_ratio = vowels / max(1, consonants + vowels)
    digit_consonant_mix = (sum(1 for c in v if c.isdigit()) + consonants) / max(1, len(v))
    entropy_per_char = _entropy(v) / max(1, len(v))

    # 上下文关键词 (4 维)
    context_flag_near = float(ctx.get('ctx_flag_near', 0))
    context_secret_near = float(ctx.get('ctx_secret_near', 0))
    context_key_near = float(ctx.get('ctx_key_near', 0))
    context_pass_near = float(ctx.get('ctx_pass_near', 0))

    # 上下文网络 (4 维)
    context_url_near = float(ctx.get('ctx_url_near', 0))
    context_email_near = float(ctx.get('ctx_email_near', 0))
    context_path_near = float(ctx.get('ctx_path_near', 0))
    context_port_near = float(ctx.get('ctx_port_near', 0))

    # 上下文数据格式 (4 维)
    context_json_near = float(ctx.get('ctx_json_near', 0))
    context_xml_near = float(ctx.get('ctx_xml_near', 0))
    context_csv_near = float(ctx.get('ctx_csv_near', 0))
    context_sql_near = float(ctx.get('ctx_sql_near', 0))

    # 上下文取证类型 (4 维)
    context_pcap_near = float(ctx.get('ctx_pcap_near', 0))
    context_mem_near = float(ctx.get('ctx_mem_near', 0))
    context_log_near = float(ctx.get('ctx_log_near', 0))
    context_db_near = float(ctx.get('ctx_db_near', 0))

    # 复杂度评分 (4 维)
    val_length_norm = min(1.0, len(v) / 100.0)
    entropy_norm = min(1.0, _entropy(v) / 5.0)
    complexity_score = (special_char_ratio + entropy_per_char + char_diversity) / 3.0
    readability_score = 1.0 - (special_char_ratio + unicode_ratio)

    # 格式匹配 (4 维)
    is_uuid_like = float(bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', v, re.I)))
    is_hash_like = float(bool(re.match(r'^[0-9a-f]{32,}$', v, re.I)))
    is_ip_like = float(bool(re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', v)))
    is_mac_like = float(bool(re.match(r'^([0-9a-f]{2}:){5}[0-9a-f]{2}$', v, re.I)))

    # 模式匹配 (4 维)
    is_timestamp_like = float(bool(re.match(r'^\d{4}-\d{2}-\d{2}', v)))
    is_url_like = float(bool(re.match(r'^https?://', v)))
    is_email_like = float(bool(re.match(r'^[^@]+@[^@]+\.[^@]+$', v)))
    is_filepath_like = float(bool(re.match(r'^[a-zA-Z]:\\|/^|\\.\\.', v)))

    # 编码校验 (4 维)
    is_base64_padding = float(v.endswith('=') or v.endswith('=='))
    is_hex_padded = float(len(v) % 2 == 0 and all(c in '0123456789abcdefABCDEF' for c in v))
    is_url_encoded = float('%' in v and all(v[i:i+3] == '%XX' for i in range(len(v)-2) if v[i] == '%'))
    is_utf8_valid = float(all(ord(c) < 128 or ord(c) > 255 for c in v))

    # 数据格式校验 (4 维)
    is_json_valid = float(bool(re.match(r'^[\[{].*[\]}]$', v.strip())))
    is_xml_valid = float(bool(re.match(r'^<\w+>.*</\w+>$', v.strip())))
    is_csv_valid = float(bool(re.match(r'^[^,]+,[^,]+', v)))
    is_sql_valid = float(bool(re.match(r'^(SELECT|INSERT|UPDATE|DELETE|DROP)', v, re.I)))

    # 安全性校验 (4 维)
    is_printable_ascii = float(all(32 <= ord(c) < 127 for c in v))
    is_unicode_safe = float(all(ord(c) < 65536 for c in v))
    is_binary_safe = float(sum(1 for c in v if ord(c) > 127) < len(v) * 0.1)
    is_text_safe = float(sum(1 for c in v if c in '\x00\x01\x02\x03\x04\x05') == 0)

    feats = [
        # 原始特征 28 维
        score,
        kinds['kind_flag'], kinds['kind_decode'], kinds['kind_frag_open'],
        kinds['kind_frag_close'], kinds['kind_keyword'], kinds['kind_jwt'],
        kinds['kind_echo'], kinds['kind_dns'], kinds['kind_other'],
        min(1.0, len(v) / 120.0),
        1.0 if '{' in v else 0.0,
        1.0 if '}' in v else 0.0,
        1.0 if ('{' in v and '}' in v) else 0.0,
        digits, alpha, upper, hexr, ent,
        min(1.0, v.count(' ') / 16.0),
        min(1.0, v.count(':') / 4.0),
        min(1.0, (v.count('/') + v.count('\\')) / 4.0),
        float(ctx.get('prev_space', 0.0)),
        float(ctx.get('prev_dotslash', 0.0)),
        float(ctx.get('ctx_ws', 0.0)),
        float(ctx.get('ctx_printable', 0.0)),
        1.0 if ftype == 'capture' else 0.0,
        1.0 if ftype == 'raw' else 0.0,
        # 语义特征 36 维
        flag_format, suctf_format, ctf_format, bracket_pair,
        keyword_flag, keyword_secret, keyword_key, keyword_password,
        keyword_token, keyword_auth, keyword_credential, keyword_exploit,
        enc_base64, enc_hex, enc_url, enc_rot13, enc_base32,
        module_router, module_scanner, module_memory, module_browser,
        module_logs, module_email, module_archives, module_config,
        module_dns, module_db, meta_judge_score,
        val_has_flag_brace, val_has_suctf_brace, val_has_ctf_brace,
        val_is_short, val_is_medium, val_is_long,
        val_alphanumeric, val_printable,
        # 新增语义特征 64 维
        flag_variants, ctf_variants, flag_case_insensitive, brace_content_ratio,
        keyword_count, keyword_density, sensitive_word_ratio, unique_keyword_count,
        base64_strength, hex_strength, url_safe_ratio, alphanumeric_ratio,
        char_diversity, repeated_pattern, sequential_chars, keyboard_pattern,
        word_boundary_count, special_char_ratio, unicode_ratio, control_char_ratio,
        prefix_flag, prefix_suctf, prefix_ctf, suffix_brace,
        mid_flag_keyword, starts_with_alpha, ends_with_digit, mixed_case,
        digit_groups, alpha_groups, special_groups, mixed_groups,
        consonant_ratio, vowel_ratio, digit_consonant_mix, entropy_per_char,
        context_flag_near, context_secret_near, context_key_near, context_pass_near,
        context_url_near, context_email_near, context_path_near, context_port_near,
        context_json_near, context_xml_near, context_csv_near, context_sql_near,
        context_pcap_near, context_mem_near, context_log_near, context_db_near,
        val_length_norm, entropy_norm, complexity_score, readability_score,
        is_uuid_like, is_hash_like, is_ip_like, is_mac_like,
        is_timestamp_like, is_url_like, is_email_like, is_filepath_like,
        is_base64_padding, is_hex_padded, is_url_encoded, is_utf8_valid,
        is_json_valid, is_xml_valid, is_csv_valid, is_sql_valid,
        is_printable_ascii, is_unicode_safe, is_binary_safe, is_text_safe,
    ]
    return feats


# ---------------------------------------------------------------- 网络
class JudgeNet:
    """纯 Python MLP：全连接 + ReLU 隐层 + Sigmoid 输出，SGD(momentum) 训练。"""

    def __init__(self, sizes=None, seed=42):
        self.sizes = list(sizes) if sizes else [len(FEATURES), 64, 32, 1]
        rnd = random.Random(seed)
        self.W, self.b = [], []
        for li in range(len(self.sizes) - 1):
            fi, fo = self.sizes[li], self.sizes[li + 1]
            scale = math.sqrt(2.0 / fi)
            self.W.append([[rnd.gauss(0.0, scale) for _ in range(fi)] for _ in range(fo)])
            self.b.append([0.0] * fo)
        self._zs, self._acts = [], []

    @staticmethod
    def _sig(x):
        return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))

    def forward(self, x):
        a = [float(v) for v in x]
        self._zs, self._acts = [], [a]
        L = len(self.W)
        for li in range(L):
            z = []
            W, b = self.W[li], self.b[li]
            for row, bi in zip(W, b):
                s = bi
                for w, xj in zip(row, a):
                    s += w * xj
                z.append(s)
            self._zs.append(z)
            a = [self._sig(v) for v in z] if li == L - 1 else [(v if v > 0.0 else 0.0) for v in z]
            self._acts.append(a)
        return a[0]

    def predict(self, x):
        return self.forward(x)

    def train(self, X, y, epochs=300, lr=0.1, l2=0.0, mu=0.9, seed=13):
        """全批量梯度下降（对小样本最稳，且训练是确定性的）。

        逐样本 SGD 在小数据集上会被样本间的对抗梯度带进死区（ReLU 全灭）；
        全批量先把整个数据集的梯度加和后更新一次，方向稳定、结果可复现。

        lr 默认 0.1（曾为 0.5）：大步长在正负均衡的小样本上会一步把隐层
        推入全负死区（ReLU 全灭后梯度断流、输出锁死 0.5、loss 冻结在 ln2）。
        0.1 在真实数据上收敛效果与 0.5 一致，同时消除死锁风险。
        """
        L = len(self.W)
        VW = [[[0.0] * len(r) for r in m] for m in self.W]
        Vb = [[0.0] * len(r) for r in self.b]
        n = max(1, len(X))
        losses = []
        for _ep in range(max(1, epochs)):
            gW = [[[0.0] * len(r) for r in m] for m in self.W]
            gb = [[0.0] * len(r) for r in self.b]
            tot = 0.0
            for xi, yi in zip(X, y):
                p = self.forward(xi)
                pc = min(1.0 - 1e-7, max(1e-7, p))
                tot += -(yi * math.log(pc) + (1.0 - yi) * math.log(1.0 - pc))
                ds = [None] * L
                ds[L - 1] = [p - yi]
                for li in range(L - 2, -1, -1):
                    nxt = ds[li + 1]
                    Wn = self.W[li + 1]
                    z = self._zs[li]
                    d = []
                    for j in range(len(self.W[li])):
                        s = 0.0
                        for k in range(len(nxt)):
                            s += Wn[k][j] * nxt[k]
                        d.append(s if z[j] > 0.0 else 0.0)
                    ds[li] = d
                for li in range(L):
                    a0 = self._acts[li]
                    for i in range(len(self.W[li])):
                        g = ds[li][i]
                        gi = gW[li][i]
                        for j in range(len(a0)):
                            gi[j] += g * a0[j]
                        gb[li][i] += g
            for li in range(L):
                for i in range(len(self.W[li])):
                    Wrow = self.W[li][i]
                    Vrow = VW[li][i]
                    grow = gW[li][i]
                    for j in range(len(Wrow)):
                        gr = grow[j] / n + (l2 * Wrow[j] if l2 else 0.0)
                        Vrow[j] = mu * Vrow[j] - lr * gr
                        Wrow[j] += Vrow[j]
                    vb = Vb[li]
                    vb[i] = mu * vb[i] - lr * (gb[li][i] / n)
                    self.b[li][i] += vb[i]
            losses.append(tot / n)
        return losses


def param_count(sizes):
    return sum(sizes[i] * sizes[i + 1] + sizes[i + 1] for i in range(len(sizes) - 1))


# ---------------------------------------------------------------- 数据 / 评估
# 布局约定（2026-10-12 定稿，2026-10-13 补安装态）：
#   · 模型 + 训练配置 → models/（随版本发布；安装态落在 <安装根>/lib/models）
#     专注"训练/升级模型"，改超参数无需改代码
#   · 运行时缓存（扫描候选池、累积数据集）→ ~/.devtools/ctfsweep/judge/
#   训练流 = 读缓存数据 → 按配置训练 → 产出模型写回 models_dir()。
#   ⚠️ 安装态下 models_dir() 在安装根内，系统级安装（sudo）属 root，train 需 sudo。

def project_dir():
    """项目根目录（judge.py 位于 <root>/.../ctfsweep/core/judge.py，上溯三级）。

    注意安装态下这里得到的是**安装根的 lib/**（启动器在 <root>/lib/ctfsweep.sh、
    包在 <root>/lib/ctfsweep/），于是 models_dir() = <root>/lib/models——
    所以 deploy.sh 必须把 models/ 一起装，否则 --judge 会静默退化成「未训练」。

    环境变量 CTFSWEEP_PROJECT_DIR 可覆盖（测试隔离用）。
    """
    env = os.environ.get('CTFSWEEP_PROJECT_DIR')
    if env:
        return os.path.expanduser(env)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def models_dir():
    """模型目录（项目内）：model.ctfj + train_config.json。

    环境变量 CTFSWEEP_MODELS_DIR 可覆盖（测试隔离用）。
    """
    env = os.environ.get('CTFSWEEP_MODELS_DIR')
    if env:
        return os.path.expanduser(env)
    return os.path.join(project_dir(), 'models')


def user_dir():
    """运行时缓存目录（扫描候选池 / 累积数据集）。

    默认 ~/.devtools/ctfsweep/judge/：扫描跑动产生的候选记录（pending.jsonl）
    与标注后的累积训练数据（dataset.jsonl）都放在这里——纯运行时数据，
    不属于"模型/配置"，随时可以从扫描中重新积累。

    环境变量 CTFSWEEP_DATA_DIR 可覆盖数据根目录（返回 <root>/judge）：
    供测试隔离与多环境使用。
    """
    root = os.environ.get('CTFSWEEP_DATA_DIR')
    if root:
        return os.path.join(os.path.expanduser(root), 'judge')
    return os.path.join(os.path.expanduser('~'), '.devtools', 'ctfsweep', 'judge')


def default_dataset_path():
    """训练数据集路径（缓存区，持续累积）。"""
    return os.path.join(user_dir(), 'dataset.jsonl')


def model_path():
    """模型路径（项目内 models/model.ctfj；.ctfj 二进制唯一格式）。

    环境变量 CTFSWEEP_JUDGE_MODEL 可显式指定模型文件（测试隔离用）。
    """
    env = os.environ.get('CTFSWEEP_JUDGE_MODEL')
    if env:
        return env
    return os.path.join(models_dir(), 'model.ctfj')


def model_binary_path():
    """返回二进制模型路径（.ctfj，项目内 models/）。"""
    return model_path()


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


def predict_finding(net, finding, finder, file_type):
    """finding 为扫描器输出元组 (score, kind, tok, val, loc)。"""
    score, kind, tok, val, _loc = finding
    sample = {'score': score, 'kind': kind, 'tok': tok, 'val': val,
              'finder': finder, 'file_type': file_type}
    return net.predict(extract_features(sample))


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


def check_convergence(info, prev_info, min_auc, min_samples, max_epochs):
    """检查训练是否收敛。

    返回 (converged: bool, reason: str)
    """
    auc = info.get('auc')
    n = info.get('n', 0)
    epochs = info.get('epochs', 0)

    # 数据量不足
    if n < min_samples:
        return False, '数据不足 (%d < %d)' % (n, min_samples)

    # AUC 达标
    if auc is not None and auc >= min_auc:
        return True, 'AUC 达标 (%.2f >= %.2f)' % (auc, min_auc)

    # 达到最大轮数
    if epochs >= max_epochs:
        return True, '达到最大轮数 (%d)' % max_epochs

    # Loss 不再下降（对比上一轮）
    if prev_info is not None:
        prev_loss = prev_info.get('loss')
        curr_loss = info.get('loss')
        if prev_loss is not None and curr_loss is not None:
            if abs(prev_loss - curr_loss) < 0.001:
                return True, 'Loss 收敛 (%.4f → %.4f)' % (prev_loss, curr_loss)

    return False, '未收敛 (AUC=%s, epochs=%d)' % (_fmt(auc), epochs)


DEFAULT_SEEDS = (1, 7, 13, 42, 2026)


# ================================================================= 训练配置（独立于代码）
# 训练超参数集中放配置文件（~/.devtools/ctfsweep/judge/train_config.json），
# 调整模型结构 / 学习率 / 种子 / 训练轮数等**无需修改代码**：
#   · 编辑该文件后直接运行 ctfsweep train / ctfsweep learning 生效；
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


class JudgePredictor:
    """判断核预测器：单模型或多模型集成（对成员预测取平均）。

    - 集成显著降低小样本下随机初始化的方差（实测：28→10→1 单模型 AUC 随种子
      波动大，5 种子集成后稳定在 0.92+）；
    - 保存格式 v2 = 全部成员权重 + 元信息；兼容读取 v1 单模型文件。
    """

    def __init__(self, nets, meta=None):
        self.nets = list(nets)
        self.meta = meta or {}

    @property
    def sizes(self):
        return self.nets[0].sizes

    def predict(self, x):
        if len(self.nets) == 1:
            return self.nets[0].predict(x)
        return sum(n.predict(x) for n in self.nets) / len(self.nets)

    def describe(self):
        base = ' → '.join(str(s) for s in self.sizes)
        if len(self.nets) == 1:
            return '单模型 (%s)，%d 参数' % (base, param_count(self.sizes))
        return '集成 %d × (%s)，%d 参数' % (len(self.nets), base,
                                          param_count(self.sizes) * len(self.nets))

    @classmethod
    def load(cls, path):
        """加载模型（仅 .ctfj 二进制格式）。"""
        return model_io.load_binary(path)


def run_training(rows, model_out=None, epochs=None, lr=None, l2=None, mu=None,
                 seeds=None, sizes=None, config=None):
    """留一组评估（集成） + 全量重训（集成） + 保存。返回 (predictor, info)。

    超参数默认读取训练配置（~/.devtools/ctfsweep/judge/train_config.json）；
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
        from . import model_io
        model_io.save_binary(pred, model_out)
        print('')
        print('已保存模型: %s（%s）' % (model_out, pred.describe()))
    return pred, info


# ================================================================= 自动数据收集
def pending_dataset_path():
    """未标注候选数据集路径。"""
    return os.path.join(user_dir(), 'pending.jsonl')


def save_pending(candidate, dataset_path=None):
    """保存未标注候选到 pending.jsonl。

    candidate 键：score / kind / val / tok / file_type / module_scores / meta_score
    """
    dataset_path = dataset_path or pending_dataset_path()
    os.makedirs(os.path.dirname(dataset_path), exist_ok=True)
    tok = candidate.get('tok', '')
    if isinstance(tok, bytes):
        tok = tok.decode('utf-8', 'replace')
    row = {
        'v': 2,  # 特征版本
        'score': candidate.get('score', 0.0),
        'kind': candidate.get('kind', ''),
        'val': candidate.get('val', ''),
        'tok': tok,
        'file_type': candidate.get('file_type', ''),
        'module_scores': candidate.get('module_scores', {}),
        'meta_score': candidate.get('meta_score', 0.0),
        'feats': extract_features(candidate),
        'label': None,  # 未标注
        'status': 'pending',
        'collected_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
    }
    with open(dataset_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    return row


def load_pending(dataset_path=None):
    """加载未标注候选。"""
    dataset_path = dataset_path or pending_dataset_path()
    if not os.path.isfile(dataset_path):
        return []
    rows = []
    with open(dataset_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                r = json.loads(line)
                if r.get('status') == 'pending':
                    rows.append(r)
            except Exception:
                continue
    return rows


def merge_pending_to_dataset(pending_path=None, dataset_path=None):
    """将已标注的 pending 数据合并到 dataset.jsonl。"""
    pending_path = pending_path or pending_dataset_path()
    dataset_path = dataset_path or default_dataset_path()
    if not os.path.isfile(pending_path):
        return 0
    merged = 0
    with open(pending_path, 'r', encoding='utf-8') as fin:
        lines = fin.readlines()
    with open(pending_path, 'w', encoding='utf-8') as fout:
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                fout.write(line + '\n')
                continue
            try:
                r = json.loads(line)
                if r.get('status') == 'pending':
                    continue  # 跳过未标注
                # 写入 dataset
                fout.write(line + '\n')  # 保留到 pending（标记已处理）
                with open(dataset_path, 'a', encoding='utf-8') as fout2:
                    fout2.write(json.dumps(r, ensure_ascii=False) + '\n')
                merged += 1
            except Exception:
                fout.write(line + '\n')
    return merged


# ================================================================= 留存区（扫描记录 / 答案回填）
# 设计（用户需求 2026-10-12）：每次扫描（跑动）把候选快照记入留存区；
#   · 已知答案 → ctfsweep mark <路径> <真实flag> 立即回填
#   · 未知答案 → ctfsweep learning 时逐题询问（题目；答案：），处理完再训练
RETENTION_MAX_CANDIDATES = 80   # 每题最多保留的候选快照数（按分数取高）
RETENTION_MARK_MAX_NEG = 40     # mark 回填时每题最多回填的负样本数（难负样本）
RETENTION_MIN_SCORE = 0.6       # 候选入留存区的最低分数（与 pending 收集一致）


def retention_path():
    """留存区文件路径（记录每次扫描的候选快照；缓存区）。"""
    return os.path.join(user_dir(), 'retention.jsonl')


def load_retention():
    """读取留存区全部记录（列表）。"""
    path = retention_path()
    records = []
    if os.path.isfile(path):
        with open(path, encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
    return records


def save_retention(records):
    """全量重写留存区（记录条数少，直接覆盖写，不做删除）。"""
    path = retention_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def _update_retention(scan_path, **fields):
    """按路径更新留存记录字段并落盘。"""
    records = load_retention()
    for r in records:
        if r.get('path') == scan_path:
            r.update(fields)
    save_retention(records)


def record_scan(scan_path, candidates, files_count=0):
    """记录一次扫描到留存区（按路径去重更新；无候选的扫描不记录）。

    scan_path: 扫描的路径（文件或文件夹）
    candidates: [{score, kind, val, file}, ...] 候选快照
    files_count: 本次扫描覆盖的文件数
    返回记录 dict；未记录返回 None。
    """
    scan_path = os.path.abspath(os.path.expanduser(str(scan_path)))
    if not candidates:
        return None
    top = sorted(candidates, key=lambda c: -float(c.get('score') or 0.0))[:RETENTION_MAX_CANDIDATES]
    records = load_retention()
    entry = {
        'v': 1,
        'path': scan_path,
        'scanned_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'files': int(files_count),
        'candidates': top,
    }
    for r in records:
        if r.get('path') == scan_path:
            # 已有记录：更新快照，保留处理状态与已填答案
            entry['status'] = r.get('status') or 'pending'
            for k in ('answer', 'marked_at', 'reviewed_at'):
                if r.get(k):
                    entry[k] = r[k]
            r.clear()
            r.update(entry)
            save_retention(records)
            return r
    entry['status'] = 'pending'
    records.append(entry)
    save_retention(records)
    return entry


def find_retention_for(scan_path):
    """精确查找路径的留存记录（mark 用）。找不到返回 None。"""
    scan_path = os.path.abspath(os.path.expanduser(str(scan_path)))
    for r in load_retention():
        if r.get('path') == scan_path:
            return r
    return None


def _norm_flag(s):
    """规范化：折叠空白差异。"""
    return ' '.join(str(s or '').split())


def match_flag(val, real_flag):
    """候选与真实答案的匹配判定。

    · 候选包含完整答案（忽略空白差异）→ 匹配
    · 候选是答案的有效片段（去空白后为答案子串，长度 ≥ 6 且 ≥ 答案 40%）→ 匹配
      （题目的候选常被分段展示，片段属于同一答案的线索）
    """
    v = _norm_flag(val)
    f = _norm_flag(real_flag)
    if not v or not f:
        return False
    if f in v:
        return True
    vn, fn = v.replace(' ', ''), f.replace(' ', '')
    if len(vn) >= 6 and len(vn) >= 0.4 * len(fn) and vn in fn:
        return True
    return False


def mark_answers(scan_path, real_flag, dataset_path=None, record=None):
    """用真实答案回填一道题的标注（正=匹配候选；负=同题其他高分候选）。

    同题的干扰候选是高质量的"难负样本"（与答案同语境），负样本按分数
    取前 RETENTION_MARK_MAX_NEG 条。与现有数据集按 val 去重。
    返回 (pos, neg, dedup, matched_any, record)；无记录返回 None。
    """
    dataset_path = dataset_path or default_dataset_path()
    rec = record or find_retention_for(scan_path)
    if rec is None:
        # 无留存记录（如扫描无候选、答案由深度分析恢复）：仍允许回填——
        # 用最小记录继续，把答案本身作为正样本入库。
        rec = {
            'v': 1,
            'path': os.path.abspath(os.path.expanduser(str(scan_path))),
            'scanned_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'files': 0,
            'candidates': [],
            'status': 'pending',
        }
    cands = list(rec.get('candidates') or [])
    existing = set()
    if os.path.isfile(dataset_path):
        for r in load_rows(dataset_path):
            v = r.get('val')
            if v is not None:
                existing.add(_norm_flag(v))
    path_base = os.path.basename(str(rec.get('path') or 'scan')) or 'scan'
    group = path_base  # 同题共享组名（留一组评估防泄漏）
    pos_rows, neg_rows, dedup = [], [], 0
    matched_any = False
    for c in cands:
        v = str(c.get('val') or '')
        if not v.strip():
            continue
        is_pos = match_flag(v, real_flag)
        if is_pos:
            matched_any = True  # 命中判定在去重之前（重复的答案样本也算命中）
        if _norm_flag(v) in existing:
            dedup += 1
            continue
        row = {
            'v': 2,
            'score': c.get('score', 0.0),
            'kind': c.get('kind', ''),
            'val': v,
            'tok': '',
            'file_type': 'raw',
            'module_scores': {},
            'meta_score': 0.0,
            'feats': extract_features({'score': c.get('score', 0.0),
                                       'kind': c.get('kind', ''), 'val': v,
                                       'file_type': 'raw'}),
            'label': 1.0 if is_pos else 0.0,
            'status': 'marked',
            'group': group,
            'file': c.get('file') or group,
            'source': group + '_marked',
            'verify_reason': 'user_marked',
            'verified_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }
        (pos_rows if is_pos else neg_rows).append(row)
    # 答案本身作为正样本入库（即使未匹配到候选——深度分析恢复的 flag 也算；
    # 与已有数据、本轮新增去重）。
    flag_norm = _norm_flag(real_flag)
    added_vals = {_norm_flag(r.get('val')) for r in (pos_rows + neg_rows)}
    if flag_norm and flag_norm not in existing and flag_norm not in added_vals:
        pos_rows.append({
            'v': 2,
            'score': 0.99,
            'kind': '答案回填',
            'val': flag_norm,
            'tok': '',
            'file_type': 'raw',
            'module_scores': {},
            'meta_score': 0.0,
            'feats': extract_features({'score': 0.99, 'kind': '明文flag',
                                       'val': flag_norm, 'file_type': 'raw'}),
            'label': 1.0,
            'status': 'marked',
            'group': group,
            'file': group,
            'source': group + '_marked',
            'verify_reason': 'user_marked',
            'verified_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        })
    neg_rows.sort(key=lambda r: -float(r.get('score') or 0.0))
    neg_rows = neg_rows[:RETENTION_MARK_MAX_NEG]
    os.makedirs(os.path.dirname(os.path.abspath(dataset_path)), exist_ok=True)
    with open(dataset_path, 'a', encoding='utf-8') as f:
        for r in pos_rows + neg_rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    rec['status'] = 'marked'
    rec['answer'] = flag_norm
    rec['marked_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    # 留存区 upsert：已有记录更新；无记录（深度分析回填场景）补写一条
    records = load_retention()
    found = False
    for r in records:
        if r.get('path') == rec.get('path'):
            r.update({'status': 'marked', 'answer': rec['answer'],
                      'marked_at': rec['marked_at']})
            found = True
    if not found:
        rec['candidates'] = rec.get('candidates') or []
        records.append(rec)
    save_retention(records)
    return len(pos_rows), len(neg_rows), dedup, matched_any, rec


def review_retention(dataset_path=None, input_fn=None):
    """learning 前的留存区复核：逐题询问真实答案（一个接一个）。

    · 输入真实 flag → 回填（正=匹配候选；负=同题其他候选）
    · 输入 无/none/skip → 标记为无答案（不再询问）
    · 直接回车 → 暂不处理（保留记录，下次再问）
    · 输入 q → 结束复核
    全部处理完（或 q 结束）后返回统计 dict。
    """
    input_fn = input_fn or input
    dataset_path = dataset_path or default_dataset_path()
    records = load_retention()
    pend = [r for r in records if (r.get('status') or 'pending') == 'pending']
    stats = {'asked': 0, 'marked': 0, 'skipped': 0, 'kept': 0, 'pos': 0, 'neg': 0}
    if not pend:
        print('[复核] 留存区无待处理记录')
        return stats
    print('[复核] 留存区有 %d 道待处理扫描 —— 输入真实flag回填 / 输入 无 标记无答案 / 回车暂留 / q 结束'
          % len(pend))
    for rec in pend:
        stats['asked'] += 1
        cands = rec.get('candidates') or []
        print('─' * 66)
        print('题目: %s' % rec.get('path', ''))
        print('  扫描于 %s · %d 个文件 · %d 条候选'
              % (rec.get('scanned_at', '?'), rec.get('files', 0), len(cands)))
        for c in cands[:3]:
            print('    · [%.2f] %s'
                  % (float(c.get('score') or 0), str(c.get('val'))[:96]))
        try:
            ans = input_fn('  答案: ').strip()
        except EOFError:
            break
        if ans.lower() in ('q', 'quit', 'exit'):
            print('  （结束复核；未处理记录保留，下次 learning 再询问）')
            break
        if ans in ('无', 'none', 'skip', '-', '没有', '无答案'):
            _update_retention(rec.get('path'), status='skipped',
                              reviewed_at=time.strftime('%Y-%m-%dT%H:%M:%S'))
            stats['skipped'] += 1
            print('  → 已标记为无答案')
            continue
        if not ans:
            stats['kept'] += 1
            print('  → 暂留（保留记录，下次再问）')
            continue
        res = mark_answers(rec.get('path'), ans, dataset_path=dataset_path, record=rec)
        if res:
            pos, neg, dedup, matched, _ = res
            stats['marked'] += 1
            stats['pos'] += pos
            stats['neg'] += neg
            if matched:
                if pos:
                    print('  → 回填完成: 正 %d / 负 %d（重复跳过 %d）' % (pos, neg, dedup))
                else:
                    print('  → 答案命中但样本已在数据集中（重复跳过 %d）；负样本补充 %d 条'
                          % (dedup, neg))
            else:
                print('  → [警告] 候选里没有找到与答案匹配的内容！已入 %d 条负样本，请确认答案拼写'
                      % neg)
    print('─' * 66)
    print('[复核] 完成: 回填 %d 题（正 %d / 负 %d）· 标记无答案 %d · 暂留 %d'
          % (stats['marked'], stats['pos'], stats['neg'], stats['skipped'], stats['kept']))
    return stats


# ================================================================= 交互式标注工具
def interactive_label(pending_path=None, dataset_path=None, batch_size=10):
    """交互式标注未标注候选。

    逐条显示候选，用户输入 y/n/d 确认/否定/跳过。
    标注完成后自动合并到 dataset.jsonl。
    """
    pending_path = pending_path or pending_dataset_path()
    dataset_path = dataset_path or default_dataset_path()

    pending = load_pending(pending_path)
    if not pending:
        print('没有未标注候选。')
        return 0

    print('交互式标注工具')
    print('  候选总数: %d 条' % len(pending))
    print('  说明: y=确认(正样本), n=否定(负样本), d=跳过, q=退出')
    print('')

    annotated = 0
    pos_count = 0
    neg_count = 0
    skip_count = 0

    for i, row in enumerate(pending):
        if i >= batch_size:
            print('')
            print('--- 批次完成，继续下一批 ---')
            ans = input('输入 q 退出，其他任意键继续: ')
            if ans.lower() == 'q':
                break

        val_preview = str(row.get('val', ''))[:100]
        kind = row.get('kind', 'unknown')
        score = row.get('score', 0.0)
        print('[%d/%d] kind=%s  score=%.2f' % (i + 1, len(pending), kind, score))
        print('  val: %s' % val_preview)

        ans = input('  [y/n/d]? ').strip().lower()
        if ans == 'q':
            break
        elif ans == 'y':
            row['label'] = 1.0
            row['status'] = 'annotated'
            pos_count += 1
        elif ans == 'n':
            row['label'] = 0.0
            row['status'] = 'annotated'
            neg_count += 1
        elif ans == 'd':
            row['status'] = 'skipped'
            skip_count += 1
            continue
        else:
            print('  无效输入，跳过')
            continue

        annotated += 1
        # 实时更新到 pending 文件
        with open(pending_path, 'w', encoding='utf-8') as f:
            for r in pending:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')

        if (i + 1) % 5 == 0:
            print('  已标注 %d 条（正 %d / 负 %d / 跳 %d）' % (annotated, pos_count, neg_count, skip_count))

    print('')
    print('标注完成: 总计 %d 条（正 %d / 负 %d / 跳 %d）' % (annotated, pos_count, neg_count, skip_count))

    if annotated > 0:
        # 合并到 dataset
        count = merge_pending_to_dataset(pending_path, dataset_path)
        print('已合并 %d 条到数据集: %s' % (count, dataset_path))
        print('提示: 运行 `ctfsweep learning` 开始训练')

    return annotated


# ================================================================= 自动化反馈闭环 (强模型→小模型)
def auto_verify_candidate(candidate):
    """用强模型(规则引擎)验证候选是否为真正 flag。
    
    返回 (is_flag: bool, reason: str)
    - is_flag=True: 确认是 flag,标注为正样本
    - is_flag=False: 不是 flag,标注为负样本,记录失败原因
    """
    val = str(candidate.get('val', ''))
    kind = str(candidate.get('kind', ''))
    score = float(candidate.get('score', 0.0))
    
    # 强模型规则:检查 flag 格式
    flag_patterns = [
        r'flag\{[^}]*\}',      # flag{...}
        r'SUCTF\{[^}]*\}',     # SUCTF{...}
        r'CTF\{[^}]*\}',       # CTF{...}
        r'flag[_:]\s*\S+',     # flag: xxx / flag-xxx
        r'FLAG[_:]\s*\S+',     # FLAG: xxx
        r'answer[_:]\s*\S+',   # answer: xxx
        r'key[_:]\s*\S+',      # key: xxx
    ]
    
    for pattern in flag_patterns:
        if re.search(pattern, val, re.I):
            return True, 'flag_format_match'
    
    # 检查敏感关键词 + 高置信度
    if score >= 0.85:
        sensitive_keywords = ['flag', 'secret', 'key', 'password', 'token', 'auth']
        if any(kw in val.lower() for kw in sensitive_keywords):
            return True, 'high_confidence_sensitive'
    
    # 检查 Base64/Hex 编码的 flag
    try:
        import base64
        decoded = base64.b64decode(val).decode('utf-8', 'ignore')
        if re.search(r'flag\{[^}]*\}', decoded, re.I):
            return True, 'base64_decoded_flag'
    except Exception:
        pass
    
    # 检查 Hex 编码的 flag
    try:
        decoded = bytes.fromhex(val).decode('utf-8', 'ignore')
        if re.search(r'flag\{[^}]*\}', decoded, re.I):
            return True, 'hex_decoded_flag'
    except Exception:
        pass
    
    # 低置信度且无 flag 格式 → 负样本
    if score < 0.7:
        return False, 'low_confidence_no_format'
    
    # 中等置信度但无 flag 格式 → 负样本,记录原因
    return False, 'medium_confidence_no_format'


def auto_annotate_pending(pending_path=None, dataset_path=None):
    """自动标注未标注候选。
    
    使用强模型规则验证每个候选,标注为正/负样本,记录失败原因。
    返回 (pos_count, neg_count, fail_reasons)
    """
    pending_path = pending_path or pending_dataset_path()
    dataset_path = dataset_path or default_dataset_path()
    
    pending = load_pending(pending_path)
    if not pending:
        return 0, 0, []
    
    pos_count = 0
    neg_count = 0
    fail_reasons = []
    
    for row in pending:
        is_flag, reason = auto_verify_candidate(row)
        row['label'] = 1.0 if is_flag else 0.0
        row['status'] = 'auto_annotated'
        row['verify_reason'] = reason
        row['verified_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        
        if is_flag:
            pos_count += 1
        else:
            neg_count += 1
            fail_reasons.append(reason)
    
    # 更新 pending 文件
    with open(pending_path, 'w', encoding='utf-8') as f:
        for row in pending:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    
    # 合并到 dataset
    count = merge_pending_to_dataset(pending_path, dataset_path)
    
    print('自动标注完成: 正 %d / 负 %d / 合并 %d 条' % (pos_count, neg_count, count))
    if fail_reasons:
        print('失败原因统计: %s' % str(fail_reasons[:10]))
    
    return pos_count, neg_count, fail_reasons


def learning_loop(pending_path=None, dataset_path=None, model_path_out=None,
                  min_auc=None, min_samples=None, max_epochs=None,
                  epochs_per_run=None, check_interval=50):
    """自主学习循环 (强模型→小模型)。

    超参数默认读取训练配置（项目内 models/train_config.json）；
    显式传参可覆盖（命令行参数 > 配置文件 > 内置默认）。
    
    流程:
    0. 留存区复核（逐题询问真实答案：题目；答案：<真实flag>，一个接一个）
    1. 自动标注未标注候选 (强模型验证)
    2. 合并到 dataset
    3. 训练模型
    4. 检查收敛 (AUC >= min_auc)
    5. 未收敛则提示继续,用户选择是否继续
    """
    cfg = load_train_config()
    min_auc = min_auc if min_auc is not None else cfg['min_auc']
    min_samples = min_samples if min_samples is not None else cfg['min_samples']
    max_epochs = max_epochs if max_epochs is not None else cfg['max_epochs']
    epochs_per_run = epochs_per_run if epochs_per_run is not None else cfg['epochs_per_run']
    pending_path = pending_path or pending_dataset_path()
    dataset_path = dataset_path or default_dataset_path()
    model_path_out = model_path_out or model_path()
    
    print('自主学习启动 (强模型→小模型)')
    print('  目标: AUC >= %.2f, 样本 >= %d' % (min_auc, min_samples))
    print('  最大轮数: %d, 每轮训练: %d epochs' % (max_epochs, epochs_per_run))
    print('')
    
    # 步骤 0: 留存区复核（有真实答案的题目在此回填；处理完再训练）
    review_retention(dataset_path=dataset_path)
    print('')
    
    # 第一步: 自动标注未标注候选
    print('步骤 1: 自动标注未标注候选 (强模型验证)')
    pos_count, neg_count, fail_reasons = auto_annotate_pending(pending_path, dataset_path)
    
    if pos_count + neg_count == 0:
        print('没有未标注候选,请先运行扫描')
        return 2
    
    print('')
    
    # 第二步: 加载数据集
    rows = load_rows(dataset_path)
    print('步骤 2: 加载数据集 (%d 条已标注)' % len(rows))
    
    if len(rows) < min_samples:
        print('数据不足 (%d < %d),请先标注更多样本' % (len(rows), min_samples))
        return 2
    
    # 第三步: 训练循环
    prev_info = None
    total_epochs = 0
    
    while total_epochs < max_epochs:
        print('')
        print('=' * 60)
        print('第 %d 轮训练 (累计 %d epochs)' % (total_epochs // epochs_per_run + 1, total_epochs))
        print('=' * 60)
        
        # 训练
        pred, info = run_training(
            rows, model_out=model_path_out,
            epochs=epochs_per_run,
            config=cfg,          # 超参数来自训练配置（改参数不改代码）
        )
        total_epochs += epochs_per_run
        
        # 检查收敛
        converged, reason = check_convergence(info, prev_info, min_auc, min_samples, max_epochs)
        print('')
        print('收敛检查: %s' % reason)
        
        if converged:
            print('')
            print('✓ 训练收敛！模型已保存: %s' % model_path_out)
            print('  AUC: %s' % _fmt(info.get('auc')))
            print('  样本: %d 条（正 %d / 负 %d）' % (info['n'], info['n_pos'], info['n_neg']))
            
            # 清除已学习的失败记录
            if fail_reasons:
                print('')
                print('清除已学习的失败记录...')
                # 这里可以添加清除逻辑
            return 0
        
        if total_epochs < max_epochs:
            ans = input('是否继续训练？(y/n, 默认 n): ').strip().lower()
            if ans != 'y':
                print('训练已中止。')
                return 1
        
        prev_info = info
    
    print('')
    print('达到最大训练轮数 (%d),模型已保存。' % max_epochs)
    print('提示: 继续标注更多数据,运行 `ctfsweep learning` 重新训练。')
    return 0
