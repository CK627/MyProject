# -*- coding: utf-8 -*-
"""判断核（judge）：轻量本地"判断网络"——对扫描候选做答案相关性打分。

本模块是**纯推理库**，运行时只做两件事：
- 从 .ctfj 二进制读回模型（`JudgePredictor.load` → `model_io`），
- 对扫描候选取特征并打分（`predict_finding` / `extract_features`）。

模型**随版本发布**（`models/model.ctfj`，安装态落在 <安装根>/lib/models）——
deploy.sh 必须把它一起装，否则 `--judge` 会静默退化成「未训练」。
离线训练与数据生成不在安装载荷内，脚本在仓库 `lab/`：
    python3 lab/train.py --data lab/dataset.jsonl      # 训练 → models/model.ctfj
    python3 lab/build_dataset.py                       # 从题库构建训练语料
    python3 lab/data_generator.py                      # 合成训练样本

设计：
- 纯 Python 手写 MLP 集成（140 维语义特征输入），零依赖；
- 特征 = 候选自身统计 + 源文件上下文 + 语义特征（flag 格式、敏感关键词、编码类型、模块置信度、MetaJudge 评分、文本复杂度、上下文语义等）；
- 模型为 .ctfj 二进制（CtfSweep JudgeNet Binary，唯一格式），加载快、体积小；
- 完全离线；**无模型时工具行为与之前完全一致**。

CLI:
    ctfsweep <文件> --judge        # 扫描时给出 p= 分与【判断核·重点候选】
"""
import math
import os
import random
import re

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


# ---------------------------------------------------------------- 模型定位
# 布局约定（2026-10-13 去自学习后）：
#   · 模型 + 训练超参 → models/（随版本发布；安装态落在 <安装根>/lib/models）
#     模型是**离线统一训练**的产物，运行时不训练、不写这里。
#   · 扫描缓存 → ~/.devtools/ctfsweep/cache/（见 core/paths.py），与模型互不相干。
#   ⚠️ 安装态下 models_dir() 在安装根内，所以 deploy.sh 必须把 models/ 一起装。

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


def model_path():
    """模型路径（项目内 models/model.ctfj；.ctfj 二进制唯一格式）。

    环境变量 CTFSWEEP_JUDGE_MODEL 可显式指定模型文件（测试隔离用）。
    """
    env = os.environ.get('CTFSWEEP_JUDGE_MODEL')
    if env:
        return env
    return os.path.join(models_dir(), 'model.ctfj')


def predict_finding(net, finding, finder, file_type):
    """finding 为扫描器输出元组 (score, kind, tok, val, loc)。"""
    score, kind, tok, val, _loc = finding
    sample = {'score': score, 'kind': kind, 'tok': tok, 'val': val,
              'finder': finder, 'file_type': file_type}
    return net.predict(extract_features(sample))


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
