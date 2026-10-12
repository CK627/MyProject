"""日志分析模块（Nginx/Apache/syslog/auth.log）。

分析链路：
1. 类型匹配 → 检测日志格式（Access Log / syslog / auth.log）
2. 解析对应格式 → 提取状态码/请求/认证事件
3. 攻击模式匹配 → SQLi/XSS/RCE/目录遍历/WebShell
4. 置信度评估 → 高(完整攻击载荷) / 中(可疑请求/异常状态) / 低(注释/噪音)
"""

import re
from .router import Finding, AnalysisResult


# ---------------------------------------------------------------------------
# 二进制日志容器（.evtx 等）的字符串抽取
# ---------------------------------------------------------------------------

# 可读片段的判定：ASCII 可见字符 + CJK
_STR_WIDE_RE = re.compile(r"[\x20-\x7e　-〿一-鿿＀-￯]{4,}")
_STR_NARROW_RE = re.compile(rb"[\x20-\x7e]{4,}")


def _looks_binary(raw: bytes) -> bool:
    """靠 NUL 字节判断是不是二进制容器（文本日志不会有 NUL）。"""
    return b"\x00" in raw


def _extract_strings(raw: bytes) -> str:
    """从二进制容器里抽可读字符串。

    Windows 事件日志是 UTF-16LE：直接按字节当文本读，会把 0x60 这类字节的巧合
    喂给攻击正则，产出「RCE（命令替换）」这种高置信乱码误报——证据行本身是乱码，
    对解题毫无引导价值，还会把真正的 flag 片段挤下去。所以先把可读部分捞出来，
    后续分析只在真实文本上做。

    两种对齐都要试：EVTX 里的字符串常常相对文件头**错位 1 字节**
    （`\\x00f\\x00l\\x00a\\x00g`），只按偏移 0 解会把整段文本解成 CJK 乱码。
    scanner 的 UTF-16LE 关键字扫描同样是从字符本身起匹配，这里与之对齐。
    """
    out, seen = [], set()

    def take(s):
        if s not in seen:
            seen.add(s)
            out.append(s)

    for off in (0, 1):
        for m in _STR_WIDE_RE.finditer(raw[off:].decode("utf-16-le", "replace")):
            take(m.group(0))
    for m in _STR_NARROW_RE.finditer(raw):
        take(m.group(0).decode("ascii"))
    return "\n".join(out)

# ---------------------------------------------------------------------------
# 攻击模式匹配（正则 → 描述 → 置信度）
# ---------------------------------------------------------------------------

