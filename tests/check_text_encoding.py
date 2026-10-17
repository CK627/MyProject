# -*- coding: utf-8 -*-
r"""体检「文本编码契约」（devtool 系列一致）。

## 契约

一切文本 **UTF-8 无 BOM**（Inno Setup 例外，见下），文件头部加一行**编码声明**：

    .sh          # encoding: utf-8
    .py          # -*- coding: utf-8 -*-   （PEP 263）
    .bat         @rem encoding: utf-8
    .ps1         # encoding: ascii-b64      （经 irm|iex 分发）
                 # encoding: utf-8-bom      （从磁盘执行）
    .iss/.in     ; encoding: utf-8

## 为什么声明只能当"契约"，不能当"机制"

各运行环境**没有任何一个共通的 pragma**，这一点必须说清楚，否则会写出看似
统一、实则在某一个平台上静默损坏的东西：

| 环境 | 认声明吗 | 真正决定解码的是 |
|---|---|---|
| Python | ★ 认（PEP 263） | 文件头声明 |
| POSIX shell | 不认，但**字节透明** | 无所谓 |
| cmd.exe | 不认 | 控制台代码页；`.bat` 必须 `chcp 65001` 且在第一处非 ASCII 之前 |
| PowerShell 读磁盘 | 不认 | **BOM**：有 BOM 按 UTF-8，无 BOM 按 ANSI(GBK) |
| PowerShell `irm\|iex` | 不认，且 BOM 会炸第一行 | 管道按 ANSI 解码 → 只能纯 ASCII |
| Inno Setup 6.7.3 | 不认 | 实测默认按 UTF-8 读（有无 BOM 都正确） |

所以声明行是给**检查器和人**看的：它把"这份文件应当是什么字节"写下来，
再由本脚本逐条核对实际字节。声明与事实不符即失败。

## 各格式的硬规则（全部有实测依据）

`.bat`
  1. 无 BOM；2. 全部 CRLF；3. 含中文时 `chcp 65001` 必须在第一处非 ASCII 之前。
  （2026-10 实测：UTF-8 无 BOM + CRLF + chcp 65001，中文 REM/echo/if 块在
  直接调用与 call 两种方式下都正确显示。带 BOM 会报 `'?@echo' 不是内部或外部命令`；
  LF-only 会碎片化解析。）

`.ps1` + `ascii-b64`
  必须**纯 ASCII**。`irm ... | iex` 把正文当字符串交给 Invoke-Expression，
  非 ASCII 会按 ANSI 解码后变成 `ä¸æ` 那类乱码（2026-10 在中文 Windows 上实测）。
  中文以 UTF-8 Base64 内嵌，运行时由 `T()` 解码；本脚本会把每条 Base64
  **反解一遍**，防止手抄错。

`.ps1` + `utf-8-bom`
  必须有 BOM。从磁盘执行时，Windows PowerShell 5.1 无 BOM 会按 ANSI 读，
  中文注释与字符串全部损坏；BOM 是两个版本 PowerShell 都认的唯一信号。

`.iss` / `.iss.in`
  UTF-8；BOM 可有可无（ISCC 6.7.3 实测两种都对）。

`.sh` / `.py`
  `# encoding: utf-8` / `# -*- coding: utf-8 -*-`。对 shell 是文档（字节透明），
  对 Python 3 是冗余（默认 UTF-8），但**统一要求**：一条规则比"看情况"更容易守，
  也让"这个文件是什么编码"在任何编辑器里都是自解释的。

⚠️ 用 Python 判字节而不是 `grep -P '[\x80-\xFF]'`：BSD grep（macOS 自带）
   不支持 `-P` 与 `\xNN`，本地跑不出来；Python 到处都一样。
"""
import base64
import os
import re
import sys

DECL_RE = re.compile(r'^\s*(?:@?rem|#|;)\s*encoding\s*:\s*([A-Za-z0-9._-]+)\s*$',
                     re.IGNORECASE)
PEP263_RE = re.compile(r'^\s*#.*coding[:=]\s*([-\w.]+)')
B64_RE = re.compile(r"T '([A-Za-z0-9+/=]+)'")

BOM = b'\xef\xbb\xbf'

# 每种格式：是否强制声明、允许的取值
FORMATS = {
    '.bat': (True, ('utf-8',)),
    '.ps1': (True, ('ascii-b64', 'utf-8-bom', 'utf-8')),
    '.iss': (True, ('utf-8', 'utf-8-bom')),
    '.sh':  (True, ('utf-8',)),
    '.py':  (True, ('utf-8',)),
}


def _ext(path):
    name = os.path.basename(path)
    if name.endswith('.iss.in'):
        return '.iss'
    return os.path.splitext(name)[1].lower()


