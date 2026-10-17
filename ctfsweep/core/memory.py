# -*- coding: utf-8 -*-
"""内存转储分析模块（Volatility / raw memory）。

支持格式：
- Volatility2/3 输出文件（pslist、netscan、cmdline、dlllist、consoles、hivelist）
- 原始内存转储（.mem / .raw）

分析链路：
1. 类型匹配 → 检测 Volatility 输出 / 原始内存
2. 解析对应格式 → 提取进程/连接/命令行/控制台/注册表
3. 关键词扫描 → flag/密钥/可疑进程/外连 IP
4. 置信度评估 → 高(明文flag/硬编码密钥) / 中(可疑进程/外连) / 低(注释/噪音)
"""

import os
import re
from .router import Finding, AnalysisResult

# ---------------------------------------------------------------------------
# 可疑进程白名单（常见 CTF / 恶意软件工具）
# ---------------------------------------------------------------------------

SUSPICIOUS_PROCESSES = {
    "mimikatz.exe": "凭据窃取工具",
    "procdump.exe": "内存转储工具",
    "cs64.exe": "Cobalt Strike Beacon",
    "c2.exe": "C2 客户端",
    "beacon.exe": "Cobalt Strike",
    "lazagne.exe": "凭据提取工具",
    "secretsdump.exe": "凭据提取",
    "pwdump.exe": "SAM 密码dump",
    "hashdump.exe": "哈希dump",
    "keyscan.exe": "键盘记录",
    "screenshot.exe": "截图工具",
    "netcat.exe": "Netcat 后门",
    "nc.exe": "Netcat",
    "powershell.exe": "PowerShell（可能用于无文件攻击）",
    "cmd.exe": "命令提示符",
    "certutil.exe": "证书工具（可能用于编码/下载）",
    "bitsadmin.exe": "BITS 管理员（可能用于下载）",
    "reg.exe": "注册表编辑",
    "wbadmin.exe": "Windows 备份（可能用于数据外传）",
    "wmic.exe": "WMI 远程执行",
    "msbuild.exe": "MSBuild（可能用于 AMSI 绕过）",
    "rundll32.exe": "DLL 加载（可能用于无文件执行）",
    "regsvr32.exe": "注册服务器（可能用于 DLL 注入）",
    "cscript.exe": "脚本宿主",
    "wscript.exe": "脚本宿主",
    "certmgr.exe": "证书管理器",
    "schtasks.exe": "任务计划（持久化）",
    "sc.exe": "服务控制",
    "net.exe": "网络命令（可能用于横向移动）",
    "psexec.exe": "PsExec（远程执行）",
    "winrm.exe": "Windows Remote Management",
    "ftp.exe": "FTP 客户端（数据外传）",
    "curl.exe": "cURL（数据外传）",
    "wget.exe": "Wget（数据外传）",
}

# ---------------------------------------------------------------------------
# 分析函数
# ---------------------------------------------------------------------------

def analyze(filepath: str) -> AnalysisResult:
    """分析内存转储文件。

    支持：
    - Volatility 输出文件（pslist、netscan、cmdline、dlllist、consoles）
    - 原始内存转储（.mem / .raw）
    """
    result = AnalysisResult("memory")

    # 检测文件类型
    with open(filepath, "rb") as f:
        header = f.read(4096)

    text = header.decode("utf-8", errors="replace")

    # 判断是否为 Volatility 输出
    is_volatility = "volatility" in text.lower() or "pslist" in text.lower()

    if is_volatility:
        # Volatility 输出解析
        _analyze_volatility(filepath, result)
    else:
        # 原始内存转储（简单关键词扫描）
        _analyze_raw_memory(filepath, result)

    return result


def _analyze_volatility(filepath: str, result: AnalysisResult):
    """解析 Volatility 输出。"""
    with open(filepath, "r", errors="replace") as f:
        content = f.read()

    lines = content.split("\n")

    # 1. pslist 解析（进程列表）
    _parse_pslist(lines, result)

    # 2. netscan 解析（网络连接）
    _parse_netscan(lines, result)

    # 3. cmdline 解析（命令行参数）
    _parse_cmdline(lines, result)

    # 4. consoles 解析（控制台输出）
    _parse_consoles(lines, result)

    # 5. dlllist 解析（加载的 DLL）
    _parse_dlllist(lines, result)

    # 6. 通用关键词扫描
    _keyword_scan(content, result)


