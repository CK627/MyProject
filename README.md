# ctfsweep - CTF 流量 / 日志 / 注册表 快速扫描器

> 面向 CTF 与应急响应的取证扫描工具：把流量包（pcap / pcapng）、Windows 事件日志（evtx）、
> 注册表（.reg）里"可疑的东西"一次性翻出来，并按**置信度分级**输出——高置信可直接核验，
> 低置信留作人工排查线索。
>
> 零依赖（纯标准库，Python 3.8+），`ctfsweep <文件或目录>` 即用；支持 macOS / Linux / Windows。

## 快速开始（源码直跑）

本工具采用**源码直跑**模式：功能完整存在于项目目录，**不安装外部副本**；
模型与训练配置随项目（`models/`），运行时缓存（扫描候选池 / 数据集）放
`~/.devtools/ctfsweep/`（见下）。

macOS / Linux / Windows 通用，零依赖（Python 3.8+）：

```bash
# 方式一：项目启动器（任意目录可用）
./bin/ctfsweep <文件或目录> [选项]

# 方式二：模块方式（项目根目录内）
python3 -m ctfsweep <文件或目录> [选项]

# 方式三（推荐）：把项目的 bin 加入 PATH，之后 ctfsweep / ctf 命令全局可用
#   在项目根目录执行：
echo "export PATH=\"$PWD/bin:\$PATH\"" >> ~/.zshrc && source ~/.zshrc
```

### Windows

Windows 下无需安装：运行 `bin\ctfsweep.bat <文件或目录>`（任意目录可用），
或把项目根目录加入 `PYTHONPATH` 后使用 `python -m ctfsweep`。

### 文件布局（模型随项目 / 缓存集中）

| 内容 | 位置 | 说明 |
|------|------|------|
| **判断核模型 + 训练配置** | 项目内 `models/`（`model.ctfj` + `train_config.json`） | 训练产物与超参数，随项目版本管理；专注升级模型参数无需改代码 |
| 扫描缓存（留存区 / 候选池 / 累积数据集） | `~/.devtools/ctfsweep/judge/` | `retention.jsonl` 每次扫描的候选快照（留存区）、`pending.jsonl` 扫描候选记录、`dataset.jsonl` 累积标注数据 |
| 自主学习数据 | `~/.devtools/ctfsweep/auto_learn/` | 自主学习引擎的运行时数据 |
| 配置文件（可选） | `~/.devtools/ctfsweep/ctfsweep.conf` | 扫描行为配置 |

> 训练数据流：**每次扫描跑动 → 候选记入留存区（retention）+ 缓存池（pending）→
> 已知答案 `ctfsweep mark` 回填 / 未知答案 `ctfsweep learning` 时逐题询问（题目；答案：）→
> 标注累积到数据集（dataset）→ `ctfsweep train` 按项目配置训练 → 模型写回项目 `models/`**。

> 历史说明：早期版本支持"安装到 `~/.devtools/ctfsweep/`（devtools 布局）"。
> 现已改为源码直跑（不做外部拓展）；如本机留有旧安装副本，运行
> `ctfsweep uninstall` 清理（**用户数据始终保留**）。

## 清理旧版安装（uninstall）

源码直跑模式下通常无需卸载。如本机曾装过旧版（devtools 布局），清理方式：

```bash
ctfsweep uninstall            # 推荐：带确认提示（-y 跳过）
./installer/uninstall.sh      # 等价脚本

sudo ./installer/uninstall.sh # 连同系统级目录（/Library/devtools/ctfsweep）一起清理
```

清理只删除功能残留（bin / lib / config / completions 等），
**缓存目录（`~/.devtools/ctfsweep/` 下的候选池与数据集）始终保留**。

> 历史安装脚本仍保留在 `installer/`（如需在别的机器临时部署），当前模式不再使用。

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
  | 0.97 | 高 | 明文完整 flag |
  | 0.95 | 高 | 解码后得到完整 flag（hex/base64/DNS 等） |
  | 0.75 | 中 | 内容"加壳"候选（疑似 flag 本体） |
  | 0.72 | 中 | JWT 令牌（payload 已解码） |
  | 0.65 | 中 | 未闭合片段（分段 flag 前半截） |
  | 0.62 | 中 | 命令回显 / 环境变量密钥回显 / AES Kerberos 票据（需字典） |
  | 0.55 | 中 | 域账号 / SPN 清单（AD 线索） |
  | 0.60 / 0.55 | 中 | 裸花括号片段 `{xxx` / `xxx}` |
  | 0.45 | 低 | DNS 查询名 |
  | 0.42 | 低 | 接口短文本响应 |
  | 0.40 | 低 | 关键词上下文 |

