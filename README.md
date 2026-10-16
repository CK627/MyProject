# ctfsweep - CTF / 应急响应取证扫描器

> 面向 CTF 与应急响应的取证扫描工具：把流量包（pcap / pcapng）、Windows 事件日志（evtx）、
> 注册表（.reg）里"可疑的东西"一次性翻出来，并按**置信度分级**输出——高置信可直接核验，
> 低置信留作人工排查线索。
>
> 零依赖（纯标准库，Python 3.8+），`ctfsweep <文件或目录>` 即用；支持 macOS / Linux / Windows。

## 安装

### 命令行一键安装

macOS / Linux（安装后自动刷新当前终端，无需手动 source）：

```bash
source <(curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/CtfSweep/installer/install.sh)
```

装成 devtools 副本（与同仓库的 jtool / ptool 同规）：**默认系统级** → macOS
`/Library/devtools/ctfsweep`、Linux `/usr/local/devtools/ctfsweep`，需要时在脚本里提示
管理员密码；代码全在安装目录，PATH 上只多一个无后缀的 `ctfsweep`，之后用
`ctfsweep update` 更新。

> 只想装给当前用户（不需要密码，落到 `~/.devtools/ctfsweep`）：在命令前加
> `CTFSWEEP_USER=1`。

装完重开终端（`source <(...)` 的形式会自动刷新当前终端），然后：

```bash
ctfsweep <文件或目录> [选项]
ctfsweep update               # 更新到最新版（--check 只比对版本，不落盘）
```

Windows（PowerShell，与 ptool / jtool 同规的一键安装：下载快照 → 装到
`%USERPROFILE%\.devtools\ctfsweep` → 把 `bin` 挂进用户 PATH，**不需要管理员**）：

```powershell
irm https://raw.githubusercontent.com/CK627/MyProject/CtfSweep/installer/install.ps1 | iex
```

已下载源码快照/仓库时也可以右键运行 `installer\windows\install.bat`（同一个安装动作）。
卸载用 `ctfsweep uninstall -y`，或右键 `installer\windows\uninstall.bat`：摘掉 PATH 项、
删掉功能文件，**扫描缓存一律保留**。Windows 需要 Python 3.8+ 在 PATH 上（`python` 或
`python3` 均可）。

### 国内镜像（无需 VPN）

GitHub 的 `raw` / `api` 域名在国内不保证可达。镜像服务器在国内，产物与 GitHub 分支逐字节相同：

```bash
source <(curl -fsSL http://101.132.165.98/dist/ctfsweep/install.sh)
```

```powershell
# Windows
irm http://101.132.165.98/dist/ctfsweep/install.ps1 | iex
```

安装脚本**先访问镜像，拿不到再回退 GitHub**，`ctfsweep update` 同样如此。换源用环境变量：

```bash
CTFSWEEP_MIRROR=https://mirror.example.com/ctfsweep source <(curl -fsSL .../install.sh)
CTFSWEEP_MIRROR=none source <(curl -fsSL .../install.sh)   # 强制只走 GitHub
```

### macOS / Linux（源码安装）

```bash
cd /path/to/CtfSweep
./installer/install.sh                    # 默认系统级（需要时提示管理员密码）
CTFSWEEP_USER=1 ./installer/install.sh    # 只装给当前用户 → ~/.devtools/ctfsweep
```

安装完成后执行 `source ~/.zshrc`（或 `source ~/.bashrc`）或重新打开终端。

### Windows / 不安装也能跑

纯标准库、Python 3.8+，Windows 下不需要安装：

```bash
python3 -m ctfsweep <文件或目录> [选项]   # 项目根目录内
./bin/ctfsweep.sh <文件或目录> [选项]     # 仓库启动器（macOS / Linux）
```

Windows 运行 `bin\ctfsweep.bat <文件或目录>`，或把项目根目录加入 `PYTHONPATH`
后使用 `python -m ctfsweep`。

> ⚠️ **别把仓库的 `bin/` 直接加进 PATH**。那是**素材目录**：`ctfsweep.sh`（macOS / Linux）
> 与 `ctfsweep.bat`（Windows）靠扩展名区分系统。整体挂上 PATH 后，zsh 的命令名补全走
> `$commands` 哈希，而**这个哈希不检查可执行位**——macOS 上根本跑不起来的 `.bat`
> 也会进候选，`ctfsweep<TAB>` 就同时列出 `ctfsweep` 和 `ctfsweep.bat`。
> 安装形态正是为此设计的：真实脚本住在安装目录的 `lib/ctfsweep.sh`，
> PATH 上的 `bin/ctfsweep` 只是指向它的软链，全程只有**一个**名字。

### 安装后的目录布局

```
/Library/devtools/ctfsweep/          ← 默认（Linux: /usr/local/devtools/）；
                                     CTFSWEEP_USER=1 则装在 ~/.devtools/ctfsweep/
├── bin/ctfsweep -> ../lib/ctfsweep.sh   ← PATH 上唯一的名字（软链）
├── lib/ctfsweep.sh                      启动器实体
├── lib/ctfsweep/                        Python 包
├── lib/models/                          判断核模型（model.ctfj + train_config.json）
├── config/ completions/ VERSION
└── uninstall  deploy.sh  shell-setup.sh
```

数据目录**与安装位置无关**，恒定在家目录（`update` 与 `uninstall` 都不碰它；
用户级安装时它与上面的安装根是同一个目录）。它（**只有扫描缓存**）：

```
~/.devtools/ctfsweep/
└── cache/         每次扫描的结果缓存（一次运行一个目录）
```

### 数据与模型（模型随版本 / 数据目录只放缓存）

| 内容 | 位置 | 说明 |
|------|------|------|
| **判断核模型 + 训练配置** | 安装目录 `lib/models/`（未安装时是项目内 `models/`） | 训练产物与超参数，随版本一起发布；升级模型参数无需改代码 |
| **扫描缓存** | `~/.devtools/ctfsweep/cache/<运行名>-<路径哈希6位>/`（Windows 同形：`%USERPROFILE%\.devtools\ctfsweep\cache\…`） | `1.txt`/`2.txt`/`3.txt` 高/中/低分档明细 + `<运行名>_cache.txt` 本次运行的完整报告。**一次运行一个目录**（目录扫描时明细每行带 `← <相对路径>` 标出来源），**每次扫描都尝试写**（默认模式与 `-q` 内容相同；同一目标已有缓存则不覆盖、提示先 `clear`），跑完即可回看 |
| 配置文件（可选） | `~/.devtools/ctfsweep/ctfsweep.conf` | 扫描行为配置 |

