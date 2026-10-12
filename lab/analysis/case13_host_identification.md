---
case_id: 13
type: host-identification
source_file: （通用能力，样例 2026-10-01-traffic-analysis-exercise.pcap）
linktype: 1
answer: unknown
detect: "题目问'感染主机/攻击者的 IP、MAC、主机名、账号名'（事件报告式问答）"
method: arp-ethernet-host-table + dhcp-opt12 + nbns-names
tool: ctfsweep/core/hosts.py（新）
---

# case13：主机识别——IP ↔ MAC ↔ 主机名（事件报告式三问）

**类型**：主机身份识别（"感染的 Windows 客户端 IP / MAC / 主机名 / 用户账号"）
**方法**：ARP + Ethernet 主机表 + DHCP/NBNS 主机名线索

## 为什么需要专门能力

事件报告类题目（SOC 告警复核、入侵分析）固定四问：
**感染主机是谁**（IP）、**网卡地址**（MAC）、**机器名**（hostname）、**账号**（user）。
修复前的扫描器输出 IP 与账号（AD 板块），但 **MAC 与主机名没有出处**——
分析师还得手工翻 Wireshark。→ 新增 `hosts.py`。

## 数据源与提取规则

| 线索 | 来源 | 可靠性 |
|------|------|--------|
| IP ↔ MAC | ARP sender / reply target；Ethernet 源 MAC | 高（同一 L2 段内） |
| 主机名 | DHCP 选项 12（客户端自报机器名） | 高 |
| 主机名 | NBNS（UDP 137）响应 / 名字注册的发送方 | 中（WINS 服务器响应会错标，仅作线索） |
| 账号 | Kerberos cname（AD 板块，过滤 `$` 机器账号） | 高 |

**关键工程点：网关折叠**。抓包里所有远端 IP 的以太网源 MAC 都是网关的，
不折叠的话主机表会被几十个远端 IP 淹没。规则：**一个 MAC 挂 ≥5 个 IP → 判定为
路由器/网关，折叠成一行提示**；终端主机（少数 IP）逐条列出。

## 输出样例（直接回答三问）

```
【主机表】---- 路由器/网关 MAC（挂多个 IP，非终端主机）----
    00:01:96:ce:dd:92  ← 68 个 IP（4.150.x.x, 8.8.4.4, ...）
【主机表】IP ↔ MAC / 主机名（ARP+Ethernet+DHCP+NBNS）：
    10.10.1.10      18:a9:9b:20:dd:f1
    10.10.1.128     00:22:fb:ec:7e:e7   DESKTOP-4VGYQX7(DHCP)
```

对照官方答案：感染主机 IP `10.10.1.128`、MAC `00:22:fb:ec:7e:e7`、
主机名 `DESKTOP-4VGYQX7`、账号 `bdiaz`（AD 板块给出）——**四问全中**。

## 交叉验证（做一致性校验的习惯）

- 主机名可在三处互证：DHCP 自报名 vs NBNS 响应名 vs Kerberos 机器账号（`HOST$`）。
  三处一致 → 放心采用；不一致 → 报出全部线索人工裁决。
- 感染主机的判定：结合"哪个 IP 出现了恶意下载/外连"（提取物来源行给出
  `恶意IP:端口 -> 受害IP:端口`），再到主机表拿该 IP 的 MAC/主机名。

## 工具沉淀

- `ctfsweep/core/hosts.py`：`collect_hosts(pkts)` → (ip_macs, mac_names, ip_names)；
  `print_hosts()` 折叠网关 + 合并输出。
- 集成在 `scan_capture` 主流程（每次扫描自动打印主机表）。
- 冒烟夹具 `t6-hosts.pcap`（ARP 请求/应答 + DHCP 选项 12）覆盖回归。