- 🧾 输出结构：逐文件报告（**按级别分区换行**：高置信 / 中置信 / 低置信）→ 拼接建议 →
  **候选汇总**（flag 候选 / 非 flag 证据分组，非 flag 文件明确提示"未发现 flag 形状候选"）
  → 全局片段池（按行标注来源）→ 扫描统计（高/中/低条数分区）
- 🎛️ `--min-score` 过滤、`--limit` 截断、`--depth` 控制解码深度、`--no-decode` 关闭解码
- 🛡️ 单文件出错不中断，继续扫下一个

### 判断核（实验特性，`train` + `--judge`）

本地训练的**轻量判断网络**：对扫描候选做"答案相关性"打分（`p=0.9x`），用于人工核验前的排序与降噪。

- 🧠 **纯 Python 手写 MLP 集成**（默认 5 个成员，140 维特征输入；模型为 `.ctfj` 二进制单一格式）——零依赖、完全离线、训练确定性
- 🏷️ 训练数据 = 本机积累的解题标注（缓存区 `~/.devtools/ctfsweep/judge/dataset.jsonl`：每行 = 候选 + 真/假标签），永不自动删除
- 🧩 **模型随项目**：训练产物保存在项目内 `models/model.ctfj`（与代码同步版本管理，可单独升级/替换）
- ⚙️ **训练超参数独立于代码**：编辑项目内 `models/train_config.json`（网络结构 / 学习率 / 种子 / 轮数等）——升级模型参数无需改代码
- 📏 **留一组评估**（leave-one-group-out）：每组轮流当测试集，评估泛化后再全量重训；实测当前题库汇总 AUC ≈ 0.92
- 🔌 无模型时工具行为与之前完全一致；`--judge` 时输出 `p=` 分与【判断核·重点候选】

```bash
ctfsweep train                 # 训练（留一组评估 + 保存模型到项目内 models/model.ctfj）
ctfsweep train --epochs 500    # 临时覆盖训练轮数（其余参数读训练配置）
ctfsweep file.pcap --judge     # 扫描时给候选打 p 分，并列出模型排序的重点候选
```

> 诚实边界：判断核的"推理"是**统计归纳**（形状 / 上下文 / 模式），不是语义理解——
> 开放语义推理仍交给 LLM / 人工；它的定位是"扫描器找全 → 判断核排序 → 人最终确认"。

### 工程特性

- ⚡ **零第三方依赖**：任意 Python 3.8+，无需 pip install 任何东西
- 📁 目录递归扫描；260MB 注册表全量 10 秒内、常规抓包亚秒级
- 🔁 自助管理：`ctfsweep config`（运行信息）/ `train` / `label` / `learning` 等；`uninstall` 仅用于清理历史旧安装
- 🧰 完整工程配套：CLI 包装器、shell 补全、配置文件、冒烟测试、CI

## 使用方法

### 快速开始