> ⚠️ **缓存永不自动删除**：`ctfsweep update` 只覆盖功能文件，`ctfsweep uninstall` 也只删功能
> 文件与 shell 接线——`cache/` 一律保留（想清就在**卸载之前** `ctfsweep clear`，卸完命令
> 就没了）。卸载后系统级的 devtools 根（`/Library/devtools`、`/usr/local/devtools`）只在
> 空的时候才收掉，里面还有 jtool/ptool 之类就原样留着。
>
> 模型是**离线统一训练**的产物，随版本发布；用户要自己重训（例如用自己的题库），
> 用仓库里的 `python3 lab/train.py`——运行时命令行**不提供**任何训练/标注入口。

## 更新

```bash
ctfsweep update               # 拉取最新源码快照并重装（镜像优先，回退 GitHub）
ctfsweep update --check       # 只比对版本，不落盘
```

`update` 会读镜像上的 `VERSION` 比对，只在版本更高（或检测到安装残缺）时才下载重装；
下载到的快照版本号与远端对不上（镜像半发布）就拒绝落盘。
换源：`CTFSWEEP_MIRROR=<url>`；`CTFSWEEP_MIRROR=none` 只走 GitHub；
`CTFSWEEP_GITHUB=none` 只认镜像（离线环境用）。

> **旧版（≤ 1.8.10）无法自我更新**：那一版的 `update` 只打印 `git pull` 提示，不认识这套
> 更新流程。老机器第一次必须手动装一次（跑上面的「命令行一键安装」），之后 `ctfsweep update`
> 才会走真更新。系统级安装下更新会提示管理员密码（落盘要写 `/Library/devtools`）。

## 卸载

```bash
ctfsweep uninstall            # 带确认提示（-y 跳过）
./installer/uninstall.sh      # 等价脚本（用户级 + 系统级一起清）
```

> 默认是系统级安装，所以 `./installer/uninstall.sh` 需要 `sudo` 才能删掉
> `/Library/devtools/ctfsweep`（脚本会明确告诉你哪一项没权限，重跑一次带 sudo 即可）。
> 卸载只删功能文件与 shell 接线，**扫描缓存一律保留**（要清就在卸载**之前** `ctfsweep clear`）；
> 系统级的 devtools 根只在空时收掉（里面还有 jtool/ptool 就留着）。

## 功能特性

### 输入与解析

- 📦 三种输入通吃：
  - **pcap / pcapng**：纯 Python 自解析（不依赖 Wireshark / scapy / dpkt）
  - **evtx**（Windows 事件日志）：字节级 UTF-16LE 扫描，免对齐、免解析器，损坏区块也不怕
  - **.reg / 任意文本**：自动识别 UTF-16 编码
- 🌐 链路层支持：Ethernet / VLAN / PPPoE / Raw-IP / Linux-SLL / SLL2 / NULL；
  pcapng 支持 SHB / IDB / EPB / SPB / 老式 PB 与多接口
- 🧵 逐包独立扫描 + **按 TCP 序号重组**：带序号的流按 seq 合并（重传/重叠去重、乱序恢复、
  流尾填充剔除），**提取出的文件字节与 Wireshark 重组一致**（可直接比对哈希）；无序号数据退化按包序拼接
- 🖧 **主机识别**：ARP + Ethernet 汇总 **IP ↔ MAC 主机表**（挂多个 IP 的 MAC 自动折叠为
  路由器/网关提示）；DHCP 选项 12 与 NBNS 名称自动关联主机名（"感染主机 MAC/主机名"类问题直接可答）

### 线索扫描

- 🚩 明文 flag 直接命中（支持 `flag/ctf/key/sec/solar/admin` 等多种前缀）
- 🔓 **hex / base64 多层解码链**：自动套娃解码（默认 3 层），命中关键词或 flag 结构才记录
- 🌐 **DNS 外带解码**：DNS 子域名自动 base64 解码（防 DNS 隧道外泄题）
- 🧩 **花括号片段探测**：分段 flag 题的核心线索（如 `{krjl424` / `zlmqu458xktq}`），
  并给出**启发式拼接尝试**；跨文件自动汇总全局片段池（按文件标注来源）
  - 🚫 自动剔除二进制噪音：GUID 花括号 / 路径后缀拼贴（`setupetw.dll55e3}`）/ 乱码密集区 /
    词内误报（`FolderValueFlags`、`create_pdo_flag`、`msctf_`）等
- 📦 **"加壳"识别**：txt / 响应体内容是 flag 本体但不带 `flag{}` 外壳时给出加壳建议
- 🔑 关键词上下文扫描（默认 `flag,ctf`，`-k` 可扩展；UTF-16LE / ASCII 双模式）

### AD / 域协议取证（Kerberos · NTLM · LDAP）

AD 类题目（Kerberoasting / AS-REP Roasting / NetNTLM 中继 / LDAP 明文绑定）的流量里
**没有 `flag{}` 明文**，也不走 HTTP 外带，纯字符串扫描必然零命中。这块能力直接把域协议里的
"答案素材"解出来，并转成 hashcat / john 能吃的格式：

- 🎫 **Kerberos（TCP/UDP 88）**：解析 AS-REP / TGS-REP，给出域、账号、SPN、etype、票据长度
  - `etype 23 (RC4)` → 直接产出 `$krb5asrep$23$...`（hashcat -m 18200）/ `$krb5tgs$23$...`（-m 13100）
  - `etype 17/18 (AES)` → 标注需字典（-m 19700 / 19900），不明示为"可爆破"
- 🔐 **NTLMSSP（SMB / HTTP / 任意流）**：按连接配对 challenge 与响应，产出
  **NetNTLMv2**（-m 5600）/ NetNTLMv1（-m 5500），未配到 challenge 时至少给出 `域\账号@主机`
- 🔑 **LDAP simple bind（389 / 3268）**：明文绑定口令（0.93 高置信）
- 🗂️ 额外打印【AD / 域渗透线索】区块：域、账号清单、SPN 清单、票据与破解建议

