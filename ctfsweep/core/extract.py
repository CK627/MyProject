# -*- coding: utf-8 -*-
"""文件雕刻/提取：签名识别、候选口令池、压缩包处理（弱口令/假加密绕过/嵌套递归）"""
import hashlib
import io
import os
import re
import struct
import zipfile
import zlib

from .blobscan import add, scan_blob
from .capture import l4_parse, load_packets
from .decode import flagify
from .utils import printable_ratio


# ---------------------------------------------------------------- 文件雕刻
def carve_files(blob, min_size=80):
    """按文件签名从字节流中雕刻文件，返回 [(扩展名, 偏移, 数据)]（已按重叠裁剪）"""
    hits = []
    for m in re.finditer(rb'PK\x03\x04', blob):                  # ZIP（含 docx/xlsx）
        st = m.start()
        eocd = blob.rfind(b'PK\x05\x06', st)
        seg = blob[st:]
        if eocd >= 0 and eocd + 22 <= len(blob):
            clen = struct.unpack('<H', blob[eocd + 20:eocd + 22])[0]
            end = eocd + 22 + clen
            if end <= len(blob):
                seg = blob[st:end]
        hits.append(('.zip', st, seg))
    for m in re.finditer(rb'\x89PNG\r\n\x1a\n', blob):           # PNG
        st = m.start()
        end = blob.find(b'IEND\xaeB`\x82', st)
        if end >= 0:
            hits.append(('.png', st, blob[st:end + 8]))
    for m in re.finditer(rb'\xff\xd8\xff', blob):                # JPEG
        st = m.start()
        nxt = blob.find(b'\xff\xd8\xff', st + 4)
        limit = nxt if nxt > 0 else min(len(blob), st + 20 * 1024 * 1024)
        e = blob[st:limit].rfind(b'\xff\xd9')
        if e >= 0:
            hits.append(('.jpg', st, blob[st:st + e + 2]))
    for m in re.finditer(rb'GIF8[79]a', blob):                   # GIF
        st = m.start()
        end = blob.find(b'\x00\x3b', st)
        hits.append(('.gif', st, blob[st:end + 2] if end > 0 else blob[st:]))
    for m in re.finditer(rb'%PDF', blob):                        # PDF
        st = m.start()
        end = blob.find(b'%%EOF', st)
        hits.append(('.pdf', st, blob[st:end + 5] if end > 0 else blob[st:]))
    for m in re.finditer(rb'\x1f\x8b\x08', blob):                # GZIP
        st = m.start()
        try:
            d = zlib.decompressobj(31)
            window = blob[st:st + 64 * 1024 * 1024]
            d.decompress(window)
            used = len(window) - len(d.unused_data)
            if used > 20:
                hits.append(('.gz', st, blob[st:st + used]))
        except Exception:
            pass
    for m in re.finditer(rb'Rar!\x1a\x07.', blob):               # RAR
        hits.append(('.rar', m.start(), blob[m.start():]))
    for m in re.finditer(rb'7z\xbc\xaf\x27\x1c', blob):          # 7Z
        hits.append(('.7z', m.start(), blob[m.start():]))
    hits.sort(key=lambda h: (h[1], -len(h[2])))
    out, last_end = [], -1
    for ext, st, seg in hits:
        if st < last_end or len(seg) < min_size:
            continue
        out.append((ext, st, seg))
        last_end = st + len(seg)
    return out


# ---------- 候选口令池（跨文件累积：显式口令字段 > URL/路径词 > 通用 token） ----------
COMMON_ZIP_PWDS = ['123456', 'password', 'flag', 'ctf', 'admin', 'root', '12345678', '111111',
                   '123123', 'abc123', 'qwerty', 'letmein', 'test', '123456789', '000000',
                   '666666', '888888', 'admin123', 'password123', '1234', '12345', '1']

PWD_POOL, PWD_SEEN = [], set()
PWD_FIELD_RE = re.compile(rb'(?i)(?:pass(?:wd|word)?|pwd|key|secret|token|auth)[=:\s]{0,3}["\']?([^\s&;,"\'<>\r\n]{3,32})')
TOKEN_RE = re.compile(rb'[A-Za-z0-9_@\-\.]{3,26}')


