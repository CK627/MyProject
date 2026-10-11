# ctfsweep - CTF 流量 / 日志 / 注册表 快速扫描器

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

> 也可以 `curl -fsSL ... | bash`（安装后重开终端生效）。
> 默认安装到用户级 `~/.devtools/ctfsweep`（无需 sudo）；要系统级安装见下方「从源码安装」。

### 国内镜像（无需 VPN）

GitHub 的 raw 域名在国内不保证可达。镜像服务器在国内，源码快照与 GitHub 分支同源：

```bash
# macOS / Linux
source <(curl -fsSL http://101.132.165.98/dist/ctfsweep/install.sh)
```

安装脚本**先访问镜像，拿不到再回退 GitHub**。换源用环境变量：

```bash
CTFSWEEP_MIRROR=https://mirror.example.com/ctfsweep source <(curl -fsSL .../install.sh)
CTFSWEEP_MIRROR=none source <(curl -fsSL .../install.sh)   # 强制只走 GitHub
```

### macOS / Linux（从源码安装）

```bash
cd /path/to/CtfSweep
./installer/install-from-source.sh install          # 用户级（默认 → ~/.devtools/ctfsweep）
sudo ./installer/install-from-source.sh install     # 系统级（→ /Library/devtools/ctfsweep）
```

安装完成后执行 `source ~/.zshrc`（或 `source ~/.bashrc`）或重新打开终端。

> 在源码仓库内直接运行 `./installer/install.sh` 也可以——脚本会自动识别本地源码并安装，
> 等价于上一条命令。

### 免安装试用

```bash
cd /path/to/CtfSweep
python3 -m ctfsweep <文件或目录> [选项]     # 在项目根目录内
./bin/ctfsweep <文件或目录> [选项]          # 或使用仓库启动器（任意目录）
```

### Windows

Windows 下无需安装：运行 `bin\ctfsweep.bat <文件或目录>`（任意目录可用），
或把项目根目录加入 `PYTHONPATH` 后使用 `python -m ctfsweep`。

> 目前没有 Windows 的 PowerShell 一键安装脚本（一键安装覆盖 macOS / Linux，见上）。

---

> 安装脚本会做三件事：① 部署到 devtools 目录（bin / lib / config / completions / uninstall）；
> ② 把 PATH、短命令别名 `ctf` 与补全写入 shell 配置（幂等，重复安装不会写重）；
> ③ 自动清理旧版软链（`~/.local/bin`）。重开终端后 `ctfsweep` 与 `ctf` 即可用。

### 安装位置（devtools 布局）

| 层级 | macOS | Linux | 说明 |
|------|-------|-------|------|
| 系统级安装 | `/Library/devtools/ctfsweep/` | `/usr/local/devtools/ctfsweep/` | 需 sudo；含 bin / lib / config / completions / uninstall |
| 用户级安装 | `~/.devtools/ctfsweep/` | 同 | 无 sudo 时的默认位置 |
| 用户数据目录 | `~/.devtools/ctfsweep/` | 同 | 补全等用户级数据；未来缓存/更新机制同规（与 `~/.devtools/ptool/` 一致） |

## 卸载

```bash
ctfsweep uninstall            # 推荐：带确认提示（-y 跳过）
./installer/uninstall.sh      # 等价脚本（无确认，直接执行）

sudo ./installer/uninstall.sh               # 连同系统级目录一起清理
sudo /Library/devtools/ctfsweep/uninstall   # 或安装目录内的副本
```

卸载会删除安装目录（含 bin / lib / config / completions / uninstall）与用户数据目录，
并清理 shell 配置里由 ctfsweep 写入的 PATH 行、别名与补全 source 行（不触碰其他配置）。

## 功能特性

### 输入与解析

- 📦 三种输入通吃：
  - **pcap / pcapng**：纯 Python 自解析（不依赖 Wireshark / scapy / dpkt）
  - **evtx**（Windows 事件日志）：字节级 UTF-16LE 扫描，免对齐、免解析器，损坏区块也不怕
  - **.reg / 任意文本**：自动识别 UTF-16 编码
- 🌐 链路层支持：Ethernet / VLAN / PPPoE / Raw-IP / Linux-SLL / SLL2 / NULL；
  pcapng 支持 SHB / IDB / EPB / SPB / 老式 PB 与多接口
- 🧵 逐包独立扫描 + 按捕获顺序的 TCP 会话拼接（**对伪造序号 / 乱序合成的抓包同样稳**）

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

### HTTP 深度分析

- 📋 请求序列（带时间戳）：目录扫描次序、登录、上传等操作一览
- 📝 **POST 字段摘录**：form-urlencoded / multipart（文件名）/ **JSON 体**（登录凭证、上传名、木马参数）
- 🔁 **请求↔响应事务配对**：命令回显、接口短文本直接可读（RCE / webshell 场景）
- 🪪 **JWT 自动识别与解码**：header / payload 直接展开（伪造身份类题目的答案就在 payload 里）
- 🔍 **环境变量 / 密钥回显侦测**：`WEBUI_SK=...`、`PWD=...` 等一条不落

