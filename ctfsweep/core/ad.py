# -*- coding: utf-8 -*-
"""AD / 域协议取证：Kerberos(88) / NTLMSSP(SMB·HTTP) / LDAP(389) 凭据与票据提取。

为什么需要这个模块：
    AD 类题目（Kerberoasting / AS-REP Roasting / NetNTLM 中继 / LDAP 明文绑定）
    的流量里**没有 flag{} 明文**，也不走 HTTP/DNS 外带——纯字符串扫描必然零命中。
    真正有价值的"答案素材"是：域账号、SPN、票据加密块、NetNTLM 响应、明文口令。
    本模块把它们解出来，并转成可直接交给 hashcat / john 的形式。

输出候选的置信度口径（沿用全局分级）：
    0.93 LDAP 明文绑定口令 / 0.90 可离线爆破的 RC4 票据 / 0.85 NetNTLM 响应
    0.62 AES 票据（需字典，成本高） / 0.55 域账号·SPN 清单（线索）
"""
import struct

KDC_PORTS = (88, 464)
LDAP_PORTS = (389, 3268, 636, 3269)
KRB_MSG_TAGS = {0x6a: 'AS-REQ', 0x6b: 'AS-REP', 0x6c: 'TGS-REQ',
                0x6d: 'TGS-REP', 0x6e: 'AP-REQ', 0x6f: 'AP-REP'}
ETYPES = {1: 'des-cbc-crc', 3: 'des-cbc-md5', 17: 'AES128', 18: 'AES256',
          23: 'RC4-HMAC', 24: 'RC4-HMAC-EXP'}


# ---------------------------------------------------------------- 极简 ASN.1
def _clean(s):
    """去掉 GeneralString 残留的控制字符（类名/账号里混入会把报告版面弄乱）"""
    return ''.join(ch if (ch.isprintable() and ch != '\x1b') else '' for ch in s)


def _tlv(b, i):
    """返回 (tag, content_start, content_len)；越界返回 (0, i, 0)"""
    if i < 0 or i + 2 > len(b):
        return 0, i, 0
    t = b[i]
    l = b[i + 1]
    i += 2
    if l & 0x80:
        n = l & 0x7F
        if n > 4 or i + n > len(b):
            return 0, i, 0
        l = int.from_bytes(b[i:i + n], 'big')
        i += n
    return t, i, l


def _int(b, c, l):
    """上下文内是完整 INTEGER TLV，需再剥一层"""
    t, i2, l2 = _tlv(b, c)
    if t != 0x02:
        return 0
    return int.from_bytes(b[i2:i2 + l2], 'big') if l2 else 0


def _enter(b, i):
    """进入 [n] 上下文内部的 SEQUENCE，返回 (content_start, content_len)"""
    t, cs, cl = _tlv(b, i)
    t2, c2, l2 = _tlv(b, cs)
    return c2, l2


def _pname(b, i):
    """PrincipalName → 'primary/instance' 字符串"""
    try:
        c2, l2 = _enter(b, i)
        j = c2
        t, c, l = _tlv(b, j)
        j = c + l                                   # name-type [0]
        t, c, l = _tlv(b, j)                        # name-string [1]
        parts, k = [], c
        while k < c + l:
            t2, c2, l2 = _tlv(b, k)
            if not l2:
                break
            if t2 == 0x30:                            # [1] 隐式 SEQUENCE OF 时多包一层
                t2, c2, l2 = _tlv(b, c2)
            parts.append(_clean(b[c2:c2 + l2].decode('utf-8', 'replace')))
            k = c2 + l2
        return '/'.join(p for p in parts if p)
    except Exception:
        return ''


def _encdata(b, i):
    """EncryptedData → (etype, kvno, cipher_bytes)"""
    try:
        c2, l2 = _enter(b, i)
        j, et, kv, cip = c2, 0, 0, b''
        while j < c2 + l2:
            t, c, l = _tlv(b, j)
            if not l and t == 0:
                break
            if t == 0xA0:
                et = _int(b, c, l)
            elif t == 0xA1:
                kv = _int(b, c, l)
            elif t == 0xA2:
                t2, cc, ll = _tlv(b, c)
                cip = b[cc:cc + ll]
            j = c + l
        return et, kv, cip
    except Exception:
        return 0, 0, b''