```text
【AD / 域渗透线索】
  域: WIRE.COM
  账号(2): Administrator、kanna.seto
  SPN(3): krbtgt/WIRE.COM、Administrator、host/dc01.wire.com
  票据: AS-REP kanna.seto  etype 18 (AES256)  cipher 264B  AES：hashcat -m 19700/19900 需字典
  NetNTLMv2: kanna.seto
    └ kanna.seto::wire.com:e9b597a6e03a5122:c4ec074163bee82d9f829d1aa22de185:0101...
```

### HTTP 深度分析

- 📋 请求序列（带时间戳）：目录扫描次序、登录、上传等操作一览
- 📝 **POST 字段摘录**：form-urlencoded / multipart（文件名）/ **JSON 体**（登录凭证、上传名、木马参数）
- 🔁 **请求↔响应事务配对**：命令回显、接口短文本直接可读（RCE / webshell 场景）
- 🪪 **JWT 自动识别与解码**：header / payload 直接展开（伪造身份类题目的答案就在 payload 里）
- 🔍 **环境变量 / 密钥回显侦测**：`WEBUI_SK=...`、`PWD=...` 等一条不落

### 会话 / 协议提取（FTP · 邮件 · 反弹 shell）

针对"入侵行为分析"类问答式取证题，直接给出可作答的字段：

- 📂 **FTP（21）**：登录尝试序列（USER/PASS 失败与成功）、**成功凭据**、登录后的命令序列；
  识别 vsftpd 2.3.4 笑脸后门（CVE-2011-2523）
- 📧 **邮件（SMTP/ESMTP 25 / 587 / 465）**：会话数、目标服务器数、**客户端自报主机名
  （HELO/EHLO，僵尸网络/群发的关键指纹）**、明文投递信封（`MAIL FROM` → `RCPT TO`）与主题。
  正文被 `STARTTLS` 加密时会**如实标注"内容不可解读"**——会话形态本身就是线索，
  不会因为正文加密而整份文件零输出
- 🐚 **反弹 / 交互 shell**：Windows cmd 与 Linux shell 的命令记录与回显、系统版本、
  暴露的 bash bind shell、Hydra/Medusa 爆破结果、Redis 写 SSH 公钥提权链

同一份证据在多个会话里重复出现时（FTP 爆破的 11 次登录），**前 N 项发现会自动按
（类型 + 证据）去重**，不会让同一行占满整份线索列表。

### 文件提取（`--extract`）

- 🔪 从 TCP 会话与 UDP 载荷中按文件签名**雕刻文件**：ZIP / PNG / JPG / GIF / PDF / GZ / RAR / 7Z /
  **PE(.exe) / OLE2(.doc) / ELF**（自动裁剪边界、哈希去重、合法性校验）
- 📏 **HTTP 响应体精确切分**：雕刻按"逐响应体"进行（Content-Length 精确切片 / chunked 自动解码）
  —— 下载文件按落盘尺寸原样产出，**SHA-256 可直接与官方报告/IOC 比对**
- 🧬 **页面内嵌 base64 载荷**：HTML/JS 下载页里的超长 base64 段自动解码还原
  （Word/EXE/ZIP 等带文件签名者；实测与官方哈希逐字节一致）
- 🗜️ **zip 自动深挖**：列条目 → 逐条内容扫描 → **嵌套 zip 递归** → 小文本条目预览
- 🔐 **加密 zip 自动尝试口令**：空口令 → 常用口令表 → `--pwd-file` 字典 → **流量采集口令池**（含大小写/后缀变体）
- 👻 **"假加密"绕过**：中心目录标记加密、本地头实际未加密的 zip，直接解析数据区（CRC 校验后取内容）
- 📄 GZ 自动解压扫描；提取到的内容全部并入置信度报告

### 输出与置信度

- 🎯 **置信度分级**（每条结果带 `[分数 级别]`，按分数排序）：

  | 分数 | 级别 | 含义 |
  |------|------|------|
  | 0.93 | 高 | LDAP 明文绑定口令 |
  | 0.90 | 高 | 可离线爆破的 RC4 Kerberos 票据（AS-REP / TGS） |
  | 0.85 | 高 | NetNTLMv1/v2 响应（可直接交给 hashcat） |
  | 0.85 | 高 | 邮件投递信封（`MAIL FROM` → `RCPT TO` + 主题；**≤8 封**时逐封列出） |
  | 0.55 | 中 | 邮件投递形态（**>8 封**只报发件域/收件域分布 + 3 个样例，不逐封刷屏） |
  | 0.97 | 高 | 明文完整 flag |
  | 0.95 | 高 | 解码后得到完整 flag（hex/base64/DNS 等） |
  | 0.75 | 中 | 内容"加壳"候选（疑似 flag 本体） |
  | 0.72 | 中 | JWT 令牌（payload 已解码） |
  | 0.65 | 中 | 未闭合片段（分段 flag 前半截） |
  | 0.62 | 中 | 命令回显 / 环境变量密钥回显 / AES Kerberos 票据（需字典） |
  | 0.55 | 中 | 域账号 / SPN 清单（AD 线索） |
  | 0.60 / 0.55 | 中 | 裸花括号片段 `{xxx` / `xxx}` |
  | 0.55 | 中 | 邮件会话形态（会话数 / 自报主机名 / 加密会话数） |
  | 0.45 | 低 | DNS 查询名 |
  | 0.45 | 低 | 服务发现类 DNS 查询（SRV/`wpad`；折叠成一行按域名计数，域外域名显形） |
  | 0.42 | 低 | 接口短文本响应 |
  | 0.40 | 低 | 关键词上下文 |

- 🧾 输出结构：逐文件报告（**按级别分区换行**：高置信 / 中置信 / 低置信）→ 拼接建议 →
  **候选汇总**（flag 候选 / 非 flag 证据分组，非 flag 文件明确提示"未发现 flag 形状候选"）
  → 全局片段池（按行标注来源）→ 扫描统计（高/中/低条数分区）
- 🎛️ `--min-score` 过滤、`--limit` 截断、`--depth` 控制解码深度、`--no-decode` 关闭解码
- 🛡️ 单文件出错不中断，继续扫下一个

### 判断核（`--judge` 打分；模型随版本发布）

**轻量判断网络**：对扫描候选做"答案相关性"打分（`p=0.9x`），用于人工核验前的排序与降噪。

