---
case_id: 01
type: usb-keyboard
source_file: /Users/jj/Downloads/2/wire0078.pcap
linktype: 249
answer: "flag{pr355_0nwards_a2fee6e0}"
detect: "linktype==249 (USBPcap) 或 包前两字节==0x1b00 (headerLen=27)"
method: hid-keyboard-decode
tool: ctfsweep/core/usb.py
---

# 案例 01：USB 键盘流量解码（wire0078.pcap）

## 一、题目信息

| 项 | 值 |
|---|---|
| 文件 | wire0078.pcap（3.3 KB，66 个数据包，每包 35 字节） |
| 捕获类型 | USB 抓包（USBPcap，pcap 链路类型 **249**） |
| 答案 | `flag{pr355_0nwards_a2fee6e0}`（键盘键入文本，"pr355_0nwards" = "press onwards" 的 leet 写法） |

## 二、识别特征（这类题长什么样）

1. **链路类型 249**（USBPcap）——pcap 文件头 offset 20 处的 linktype
2. 每包以 `1b 00` 开头（USBPcap headerLen = 0x1b = 27）
3. 包长固定 = 27 字节头 + 8 字节 HID 数据
4. 数据包成对出现：keydown（HID 数据非零）+ keyup（HID 数据全零）

## 三、分析过程（完整推理链）

### Step 1: 初扫无输出
`ctfsweep -f wire0078.pcap` 原始版本输出"(无命中)"——连解析过程都没有。
**根因**：linktype 249 不在扫描器支持的链路类型表 → 所有包被跳过。

### Step 2: 手动解析 pcap 头
```
magic: d4 c3 b2 a1   → 小端序 pcap
linktype: 0xF9 = 249 → USBPcap（Windows USB 抓包工具）
包数 66，每包 caplen = 35
```

### Step 3: 帧结构拆解（以包 #1 为例）
```
1b 00 | 40 39 2d ac 89 b6 ff ff | 00 00 00 00 | 09 00 | 01 | 02 00 | 01 00 | 81 | 01 | 08 00 00 00 | 00 00 09 00 00 00 00 00
↑headerLen(2)  ↑irpId(8)            ↑status(4)    ↑func(2) ↑info ↑bus    ↑dev  ↑ep  ↑xfer ↑dataLength(4) ↑HID数据(8)
```
- 前 27 字节 = USBPcap 伪头（2+8+4+2+1+2+2+1+1+4）
- 后 8 字节 = **USB HID 键盘报告**

### Step 4: HID 键盘协议解码
HID 键盘 8 字节格式：`[modifier, reserved, key1, key2, key3, key4, key5, key6]`
- modifier 位：`0x02/0x20` = Shift（上档符号）；`0x01/0x10` = Ctrl（组合键不计文本）
- HID Usage ID：`0x04-0x1d` = a-z，`0x1e-0x27` = 1-0，`0x2c` = 空格，`0x2d-0x38` = 符号

### Step 5: 逐键提取（33 个按键报告）
| 序 | HID 码 | Shift | 字符 | | 序 | HID 码 | Shift | 字符 |
|---|---|---|---|---|---|---|---|---|
| 1 | 09 | - | f | | 15 | 04 | - | a |
| 2 | 0f | - | l | | 16 | 15 | - | r |
| 3 | 04 | - | a | | 17 | 07 | - | d |
| 4 | 0a | - | g | | 18 | 16 | - | s |
| 5 | 2f | ✔ | { | | 19 | 2d | ✔ | _ |
| 6 | 13 | - | p | | 20 | 04 | - | a |
| 7 | 15 | - | r | | 21 | 1f | - | 2 |
| 8 | 20 | - | 3 | | 22 | 09 | - | f |
| 9 | 22 | - | 5 | | 23 | 08 | - | e |
| 10 | 22 | - | 5 | | 24 | 08 | - | e |
| 11 | 2d | ✔ | _ | | 25 | 23 | - | 6 |
| 12 | 27 | - | 0 | | 26 | 08 | - | e |
| 13 | 11 | - | n | | 27 | 27 | - | 0 |
| 14 | 1a | - | w | | 28 | 30 | ✔ | } |

最后一个报告（#66）为 `mod=0x01 + key=0x06` = **Ctrl+C**（结束信号，不计入文本）。

### Step 6: 结果
```
flag{pr355_0nwards_a2fee6e0}
```

## 四、工具化沉淀（已并入 ctfsweep）

- **新增模块** `ctfsweep/core/usb.py`：
  - `is_usbpcap(pkts)`：链路类型/帧头特征检测
  - `ext_hid_reports(pkts)`：提取 HID 报告（27 字节偏移 + dataLength 校验）
  - `hid_keyboard_text(reports)`：逐键解码（新键输出、Shift 上档、Ctrl 组合跳过）
  - `decode_usb_keyboard(pkts)`：一站式解码
- **扫描器集成**：`scanner.scan_capture` 自动识别 USBPcap → 输出
  `[USB键盘] 键入文本: ...` + 高置信候选（含 flag 形态 0.97 / 其他 0.75）
- **修复的隐藏 bug**：解码成功但候选未入列表——`FLAG_RE` 是 bytes 正则，
  对 str 文本调用抛 TypeError 被 try/except 静默吞掉；改用字符串包含判断。

## 五、同类题型变体（判断指引，供模型/后续分析）

| 变体 | 识别 | 方法 |
|---|---|---|
| USB 键盘（本题） | linktype 249 + 每包 35B | HID 键码表逐键解码 |
| USB 鼠标 | HID 数据 4 字节（buttons, x, y, wheel） | movement 累加 → 坐标绘制轨迹图 |
| USB 存储 | 大量数据块搬运 | 字节块提取（carve 文件） |
| Linux usbmon | linktype 220 | 偏移不同（usbmon 头），待支持 |

**通用判断规则**（已按此逻辑落到工具）：
1. 包长固定 + 成对出现 + 数据字节极少 → 极可能是 HID 输入设备流量
2. 解码文本含 `flag{...}` → 直接作为答案（0.97 高置信）
3. 文本为乱码 → 检查键盘布局（US/JIS）、检查是否有大小写锁定、检查是否为近似键位
4. Ctrl 组合键（如 Ctrl+C）通常是"结束/复制"信号，不代表文本字符

## 六、对训练数据的贡献

- 正样本入集：`flag{pr355_0nwards_a2fee6e0}`（kind=USB键盘输入，group=wire0078.pcap）
- 该样本教会 JudgeNet：**"USB HID 解码文本" 这类来源是高价值答案**（类似 JWT/AD 票据等结构化输出）
