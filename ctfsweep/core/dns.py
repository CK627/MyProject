"""DNS 分析增强模块。

分析链路：
1. 类型匹配 → 检测 DNS 流量/日志
2. 解析 DNS 查询/响应 → 提取域名/记录类型/TTL/IP
3. 异常检测 → 长域名/高频查询/TXT 记录/DGA 域名
4. 置信度评估 → 高(明显外带通道) / 中(可疑域名) / 低(噪音)
"""

import re
import collections
from .router import Finding, AnalysisResult
from .utils import KNOWN_INFRA_SUFFIXES, is_service_discovery

# GUID 标签（AD 的 _ldap._tcp.<GUID>.domains._msdcs 等查询）→ 长域名判定豁免
_GUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

# ---------------------------------------------------------------------------
# DGA 域名检测启发式
# ---------------------------------------------------------------------------

def _dga_score(domain: str) -> float:
    """计算 DGA 域名分数（0-1，越高越可疑）。"""
    score = 0.0
    parts = domain.split(".")
    if not parts:
        return 0.0

    sld = parts[0]  # 二级域名

    # 长度特征
    if len(sld) > 15:
        score += 0.3
    elif len(sld) > 10:
        score += 0.15

    #  consonant ratio（辅音比例高 → 可疑）
    vowels = set("aeiou")
    alpha_chars = [c for c in sld.lower() if c.isalpha()]
    if alpha_chars:
        vowel_ratio = sum(1 for c in alpha_chars if c in vowels) / len(alpha_chars)
        if vowel_ratio < 0.2:
            score += 0.3
        elif vowel_ratio < 0.3:
            score += 0.15

    # digit ratio
    digits = sum(1 for c in sld if c.isdigit())
    if len(sld) > 0:
        digit_ratio = digits / len(sld)
        if digit_ratio > 0.4:
            score += 0.2
        elif digit_ratio > 0.2:
            score += 0.1

    # entropy
    if len(sld) > 5:
        char_counts = collections.Counter(sld.lower())
        entropy = -sum((c / len(sld)) * (2 ** c / len(sld)) for c in char_counts.values())
        if entropy > 3.5:
            score += 0.2
        elif entropy > 3.0:
            score += 0.1

    return min(score, 1.0)


# 知名基础设施后缀见 utils.KNOWN_INFRA_SUFFIXES（与 dns_lead_reason 的随机主机名
# 判定共用同一份名单，避免两处白名单漂移）。


# ---------------------------------------------------------------------------
# 分析函数
# ---------------------------------------------------------------------------

def analyze(filepath: str, ctx=None) -> AnalysisResult:
    """分析 DNS 流量/日志。

    支持：
    - PCAP/PCAPNG 中的 DNS 查询/响应（真实解析 DNS 报文）
    - DNS 日志文件

    `ctx` 为可选的 `capture.CaptureContext`：给了就直接复用它的解析结果
    （同一个抓包文件不再被解析第二遍）。
    """
    result = AnalysisResult("dns")

    if ctx is not None and ctx.is_capture:
        _analyze_dns_pcap(None, result, ctx)
        return result

    with open(filepath, "rb") as f:
        data = f.read()

    from .capture import PCAP_MAGICS, PCAPNG_MAGIC

    if data[:4] in PCAP_MAGICS or data[:4] == PCAPNG_MAGIC:
        # 抓包文件：必须真实解析 DNS 报文。
        # （历史教训：曾用文本正则在全球找 "….com/.cn" 字符串，
        #   把 HTML/CSS/文件名等全部误报为"长域名 DNS 外带"，噪音巨大）
        _analyze_dns_pcap(data, result)
        return result

    text = data.decode("utf-8", errors="replace")
    if "QUERY" in text or "RESPONSE" in text or "DNS" in text:
        _analyze_dns_log(text, result)

    return result


def _analyze_dns_log(text: str, result: AnalysisResult):
    """分析 DNS 日志。"""
    lines = text.split("\n")

    # 收集域名统计
    domain_counts = collections.Counter()
    txt_records = []

    for line in lines:
        if not line.strip():
            continue

        # 提取域名
        domain_match = re.search(r'(?:domain|name|qname)[=:]\s*(\S+)', line, re.IGNORECASE)
        if domain_match:
            domain = domain_match.group(1).rstrip(".")
            domain_counts[domain] += 1

        # 提取 TXT 记录
        txt_match = re.search(r'(?:TXT|txt)[=:]\s*(\S+)', line, re.IGNORECASE)
        if txt_match:
            txt_records.append(txt_match.group(1))

        # 检查 flag
        if "flag{" in line.lower():
            result.findings.append(
                Finding(
                    kind="DNS 日志中的 flag",
                    confidence=0.97,
                    evidence=f"日志: {line[:300]}",
                    suggestion="提取 flag",
                    module="dns",
                )
            )

    # 分析域名统计
    _analyze_domain_stats(domain_counts, result)

    # 分析 TXT 记录（常见于 DNS 外带通道）
    if txt_records:
        for record in txt_records[:10]:
            result.findings.append(
                Finding(
                    kind="DNS TXT 记录",
                    confidence=0.80,
                    evidence=f"TXT 记录: {record[:200]}",
                    suggestion="检查该 TXT 记录是否用于数据外带",
                    module="dns",
                )
            )