ATTACK_PATTERNS = [
    # SQL 注入
    (r"(?:union\s+(?:all\s+)?select|select\s+.+\s+from|insert\s+into|delete\s+from|update\s+.+\s+set|drop\s+table|drop\s+database|alter\s+table|exec\s*\(|execute\s*\()",
     "SQL 注入", 0.95, "sql_injection"),
    (r"(?:'\s*(?:or|and)\s+'?\d+'?\s*=\s*'?\d+'?|'\s*(?:or|and)\s+'[^']*'\s*=\s*'[^']*'|1\s*=\s*1|'\s*;\s*--)",
     "SQL 注入（布尔盲注）", 0.90, "sql_injection"),
    (r"(?:sleep\s*\(\s*\d+\s*\)|benchmark\s*\(|waitfor\s+delay|pg_sleep)",
     "SQL 注入（时间盲注）", 0.90, "sql_injection"),
    (r"(?:load_file|into\s+(?:out|dump)file|information_schema|sys\.)",
     "SQL 注入（信息提取）", 0.90, "sql_injection"),

    # XSS
    (r"<script[^>]*>.*?</script>", "XSS（脚本注入）", 0.95, "xss"),
    (r"javascript\s*:", "XSS（JavaScript 协议）", 0.90, "xss"),
    (r"on(?:load|error|click|mouseover)\s*=", "XSS（事件处理器）", 0.90, "xss"),
    (r"<(?:iframe|img|svg|embed|object)[^>]*>", "XSS（标签注入）", 0.85, "xss"),

    # RCE
    (r"(?:;\s*|\|\|\s*&&\s*)\s*(?:cat|ls|dir|whoami|id|uname|pwd|wget|curl|nc|netcat|bash|sh|cmd|powershell)\b",
     "RCE（命令注入）", 0.95, "rce"),
    (r"(?:`[^`]*`|\$\([^)]*\))", "RCE（命令替换）", 0.90, "rce"),
    (r"(?:/etc/(?:passwd|shadow|hosts)|(?:c|w|n)proc/self)",
     "RCE（文件读取）", 0.90, "rce"),

    # 目录遍历
    (r"(?:\.\./){3,}", "目录遍历（深层）", 0.90, "dir_traversal"),
    (r"(?:%2e%2e[%/%00]|%252e%252e|%252e%252e%252f)",
     "目录遍历（编码绕过）", 0.90, "dir_traversal"),
    (r"(?:/etc/(?:passwd|shadow|hosts)|/windows/(?:system32|win\.ini))",
     "目录遍历（系统文件）", 0.95, "dir_traversal"),

    # WebShell
    (r"(?:eval|assert|exec|system|passthru|popen|proc_open)\s*\(\s*(?:\$\w+|base64_decode|gzinflate|str_rot13)",
     "WebShell（代码执行）", 0.95, "webshell"),
    (r"(?:cmd|command|exec|run|shell|backdoor|webshell)\s*[=:]\s*['\"]",
     "WebShell（参数注入）", 0.90, "webshell"),
    (r"(?:<?php|<\?php|<\?|\$GLOBALS|\$_(?:GET|POST|REQUEST|SERVER|COOKIE))",
     "WebShell（PHP 代码）", 0.85, "webshell"),

    # 文件上传
    (r"(?:multipart/form-data|file\[\]|input\s+type\s*=\s*['\"]file)",
     "文件上传", 0.75, "file_upload"),
    (r"(?:upload|file|attachment)\s*[=:]\s*['\"]",
     "文件上传（参数）", 0.70, "file_upload"),

    # 认证相关
    (r"(?:Failed password|Failed login|Invalid password|Authentication failed)",
     "认证失败", 0.80, "auth_failure"),
    (r"(?:Accepted password|Accepted publickey|Successful login|Login successful)",
     "认证成功", 0.85, "auth_success"),
    (r"(?:sudo\s+.*:.*COMMAND=|sudo\[.*\]:.*TTY=)",
     "Sudo 提权", 0.85, "privilege_escalation"),
    (r"(?:su:\s+.*session\s+opened|su\[.*\]:.*successful)",
     "Su 提权", 0.80, "privilege_escalation"),
]

# ---------------------------------------------------------------------------
# 分析函数
# ---------------------------------------------------------------------------

def analyze(filepath: str) -> AnalysisResult:
    """分析日志文件。

    支持：
    - Nginx/Apache Access Log
    - syslog
    - auth.log
    - Windows Event Log（.evtx，二进制：先抽 UTF-16LE/ASCII 字符串再分析）
    """
    result = AnalysisResult("logs")

    with open(filepath, "rb") as f:
        raw = f.read()

    if _looks_binary(raw):
        content = _extract_strings(raw)
    else:
        content = raw.decode("utf-8", "replace")

    if content:
        _detect_and_analyze(content, filepath, result)

    return result


def _detect_and_analyze(content: str, filepath: str, result: AnalysisResult):
    """检测日志类型并分析。"""
    lines = content.split("\n")

    # 1. 检测 Access Log 格式
    if _is_access_log(lines):
        _analyze_access_log(content, result)
    # 2. 检测 syslog 格式
    elif _is_syslog(lines):
        _analyze_syslog(content, result)
    # 3. 检测 auth.log 格式
    elif _is_auth_log(lines):
        _analyze_auth_log(content, result)
    # 4. 通用日志分析
    else:
        _analyze_generic(content, result)


def _is_access_log(lines: list) -> bool:
    """检测是否为 Access Log。"""
    access_log_pattern = r'\d+\.\d+\.\d+\.\d+\s+-\s+-\s+\['
    count = sum(1 for line in lines[:100] if re.match(access_log_pattern, line))
    return count > 0


def _is_syslog(lines: list) -> bool:
    """检测是否为 syslog。"""
    syslog_pattern = r'\w+\s+\d+\s+\d+:\d+:\d+\s+\S+'
    count = sum(1 for line in lines[:100] if re.match(syslog_pattern, line))
    return count > 0


def _is_auth_log(lines: list) -> bool:
    """检测是否为 auth.log。"""
    auth_keywords = ["Failed password", "Accepted password", "sudo", "su:"]
    count = sum(1 for line in lines[:100] if any(kw in line for kw in auth_keywords))
    return count > 0