- 🧠 **纯 Python 手写 MLP 集成**（默认 5 个成员，140 维特征输入；模型为 `.ctfj` 二进制单一格式）——零依赖、完全离线、推理确定性
- 🧩 **模型随项目版本发布**：`models/model.ctfj`（与代码同步版本管理，可单独升级/替换），安装时随包部署到 `lib/models/`
- ⚙️ **超参数独立于代码**：`models/train_config.json`（网络结构 / 学习率 / 种子 / 轮数等）——调参无需改代码
- 🔌 无模型时工具行为与之前完全一致；`--judge` 时输出 `p=` 分与【判断核·重点候选】

```bash
ctfsweep file.pcap --judge     # 扫描时给候选打 p 分，并列出模型排序的重点候选

# 自己重训（离线脚本，不在运行时命令里）：留一组评估 + 全量重训 + 保存模型
python3 lab/build_dataset.py   # 从题库构建 lab/dataset.jsonl（或 lab/data_generator.py 合成）
python3 lab/train.py           # → models/model.ctfj
python3 lab/train.py --epochs 500
```

> 运行时**不提供**训练/标注子命令（自学习闭环已整体移除）：模型由作者离线统一训练后随
> 版本发布，装机与日常使用都只做推理打分。`lab/` 下的脚本是仓库内的实验工具，**不随安装提供**。
>
> 诚实边界：判断核的"推理"是**统计归纳**（形状 / 上下文 / 模式），不是语义理解——
> 开放语义推理仍交给 LLM / 人工；它的定位是"扫描器找全 → 判断核排序 → 人最终确认"。

### 工程特性

- ⚡ **零第三方依赖**：任意 Python 3.8+，无需 pip install 任何东西
- 📁 目录递归扫描；260MB 注册表全量 10 秒内、常规抓包亚秒级
- 🔁 自助管理：`ctfsweep update`（真更新，镜像优先）/ `install` / `uninstall` / `config`（运行信息含缓存占用）/ `clear`（清空缓存）/ `help`
- 🧰 完整工程配套：CLI 包装器、shell 补全、配置文件、冒烟测试、CI

## 使用方法

### 快速开始

```bash
# 扫描一个抓包（默认输出 >= 0.40 的全部候选）
ctfsweep capture.pcap

# -f 与位置参数写法等价（命令名优先：要扫名叫 update 的文件就用 -f 或 ./update）
ctfsweep -f capture.pcap

# 只看高置信结果（直接要 flag 时）
ctfsweep capture.pcap --min-score 0.85

# 扫描并提取流量中的文件（含加密 zip 自动尝试口令）
ctfsweep capture.pcap --extract

# 批量扫描整个目录（含 evtx / reg / 文本）
ctfsweep ./logs/

# 用 -F 指定文件夹（与位置参数传目录等价，语义更直观；适合"整个项目=一个文件夹"的日志包）
ctfsweep -F ./logs/

# 事件日志搜索特定关键词
ctfsweep Security.evtx -k flag1,flag2,flag3
```

### 命令行选项

| 选项 | 说明 |
|------|------|
| `<文件或目录>` | 必填（或用 `-f` / `-F` 指定）。支持单个文件或目录递归 |
| `-f, --file F` | 指定要扫描的文件（等同位置参数，两种写法都行） |
| `-F, --folder D` | 指定要扫描的文件夹（递归扫描其中全部文件，适合"整个项目就是一个文件夹"的日志包） |
| `-k, --keywords` | 追加关键词（逗号分隔），默认 `flag,ctf` |
| `--min-score N` | 只显示置信度 ≥ N 的结果（默认 0.40，设 0 显示全部） |
| `--no-decode` | 关闭 hex / base64 自动解码 |
| `--depth N` | 解码链最大深度（默认 3，即 hex/base64 可反复套娃） |
| `--limit N` | 每个文件最多输出条数（默认 50，按置信度排序后截取） |
| `-q, --brief` | 精简输出：控制台只打「分档统计块」（高/中/低 + 缓存文件路径；目录扫描时逐文件只报条数，路径统一在末尾打一次）。注意**缓存两种模式都写**（默认模式扫描完还会在末尾打印本轮写出的缓存目录），`-q` 只改变控制台是否上屏。缓存位置 `<数据目录>/cache/<运行名>-<哈希>/`（1.txt / 2.txt / 3.txt / `<运行名>_cache.txt`），目录名带**完整路径**的短哈希，同名不同目录的两次运行不会互相覆盖。该缓存只增不减且**同一目标不覆盖**（已有缓存时本次只提示、不再落盘），`ctfsweep config` 报占用，清理用 `ctfsweep clear` |
| `--extract` | 从流量中提取文件并按内容扫描（详见下文） |
| `--extract-dir D` | 指定提取输出目录（默认 `<抓包名>_extracted/`，与抓包同目录） |
| `--pwd-file F` | 附加口令字典文件（每行一个，用于加密压缩包） |
| `--judge` | 用本地判断核模型对候选打分（`p=…` + 重点候选排序；模型随版本发布，重装或离线训练后替换） |
| `--config F` | 指定配置文件（默认读取 `~/.devtools/ctfsweep/ctfsweep.conf`） |
| `--version` | 显示版本 |
| `-h, --help` | 显示帮助 |

### 子命令（管理）

| 子命令 | 说明 |
|--------|------|
| `ctfsweep update [--check]` | 拉取最新源码快照并重装（镜像优先，回退 GitHub）；`--check` 只比对版本不落盘 |
| `ctfsweep install` | 显示安装方式（一键 / 镜像 / 本地源码，装到 devtools 目录） |
| `ctfsweep uninstall [-y]` | 卸载安装副本并摘除 shell 接线（**扫描缓存保留**；`-y` 跳过确认） |
| `ctfsweep config` | 显示运行信息、数据目录与生效配置（含扫描缓存占用与可删路径） |
| `ctfsweep clear [名称] [-y]` | **清空扫描缓存**：不给名称就清空数据目录下的全部内容（含各题图片缓存），给名称（如 `ctfsweep clear capture4.pcapng`）只清那个项目；保留 `ctfsweep.conf`；`-y` 跳过确认 |
| `ctfsweep help` | 显示帮助 |

