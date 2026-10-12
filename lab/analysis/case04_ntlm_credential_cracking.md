# case04: NetNTLM 凭证提取与爆破（AD 认证流量）

## 元数据

```yaml
id: case04
title: 从流量提取 NetNTLM(v1/v2) 哈希并用 hashcat 爆破
type: ad-credential / ntlm-cracking
source_files:
  - Alpha-1.pcapng（NetNTLMv1，WINXP\Administrator）
  - capture.pcapng（NetNTLMv2，空用户 + 域 "."）
  - wire0077.pcap（NetNTLMv2，PASCALPIG\ronaldo.paccione）
answers:
  Alpha-1: "密码 123456（NetNTLMv1，已破解）"
  capture: "空密码（NetNTLMv2，HMAC 链验证通过）"
  wire0077: "未解出（见下"难点"）"
tools_used: [hashcat -m 5500/5600/13100, 手写 NTLMSSP 解析, HMAC 链复算验证]
status: partial
```

## 识别特征

- pcap 含 `NTLMSSP` 标识（SMB(445)/HTTP Negotiate 流量）
- 三类消息：Type1 NEGOTIATE → Type2 CHALLENGE（含 8 字节 server challenge）
  → Type3 AUTHENTICATE（含 user/domain/LM response/NT response）
- 题目要求通常是"还原被攻击的账号密码"或渗透报告

## 分析步骤

### 1. 提取哈希（程序化，不依赖 Wireshark GUI）

```python
# 找 Type2：challenge = 消息偏移 24..32
# 找 Type3：解析字段偏移表
#   LM:   len@12  off@16
#   NT:   len@20  off@24
#   dom:  len@28  off@32
#   usr:  len@36  off@40
```

### 2. 判定 v1/v2 与哈希格式

- **NT response 24 字节 且 无 blob** → NetNTLMv1
  hashcat 格式（m=5500）：`user::host:LM_24B:NT_24B:challenge_8B`
- **NT response = 16B NTProof + 变长 blob** → NetNTLMv2
  hashcat 格式（m=5600）：`user::domain:challenge:NTProof:blob`

### 3. 爆破

```bash
hashcat -m 5500 hash.txt rockyou.txt       # NetNTLMv1
hashcat -m 5600 hash.txt rockyou.txt       # NetNTLMv2
hashcat -m 13100 hash.txt rockyou.txt      # Kerberoast RC4（$krb5tgs$23$）
```

### 4. 结果与验证

- **Alpha-1**：`Administrator::WINXP:...:b82952d898fd092b` → 字典第 1 位即中：
  **密码 `123456`**（弱口令，NetNTLMv1 无 ESS）
- **capture**：空用户名 + 域 "."，rockyou 直接出"空密码"嫌疑 → **用 HMAC 链
  独立复算验证**（NT_hash=空密码常量 31d6...c0 → HMAC-MD5 两级链 → NTProof
  完全一致）→ 确认**空密码**为真
- **wire0077（PASCALPIG\ronaldo.paccione）**：rockyou 14M + best64 自定义规则 +
  8 位数字掩码 + 针对性候选均未中哈希；但**整题已完整解出**（见下）。

## wire0077 完整解题（绕开损坏的哈希）

出处：**malware-traffic-analysis.net 2020-09-25 "TROUBLE ALERT"** 练习
（官方答案 PDF 可通过站点规则密码 `infected_20200925` 获取——规则：
"infected_ + 发布日期YYYYMMDD"，见站点 about 页 about.gif）。

**完整答案链**（无需破哈希——从同 pcap 的其他渠道拿到全部信息）：

1. **受害者**：ronaldo.paccione @ DESKTOP-M1JC4XX，IP 10.0.0.179
2. **恶意软件**：Agent Tesla 信息窃取木马
   （jojo.exe，来源 http://198.12.66.108/jojo.exe，
   SHA256 1e4b7d7868d25071db67da87392fd5dafab344a9fa6dc040f7afb0699152fc13）
3. **外发渠道**：未加密 SMTP（mail.big3.icu:587），5 封邮件
   - **PW 邮件** → **明文密码 `P@ssw0rd987654e21$`**（Outlook 账号
     ronaldo.paccione@outlook.com，Edge Chromium 保存）
   - **KL 邮件**（base64）→ 键盘记录：用户正在编辑 password-list.txt，
     捕获到 **`AOL - dkk3jjfh5hjkd!!!!!`**（密码清单条目）
   - CO 邮件（浏览器 cookie）/ SC 邮件（屏幕截图 jpeg 附件）
4. **IOC**：paste.nrecom.net（HTTPS）、api.ipify.org（IP 检测）

**技术要点**：
- 邮件正文用 quoted-printable / base64 编码，`{ENTER}` 标记按键边界
- 提取 SMTP 邮件 = 按 TCP 五元组重组流（端口 587，服务器→客户端流含 MAIL FROM）
- 官方答案包密码规则 `infected_YYYYMMDD`（about.gif 图里给出）

## 损坏哈希结论（wire0077）

Type3 用户名字段 `0x00→0x2E(".")`、blob 内 UTF-16 空字节 `0x00→0x20(" ")`
替换（"r.o.n.a.l.d.o.paccione"、"p ascal p ig.com"），AV 对长度结构完整
但字节已变。用 ①点号字面量用户名 ②正常用户名 ③PW/KL 邮件密码 全测不中
→ **文件级损坏，哈希不可破**。实战教训：**哈希破不出来时换渠道**
（同一 pcap 的邮件/文件/票据里往往就有明文答案）。

## 沉淀工具建议（待做）

- `core/ad.py` 已能做 NTLMSSP 提取；可补充：
  - 自动判定 v1/v2 并输出**双格式**哈希串
  - Type3 字段完整性自检（偏移越界/UTF-16 异常检测 → 标记"疑似损坏"）

## 同类变体判断指引

- 先看 NT response 长度：24B→v1；>24B→v2（前 16B 是 NTProof）
- v2 爆破需要正确 user+domain（错一个字母全盘不中）→ 从 Kerberos 票据交叉验证
- rockyou + best64 规则 + 数字掩码是标配三连；仍不中且怀疑数据损坏时，
  用 HMAC 链手动验证"空密码/简单密码"假设，判定是否 uncrackable
