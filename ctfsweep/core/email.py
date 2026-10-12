"""邮件取证模块（.eml / .mbox / .msg / .pst）。

分析链路：
1. 类型匹配 → 检测邮件格式（.eml / .mbox / .msg）
2. 解析邮件头 → 提取 Received 链 / SPF/DKIM/DMARC / 原始 IP
3. 解析邮件体 → 提取链接 / Base64 附件 / HTML 恶意代码
4. 置信度评估 → 高(SPF/DKIM 失败/钓鱼链接) / 中(可疑域名/编码附件) / 低(普通邮件)
"""

import base64
import re
import json
from .router import Finding, AnalysisResult

# ---------------------------------------------------------------------------
# 可疑域名/链接模式
# ---------------------------------------------------------------------------

SUSPICIOUS_DOMAIN_PATTERNS = [
    (r"192\.168\.\d+\.\d+", "内网 IP（可能为钓鱼内网地址）"),
    (r"10\.\d+\.\d+\.\d+", "内网 IP（可能为钓鱼内网地址）"),
    (r"0\.0\.0\.0", "无效 IP（可能为 DNS 重定向）"),
    (r"evil\.com", "可疑域名"),
    (r"malware\.com", "可疑域名"),
    (r"phish(?:ing)?\.(?:com|net|org)", "可疑域名"),
    (r"login-?\w+\.com", "疑似钓鱼域名（login 伪装）"),
    (r"secure-?\w+\.com", "疑似钓鱼域名（secure 伪装）"),
    (r"account-?\w+\.com", "疑似钓鱼域名（account 伪装）"),
    (r"bank-?\w+\.com", "疑似钓鱼域名（bank 伪装）"),
    (r"pay-?\w+\.com", "疑似钓鱼域名（pay 伪装）"),
    (r"t\.cn/|bit\.ly/|tinyurl\.cn/", "短链接（可能为钓鱼）"),
    (r"http://", "非 HTTPS 链接（可能为钓鱼）"),
]

# ---------------------------------------------------------------------------
# 分析函数
# ---------------------------------------------------------------------------

def analyze(filepath: str) -> AnalysisResult:
    """分析邮件文件。

    支持：
    - .eml 格式
    - .mbox 格式
    - .msg 格式（Outlook）
    """
    result = AnalysisResult("email")

    with open(filepath, "rb") as f:
        header = f.read(1024)

    text = header.decode("utf-8", errors="replace")

    if ".eml" in filepath.lower() or "from " in text[:100].lower():
        _analyze_eml(filepath, result)
    elif ".mbox" in filepath.lower():
        _analyze_mbox(filepath, result)
    elif ".msg" in filepath.lower():
        _analyze_msg(filepath, result)
    else:
        # 尝试检测 eml 格式
        if "Subject:" in text or "From:" in text or "To:" in text:
            _analyze_eml(filepath, result)

    return result


def _analyze_eml(filepath: str, result: AnalysisResult):
    """解析 .eml 邮件。"""
    with open(filepath, "r", errors="replace") as f:
        content = f.read()

    # 1. 解析邮件头
    _parse_email_headers(content, result)

    # 2. 解析邮件体
    _parse_email_body(content, result)

    # 3. 解析 Base64 附件
    _parse_base64_attachments(content, result)


def _parse_email_headers(content: str, result: AnalysisResult):
    """解析邮件头。"""
    lines = content.split("\n")
    headers = {}

    # 提取所有 Received 链
    received_chain = []
    current_header = None
    current_value = ""

    for line in lines:
        if line.startswith(" ") or line.startswith("\t"):
            #  continuation line
            if current_header:
                current_value += " " + line.strip()
        elif ":" in line:
            # 保存前一个 header
            if current_header:
                headers[current_header.lower()] = current_value

            # 解析新 header
            header_name, _, header_value = line.partition(":")
            current_header = header_name.strip()
            current_value = header_value.strip()

            # 提取 Received 链
            if current_header.lower() == "received":
                received_chain.append(current_value)
        else:
            # 空行，表示邮件头结束
            if current_header:
                headers[current_header.lower()] = current_value
                current_header = None
                current_value = ""
            break

    # 保存最后一个 header
    if current_header:
        headers[current_header.lower()] = current_value

    # 分析 Received 链
    _analyze_received_chain(received_chain, result)

    # 分析 SPF/DKIM/DMARC
    _analyze_spf_dkim_dmarc(headers, result)

    # 分析发件人
    _analyze_sender(headers, result)