> 子命令名（update / install / uninstall / clear / config / help）优先于文件路径解析——
> 若要扫描恰好同名的文件，请用 `-f 文件名` 或 `./文件名`。
>
> **没有训练/标注子命令**：`train` / `label` / `auto-label` / `mark` / `learning` / `gen-data`
> 已从运行时整体移除（自学习闭环废弃，模型离线统一训练）。要自己重训就进仓库跑
> `python3 lab/train.py`。

### 扫描缓存（每次扫描自动写入）

**每次扫描都会把结果写进缓存**，跑完即可回看，不必重扫：

```bash
ctfsweep /path/to/logs/              # 扫描（默认模式：报告上屏 + 缓存落盘）
# 结束后控制台会打印本轮写出的缓存目录（整次运行只有一个）：
#   【扫描缓存】本次 N 个文件，报告与分档明细已写入:
#     ~/.devtools/ctfsweep/cache/logs-9f2c1a/
#     完整报告见 logs_cache.txt；占用与清理见 ctfsweep config

ctfsweep /path/to/logs/ -q           # 精简输出：控制台只留分档统计块，明细照旧落盘
ctfsweep config                      # 报出缓存占用与路径
ctfsweep clear                       # 清空缓存（确认后执行；-y 跳过确认）
```

**一次运行一个目录** `cache/<运行名>-<路径哈希6位>/`：运行名取扫描根目录名（单文件取
文件名去扩展名），哈希取完整路径——同名不同目录的两次运行各成一份、互不覆盖。
`1.txt`/`2.txt`/`3.txt` 是**本次全部文件**的分档明细（目录扫描时每行带 `← <相对路径>`
标出来源），`<运行名>_cache.txt` 是本次运行的完整报告 + 汇总尾段。

> 为什么按运行而不按文件分：`-f` 单文件时两者重合，但 `-F 项目/` 扫整个项目会摊出十几个
> `<文件名>-<哈希>` 平铺目录，`sub1/a.pcap` 与 `sub2/a.pcap` 的目录名肉眼还分不出对应关系。
> 同一个目标**不会**覆盖：该运行目录里已经有文件时，这次扫描只打印
> `缓存目录：<目录>/ 目录有文件，请使用 clear 清除`，**不往盘上写第二份**（报告照常上屏）。
> 想重扫并留下新报告，先清掉它：`ctfsweep clear <运行名>`（如 `ctfsweep clear capture4`）。

**缓存只增不减**（`update` / `uninstall` 都不碰，也不自动过期）：需要腾地方时用
`ctfsweep clear` —— 它清空数据目录下的**内容**（`cache/` 结果缓存 + 各题图片缓存），
保留目录本身与配置文件 `ctfsweep.conf`，程序本体不受影响；不带 `-y` 时会先列出要删的
条目与占用、等一次确认（非交互环境必须显式加 `-y`）。

只清一个项目就带上名称：`ctfsweep clear capture4.pcapng` 会删掉数据目录下的
`capture4.pcapng/`（提取的图片缓存）与 `cache/capture4-<哈希>/`（那个文件的扫描缓存），
其他项目一个不动——这也是重扫某个项目前的标准动作。
`-q` 与默认模式写出的缓存**内容相同**——`-q` 只决定控制台是否上屏。

### 典型场景

```bash
# DNS 外带：直接看 DNS 查询名里的 base64 子域名
ctfsweep exfil.pcap --min-score 0.4        # 0.45 DNS查询 + 0.95 base64解码 两条线索

# webshell / RCE：看 HTTP 事务摘要里的命令回显
ctfsweep rce.pcap                          # [HTTP事务摘要] 区段

# 分段 flag：看片段探测与拼接建议
ctfsweep Security.evtx -k flag1,flag2      # [拼接建议] 区段

# 加密压缩包：跨文件采集口令池自动尝试
ctfsweep ./all_captures/ --extract         # 预扫全部抓包采集候选口令
ctfsweep secret.zip --pwd-file rockyou.txt # 或用自定义字典（zip 会先解压扫描）

# 判断核：对候选按"答案相关性"排序（模型随版本发布，直接加 --judge）
ctfsweep Security.evtx --judge              # 输出 p= 分 + 【判断核·重点候选】
```

## 命令速查表

| 命令 | 说明 | 示例 |
|------|------|------|
| `ctfsweep <文件或目录>` | 扫描（pcap · evtx · reg · 文本 · 内存镜像 …） | `ctfsweep capture.pcap` |
| `ctfsweep -f <文件>` | 指定要扫描的文件（等同位置参数） | `ctfsweep -f dump.raw` |
| `ctfsweep -F <目录>` | 递归扫描整个目录 | `ctfsweep -F ./logs/` |
| `ctfsweep -k <关键词>` | 追加关键词（逗号分隔） | `ctfsweep a.pcap -k flag1,flag2` |
| `ctfsweep --min-score N` | 只显示置信度 ≥ N 的结果（默认 0.40） | `ctfsweep a.pcap --min-score 0.85` |
| `ctfsweep --no-decode` | 关闭 hex / base64 自动解码 | `ctfsweep a.pcap --no-decode` |
| `ctfsweep --depth N` | 解码链最大深度（默认 3） | `ctfsweep a.pcap --depth 5` |
| `ctfsweep --limit N` | 每个文件最多输出条数（默认 50） | `ctfsweep a.pcap --limit 200` |
| `ctfsweep -q` | 精简输出（明细在扫描缓存里） | `ctfsweep -F ./logs/ -q` |
| `ctfsweep --extract` | 提取流量中的文件并扫其内容 | `ctfsweep a.pcap --extract` |
| `ctfsweep --extract-dir D` | 提取输出目录 | `ctfsweep a.pcap --extract --extract-dir out/` |
| `ctfsweep --pwd-file F` | 附加口令字典（用于加密压缩包） | `ctfsweep a.pcap --pwd-file pw.txt` |
| `ctfsweep --judge` | 用判断核模型对候选打分 | `ctfsweep a.pcap --judge` |
| `ctfsweep --config F` | 指定配置文件 | `ctfsweep a.pcap --config my.conf` |
| `ctfsweep update [--check]` | 拉取最新快照并重装（`--check` 只比对版本） | `ctfsweep update --check` |
| `ctfsweep install` | 显示安装方式（装到 devtools 目录） | `ctfsweep install` |
| `ctfsweep uninstall [-y]` | 卸载（扫描缓存保留） | `ctfsweep uninstall -y` |
| `ctfsweep clear [名称] [-y]` | 清空扫描缓存（给名称只清那个项目） | `ctfsweep clear capture4 -y` |
| `ctfsweep config` | 显示运行信息与生效配置（含缓存占用） | `ctfsweep config` |
| `ctfsweep help` | 显示帮助 | `ctfsweep help` |