def _parse_pslist(lines: list, result: AnalysisResult):
    """解析 pslist 输出。"""
    in_pslist = False
    for line in lines:
        if "pslist" in line.lower() or "Name" in line and "PID" in line:
            in_pslist = True
            continue
        if in_pslist and line.strip():
            # 简单 CSV 格式解析
            parts = line.split()
            if len(parts) >= 2:
                proc_name = parts[0].lower()
                for suspicious, desc in SUSPICIOUS_PROCESSES.items():
                    if suspicious in proc_name:
                        result.findings.append(
                            Finding(
                                kind=f"可疑进程: {proc_name}",
                                confidence=0.85,
                                evidence=f"进程名: {proc_name}, 描述: {desc}",
                                suggestion=f"检查该进程是否正常，是否为恶意软件工具",
                                module="memory",
                            )
                        )
                        break


def _parse_netscan(lines: list, result: AnalysisResult):
    """解析 netscan 输出。"""
    in_netscan = False
    for line in lines:
        if "netscan" in line.lower() or "Address" in line and "Port" in line:
            in_netscan = True
            continue
        if in_netscan and line.strip():
            # 简单解析
            if "ESTABLISHED" in line or "CLOSE_WAIT" in line:
                # 提取 IP 和端口
                parts = line.split()
                for part in parts:
                    if "." in part and part.replace(".", "").isdigit():
                        result.findings.append(
                            Finding(
                                kind=f"网络连接: {part}",
                                confidence=0.60,
                                evidence=f"连接状态: {'ESTABLISHED' if 'ESTABLISHED' in line else 'CLOSE_WAIT'}, 目标: {part}",
                                suggestion="检查该连接是否为可疑通信",
                                module="memory",
                            )
                        )


def _parse_cmdline(lines: list, result: AnalysisResult):
    """解析 cmdline 输出。"""
    in_cmdline = False
    for line in lines:
        if "cmdline" in line.lower() or "Command" in line and "PID" in line:
            in_cmdline = True
            continue
        if in_cmdline and line.strip():
            # 检查命令行参数中的密钥
            for keyword in ["password=", "/pass=", "/key=", "secret=", "token="]:
                if keyword in line.lower():
                    result.findings.append(
                        Finding(
                            kind=f"命令行密钥: {keyword}",
                            confidence=0.90,
                            evidence=f"命令行参数包含: {keyword}",
                            suggestion="提取该密钥，可能用于认证或加密",
                            module="memory",
                        )
                    )
                    break


def _parse_consoles(lines: list, result: AnalysisResult):
    """解析 consoles 输出。"""
    in_consoles = False
    for line in lines:
        if "consoles" in line.lower() or "Console" in line:
            in_consoles = True
            continue
        if in_consoles and line.strip():
            # 检查控制台输出中的 flag
            if "flag{" in line.lower():
                result.findings.append(
                    Finding(
                        kind="控制台 flag",
                        confidence=0.97,
                        evidence=f"控制台输出: {line[:200]}",
                        suggestion="提取 flag",
                        module="memory",
                    )
                )


def _parse_dlllist(lines: list, result: AnalysisResult):
    """解析 dlllist 输出。"""
    in_dlllist = False
    for line in lines:
        if "dlllist" in line.lower() or "Image" in line and "Path" in line:
            in_dlllist = True
            continue
        if in_dlllist and line.strip():
            # 检查可疑 DLL
            for dll in ["mimikatz.dll", "injection.dll", "hook.dll"]:
                if dll in line.lower():
                    result.findings.append(
                        Finding(
                            kind=f"可疑 DLL: {dll}",
                            confidence=0.85,
                            evidence=f"DLL 路径: {line[:200]}",
                            suggestion=f"检查该 DLL 是否为恶意软件组件",
                            module="memory",
                        )
                    )
                    break


def _analyze_raw_memory(filepath: str, result: AnalysisResult):
    """分析原始内存转储。"""
    with open(filepath, "rb") as f:
        content = f.read()

    # 简单关键词扫描
    for keyword in [b"flag{", b"password", b"secret", b"token"]:
        if keyword in content:
            result.findings.append(
                Finding(
                    kind=f"关键词: {keyword.decode()}",
                    confidence=0.60,
                    evidence=f"在原始内存中找到: {keyword.decode()}",
                    suggestion="进一步分析该关键词上下文",
                    module="memory",
                )
            )


def _keyword_scan(content: str, result: AnalysisResult):
    """通用关键词扫描。"""
    for keyword in ["flag{", "suctf", "ctf", "password", "secret", "token"]:
        if keyword in content.lower():
            result.findings.append(
                Finding(
                    kind=f"关键词: {keyword}",
                    confidence=0.55,
                    evidence=f"在内容中找到: {keyword}",
                    suggestion=f"检查上下文，确认是否为有效证据",
                    module="memory",
                )
            )
