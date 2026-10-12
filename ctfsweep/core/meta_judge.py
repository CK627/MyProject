"""元判断核（meta_judge）：聚合各模块结构化输出，做综合评分。

设计原则：
- 每个模块输出结构化 Finding（kind/confidence/evidence/suggestion/module）
- 元判断核理解各模块的语义，按模块先验做**提升**（模块自评是下界，综合分只会更高）
- 输出综合评分 + 优先级排序 + 行动建议

评分公式（单调不降）：
    基础分 = 模块自评 confidence（被 MODULE_RULES 抬高则为规则分，规则只作下限）
    先验加成 = max(0, (模块权重 - 0.65) * 0.2)      # 权重低于中性点时不减分
    关键词加成 = +0.05（命中 HIGH_PRIORITY_KEYWORDS）
    综合分 = min(基础分 + 加成, 0.95)（基础分已 ≥0.95 时保持原值）

恒有 **综合分 ≥ 模块自评**——模块权重表是"信誉先验"，不是惩罚系数；
加成封顶 0.95 是为了不制造倒挂（0.949 被推到 1.00 而 0.951 停在 0.951 会让低分反超）。

模块权重（经验值，后续可训练优化；0.65 = 中性点，即最常见的通用流量分析）：
- ad.py (Kerberos/NTLM/LDAP): 0.95（域渗透证据强）
- memory.py (Volatility/内存): 0.90（内存取证证据强）
- browser.py (SQLite/JSON): 0.80（浏览器取证中等可信）
- logs.py (Access Log/syslog): 0.75（日志分析中等可信）
- email.py (邮件取证): 0.70（邮件分析中等可信）
- archives.py (压缩): 0.60（解压结果需验证，低于中性点 ⇒ 不加成）
- config.py (配置/密钥): 0.85（密钥泄露证据强）
- db.py (数据库): 0.75（数据库导出中等可信）
- dns.py (DNS): 0.70（DNS 分析中等可信）
- scanner.py (流量): 0.65（中性点）
"""

import json
import math
import os
import re
from typing import Any, Dict, List, Optional

from .utils import BAND_HIGH, BAND_MID, level_of


# ---------------------------------------------------------------------------
# 模块权重表
# ---------------------------------------------------------------------------

MODULE_WEIGHTS = {
    "ad": 0.95,
    "memory": 0.90,
    "browser": 0.80,
    "logs": 0.75,
    "email": 0.70,
    "archives": 0.60,
    "config": 0.85,
    "db": 0.75,
    "dns": 0.70,
    "scanner": 0.65,
}

# 评分参数（不要内联魔数，这几个数是评分语义的一部分）
PRIOR_NEUTRAL = 0.65    # 权重表中性点：等于它的模块既不加也不减
PRIOR_GAIN = 0.2        # 权重高出中性点部分的换算增益
KEYWORD_BONUS = 0.05    # 高优先级关键词加成
BONUS_CEILING = 0.95    # 加成能到达的上限（同时也是"不再加成"的门槛）

# 关键词优先级（高优先级关键词直接给高分）
HIGH_PRIORITY_KEYWORDS = [
    "flag{", "suctf", "ctf", "flag", "解", "答案",
    "password", "secret", "key", "token", "api_key",
    "mimikatz", "procdump", "beacon", "c2",
]

# 模块特定评分规则
MODULE_RULES = {
    "ad": {
        "LDAP口令": 0.93,
        "Kerberos票据": 0.90,
        "NetNTLM": 0.85,
        "域账号": 0.55,
    },
    "memory": {
        "控制台 flag": 0.97,
        "命令行密钥": 0.90,
        "可疑进程": 0.85,
        "网络连接": 0.60,
    },
    "browser": {
        "登录凭据": 0.90,
        "敏感 Cookie": 0.80,
        "可疑历史记录": 0.75,
        "可疑下载": 0.70,
    },
    "logs": {
        "攻击检测: SQL 注入": 0.95,
        "攻击检测: XSS": 0.95,
        "攻击检测: RCE": 0.95,
        "攻击检测: WebShell": 0.95,
        "认证失败": 0.80,
        "认证成功": 0.85,
    },
    "email": {
        "SPF 验证失败": 0.95,
        "DKIM 验证失败": 0.95,
        "DMARC 验证失败": 0.95,
        "HTML 恶意代码": 0.90,
        "可疑链接": 0.85,
    },
    "archives": {
        "flag": 0.97,
        "敏感信息": 0.85,
    },
    "config": {
        "AWS 密钥": 0.95,
        "JWT 密钥": 0.95,
        "数据库密码": 0.95,
        "加密密钥": 0.95,
        "SSH 密钥": 0.95,
        "密码": 0.85,
    },
    "db": {
        "flag": 0.97,
        "敏感字段": 0.85,
    },
    "dns": {
        "长域名（可能为 DNS 外带）": 0.90,
        "DGA 域名": 0.75,
        "DNS TXT 记录": 0.80,
    },
}


# ---------------------------------------------------------------------------
# 元判断核
# ---------------------------------------------------------------------------

def _as_float(value, default=0.0):
    """把任意值安全转成 float。

    None / 非数字 / NaN / ±inf 一律回落 default——元判断核跑在所有模块产出的
    汇合处，而 cli 里的 `meta.score()` 不在 try/except 内，一条畸形 finding
    （比如模块误传了字符串）会中断整份报告。这里必须兜住。
    """
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    return num if math.isfinite(num) else default