def _analyze_domain_stats(domain_counts: collections.Counter, result: AnalysisResult):
    """分析域名统计（仅接受真实 DNS 查询名；各分类有输出上限，防刷屏）。"""
    # 高频查询域名。跳过服务发现类（`wpad.` / `_ldap._tcp` / `_msdcs`）：
    # 它们在每个 Windows 域环境里都是查询量最大的名字，却和题目答案毫无关系。
    # 实测 bepositive.com 那道题，`wpad.bepositive.com`（20 次）靠"查询最多"坐上
    # 【dns】块和第 1 项发现，把真正要看的受害主机信息挤在后面。
    for domain, count in domain_counts.most_common(15):
        if count > 10 and not is_service_discovery(domain):
            result.findings.append(
                Finding(
                    kind=f"高频查询域名: {domain}",
                    confidence=0.65,
                    evidence=f"查询次数: {count}",
                    suggestion="检查该域名是否可疑（可能是 C2 或 DGA）",
                    module="dns",
                )
            )

    # DGA 域名检测（封顶 10 条）
    dga_hits = 0
    for domain, count in domain_counts.items():
        if dga_hits >= 10:
            break
        # 服务发现类（`_ldap._tcp.WIN-CTL9XBQ9Y19._sites...`）里的机器名标签
        # 是系统随机分配的，`_dga_score` 必然给高分，但它是域控不是 C2。
        if is_service_discovery(domain):
            continue
        score = _dga_score(domain)
        if score > 0.6:
            dga_hits += 1
            result.findings.append(
                Finding(
                    kind=f"DGA 域名: {domain}",
                    confidence=0.75,
                    evidence=f"DGA 分数: {score:.2f}, 查询次数: {count}",
                    suggestion="该域名可能是 DGA（域名生成算法）生成的，检查是否为恶意域名",
                    module="dns",
                )
            )

    # 长域名检测：真实 DNS 外带的特征 = 超长"单个标签"（一次性编码外带数据）。
    # 只有整体长度 > 50 且最长标签 ≥ 25 字符才报（排除 CDN/广告类"多短标签拼接"长域名，如
    # adsh.wagbridge.taobao.alimama.com.gds.alibabadns.com）。封顶 15 条。
    long_hits = 0
    for domain, count in sorted(domain_counts.items(), key=lambda kv: -kv[1]):
        if long_hits >= 15:
            break
        if len(domain) <= 50 or " " in domain:
            continue
        max_label = max((len(x) for x in domain.split(".")), default=0)
        if max_label < 25:
            continue
        if any(domain.endswith(s) for s in KNOWN_INFRA_SUFFIXES):
            continue
        if _GUID_RE.match(max(domain.split("."), key=len)):
            continue  # AD SRV 查询（GUID 标签），非外带
        long_hits += 1
        result.findings.append(
            Finding(
                kind=f"长域名（可能为 DNS 外带）: {domain[:80]}...",
                confidence=0.90,
                evidence=f"域名长度: {len(domain)}, 最长标签: {max_label}, 查询次数: {count}",
                suggestion="该域名可能为 DNS 外带通道，检查是否泄露数据",
                module="dns",
            )
        )


def _analyze_dns_pcap(data: bytes, result: AnalysisResult, ctx=None):
    """分析 PCAP/PCAPNG 中的 DNS 流量（真实解析 UDP:53 的查询报文）。

    `ctx` 与 `data` 二选一：给了 ctx 就不再解析一遍。
    """
    from .capture import CaptureContext, dns_qname

    if ctx is None:
        ctx = CaptureContext(data)
    if not ctx.is_capture:
        return

    domains = collections.Counter()
    for _num, _lt, _pkt, _ts, r in ctx.l4:
        if not r:
            continue
        proto, _src, _dst, sport, dport, payload = r
        if proto != "udp" or 53 not in (sport, dport):
            continue
        # 仅统计"查询"（QR=0）；响应报文不计入查询次数
        if len(payload) < 13 or (payload[2] & 0x80):
            continue
        q = dns_qname(payload)
        if not q:
            continue
        try:
            domain = q.decode("ascii").rstrip(".").lower()
        except Exception:
            continue
        if domain and " " not in domain:
            domains[domain] += 1

    _analyze_domain_stats(domains, result)
