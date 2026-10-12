# case07：入侵行为分析（FTP 攻击链 + 反弹 shell）

**类型**：问答式取证（入侵行为分析）——"第 N 条命令 / 成功凭据 / 系统版本 / 开放端口"
**样本**：hacker.pcapng（FTP 上传 webshell 链）、hacker1.pcapng（反弹 shell 链）
**工具化**：`ctfsweep/core/session.py`（本轮新增，扫描时自动输出）

---

## 识别特征（一眼定性）

| 特征 | 判定 |
|------|------|
| 21 端口多个独立会话、USER/PASS 高频反复 | FTP 爆破/登录序列题 |
| 单会话出现 `Microsoft Windows [版本 x.x.x.x]` banner + `C:\...>` 提示符 | 反弹/交互 shell 会话 |
| 目标机主动连到攻击机高位端口（4444 等）后出现命令往返 | 反弹 shell（目标发起连接） |
| 大量 SYN 扫多端口、少量 SYN-ACK 返回 | 端口扫描（**开放端口 = 回 SYN-ACK 的端口**） |

## 分析步骤（通用五步）

1. **定端点**：找发起扫描/登录的 IP（本次：hacker.pcapng→192.168.8.126；hacker1→192.168.1.10）
2. **定开放端口**：过滤 SYN-ACK（`tcp.flags == 18 and src==目标`）→ 应答端口即开放端口
3. **登录/命令序列**：合并控制流双向（按包号时序）→ 逐条命令 + 成功判定（响应码 230/530）
4. **载荷内容**：FTP-DATA 通道取文件；HTTP 响应取 webshell 回显
5. **汇总回答**：IP / 端口 / 用户名 / 命令 / 版本 / 获取内容

---

## 样本一：FTP 攻击链（hacker.pcapng）

### 结论（逐问）

| 问题 | 答案 | 依据 |
|------|------|------|
| 攻击者 IP | `192.168.8.126` | 扫描与登录发起方 |
| 开放端口（最小） | `21` | SYN-ACK 端口 = [21, 80, 135, 139, 445, 3389, 49152-49157]，最小 21 |
| 初次尝试用户名 | `anonymous` | 第 1 个会话 USER anonymous |
| 成功登录用户名 | `admin` | 第 4 个会话 USER admin/PASS admin → 230 |
| 第 3 条命令 ⚠️ | `LIST`（全命令计数）/ `STOR one.asp`（仅文件操作计数） | 见下方"计数口径" |
| 利用的应用版本 | `Microsoft-IIS/7.5` | HTTP 响应头 Server |
| 获取的内容 | `Tomorrow` | one.asp（含 `#include file="../../flagvalu.txt"`）访问回显 |

### 登录尝试序列（4 个独立会话）

```
① USER anonymous / PASS (空)     → 530 失败
② USER root      / PASS :)       → 530 失败
③ USER root:)    / PASS (空)     → 530 失败
④ USER admin     / PASS admin    → 230 成功 ✓
```

### 成功会话命令序列（10 条，含协议命令）

```
SYST → PORT → LIST → CWD Web → PORT → LIST → PORT → STOR one.asp → PORT → LIST
```

- 黑客上传 `one.asp`（内容：`<!-- #include file="../../flagvalu.txt" -->`）
- 访问 `GET /one.asp` 回显 = flagvalu.txt 的内容（8 字节）：`Tomorrow`

### ⚠️ 计数口径问题（重要）

"第 3 条命令"存在两种考场答案版本，因为计数口径不同：

| 口径 | 1 | 2 | 3 |
|------|---|---|---|
| 全部命令 | SYST | PORT | **LIST** |
| 剔除协议命令(SYST/PORT/CWD) | LIST | CWD Web | **LIST**（另一路径） |
| 仅文件操作(LIST/STOR) | LIST | LIST | **STOR one.asp** |

→ 分析时必须把**完整命令序列**都列出来，而不要只报一个数——不同考场 key 都出现过。

## 样本二：反弹 shell 链（hacker1.pcapng）

### 拓扑

- 攻击者 `192.168.1.10` ↔ 目标 `192.168.1.100`（Windows 7 SP1）
- 扫描：1000 个端口 SYN 探测；SYN-ACK 开放 = `135, 139, 445, 3389, 49152-49157`
- 反连：目标 `:49163 → 攻击者 :4444`（攻击端监听 4444）

### 反弹 shell 命令记录（9 条，完整）

```
whoami → net user → pwd → chcp 437 → dir → ls
       → net user asdf asdf /add
       → net localgroup administrators asdf /add
       → shutdown -s -t 0
```

### 关键回显

| 命令 | 回显 |
|------|------|
| 系统 banner | `Microsoft Windows [版本 6.1.7601]`（= 版本号 6.1.7601） |
| whoami | `win-k1unj4kn7qj\administrator`（主机名 WIN-K1UNJ4KN7QJ） |
| net user | 用户列表：a / Administrator / b / backdoor / c / Guest |
| pwd | `'pwd' 不是内部或外部命令`（Linux 命令在 Windows 上失败） |
| dir | 桌面文件：shell.exe、webshell.php、phpStudy_64.zip、KMSpico 等 |
| net user asdf asdf /add | The command completed successfully（建后门账户） |

攻击者行为链：**whoami 侦察 → net user 枚举 → 尝试 Linux 命令 → 建后门用户 asdf → 提权管理员 → 关机**。

---

## 工具化沉淀（已实现）

新增 `ctfsweep/core/session.py`，扫描时自动输出（并作为候选入库）：

```
[FTP会话] 192.168.8.126:50308 → 192.168.8.106:21 登录尝试 1 次: admin/admin
  成功凭据: admin / admin
  命令序列(10): SYST → PORT … → STOR one.asp → … → LIST
[交互会话] 192.168.1.100:49163 ↔ 192.168.1.10:4444（Windows 6.1.7601，9 条命令）
  命令: whoami → net user → pwd → chcp 437 → dir → ls → … → shutdown -s -t 0
  系统版本: 6.1.7601
```

实现要点：
- **FTP**：客户端/服务端双向按包号合并时序；`230`=成功、`530`=失败；成功后命令全部入列
- **Shell**：`Microsoft Windows [版本 x]` banner 或 `C:\..>` 提示符触发；
  按提示符切分 → 每条 = 命令回显行 + 输出；版本号正则 `(\d+(?:\.\d+)+)`
- 输出发现（0.8-0.9 分）自动进候选与留存区

## 同类变体判断指引

- 见到 `USER/PASS` 循环 + `530` 重复 = FTP 爆破；`230` 即成功点
- 见到 4444/5555/1337 等监听端口 + 命令往返 = 反弹 shell（**目标主动外连**方向别搞反）
- 见到大量 SYN 无应答 = 扫描噪音；**只把 SYN-ACK 的端口计为"开放"**
- 系统版本：`ver` 命令回显 / banner（`6.1.7600`=Win7 未打补丁、`6.1.7601`=Win7 SP1）
- 计数类问题（第 N 条）：**先列完整序列再计数**，避免口径争议