def _analyze_received_chain(received_chain: list, result: AnalysisResult):
    """分析 Received 链。"""
    if not received_chain:
        return

    # 检查是否为反向链（最后一封是原始发件人）
    if received_chain:
        last_received = received_chain[-1]
        # 提取 IP
        ip_match = re.search(r'\b(\d+\.\d+\.\d+\.\d+)\b', last_received)
        if ip_match:
            ip = ip_match.group(1)
            if ip.startswith("192.168.") or ip.startswith("10."):
                result.findings.append(
                    Finding(
                        kind="内网 IP 邮件",
                        confidence=0.70,
                        evidence=f"原始发件人 IP: {ip}, Received: {last_received[:200]}",
                        suggestion="检查该内网 IP 是否为合法发件人",
                        module="email",
                    )
                )


def _analyze_spf_dkim_dmarc(headers: dict, result: AnalysisResult):
    """分析 SPF/DKIM/DMARC。"""
    # 检查 SPF
    if "received-spf" in headers:
        spf_result = headers["received-spf"].lower()
        if "fail" in spf_result:
            result.findings.append(
                Finding(
                    kind="SPF 验证失败",
                    confidence=0.95,
                    evidence=f"SPF: {headers['received-spf']}",
                    suggestion="SPF 验证失败，邮件可能为钓鱼邮件",
                    module="email",
                )
            )
        elif "pass" in spf_result:
            result.findings.append(
                Finding(
                    kind="SPF 验证通过",
                    confidence=0.80,
                    evidence=f"SPF: {headers['received-spf']}",
                    module="email",
                )
            )

    # 检查 DKIM
    if "dkim-signature" in headers or "authentication-results" in headers:
        auth_results = headers.get("authentication-results", "")
        if "dkim=fail" in auth_results.lower():
            result.findings.append(
                Finding(
                    kind="DKIM 验证失败",
                    confidence=0.95,
                    evidence=f"DKIM: {auth_results}",
                    suggestion="DKIM 验证失败，邮件可能为钓鱼邮件",
                    module="email",
                )
            )

    # 检查 DMARC
    if "dmarc" in headers.get("authentication-results", "").lower():
        dmarc_result = headers.get("authentication-results", "").lower()
        if "dmarc=fail" in dmarc_result:
            result.findings.append(
                Finding(
                    kind="DMARC 验证失败",
                    confidence=0.95,
                    evidence=f"DMARC: {headers['authentication-results']}",
                    suggestion="DMARC 验证失败，邮件可能为钓鱼邮件",
                    module="email",
                )
            )


def _analyze_sender(headers: dict, result: AnalysisResult):
    """分析发件人。"""
    sender = headers.get("from", "")
    if not sender:
        return

    # 检查发件人域名是否与接收域名不一致
    if "@" in sender:
        sender_domain = sender.split("@")[-1].lower()
        # 简单检查（实际应该与邮件接收域名比较）
        for pattern, desc in SUSPICIOUS_DOMAIN_PATTERNS:
            if re.search(pattern, sender_domain):
                result.findings.append(
                    Finding(
                        kind=f"可疑发件人: {desc}",
                        confidence=0.80,
                        evidence=f"发件人: {sender}",
                        suggestion=f"检查该发件人域名是否可疑",
                        module="email",
                    )
                )
                break