# ---------------------------------------------------------------- Kerberos
def krb_messages(blob, framed):
    """切出 Kerberos 消息体。TCP 88 有 4 字节长度前缀，UDP 88 没有。"""
    out = []
    if framed:
        i = 0
        while i + 4 <= len(blob):
            n = int.from_bytes(blob[i:i + 4], 'big')
            if n <= 0 or i + 4 + n > len(blob):
                break
            body = blob[i + 4:i + 4 + n]
            if body and body[0] in KRB_MSG_TAGS:
                out.append(body)
            i += 4 + n
    elif blob and blob[0] in KRB_MSG_TAGS:
        out.append(blob)
    return out


def krb_rep(body):
    """解析 KDC-REP（AS-REP / TGS-REP），返回字段字典"""
    try:
        t, cs, cl = _tlv(body, 0)
        t2, c2, l2 = _tlv(body, cs)
        j, o = c2, {}
        while j < c2 + l2:
            t, c, l = _tlv(body, j)
            if not l and t == 0:
                break
            if t == 0xA1:
                o['msg'] = _int(body, c, l)
            elif t == 0xA3:
                t2, c3, l3 = _tlv(body, c)
                o['realm'] = _clean(body[c3:c3 + l3].decode('utf-8', 'replace'))
            elif t == 0xA4:
                o['cname'] = _pname(body, j)
            elif t == 0xA5:                               # Ticket [APPLICATION 1]
                tcs, tcl = _enter(body, c)
                k = tcs
                while k < tcs + tcl:
                    a, ac, al = _tlv(body, k)
                    if not al and a == 0:
                        break
                    if a == 0xA2:
                        o['sname'] = _pname(body, k)
                    elif a == 0xA3:
                        o['tenc'] = _encdata(body, k)
                    k = ac + al
            elif t == 0xA6:
                o['enc'] = _encdata(body, j)
            j = c + l
        return o
    except Exception:
        return {}


def asrep_hash(user, realm, cip):
    return '$krb5asrep$23$%s@%s:%s$%s' % (user, realm, cip[:16].hex(), cip[16:].hex())


def tgs_hash(user, realm, spn, cip):
    return '$krb5tgs$23$*%s$%s$%s*$%s$%s' % (user, realm, spn,
                                             cip[:16].hex(), cip[16:].hex())


def roast_note(etype):
    """按加密类型给出破解建议"""
    if etype == 23:
        return 'RC4：hashcat -m 18200/13100 可离线爆破（首选）'
    if etype in (17, 18):
        return 'AES：hashcat -m 19700/19900 需字典，成本远高于 RC4'
    if etype in (1, 3):
        return 'DES：已废弃，hashcat -m 8500 可爆破'
    return '未知加密类型'


# ---------------------------------------------------------------- NTLMSSP
NTLM_SIG = b'NTLMSSP\x00'


def _ntlm_field(b, o, idx):
    base = o + 12 + idx * 8
    if base + 8 > len(b):
        return b''
    ln = struct.unpack('<H', b[base:base + 2])[0]
    off = struct.unpack('<I', b[base + 4:base + 8])[0]
    if off + ln > len(b) - o:
        return b''
    return b[o + off: o + off + ln]


def ntlm_messages(blob):
    """按偏移顺序产出 (offset, type, info)；type 2 带 challenge，type 3 带响应/账号"""
    out, i = [], 0
    while True:
        i = blob.find(NTLM_SIG, i)
        if i < 0:
            break
        try:
            mtype = struct.unpack('<I', blob[i + 8:i + 12])[0]
        except Exception:
            i += 8
            continue
        info = {'type': mtype}
        try:
            if mtype == 2:
                info['challenge'] = blob[i + 24:i + 32]
            elif mtype == 3:
                nt = _ntlm_field(blob, i, 1)
                info['nt'] = nt
                for key, idx in (('domain', 2), ('user', 3), ('host', 4)):
                    raw = _ntlm_field(blob, i, idx)
                    try:
                        info[key] = _clean(raw.decode('utf-16-le', 'replace'))
                    except Exception:
                        info[key] = _clean(raw.decode('latin-1', 'replace'))
        except Exception:
            pass
        out.append((i, mtype, info))
        i += 8
    return out


def netntlm_hash(user, domain, challenge, nt):
    """NetNTLMv2 → hashcat 5600；NetNTLMv1 → 5500"""
    if not challenge or not nt:
        return None
    if len(nt) > 24:                                  # NTLMv2: 16B NTProofStr + blob
        return (5600, '%s::%s:%s:%s:%s' % (user, domain, challenge.hex(),
                                           nt[:16].hex(), nt[16:].hex()))
    if len(nt) == 24:                                 # NTLMv1
        return (5500, '%s::%s:%s:%s:%s' % (user, domain, '0' * 32,
                                           nt.hex(), challenge.hex()))
    return None


