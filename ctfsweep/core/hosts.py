# -*- coding: utf-8 -*-
"""主机识别：IP ↔ MAC（ARP/Ethernet）+ 主机名线索（DHCP/NBNS）
恶意流量分析题的经典三问：感染主机 IP / MAC / 主机名——本模块负责 MAC 与主机名。
输出为信息性表格（不作为候选 flagged，避免污染候选池）。"""
import struct


def _mac(b):
    return ':'.join('%02x' % x for x in b)


def _ip4(b):
    return '.'.join(str(x) for x in b)


def _nbns_first_name(payload):
    """从 NBNS(UDP:137) 报文解出第一个 NetBIOS 名字（一级编码 A-P）"""
    if len(payload) < 12 + 34:
        return None
    seg = payload[12:12 + 32]
    out = []
    for i in range(0, 32, 2):
        hi, lo = seg[i] - 0x41, seg[i + 1] - 0x41
        if not (0 <= hi <= 15 and 0 <= lo <= 15):
            return None
        ch = (hi << 4) | lo
        if ch == 0:
            continue
        # 名字类型后缀（第16字节）先不剔
        out.append(chr(ch))
    name = ''.join(out).strip()
    return name or None


def _dhcp_hostname(payload):
    """从 DHCP/BOOTP 载荷取 option 12（主机名）与 chaddr（MAC）"""
    if len(payload) < 240 or payload[236:240] != b'\x63\x82\x53\x63':
        return None, None
    chaddr = payload[28:34] if payload[2] == 6 else None
    pos, hostname = 240, None
    while pos < len(payload):
        code = payload[pos]
        pos += 1
        if code == 0:
            continue
        if code == 255:
            break
        if pos >= len(payload):
            break
        ln = payload[pos]
        pos += 1
        val = payload[pos:pos + ln]
        pos += ln
        if code == 12 and val:
            hostname = val.decode('utf-8', 'replace').strip().strip('\x00') or None
        elif code == 61 and not chaddr and ln >= 7:
            chaddr = val[1:7]  # client-id 类型(1) + MAC
    mac = _mac(chaddr) if chaddr else None
    return mac, hostname


def collect_hosts(pkts):
    """遍历抓包，收集 IP↔MAC 与主机名线索

    返回 (ip_macs, mac_names, ip_names):
      ip_macs:   {ip: mac}   （Ethernet 源 + ARP sender/ reply target）
      mac_names: {mac: name} （DHCP option 12）
      ip_names:  {ip: name}  （NBNS 响应/名字注册）
    """
    ip_macs, mac_names, ip_names = {}, {}, {}
    for num, lt, pkt, ts in pkts:
        if lt != 1 or len(pkt) < 14:
            continue
        smac = _mac(pkt[6:12])
        et = struct.unpack('>H', pkt[12:14])[0]
        if et == 0x0806 and len(pkt) >= 42:               # ARP
            if pkt[18] == 6 and pkt[19] == 4:
                oper = struct.unpack('>H', pkt[20:22])[0]
                sha, spa = _mac(pkt[22:28]), _ip4(pkt[28:32])
                if spa != '0.0.0.0':
                    ip_macs.setdefault(spa, sha)
                if oper == 2:                              # reply: target 也有归属
                    tha, tpa = _mac(pkt[32:38]), _ip4(pkt[38:42])
                    if tpa != '0.0.0.0' and tha != '00:00:00:00:00:00':
                        ip_macs.setdefault(tpa, tha)
            continue
        off = 14
        while et in (0x8100, 0x88a8) and len(pkt) >= off + 4:   # VLAN
            et = struct.unpack('>H', pkt[off + 2:off + 4])[0]
            off += 4
        if et != 0x0800 or len(pkt) < off + 20 or pkt[off] >> 4 != 4:
            continue
        sip = _ip4(pkt[off + 12:off + 16])
        if not sip.startswith(('224.', '239.', '255.', '0.')):
            ip_macs.setdefault(sip, smac)
        # DHCP / NBNS（仅 UDP）
        proto = pkt[off + 9]
        if proto != 17 or len(pkt) < off + 20 + 8:
            continue
        ihl = (pkt[off] & 0xF) * 4
        l4 = off + ihl
        sport, dport = struct.unpack('>HH', pkt[l4:l4 + 4])
        payload = pkt[l4 + 8:]
        if 67 in (sport, dport) or 68 in (sport, dport):
            mac, host = _dhcp_hostname(payload)
            if mac and host and mac != '00:00:00:00:00:00':
                mac_names.setdefault(mac, host)
        elif 137 in (sport, dport) and len(payload) >= 14:
            flags = struct.unpack('>H', payload[2:4])[0]
            qr = (flags >> 15) & 1
            opcode = (flags >> 11) & 0xF
            if qr == 1 or opcode == 5:                     # 响应 / 名字注册 → 归属发送者
                nm = _nbns_first_name(payload)
                if nm and nm not in ('*',) and len(nm) <= 15:
                    nm = nm.rstrip('\x00 ').strip()
                    if nm:
                        ip_names.setdefault(sip, nm)
    return ip_macs, mac_names, ip_names


def print_hosts(ip_macs, mac_names, ip_names, limit=48):
    """打印主机表；返回打印行数

    一个 MAC 挂 ≥5 个 IP → 判定为路由器/网关（抓包中远端 IP 的以太网源都是网关 MAC），
    折叠为一行提示，不逐条列出，避免主机表被远端 IP 淹没。
    """
    if not ip_macs:
        return 0

    def ipkey(ip):
        try:
            return tuple(int(x) for x in ip.split('.'))
        except Exception:
            return (999, 999, 999, 999)

    # 按 MAC 归类
    mac_ips = {}
    for ip, mac in ip_macs.items():
        if ip.startswith(('224.', '239.', '255.', '0.')):
            continue
        mac_ips.setdefault(mac, []).append(ip)
    infra, hosts = {}, {}
    for mac, ips in mac_ips.items():
        ips = sorted(set(ips), key=ipkey)
        if len(ips) >= 5:
            infra[mac] = ips
        else:
            for ip in ips:
                hosts[ip] = mac

    out = []
    if infra:
        out.append('  【主机表】---- 路由器/网关 MAC（挂多个 IP，非终端主机）----')
        for mac, ips in sorted(infra.items(), key=lambda kv: -len(kv[1])):
            shown = ', '.join(ips[:4]) + (', ...' if len(ips) > 4 else '')
            out.append('    %s  ← %d 个 IP（%s）' % (mac, len(ips), shown))
    if hosts:
        out.append('  【主机表】IP ↔ MAC / 主机名（ARP+Ethernet+DHCP+NBNS）：')
        for ip, mac in sorted(hosts.items(), key=lambda kv: ipkey(kv[0])):
            extra = []
            nm = ip_names.get(ip)
            if nm:
                extra.append(nm)
            dn = mac_names.get(mac)
            if dn and dn not in extra:
                extra.append(dn + '(DHCP)')
            out.append('    %-15s %s%s' % (ip, mac, ('   ' + ' / '.join(extra)) if extra else ''))
    if len(out) <= 1:
        return 0
    # 限制行数（infra 行优先保留）
    if len(out) > limit + 2:
        out = out[:limit + 2] + ['    ...（其余省略）']
    for line in out:
        print(line)
    return len(out)
