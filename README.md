# ctfsweep - CTF 流量 / 日志 / 注册表 快速扫描器

> 面向 CTF 与应急响应的取证扫描工具：把流量包、事件日志、注册表里"可疑的东西"
> 一次性翻出来，并按**置信度分级**输出——高置信可直接核验，低置信留作人工排查线索。
>
> 零依赖（纯标准库，Python 3.8+），`python3 -m ctfsweep <文件或目录>` 即用。

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
  并给出**启发式拼接尝试**；跨文件自动汇总全局片段池
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

- 🧾 输出结构：逐文件报告 → 拼接建议 → **高置信候选汇总** → 统计（高/中/低条数）
- 🎛️ `--min-score` 过滤、`--limit` 截断、`--depth` 控制解码深度、`--no-decode` 关闭解码
- 🛡️ 单文件出错不中断，继续扫下一个

### 工程特性

- ⚡ **零第三方依赖**：任意 Python 3.8+，无需 pip install 任何东西
- 📁 目录递归扫描；260MB 注册表全量 10 秒内、常规抓包亚秒级
- 🧰 完整工程配套：CLI 包装器、安装脚本、shell 补全、配置文件、冒烟测试、CI

## 环境要求

- Python **3.8+**（无第三方依赖）
- 支持 macOS / Linux / Windows

## 安装

### 免安装直接运行（推荐先试）

```bash
cd /path/to/CtfSweep
python3 -m ctfsweep <文件或目录> [选项]     # 在项目根目录内
./bin/ctfsweep <文件或目录> [选项]          # 或使用仓库启动器（任意目录）
```

### 安装到 PATH

```bash
# 安装到 ~/.local（默认，无需 sudo）
./installer/install.sh

# 或指定前缀
./installer/install.sh --prefix /usr/local
```

安装完成后 `ctfsweep` 命令即全局可用（若 `~/.local/bin` 不在 PATH，脚本会给出提示）。

### 卸载

```bash
./installer/install-from-source.sh uninstall      # 只移除本仓库创建的软链接
```

### Windows

在项目目录内直接运行 `bin\ctfsweep.bat`，或把项目根目录加入 `PYTHONPATH` 后使用
`python -m ctfsweep`。

## 快速开始

```bash
# 扫描一个抓包（默认输出 >= 0.40 的全部候选）
ctfsweep capture.pcap

# 只看高置信结果（直接要 flag 时）
ctfsweep capture.pcap --min-score 0.85

# 扫描并提取流量中的文件（含加密 zip 自动尝试口令）
ctfsweep capture.pcap --extract

# 批量扫描整个目录（含 evtx / reg / 文本）
ctfsweep ./logs/

# 事件日志搜索特定关键词
ctfsweep Security.evtx -k flag1,flag2,flag3
```

## 使用方法

### 命令行选项

| 选项 | 说明 |
|------|------|
| `<文件或目录>` | 必填。支持单个文件或目录递归 |
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

```bash
# zsh：把 completions/ctfsweep.zsh 所在目录加入 fpath 后重开终端
# bash：source completions/ctfsweep.bash，或放入 /etc/bash_completion.d/
```

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
│   ├── cli.py                     # 命令行解析 / 配置加载 / 批量扫描与汇总
│   └── core/
│       ├── utils.py               # 共享正则、编码尝试、置信度分级
│       ├── capture.py             # pcap/pcapng 解析 + 四层解析（TCP/UDP/DNS）
│       ├── decode.py              # hex/base64 解码链、片段探测、加壳与拼接建议
│       ├── blobscan.py            # 字节块扫描原语（findings 去重 + 多策略扫描）
│       ├── http.py                # 请求序列 / POST 字段 / JWT / 事务配对
│       ├── extract.py             # 文件雕刻、口令池、zip 弱口令与假加密绕过
│       ├── scanner.py             # 抓包扫描与原始文件扫描的编排
│       └── report.py              # 置信度报告渲染
├── bin/
│   ├── ctfsweep                   # 启动器（macOS / Linux，支持软链，定位仓库根）
│   └── ctfsweep.bat               # 启动器（Windows）
├── config/
│   └── ctfsweep.conf              # 配置文件模板
├── completions/
│   ├── ctfsweep.zsh               # zsh 补全
│   └── ctfsweep.bash              # bash 补全
├── installer/
│   ├── install.sh                 # 安装到 $PREFIX/bin（默认 ~/.local）
│   └── install-from-source.sh     # 源码安装 / 卸载（uninstall 只删本仓库的软链）
├── tests/
│   ├── gen_fixtures.py            # 生成确定性测试样例（pcap/pcapng/evtx/内嵌 zip）
│   ├── test_smoke.py              # 纯标准库冒烟（19 项断言）
│   └── smoke.sh                   # 冒烟总入口（语法门 + 单元冒烟 + 启动器）
└── .github/workflows/ci.yml       # CI：Python 3.8 / 3.11 / 3.13 三版本跑冒烟
```

## 开发与测试

```bash
# 一键冒烟：语法门（compileall） + 19 项单元冒烟 + shell 语法 + 启动器
bash tests/smoke.sh

# 单独跑单元冒烟
python3 tests/test_smoke.py

# 手动生成测试样例（确定性输出）
python3 tests/gen_fixtures.py /tmp/fixtures
```

CI（`.github/workflows/ci.yml`）在 ubuntu 上以 Python **3.8 / 3.11 / 3.13** 三个版本
运行同一套冒烟，保证最低版本承诺不漂移。

## 常见问题

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

**Q: 会不会污染我的目录？**
只有 `--extract` 会写文件，默认写到 `<抓包名>_extracted/`（可用 `--extract-dir` 改）；
若没有提取到任何文件，该目录会被自动移除。

## 许可证

MIT License