# ---------------------------------------------------------------- LDAP
def ldap_binds(blob):
    """产出 (绑定DN, 明文口令)：LDAP simple bind 的口令是明文的"""
    out, i = [], 0
    n = len(blob)
    while i < n - 8:
        i = blob.find(b'\x60', i)
        if i < 0:
            break
        try:
            t, c, l = _tlv(blob, i)                   # BindRequest [APPLICATION 0]
            if t != 0x60 or l < 8:
                i += 1
                continue
            j = c
            t2, c2, l2 = _tlv(blob, j)                # version INTEGER
            if t2 != 0x02:
                i += 1
                continue
            j = c2 + l2
            t3, c3, l3 = _tlv(blob, j)                # name LDAPDN
            if t3 != 0x04:
                i += 1
                continue
            dn = _clean(blob[c3:c3 + l3].decode('utf-8', 'replace'))
            j = c3 + l3
            t4, c4, l4 = _tlv(blob, j)                # simple password [0]
            if t4 != 0x80 or l4 < 1:
                i += 1
                continue
            pw = blob[c4:c4 + l4]
            if sum(32 <= x < 127 for x in pw) >= max(1, len(pw) - 1):
                out.append((dn, _clean(pw.decode('utf-8', 'replace'))))
            i = c4 + l4
        except Exception:
            i += 1
    return out


# ---------------------------------------------------------------- 编排
def _conn_key(dirkey):
    a = (dirkey[0], dirkey[1])
    b = (dirkey[2], dirkey[3])
    return (a, b) if a <= b else (b, a)