class MetaJudge:
    """元判断核：聚合各模块结构化输出，做综合评分。"""

    def __init__(self, findings: List[Dict[str, Any]] = None):
        self.findings = findings or []
        self.scored_findings = []

    def add_finding(self, finding: Dict[str, Any]):
        """添加发现项。"""
        self.findings.append(finding)

    def add_findings(self, findings: List[Dict[str, Any]]):
        """批量添加发现项。"""
        self.findings.extend(findings)

    def score(self) -> List[Dict[str, Any]]:
        """对每个发现项打分。

        返回按分数排序的列表。
        """
        self.scored_findings = []

        for finding in self.findings:
            module = finding.get("module", "scanner")
            # kind/evidence 归一后回写：print_report 直接取用，取值处不必再加守卫
            kind = str(finding.get("kind") or "")
            evidence = str(finding.get("evidence") or "")

            # 1. 模块权重（未知模块按中性点处理）
            module_weight = MODULE_WEIGHTS.get(module, PRIOR_NEUTRAL)

            # 2. 模块自评置信度，归一到 [0,1]
            confidence = _as_float(finding.get("confidence"))
            confidence = min(max(confidence, 0.0), 1.0)

            # 3. 模块特定规则：只作**下限**抬高，不再覆盖（覆盖是可升可降的双向机制，
            #    和权重加成做同一件事，且会让"正则逐字命中"的高分被压低）
            rule_score = MODULE_RULES.get(module, {}).get(kind, None)
            if rule_score is not None:
                confidence = max(confidence, _as_float(rule_score))

            # 4. 模块先验加成：只加不减（archives 等低于中性点的模块加成为 0）
            prior_bonus = max(0.0, (module_weight - PRIOR_NEUTRAL) * PRIOR_GAIN)

            # 5. 综合评分：加成封顶在 BONUS_CEILING，避免与已顶格的形态倒挂
            if confidence < BONUS_CEILING:
                final_score = confidence + prior_bonus
                if any(kw in kind.lower() or kw in evidence.lower() for kw in HIGH_PRIORITY_KEYWORDS):
                    final_score += KEYWORD_BONUS
                final_score = min(final_score, BONUS_CEILING)
            else:
                final_score = confidence
            final_score = min(max(final_score, 0.0), 1.0)

            self.scored_findings.append({
                **finding,
                "kind": kind,
                "evidence": evidence,
                "score": round(final_score, 2),
                "module_weight": module_weight,
                "prior_bonus": round(prior_bonus, 4),
            })

        # 按分数排序
        self.scored_findings.sort(key=lambda x: x["score"], reverse=True)

        return self.scored_findings

    def get_summary(self, min_score: float = 0.0) -> Dict[str, Any]:
        """获取综合摘要（只统计 score >= min_score 的发现项）。"""
        if not self.scored_findings:
            self.score()

        items = [f for f in self.scored_findings if f["score"] >= min_score]
        # 分档走 utils.level_of，与报告/统计保持同一口径
        by_level = {'高': [], '中': [], '低': []}
        for f in items:
            by_level[level_of(f["score"])].append(f)
        high, medium, low = by_level['高'], by_level['中'], by_level['低']

        return {
            "total": len(items),
            "high": len(high),
            "medium": len(medium),
            "low": len(low),
            "modules": list(set(f.get("module", "") for f in items)),
        }

    def get_top_findings(self, n: int = 10, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """获取前 N 个最高分发现项（只含 score >= min_score 的项）。

        同 kind + 同证据只取第一条：**同一份证据在多个会话里重复出现**时
        （FTP 爆破/邮件群发的典型形态），11 条一模一样的"成功凭据"会把前 N 项
        全部占满，其余线索一条都看不见——实测 FTP-malware.pcap 的前 10 项就是
        同一个凭据的 10 份拷贝。分带报告与统计仍按原始条数如实计数，
        这里只是让"前 N 项"真正覆盖 N 条**不同**的线索。
        """
        if not self.scored_findings:
            self.score()
        items = [f for f in self.scored_findings if f["score"] >= min_score]
        out, seen = [], set()
        for f in items:
            key = (f["kind"], f["evidence"])
            if key in seen:
                continue
            seen.add(key)
            out.append(f)
            if len(out) >= n:
                break
        return out

    def get_json(self) -> Dict[str, Any]:
        """获取 JSON 输出（供判断核使用）。"""
        if not self.scored_findings:
            self.score()

        return {
            "summary": self.get_summary(),
            "findings": self.scored_findings,
            "top_findings": self.get_top_findings(10),
        }

    def print_report(self, min_score: float = 0.0):
        """打印报告（遵守 --min-score：低于阈值的发现项不显示）。"""
        if not self.scored_findings:
            self.score()

        summary = self.get_summary(min_score)
        print("\n【元判断核综合评分】")
        print(f"总发现项: {summary['total']}")
        print(f"  高置信（>={BAND_HIGH}）: {summary['high']}")
        print(f"  中置信（{BAND_MID}-{BAND_HIGH}）: {summary['medium']}")
        print(f"  低置信（<{BAND_MID}）: {summary['low']}")

        top = self.get_top_findings(10, min_score)
        if top:
            print("\n【前 10 项发现】")
        for i, finding in enumerate(top, 1):
            conf_label = level_of(finding["score"])
            print(f"  {i}. [{conf_label} {finding['score']:.2f}] {finding['kind']}")
            print(f"     模块: {finding.get('module', 'scanner')}")
            print(f"     证据: {finding.get('evidence', '')[:200]}")
            if finding.get("suggestion"):
                print(f"     建议: {finding['suggestion']}")
            print()
