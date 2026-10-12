"""浏览器取证模块（Chrome/Edge/Firefox）。

支持格式：
- Chrome/Edge SQLite 数据库（History、Login Data、Cookies、Bookmarks、Downloads）
- Chrome Bookmarks JSON 文件
- Firefox Places.sqlite

分析链路：
1. 类型匹配 → SQLite / JSON
2. 解析对应格式 → 提取历史/书签/Cookie/下载
3. 关键词扫描 → flag/CTF 站点/可疑 URL/敏感 Cookie
4. 置信度评估 → 高(flag URL/敏感 Cookie) / 中(可疑书签/下载) / 低(普通历史)
"""

import json
import os
import re
import sqlite3
from .router import Finding, AnalysisResult

# ---------------------------------------------------------------------------
# 可疑 URL 关键词
# ---------------------------------------------------------------------------

SUSPICIOUS_URL_PATTERNS = [
    (r"flag", "Flag 相关 URL"),
    (r"ctf", "CTF 站点"),
    (r"suctf", "SUCTF 站点"),
    (r"admin", "Admin 页面"),
    (r"login", "登录页面"),
    (r"upload", "上传页面"),
    (r"download", "下载页面"),
    (r"secret", "Secret 页面"),
    (r"password", "密码页面"),
    (r"token", "Token 页面"),
    (r"api_key", "API Key 页面"),
    (r"key", "Key 页面"),
    (r"private", "Private 页面"),
    (r"hidden", "Hidden 页面"),
    (r"hidden", "Hidden 页面"),
    (r"\.pdf", "PDF 文件下载"),
    (r"\.zip", "ZIP 文件下载"),
    (r"\.rar", "RAR 文件下载"),
    (r"\.7z", "7Z 文件下载"),
]

# 敏感 Cookie 关键词
SENSITIVE_COOKIE_PATTERNS = [
    r"session",
    r"token",
    r"auth",
    r"password",
    r"secret",
    r"api_key",
    r"jwt",
    r"csrf",
    r"csrf_token",
    r"remember",
    r"login",
]

# ---------------------------------------------------------------------------
# 分析函数
# ---------------------------------------------------------------------------

def analyze(filepath: str) -> AnalysisResult:
    """分析浏览器文件。

    支持：
    - SQLite 数据库（History、Login Data、Cookies、Downloads）
    - JSON 文件（Bookmarks）
    """
    result = AnalysisResult("browser")

    # 检测文件类型
    with open(filepath, "rb") as f:
        header = f.read(16)

    if header.startswith(b"SQLite format 3"):
        # SQLite 数据库
        _analyze_sqlite(filepath, result)
    elif filepath.endswith(".json") or filepath.endswith(".jsonl"):
        # JSON 文件（Bookmarks）
        _analyze_json(filepath, result)
    elif filepath.endswith(".html") or filepath.endswith(".htm"):
        # HTML 文件（导出书签）
        _analyze_html(filepath, result)
    else:
        # 尝试 SQLite
        try:
            _analyze_sqlite(filepath, result)
        except Exception:
            pass

    return result


def _analyze_sqlite(filepath: str, result: AnalysisResult):
    """解析 SQLite 数据库。"""
    try:
        conn = sqlite3.connect(f"file:{filepath}?mode=ro", uri=True)
        cursor = conn.cursor()

        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # 1. 解析 History
        if "urls" in tables or "history" in tables:
            _parse_history(conn, tables, result)

        # 2. 解析 Cookies
        if "cookies" in tables:
            _parse_cookies(conn, result)

        # 3. 解析 Downloads
        if "downloads" in tables:
            _parse_downloads(conn, tables, result)

        # 4. 解析 Login Data
        if "logins" in tables:
            _parse_logins(conn, tables, result)

        conn.close()
    except Exception as e:
        result.findings.append(
            Finding(
                kind="SQLite 解析失败",
                confidence=0.0,
                evidence=str(e),
                module="browser",
            )
        )


def _parse_history(conn: sqlite3.Connection, tables: list, result: AnalysisResult):
    """解析浏览器历史记录。"""
    # 尝试 urls 表（Chrome/Edge）
    table = None
    url_col = None
    title_col = None

    if "urls" in tables:
        table = "urls"
        url_col = "url"
        title_col = "title"
    elif "history" in tables:
        table = "history"
        url_col = "url"
        title_col = "title"

    if table:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT {url_col}, {title_col} FROM {table} LIMIT 1000")
            rows = cursor.fetchall()

            for row in rows:
                url = row[0]
                title = row[1] or ""

                # 检查 URL 是否匹配可疑模式
                for pattern, desc in SUSPICIOUS_URL_PATTERNS:
                    if re.search(pattern, url, re.IGNORECASE):
                        result.findings.append(
                            Finding(
                                kind=f"可疑历史记录: {desc}",
                                confidence=0.75 if "flag" in pattern or "ctf" in pattern else 0.60,
                                evidence=f"URL: {url[:200]}, 标题: {title[:100]}",
                                suggestion=f"检查该 URL 是否与 CTF 或攻击相关",
                                module="browser",
                            )
                        )
                        break
        except Exception:
            pass