def _declared(raw):
    """在前 5 行里找编码声明，返回 (值 or None)。"""
    # 先去掉 BOM：U+FEFF 不是 `\s`，带着它永远匹配不到声明——
    # 这正是"声明明明写了却报缺失"的成因。
    head = raw[len(BOM):] if raw.startswith(BOM) else raw
    head = head[:2048]
    for line in head.splitlines()[:5]:
        try:
            text = line.decode('utf-8', 'replace')
        except Exception:
            continue
        m = PEP263_RE.match(text) or DECL_RE.match(text)
        if m:
            return m.group(1).lower()
    return None


def _valid_utf8(raw):
    try:
        raw.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False


def check(path):
    """返回问题列表（空 = 通过）。"""
    ext = _ext(path)
    if ext not in FORMATS:
        return []
    required, allowed = FORMATS[ext]
    try:
        raw = open(path, 'rb').read()
    except OSError as e:
        return ['读不到: %s' % e]

    bad = []
    has_bom = raw.startswith(BOM)
    body = raw[len(BOM):] if has_bom else raw

    # ---- 声明 ----
    decl = _declared(raw)
    if decl is None:
        if required:
            bad.append('缺编码声明（首部应有 `encoding: <格式>`）')
        # 可选格式：没声明就不管，但下面仍做 UTF-8 合法性检查
    elif decl not in allowed:
        bad.append('声明 `encoding: %s` 不适用于 %s（允许: %s）'
                   % (decl, ext, ', '.join(allowed)))

    # ---- 公共：UTF-8 合法性 ----
    if not _valid_utf8(body):
        bad.append('不是合法 UTF-8')

    # ---- 按格式 ----
    if ext == '.bat':
        if has_bom:
            bad.append('有 UTF-8 BOM（cmd 会把 BOM 当命令的一部分，第一行直接报错）')
        bare_lf = body.replace(b'\r\n', b'').count(b'\n')
        if bare_lf:
            bad.append('含 %d 个裸 LF（必须 CRLF，否则 cmd 会碎片化解析）' % bare_lf)
        first = next((i for i, b in enumerate(body) if b > 0x7f), None)
        if first is not None:
            pos = body.find(b'chcp 65001')
            if pos < 0:
                bad.append('含中文但没有 `chcp 65001`（控制台会按本地代码页渲染成乱码）')
            elif pos > first:
                bad.append('`chcp 65001` 出现在第一处中文之后（要放在它之前才生效）')

    elif ext == '.ps1':
        if decl == 'ascii-b64':
            nonascii = [b for b in body if b > 0x7f]
            if nonascii:
                bad.append('声明为 ascii-b64 却有 %d 个非 ASCII 字节'
                           '（irm|iex 会按 ANSI 解码成乱码）' % len(nonascii))
            if has_bom:
                bad.append('有 BOM（irm|iex 下 BOM 会变成第一行的一部分，直接 CommandNotFound）')
            # 每条内嵌 Base64 必须能还原成合法 UTF-8 —— 手抄错一位在这里就被抓住
            for b64 in B64_RE.findall(body.decode('ascii', 'ignore')):
                try:
                    base64.b64decode(b64).decode('utf-8')
                except Exception:
                    bad.append('Base64 解不出合法 UTF-8: %s' % b64[:40])
        elif decl == 'utf-8-bom':
            if not has_bom:
                bad.append('声明为 utf-8-bom 却没有 BOM'
                           '（Windows PowerShell 5.1 会按 ANSI 读，中文全坏）')
        elif decl == 'utf-8':
            if has_bom:
                bad.append('声明为 utf-8（无 BOM）却带了 BOM')

    elif ext == '.iss':
        # ISCC 两种都认；只要求是合法 UTF-8（上面已查）
        pass

    return bad


def main(argv):
    if argv:
        files = argv
    else:
        files = []
        for dp, dn, fn in os.walk('.'):
            dn[:] = [d for d in dn if d not in ('.git', 'dist', 'build', '__pycache__')]
            for f in fn:
                if _ext(f) in FORMATS:
                    files.append(os.path.join(dp, f))
        files.sort()
    fails = 0
    for f in files:
        if not os.path.isfile(f):
            continue
        problems = check(f)
        if problems:
            fails += 1
            for p in problems:
                print('FAIL %s: %s' % (f, p))
        elif os.environ.get('ENCODING_VERBOSE'):
            print('ok   %s' % f)
    if fails:
        print('\n编码契约失败 %d 个文件' % fails)
    else:
        print('编码契约通过（%d 个文件）' % len([f for f in files if os.path.isfile(f)]))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