### 文件提取（`--extract`）

- 🔪 从 TCP 会话与 UDP 载荷中按文件签名**雕刻文件**：ZIP / PNG / JPG / GIF / PDF / GZ / RAR / 7Z
  （自动裁剪边界、哈希去重、合法性校验）
- 🗜️ **zip 自动深挖**：列条目 → 逐条内容扫描 → **嵌套 zip 递归** → 小文本条目预览
- 🔐 **加密 zip 自动尝试口令**：空口令 → 常用口令表 → `--pwd-file` 字典 → **流量采集口令池**（含大小写/后缀变体）
- 👻 **"假加密"绕过**：中心目录标记加密、本地头实际未加密的 zip，直接解析数据区（CRC 校验后取内容）
- 📄 GZ 自动解压扫描；提取到的内容全部并入置信度报告

### 输出与置信度

- 🎯 **置信度分级**（每条结果带 `[分数 级别]`，按分数排序）：

  | 分数 | 级别 | 含义 |
  |------|------|------|
  | 0.97 | 高 | 明文完整 flag |
  | 0.95 | 高 | 解码后得到完整 flag（hex/base64/DNS 等） |
  | 0.75 | 中 | 内容"加壳"候选（疑似 flag 本体） |
  | 0.72 | 中 | JWT 令牌（payload 已解码） |
  | 0.65 | 中 | 未闭合片段（分段 flag 前半截） |
  | 0.62 | 中 | 命令回显 / 环境变量密钥回显 |
  | 0.60 / 0.55 | 中 | 裸花括号片段 `{xxx` / `xxx}` |
  | 0.45 | 低 | DNS 查询名 |
  | 0.42 | 低 | 接口短文本响应 |
  | 0.40 | 低 | 关键词上下文 |

- 🧾 输出结构：逐文件报告（**按级别分区换行**：高置信 / 中置信 / 低置信）→ 拼接建议 →
  **高置信候选汇总** → 全局片段池（按行标注来源）→ 扫描统计（高/中/低条数分区）
- 🎛️ `--min-score` 过滤、`--limit` 截断、`--depth` 控制解码深度、`--no-decode` 关闭解码
- 🛡️ 单文件出错不中断，继续扫下一个

### 工程特性

- ⚡ **零第三方依赖**：任意 Python 3.8+，无需 pip install 任何东西
- 📁 目录递归扫描；260MB 注册表全量 10 秒内、常规抓包亚秒级
- 🔁 自助管理：`ctfsweep update`（镜像优先、指纹校验、损坏自修复）/ `install` / `uninstall` / `config`
- 🧰 完整工程配套：CLI 包装器、一键/源码安装脚本、shell 补全、配置文件、冒烟测试、CI

## 使用方法

### 快速开始