def scan_ad(tcp_streams, udp_payloads, add):
    """扫描 AD 协议，返回供打印的线索结构 dict。"""
    info = {'realm': '', 'users': [], 'spns': [], 'tickets': [], 'ntlm': [],
            'ldap': [], 'krb_loose': []}
    seen_user = set()

    def _add_user(u):
        if u and u != '?' and u.lower() not in seen_user:
            seen_user.add(u.lower())
            info['users'].append(u)

    # --- 1) Kerberos：TCP 88（带 4 字节帧）与 UDP 88
    krb_blobs = []
    for dirkey, segs in tcp_streams.items():
        if 88 in (dirkey[1], dirkey[3]):
            krb_blobs.append(('%s:%d -> %s:%d' % dirkey, b''.join(p for _n, _t, p in segs), True))
    for num, src, sport, dst, dport, payload in udp_payloads:
        if 88 in (sport, dport):
            krb_blobs.append(('UDP %s:%d -> %s:%d 包#%d' % (src, sport, dst, dport, num),
                              payload, False))
    # 兜底：任意流里出现 Kerberos 消息头（端口被改/隧道）
    for dirkey, segs in tcp_streams.items():
        if 88 in (dirkey[1], dirkey[3]):
            continue
        blob = b''.join(p for _n, _t, p in segs)
        if blob[:1] in (b'\x6a', b'\x6b', b'\x6c', b'\x6d') or b'\x6b\x82' in blob[:3 * 1024 * 1024]:
            krb_blobs.append(('%s:%d -> %s:%d (疑似Kerberos)' % dirkey, blob, False))

    seen_ticket = set()
    for loc, blob, framed in krb_blobs:
        for body in krb_messages(blob, framed):
            kind = KRB_MSG_TAGS.get(body[0])
            if kind not in ('AS-REP', 'TGS-REP'):
                continue
            o = krb_rep(body)
            user = o.get('cname') or '?'
            realm = o.get('realm') or '?'
            if realm != '?':
                info['realm'] = realm
            _add_user(user)
            spn = o.get('sname') or ''
            if spn and spn not in info['spns']:
                info['spns'].append(spn)
            if kind == 'AS-REP':
                et, kv, cip = o.get('enc', (0, 0, b''))
                what, tgt = 'AS-REP（可 AS-REP Roasting）', user
            else:
                et, kv, cip = o.get('tenc', (0, 0, b''))
                what, tgt = 'TGS-REP 服务票据（Kerberoasting）', spn or user
            if not cip:
                continue
            key = (kind, tgt.lower(), et, len(cip))
            if key in seen_ticket:
                continue
            seen_ticket.add(key)
            rec = {'kind': kind, 'user': user, 'spn': spn, 'etype': et,
                   'name': ETYPES.get(et, str(et)), 'cipher': len(cip),
                   'target': tgt, 'loc': loc}
            if et == 23:
                rec['hash'] = (asrep_hash(user.split('/')[0], realm, cip) if kind == 'AS-REP'
                               else tgs_hash(user.split('/')[0], realm, spn, cip))
            info['tickets'].append(rec)
            score = 0.90 if et == 23 else 0.62
            val = '%s | %s | %s %s | cipher %dB | %s' % (
                what, tgt, 'etype', ETYPES.get(et, et), len(cip), roast_note(et))
            add((score, 'Kerberos票据', b'', val.encode('utf-8', 'replace'), loc))
            if rec.get('hash'):
                add((0.90, 'Kerberos票据', b'', rec['hash'].encode('utf-8', 'replace'),
                     loc + ' [hashcat]'))

    # --- 2) NTLMSSP（SMB / HTTP / 任意流）
    streams = []
    for dirkey, segs in tcp_streams.items():
        streams.append((dirkey, b''.join(p for _n, _t, p in segs)))
    for num, src, sport, dst, dport, payload in udp_payloads:
        streams.append((('%s' % src, sport, '%s' % dst, dport), payload))
    challenges = {}
    for dirkey, blob in streams:
        for _o, mt, inf in ntlm_messages(blob):
            if mt == 2 and inf.get('challenge'):
                challenges.setdefault(_conn_key(dirkey), []).append(inf['challenge'])
    for dirkey, blob in streams:
        for _o, mt, inf in ntlm_messages(blob):
            if mt != 3:
                continue
            chs = challenges.get(_conn_key(dirkey)) or []
            chal = chs[0] if chs else b''
            got = netntlm_hash(inf.get('user', '?'), inf.get('domain', ''), chal, inf.get('nt', b''))
            user = inf.get('user', '?')
            _add_user(user)
            loc = '%s:%d -> %s:%d' % dirkey
            if got:
                mode, h = got
                info['ntlm'].append({'user': user, 'mode': mode, 'hash': h})
                add((0.85, 'NetNTLM', b'',
                     ('NetNTLMv2 响应（hashcat -m 5600）：%s@%s' % (user, inf.get('domain', '')))
                     .encode('utf-8', 'replace'), loc))
                add((0.85, 'NetNTLM', b'', h.encode('utf-8', 'replace'), loc + ' [hashcat]'))
            else:
                add((0.55, '域账号', b'',
                     ('NTLM 认证：%s\\%s（主机 %s，未捕获 challenge）'
                      % (inf.get('domain', ''), user, inf.get('host', '')))
                     .encode('utf-8', 'replace'), loc))

    # --- 3) LDAP simple bind 明文口令
    for dirkey, blob in streams:
        if len(blob) < 16:
            continue
        for dn, pw in ldap_binds(blob):
            loc = '%s:%d -> %s:%d' % dirkey
            info['ldap'].append({'dn': dn, 'pw': pw})
            add((0.93, 'LDAP口令', b'', ('LDAP 明文绑定：%s  口令= %s' % (dn, pw))
                 .encode('utf-8', 'replace'), loc))

    # --- 4) 域账号/SPN 清单（线索，低置信）
    if info['realm'] and info['users']:
        add((0.55, '域账号', b'', ('域 %s 出现的账号：%s' % (info['realm'], '、'.join(info['users'][:20])))
             .encode('utf-8', 'replace'), '(Kerberos/NTLM)'))
    for spn in info['spns'][:20]:
        add((0.55, '域账号', b'', ('SPN（服务主体名，Kerberoasting 目标）：%s' % spn)
             .encode('utf-8', 'replace'), '(Kerberos TGS-REP)'))
    return info


def print_ad_info(info):
    """打印【AD / 域渗透线索】区块"""
    if not (info['realm'] or info['tickets'] or info['ntlm'] or info['ldap']):
        return
    print('  【AD / 域渗透线索】')
    if info['realm']:
        print('    域: %s' % info['realm'])
    if info['users']:
        print('    账号(%d): %s' % (len(info['users']), '、'.join(info['users'][:20])))
    if info['spns']:
        print('    SPN(%d): %s' % (len(info['spns']), '、'.join(info['spns'][:12])))
    for t in info['tickets'][:12]:
        print('    票据: %s %s  etype %s (%s)  cipher %dB  %s'
              % (t['kind'], t['target'], t['etype'], t['name'], t['cipher'], roast_note(t['etype'])))
        if t.get('hash'):
            print('      └ %s' % t['hash'][:170])
    for n in info['ntlm'][:10]:
        print('    NetNTLMv%d: %s' % (2 if n['mode'] == 5600 else 1, n['user']))
        print('      └ %s' % n['hash'][:170])
    for l in info['ldap'][:10]:
        print('    LDAP 明文口令: %s = %s' % (l['dn'][:60], l['pw']))
