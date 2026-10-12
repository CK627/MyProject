# case06: 双服务爆破攻击还原（FTP + Telnet）

## 元数据

```yaml
id: case06
title: 爆破攻击流量还原——FTP/Telnet 双服务弱口令 + 登录后操作追踪
type: brute-force / ftp / telnet / credential-recovery
source_files:
  - capture4.pcap（206KB，1368 包，攻击流量）
answers:
  FTP: "root / toor654321（成功登录，下载 123456.txt = helloworld）"
  Telnet: "administrator / admin654321（成功登录，获得 Windows shell）"
tools_used: [TCP 流重组, 攻击序列提取]
status: solved
```

## 识别特征

- 同一源 IP 对 21/23 端口的**密集短连接**（每次连接 = 一次口令尝试）
- FTP：`USER xxx / PASS yyy / 530 ...` 反复循环，直到 `230 ...`
- Telnet：`login: / password:` 提示反复出现
- 这是"攻击溯源/密码恢复"型题目（考题通常是：**成功登录的密码是什么？**）

## 分析步骤

### 1. 提取爆破序列（FTP）

从 TCP 流中还原尝试序列（按时间顺序）：

```
USER root / PASS aaaaaa      → 530
USER root / PASS aaaaab      → 530
USER root / PASS aaaaac      → 530
USER root / PASS aaaaa1      → 530
USER root / PASS aaaaa2      → 530
USER root / PASS admin123654 → 530
USER root / PASS admin654321 → 530
USER root / PASS toor654321  → 230 User logged in  ★成功
```

**关键点**：定位"最后一个 530 之后、230 之前"的 PASS 即为成功口令
（本次为 `toor654321`，注意 "toor" 是 "root" 的倒写）。

### 2. 提取爆破序列（Telnet）

尝试序列：aaaaaa → aaaaab → ... → admin123654 → **admin654321（★成功）**
成功标志（服务器响应流）：

```
Welcome to Microsoft Telnet Service
login: administrator
password: ...
*===============================================================
Microsoft Telnet Server.
*===============================================================
C:\Users\Administrator>
```

### 3. 登录后行为追踪（FTP 数据连接单独成流）

- `SYST → 215 Windows_NT`、`PORT`、`LIST` → 目录列表：
  **`05-06-19 07:05AM 10 123456.txt`**（一个 10 字节文件）
- 文件下载（FTP-DATA 流，端口 20）：内容 = **`helloworld`**
- Telnet 会话：登录后执行 `exit` 退出（无进一步操作）

## 解码/提取规则（工具化建议）

1. **爆破流量三步法**：①按五元组拆分短连接 ②按时间排序提取"尝试序列"
   ③找状态跳变点（530→230 / 失败→横幅）——**成功口令 = 跳变前最后一次尝试**
2. FTP-DATA 是**独立 TCP 流**（源端口 20 或动态端口）——目录列表与文件内容
   要在数据流里找，别只盯控制流
3. Telnet 成功标志：`*====...` 横幅 + shell 提示符（`C:\...>` / `$`）

## 同类变体判断指引

- 见到 `USER/PASS` 高频循环 = FTP 爆破；`login:` 循环 = Telnet 爆破
- 用"响应码跳变"而非"内容关键词"定位成功点（防止漏判）
- 成功口令集合就是题目的"答案"（NCCAW-2020 "FTP Attack" 等考题同套路）

## 批量战果（同批 8 个爆破/登录类 capture 全解，2026-10-12）

| 文件 | 服务 | 成功凭证 | 登录后动作 | 答案 |
|------|------|----------|-----------|------|
| capture4.pcap | FTP | root/toor654321 | 下载 123456.txt="helloworld" | 凭证 |
| capture4.pcap | Telnet | administrator/admin654321 | Windows shell | 凭证 |
| wireshark0051.pcap | FTP | admin/admin654321（第7次） | 下载 flag123.txt="helloworld" | 凭证 |
| wireshark0051.pcap | Telnet | root（Linux el7） | cd /var/www/html；写 webshell admin654321.php | 凭证 |
| CaptureWH.pcapng | FTP | Z/qazwsx123 | CWD /var/ftp；下载 exploit.c(7445B) | 凭证 |
| dump.pcapng | FTP | suictsr247/aaaa3b | CWD /root；**下载 flag.jpg → 内容 "harmony"** | **flag{harmony}** |
| 不知名省赛.pcapng | FTP | （本机回环抓包） | 下载 flag.py(ROT13 解码器) + **Stan's XX.png** | **flag{who_am_1}** |
| B2数据包.pcapng | FTP | Administrator/123.com | 下载 flag3.bin（纯诱饵"Fake Flag"×96） | 凭证 |
| B2数据包.pcapng | Telnet(华为) | Huawei/CNSkills@2020 | system-view | 凭证 |
| hacker.pcapng | FTP | anonymous 系列尝试 | readme.txt / one.asp（IIS aspnet 攻击链） | 待定 |
| hacker1.pcapng | FTP | — | （未见成功） | — |

**hacker.pcapng 细节**：目标 IIS 服务器（aspnet_client、iisstart.htm、welcome.png），
目录扫描特征 + one.asp（43B webshell？）——经典 IIS 攻击链。

## 关键补充经验

1. **ROT13 编码 flag 藏在图片里**（不知名省赛）：`synt{jub_nz_1}` →
   ROT13 → `flag{who_am_1}`。**同包内附有解码脚本 flag.py**（但脚本内样例
   输出是 `{flag_is_not_here}` 诱饵——真值在图片里）——"脚本样例≠真值，
   注意找真载体"。
2. **"Fake Flag" 诱饵文件**（B2数据包）：flag3.bin 全文为
   "Fake Flag In here"×96——遇到此类直读诱饵要检查**同目录其他文件**
   （Hint.bin 1.3GB 未完整下载）→ 判定本题答案为凭证而非文件内容。
3. **同系列题目文件互相印证**：capture4 与 wireshark0051 均为
   10.1.128.x 网段的"Kript_labs-2019"系列，成功密码均为 `admin654321`
   变体、下载文件名均含 "flag" 但内容为 "helloworld"——同系列出题模板。
4. **JPEG 提取显示**：FTP 数据用 ASCII 模式会带尾部 `\n`（`FFD9` 后多一字节），
   提取时裁到 `FFD9` 边界；macOS 可用 `sips` 转 PNG 查看。