```bash
# 扫描一个抓包（默认输出 >= 0.40 的全部候选）
ctfsweep capture.pcap

# 短命令 ctf（项目 bin 加入 PATH 后与 ctfsweep 等价）与 -f 写法，都等价
ctf -f capture.pcap

# 只看高置信结果（直接要 flag 时）
ctfsweep capture.pcap --min-score 0.85

# 扫描并提取流量中的文件（含加密 zip 自动尝试口令）
ctfsweep capture.pcap --extract

# 批量扫描整个目录（含 evtx / reg / 文本）
ctfsweep ./logs/

# 用 -F 指定文件夹（与位置参数传目录等价，语义更直观；适合"整个项目=一个文件夹"的日志包）
ctf -F ./logs/

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
| `--extract` | 从流量中提取文件并按内容扫描（详见下文） |
| `--extract-dir D` | 指定提取输出目录（默认 `<抓包名>_extracted/`，与抓包同目录） |
| `--pwd-file F` | 附加口令字典文件（每行一个，用于加密压缩包） |
| `--judge` | 用本地判断核模型对候选打分（`p=…` + 重点候选排序；需先 `ctfsweep train`） |
| `--config F` | 指定配置文件（默认读取 `~/.devtools/ctfsweep/ctfsweep.conf`） |
| `--version` | 显示版本 |
| `-h, --help` | 显示帮助 |

### 子命令（管理）

| 子命令 | 说明 |
|--------|------|
| `ctfsweep update` | 更新指引（源码直跑模式：在项目目录 `git pull`） |
| `ctfsweep install` | 已弃用（源码直跑，不安装外部副本） |
| `ctfsweep uninstall [-y]` | 清理历史旧安装残留（用户数据保留；`-y` 跳过确认） |
| `ctfsweep config` | 显示运行信息、数据目录与生效配置 |
| `ctfsweep train [--data F] [--epochs N] [--model-out F]` | 训练本地判断核：留一组评估 + 全量重训 + 保存模型（超参数读训练配置） |
| `ctfsweep mark <路径> <真实flag>` | 用真实答案回填一道题（文件/文件夹均可）：匹配候选→正样本，同题其他高分候选→负样本（难负样本）；无记录时自动先扫描 |
| `ctfsweep learning [opts]` | 自主学习：**先逐题复核留存区**（题目；答案：<真实flag>，一个接一个），再自动标注 + 训练（带收敛判断） |
| `ctfsweep label` / `auto-label` | 交互式标注 / 自动标注未标注候选 |
| `ctfsweep gen-data [-o F]` | 生成 CTF 取证训练数据集（多类型覆盖；默认输出到用户数据目录） |
| `ctfsweep help` | 显示帮助 |

> 子命令名（update / install / uninstall / config / train / label / learning / mark / gen-data / help 等）优先于文件路径解析——
> 若要扫描恰好同名的文件，请用 `-f 文件名` 或 `./文件名`。

### 留存区（每次扫描自动记录，学习数据的来源）

**每次扫描都会把候选快照记入留存区**（缓存区 `retention.jsonl`）——这是"每次跑动 → 积累 → 学习"的入口：

```bash
# ① 扫描一道题（文件或文件夹都一样，目录名随意——里面是啥就扫啥）
ctfsweep /path/to/logs/              # → 留存区自动记录这道题的候选

# ② 有答案：立即回填（正=匹配候选；负=同题其他高分候选，即难负样本）
ctfsweep mark /path/to/logs/ "flag{windows-log-answer}"

# ③ 没答案（或拿不准）：留到 learning 时逐题询问
ctfsweep learning                    # 逐题显示「题目；答案：<真实flag>」——输入答案回填 / 输入"无"标记无答案 / 回车暂留 / q 结束
```

> `mark` 支持文件与文件夹：路径给什么扫什么（递归）。像 `flag.pacpng/flag.pcapng` 这种
> "文件夹名像文件名"的结构也不受影响——把题目文件夹路径传进来即可。

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

# 判断核：对候选按"答案相关性"排序（先 ctfsweep train 一次，之后每次扫描都可加 --judge）
ctfsweep Security.evtx --judge              # 输出 p= 分 + 【判断核·重点候选】
```

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

## Tab 补全

把下面这行加入 `~/.zshrc`（bash 用户见后文），重开终端或 `source ~/.zshrc` 后生效：

```bash
source <项目根>/completions/ctfsweep.zsh
```

```bash
ctfs<TAB>              # 补全命令名 → ctfsweep（ctf<TAB> 会同时列出系统自带的 ctf_insert）
ctf <TAB>              # 子命令 + 全部选项 + 文件（不敲 "-" 也能直接看到 --extract 等）
ctf -<TAB> / --<TAB>   # 全部选项；同义短/长合并为一行显示（如 "-f --file"，只出现一次）
ctf --ex<TAB>          # 按前缀补全（--extract / --extract-dir ...）
ctf -f<TAB>            # 补全短选项 → -f（--f<TAB> 同理 → --file）
ctf -f <TAB>           # 补全文件路径（--extract-dir <TAB> 补全目录）
ctf -F <TAB>           # 补全文件夹路径（-F/--folder；目录递归扫描整个项目）
ctf --min-score <TAB>  # 补全取值（0.40 / 0.55 / 0.85 / 0.95）
ctf uninstall <TAB>    # → -y / --yes
```

说明：

- **不敲 `-` 也能看到选项**：zsh 的 `_describe -t options` 有默认门禁（prefix-needed，
  光标不以 `-` 开头就不列出选项）；本项目改用「`compadd -l -d` + 手写显示串」直接列出，
  TAB 即见全部选项；bash 版行为一致。
- **同义短/长选项合并显示**（如 `-f --file`，只出现一次）；`-f<TAB>` 与 `--f<TAB>` 均按前缀补全。
- 已输入过的选项不会重复列出（`-f` 与 `--file` 视为同一个）。

> 手动接线：zsh 直接 `source <项目根>/completions/ctfsweep.zsh`（需已启用 compinit）；
> bash source 同目录下的 `ctfsweep.bash` 即可。

