"""智能路由：类型匹配 → 模块调度 → 结构化输出 → 判断核聚合。

设计原则：
- 每个分析模块输出统一的 JSON 结构，包含置信度、证据、建议
- 调度器根据文件类型自动匹配模块
- 判断核能理解各模块的结构化输出，做综合评分
"""

import os
from typing import Any, Dict, List

from .utils import level_of


# ---------------------------------------------------------------------------
# 统一输出结构
# ---------------------------------------------------------------------------

class Finding:
    """单个发现项——全项目的统一候选货币。

    文件类型模块（dns/logs/config…）直接构造 `Finding`；流扫描（scanner/ad）
    内部仍用 5 元组 `(score, kind, tok, val, loc)` 这个局部 ABI，
    在边界上经 `from_tuple()` / `to_tuple()` 转换。

    两条不能违反的约定：
    * `to_tuple()` **原样回吐** `tok`/`val`（bytes 就是 bytes，不解码）。
      `report()` 对 `val` 用 utf-8、对 `tok` 用 **latin-1** 解码，提前解码会
      静默改掉非 UTF-8 的 token。
    * `confidence` 存**不 round 的原始值**；只有 `to_dict()` 才 round。
      留存区 / 候选池 / `report()` 都要原始值。
    """

    def __init__(
        self,
        kind: str,
        confidence: float,
        evidence: str,
        suggestion: str = "",
        module: str = "",
        tok: Any = b"",
        loc: str = "",
        val: Any = None,
    ):
        self.kind = kind
        self.confidence = confidence
        self.evidence = evidence
        self.suggestion = suggestion
        self.module = module
        self.tok = tok
        self.loc = loc
        # 缺省回落 evidence：这样既有模块的 Finding(...) 调用点不必改动
        self.val = evidence if val is None else val

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "kind": self.kind,
            "confidence": round(self.confidence, 2),
            "evidence": self.evidence,
            "module": self.module,
        }
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d

    def to_meta_dict(self) -> Dict[str, Any]:
        """给 MetaJudge 的字典。

        刻意不用 `to_dict()`：`to_dict()` 会 round confidence，而元判断核的排序与
        加成吃的是**未 round** 的原始值，换成 round 值会改掉并列项顺序与加分。
        `evidence` 取 `str(val)[:300]`——bytes 会带 `b'…'` repr，与流扫描模块内部
        的结构化输出同形。
        """
        return {
            "kind": self.kind,
            "confidence": self.confidence,
            "evidence": str(self.val)[:300],
            "module": self.module,
        }

    def to_tuple(self):
        """导出为 5 元组（给继续吃元组的旧接口：report / judge.predict_finding）。"""
        return (self.confidence, self.kind, self.tok, self.val, self.loc)

    @classmethod
    def from_tuple(cls, t, module: str = "scanner"):
        """从 5 元组构造。`evidence` 与旧版结构化输出同形：`str(val)[:300]`。"""
        score, kind, tok, val, loc = t
        return cls(kind=kind, confidence=score, evidence=str(val)[:300],
                   module=module, tok=tok, loc=loc, val=val)


class AnalysisResult:
    """单次分析结果。"""

    def __init__(self, module: str, findings: List[Finding] = None):
        self.module = module
        self.findings = findings or []


# ---------------------------------------------------------------------------
# 类型匹配
# ---------------------------------------------------------------------------

# 文件类型 → 模块优先级列表
_TYPE_MAP = {
    ".mem": ["memory"],
    ".raw": ["memory"],
    ".pcap": ["scanner", "ad", "dns"],
    ".pcapng": ["scanner", "ad", "dns"],
    ".evtx": ["logs"],
    ".log": ["logs"],
    ".txt": ["config"],
    ".json": ["browser", "config"],
    ".xml": ["email"],
    ".eml": ["email"],
    ".pst": ["email"],
    ".mbox": ["email"],
    ".msg": ["email"],
    ".zip": ["archives"],
    ".rar": ["archives"],
    ".7z": ["archives"],
    ".tar": ["archives"],
    ".gz": ["archives"],
    ".sql": ["db"],
    ".db": ["browser", "db"],
    ".sqlite": ["browser", "db"],
    ".env": ["config"],
    ".git": ["config"],
}

# 内容匹配（字节特征）
_CONTENT_SIGNS = [
    (b"SQLite format 3", "browser", "SQLite 数据库"),
    (b"PK\x03\x04", "archives", "ZIP 归档"),
    (b"\x1f\x8b", "archives", "GZIP"),
    (b"RAR\x07", "archives", "RAR"),
    (b"7z\xbc\xaf\x27\x1d", "archives", "7-Zip"),
    (b"volatility", "memory", "Volatility 输出"),
    (b"Received: from", "email", "邮件头"),
]

# 注：这里曾有条目把含 `HTTP/1.` 的内容判给 scanner、含 `krbtgt`/`NTLMSSP` 的判给 ad。
# 前者一旦 scanner 有了 analyze()，任何前 1KB 带 `HTTP/1.` 的日志/文本都会凭空多出一个
# 【scanner】块；后者与 .pcap 的类型映射重复（ad 已在列表里）。两者都已删除。


def match_module(filepath: str) -> List[str]:
    """根据文件类型和内容匹配模块。

    返回模块优先级列表。
    """
    result = []

    # 1. 类型匹配
    ext = os.path.splitext(filepath)[1].lower()
    if ext in _TYPE_MAP:
        result.extend(_TYPE_MAP[ext])

    # 2. 内容匹配（读前 1KB）
    try:
        with open(filepath, "rb") as f:
            header = f.read(1024)
        for sign, module, desc in _CONTENT_SIGNS:
            if sign in header:
                if module not in result:
                    result.append(module)
    except Exception:
        pass

    # 去重并保持优先级
    seen = set()
    unique = []
    for m in result:
        if m not in seen:
            seen.add(m)
            unique.append(m)
    return unique