def _parse_email_body(content: str, result: AnalysisResult):
    """解析邮件体。"""
    # 提取邮件体（假设邮件头以空行结束）
    parts = content.split("\n\n", 1)
    if len(parts) < 2:
        return

    body = parts[1]

    # 提取链接
    urls = re.findall(r'https?://[^\s"<>\)\]]+', body)
    for url in urls:
        for pattern, desc in SUSPICIOUS_DOMAIN_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                result.findings.append(
                    Finding(
                        kind=f"可疑链接: {desc}",
                        confidence=0.85 if "http://" in url else 0.70,
                        evidence=f"链接: {url[:200]}",
                        suggestion="检查该链接是否指向钓鱼站点",
                        module="email",
                    )
                )
                break

    # 检查 HTML 恶意代码
    if "<iframe" in body.lower() or "<script" in body.lower() or "javascript:" in body.lower():
        result.findings.append(
            Finding(
                kind="HTML 恶意代码",
                confidence=0.90,
                evidence=f"邮件体包含: {'<iframe>' if '<iframe' in body.lower() else '<script>' if '<script' in body.lower() else 'javascript:'}",
                suggestion="检查该 HTML 代码是否包含恶意内容",
                module="email",
            )
        )

    # 检查 flag
    if "flag{" in body.lower():
        result.findings.append(
            Finding(
                kind="邮件中的 flag",
                confidence=0.97,
                evidence=f"邮件体: {body[:300]}",
                suggestion="提取 flag",
                module="email",
            )
        )


def _parse_base64_attachments(content: str, result: AnalysisResult):
    """解析 Base64 附件。"""
    # 查找 Base64 编码的数据
    base64_pattern = r"base64,\s*([A-Za-z0-9+/=\n\r]+)"
    matches = re.findall(base64_pattern, content, re.IGNORECASE)

    for match in matches:
        try:
            decoded = base64.b64decode(match.strip())
            # 检查解码后的内容
            if b"flag{" in decoded:
                result.findings.append(
                    Finding(
                        kind="Base64 附件中的 flag",
                        confidence=0.97,
                        evidence=f"Base64 附件解码后包含: flag{{...}}",
                        suggestion="提取 flag",
                        module="email",
                    )
                )
            elif b"password" in decoded or b"secret" in decoded:
                result.findings.append(
                    Finding(
                        kind="Base64 附件中的敏感信息",
                        confidence=0.85,
                        evidence=f"Base64 附件解码后包含敏感信息",
                        suggestion="检查该附件是否包含敏感信息",
                        module="email",
                    )
                )
        except Exception:
            pass


def _analyze_mbox(filepath: str, result: AnalysisResult):
    """解析 .mbox 邮件。"""
    with open(filepath, "r", errors="replace") as f:
        content = f.read()

    # 分割邮件
    emails = re.split(r"^From \s", content, flags=re.MULTILINE)

    for email in emails:
        if not email.strip():
            continue

        # 解析每封邮件
        _parse_email_headers(email, result)
        _parse_email_body(email, result)


def _analyze_msg(filepath: str, result: AnalysisResult):
    """解析 .msg 邮件（Outlook）。"""
    with open(filepath, "rb") as f:
        content = f.read()

    # 简单文本提取
    text = content.decode("utf-8", errors="replace")

    # 检查 flag
    if "flag{" in text.lower():
        result.findings.append(
            Finding(
                kind="邮件中的 flag",
                confidence=0.97,
                evidence=f"邮件: {text[:300]}",
                suggestion="提取 flag",
                module="email",
            )
        )

    # 检查链接
    urls = re.findall(r'https?://[^\s"<>\)\]]+', text)
    for url in urls:
        for pattern, desc in SUSPICIOUS_DOMAIN_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                result.findings.append(
                    Finding(
                        kind=f"可疑链接: {desc}",
                        confidence=0.85,
                        evidence=f"链接: {url[:200]}",
                        suggestion="检查该链接是否指向钓鱼站点",
                        module="email",
                    )
                )
                break
