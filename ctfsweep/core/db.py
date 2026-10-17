# -*- coding: utf-8 -*-
"""数据库导出分析模块（.sql / MongoDB JSON）。

分析链路：
1. 类型匹配 → 检测 SQL/MongoDB 导出格式
2. 解析对应格式 → 提取 INSERT/CREATE/JSON 记录
3. 关键词扫描 → flag/密钥/用户表/配置表
4. 置信度评估 → 高(明文 flag 字段) / 中(可疑表结构) / 低(噪音)
"""

import json
import re
import sqlite3
from .router import Finding, AnalysisResult

# ---------------------------------------------------------------------------
# 分析函数
# ---------------------------------------------------------------------------

def analyze(filepath: str) -> AnalysisResult:
    """分析数据库导出文件。

    支持：
    - .sql 导出（MySQL/PostgreSQL/SQLite）
    - MongoDB JSON 导出
    - SQLite 数据库
    """
    result = AnalysisResult("db")

    with open(filepath, "rb") as f:
        header = f.read(16)

    text = header.decode("utf-8", errors="replace")

    if header.startswith(b"SQLite format 3"):
        # SQLite 数据库
        _analyze_sqlite(filepath, result)
    elif text.strip().startswith("{") or text.strip().startswith("["):
        # JSON 导出（MongoDB）
        _analyze_json_export(filepath, result)
    else:
        # SQL 导出
        _analyze_sql_export(filepath, result)

    return result


def _analyze_sql_export(filepath: str, result: AnalysisResult):
    """分析 SQL 导出文件。"""
    with open(filepath, "r", errors="replace") as f:
        content = f.read()

    lines = content.split("\n")

    # 1. 提取 CREATE TABLE 语句（表结构）
    _parse_create_tables(content, result)

    # 2. 提取 INSERT 语句中的数据
    _parse_insert_values(content, result)

    # 3. 检查 flag
    if "flag{" in content.lower():
        # 提取 flag 所在行
        for i, line in enumerate(lines):
            if "flag{" in line.lower():
                result.findings.append(
                    Finding(
                        kind="SQL 导出中的 flag",
                        confidence=0.97,
                        evidence=f"行 {i+1}: {line[:300]}",
                        suggestion="提取 flag",
                        module="db",
                    )
                )

    # 4. 检查敏感数据
    _scan_sensitive_data(content, result)


def _parse_create_tables(content: str, result: AnalysisResult):
    """解析 CREATE TABLE 语句。"""
    # 提取所有 CREATE TABLE 语句
    create_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?\s*\((.*?)\)'
    matches = re.findall(create_pattern, content, re.IGNORECASE | re.DOTALL)

    for table_name, columns in matches:
        # 检查表名是否可疑
        suspicious_tables = ["flag", "ctf", "secret", "key", "password", "user", "admin"]
        for suspicious in suspicious_tables:
            if suspicious in table_name.lower():
                result.findings.append(
                    Finding(
                        kind=f"可疑表结构: {table_name}",
                        confidence=0.70,
                        evidence=f"表名: {table_name}, 列: {columns[:200]}",
                        suggestion=f"检查该表是否包含敏感数据",
                        module="db",
                    )
                )
                break


def _parse_insert_values(content: str, result: AnalysisResult):
    """解析 INSERT 语句中的数据。"""
    # 提取 INSERT INTO ... VALUES 语句
    insert_pattern = r'INSERT\s+INTO\s+[`"\']?(\w+)[`"\']?\s*\(.*?\)\s*VALUES\s*(.*?)\s*;'
    matches = re.findall(insert_pattern, content, re.IGNORECASE | re.DOTALL)

    for table_name, values in matches:
        # 检查值中是否包含 flag
        if "flag{" in values.lower():
            result.findings.append(
                Finding(
                    kind=f"表 {table_name} 中的 flag",
                    confidence=0.97,
                    evidence=f"表: {table_name}, 值: {values[:300]}",
                    suggestion="提取 flag",
                    module="db",
                )
            )

        # 检查值中是否包含敏感数据
        for keyword in ["password", "secret", "key", "token"]:
            if keyword in values.lower():
                result.findings.append(
                    Finding(
                        kind=f"表 {table_name} 中的敏感数据",
                        confidence=0.80,
                        evidence=f"表: {table_name}, 包含: {keyword}",
                        suggestion="检查该数据是否敏感",
                        module="db",
                    )
                )