# ---------------------------------------------------------------------------
# 调度器
# ---------------------------------------------------------------------------


class ScanOptions:
    """流扫描（scanner）的运行时参数：由 CLI 装配，模块只读。"""

    def __init__(self, keywords=(), decode=True, depth=3, limit=50, extract=None,
                 quiet=False):
        self.keywords = keywords
        self.decode = decode
        self.depth = depth
        self.limit = limit
        self.extract = extract          # {'outdir':…, 'stem':…} 或 None
        self.quiet = quiet              # 供非扫描场景（mark 补扫 / 单测）静音过程输出


# 模块角色：决定它在哪个阶段跑、由谁驱动。
#   filetype —— 按文件类型分派，产出 `【<模块名>】` 块（dns/logs/config/…）
#   stream   —— 流扫描阶段，产出交给分带报告（report()），**不打模块块**
#   sub      —— 不顶层分派，由 stream 模块在内部驱动（ad 由 scanner 驱动：
#                AD 的 findings 必须保持 module="scanner"，且 print_ad_info 的位置
#                在 [交互会话] 之前——挪到顶层会同时改变打分与打印位置）
_MODULE_ROLE = {"scanner": "stream", "ad": "sub"}

# 流扫描模块：**每个文件都跑**（抓包走 scan_capture，其余走 scan_rawfile）。
# 它不由 match_module() 决定——`_TYPE_MAP` 里只列了 .pcap/.pcapng，
# 而原始字节扫描是全体文件的兜底能力。
_STREAM_MODULE = "scanner"


class Router:
    """分析路由 + 调度。

    分两个阶段执行（顺序不可颠倒）：
      1. `run_filetype()` —— 文件类型模块，产出 `【模块名】` 块；
      2. `run_stream()`   —— 流扫描，它的过程输出（格式:/主机表/[交互会话]/[提取]）
         与分带报告交错，必须**排在文件类型块之后**。

    `tests/test_smoke.py` 断言 `【dns】` 出现在 `格式:` 之前——即阶段次序本身是契约。
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.modules = match_module(filepath)   # 仅用于【路由匹配模块】标题
        self.results: List[AnalysisResult] = []

    def _dispatch(self, module_name: str, ctx=None, opts=None):
        """分派到对应模块。

        **按形参表传参**：只有真的声明了 `ctx`/`opts` 的模块才收得到它们
        （`scanner`/`ad` 收两个，`dns` 收 `ctx` 复用单次解析，其余仍是
        `analyze(filepath)` / `analyze(filepath, max_depth=…)`）。

        ⚠️ 曾经无条件传 `ctx=`：`browser`/`config`/`db`/`email`/`logs`/`memory`/
        `archives` 七个模块全都 `TypeError`，而 `run_filetype()` 的 `except: pass`
        把它吞了——表现是这些格式的 `【模块名】` 块**永远为空**，且没有任何报错。
        `tests/test_smoke.py::check_router_dispatch()` 守着这条。
        """
        import importlib
        import inspect

        mod = importlib.import_module(f"ctfsweep.core.{module_name}")
        fn = getattr(mod, "analyze", None) or getattr(mod, "scan", None)
        if fn is None:
            raise ValueError(f"模块 {module_name} 缺少 analyze/scan 函数")

        params = inspect.signature(fn).parameters
        kwargs = {}
        if "ctx" in params:
            kwargs["ctx"] = ctx
        if "opts" in params:
            kwargs["opts"] = opts
        return fn(self.filepath, **kwargs)

    def run_filetype(self, ctx=None):
        """阶段一：跑所有文件类型模块（stream/sub 角色跳过）。"""
        for mod_name in self.modules:
            if _MODULE_ROLE.get(mod_name, "filetype") != "filetype":
                continue
            try:
                result = self._dispatch(mod_name, ctx=ctx)
                if result:
                    self.results.append(result)
            except Exception:
                # 模块执行失败不中断（历史行为：路由的失败是静默的）
                pass

    def run_stream(self, ctx, opts) -> List[Finding]:
        """阶段二：流扫描，返回 `Finding` 列表。

        `scanner` 内部的候选仍走 5 元组 ABI（`blobscan`/`decode`/`extract`/`http`/
        `session` 的局部约定），转换只发生在这里。需要元组的消费方
        （`report()`、`judge.predict_finding`）自己调 `to_tuple()`。
        异常向上抛，由 CLI 打印并跳过该文件。
        """
        import importlib

        mod = importlib.import_module(f"ctfsweep.core.{_STREAM_MODULE}")
        result = mod.analyze(self.filepath, ctx=ctx, opts=opts)
        if not result:
            return []
        self.results.append(result)
        return list(result.findings)

    def get_all_findings(self) -> List[Finding]:
        """获取所有发现项。"""
        findings = []
        for result in self.results:
            findings.extend(result.findings)
        return findings

    def print_filetype_report(self):
        """打印文件类型模块报告（`【<模块名>】` 块）。"""
        for result in self.results:
            if result.findings:
                print(f"\n【{result.module}】")
                for f in sorted(result.findings, key=lambda x: x.confidence, reverse=True):
                    # 分档口径走 utils.level_of（BAND_HIGH 0.85 / BAND_MID 0.55），
                    # 与分带报告、元判断核一致——这里曾是第三份各自为政的阈值
                    conf_label = level_of(f.confidence)
                    print(f"  [{conf_label} {f.confidence:.2f}] {f.kind}")
                    print(f"    证据: {f.evidence[:200]}")
                    if f.suggestion:
                        print(f"    建议: {f.suggestion}")
