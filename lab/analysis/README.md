# 分析案例库（Analysis Case Library）

本目录保存**每一道题目的完整分析过程**——既是人查阅的笔记，也是将来喂给
LLM / 判断核的"分析教材"：

- **人**：复盘解题思路、复用分析套路
- **AI（LLM 分析助手）**：作为 few-shot 上下文——给定新题目时先检索相似案例
- **JudgeNet（判断核）**：案例对应的"发现"已由 `lab/build_dataset.py` 回填为训练样本
  （`lab/dataset.jsonl`），模型由此学会"什么形态的候选是高价值答案"

> **图片缓存约定**（2026-10-13 定稿）：提取到但**未识别/无法判定**的图片属于
> 扫描缓存的一部分，与结果缓存同放在数据根 `~/.devtools/ctfsweep/` 下，按题目分目录：
>
> - 该题图片 **≤3 张** → 直接放 `<题目名>/`，不另建子目录；
> - 该题图片 **>3 张** → 收进 `<题目名>/image/`（题内图多时避免根目录被刷屏）。
>
> 状态统一登记在 `~/.devtools/ctfsweep/README.md`（⬜未识别 / 🔷普通资源 / ✅已解出）；
> 已解出的图片连同结论一并保留作参考。**不要直接丢弃**。
> 与结果缓存一样**只增不减**：`ctfsweep update` / `uninstall` 都不碰它。

## 格式约定

每个案例一个 `.md` 文件，头部为 machine-readable 元数据（YAML front matter）：

```yaml
---
case_id: 01            # 案例编号
type: usb-keyboard      # 题型（usb-keyboard / http-plaintext / ad-credential / ...）
source_file: <路径>      # 题目文件
linktype: 249           # 链路类型（如有）
answer: "flag{...}"     # 分析得出的答案（无答案写 unknown）
detect: "识别特征"       # 怎么判断是这类题（供自动路由）
method: hid-keyboard-decode  # 分析方法（工具函数或人工步骤）
tool: ctfsweep/core/usb.py   # 沉淀到的工具模块
---
```

正文结构：题目信息 → 识别特征 → 分析过程（完整推理链）→ 解码/提取规则 →
工具沉淀 → 同类变体（判断指引）→ 对训练数据的贡献。

## 案例索引

| 编号 | 题型 | 文件 | 答案 | 工具化 |
|------|------|------|------|--------|
| 01 | USB 键盘流量 | wire0078.pcap | `flag{pr355_0nwards_a2fee6e0}` | core/usb.py |
| 02 | HTTP 嵌套编码文件提取 | extracting-objects-…-01.pcap | 无 flag（提取即目标） | http.py + extract.py |
| 03 | RGB 像素流还原图像 | misc1.pcapng | `flag{Rgb_dhskjadyhjksndjsagh}` | lab/tools/pixels_to_png.py |
| 04 | NetNTLM 凭证提取与爆破 | Alpha-1 / capture / wire0077 | 123456 / 空密码 / 邮件解出 | hashcat 三连 |
| 05 | 流量藏加密 zip + 提示爆破 | A.pcapng / logs.pcapng | `flag{friday}` / `flag{Find You!}` | extract 链 |
| 06 | FTP/Telnet 双服务爆破还原 | capture4.pcap | root/toor654321 + administrator/admin654321 | 五元组重组法 |
| 07 | **入侵行为分析（问答式）** | hacker / hacker1.pcapng | 见 case07（IP/端口/凭据/命令/版本） | **core/session.py（新）** |
| 08 | **vsftpd 笑脸后门利用链** | attack.pcapng | 见 case08（CVE-2011-2523/6200/root） | session.py 后门+shell 检测 |
| 09 | **渗透演练链（nmap→Hydra→Telnet）** | infiltration.pcapng | 凭据 `administrator/YwQgj8eN` | session.py 爆破结果提取 |
| 10 | **Redis 写 SSH 公钥提权链** | 2021.pcapng | AUTH `11aacc` → 注入 root 公钥 | session.py Redis 检测 |
| 11 | **phpMyAdmin 写 Webshell + 读文件** | Bravo-1.pcapng | shell2.php（密码 `cia`）；flag.txt=`DCZ` | SQL 语句明文化分析 |
| 12 | **TCP 重组一致性 + HTTP 响应体雕刻** | 2026-10-01-…pcap | 提取 EXE 哈希与官方逐字节一致 | **core/capture.py merge_stream + 逐响应体雕刻（新）** |
| 13 | **主机识别（IP↔MAC↔主机名）** | 通用（样例 2026-10-01-…pcap） | 感染主机三问全中 | **core/hosts.py（新）** |
| 14 | **真实流量误报治理** | 批量恶意流量题（样例 2021-10-22 等） | TLS 伪文件/假 JPEG/HTML 假命令三处修复 | scanner._is_tls_stream + JPEG_MARKERS + session 过滤 |
| 15 | **base64 载荷页解码（saveAs 页）** | 2021-02-08-…pcap | 页面内嵌 822KB Word 文档 → 官方哈希一致 | **extract.carve_base64_blobs（新）** |

