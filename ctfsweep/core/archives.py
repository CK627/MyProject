# -*- coding: utf-8 -*-
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
from .utils import FLAG_RE

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
# 解压产物扫描
# ---------------------------------------------------------------------------
#
# ⚠️ 这里是"解开了却不说里面是什么"的经典死胡同。模块 docstring 一直写着「最终文件扫描」，
# 但 `analyze()` 解压完就 `shutil.rmtree` 掉了——实测 SU_Artifact_Online.zip（密码 password，
# 1 KB）只报一句「ZIP 解压成功（密码: password）」+ 建议「检查解压出的文件内容」，
# 而包内是 3369 字节的**卢恩字母替换密码**文本。对一道陌生题来说，"解开了但不说里面
# 是什么"等于没解：报告既没告诉人题型，也没给出任何下一步。下面是补上的那一半。

_LIST_CAP = 12            # 「压缩包内容」里最多列出多少个成员
_EXCERPT_CAP = 6          # 最多给几个成员出正文摘录
_EXCERPT_MIN = 32         # 小于这个体积的成员不出摘录（容器内部零件多为个位数字节）
_PEEK_CAP = 8192          # 每个成员最多读多少字节
_EXCERPT_LEN = 180        # 摘录长度

# 单一 Unicode 块占比过高时给出的"这是哪种文字"提示。CTF 里密集出现的非拉丁字符
# 几乎总是替换密码或字体加密，认出区块就等于给出解法方向。
_SCRIPT_RANGES = (
    ("卢恩字母（北欧符文，常见替换密码）", 0x16A0, 0x16FF),
    ("欧甘字母（Ogham，常见替换密码）", 0x1680, 0x169F),
    ("哥特字母", 0x10330, 0x1034F),
    ("格拉哥里字母", 0x2C00, 0x2C5F),
    ("腓尼基字母", 0x10900, 0x1091F),
    ("楔形文字", 0x12000, 0x123FF),
    ("盲文点字（Braille）", 0x2800, 0x28FF),
    ("私用区码位（自定义字体 / 字体加密）", 0xE000, 0xF8FF),
    ("全角字符（全角替换 / 宽字符隐写）", 0xFF00, 0xFFEF),
)


def _human_size(n):
    if n < 1024:
        return "%d B" % n
    if n < 1024 * 1024:
        return "%.1f KB" % (n / 1024.0)
    return "%.1f MB" % (n / 1048576.0)


def _text_of(data):
    """解压产物是不是**文本**；是则返回 (解码后的串, None)，否则返回 (None, 类型描述)。

    这里**故意不用** `utils.looks_like_text`：它的码位白名单只放行 ASCII/Latin-1/CJK/
    谚文/全角，卢恩字母这类真脚本会被整串判成"乱码"而丢掉——恰恰是最需要看见的那类题。
    改判「能否严格按 UTF-8 解码且几乎没有控制字符」：二进制/加密体几乎不可能通过，
    而任何真实文字（含冷门脚本）都能通过。
    """
    # ⚠️ bzImage 必须先于 MZ 判定：Linux 内核镜像的开头是引导用的 `MZ` 桩，
    # 会被 `FILE_SIGNATURES` 认成「PE (Windows)」——一道 kernel pwn 题的关键附件
    # 被判成 Windows 可执行文件，方向就带偏了。真正的标志在偏移 0x202 的 `HdrS`。
    if len(data) > 0x206 and data[0x202:0x206] == b"HdrS":
        return None, "Linux 内核镜像（bzImage / x86 boot protocol）"
    for sig, name in FILE_SIGNATURES.items():
        if data.startswith(sig):
            return None, name
    try:
        s = data.decode("utf-8")
    except UnicodeDecodeError:
        return None, "二进制"
    if not s:
        return "", None
    ctrl = sum(1 for ch in s if ord(ch) < 32 and ch not in "\r\n\t")
    if ctrl > len(s) * 0.02:
        return None, "二进制"
    return s, None


def _script_hint(s):
    """文本是否高度集中在某个 Unicode 块；是则返回该块的说明。"""
    letters = [ch for ch in s if not ch.isascii() and not ch.isspace()]
    if len(letters) < 8:
        return None
    for name, lo, hi in _SCRIPT_RANGES:
        hit = sum(1 for ch in letters if lo <= ord(ch) <= hi)
        if hit >= len(letters) * 0.7:
            return name
    return None