> 三个平台统一使用 `ctfsweep`（无后缀）。macOS / Linux 上真实脚本装在
> `<安装根>/lib/ctfsweep.sh`，`<安装根>/bin/ctfsweep` 是指向它的软链接——
> `bin/` 在 PATH 上，若把 `.sh` 也放在那里，命令名补全就会同时列出两个名字。

## 支持的输入格式

| 格式 | 识别方式 | 说明 |
|------|----------|------|
| pcap | 魔数（4 字节） | 大端/小端、微秒/纳秒精度 |
| pcapng | 魔数 `0x0A0D0D0A` | SHB/IDB/EPB/SPB/PB，多接口，SLL 等链路层 |
| evtx | 无魔数（按内容） | 免对齐 UTF-16LE 字节扫描 |
| .reg / 文本 | 按内容 | 自动识别 UTF-16LE / UTF-8 |

## 文件提取说明

`--extract` 在完成常规扫描后，从每条 TCP 会话与 UDP 载荷中雕刻文件并保存：

| 文件类型 | 边界裁剪 | 自动深挖 |
|----------|----------|----------|
| ZIP | EOCD 结束符 | ✅ 列条目 / 内容扫描 / 嵌套递归 / 加密试口令 / 假加密绕过 |
| PNG | IEND | — |
| JPG | FFD9 | — |
| GIF / PDF / GZ / RAR / 7Z | 各自结束符 | GZ 自动解压扫描 |

加密 zip 的口令尝试顺序：**空口令 → 常用口令表 → `--pwd-file` 字典 → 流量采集口令池**
（口令池为跨文件预扫采集，含大写 / 首字母大写 / `+123` / `+1` 变体，最多 12 万个候选）。

## 配置文件

复制 `config/ctfsweep.conf` 到 `~/.devtools/ctfsweep/ctfsweep.conf` 即自动生效
（也可用 `--config` 指定路径，或环境变量 `CTFSWEEP_CONF`）。优先级：
**命令行参数 > 配置文件 > 内置默认值**。

```ini
KEYWORDS=flag,ctf,key,secret   # 追加关键词
MIN_SCORE=0.40                 # 置信度下限
DEPTH=3                        # 解码链深度
LIMIT=50                       # 每文件输出条数
NO_DECODE=false                # true 关闭自动解码
```

## 跨平台支持

| 系统 | 主脚本 | 安装路径 | 配置文件 | 入口 |
|------|--------|----------|----------|------|
| macOS | `ctfsweep`（→ `lib/ctfsweep.sh`） | `/Library/devtools/ctfsweep/` | `…/config/ctfsweep.conf` | `installer/` |
| Linux | `ctfsweep`（→ `lib/ctfsweep.sh`） | `/usr/local/devtools/ctfsweep/` | `…/config/ctfsweep.conf` | `installer/` |
| Windows | `ctfsweep.bat` | `%USERPROFILE%\.devtools\ctfsweep\` | `…\config\ctfsweep.conf` | `installer/windows/` |

用户级安装（`CTFSWEEP_USER=1`）三平台都是 `~/.devtools/ctfsweep`。

> Windows 上是**纯用户级**安装：不需要管理员，PATH 走 `HKCU\Environment`。
> 这和 ptool 不同——ptool 的 shim 必须在机器级 PATH 最前才能生效，所以要提权；
> 本工具没有 shim，一个用户级 `bin` 目录就够了。
>
> 用户级安装下**安装根就是数据根**（扫描缓存 `cache/` 住在同一层），所以安装 / 更新 /
> 卸载一律**只碰功能项**，那三样数据永不自动删除。

> **2.2 之外的平台差异**：Windows 上没有 `.sh` 启动器、没有 bash/zsh 补全、也没有
> `shell-setup.sh` 那套 rc 接线——它们各自都有 Python 侧实现（`deploy_nt` /
> `_win_uninstall` / 注册表 PATH）。图形安装包（.exe）与 `install.ps1` 两条路径
> 装出**同一个形状**，测试里有一条断言逐项比对载荷表与 `.iss` 的 `[Files]`。

## 在脚本中使用

退出码是给脚本用的接口：`0` 成功 · `1` 失败（含未给参数时打印帮助）· `2` 用法错。

```bash
#!/bin/bash

# 打到一个目录，只在有高置信命中时才继续
if ctfsweep -F ./evidence/ --min-score 0.85 -q >/dev/null; then
    echo "发现高置信线索"
fi

# 扫完取回这次的完整报告（扫描缓存：一次运行一个目录）
ctfsweep capture.pcap >/dev/null
ls ~/.devtools/ctfsweep/cache/

