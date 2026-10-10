# -*- coding: utf-8 -*-
"""pcap / pcapng 纯 Python 解析与四层解析（Ethernet/VLAN/PPPoE/Raw-IP/SLL/NULL + TCP/UDP/DNS）"""
import struct

PCAP_MAGICS = {
    b'\xd4\xc3\xb2\xa1': ('<', False),
    b'\xa1\xb2\xc3\xd4': ('>', False),
    b'\x4d\x3c\xb2\xa1': ('<', True),
    b'\xa1\xb2\x3c\x4d': ('>', True),
}
PCAPNG_MAGIC = b'\x0a\x0d\x0d\x0a'
LINKNAMES = {0: 'NULL/Loopback', 1: 'Ethernet', 101: 'Raw-IP', 12: 'Raw-IP', 228: 'Raw-IP',
             229: 'Raw-IP', 113: 'Linux-SLL', 276: 'Linux-SLL2'}


def parse_pcap(data):
    magic = data[:4]
    if magic not in PCAP_MAGICS or len(data) < 24:
        return None
    e, _nano = PCAP_MAGICS[magic]
    linktype = struct.unpack(e + 'I', data[20:24])[0]
    pkts, pos, n = [], 24, len(data)
    while pos + 16 <= n:
        ts_sec, ts_usec, caplen, _orig = struct.unpack(e + 'IIII', data[pos:pos + 16])
        pos += 16
        pkts.append((len(pkts) + 1, ts_sec + ts_usec / 1e6, data[pos:pos + caplen]))
        pos += caplen
    return linktype, pkts


def parse_pcapng(data):
    """解析 pcapng（SHB/IDB/EPB/SPB/老式PB），返回 (linktypes, [(包号, linktype, bytes)])"""
    if data[:4] != PCAPNG_MAGIC or len(data) < 28:
        return None
    bom = data[8:12]
    if bom == b'\x4d\x3c\x2b\x1a':
        e = '<'
    elif bom == b'\x1a\x2b\x3c\x4d':
        e = '>'
    else:
        return None
    linktypes, pkts = {}, []
    pos, n = 0, len(data)
    while pos + 12 <= n:
        try:
            btype, blen = struct.unpack(e + 'II', data[pos:pos + 8])
        except struct.error:
            break
        if blen < 12 or pos + blen > n:
            break
        body = data[pos + 8:pos + blen - 4]
        if btype == 1:                      # Interface Description Block
            if len(body) >= 8:
                linktypes[len(linktypes)] = struct.unpack(e + 'H', body[:2])[0]
        elif btype == 6:                    # Enhanced Packet Block
            if len(body) >= 20:
                iface = struct.unpack(e + 'I', body[:4])[0]
                tsh = struct.unpack(e + 'I', body[4:8])[0]
                tsl = struct.unpack(e + 'I', body[8:12])[0]
                caplen = struct.unpack(e + 'I', body[12:16])[0]
                pkts.append((len(pkts) + 1, linktypes.get(iface, 1), body[20:20 + caplen], ((tsh << 32) | tsl) / 1e6))
        elif btype == 3:                    # Simple Packet Block
            if len(body) >= 4:
                origlen = struct.unpack(e + 'I', body[:4])[0]
                pkts.append((len(pkts) + 1, linktypes.get(0, 1), body[4:4 + origlen], 0.0))
        elif btype == 2:                    # 已废弃 Packet Block
            if len(body) >= 20:
                iface = struct.unpack(e + 'H', body[:2])[0]
                tsh = struct.unpack(e + 'I', body[4:8])[0]
                tsl = struct.unpack(e + 'I', body[8:12])[0]
                caplen = struct.unpack(e + 'I', body[12:16])[0]
                pkts.append((len(pkts) + 1, linktypes.get(iface, 1), body[20:20 + caplen], ((tsh << 32) | tsl) / 1e6))
        pos += blen
    return linktypes, pkts


def load_packets(data):
    """统一装载 pcap / pcapng，返回 (格式名, [(包号, linktype, 包字节, 时间戳)])"""
    if data[:4] in PCAP_MAGICS:
        linktype, pkts = parse_pcap(data)
        return 'pcap', [(n, linktype, p, ts) for n, ts, p in pkts]
    if data[:4] == PCAPNG_MAGIC:
        got = parse_pcapng(data)
        if got:
            _linktypes, pkts = got
            return 'pcapng', pkts
    return None


def ip_offset(linktype, pkt):
    """返回 IP 头偏移（支持 Ethernet/VLAN/PPPoE、Raw-IP、SLL/SLL2、NULL）"""
    if linktype == 1:
        if len(pkt) < 14:
            return None
        et = struct.unpack('>H', pkt[12:14])[0]
        off = 14
        while et in (0x8100, 0x88a8):
            if len(pkt) < off + 4:
                return None
            et = struct.unpack('>H', pkt[off + 2:off + 4])[0]
            off += 4
        if et == 0x8864:                    # PPPoE 会话
            if len(pkt) < off + 8:
                return None
            ppp = struct.unpack('>H', pkt[off + 6:off + 8])[0]
            off += 8
            return off if ppp == 0x0021 else None
        return off if et == 0x0800 else None
    if linktype in (101, 12, 228, 229, 14):
        return 0
    if linktype == 113 and len(pkt) >= 16:  # Linux SLL
        et = struct.unpack('>H', pkt[14:16])[0]
        return 16 if et == 0x0800 else None
    if linktype == 276 and len(pkt) >= 20:  # Linux SLL2
        et = struct.unpack('>H', pkt[0:2])[0]
        return 20 if et == 0x0800 else None
    if linktype == 0 and len(pkt) >= 4:     # NULL/Loopback
        return 4
    return None


def l4_parse(linktype, pkt):
    off = ip_offset(linktype, pkt)
    if off is None or len(pkt) < off + 20 or pkt[off] >> 4 != 4:
        return None
    ihl = (pkt[off] & 0xF) * 4
    proto = pkt[off + 9]
    if struct.unpack('>H', pkt[off + 6:off + 8])[0] & 0x1FFF:
        return None
    src = '%d.%d.%d.%d' % tuple(pkt[off + 12:off + 16])
    dst = '%d.%d.%d.%d' % tuple(pkt[off + 16:off + 20])
    l4 = off + ihl
    if proto == 6 and len(pkt) >= l4 + 20:
        sport, dport = struct.unpack('>HH', pkt[l4:l4 + 4])
        doff = (pkt[l4 + 12] >> 4) * 4
        return ('tcp', src, dst, sport, dport, pkt[l4 + doff:])
    if proto == 17 and len(pkt) >= l4 + 8:
        sport, dport = struct.unpack('>HH', pkt[l4:l4 + 4])
        return ('udp', src, dst, sport, dport, pkt[l4 + 8:])
    return None


def dns_qname(payload):
    try:
        if len(payload) < 13 or struct.unpack('>H', payload[4:6])[0] < 1:
            return None
        off, labels = 12, []
        while off < len(payload):
            ln = payload[off]
            if ln == 0:
                break
            if ln & 0xC0:
                return None
            labels.append(payload[off + 1:off + 1 + ln])
            off += 1 + ln
        return b'.'.join(labels) if labels else None
    except Exception:
        return None