def _pk(v):
    v = v.strip()
    if 3 <= len(v) <= 32 and v not in PWD_SEEN:
        PWD_SEEN.add(v)
        PWD_POOL.append(v)


def collect_pwds_from_blob(blob):
    """从流量字节块中采集候选口令：口令字段值、URL/路径片段、通用 token"""
    window = blob[:2 * 1024 * 1024]
    for m in PWD_FIELD_RE.finditer(window):                      # 显式口令字段
        _pk(m.group(1).decode('latin-1', 'replace'))
    try:
        text = window.decode('latin-1')
    except Exception:
        return
    for seg in re.split(r'[^A-Za-z0-9_@\-\.]+', text):           # URL/路径词（含 URL 解码残留）
        if 3 <= len(seg) <= 26 and sum(ch.isalpha() for ch in seg) >= 2:
            _pk(seg)
    cnt = 0
    for m in TOKEN_RE.finditer(window):                          # 通用 token（限量）
        tok = m.group(0).decode('latin-1', 'replace')
        if any(ch.isalpha() for ch in tok):
            _pk(tok)
        cnt += 1
        if cnt > 8000:
            break


def precollect_pwds(data):
    """预扫一个抓包文件，把候选口令收集进全局池（用于跨文件共享）"""
    got = load_packets(data)
    if not got:
        return
    _fmt, pkts = got
    for _num, lt, pkt, _ts in pkts:
        r = l4_parse(lt, pkt)
        if r and r[5]:
            try:
                collect_pwds_from_blob(r[5])
            except Exception:
                pass


# ---------------------------------------------------------------- 压缩包处理
def try_fake_decrypt(zip_bytes, info):
    """绕过'假加密'：中心目录标了加密位、但本地头/实际数据未加密时，直接解析本地头解压数据区。
       返回解出的内容（CRC 校验通过）或 None。"""
    pos = 0
    while True:
        i = zip_bytes.find(b'PK\x03\x04', pos)
        if i < 0:
            return None
        try:
            (_sig, _ver, l_flags, method, _mt, _md, _crc, _csize, _usize,
             fnl, exl) = struct.unpack('<IHHHHHIIIHH', zip_bytes[i:i + 30])
        except struct.error:
            return None
        name = zip_bytes[i + 30:i + 30 + fnl]
        if name in (info.filename.encode('utf-8', 'replace'), info.filename.encode('cp437', 'replace')):
            if l_flags & 0x1:                     # 本地头也标加密 → 真加密，交给口令尝试
                return None
            data_off = i + 30 + fnl + exl
            if method == 8:                       # 原始 deflate
                try:
                    d = zlib.decompressobj(-15)
                    out = d.decompress(zip_bytes[data_off:data_off + 64 * 1024 * 1024])
                except Exception:
                    return None
                if zlib.crc32(out) & 0xffffffff == info.CRC:
                    return out
                return None
            if method == 0:
                out = zip_bytes[data_off:data_off + info.file_size]
                if len(out) == info.file_size and zlib.crc32(out) & 0xffffffff == info.CRC:
                    return out
            return None
        pos = i + 1