def _scan_extracted(tmpdir, result):
    """把解压出来的成员列出来、扫 flag、给文本成员一段摘录。

    ⚠️ **顺序按"层级浅 → 深，同层按名字"**，不是全路径字母序。`.pth`/`.docx` 这类
    本身就是容器的成员，递归解压后会散出一堆内部零件（实测 SU_theif 的
    `model_base.pth` 解出 `model_base/{byteorder, version, .data/serialization_id, data/0, …}`）——
    按全路径排，`model_base/.data/...` 会排到 `README.md` 前面，把摘录名额吃光，
    真正要看的 `README.md`/`app.py` 反而挤不进去。浅层才是"这道题真正交给你的东西"。
    """
    entries = []
    for root, _dirs, files in os.walk(tmpdir):
        for name in files:
            path = os.path.join(root, name)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            rel = os.path.relpath(path, tmpdir)
            entries.append((rel.count(os.sep), rel, size, path))
    if not entries:
        return
    # 递归解压产物不再当"成员"：`model_base.pth` 解出的 `model_base/` 是**容器的内部结构**，
    # 不是这道题交给你的东西。判据是"第 1 层目录名 == 某个第 0 层文件的词干"
    # （`.pth`/`.docx`/`.xlsx` 都是这个形状）。不排掉的话，`byteorder`（6 B）/`version`（2 B）
    # 会把 12 个列表名额和 6 个摘录名额吃光，真正要读的 README/app.py 被挤下去。
    stems = set(os.path.splitext(rel)[0] for depth, rel, _sz, _p in entries if depth == 0)
    entries = [e for e in entries
               if e[0] == 0 or e[1].split(os.sep, 1)[0] not in stems]
    if not entries:
        return
    entries.sort(key=lambda e: (e[0], e[1]))
    listed = "、".join("%s（%s）" % (rel, _human_size(sz))
                       for _d, rel, sz, _p in entries[:_LIST_CAP])
    if len(entries) > _LIST_CAP:
        listed += " 等 %d 个文件" % len(entries)
    result.findings.append(
        Finding(
            kind="压缩包内容",
            confidence=0.75,
            evidence=listed,
            suggestion="先按文件名与下面的摘录判题型（编码 / 替换密码 / 隐写 / 内存镜像）",
            module="archives",
        )
    )
    shown = {"text": 0, "binary": 0}
    # 摘录名额按"层级浅、同层体积大"发放：容器内部零件（`byteorder` 6 B、`version` 2 B）
    # 与真正要读的 `README.md`/`app.py` 同处第 1 层，只有体积能把它们分开。
    for _d, rel, sz, path in sorted(entries, key=lambda e: (e[0], -e[2])):
        if sz < _EXCERPT_MIN:
            continue
        _emit_member(rel, path, result, shown)


def _emit_member(name, path, result, shown):
    """flag 命中一律上报；正文摘录与成员类型各自限量，避免大包刷屏。"""
    try:
        with open(path, "rb") as f:
            data = f.read(_PEEK_CAP)
    except OSError:
        return

    for m in FLAG_RE.finditer(data):
        result.findings.append(
            Finding(
                kind="压缩包中的 flag",
                confidence=0.97,
                evidence="%s: %s" % (name, m.group(0).decode("utf-8", "replace")),
                suggestion="提取 flag",
                module="archives",
            )
        )

    text, binary_kind = _text_of(data)
    if text is None:
        if shown["binary"] >= _EXCERPT_CAP:
            return
        shown["binary"] += 1
        result.findings.append(
            Finding(
                kind="压缩包成员类型",
                confidence=0.55,
                evidence="%s：%s" % (name, binary_kind),
                suggestion="二进制成员用 -x 提取到目录后单独分析",
                module="archives",
            )
        )
        return
    if shown["text"] >= _EXCERPT_CAP or not text.strip():
        return
    shown["text"] += 1
    excerpt = " ".join(text.split())[:_EXCERPT_LEN]
    hint = _script_hint(text)
    if hint:
        excerpt = "【%s】%s" % (hint, excerpt)
    result.findings.append(
        Finding(
            kind="压缩包成员摘录",
            confidence=0.60,
            evidence="%s: %s" % (name, excerpt),
            suggestion="据摘录判断编码 / 加密方式，不要只看文件名",
            module="archives",
        )
    )


# ---------------------------------------------------------------------------
# 分析函数
# ---------------------------------------------------------------------------

def analyze(filepath: str, max_depth: int = 5) -> AnalysisResult:
    """分析多层压缩包。

    支持：
    - ZIP → RAR → 7Z → TAR → GZ 多层解压
    - 常见密码尝试
    - 最终文件扫描（成员清单 + flag + 文本摘录，见 `_scan_extracted`）
    """
    result = AnalysisResult("archives")

    # 创建临时目录
    tmpdir = tempfile.mkdtemp(prefix="ctfsweep_archives_")

    try:
        _extract_archive(filepath, tmpdir, depth=0, max_depth=max_depth, password=None, result=result)
        _scan_extracted(tmpdir, result)
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
                            # 只留成员名：这里是递归解压，`filepath` 是临时目录里的绝对路径，
                            # 打进报告就是 `/var/folders/...` 这种对解题零价值的噪音。
                            evidence=f"文件: {os.path.basename(filepath)}, 密码: {password}, 深度: {depth}",
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
