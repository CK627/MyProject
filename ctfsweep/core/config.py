# -*- coding: utf-8 -*-
"""配置/密钥泄露扫描模块（.env / config.php / settings.json / .git / docker-compose.yml）。

分析链路：
1. 类型匹配 → 检测配置文件格式
2. 解析对应格式 → 提取键值对/配置项
3. 关键词扫描 → AWS_SECRET/DATABASE_URL/password=/api_key=/SECRET_KEY
4. 置信度评估 → 高(硬编码密码/密钥) / 中(环境变量名) / 低(注释中的密钥)
"""

import json
import os
import re
import yaml
from .router import Finding, AnalysisResult

# ---------------------------------------------------------------------------
# 敏感关键词模式
# ---------------------------------------------------------------------------

SENSITIVE_PATTERNS = [
    # AWS
    (r"(?:AWS_SECRET|AWS_KEY|AWS_ACCESS_KEY|AWS_SECRET_KEY)\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{16,})",
     "AWS 密钥", 0.95, "aws_secret"),
    (r"(?:AWS_REGION|AWS_BUCKET|AWS_S3)\s*[=:]\s*['\"]?(\S+)",
     "AWS 配置", 0.80, "aws_config"),

    # 数据库
    (r"(?:DATABASE_URL|DB_URL|DATABASE_URI)\s*[=:]\s*['\"]?(\S+)",
     "数据库连接串", 0.90, "database_url"),
    (r"(?:MYSQL_ROOT_PASSWORD|DB_PASSWORD|DB_PASS|DATABASE_PASSWORD|DB_PASSWD)\s*[=:]\s*['\"]?(\S+)",
     "数据库密码", 0.95, "database_password"),
    (r"(?:POSTGRES_PASSWORD|MYSQL_PASSWORD|MONGO_PASSWORD)\s*[=:]\s*['\"]?(\S+)",
     "数据库密码", 0.95, "database_password"),

    # API 密钥
    (r"(?:API_KEY|API_SECRET|API_TOKEN|SECRET_KEY|SECRET|APP_SECRET)\s*[=:]\s*['\"]?([A-Za-z0-9/+=_-]{8,})",
     "API 密钥", 0.90, "api_key"),
    (r"(?:GOOGLE_API_KEY|GOOGLE_MAPS_API_KEY|GEMINI_API_KEY)\s*[=:]\s*['\"]?([A-Za-z0-9_-]{16,})",
     "Google API 密钥", 0.95, "google_api_key"),
    (r"(?:GH_TOKEN|GITHUB_TOKEN|GIT_TOKEN)\s*[=:]\s*['\"]?([A-Za-z0-9]{20,})",
     "Git 令牌", 0.95, "git_token"),
    (r"(?:SLACK_TOKEN|SLACK_WEBHOOK|DISCORD_TOKEN|DISCORD_WEBHOOK)\s*[=:]\s*['\"]?([A-Za-z0-9_-]{20,})",
     "Slack/Discord 令牌", 0.90, "slack_discord_token"),

    # 通用密码
    (r"(?:PASSWORD|PASS|PASSWD|PWD)\s*[=:]\s*['\"]?(\S+)",
     "密码", 0.85, "password"),
    (r"(?:USERNAME|USER|LOGIN|ACCOUNT)\s*[=:]\s*['\"]?(\S+)",
     "用户名", 0.70, "username"),

    # JWT
    (r"(?:JWT_SECRET|JWT_KEY|JWT_TOKEN)\s*[=:]\s*['\"]?(\S+)",
     "JWT 密钥", 0.95, "jwt_secret"),

    # Redis
    (r"(?:REDIS_PASSWORD|REDIS_URL|REDIS_HOST)\s*[=:]\s*['\"]?(\S+)",
     "Redis 配置", 0.85, "redis_config"),

    # Docker
    (r"(?:DOCKER_PASSWORD|DOCKER_USERNAME|DOCKER_REGISTRY)\s*[=:]\s*['\"]?(\S+)",
     "Docker 凭据", 0.90, "docker_credential"),

    # SSH
    (r"(?:SSH_PRIVATE_KEY|SSH_KEY)\s*[=:]\s*['\"]?([A-Za-z0-9+/=]{32,})",
     "SSH 密钥", 0.95, "ssh_key"),

    # 证书
    (r"(?:SSL_CERT|SSL_KEY|TLS_CERT|TLS_KEY)\s*[=:]\s*['\"]?(\S+)",
     "SSL/TLS 证书", 0.85, "ssl_cert"),

    # 加密
    (r"(?:ENCRYPTION_KEY|ENCRYPT_KEY|AES_KEY|RSA_KEY)\s*[=:]\s*['\"]?([A-Za-z0-9+/=]{16,})",
     "加密密钥", 0.95, "encryption_key"),

    # 邮件
    (r"(?:MAIL_PASSWORD|MAIL_USERNAME|SMTP_PASSWORD|SMTP_USERNAME)\s*[=:]\s*['\"]?(\S+)",
     "邮件凭据", 0.85, "mail_credential"),
]