def scan_zip(data, keywords, do_decode, depth, findings, seen, loc, logger, pwds=None):
    """解压 zip：列出条目、扫描每个条目内容（含嵌套 zip，递归；加密条目尝试弱口令）"""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        entries = [i for i in zf.infolist() if not i.is_dir()]
    except Exception:
        scan_blob(data[:2 * 1024 * 1024], keywords, do_decode, depth, findings, seen, loc)
        return
    logger('            [zip] 内含 %d 项：%s' % (len(entries), '; '.join(i.filename for i in entries[:10])))
    for info in entries:
        content = None
        try:
            content = zf.read(info.filename)
        except RuntimeError:
            if not (info.flag_bits & 0x1):
                logger('            [zip] 条目读取失败（未标记加密，结构可能异常）：%s' % info.filename)
                continue
            content = try_fake_decrypt(data, info)
            if content is not None:
                logger('            [zip] 假加密绕过成功（目录头标记加密、实际数据未加密）：%s' % info.filename)
            else:
                groups = [('空口令', ['']), ('常用口令表', COMMON_ZIP_PWDS)]
                if pwds:
                    base = list(pwds)[:30000]
                    mutated = list(base)
                    for p in base:
                        if 4 <= len(p) <= 14 and p.isascii():
                            mutated.append(p.upper())
                            mutated.append(p.capitalize())
                            mutated.append(p + '123')
                            mutated.append(p + '1')
                    groups.append(('用户字典/流量采集(含常见变体)', mutated[:120000]))
                cracked, tried = None, 0
                for gname, lst in groups:
                    for pw in lst:
                        tried += 1
                        try:
                            zf.setpassword(pw.encode('utf-8', 'replace'))
                            content = zf.read(info.filename)
                            cracked = (pw, gname)
                            break
                        except Exception:
                            continue
                    if cracked:
                        break
                if content is None:
                    logger('            [zip] 已确认 ZipCrypto 加密：%s；已尝试 %d 个候选口令（空/常用/字典/流量采集）未命中——可提供更大字典(--pwd-file)' % (info.filename, tried))
                    continue
                logger('            [zip] ✔ 口令命中 \'%s\'（来源：%s）→ 解开 %s' % (cracked[0], cracked[1], info.filename))
        except Exception:
            continue
        if content is None:
            continue
        if len(content) > 20 * 1024 * 1024:
            content = content[:20 * 1024 * 1024]
        if 0 < len(content) <= 4096 and printable_ratio(content) > 0.85:
            prev = ' '.join(content.decode('utf-8', 'replace').split())[:240]
            if prev:
                logger('            [zip] 文本预览(%s)：%s' % (info.filename, prev))
            sug = flagify(content)
            if sug:
                logger('            [zip] 加壳建议(%s)：%s' % (info.filename, sug))
                add((0.75, '加壳候选', b'', sug.encode('utf-8', 'replace'), 'zip内容:%s' % info.filename), findings, seen)
        sub_loc = '%s!%s' % (loc, info.filename)
        if content[:4] == b'PK\x03\x04' and depth > 0:
            logger('            [zip] 嵌套 zip：%s' % info.filename)
            scan_zip(content, keywords, do_decode, depth - 1, findings, seen, sub_loc, logger, pwds)
        scan_blob(content, keywords, do_decode, depth, findings, seen, sub_loc)


def extract_scan(ext, data, outdir, stem, idx, src, keywords, do_decode, depth, findings, seen, saved, pwds=None):
    """保存雕刻出的文件并扫描其内容；返回保存路径（重复或失败返回 None）"""
    h = hashlib.sha1(data).hexdigest()[:12]
    if h in saved:
        return None
    saved.add(h)
    path = os.path.join(outdir, '%s_%03d%s' % (stem, idx, ext))
    try:
        with open(path, 'wb') as f:
            f.write(data)
    except Exception as ex:
        print('    [提取] 写入失败: %r' % ex)
        return None
    print('    [提取] %s (%d B)   ← %s' % (os.path.basename(path), len(data), src))
    if ext == '.zip':
        scan_zip(data, keywords, do_decode, depth, findings, seen, 'zip:' + os.path.basename(path), print, pwds)
    elif ext == '.gz':
        try:
            inner = zlib.decompress(data, 31)
            scan_blob(inner[:2 * 1024 * 1024], keywords, do_decode, depth, findings, seen, 'gz:' + os.path.basename(path))
            sug = flagify(inner)
            if sug:
                print('            [gz] 加壳建议：%s' % sug)
                add((0.75, '加壳候选', b'', sug.encode('utf-8', 'replace'), 'gz内容:' + os.path.basename(path)), findings, seen)
        except Exception:
            pass
    else:
        scan_blob(data[:2 * 1024 * 1024], keywords, do_decode, depth, findings, seen, '提取:' + os.path.basename(path))
    return path