## 已解出汇总（Downloads/2 第二批）

| 题目 | flag / 答案 | 方式 |
|------|------|------|
| wire0078.pcap | `flag{pr355_0nwards_a2fee6e0}` | USB HID 键盘解码（case01） |
| caidao.pcapng | `key{8769fe393f2b998fa6a11afe2bfcd65e}` | gz 提取 |
| 山东.pcapng | `flag{Manners maketh man}` | zip 提取 |
| misc1.pcapng | `flag{Rgb_dhskjadyhjksndjsagh}` | 像素图还原——**宽度因子 111 是钥匙**（case03） |
| A.pcapng | `flag{friday}`（密码 DBOQ6457） | 嵌套 zip 爆破（case05） |
| logs.pcapng | `flag{Find You!}` | zip flag.txt（case05） |
| 广西-flag.pcapng | `flag{4de36e4c7f941590b0f8ae2a74051f8e}` | 服务器响应明文（图片为占位素材） |
| Alpha-1.pcapng | 密码 `123456` | NetNTLMv1 爆破（case04） |
| capture.pcapng | 空密码 | NetNTLMv2 + HMAC 验证（case04） |
| wire0077.pcap | 完整解题：`P@ssw0rd987654e21$` + `dkk3jjfh5hjkd!!!!!` | PW/KL 邮件（case04；哈希损坏不可破） |
| **capture4.pcap** | **root/toor654321（FTP）+ administrator/admin654321（Telnet）** | 爆破序列还原（case06） |
| wireshark0051.pcap | FTP `admin/admin654321` → flag123.txt；Telnet root → webshell | 爆破序列还原（case06） |
| dump.pcapng | **`flag{harmony}`**（suictsr247/aaaa3b → /root/flag.jpg） | 爆破+文件提取（case06） |
| 不知名省赛.pcapng | **`flag{who_am_1}`**（图片内 ROT13 `synt{jub_nz_1}` + 解码脚本） | 爆破+图像文字（case06） |
| CaptureWH.pcapng | FTP `Z/qazwsx123` → exploit.c | 爆破序列还原（case06） |
| B2数据包.pcapng | FTP `Administrator/123.com`；华为 Telnet `Huawei/CNSkills@2020` | 爆破+设备登录（case06） |
| **hacker.pcapng** | 攻击者 192.168.8.126；凭据 admin/admin；one.asp 上传；IIS 7.5；内容 "Tomorrow" | 入侵行为分析（case07） |
| **hacker1.pcapng** | 开放端口 135/139/445/3389/49152-57；反弹 shell 9 条命令；系统 6.1.7601 | 入侵行为分析（case07） |
| **attack.pcapng** | vsftpd 2.3.4 笑脸后门（CVE-2011-2523）→ 6200 root shell；6 个预置 bash 后门；全端口扫描(固定源端口60099) | 漏洞利用链还原（case08） |
| **infiltration.pcapng** | Hydra 爆破成功：**administrator / YwQgj8eN**（Windows XP Telnet）；登录后 systeminfo/ipconfig/arp 收集 | 渗透链还原（case09） |
| **2021.pcapng** | **Redis AUTH 11aacc → 写 SSH 公钥到 /root/.ssh/authorized_keys → SSH root 登录** | Redis 提权链（case10） |
| **Bravo-1.pcapng** | **phpMyAdmin 写 shell2.php（密码 `cia`）+ load_file 读 flag.txt = `DCZ`** | SQL 滥用链（case11） |
| B.pcap | `flag1{5d41402abc4b2a76b9719d11017c592}` | 页面内 flag（已回填） |
| upload.pcapng | 无 flag（upload-labs 靶场练习流量） | — |

