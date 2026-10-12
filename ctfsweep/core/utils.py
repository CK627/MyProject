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


# ---------------------------------------------------------------------------
# DNS 查询线索判定
# ---------------------------------------------------------------------------
#
# 判定"这个域名值不值得逐条列出"。正常上网与系统遥测（含中文互联网的 CDN、门户）
# 一条都不匹配 → 折叠；外带 / DGA / 动态 DNS / AD 服务发现 / WPAD 投毒逐条保留。
#
# 为什么按"结构异常"而不是"白名单厂商域名"：白名单是针对英文互联网的，中文流量
# （qq.com、g-fox.cn、wp.com）一条都盖不住，而逐条列举这类常规域名会把真正的线索
# 挤出屏幕——正是"与答案无关的噪音"。结构异常则与语言、地区无关。

# 知名基础设施后缀：系统遥测/更新/CDN 域名的随机标签是正常现象
# （`d15krst4gi8g86.cloudfront.net`、`cp601-prod.do.dsp.mp.microsoft.com`、
# `adsh.wagbridge.taobao.alimama.com.gds.alibabadns.com`），不算"结构异常"。
# 供 dns.py 的长域名判定与 dns_lead_reason 的随机主机名判定共用。
KNOWN_INFRA_SUFFIXES = (
    ".microsoft.com", ".microsoftaik.azure.net", ".azure.net", ".azure.com",
    ".windowsupdate.com", ".windows.com", ".msftncsi.com", ".msftconnecttest.com",
    ".office.net", ".office.com", ".live.com", ".msn.com", ".bing.com",
    # Edge/Teams/Xbox/更新链路的 HTTPS 服务名（实测一台普通 Windows 主机的
    # SNI 列表里这些占 90%，不豁免就会把真正的 C2 域名挤到列表末尾）
    ".msedge.net", ".skype.com", ".xboxlive.com", ".azureedge.net",
    ".trafficmanager.net", ".akamaiedge.net", ".edgesuite.net", ".msecnd.net",
    ".google.com", ".googlevideo.com", ".gstatic.com", ".googleapis.com",
    ".youtube.com", ".apple.com", ".icloud.com", ".mzstatic.com",
    ".adobe.com", ".akamai.net", ".akamaized.net", ".akamaihd.net", ".edgekey.net",
    ".cloudfront.net", ".cloudflare.com", ".cloudflare.net", ".fastly.net",
    ".amazonaws.com", ".digicert.com", ".sectigo.com", ".verisign.com",
    ".mozilla.org", ".mozilla.net", ".firefox.com", ".yahoo.com",
    ".footprintdns.com", ".opendns.com", ".umbrella.com",
    # 国内 CDN / 云（中文流量抓包里这些随机名同样是正常现象）
    ".alicdn.com", ".aliyun.com", ".aliyuncs.com", ".myqcloud.com", ".qcloud.com",
    ".bdydns.com", ".baidubce.com", ".jomodns.com", ".ourdvsss.com",
    ".kunlunca.com", ".wswebpic.com", ".jiashule.com", ".qiyipic.com",
    ".hdslb.com", ".biliapi.net", ".douyucdn.cn", ".pstatp.com", ".bytedns.net",
    ".ourdvsss.cn", ".lxdns.com", ".gslb.com", ".mmtrix.com",
    # 虚拟主机运营商的机器名（p3plcpnl001.prod.phx3.secureserver.net
    # 会被"主机名尾部数字串"误判成 DGA）
    ".secureserver.net",
)


def under_known_infra(name):
    """域名是否落在已知基础设施（厂商遥测/CDN/云）之下。"""
    s = name.decode('latin-1') if isinstance(name, bytes) else str(name)
    s = s.lower().rstrip('.')
    return any(s == suf[1:] or s.endswith(suf) for suf in KNOWN_INFRA_SUFFIXES)


_ABUSED_TLDS = frozenset("""
    cyou casa club top pw xyz icu tk gq ml cf ga ws buzz click link online site
    live store fun space website monster quest rest bar bond cfd sbs cyber mom
    lol best shop work men loan download stream gdn bid win review country kim
    party science racing date faith trade webcam accountant cricket
""".split())

# 动态 DNS / 内网穿透服务：C2 回连的常见落脚点，域名本身就是线索
_DYNDNS_SUFFIXES = (
    '.ddns.net', '.no-ip.org', '.no-ip.com', '.noip.com', '.dyndns.org',
    '.dynu.com', '.dynu.net', '.hopto.org', '.zapto.org', '.sytes.net',
    '.duckdns.org', '.3utilities.com', '.myftp.org', '.myvnc.com',
    '.serveftp.com', '.redirectme.net', '.dnsalias.com', '.dnsalias.net',
    '.chickenkiller.com', '.mooo.com', '.strangled.net', '.ignorelist.com',
    '.jumpingcrab.com', '.linkpc.net', '.dynalias.com',
    '.ngrok.io', '.ngrok-free.app', '.trycloudflare.com', '.serveo.net',
)

