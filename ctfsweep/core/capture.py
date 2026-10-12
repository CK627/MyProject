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
             229: 'Raw-IP', 113: 'Linux-SLL', 276: 'Linux-SLL2',
             # 无线 / 物联网 / USB 等特殊链路（无 IP 解析）
             105: 'IEEE802.11(无线)', 127: 'Radiotap(无线)', 119: 'Prism(无线)',
             192: 'PPI(无线)', 195: 'IEEE802.15.4(带FCS)',
             220: 'USB-Linux(usbmon)', 249: 'USBPcap(USB抓包)'}


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


def tcp_seq(linktype, pkt):
    """TCP 序列号（流重组去重/定位用）；非 TCP 或解析失败返回 None"""
    off = ip_offset(linktype, pkt)
    if off is None or len(pkt) < off + 20 or pkt[off] >> 4 != 4:
        return None
    if pkt[off + 9] != 6:
        return None
    ihl = (pkt[off] & 0xF) * 4
    l4 = off + ihl
    if len(pkt) < l4 + 8:
        return None
    return struct.unpack('>I', pkt[l4 + 4:l4 + 8])[0]


def merge_stream(segs):
    """按 TCP seq 合并一个方向流的载荷（抗重传 / 重叠 / 乱序）。

    segs: [(num, ts, payload[, seq]), ...]（包序）。
    有 seq 时用"逐字节 last-wins"覆盖拼接：后到的重传/修正段覆盖先到的，
    这样重传、异常分段（同 seq 的短段+长段）不会产生重复/错位字节；
    未截获的中间空洞补 0x00。无 seq 数据、或序号跨度与载荷量严重不符
    （同一 4 元组混入了多条连接的 ISN）时，退化为按包序直接拼接。

    典型场景：HTTP 下载 exe 的流里有重传/分段异常，直接拼接得到的文件
    哈希与真实文件不符；本函数保证与 Wireshark 重组一致。
    """
    if not segs:
        return b''
    if len(segs[0]) < 4 or any(s[3] is None for s in segs):
        return b''.join(s[2] for s in segs)
    minseq = min(s[3] for s in segs)
    maxend = max(s[3] + len(s[2]) for s in segs)
    span = maxend - minseq
    if span <= 0:
        return b''
    # 跨度必须与真实载荷量相称，否则退回"按包序直接拼接"。
    #
    # 序号可比的流，跨度 ≈ 去重后的字节数（丢包造成的空洞通常只占零头）。
    # 实测 spambot.pcap：7 条"流"各有 3 个包、18 字节载荷，序号却横跨 3.5 GB——
    # 那是客户端端口被多条连接复用（或序号被伪造）后，几个互不相干的 ISN 被
    # 按 4 元组聚合到一起，序号之间根本没有可比性。照跨度分配就是每条流一个
    # 256 MB 零缓冲（合计 2.1 GB RSS、单文件 250 秒），而按包序拼接正好还原
    # 出真实的 18 字节。
    total = sum(len(s[2]) for s in segs)
    if span > max(4 * 1024 * 1024, total * 64):
        return b''.join(s[2] for s in segs)
    if span > 256 * 1024 * 1024:            # 防御：异常流（seq 跳变等）
        span = 256 * 1024 * 1024
    buf = bytearray(span)
    for s in segs:                          # 包序 last-wins
        payload, seq = s[2], s[3]
        start = seq - minseq
        if start >= span:
            continue
        end = min(start + len(payload), span)
        buf[start:end] = payload[:end - start]
    return bytes(buf)


class CaptureContext:
    """一次解析，多处复用。

    背景：`cli.main()` 已经把整个文件读进内存，`scan_capture` 又解析一遍，
    dns 模块再解析一遍，`merge_stream` 更是在同一份 tcp_streams 上被算了三次。
    这里把"解析"与"分析"分开：解析结果只算一次并缓存，分析各跑各的。

    ⚠️ **不合并分析语义**：`scan_capture` 的 DNS 循环产出 `DNS查询` 候选进分带报告，
    `dns` 模块只统计查询、按域聚合、过良性后缀闸门产出 `【dns】` 块——
    两者输出不同，都要保留，这里共享的只是解析结果。

    ⚠️ `l4` **严格保持包序**：`scan_capture` 原先是在解析循环里逐包交错产出
    findings 的，顺序一变，`report()` 的并列项顺序与元判断核的前 10 项就会变。
    """

    def __init__(self, data):
        self.data = data             # 原始字节：流扫描模块据此免去二次读盘
        loaded = load_packets(data)
        self.fmt, self.pkts = loaded if loaded else (None, [])
        self.l4 = []                 # [(包号, linktype, 包字节, 时间戳, 四层|None)]
        self.tcp_streams = {}        # {(src,sport,dst,dport): [(num, ts, payload, seq)]}
        self.udp_payloads = []       # [(num, src, sport, dst, dport, payload)]
        self.unknown_pkts = []       # [(num, lt, pkt)] 非 IP 结构，兜底扫描用
        self._blobs = None

        for num, lt, pkt, ts in self.pkts:
            r = l4_parse(lt, pkt)
            self.l4.append((num, lt, pkt, ts, r))
            if not r:
                self.unknown_pkts.append((num, lt, pkt))
                continue
            proto, src, dst, sport, dport, payload = r
            if not payload:
                continue
            if proto == 'tcp':
                self.tcp_streams.setdefault((src, sport, dst, dport), []).append(
                    (num, ts, payload, tcp_seq(lt, pkt)))
            else:
                self.udp_payloads.append((num, src, sport, dst, dport, payload))

    @property
    def is_capture(self):
        return self.fmt is not None

    def linktype_names(self, limit=4):
        lts = sorted(set(lt for _n, lt, _p, _t in self.pkts))
        return ', '.join(str(LINKNAMES.get(lt, lt)) for lt in lts[:limit])

    def stream_blobs(self):
        """[(方向键, 分段, 合并载荷)]——`merge_stream` 每个方向流只算一次。"""
        if self._blobs is None:
            self._blobs = [(k, segs, merge_stream(segs))
                           for k, segs in self.tcp_streams.items()]
        return self._blobs


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