## 已定性（无 flag，缘由记录）

| 题目 | 性质 | 结论 |
|------|------|------|
| results(正常版本).pcap | 图片站 HTTP/FTP 流量（~170 张 jpg 正常下载） | 无隐写/无 flag（已抽检） |
| hahahhao.pcap | 乌云社区（www.wooyun.org）登录抓包（2015 时期） | 历史浏览流量，非 CTF |
| syc_security_system_traffic×3 | 安防设备小样本（30-100KB，成序列端口） | 设备协议流量，无应用层明文 |
| Emotet / Trickbot 样本 | **Emotet C2：TLS 加密通道（端口 447）** | IOC 类：6 个 C2 IP（185.90.61.116 / 195.123.220.86 / 195.123.238.36 / 5.53.125.13 / 195.123.221.104 / 195.123.221.178），无 flag |
| hack.pcapng | DNS 行为线索（此前已查） | 行为分析型，无 flag |

## 重要更正

- **capture4「flag{0y0w0g0q0y0}」为误报**：`{0y0w` 片段在 TLS 证书 DER 字节区、
  `0g0q0y0` 在二进制序列区，均为噪音拼接——已废弃该候选（case06 为正解）。

## 待分析队列

- **全部 52 题已完成首轮结论**（flag 已解 / 定性无 flag / IOC 提取三类皆有着落）
- 剩余深挖空间（可选）：
  - Emotet/Trickbot 载荷 URL 与欺骗文档 IOC 细提取（可从 HTTP 对象继续挖）

## 判断核训练经验（2026-10-12）

- **跨题"真实流量负样本"会毒化模型**：把真实恶意流量题（无 flag）的高分候选
  作为负样本加入训练集后，受控实验（留一组评估）显示 **'?' 组 AUC 0.956→0.779、
  solar 组 0.758→0.627**——明显退化，已回滚。
- **原因（kind 特征冲突）**：同一 kind（如"NetNTLM 响应 / 命令回显 / 片段"）
  在 CTF 题里经常**就是答案**，在真实流量里是噪音；模型在全局特征空间里无法
  区分两者（区分靠"题目语境"，不是 kind 本身）。跨题投喂会教出错误的全局先验。
- **结论**：负样本必须来自**同题语境**：正 = 命中答案的候选，负 = 同题其他高分候选
  （`lab/build_dataset.py` 按 `group` 分组建语料，训练时留一组评估即按此切分）。
  跨题样本不进训练集。
- 实验证据：/tmp/mta_compare.py 与 /tmp/mta_train.log（v220 实验）、
  /tmp/mta_train2.log（回滚后重训）。
  - Bravo-1 中 shell1（更早的 webshell）痕迹追踪（本题只捕获了 shell2 的写入）
  - B.pcap 的 flag1 系列（同题是否有 flag2+？未发现）
- 图片缓存区：全部复核完成（28 个 TLS 误报已清，见 `~/.devtools/ctfsweep/README.md`）