# 名字里直接带服务发现/投毒语义
_DISCOVERY_PREFIXES = ('wpad.', 'isatap.', '_ldap._tcp', '_kerberos._tcp',
                       '_gc._tcp', '_vlmcs._tcp', '_kpasswd._tcp')
_DISCOVERY_MARKS = ('_msdcs', '_sites')

def is_service_discovery(name):
    """域名是否为**服务发现类**查询（SRV `_ldap._tcp` / `_msdcs` / `_sites` / `wpad.`）。

    这类名字在每个 Windows 域环境里都是查询量最大的，却和题目答案毫无关系。
    `【dns】` 块的"高频查询域名"排名必须跳过它们——实测 mta 那道题，
    `wpad.bepositive.com`（20 次）靠"查询最多"坐上【dns】块与【前 10 项发现】第一名，
    把真正要看的受害主机信息挤到后面。判定口径与 `dns_lead_reason` 的
    「服务发现/投毒相关查询」共用同一份常量，避免两处漂移。
    """
    s = name.decode('latin-1') if isinstance(name, bytes) else str(name)
    s = s.lower().rstrip('.')
    if any(x.startswith('_') for x in s.split('.')):
        return True
    return any(s == p.rstrip('.') or s.startswith(p) for p in _DISCOVERY_PREFIXES) \
        or any(m in s for m in _DISCOVERY_MARKS)


_VOWELS = frozenset('aeiou')

# Windows 自动生成的计算机名：`DESKTOP-RNVO9AT` / `WIN-CTL9XBQ9Y19` / `LAPTOP-XXXX`.
# 前缀是固定词，后缀那串随机字符由系统分配——统计特征与 DGA 无异，但它是域内正常主机。
_WIN_MACHINE_RE = re.compile(r'^(?:desktop|win|laptop|srv|pc|server)-[a-z0-9]{5,15}$')


def _encoded_label(lb):
    """标签是否像**编码数据**（base64/hex 外带）而非自然语言词。

    只按长度判会误报：`mail.pisosyrecubrimientos.com` 的 20 字符标签是西语单词
    （pisos y recubrimientos），而 base64/hex 外带的标签要么带数字、要么大小写
    混排、要么几乎没有元音。三者都不占的长标签就是词，不是线索。
    """
    if len(lb) < 20:
        return False
    # 连字符分词的短语（`Default-First-Site-Name`）是自然语言，不是 base64：
    # 每一段都是正常单词长度且含元音。base64url 里的 `-` 只会零星出现，
    # 不会把整串切成 ≥3 个词。AD 的 SRV 查询名里这个标签必然出现，
    # 不豁免的话每条域加入流量都会报一次"编码外带"。
    parts = lb.split('-')
    if (len(parts) >= 2 and all(len(p) >= 3 for p in parts)
            and all(any(c in _VOWELS for c in p.lower()) for p in parts)):
        return False
    if any(c.isdigit() for c in lb):
        return True
    if lb != lb.lower() and lb != lb.upper():        # 大小写混排 = base64
        return True
    alpha = [c for c in lb if c.isalpha()]
    return bool(alpha) and sum(1 for c in alpha if c.lower() in _VOWELS) / float(len(alpha)) < 0.25


