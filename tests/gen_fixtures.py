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
    t6-hosts.pcap  ARP 请求/应答 + DHCP 主机名 → 主机表（IP↔MAC / 主机名线索）
    t7-tls.pcap    TLS 跳过 / JPEG 头判别 / HTML 反误报 / 真 Windows 会话正例
    t8-b64.pcap    HTML 载荷页内嵌 base64 的 ZIP（saveAs 下载页）
    t9-dns.pcap    真实 DNS 长查询（外带嫌疑）/ HTML·CSS·文件名不得误报
    t10-ftp.pcap   FTP 会话（凭据/命令序列 → 非 flag 证据）/ 二进制关键词字节巧合不得误报
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


def build_t6():
    """t6-hosts.pcap：ARP（IP↔MAC）+ DHCP 主机名 选项 12 → 主机表"""
    a = bytes.fromhex('0200000000aa')      # 10.9.9.10
    b = bytes.fromhex('0200000000bb')      # 10.9.9.20
    bcast = b'\xff' * 6

    def eth(smac, dmac, et):
        return dmac + smac + struct.pack('>H', et)

    arp_req = (eth(a, bcast, 0x0806)
               + struct.pack('>HHBBH', 1, 0x0800, 6, 4, 1)
               + a + _ip('10.9.9.10') + b'\x00' * 6 + _ip('10.9.9.20'))
    arp_rep = (eth(b, a, 0x0806)
               + struct.pack('>HHBBH', 1, 0x0800, 6, 4, 2)
               + b + _ip('10.9.9.20') + a + _ip('10.9.9.10'))
    bootp = (b'\x01\x01\x06\x00' + struct.pack('>I', 0x5a5a1234)
             + b'\x00' * 4 + b'\x00' * 16 + a + b'\x00' * 10 + b'\x00' * 64 + b'\x00' * 128)
    opts = b'\x35\x01\x01' + b'\x0c\x08SMOKE-PC' + b'\xff'
    dhcp_payload = bootp + b'\x63\x82\x53\x63' + opts
    ip = (struct.pack('>BBHHHBBH', 0x45, 0, 20 + len(dhcp_payload), 0x1337, 0x4000, 64, 17, 0)
          + _ip('10.9.9.10') + _ip('255.255.255.255'))
    dhcp_frame = eth(a, bcast, 0x0800) + ip + udp(68, 67, dhcp_payload)
    http = eth_ipv4(tcp(40010, 80, 1, b'GET / HTTP/1.1\r\nHost: smoke.local\r\n\r\n'), 6)
    return pcap_file([arp_req, arp_rep, dhcp_frame, http])


def build_t7():
    """t7-tls.pcap：TLS 跳过 / JPEG 判别 / HTML 反误报 / 真 Windows 会话（正例）"""
    frames = []
    # 1) TLS 流内嵌"合法头"伪 JPEG → 应被 TLS 判定跳过（不雕刻）
    tls = (b'\x16\x03\x01\x00\x64' + b'\x01' + b'\x00\x00\x60' + b'\x03\x03'
           + bytes(range(0x20, 0x80)))                       # 看起来像握手记录
    fakejpg = b'\xff\xd8\xff\xe0' + b'FAKE-IMAGE-DATA' * 20 + b'\xff\xd9'
    frames.append(eth_ipv4(tcp(49001, 443, 1, tls + fakejpg), 6))
    # 2) 明文 HTTP 流中的真 JPEG（FFD8FF E0）→ 应提取
    realjpg = b'\xff\xd8\xff\xe0' + b'JFIF\x00' + b'REAL-IMAGE-DATA' * 60 + b'\xff\xd9'
    resp = (b'HTTP/1.1 200 OK\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n'
            % len(realjpg)) + realjpg
    frames.append(eth_ipv4(tcp(80, 49002, 1, resp), 6, src='10.9.9.20', dst='10.9.9.10'))
    # 3) HTML 页面含 C:\ 字样与表格标签 → 不得误报"交互会话"
    html = (b'<html><body>\n<table class="list">\n'
            b'C:\\inetpub\\wwwroot>\r\n</td></tr>\r\n</td></tr>\r\n<b>up</b>\r\n</body></html>')
    hresp = (b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: %d\r\n\r\n'
             % len(html)) + html
    frames.append(eth_ipv4(tcp(80, 49003, 1, hresp), 6, src='10.9.9.20', dst='10.9.9.10'))
    # 4) 真 Windows 交互会话（正例：banner + 提示符 + 命令）
    win = (b'Microsoft Windows [Version 10.0.19041.1]\r\n\r\n'
           b'C:\\Users\\smoke> whoami\r\nsmoke-pc\\smoke\r\n'
           b'C:\\Users\\smoke> ipconfig\r\nWindows IP Configuration\r\n'
           b'C:\\Users\\smoke> net user\r\n\r\nC:\\Users\\smoke> ')
    frames.append(eth_ipv4(tcp(49004, 4444, 1, win), 6))
    return pcap_file(frames)


