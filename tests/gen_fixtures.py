#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成冒烟测试用例（纯标准库、确定性输出）

用法:
    python3 tests/gen_fixtures.py <输出目录>

产物:
    t1.pcap     明文/hex/DNS-base64 三种 flag + JWT + 环境变量回显
    t2.pcapng   pcapng 封装（EPB）的明文 flag
    t3.evtx     evtx 风格 UTF-16LE 字节（明文 flag + 两个花括号片段 + 五类噪音样本）
    t4.pcap     HTTP 流中内嵌 zip（内含 flag 文本），供 --extract 测试
    t5-ad.pcap  AD 域流量：Kerberos(88) RC4 票据 + SMB NTLM 认证 + LDAP 明文绑定
"""
import base64
import io
import os
import struct
import sys
import zipfile


def _ip(s):
    return bytes(int(x) for x in s.split('.'))


def eth_ipv4(payload, proto, src='10.9.9.10', dst='10.9.9.20'):
    eth = b'\x02\x00\x00\x00\x00\x01' + b'\x02\x00\x00\x00\x00\x02' + struct.pack('>H', 0x0800)
    total = 20 + len(payload)
    ip = (struct.pack('>BBHHHBBH', 0x45, 0, total, 0x1337, 0x4000, 64, proto, 0)
          + _ip(src) + _ip(dst))
    return eth + ip + payload


def tcp(sport, dport, seq, payload):
    return struct.pack('>HHIIBBHHH', sport, dport, seq, 1, 0x50, 0x18, 0x4000, 0, 0) + payload


def udp(sport, dport, payload):
    return struct.pack('>HHHH', sport, dport, 8 + len(payload), 0) + payload


def dns_query(name, qid=0x2026):
    labels = b''.join(bytes([len(l)]) + l for l in name.split(b'.'))
    return (struct.pack('>HHHHHH', qid, 0x0100, 1, 0, 0, 0)
            + labels + b'\x00' + struct.pack('>HH', 1, 1))


def pcap_file(frames, linktype=1):
    out = struct.pack('<IHHiIII', 0xa1b2c3d4, 2, 4, 0, 0, 65535, linktype)
    for i, frame in enumerate(frames):
        out += struct.pack('<IIII', 1750000000 + i, i * 1000, len(frame), len(frame)) + frame
    return out


def _pcapng_block(btype, body):
    pad = (4 - len(body) % 4) % 4
    body += b'\x00' * pad
    blen = 12 + len(body)
    return struct.pack('<II', btype, blen) + body + struct.pack('<I', blen)


def pcapng_file(frames, linktype=1):
    out = _pcapng_block(0x0A0D0D0A, struct.pack('<IHHq', 0x1A2B3C4D, 1, 0, -1))
    out += _pcapng_block(1, struct.pack('<HHI', linktype, 0, 65535))
    for i, frame in enumerate(frames):
        us = 1750000000000000 + i * 1000
        body = struct.pack('<IIIII', 0, us >> 32, us & 0xffffffff, len(frame), len(frame)) + frame
        out += _pcapng_block(6, body)
    return out


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=')


def build_t1():
    hex_flag = b'flag{h3x-smoke-ok}'.hex().encode()
    jwt = b'.'.join([
        b64url(b'{"alg":"HS256","typ":"JWT"}'),
        b64url(b'{"username":"admin","exp":1799999999}'),
        b'smoke-signature',
    ])
    req = (b'GET /admin/panel HTTP/1.1\r\nHost: smoke.local\r\n'
           b'Authorization: Bearer ' + jwt + b'\r\n\r\n'
           b'plain: flag{plain-smoke-ok}\nhex: ' + hex_flag + b'\n'
           b'PWD=/AstrBot\nWEBUI_SK=Advanced_System_for_Text\n')
    resp = b'HTTP/1.1 200 OK\r\nContent-Length: 9\r\n\r\n/AstrBot\n'
    dns_name = base64.b64encode(b'flag{dns-smoke-ok}').rstrip(b'=') + b'.exfil.smoke'
    frames = [
        eth_ipv4(tcp(40001, 8080, 1, req), 6),
        eth_ipv4(tcp(8080, 40001, 1, resp), 6),
        eth_ipv4(udp(53000, 53, dns_query(dns_name)), 17),
    ]
    return pcap_file(frames)


def build_t2():
    frames = [eth_ipv4(tcp(41001, 80, 1, b'GET / HTTP/1.1\r\n\r\nflag{pcapng-smoke-ok}\n'), 6)]
    return pcapng_file(frames)


def build_t3():
    parts = [b'\x00' * 32]
    parts.append('cmd.exe /c echo flag{evtx-smoke-ok}'.encode('utf-16-le'))
    parts.append(b'\x00' * 16)
    parts.append('reg add HKLM\\Software\\Run /v flag1 /d "cmd.exe /c echo {krjl424"'.encode('utf-16-le'))
    parts.append(b'\x00' * 16)
    parts.append('sc description flag3 "Service Key: zlmqu458xktq}"'.encode('utf-16-le'))
    parts.append(b'\x00' * 16)
    # ---- 噪音样本（严格模式闸门应全部剔除，不得出现在扫描结果中）----
    # 1) 文件名后缀拼贴：.dll 后邻接二进制字节（prev='.' 闸门）
    parts.append(b'C:\\Windows\\system32\\setupetw.dll55e3}JK\x00\x00')
    # 2) 注册表 GUID 路径（纯 hex 闸门）
    parts.append('[HKEY_CLASSES_ROOT\\CLSID\\{3050f3B3-98b5-11cf-bb82}]'.encode('utf-16-le'))
    parts.append(b'\x00' * 16)
    # 3) 密集乱码 token 区（无空白闸门）
    parts.append(b"2h@P~Iz0xl2=C6RhJ+g&[S?+Eh8_Q6y['ehZ.]w={v8ozb{5@b59J4l9r%c,oz@u=MVcA6oS3]UIG2_e9J$+xyQ7w&K@1")
    parts.append(b'\x00' * 16)
    # 4) 词内误报样本（关键字后紧跟字母：flag→Flags）
    parts.append('"FolderValueFlags"=dword:00000001'.encode('utf-16-le'))
    parts.append(b'\x00' * 16)
    # 5) 标识符内部命中样本（下划线/字母包裹：create_pdo_flag、msctf）
    parts.append('"create_pdo_flag"=hex:34,00 "amd64_windows-msctf_x"'.encode('utf-16-le'))
    parts.append(b'\x00' * 32)
    return b''.join(parts)


def build_zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('flag.txt', 'flag{zip-carve-ok}\n' + 'padding line\n' * 30)
        zf.writestr('blob.bin', bytes((i * 131 + 7) % 256 for i in range(1024)))
    return buf.getvalue()


def build_t4():
    payload = (b'HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\n\r\n'
               + b'JUNKJUNK' * 8 + build_zip_bytes() + b'TAILTAIL' * 4)
    frames = [eth_ipv4(tcp(80, 40002, 1, payload), 6)]
    return pcap_file(frames)


# ---------------------------------------------------------------- AD / 域协议样例
def _der_len(n):
    if n < 0x80:
        return bytes([n])
    raw = n.to_bytes((n.bit_length() + 7) // 8, 'big')
    return bytes([0x80 | len(raw)]) + raw


def der_tlv(tag, content):
    return bytes([tag]) + _der_len(len(content)) + content


def der_int(v):
    return der_tlv(0x02, v.to_bytes(max(1, (v.bit_length() + 7) // 8), 'big'))


def der_gstr(s):
    return der_tlv(0x1B, s.encode())


def der_principal(parts):
    """PrincipalName：name-string 用隐式 SEQUENCE OF GeneralString（真实 KDC 的写法）"""
    return der_tlv(0x30, der_tlv(0xA0, der_int(1))
                   + der_tlv(0xA1, b''.join(der_gstr(p) for p in parts)))


def der_encdata(etype, cipher, kvno=2):
    return der_tlv(0x30, der_tlv(0xA0, der_int(etype)) + der_tlv(0xA1, der_int(kvno))
                   + der_tlv(0xA2, der_tlv(0x04, cipher)))


def build_asrep(user, realm, spn, cipher):
    ticket = der_tlv(0x61, der_tlv(0x30, der_tlv(0xA0, der_int(5)) + der_tlv(0xA1, der_gstr(realm))
                     + der_tlv(0xA2, der_principal(spn)) + der_tlv(0xA3, der_encdata(23, cipher))))
    body = der_tlv(0x30,
                   der_tlv(0xA0, der_int(5)) + der_tlv(0xA1, der_int(11))
                   + der_tlv(0xA3, der_gstr(realm))
                   + der_tlv(0xA4, der_principal([user]))
                   + der_tlv(0xA5, ticket)
                   + der_tlv(0xA6, der_encdata(23, cipher)))
    return der_tlv(0x6B, body)


def build_ntlm2(challenge, target='CORP'):
    return (b'NTLMSSP\x00' + struct.pack('<I', 2)
            + struct.pack('<HHI', 0, 0, 0)          # TargetName 字段
            + struct.pack('<I', 0x00000001)
            + challenge
            + b'\x00' * 8 + b'\x00' * 8)


def build_ntlm3(user, domain, host, nt_response):
    lm = b'\x00' * 24
    dom = domain.encode('utf-16-le')
    usr = user.encode('utf-16-le')
    hst = host.encode('utf-16-le')
    base = 64
    lm_off = base
    nt_off = lm_off + len(lm)
    dom_off = nt_off + len(nt_response)
    usr_off = dom_off + len(dom)
    hst_off = usr_off + len(usr)

    def fld(off, ln):
        return struct.pack('<HHI', ln, ln, off)

    head = (b'NTLMSSP\x00' + struct.pack('<I', 3)
            + fld(lm_off, len(lm)) + fld(nt_off, len(nt_response))
            + fld(dom_off, len(dom)) + fld(usr_off, len(usr)) + fld(hst_off, len(hst))
            + struct.pack('<HHI', 0, 0, 0)          # session key
            + struct.pack('<I', 0x00000001))
    return head + lm + nt_response + dom + usr + hst


def build_ldap_bind(dn, password):
    return der_tlv(0x30, der_int(1) + der_tlv(0x60, der_int(3)
                                             + der_tlv(0x04, dn.encode())
                                             + der_tlv(0x80, password.encode())))


def build_t5_ad():
    """t5-ad.pcap：Kerberos(88) RC4 票据 + SMB NTLM 认证 + LDAP 明文绑定"""
    cipher = bytes((i * 37 + 11) % 256 for i in range(48))
    asrep = build_asrep('svc_sql', 'CORP.LOCAL', ['MSSQLSvc', 'dc01.corp.local'], cipher)
    krb = struct.pack('>I', len(asrep)) + asrep

    challenge = bytes.fromhex('0123456789abcdef')
    nt = bytes.fromhex('aabbccddeeff00112233445566778899') + b'\x01\x01\x00\x00' + b'\x00' * 28
    ntlm3 = build_ntlm3('kanna.seto', 'corp', 'WIN10-PC', nt)
    ntlm2 = build_ntlm2(challenge)

    ldap = build_ldap_bind('cn=svc_sql,dc=corp,dc=local', 'P@ssw0rd-AD-2026')
    frames = [
        eth_ipv4(tcp(50001, 88, 1, krb[:1200]), 6),
        eth_ipv4(tcp(88, 50001, 1, krb[1200:]), 6, src='10.9.9.20', dst='10.9.9.10'),
        eth_ipv4(tcp(50002, 445, 1, ntlm3), 6),
        eth_ipv4(tcp(445, 50002, 1, ntlm2), 6, src='10.9.9.20', dst='10.9.9.10'),
        eth_ipv4(tcp(50003, 389, 1, ldap), 6),
    ]
    return pcap_file(frames)


def generate(outdir):
    os.makedirs(outdir, exist_ok=True)
    files = {
        't1.pcap': build_t1(),
        't2.pcapng': build_t2(),
        't3.evtx': build_t3(),
        't4.pcap': build_t4(),
        't5-ad.pcap': build_t5_ad(),
    }
    for name in sorted(files):
        with open(os.path.join(outdir, name), 'wb') as f:
            f.write(files[name])
    return sorted(files)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    names = generate(sys.argv[1])
    print('已生成 %d 个样例 → %s: %s' % (len(names), sys.argv[1], ', '.join(names)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