def _analyze_json_export(filepath: str, result: AnalysisResult):
    """分析 MongoDB JSON 导出。"""
    with open(filepath, "r", errors="replace") as f:
        content = f.read()

    try:
        # 尝试解析为 JSON 数组
        data = json.loads(content)
        if isinstance(data, list):
            _scan_json_array(data, result)
        elif isinstance(data, dict):
            _scan_json_object(data, result)
    except json.JSONDecodeError:
        # 尝试逐行解析（JSON Lines 格式）
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                data = json.loads(line)
                _scan_json_object(data, result)
            except json.JSONDecodeError:
                continue


def _scan_json_array(data: list, result: AnalysisResult):
    """扫描 JSON 数组。"""
    for item in data:
        if isinstance(item, dict):
            _scan_json_object(item, result)
        elif isinstance(item, str):
            if "flag{" in item.lower():
                result.findings.append(
                    Finding(
                        kind="JSON 中的 flag",
                        confidence=0.97,
                        evidence=f"值: {item[:300]}",
                        suggestion="提取 flag",
                        module="db",
                    )
                )


def _scan_json_object(data: dict, result: AnalysisResult):
    """扫描 JSON 对象。"""
    for key, value in data.items():
        # 检查键是否敏感
        sensitive_keys = ["flag", "secret", "key", "password", "token", "api_key"]
        for sensitive in sensitive_keys:
            if sensitive in key.lower():
                if isinstance(value, str) and len(value) > 5:
                    result.findings.append(
                        Finding(
                            kind=f"敏感字段: {key}",
                            confidence=0.85,
                            evidence=f"键: {key}, 值: {value[:200]}",
                            suggestion="检查该字段是否敏感",
                            module="db",
                        )
                    )
                break

        # 检查值是否包含 flag
        if isinstance(value, str) and "flag{" in value.lower():
            result.findings.append(
                Finding(
                    kind="JSON 中的 flag",
                    confidence=0.97,
                    evidence=f"键: {key}, 值: {value[:300]}",
                    suggestion="提取 flag",
                    module="db",
                )
            )
        elif isinstance(value, (dict, list)):
            _scan_json_object(value, result) if isinstance(value, dict) else _scan_json_array(value, result)


def _analyze_sqlite(filepath: str, result: AnalysisResult):
    """分析 SQLite 数据库。"""
    try:
        conn = sqlite3.connect(f"file:{filepath}?mode=ro", uri=True)
        cursor = conn.cursor()

        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # 检查表名
        suspicious_tables = ["flag", "ctf", "secret", "key", "password"]
        for table in tables:
            for suspicious in suspicious_tables:
                if suspicious in table.lower():
                    result.findings.append(
                        Finding(
                            kind=f"可疑表: {table}",
                            confidence=0.70,
                            evidence=f"表名: {table}",
                            suggestion="检查该表是否包含敏感数据",
                            module="db",
                        )
                    )
                    break

        # 查询每个表的内容
        for table in tables:
            try:
                cursor.execute(f"SELECT * FROM [{table}] LIMIT 100")
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

                for row in rows:
                    for i, value in enumerate(row):
                        if value and isinstance(value, str):
                            if "flag{" in value.lower():
                                result.findings.append(
                                    Finding(
                                        kind=f"表 {table} 中的 flag",
                                        confidence=0.97,
                                        evidence=f"表: {table}, 列: {columns[i]}, 值: {value[:300]}",
                                        suggestion="提取 flag",
                                        module="db",
                                    )
                                )
                            elif any(kw in value.lower() for kw in ["password", "secret", "key", "token"]):
                                result.findings.append(
                                    Finding(
                                        kind=f"表 {table} 中的敏感数据",
                                        confidence=0.80,
                                        evidence=f"表: {table}, 列: {columns[i]}, 值: {value[:200]}",
                                        suggestion="检查该数据是否敏感",
                                        module="db",
                                    )
                                )
            except Exception:
                continue

        conn.close()
    except Exception as e:
        result.findings.append(
            Finding(
                kind="SQLite 解析失败",
                confidence=0.0,
                evidence=str(e),
                module="db",
            )
        )


def _scan_sensitive_data(content: str, result: AnalysisResult):
    """扫描敏感数据。"""
    for keyword in ["password=", "secret=", "api_key=", "token="]:
        if keyword in content.lower():
            result.findings.append(
                Finding(
                    kind="SQL 导出中的敏感数据",
                    confidence=0.80,
                    evidence=f"包含: {keyword}",
                    suggestion="检查该数据是否敏感",
                    module="db",
                )
            )
