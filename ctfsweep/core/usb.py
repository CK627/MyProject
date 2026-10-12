# -*- coding: utf-8 -*-
"""USB 流量分析：HID 键盘解码（USBPcap / pcap，linktype 249）。

CTF 常见题型：USB 键盘抓包 → 逐键解码出键入文本（常直接是 flag）。
USBPcap 帧结构（Windows）:
    headerLen(2, =27) + irpId(8) + status(4) + function(2) + info(1) +
    bus(2) + device(2) + endpoint(1) + transfer(1) + dataLength(4) = 27 字节
    + HID 数据（键盘 8 字节: [modifier, reserved, key1..key6]）
"""

# HID Usage ID → 字符（无 Shift）
HID_KEYMAP = {
    0x04: 'a', 0x05: 'b', 0x06: 'c', 0x07: 'd', 0x08: 'e', 0x09: 'f',
    0x0a: 'g', 0x0b: 'h', 0x0c: 'i', 0x0d: 'j', 0x0e: 'k', 0x0f: 'l',
    0x10: 'm', 0x11: 'n', 0x12: 'o', 0x13: 'p', 0x14: 'q', 0x15: 'r',
    0x16: 's', 0x17: 't', 0x18: 'u', 0x19: 'v', 0x1a: 'w', 0x1b: 'x',
    0x1c: 'y', 0x1d: 'z',
    0x1e: '1', 0x1f: '2', 0x20: '3', 0x21: '4', 0x22: '5', 0x23: '6',
    0x24: '7', 0x25: '8', 0x26: '9', 0x27: '0',
    0x28: '\n', 0x2c: ' ', 0x2d: '-', 0x2e: '=', 0x2f: '[', 0x30: ']',
    0x31: '\\', 0x33: ';', 0x34: "'", 0x35: '`', 0x36: ',', 0x37: '.',
    0x38: '/',
}
# Shift 组合下的字符
HID_SHIFTED = {
    0x1e: '!', 0x1f: '@', 0x20: '#', 0x21: '$', 0x22: '%', 0x23: '^',
    0x24: '&', 0x25: '*', 0x26: '(', 0x27: ')',
    0x2d: '_', 0x2e: '+', 0x2f: '{', 0x30: '}', 0x31: '|', 0x33: ':',
    0x34: '"', 0x35: '~', 0x36: '<', 0x37: '>', 0x38: '?',
}
MOD_SHIFT_MASK = 0x22   # Left(0x02) 或 Right(0x20) Shift
MOD_CTRL_MASK = 0x11    # Left(0x01) 或 Right(0x10) Ctrl


def is_usbpcap(pkts):
    """检测 USBPcap 帧（linktype 249 或 headerLen=0x1b 特征）。"""
    if not pkts:
        return False
    sample = pkts[: min(len(pkts), 10)]
    hits = 0
    for _num, lt, pkt, _ts in sample:
        if lt == 249:
            hits += 1
        elif len(pkt) >= 2 and pkt[0] == 0x1b and pkt[1] == 0x00:
            hits += 1
    return hits >= max(1, len(sample) // 2)


def ext_hid_reports(pkts, data_off=27):
    """从 USBPcap 帧提取 HID 报告（8 字节），兼容 dataLength 校验。"""
    reports = []
    for _num, _lt, pkt, _ts in pkts:
        if len(pkt) < data_off + 2:
            continue
        try:
            dlen = int.from_bytes(pkt[23:27], 'little')
        except Exception:
            dlen = 0
        if dlen >= 8:
            reports.append(pkt[data_off:data_off + 8])
        elif len(pkt) >= data_off + 8:
            reports.append(pkt[data_off:data_off + 8])
    return reports


def hid_keyboard_text(reports):
    """HID 键盘报告序列 → (键入文本, 键数)。

    规则：新键码（相对上一报告）输出字符；Shift 位上档；Ctrl 组合不计文本。
    """
    out, prev = [], set()
    for d in reports:
        if len(d) < 8:
            continue
        mod = d[0]
        keys = set(d[2:8]) - {0}
        shift = bool(mod & MOD_SHIFT_MASK)
        ctrl = bool(mod & MOD_CTRL_MASK)
        for k in sorted(keys):
            if k in prev:
                continue
            prev.add(k)
            if ctrl:
                continue          # Ctrl 组合（复制/终止等）不计入文本
            ch = None
            if shift:
                ch = HID_SHIFTED.get(k) or HID_KEYMAP.get(k)
            else:
                ch = HID_KEYMAP.get(k)
            if ch:
                out.append(ch)
        prev = keys
    return ''.join(out), len(reports)


def decode_usb_keyboard(pkts):
    """完整流程：USBPcap 帧 → 键盘文本。返回 (text, n_reports)。"""
    reports = ext_hid_reports(pkts)
    if not reports:
        return '', 0
    return hid_keyboard_text(reports)