def _parse_cookies(conn: sqlite3.Connection, result: AnalysisResult):
    """解析 Cookie。"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name, value, host_key FROM cookies LIMIT 500")
        rows = cursor.fetchall()

        for row in rows:
            name, value, host = row

            # 检查 Cookie 是否敏感
            for pattern in SENSITIVE_COOKIE_PATTERNS:
                if re.search(pattern, name, re.IGNORECASE):
                    result.findings.append(
                        Finding(
                            kind=f"敏感 Cookie: {name}",
                            confidence=0.80,
                            evidence=f"域名: {host}, 名称: {name}, 值: {value[:100]}",
                            suggestion=f"该 Cookie 可能包含敏感信息（session/token/auth）",
                            module="browser",
                        )
                    )
                    break
    except Exception:
        pass


def _parse_downloads(conn: sqlite3.Connection, tables: list, result: AnalysisResult):
    """解析下载历史。"""
    table = None
    url_col = None
    path_col = None

    if "downloads" in tables:
        table = "downloads"
        url_col = "tab_url"
        path_col = "target_path"
    elif "download_history" in tables:
        table = "download_history"
        url_col = "url"
        path_col = "path"

    if table:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT {url_col}, {path_col} FROM {table} LIMIT 500")
            rows = cursor.fetchall()

            for row in rows:
                url = row[0] or ""
                path = row[1] or ""

                # 检查下载路径是否可疑
                for pattern, desc in SUSPICIOUS_URL_PATTERNS:
                    if re.search(pattern, path, re.IGNORECASE):
                        result.findings.append(
                            Finding(
                                kind=f"可疑下载: {desc}",
                                confidence=0.70,
                                evidence=f"URL: {url[:200]}, 路径: {path}",
                                suggestion=f"检查该下载是否与 CTF 或攻击相关",
                                module="browser",
                            )
                        )
                        break
        except Exception:
            pass


def _parse_logins(conn: sqlite3.Connection, tables: list, result: AnalysisResult):
    """解析登录凭据。"""
    table = None
    origin_col = None
    user_col = None
    pass_col = None

    if "logins" in tables:
        table = "logins"
        origin_col = "origin_url"
        user_col = "username_value"
        pass_col = "password_value"
    elif "signons" in tables:
        table = "signons"
        origin_col = "hostname"
        user_col = "username_field"
        pass_col = "password_field"

    if table:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT {origin_col}, {user_col}, {pass_col} FROM {table} LIMIT 100")
            rows = cursor.fetchall()

            for row in rows:
                origin, username, password = row

                if password and len(password) > 5:
                    result.findings.append(
                        Finding(
                            kind="登录凭据",
                            confidence=0.90,
                            evidence=f"域名: {origin}, 用户名: {username}, 密码: {password[:100]}",
                            suggestion="该凭据可能用于登录 CTF 站点或攻击目标",
                            module="browser",
                        )
                    )
        except Exception:
            pass


def _analyze_json(filepath: str, result: AnalysisResult):
    """解析 JSON 文件（Bookmarks）。"""
    try:
        with open(filepath, "r", errors="replace") as f:
            data = json.load(f)

        # 递归查找 URL
        _find_urls_json(data, result)
    except Exception as e:
        result.findings.append(
            Finding(
                kind="JSON 解析失败",
                confidence=0.0,
                evidence=str(e),
                module="browser",
            )
        )


def _find_urls_json(data, result: AnalysisResult):
    """递归查找 JSON 中的 URL。"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) and ("http" in value or "www" in value):
                # 检查 URL 是否匹配可疑模式
                for pattern, desc in SUSPICIOUS_URL_PATTERNS:
                    if re.search(pattern, value, re.IGNORECASE):
                        result.findings.append(
                            Finding(
                                kind=f"可疑书签: {desc}",
                                confidence=0.75 if "flag" in pattern or "ctf" in pattern else 0.60,
                                evidence=f"URL: {value[:200]}, 键: {key}",
                                suggestion=f"检查该书签是否与 CTF 或攻击相关",
                                module="browser",
                            )
                        )
                        break
            elif isinstance(value, (dict, list)):
                _find_urls_json(value, result)
    elif isinstance(data, list):
        for item in data:
            _find_urls_json(item, result)


def _analyze_html(filepath: str, result: AnalysisResult):
    """解析 HTML 文件（导出书签）。"""
    try:
        with open(filepath, "r", errors="replace") as f:
            content = f.read()

        # 提取 URL
        urls = re.findall(r'href=["\'](.*?)["\']', content)
        for url in urls:
            for pattern, desc in SUSPICIOUS_URL_PATTERNS:
                if re.search(pattern, url, re.IGNORECASE):
                    result.findings.append(
                        Finding(
                            kind=f"可疑书签: {desc}",
                            confidence=0.75 if "flag" in pattern or "ctf" in pattern else 0.60,
                            evidence=f"URL: {url[:200]}",
                            suggestion=f"检查该书签是否与 CTF 或攻击相关",
                            module="browser",
                        )
                    )
                    break
    except Exception:
        pass