def build_t8():
    """t8-b64.pcap：HTML 载荷页内嵌 base64 的 ZIP（内含 flag）→ 应解码提取"""
    from random import Random
    rnd = Random(42)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('readme.txt', 'flag{b64-embedded-ok}\n' + 'padding data\n' * 200)
        zf.writestr('blob.bin', bytes(rnd.randrange(256) for _ in range(4096)))
    inner = buf.getvalue()
    b64 = base64.b64encode(inner)
    html = (b'<html><head><script>function saveAs(b,f){}</script></head><body>\n'
            b'<div id="payload">' + b64 + b'</div>\n</body></html>')
    resp = (b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: %d\r\n\r\n'
            % len(html)) + html
    frames = [eth_ipv4(tcp(80, 49005, 1, resp), 6, src='10.9.9.20', dst='10.9.9.10')]
    return pcap_file(frames)


def build_t9():
    """t9-dns.pcap：真实 DNS 长查询（应报外带嫌疑）/ 良性长域名 · HTML·CSS·文件名（不得误报）"""
    # 1) 真实 DNS 外带式长查询（超长单标签）
    exfil = b'Zm9vYmFy' * 6 + b'.exfil.tunnel-domain.com'
    frames = [eth_ipv4(udp(53001, 53, dns_query(exfil)), 17)]
    # 2) 良性长域名（多短标签拼接，>50 字符）——不得报"DNS 外带"
    benign = b'adsh.wagbridge.taobao.alimama.com.gds.alibabadns.com'
    frames.append(eth_ipv4(udp(53002, 53, dns_query(benign)), 17))
    # 3) HTTP 页面垃圾：CSS 颜色 / multipart 文件名 / JS 片段（历史上全部误报过）
    junk = (b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n'
            b'<style>.x{color:#f2f2f2;border-color:#fff9ec}</style>\n'
            b'form-data; name="upload_file"; filename="ms17-010.cn.php"\n'
            b'layui-v2.4.5 MIT License By https://www.layui.com\n')
    frames.append(eth_ipv4(tcp(80, 53003, 1, junk), 6, src='10.9.9.20', dst='10.9.9.10'))
    return pcap_file(frames)


def build_t10():
    """t10-ftp.pcap：FTP 会话（凭据/命令序列 → 非 flag 类高置信证据）/
    二进制流里的关键词字节巧合（不得误报）/ 真实文本关键词（正例）。

    对应两处用户实测反馈：汇总区把 FTP 凭据当"可直接提交的 flag 候选"，
    以及图片流里 latin-1 视角貌似可打印的乱码被当成关键词线索。
    """
    C, S = '10.9.9.30', '10.9.9.40'
    frames, cseq, sseq = [], 1, 1

    def cli(payload):
        nonlocal cseq
        frames.append(eth_ipv4(tcp(51000, 21, cseq, payload), 6, src=C, dst=S))
        cseq += len(payload)

    def srv(payload):
        nonlocal sseq
        frames.append(eth_ipv4(tcp(21, 51000, sseq, payload), 6, src=S, dst=C))
        sseq += len(payload)

    srv(b'220 (vsFTPd 3.0.3)\r\n')
    cli(b'USER dj\r\n')
    srv(b'331 Please specify the password.\r\n')
    cli(b'PASS dj\r\n')
    srv(b'230 Login successful.\r\n')
    cli(b'PORT 10,9,9,30,199,40\r\nNLST\r\n')
    srv(b'150 Here comes the directory listing.\r\n226 Directory send OK.\r\n')
    cli(b'RETR 1.jpg\r\n')
    srv(b'150 Opening BINARY mode data connection for 1.jpg (1234 bytes).\r\n226 Transfer complete.\r\n')
    cli(b'RETR 2.jpg\r\n')
    srv(b'150 Opening BINARY mode data connection for 2.jpg (4321 bytes).\r\n226 Transfer complete.\r\n')
    # 二进制流（确定性"散布"字节，模拟压缩/加密数据）：
    # latin-1 视角几乎全可打印（旧的 0.7 闸门必然误报），严格文本判定应全部剔除
    pool = ([c for c in range(0x20, 0x7F) if c not in (0x7B, 0x7D)]
            + list(range(0xA1, 0x100)))
    arr = bytes(pool[(i * 73 + 11) % len(pool)] for i in range(1024))
    binary = arr[:200] + b'flag' + arr[300:500] + b'ctf' + arr[:100]
    frames.append(eth_ipv4(tcp(51001, 8080, 1, binary), 6, src=C, dst=S))
    # 真实文本里的关键词（正例：必须保留线索）
    text = b'notes: the ctf challenge starts at noon\r\nsecond line mentions ctf again\r\n'
    frames.append(eth_ipv4(tcp(51002, 8080, 1, text), 6, src=C, dst=S))
    return pcap_file(frames)


def generate(outdir):
    os.makedirs(outdir, exist_ok=True)
    files = {
        't1.pcap': build_t1(),
        't2.pcapng': build_t2(),
        't3.evtx': build_t3(),
        't4.pcap': build_t4(),
        't5-ad.pcap': build_t5_ad(),
        't6-hosts.pcap': build_t6(),
        't7-tls.pcap': build_t7(),
        't8-b64.pcap': build_t8(),
        't9-dns.pcap': build_t9(),
        't10-ftp.pcap': build_t10(),
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