def _analyze_access_log(content: str, result: AnalysisResult):
    """分析 Access Log。"""
    lines = content.split("\n")

    for line in lines:
        if not line.strip():
            continue

        # 提取状态码
        status_match = re.search(r'\s(\d{3})\s', line)
        status = int(status_match.group(1)) if status_match else 0

        # 检查攻击模式
        for pattern, desc, confidence, attack_type in ATTACK_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                # 根据状态码调整置信度
                if status in [200, 301, 302]:
                    confidence = min(confidence + 0.05, 1.0)
                elif status in [403, 404]:
                    confidence = max(confidence - 0.1, 0.5)

                result.findings.append(
                    Finding(
                        kind=f"攻击检测: {desc}",
                        confidence=confidence,
                        evidence=f"状态码: {status}, 请求: {line[:300]}",
                        suggestion=f"检查该请求是否为攻击载荷，可能属于 {attack_type}",
                        module="logs",
                    )
                )
                break

        # 检查异常状态码
        if status in [500, 502, 503]:
            result.findings.append(
                Finding(
                    kind=f"服务器错误: HTTP {status}",
                    confidence=0.60,
                    evidence=f"请求: {line[:300]}",
                    suggestion="检查该请求是否导致服务器错误，可能为攻击尝试",
                    module="logs",
                )
            )


def _analyze_syslog(content: str, result: AnalysisResult):
    """分析 syslog。"""
    lines = content.split("\n")

    for line in lines:
        if not line.strip():
            continue

        # 检查攻击模式
        for pattern, desc, confidence, attack_type in ATTACK_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                result.findings.append(
                    Finding(
                        kind=f"攻击检测: {desc}",
                        confidence=confidence,
                        evidence=f"日志: {line[:300]}",
                        suggestion=f"检查该日志是否为攻击相关，可能属于 {attack_type}",
                        module="logs",
                    )
                )
                break


def _analyze_auth_log(content: str, result: AnalysisResult):
    """分析 auth.log。"""
    lines = content.split("\n")

    for line in lines:
        if not line.strip():
            continue

        # 认证失败
        if "Failed password" in line or "Failed login" in line:
            result.findings.append(
                Finding(
                    kind="认证失败",
                    confidence=0.80,
                    evidence=f"日志: {line[:300]}",
                    suggestion="检查该失败是否为暴力破解攻击",
                    module="logs",
                )
            )

        # 认证成功
        elif "Accepted password" in line or "Accepted publickey" in line:
            result.findings.append(
                Finding(
                    kind="认证成功",
                    confidence=0.85,
                    evidence=f"日志: {line[:300]}",
                    suggestion="检查该登录是否为合法用户",
                    module="logs",
                )
            )

        # Sudo 提权
        elif "sudo" in line.lower() and "command=" in line.lower():
            result.findings.append(
                Finding(
                    kind="Sudo 提权",
                    confidence=0.85,
                    evidence=f"日志: {line[:300]}",
                    suggestion="检查该 sudo 命令是否可疑",
                    module="logs",
                )
            )

        # 检查攻击模式
        for pattern, desc, confidence, attack_type in ATTACK_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                result.findings.append(
                    Finding(
                        kind=f"攻击检测: {desc}",
                        confidence=confidence,
                        evidence=f"日志: {line[:300]}",
                        suggestion=f"检查该日志是否为攻击相关，可能属于 {attack_type}",
                        module="logs",
                    )
                )
                break


def _analyze_generic(content: str, result: AnalysisResult):
    """通用日志分析。"""
    lines = content.split("\n")

    for line in lines:
        if not line.strip():
            continue

        # 检查攻击模式
        for pattern, desc, confidence, attack_type in ATTACK_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                result.findings.append(
                    Finding(
                        kind=f"攻击检测: {desc}",
                        confidence=confidence,
                        evidence=f"日志: {line[:300]}",
                        suggestion=f"检查该日志是否为攻击相关，可能属于 {attack_type}",
                        module="logs",
                    )
                )
                break

        # 检查 flag
        if "flag{" in line.lower():
            result.findings.append(
                Finding(
                    kind="日志中的 flag",
                    confidence=0.97,
                    evidence=f"日志: {line[:300]}",
                    suggestion="提取 flag",
                    module="logs",
                )
            )