# 批量：逐个文件扫，明细留在缓存里
for f in pcaps/*.pcap; do
    ctfsweep "$f" -q
done
```

> CI / 无人值守时注意两个子命令会等确认：`uninstall` 与 `clear` 不带 `-y` 时会要求
> 交互确认；非交互环境下它们会明确拒绝并提示加 `-y`，不会静默执行也不会挂住。
>
> 扫描缓存**只增不减**：安装 / 更新 / 卸载都不碰它，只有显式 `ctfsweep clear` 才清。

## Tab 补全

把下面这行加入 `~/.zshrc`（bash 用户见后文），重开终端或 `source ~/.zshrc` 后生效：

```bash
source <项目根>/completions/ctfsweep.zsh
```

```bash
ctfs<TAB>                   # 补全命令名 → ctfsweep（命令名只有这一个，无短别名）
ctfsweep <TAB>              # 子命令 + 文件（不列选项，与 jtool/ptool 的位置驱动一致）
ctfsweep -<TAB> / --<TAB>   # 全部选项；同义短/长合并为一行显示（如 "-f --file"，只出现一次）
ctfsweep --ex<TAB>          # 按前缀补全（--extract / --extract-dir ...）
ctfsweep -f<TAB>            # 补全短选项 → -f（--f<TAB> 同理 → --file）
ctfsweep -f <TAB>           # 补全文件路径（--extract-dir <TAB> 补全目录）
ctfsweep -F <TAB>           # 补全文件夹路径（-F/--folder；目录递归扫描整个项目）
ctfsweep --min-score <TAB>  # 补全取值（0.40 / 0.55 / 0.85 / 0.95）
ctfsweep -q <TAB>           # 只补文件（选项只在敲 "-" 之后出现）
ctfsweep uninstall <TAB>    # → -y / --yes
```

说明：

- **位置驱动，选项在敲 `-` 之后出现**（与同仓库的 jtool/ptool 同规）：第一个参数位只出
  「子命令 + 文件」——`ctfsweep <TAB>` 一屏就是 6 条子命令加文件候选，不铺选项墙。
  `ctfsweep -q <TAB>`、`ctfsweep a.pcap <TAB>` 因而只补文件；想知道有哪些选项就敲
  `ctfsweep -<TAB>`。
- **同义短/长选项合并显示**（如 `-f --file`，只出现一次）；`-f<TAB>` 与 `--f<TAB>` 均按前缀补全。
- 已输入过的选项不会重复列出（`-f` 与 `--file` 视为同一个）。
- **`update` 后补全自动生效**：补全文件里带一个包装函数（与 jtool/ptool 同规），
  `ctfsweep update` 跑完就在当前 shell 里重载它，不必手动 source 或重开终端。
  ⚠️ 别写成 `sudo ctfsweep update`——sudo 按 PATH 找可执行文件、不看 shell 函数，
  会绕过包装函数（更新本身会按需提权，直接敲 `ctfsweep update` 即可）。

> 手动接线：zsh 直接 `source <项目根>/completions/ctfsweep.zsh`（需已启用 compinit）；
> bash source 同目录下的 `ctfsweep.bash` 即可。

### 关于「刷新」

`install` / `update` / `uninstall` 都会**按成对标记块**改写 shell 配置：写入的是

```sh
# >>> ctfsweep >>>

export PATH="<安装根>/bin:$PATH"
[ -f "<安装根>/completions/ctfsweep.zsh" ] && source "<安装根>/completions/ctfsweep.zsh"
# <<< ctfsweep <<<
```

重复安装不会堆叠（整块先删后写），卸载会整块摘除。改完配置需重开终端或 `source` 一次；
**更新代码不需要任何刷新动作**（PATH 与补全指的都是安装目录里的文件，重装就地生效）。

提示语因此是**看情况出的**：脚本会比对改写前后 rc 的内容，只有真改动了接线才报
`已写入 shell 配置: ~/.zshrc（重开终端或 source 后生效）`；接线一字未变（升级时的常态）报的是
`shell 配置未变: ~/.zshrc（接线一致，无需重开终端）` —— 不必为一次版本升级重开终端。

## 项目结构

```
CtfSweep/
├── VERSION                        # 版本号（与 ctfsweep.__version__ 保持一致，CI 校验）
├── README.md                      # 本文档
├── LICENSE                        # MIT
├── pyproject.toml                 # 打包元数据（零依赖；console_scripts 入口）
├── .gitignore / .gitattributes    # 忽略规则 / 行尾契约（*.bat=CRLF, *.sh=LF）
├── ctfsweep/                      # Python 包（核心实现）
│   ├── __init__.py                # 版本号
│   ├── __main__.py                # python -m ctfsweep 入口
│   ├── cli.py                     # 命令行解析 / 子命令分发 / 配置加载 / 批量扫描与汇总
│   └── core/
│       ├── utils.py               # 共享正则、编码尝试、置信度分级
│       ├── capture.py             # pcap/pcapng 解析 + 四层解析（TCP/UDP/DNS）
│       ├── decode.py              # hex/base64 解码链、片段探测、加壳与拼接建议
│       ├── blobscan.py            # 字节块扫描原语（findings 去重 + 多策略扫描）
│       ├── http.py                # 请求序列 / POST 字段 / JWT / 事务配对
│       ├── ad.py                  # AD 域取证：Kerberos 票据 / NTLMSSP / LDAP 明文绑定（hashcat 格式输出）
│       ├── extract.py             # 文件雕刻、口令池、zip 弱口令与假加密绕过
│       ├── judge.py               # 判断核：轻量 MLP 集成 + 特征提取 + 推理打分（只推理，不训练）
│       ├── model_io.py            # 判断核模型 I/O（.ctfj 二进制单一格式）
│       ├── paths.py               # 数据目录布局单点定义（~/.devtools/ctfsweep/cache/）
│       ├── scanner.py             # 抓包扫描与原始文件扫描的编排
│       ├── report.py              # 置信度报告渲染
│       └── selfmgr.py             # 自管理：config / update（真更新）/ install 指引 / uninstall
├── bin/                           # ⚠️ 素材目录，**不要**整体加入 PATH（见「安装」）
│   ├── ctfsweep.sh                # 启动器（macOS / Linux；安装时复制成 <安装根>/lib/ctfsweep.sh）
│   └── ctfsweep.bat               # 启动器（Windows；只走源码直跑，不进安装目录）
├── config/
│   └── ctfsweep.conf              # 扫描配置文件模板
├── models/                        # 判断核模型与训练配置（随项目版本管理）
│   ├── model.ctfj                 # 训练产物（.ctfj 二进制，5 种子集成）
│   └── train_config.json          # 训练超参数（网络结构 / 学习率 / 种子等，改参数无需改代码）
├── completions/
│   ├── ctfsweep.zsh               # zsh 补全
│   └── ctfsweep.bash              # bash 补全
├── lab/                           # 实验/辅助工具（独立运行；脚本代码进库，数据产物不进库）
│   ├── train.py                   # 判断核离线训练入口（留一组评估 + 保存模型；不随安装提供）
│   ├── data_generator.py          # 合成训练样本（多类型覆盖）
│   ├── build_dataset.py           # 从题库构建训练语料 lab/dataset.jsonl
│   ├── task_generator.py          # SSH 远程题目生成器（pcap/evtx/registry/memory/文件取证）
│   └── analysis/                  # 案例库（每题一个 .md：识别特征 / 推理链 / 沉淀的工具函数）
├── installer/                     # 安装 / 卸载 / 发布
│   ├── install.sh                 # 一键安装（可 source；自举下载或就地调用下方脚本）
│   ├── install-from-source.sh     # 本地源码安装（deploy + shell 接线）
│   ├── deploy.sh                  # 布局实现（唯一一份）：白名单拷贝 + bin/ 只留一个软链
│   ├── shell-setup.sh             # shell 接线安装/摘除（成对标记块，幂等）
│   ├── uninstall.sh               # 卸载安装副本（保留扫描缓存；由 shell-setup 摘接线）
│   └── publish-mirror.sh          # 把源码快照 + install.sh + VERSION 发布到国内镜像
├── tests/
│   ├── gen_fixtures.py            # 生成确定性测试样例（pcap/pcapng/evtx/内嵌 zip/AD 域流量）
│   ├── test_smoke.py              # 纯标准库冒烟（CLI + 扫描行为 + AD 协议 + shell 脚本体检）
│   ├── test_golden.py             # 特征化（golden）逐字节回归（重构期手工跑，不进 CI）
│   └── smoke.sh                   # 冒烟总入口（语法门 + 单元冒烟 + 启动器 + 布局契约
│                                  #   + 引导模式 + 真更新/离线失败/uninstall，全程 file:// 镜像）
└── .github/workflows/ci.yml       # CI：Python 3.8 / 3.11 / 3.13 三版本跑冒烟
```

## 开发与测试

```bash
# 一键冒烟：compileall 语法门 + 单元冒烟 + shell 语法 + 启动器 + 安装/布局契约
#           + 引导模式（离线模拟）+ 自管理子命令（config / 真更新 / 离线失败 / uninstall）
bash tests/smoke.sh

# 单独跑单元冒烟
python3 tests/test_smoke.py

# 手动生成测试样例（确定性输出）
python3 tests/gen_fixtures.py /tmp/fixtures

# 发布到国内镜像（把当前分支快照 + 一键脚本推到镜像服务器，要求工作区干净）
./installer/publish-mirror.sh
```

CI（`.github/workflows/ci.yml`）在 ubuntu 上以 Python **3.8 / 3.11 / 3.13** 三个版本
运行同一套冒烟，保证最低版本承诺不漂移。

## 常见问题

**Q: 怎么使用？需要安装吗？**
推荐安装（`source <(curl -fsSL <镜像>/dist/ctfsweep/install.sh)`），与同仓库的 jtool / ptool
一样装成 devtools 副本。不装也能跑：在项目目录里 `python3 -m ctfsweep <文件>`
或 `./bin/ctfsweep.sh <文件>`，功能完整。

**⚠️ 别把项目的 `bin/` 加进 PATH**：它靠扩展名区分系统（`ctfsweep.sh` + `ctfsweep.bat`），
而 zsh 的命令名补全走 `$commands` 哈希、**不检查可执行位**——于是 Windows 启动器
`ctfsweep.bat` 会跟 `ctfsweep` 一起出现在 TAB 补全里（macOS 上它根本跑不起来）。
PATH 只该指向安装目录的 `bin/`，那里只有一个无后缀软链。

**Q: 已经手工把仓库 `bin/` 加进 PATH 了，怎么收拾？**
跑一次 `install.sh` 即可：`shell-setup.sh` 会把 rc 里的旧手工接线（指向
`CtfSweep/bin` 的 `export PATH`、1.10.5 及更早写过的 `alias ctf`、source 仓库补全的行）
逐行删掉，再写入 `# >>> ctfsweep >>>` 块。想彻底移除就 `ctfsweep uninstall`——扫描缓存始终保留。

**Q: 短命令 `ctf` 怎么没了？**
1.10.6 起不再写这个别名：`ctf` 太通用，同一个环境里再装别的 CTF 工具必然撞名。
跑一次 `ctfsweep update` 就会把 rc 里的旧别名摘掉（那时会提示重开终端或 `source`——
接线确实变了，不像平常那样一字未动）。此后命令名只有 `ctfsweep` 一个。

**Q: 需要装 Wireshark 或 scapy 吗？**
不需要。解析器是纯 Python 实现（不到 200 行），这也是"零依赖"的一部分。

**Q: 为什么对"合成抓包"也能用？**
合成/回放类抓包的 TCP 序号常常是伪造的，按序号重组会拼乱。本工具按**捕获顺序**拼接
并按会话隔离，同时逐包独立扫描兜底，两条路都会出结果。

**Q: 高置信结果可以直接提交吗？**
基本可信，但建议瞄一眼上下文——个别题目会故意放"诱饵 flag"。中置信是重点怀疑区
（分段的、需要拼接的、编码嵌套的都在这里）。

**Q: 提取的加密 zip 口令撞不开怎么办？**
用 `--pwd-file` 挂更大的字典；或先在整目录 `--extract` 让工具预扫全部抓包采集
流量中的候选口令（很多题目口令就藏在其他流量里）。另外留意"假加密"——工具会先
自动绕过。

**Q: 数据都存在哪里？会不会随着清理丢失？**
分两类：**模型与训练配置**随版本发布（`models/model.ctfj` + `models/train_config.json`，
安装到 `<安装根>/lib/models/`）；**扫描缓存**放 `~/.devtools/ctfsweep/cache/`——这是数据
目录下的主要内容（每次扫描都会写，跑完就能回看；同一目标已有缓存时不覆盖，提示先 `clear`）。
`update` 与 `uninstall` 都只覆盖
`bin lib completions config VERSION uninstall deploy.sh shell-setup.sh` 这些功能项，
**永不删除任何数据**（冒烟测试里有一个 `cache/sentinel-abc123/1.txt` 哨兵守着这条契约）。

**Q: 怎么更新？**
安装副本：`ctfsweep update` 读镜像 `VERSION` 比对，有新版就下载快照重装（扫描缓存保留）；
`--check` 只看不装。源码直跑：在项目目录 `git pull` 即可（`update` 会直接给出这条指引）。
代码更新后无需任何刷新动作。

**Q: `update` 提示「无法获取远端版本号」？**
镜像与 GitHub 都没读到 `VERSION`。查网络、或换源（`CTFSWEEP_MIRROR=<url>`）；临时
想只走 GitHub 用 `CTFSWEEP_MIRROR=none`。命令不会静默成功——失败一律非零退出。

**Q: 会不会污染我的目录？**
扫描结果写 `~/.devtools/ctfsweep/cache/`（数据目录下的主体，只增不减，`ctfsweep config`
报占用）；`--extract` 写 `<抓包名>_extracted/`（与抓包同目录，可用 `--extract-dir` 改，
没提取到任何文件时该目录会被自动移除）。

## 许可证

MIT License