def dns_lead_reason(name):
    """域名是否值得逐条列出；返回原因字符串（None = 常规域名，交由调用方折叠）。"""
    s = name.decode('latin-1') if isinstance(name, bytes) else str(name)
    s = s.rstrip('.')
    if not s or ' ' in s:
        return None

    # SRV 定位记录（RFC 2782 的 `_ldap._tcp...` / `_msdcs` / `_sites`）**必须先于长度判定**：
    # 这类名字普遍 70+ 字符，会先撞上下面的"域名超长（多段拼接外带特征）"。
    # 它们不折叠（查 `_ldap._tcp.pdc._msdcs.enemywatch.net` 这类陌生域仍是线索，
    # 见 test_smoke 的断言），但原因要如实标成"服务发现"，不能报成外带隧道。
    # 实测 bepositive.com 那道题，DNS 段 7 条线索里 4 条是这种错标。
    if any(x.startswith('_') for x in s.split('.')):
        return '服务发现/投毒相关查询'

    labels = s.lower().split('.')
    # 编码外带看原串（大小写混排是 base64 的特征，lower() 之后就看不出来了）
    if any(_encoded_label(x) for x in s.split('.')):
        return '超长标签（编码外带/隧道特征）'
    s = s.lower()
    if len(s) > 60:
        return '域名超长（多段拼接外带特征）'

    for suf in _DYNDNS_SUFFIXES:
        if s == suf[1:] or s.endswith(suf):
            return '动态 DNS / 内网穿透域名'
    for pre in _DISCOVERY_PREFIXES:
        if s.startswith(pre):
            return '服务发现/投毒相关查询'
    if any(m in s for m in _DISCOVERY_MARKS):
        return '服务发现/投毒相关查询'

    tld = labels[-1]
    if tld in _ABUSED_TLDS:
        return '滥用高发顶级域 .%s' % tld

    # 随机二级/主机名：逐个标签看，任一像 DGA 就算（kamuchehddhgfgf.ddns.net
    # 这类左侧随机名的落脚点）。落在已知 CDN/遥测之下的随机名是正常现象，跳过。
    if under_known_infra(s):
        return None
    for lb in labels[:-1]:
        if len(lb) < 10:
            continue
        # Windows 自动生成的机器名（DESKTOP-RNVO9AT / WIN-CTL9XBQ9Y19 / LAPTOP-XXXX）：
        # 尾部那串随机字符本就是系统随机分配的，和 DGA 长得一样但是域内正常主机。
        # 实测 bepositive.com 那道题的域控 `win-ctl9xbq9y19` 被判成 DGA，排进前 10。
        if _WIN_MACHINE_RE.match(lb):
            continue
        digits = sum(1 for c in lb if c.isdigit()) / float(len(lb))
        alpha = [c for c in lb if c.isalpha()]
        vowel = (sum(1 for c in alpha if c in _VOWELS) / float(len(alpha))
                 if alpha else 1.0)
        if len(lb) >= 12 and (digits >= 0.15 or vowel < 0.25):
            return '主机名随机（疑似 DGA）'
        # 纯字母 + 结尾一长串数字（opsbox8097 / hostjob3862 / globalcert8618）——
        # 要求数字**连成尾串**且 >=3 位，避开 cp601-prod、b28-yk-w2 这类正常编号
        tail = len(lb) - len(lb.rstrip('0123456789'))
        if tail >= 3 and alpha and digits >= 0.25:
            return '主机名尾部数字串（疑似 DGA）'
    return None


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


def _text_ok(ch):
    """单字符是否像"人写的文本"。

    白名单刻意收窄：ASCII 可打印 + Latin-1 补充（×）+ 通用标点（… —）+ 箭头（→）
    + CJK 标点/扩展A/基本区 + 谚文 + 全角。其余码位一律算二进制——
    它们在真实文本里几乎不出现，却是"二进制按 UTF-16 解码"的必经之地。
    """
    o = ord(ch)
    return (32 <= o < 127 or 0xa0 <= o < 0x100 or 0x2000 <= o < 0x2070
            or 0x2190 <= o < 0x2200 or 0x3000 <= o < 0x3040
            or 0x3400 <= o < 0x4dc0 or 0x4e00 <= o < 0xa000
            or 0xac00 <= o < 0xd7a4 or 0xff00 <= o < 0xfff0)


def readable_window(s, min_len=16):
    """从混进二进制字节的上下文里取出**最长的连续可读文本**（取不到则返回 ''）。

    为什么 `isprintable()` 不够：evtx / .reg 这类二进制里嵌的 UTF-16LE 字符串，
    按对解码后会大量落在 U+0100–U+2FFF（Ā Ѐ ఀ ᄀ ⨀ ⎬ ☿）——**它们全是 printable**，
    现有的"非可打印换点号"处理一律放行。实测 Security.evtx 的 9 条 `关键词[flag]`
    命中里，有效线索只有开头那 30 来个字节
    （`.../c echo flag{sol > C:\\Windows\\Temp\\test.txt`），尾巴几十字符全是乱码：
    零信息量，还把 4 个 flag 片段挤出了可视范围。

    规则：**整串都像文本就原样返回**（不做长度门槛，短凭据 `PWD=/AstrBot` 也得留）；
    混了二进制才按码位切段取最长一段，且要求 >= `min_len`，否则视为无可用文本。
    切段时不做首尾裁剪——填充点号是既有约定，golden 基线逐字断言着它。
    """
    if not s:
        return ''
    if all(_text_ok(ch) for ch in s):
        return s
    best, cur = [], []
    for ch in s:
        if _text_ok(ch):
            cur.append(ch)
        else:
            if len(cur) > len(best):
                best = cur
            cur = []
    if len(cur) > len(best):
        best = cur
    out = ''.join(best)
    return out if len(out) >= min_len else ''


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