# 配置文件文件名模式
CONFIG_FILE_PATTERNS = [
    r"\.env$",
    r"\.env\.(?:local|dev|staging|prod|test)$",
    r"config\.(?:php|py|js|ts|json|yml|yaml|toml)$",
    r"settings\.(?:php|py|js|ts|json|yml|yaml|toml)$",
    r"docker-compose\.(?:yml|yaml)$",
    r"\.git(?:config|modules)?$",
    r"webpack\.(?:config\.js|dev\.js)$",
    r"Gemfile(?:\.lock)?$",
    r"package\.json$",
    r"composer\.(?:json|lock)$",
    r"Cargo\.(?:toml|lock)$",
    r"go\.(?:mod|sum)$",
]

# ---------------------------------------------------------------------------
# 分析函数
# ---------------------------------------------------------------------------

def analyze(filepath: str) -> AnalysisResult:
    """分析配置文件/密钥泄露。

    支持：
    - .env 文件
    - config.php/config.js/config.json
    - settings.json/settings.py
    - docker-compose.yml
    - .git/config
    """
    result = AnalysisResult("config")

    with open(filepath, "r", errors="replace") as f:
        content = f.read()

    # 检测配置文件格式
    filename = os.path.basename(filepath).lower()

    if filename.startswith(".env") or "dotenv" in content.lower():
        _analyze_env(content, result)
    elif filename.endswith(".php"):
        _analyze_php(content, result)
    elif filename.endswith(".json"):
        _analyze_json(content, result)
    elif filename.endswith((".yml", ".yaml")):
        _analyze_yaml(content, result)
    elif filename.endswith(".js") or filename.endswith(".ts"):
        _analyze_js(content, result)
    elif filename.endswith(".py"):
        _analyze_python(content, result)
    elif ".git" in filepath:
        _analyze_git(content, filepath, result)
    else:
        # 通用配置扫描
        _analyze_generic(content, result)

    return result


def _analyze_env(content: str, result: AnalysisResult):
    """解析 .env 文件。"""
    lines = content.split("\n")

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 提取键值对
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$", line)
        if match:
            key = match.group(1)
            value = match.group(2).strip().strip("'\"")

            # 检查是否为敏感键
            for pattern, desc, confidence, category in SENSITIVE_PATTERNS:
                if re.search(pattern, f"{key}={value}", re.IGNORECASE):
                    result.findings.append(
                        Finding(
                            kind=f"敏感配置: {desc}",
                            confidence=confidence,
                            evidence=f"键: {key}, 值: {value[:100]}",
                            suggestion=f"该配置可能包含敏感信息（{category}）",
                            module="config",
                        )
                    )
                    break


def _analyze_php(content: str, result: AnalysisResult):
    """解析 PHP 配置文件。"""
    # 提取 PHP 变量
    php_vars = re.findall(r'\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*["\']([^"\']+)["\']', content)

    for var_name, var_value in php_vars:
        for pattern, desc, confidence, category in SENSITIVE_PATTERNS:
            if re.search(pattern, f"{var_name}={var_value}", re.IGNORECASE):
                result.findings.append(
                    Finding(
                        kind=f"敏感配置: {desc}",
                        confidence=confidence,
                        evidence=f"变量: ${{var_name}}, 值: {var_value[:100]}",
                        suggestion=f"该配置可能包含敏感信息（{category}）",
                        module="config",
                    )
                )
                break

    # 检查 flag
    if "flag{" in content.lower():
        result.findings.append(
            Finding(
                kind="配置中的 flag",
                confidence=0.97,
                evidence=f"配置: {content[:300]}",
                suggestion="提取 flag",
                module="config",
            )
        )


def _analyze_json(content: str, result: AnalysisResult):
    """解析 JSON 配置文件。"""
    try:
        data = json.loads(content)
        _extract_json_values(data, result)
    except json.JSONDecodeError:
        # 尝试通用扫描
        _analyze_generic(content, result)


