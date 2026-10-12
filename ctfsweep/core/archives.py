"""多层压缩包分析模块（ZIP → RAR → 7Z → TAR → GZ）。

分析链路：
1. 类型匹配 → 检测压缩包格式
2. 递归解压 → 每层尝试常见密码（password/flag/ctf/空）
3. 最终文件扫描 → 继续分析解压出的文件
4. 置信度评估 → 高(flag/密钥) / 中(可疑文件) / 低(普通文件)
"""

import gzip
import os
import re
import tarfile
import zipfile
import tempfile
from .router import Finding, AnalysisResult

# ---------------------------------------------------------------------------
# 常见密码
# ---------------------------------------------------------------------------

COMMON_PASSWORDS = [
    "",  # 空密码
    "password",
    "flag",
    "ctf",
    "admin",
    "123456",
    "root",
    "user",
    "test",
    "guest",
    "secret",
    "key",
    "download",
    "unzip",
    "extract",
    "password1",
    "changeme",
    "default",
    "letmein",
    "welcome",
    "monkey",
    "master",
    "dragon",
    "login",
    "princess",
    "qwerty",
    "abc123",
    "pass",
    "1234",
    "12345",
    "123456789",
    "12345678",
    "1234567",
    "12345",
    "1234",
    "123",
    "12",
    "1",
]

# 文件类型签名（Magic Numbers）
FILE_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": "PNG",
    b"\xff\xd8\xff": "JPEG",
    b"PK\x03\x04": "ZIP",
    b"PK\x05\x06": "ZIP (central dir)",
    b"RAR\x07\x00": "RAR",
    b"7z\xbc\xaf\x27\x1d": "7-Zip",
    b"\x1f\x8b": "GZIP",
    b"BZh": "BZIP2",
    b"\x50\x4b\x03\x04": "ZIP",
    b"\x42\x5a\x49\x32": "BZIP2",
    b"\x47\x49\x46\x46": "GIF",
    b"\x49\x44\x33": "ID3 (MP3)",
    b"\x25\x50\x44\x46": "PDF",
    b"\x7f\x45\x4c\x46": "ELF",
    b"\x4d\x5a": "PE (Windows)",
    b"\x7f\x45\x4c\x46\x02\x01\x01\x00": "ELF 64-bit",
    b"\x7f\x45\x4c\x46\x01\x01\x01\x00": "ELF 32-bit",
}

# ---------------------------------------------------------------------------
# 分析函数
# ---------------------------------------------------------------------------

def analyze(filepath: str, max_depth: int = 5) -> AnalysisResult:
    """分析多层压缩包。

    支持：
    - ZIP → RAR → 7Z → TAR → GZ 多层解压
    - 常见密码尝试
    - 最终文件扫描
    """
    result = AnalysisResult("archives")

    # 创建临时目录
    tmpdir = tempfile.mkdtemp(prefix="ctfsweep_archives_")

    try:
        _extract_archive(filepath, tmpdir, depth=0, max_depth=max_depth, password=None, result=result)
    except Exception as e:
        result.findings.append(
            Finding(
                kind="压缩包解析失败",
                confidence=0.0,
                evidence=str(e),
                module="archives",
            )
        )
    finally:
        # 清理临时目录
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    return result


def _extract_archive(filepath: str, dest_dir: str, depth: int, max_depth: int, password: str, result: AnalysisResult):
    """递归解压压缩包。"""
    if depth > max_depth:
        result.findings.append(
            Finding(
                kind="超过最大解压深度",
                confidence=0.0,
                evidence=f"最大深度: {max_depth}, 当前深度: {depth}",
                suggestion="增加 max_depth 参数以继续解压",
                module="archives",
            )
        )
        return

    with open(filepath, "rb") as f:
        header = f.read(16)

    # 检测文件格式
    if header[:4] == b"PK\x03\x04" or header[:4] == b"PK\x01\x02" or header[:4] == b"PK\x05\x06":
        _extract_zip(filepath, dest_dir, password, result, depth)
    elif header[:4] == b"RAR\x07\x00" or header[:6] == b"RAR\x1a\x07\x00":
        _extract_rar(filepath, dest_dir, password, result, depth)
    elif header[:6] == b"7z\xbc\xaf\x27\x1d":
        _extract_7z(filepath, dest_dir, password, result, depth)
    elif header[:2] == b"\x1f\x8b":
        _extract_gzip(filepath, dest_dir, result, depth)
    elif header[:2] == b"BZ":
        _extract_bzip2(filepath, dest_dir, result, depth)
    elif header[:2] == b"\x50\x4b":
        _extract_zip(filepath, dest_dir, password, result, depth)
    else:
        # 尝试 TAR
        try:
            with tarfile.open(filepath, "r:*") as tar:
                tar.extractall(dest_dir)
                result.findings.append(
                    Finding(
                        kind=f"TAR 归档（深度 {depth}）",
                        confidence=0.70,
                        evidence=f"文件: {filepath}, 深度: {depth}",
                        module="archives",
                    )
                )
        except Exception:
            pass