### 关于「刷新」

源码直跑模式下，`update` / `install` / `uninstall` 不再改写 shell 配置；
补全与 PATH 始终指向项目目录，代码更新（`git pull`）后无需任何刷新动作。

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
│       ├── judge.py               # 判断核：轻量 MLP 集成 + 特征 + 训练/标注/自主学习
│       ├── model_io.py            # 判断核模型 I/O（.ctfj 二进制单一格式）
│       ├── data_generator.py      # 训练数据集生成（多类型覆盖）
│       ├── scanner.py             # 抓包扫描与原始文件扫描的编排
│       ├── report.py              # 置信度报告渲染
│       └── selfmgr.py             # 自管理子命令：config / uninstall 清理 / 更新指引
├── bin/
│   ├── ctfsweep                   # 启动器（macOS / Linux，支持软链，定位仓库根）
│   └── ctfsweep.bat               # 启动器（Windows）
├── config/
│   └── ctfsweep.conf              # 扫描配置文件模板
├── models/                        # 判断核模型与训练配置（随项目版本管理）
│   ├── model.ctfj                 # 训练产物（.ctfj 二进制，5 种子集成）
│   └── train_config.json          # 训练超参数（网络结构 / 学习率 / 种子等，改参数无需改代码）
├── completions/
│   ├── ctfsweep.zsh               # zsh 补全
│   └── ctfsweep.bash              # bash 补全
├── lab/                           # 实验/辅助工具（独立运行；脚本代码进库，数据产物不进库）
│   ├── auto_learning.py           # 自主学习引擎：生成题目 → 扫描 → 分析 → 收集 → 训练 闭环
│   ├── task_generator.py          # SSH 远程题目生成器（pcap/evtx/registry/memory/文件取证）
│   └── build_dataset.py           # 数据集构建辅助脚本
├── installer/                     # 历史安装脚本（源码直跑模式下不再使用，临时部署可参考）
│   ├── install.sh                 # 一键安装（可 source）
│   ├── install-from-source.sh     # 从源码安装
│   ├── uninstall.sh               # 清理旧安装残留（保留用户数据）
│   └── publish-mirror.sh          # 把源码快照与一键脚本发布到国内镜像服务器
├── tests/
│   ├── gen_fixtures.py            # 生成确定性测试样例（pcap/pcapng/evtx/内嵌 zip/AD 域流量）
│   ├── test_smoke.py              # 纯标准库冒烟（CLI + 扫描行为 + AD 协议 + shell 脚本体检）
│   └── smoke.sh                   # 冒烟总入口（语法门 + 单元冒烟 + 启动器 + 清理循环 + 引导模式）
└── .github/workflows/ci.yml       # CI：Python 3.8 / 3.11 / 3.13 三版本跑冒烟
```

## 开发与测试

```bash
# 一键冒烟：compileall 语法门 + 单元冒烟 + shell 语法 + 启动器 + 清理循环
#           + 引导模式（离线模拟）+ 自管理子命令（config / uninstall，离线）
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
不需要。本工具为**源码直跑**：`./bin/ctfsweep <文件>` 或把项目的 `bin` 加入 PATH 后
`ctfsweep <文件>`。功能完整存在于项目目录；模型与配置在项目 `models/`，
运行时缓存（候选池/数据集）放 `~/.devtools/ctfsweep/`。

**Q: 之前的"一键安装"还能用吗？**
历史安装脚本保留在 `installer/`（供临时部署参考），但当前模式推荐源码直跑。
如本机留有旧版安装副本（`~/.devtools/ctfsweep/bin`、`lib` 等），运行
`ctfsweep uninstall` 清理——缓存数据（候选池/数据集）始终保留。

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
分两类：**模型与训练配置**随项目（`models/model.ctfj` + `models/train_config.json`，
版本管理、可单独升级）；**运行时缓存**（扫描候选池、累积标注数据集）放
`~/.devtools/ctfsweep/`（judge/、auto_learn/ 等）。`uninstall` 只清理功能残留，
**永不删除任何数据**。

**Q: 怎么更新？**
源码直跑模式：在项目目录 `git pull` 即可（`ctfsweep update` 会给出同样指引）。
代码更新后无需任何刷新动作。

**Q: 会不会污染我的目录？**
只有 `--extract` 会写文件，默认写到 `<抓包名>_extracted/`（可用 `--extract-dir` 改）；
若没有提取到任何文件，该目录会被自动移除。

## 许可证

MIT License