```bash
# 扫描一个抓包（默认输出 >= 0.40 的全部候选）
ctfsweep capture.pcap

# 短命令 ctf（安装脚本加的别名）与 -f 写法，都等价
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
| `--config F` | 指定配置文件（默认读取 `~/.config/ctfsweep/ctfsweep.conf`） |
| `--version` | 显示版本 |
| `-h, --help` | 显示帮助 |

### 子命令（管理）

| 子命令 | 说明 |
|--------|------|
| `ctfsweep update [--check]` | 检查并更新到最新版（镜像优先 → GitHub 回退；`--check` 只检查不安装）。用**载荷指纹**判定——版本没变但文件缺失/被改动也能检测并修复 |
| `ctfsweep install` | 在源码仓库内运行：把当前源码安装到 devtools |
| `ctfsweep uninstall [-y]` | 卸载（`-y` 跳过确认） |
| `ctfsweep config` | 显示运行模式、安装位置与生效配置 |
| `ctfsweep help` | 显示帮助 |

> 子命令名（update / install / uninstall / config / help）优先于文件路径解析——若要扫描恰好同名的文件，
> 请用 `-f 文件名` 或 `./文件名`。

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

复制 `config/ctfsweep.conf` 到 `~/.config/ctfsweep/ctfsweep.conf` 即自动生效
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

安装时会**自动把 PATH、短命令别名与补全写入 `~/.zshrc` / `~/.bashrc`**
（幂等，重复安装不会写重；补全本体在 `~/.devtools/ctfsweep/completions/`），重开终端后即生效：

```bash
ctfs<TAB>              # 补全命令名 → ctfsweep（ctf<TAB> 会同时列出系统自带的 ctf_insert）
ctf <TAB>              # 子命令 + 全部选项 + 文件（不敲 "-" 也能直接看到 --extract 等）
ctf -<TAB> / --<TAB>   # 全部选项；同义短/长合并为一行显示（如 "-f --file"，只出现一次）
ctf --ex<TAB>          # 按前缀补全（--extract / --extract-dir ...）
ctf -f<TAB>            # 补全短选项 → -f（--f<TAB> 同理 → --file）
ctf -f <TAB>           # 补全文件路径（--extract-dir <TAB> 补全目录）
ctf -F <TAB>           # 补全文件夹路径（-F/--folder；目录递归扫描整个项目）
ctf --min-score <TAB>  # 补全取值（0.40 / 0.55 / 0.85 / 0.95）
ctf update <TAB>       # → --check；ctf uninstall <TAB> → -y / --yes
```

说明：

- **不敲 `-` 也能看到选项**：zsh 的 `_describe -t options` 有默认门禁（prefix-needed，
  光标不以 `-` 开头就不列出选项）；本项目改用「`compadd -l -d` + 手写显示串」直接列出，
  TAB 即见全部选项；bash 版行为一致。
- **同义短/长选项合并显示**（如 `-f --file`，只出现一次）；`-f<TAB>` 与 `--f<TAB>` 均按前缀补全。
- 已输入过的选项不会重复列出（`-f` 与 `--file` 视为同一个）。

> 手动接线：zsh 直接 `source ~/.devtools/ctfsweep/completions/ctfsweep.zsh`（需已启用 compinit）；
> bash source 同目录下的 `ctfsweep.bash` 即可。

### 更新后无需手动 source

安装时补全脚本里会定义一个 `ctfsweep` 包装函数（`.zshrc` / `.bashrc` 只负责 source 它）。
函数在**父 shell** 中执行，所以 `ctfsweep update` / `ctfsweep install` / `ctfsweep uninstall`
跑完后会立刻刷新——不需要手动 `source ~/.zshrc`，也不需要重开终端。

> 例外：**首次安装**时函数还没定义（rc 正在被写入），第一次仍需重开终端或 `source ~/.zshrc`。

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
│       ├── extract.py             # 文件雕刻、口令池、zip 弱口令与假加密绕过
│       ├── scanner.py             # 抓包扫描与原始文件扫描的编排
│       ├── report.py              # 置信度报告渲染
│       └── selfmgr.py             # 自管理子命令：update / install / uninstall（镜像 + 指纹校验）
├── bin/
│   ├── ctfsweep                   # 启动器（macOS / Linux，支持软链，定位仓库根）
│   └── ctfsweep.bat               # 启动器（Windows）
├── config/
│   └── ctfsweep.conf              # 配置文件模板
├── completions/
│   ├── ctfsweep.zsh               # zsh 补全
│   └── ctfsweep.bash              # bash 补全
├── installer/
│   ├── install.sh                 # 一键安装（可 source；远程自举：镜像优先、GitHub 回退）
│   ├── install-from-source.sh     # 从源码安装 / 卸载（一键脚本引导后调用的也是它）
│   ├── uninstall.sh               # 卸载（安装目录 + shell 配置 + 旧版软链）
│   └── publish-mirror.sh          # 把源码快照与一键脚本发布到国内镜像服务器
├── tests/
│   ├── gen_fixtures.py            # 生成确定性测试样例（pcap/pcapng/evtx/内嵌 zip）
│   ├── test_smoke.py              # 纯标准库冒烟（CLI + 扫描行为 + shell 脚本体检）
│   └── smoke.sh                   # 冒烟总入口（语法门 + 单元冒烟 + 启动器 + 安装/卸载循环 + 引导模式）
└── .github/workflows/ci.yml       # CI：Python 3.8 / 3.11 / 3.13 三版本跑冒烟
```

## 开发与测试

```bash
# 一键冒烟：compileall 语法门 + 单元冒烟 + shell 语法 + 启动器 + 安装/卸载循环
#           + 引导模式（离线模拟）+ 自管理子命令（config / update / uninstall，离线）
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

**Q: 为什么要用 `source <(curl ...)`？`curl ... | bash` 不行吗？**
两种都行。`source` 方式下安装脚本运行在你的当前 shell 里，装完立即刷新配置、无需重开终端；
管道方式脚本在子进程里运行，装完重开终端（或手动 `source ~/.zshrc`）即可。

**Q: 一键安装提示下载失败 / raw.githubusercontent.com 连不上？**
国内网络直接用镜像地址：`source <(curl -fsSL http://101.132.165.98/dist/ctfsweep/install.sh)`。
安装脚本本身就是**先镜像、后 GitHub** 的顺序，两条都失败才报错。

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

**Q: 安装到了哪里？为什么不是 ~/.local/bin？**
与 jtool / ptool 统一为 devtools 布局：默认用户级 `~/.devtools/ctfsweep/`；`sudo` 安装则
系统级 `/Library/devtools/ctfsweep/`。补全等用户数据同规放在 `~/.devtools/ctfsweep/`
（与 ptool 的 `~/.devtools/ptool/` 一致）。

**Q: 怎么更新已安装的版本？**
`ctfsweep update` 从镜像（拿不到回退 GitHub）拉取最新快照并按**内容指纹**比对：一致就
提示「已是最新」；不一致就整装升级（文件缺失、被改动也会被检测并自动修复）。只检查不
安装用 `ctfsweep update --check`；换源用 `CTFSWEEP_MIRROR=<url>`（`none` = 只走 GitHub）。

**Q: 会不会污染我的目录？**
只有 `--extract` 会写文件，默认写到 `<抓包名>_extracted/`（可用 `--extract-dir` 改）；
若没有提取到任何文件，该目录会被自动移除。

## 许可证

MIT License