def _extract_zip(filepath: str, dest_dir: str, password: str, result: AnalysisResult, depth: int):
    """解压 ZIP 文件。"""
    try:
        with zipfile.ZipFile(filepath, "r") as zf:
            # 尝试密码
            if password:
                try:
                    zf.extractall(dest_dir, pwd=password.encode())
                    result.findings.append(
                        Finding(
                            kind=f"ZIP 解压成功（密码: {password}）",
                            confidence=0.90,
                            evidence=f"文件: {filepath}, 密码: {password}, 深度: {depth}",
                            module="archives",
                        )
                    )
                except RuntimeError:
                    # 密码错误，尝试其他密码
                    _try_passwords(zf, dest_dir, result, depth, password)
            else:
                # 尝试常见密码
                _try_passwords(zf, dest_dir, result, depth)
    except Exception as e:
        result.findings.append(
            Finding(
                kind="ZIP 解压失败",
                confidence=0.0,
                evidence=str(e),
                module="archives",
            )
        )


def _try_passwords(zf: zipfile.ZipFile, dest_dir: str, result: AnalysisResult, depth: int, tried_password: str = ""):
    """尝试常见密码解压 ZIP。"""
    for password in COMMON_PASSWORDS:
        if password == tried_password:
            continue

        try:
            zf.extractall(dest_dir, pwd=password.encode())
            result.findings.append(
                Finding(
                    kind=f"ZIP 解压成功（密码: {password}）",
                    confidence=0.90,
                    evidence=f"密码: {password}, 深度: {depth}",
                    suggestion="检查解压出的文件内容",
                    module="archives",
                )
            )

            # 递归解压新文件
            for root, dirs, files in os.walk(dest_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    with open(file_path, "rb") as f:
                        header = f.read(16)
                    if header[:4] == b"PK\x03\x04" or header[:4] == b"PK\x01\x02":
                        _extract_zip(file_path, root, password, result, depth + 1)

            return
        except RuntimeError:
            continue

    # 无密码解压
    try:
        zf.extractall(dest_dir)
        result.findings.append(
            Finding(
                kind=f"ZIP 无密码解压成功（深度 {depth}）",
                confidence=0.70,
                evidence=f"深度: {depth}",
                module="archives",
            )
        )

        # 递归解压新文件
        for root, dirs, files in os.walk(dest_dir):
            for file in files:
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as f:
                    header = f.read(16)
                if header[:4] == b"PK\x03\x04" or header[:4] == b"PK\x01\x02":
                    _extract_zip(file_path, root, "", result, depth + 1)
    except Exception:
        pass


def _extract_rar(filepath: str, dest_dir: str, password: str, result: AnalysisResult, depth: int):
    """解压 RAR 文件（需要 unrar 命令）。"""
    import subprocess

    cmd = ["unrar", "x", "-o+"]
    if password:
        cmd.extend(["-p" + password])
    cmd.extend([filepath, dest_dir + "/"])

    try:
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0:
            result.findings.append(
                Finding(
                    kind=f"RAR 解压成功（深度 {depth}）",
                    confidence=0.90,
                    evidence=f"文件: {filepath}, 深度: {depth}",
                    module="archives",
                )
            )
        else:
            # 密码错误，尝试其他密码
            if not password:
                _try_passwords_rar(filepath, dest_dir, result, depth)
    except FileNotFoundError:
        result.findings.append(
            Finding(
                kind="unrar 命令不可用",
                confidence=0.0,
                evidence="需要安装 unrar 命令",
                module="archives",
            )
        )


def _try_passwords_rar(filepath: str, dest_dir: str, result: AnalysisResult, depth: int):
    """尝试常见密码解压 RAR。"""
    for password in COMMON_PASSWORDS:
        if not password:
            continue

        import subprocess

        cmd = ["unrar", "x", "-o+", f"-p{password}", filepath, dest_dir + "/"]
        try:
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode == 0:
                result.findings.append(
                    Finding(
                        kind=f"RAR 解压成功（密码: {password}）",
                        confidence=0.90,
                        evidence=f"密码: {password}, 深度: {depth}",
                        module="archives",
                    )
                )
                return
        except Exception:
            continue


def _extract_7z(filepath: str, dest_dir: str, password: str, result: AnalysisResult, depth: int):
    """解压 7-Zip 文件（需要 7z 命令）。"""
    import subprocess

    cmd = ["7z", "x", "-o" + dest_dir]
    if password:
        cmd.extend(["-p" + password])
    cmd.append(filepath)

    try:
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0:
            result.findings.append(
                Finding(
                    kind=f"7-Zip 解压成功（深度 {depth}）",
                    confidence=0.90,
                    evidence=f"文件: {filepath}, 深度: {depth}",
                    module="archives",
                )
            )
        else:
            # 密码错误，尝试其他密码
            if not password:
                _try_passwords_7z(filepath, dest_dir, result, depth)
    except FileNotFoundError:
        result.findings.append(
            Finding(
                kind="7z 命令不可用",
                confidence=0.0,
                evidence="需要安装 7z 命令",
                module="archives",
            )
        )


def _try_passwords_7z(filepath: str, dest_dir: str, result: AnalysisResult, depth: int):
    """尝试常见密码解压 7-Zip。"""
    for password in COMMON_PASSWORDS:
        if not password:
            continue

        import subprocess

        cmd = ["7z", "x", f"-o{dest_dir}", f"-p{password}", filepath]
        try:
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode == 0:
                result.findings.append(
                    Finding(
                        kind=f"7-Zip 解压成功（密码: {password}）",
                        confidence=0.90,
                        evidence=f"密码: {password}, 深度: {depth}",
                        module="archives",
                    )
                )
                return
        except Exception:
            continue


def _extract_gzip(filepath: str, dest_dir: str, result: AnalysisResult, depth: int):
    """解压 GZIP 文件。"""
    try:
        with gzip.open(filepath, "rb") as f:
            content = f.read()

        # 保存解压后的文件
        output_path = os.path.join(dest_dir, os.path.basename(filepath) + ".decompressed")
        with open(output_path, "wb") as f:
            f.write(content)

        result.findings.append(
            Finding(
                kind=f"GZIP 解压成功（深度 {depth}）",
                confidence=0.70,
                evidence=f"文件: {filepath}, 深度: {depth}",
                module="archives",
            )
        )

        # 检查内容
        if b"flag{" in content:
            result.findings.append(
                Finding(
                    kind="GZIP 中的 flag",
                    confidence=0.97,
                    evidence=f"文件: {filepath}",
                    suggestion="提取 flag",
                    module="archives",
                )
            )
    except Exception as e:
        result.findings.append(
            Finding(
                kind="GZIP 解压失败",
                confidence=0.0,
                evidence=str(e),
                module="archives",
            )
        )


def _extract_bzip2(filepath: str, dest_dir: str, result: AnalysisResult, depth: int):
    """解压 BZIP2 文件。"""
    import bz2

    try:
        with open(filepath, "rb") as f:
            content = bz2.decompress(f.read())

        # 保存解压后的文件
        output_path = os.path.join(dest_dir, os.path.basename(filepath) + ".decompressed")
        with open(output_path, "wb") as f:
            f.write(content)

        result.findings.append(
            Finding(
                kind=f"BZIP2 解压成功（深度 {depth}）",
                confidence=0.70,
                evidence=f"文件: {filepath}, 深度: {depth}",
                module="archives",
            )
        )
    except Exception as e:
        result.findings.append(
            Finding(
                kind="BZIP2 解压失败",
                confidence=0.0,
                evidence=str(e),
                module="archives",
            )
        )