def _extract_json_values(data, result: AnalysisResult):
    """递归提取 JSON 中的敏感值。"""
    if isinstance(data, dict):
        for key, value in data.items():
            for pattern, desc, confidence, category in SENSITIVE_PATTERNS:
                if re.search(pattern, key, re.IGNORECASE):
                    result.findings.append(
                        Finding(
                            kind=f"敏感配置: {desc}",
                            confidence=confidence,
                            evidence=f"键: {key}, 值: {str(value)[:100]}",
                            suggestion=f"该配置可能包含敏感信息（{category}）",
                            module="config",
                        )
                    )
                    break

            if isinstance(value, (dict, list)):
                _extract_json_values(value, result)
    elif isinstance(data, list):
        for item in data:
            _extract_json_values(item, result)


def _analyze_yaml(content: str, result: AnalysisResult):
    """解析 YAML 配置文件。"""
    try:
        data = yaml.safe_load(content)
        _extract_json_values(data, result)
    except Exception:
        # 尝试通用扫描
        _analyze_generic(content, result)


def _analyze_js(content: str, result: AnalysisResult):
    """解析 JavaScript/TypeScript 配置文件。"""
    # 提取 JavaScript 变量
    js_vars = re.findall(r'(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*["\']([^"\']+)["\']', content)

    for var_name, var_value in js_vars:
        for pattern, desc, confidence, category in SENSITIVE_PATTERNS:
            if re.search(pattern, f"{var_name}={var_value}", re.IGNORECASE):
                result.findings.append(
                    Finding(
                        kind=f"敏感配置: {desc}",
                        confidence=confidence,
                        evidence=f"变量: {var_name}, 值: {var_value[:100]}",
                        suggestion=f"该配置可能包含敏感信息（{category}）",
                        module="config",
                    )
                )
                break

    # 检查 flag
    if "flag{" in content.lower():
        result.findings.append(
            Finding(
                kind="配置中的 flag",
                confidence=0.97,
                evidence=f"配置: {content[:300]}",
                suggestion="提取 flag",
                module="config",
            )
        )


def _analyze_python(content: str, result: AnalysisResult):
    """解析 Python 配置文件。"""
    # 提取 Python 变量
    py_vars = re.findall(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)

    for var_name, var_value in py_vars:
        for pattern, desc, confidence, category in SENSITIVE_PATTERNS:
            if re.search(pattern, f"{var_name}={var_value}", re.IGNORECASE):
                result.findings.append(
                    Finding(
                        kind=f"敏感配置: {desc}",
                        confidence=confidence,
                        evidence=f"变量: {var_name}, 值: {var_value[:100]}",
                        suggestion=f"该配置可能包含敏感信息（{category}）",
                        module="config",
                    )
                )
                break

    # 检查 flag
    if "flag{" in content.lower():
        result.findings.append(
            Finding(
                kind="配置中的 flag",
                confidence=0.97,
                evidence=f"配置: {content[:300]}",
                suggestion="提取 flag",
                module="config",
            )
        )


def _analyze_git(content: str, filepath: str, result: AnalysisResult):
    """解析 .git 配置。"""
    # 提取远程 URL
    remote_match = re.search(r'url\s*=\s*(\S+)', content)
    if remote_match:
        remote_url = remote_match.group(1)
        result.findings.append(
            Finding(
                kind="Git 远程 URL",
                confidence=0.70,
                evidence=f"远程 URL: {remote_url}",
                suggestion="检查该远程 URL 是否为敏感仓库",
                module="config",
            )
        )

    # 检查是否有密码
    if "password" in content.lower() or "token" in content.lower():
        result.findings.append(
            Finding(
                kind="Git 配置中的敏感信息",
                confidence=0.85,
                evidence=f"配置: {content[:300]}",
                suggestion="检查该 Git 配置是否包含敏感信息",
                module="config",
            )
        )


def _analyze_generic(content: str, result: AnalysisResult):
    """通用配置扫描。"""
    for pattern, desc, confidence, category in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            value = match if isinstance(match, str) else match[0] if isinstance(match, tuple) else str(match)
            result.findings.append(
                Finding(
                    kind=f"敏感配置: {desc}",
                    confidence=confidence,
                    evidence=f"值: {value[:100]}",
                    suggestion=f"该配置可能包含敏感信息（{category}）",
                    module="config",
                )
            )

    # 检查 flag
    if "flag{" in content.lower():
        result.findings.append(
            Finding(
                kind="配置中的 flag",
                confidence=0.97,
                evidence=f"配置: {content[:300]}",
                suggestion="提取 flag",
                module="config",
            )
        )
