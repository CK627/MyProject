# startupctl - 启动项扫描与管理

> 看清开机自启了什么 · 定一条策略管住它 · 用两个窗口挑选要留的和要拦的。

一台用久了的机器，开机自启项会被各种软件悄悄塞满。本项目把散落在
**launchd / systemd / XDG autostart / 注册表 / 服务 / 计划任务 / cron** 里的
启动项扫成一张说得清的清单，并用**三种模式 + 两套名单**决定哪些该留、哪些该拦。

```bash
startupctl list                      # 看清有哪些第三方启动项
startupctl whitelist process selector   # 开窗口挑要放行的进程
startupctl whitelist startup selector   # 开窗口挑要放行的启动项
startupctl mode whitelist            # 按白名单执行：只留挑中的
startupctl mode                      # 先看这么设置会结束哪些（不改动）
```

- **零第三方依赖**，纯 Python 3.8+ 标准库（`plistlib` / `configparser` / `winreg` / `/proc` / `tkinter`）。
- **三平台**：macOS（launchd · 登录项 · BTM）· Linux（systemd · XDG · cron）· Windows（注册表 · 服务 · 计划任务）。
- **只用子命令，没有 `--` 旗标**（与 ptool 同形）。
- 安装形态与 `jtool` / `ptool` 同规：装到 devtools 目录，`PATH` 上只有一个无后缀软链。

## 安装

### 命令行一键安装

```bash
source <(curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/StartupItemManagement/installer/install.sh)
```

### 国内镜像（无需 VPN）

```bash
source <(curl -fsSL http://101.132.165.98/dist/startupctl/install.sh)
```

### macOS / Linux

```bash
# 默认装到系统级（脚本内提示管理员密码）
bash installer/install.sh

# 只想装给当前用户（无需密码）→ ~/.devtools/startupctl
STARTUPCTL_USER=1 bash installer/install.sh

# 指定安装根（优先级最高，测试用）
STARTUPCTL_DEVROOT=/tmp/dev bash installer/install.sh
```

默认安装路径：macOS `/Library/devtools/startupctl`，Linux `/usr/local/devtools/startupctl`。

### 离线安装包（macOS / Linux / Windows）

三个平台各有独立安装包（与 jtool / ptool 同规），适合无网络或想双击安装的场景。
版本目录名与 `VERSION` 一致：

```
http://101.132.165.98/dist/startupctl/<版本>/startupctl-<版本>.dmg            # macOS
http://101.132.165.98/dist/startupctl/<版本>/startupctl-<版本>-linux.tar.gz  # Linux
http://101.132.165.98/dist/startupctl/<版本>/startupctl-setup-<版本>.exe     # Windows
```

- **`.dmg`**：双击 `.pkg`，装到 `/Library/devtools/startupctl`
- **`.tar.gz`**：解压后 `./installer/install-from-source.sh install`
- **`.exe`**：用户级装到 `%USERPROFILE%\.devtools\startupctl`，不需要管理员

> `.pkg` / `.exe` 都未签名。macOS 首次打开需右键「打开」，Windows 可能提示
> SmartScreen「更多信息 → 仍要运行」。

### Windows

图形安装包（推荐，与 jtool / ptool 同规）：

```
http://101.132.165.98/dist/startupctl/<版本>/startupctl-setup-<版本>.exe
```

或一行命令（无需管理员）：

```powershell
irm http://101.132.165.98/dist/startupctl/install.ps1 | iex
```

装到 `%USERPROFILE%\.devtools\startupctl`，并把 `<安装根>\bin` 追加进**用户级** PATH。
**不需要管理员**——本项目在 Windows 上是纯用户级安装（不像 ptool 那样要写机器级 PATH）。

### 安装后的目录布局

仓库布局与**安装后**布局不同（与 jtool / ptool 同规）：

```
<安装根>/bin/startupctl         →  ../lib/startupctl.sh   （无后缀软链，PATH 上唯一的名字）
<安装根>/lib/startupctl.sh      真实启动器
<安装根>/lib/startupctl/        Python 包
<安装根>/config/startupctl.conf 配置
<安装根>/completions/           zsh / bash 补全
<安装根>/uninstall              卸载脚本
```

> `bin/` 在 PATH 上，所以那里**只能有无后缀的 `startupctl` 一个名字**。真实脚本放 `lib/`，
> 否则命令名补全就会同时列出 `startupctl` 和 `startupctl.sh`（Windows 的 `.bat` 同理）。
> 仓库里的 `bin/` 是**素材目录**，整体挂上 PATH 会让 zsh 补全把 `startupctl.bat` 也列出来。

### 仓库里直接跑（不安装）

```bash
./bin/startupctl.sh list        # 仓库启动器
python3 -m startupctl list      # 或者这样
```

## 卸载

### macOS / Linux

```bash
startupctl uninstall confirm          # 用户级，跳过确认
sudo startupctl uninstall confirm     # 系统级
```

也可以直接跑安装目录里的卸载脚本（零依赖，不要求 `startupctl` 本身还能跑）：

```bash
sudo /Library/devtools/startupctl/uninstall -y
```

### Windows

控制面板 →「程序和功能」→ startupctl 卸载；或用安装目录里的卸载器静默卸载：

```powershell
& "$env:USERPROFILE\.devtools\startupctl\unins000.exe" /VERYSILENT
```

### 数据跟着项目一起删

名单与模式住在**安装根下**的 `data/guard.json`（例如
`/Library/devtools/startupctl/data/guard.json`），所以卸载会把它们一起带走，
不在主目录里留无主文件。升级不在此列：`update` 只替换功能项，`data/` 原样保留。

## 功能特性

### 扫描：只碰第三方项

**系统项永远不动，也不建议动。** 分类不确定时一律倒向"系统"：

- macOS：`com.apple.*`、`/System/Library/*` 一律按系统项，哪怕文件是伪装的。
  身份与文件名不一致会单独打一条警告——那正是"披着 Apple 名字的持久化植入"的形状。
- Linux：`systemd-*`、`dbus`、`NetworkManager`、`ssh` 等发行版前缀判系统；
  `/etc/systemd/system/` 下的真文件判第三方。
- Windows：`%SystemRoot%` 下判系统；`\Microsoft\Windows\` 命名空间的任务判系统。

每条判定都带**依据**（`origin_evidence`），`list` 的表里"来源判定"列就是它。

### 两个维度：启动项与进程

名单同时收两类东西，因为**只看一类都会漏**：

- **启动项**（launchd / systemd / 注册表 / 服务 / 计划任务）——"该不该开机起来"。
- **进程**——"现在该不该活着"。

Windows 上大量自启根本不出现在启动项列表里（组策略、服务、注册表、启动文件夹各有
各的存储），所以必须看进程；反过来只看进程又分不清"开机自己起的"和"你刚手敲的"。
两个维度**命中任一即算命中**：把一个启动项钉进白名单，它拉起的进程同样被放行。

### 三种模式

| 模式 | 含义 |
|---|---|
| `off` | 不干预，只报告（默认） |
| `deny_all` | 全部拒绝：除系统基础进程外一律结束 |
| `blacklist` | 黑名单：只结束挑中的，其余放行 |
| `whitelist` | 白名单：只放行挑中的（+系统基础进程），其余结束 |

**三种模式一律保留系统基础进程**，也一律保留你自己的 shell / 终端 / 会话——
否则第一次切到全部拒绝就把 shell 和终端一起没了，你连"关掉它"都做不到。
这是 `is_protected()` 里**先于模式判断**的一道闸，不是每个模式各写一遍的规则。

### 只有选择的时候才生效

名单为空时拒绝切换到 `deny_all` / `blacklist` / `whitelist`（退出码 3）。
空名单的白名单模式等于"除系统外全杀"，用户什么都没选，工具不该按最激进的解释动手。

切换模式时会**先打印计划**（这次会结束哪些进程），问一次确认，然后执行一次。

### 图形选择器

`whitelist` / `blacklist` 不带参数或带 `startup` / `process` 时打开**管理窗口**
（两个页签，可删除）；带 `selector` 时打开**选择窗口**（勾选加入）。

进程页按**应用分组**：同一个 `.app` 下的主进程与各 Helper 归在一起，可折叠/展开；
点组前的方框 = 整组选中或取消，点单个子行的方框 = 只选这一个。
组框有三种状态：`☐` 全未选 · `◩` 部分选中 · `☑` 全选。

窗口只在交互式终端里弹；CI / 管道里自动回退到编号清单，绝不把任务挂死。

> 进程选择器里**系统基础进程与已锁定条目是真的选不了**，不是只画成灰的。
> UI 只是提示，真正的防线在 `is_protected()`，执行前还会再查一次。

## 使用方法

### 查看

```bash
startupctl list            # 第三方（默认）
startupctl list all        # 全部
startupctl list system     # 只看系统项
```

标记列里 `[白]` / `[黑]` 表示该启动项在对应名单里。

### 挑选

```bash
startupctl whitelist                    # 管理窗口：启动项 / 进程两个页
startupctl whitelist startup            # 只看启动项那页
startupctl whitelist process            # 只看进程那页
startupctl whitelist startup selector   # 开窗口挑启动项，加进白名单
startupctl whitelist process selector   # 开窗口挑进程，加进白名单
```

黑名单把上面的 `whitelist` 换成 `blacklist` 即可。

### 定模式

```bash
startupctl mode             # 只报告：当前模式、名单条数、这次会结束哪些进程
startupctl mode whitelist   # 按白名单执行（先打印计划、问确认）
startupctl mode off         # 关闭干预
```

## 命令速查表

| 命令 | 说明 |
|---|---|
| `startupctl list` | 列出第三方启动项 |
| `startupctl list all` | 连系统项一起列 |
| `startupctl list system` | 只看系统项 |
| `startupctl mode` | 看当前模式与将会发生什么 |
| `startupctl mode off` | 关闭干预（默认） |
| `startupctl mode deny_all` | 全部拒绝 |
| `startupctl mode blacklist` | 黑名单模式 |
| `startupctl mode whitelist` | 白名单模式 |
| `startupctl whitelist` | 管理白名单（两个页签） |
| `startupctl whitelist startup` | 只看启动项那页 |
| `startupctl whitelist process` | 只看进程那页 |
| `startupctl whitelist startup selector` | 选启动项加入白名单 |
| `startupctl whitelist process selector` | 选进程加入白名单 |
| `startupctl blacklist ...` | 同上，作用于黑名单 |
| `startupctl config` | 显示配置、数据目录与模式 |
| `startupctl version` | 显示版本 |
| `startupctl help [子命令]` | 帮助 |
| `startupctl update [check]` | 检查并更新到最新版本 |
| `startupctl install` | 完整安装（从源码目录） |
| `startupctl uninstall [confirm]` | 卸载（`confirm` 跳过确认） |

> **没有 `--` 旗标**。`startupctl list --all` 会被明确拒绝（退出 2），
> 正确写法是 `startupctl list all`。

## Tab 补全

安装时自动接进 `~/.zshrc` 或 `~/.bashrc`（成对标记 `# >>> startupctl >>>`）。
仓库里也可直接 source：

```bash
source completions/startupctl.zsh     # zsh
source completions/startupctl.bash    # bash
```

补全是**位置驱动**的：`startupctl <TAB>` 列子命令，`startupctl mode <TAB>` 列四种模式，
`startupctl whitelist <TAB>` 列 `startup` / `process`，再下一层列 `selector`。

### 更新后无需手动 source

`update` 与重装都会重写补全文件，并说明当前终端是否需要重开。

## 配置文件

`<安装根>/config/startupctl.conf`（INI）。常用项：

| 键 | 默认 | 说明 |
|---|---|---|
| `SHOW_SYSTEM` | `false` | `list` 是否默认带系统项 |
| `CONFIRM` | `true` | 执行前是否要求确认 |
| `DRY_RUN` | `false` | 全局只读（等价于永远不执行） |
| `NO_GUI` | `false` | 禁用图形窗口，强制回退到编号清单 |
| `EXTRA_VENDORS` | 空 | 追加的厂商前缀 |

环境变量：`STARTUPCTL_DATA_DIR`、`STARTUPCTL_CONFIG`、`STARTUPCTL_DRY_RUN`、
`STARTUPCTL_ROOTS`（测试接缝）、`STARTUPCTL_PLATFORM`、`STARTUPCTL_MIRROR`、
`STARTUPCTL_USER`、`STARTUPCTL_DEVROOT`。

### 数据目录

数据**跟着项目走**：放在安装根下的 `data/`，不是用户主目录。

```
<安装根>/data/
└── guard.json      白/黑名单（各分 startup / process 两个维度）+ 当前模式
```

- macOS 系统级：`/Library/devtools/startupctl/data/guard.json`
- Windows：`%USERPROFILE%\.devtools\startupctl\data\guard.json`
- 仓库里直接跑：`<仓库>/data/guard.json`（已在 `.gitignore` 里）
- 覆盖位置：`STARTUPCTL_DATA_DIR=<目录>`

`data/` 归**登录用户**所有（安装时 chown），所以普通用户存名单不会被拒。

JSON，可直接查看与手改：

```json
{
  "version": 3,
  "mode": "whitelist",
  "whitelist": {
    "startup": [{"uid": "...", "anchor": "homebrew.mxcl.mysql", "kind": "launchd-agent"}],
    "process": [{"match": "proc_name", "value": "mysqld", "locked": false}]
  },
  "blacklist": {"startup": [], "process": []}
}
```

升级不碰 `data/`；卸载会连同安装根一起删除——删掉项目就不留垃圾。

## 跨平台支持

| | macOS | Linux | Windows |
|---|---|---|---|
| 启动项 | launchd plist · 登录项 · BTM 数据库 · cron | systemd · XDG autostart · cron | 注册表 Run/RunOnce · 服务 · 计划任务 · 启动文件夹 |
| 进程 | `ps` | `/proc` | `Get-CimInstance Win32_Process` |
| 结束进程 | `TERM`，`--force` 不支持；需要时用 `kill` | 同 | `taskkill` |

### 平台覆盖

- **Windows 绝不解析本地化输出**（`tasklist` / `sc query` / `schtasks /fo CSV` 在中文系统上
  列名与偏移都不同）→ 读注册表 `Services\<name>` 的 `Start` DWORD、读 `System32\Tasks` 的 XML。
- **macOS 不调用 `sfltool`**：实测非交互下挂起超过 120 秒。BTM 数据库直接按
  NSKeyedArchiver 解析。
- **Linux 不硬编码单元路径**：`systemd-analyze unit-paths` 优先，硬编码表作回退。

## 在脚本中使用

```bash
startupctl mode | grep '将结束 0'   # 体检：当前模式下不会结束任何进程
startupctl list | wc -l             # 数一下第三方启动项
```

退出码：`0` 成功 · `1` 失败 · `2` 用法错 · `3` **因安全理由被拒绝**（例如名单为空时切模式）。

脚本里别依赖交互：`mode <非 off>` 在非交互环境中会要求确认；非交互时它拒绝执行并退 1，
不会悄悄动手。

## 项目结构

```
startupctl/
├── cli.py              子命令分发（无旗标）
├── help.py             帮助文本（数据表构建，≤50 行）
└── core/
    ├── model.py        启动项模型 · 稳定 uid · 合并
    ├── classify.py     系统 / 第三方判定（不确定倒向系统）
    ├── roots.py        扫描根（测试接缝）
    ├── guard.py        策略：三种模式 + 两套名单 × 两个维度
    ├── picker.py       进程选择器 / 启动项选择器（窗口 → 终端 → 编号清单）
    ├── gui.py          tkinter 窗口：选择器与管理窗口
    ├── enforce.py      决策与结束进程
    ├── proc.py         进程枚举 · 与启动项关联
    └── selfmgr.py      自管理（update / install / uninstall）
backends/               darwin · linux · windows（扫描与关联）
installer/              安装、卸载、打包（macOS / Linux / Windows）
tests/                  冒烟与契约检查
```

## 常见问题

### Q: `startupctl list --all` 报"不支持选项"？

本工具**只用子命令**（与 ptool 一致）。用 `startupctl list all`。

### Q: 切模式时被拒绝（退出码 3）？

名单是空的。白名单模式下空名单等于"除系统外全杀"，所以工具拒绝执行。
先 `startupctl whitelist process selector` 挑几项。

### Q: 窗口没弹出来？

只在交互式终端里弹。`CI` / 管道 / 重定向会回退到编号清单；也可以用
`config` 里的 `NO_GUI=true` 强制回退。

### Q: 会不会把系统进程结束掉？

不会。`is_protected()` 在**任何模式**下都先于模式判断，系统基础进程、你的 shell、
终端与会话永远受保护。全部拒绝模式也给你留一条能敲命令的路。

### Q: 名单文件能不能手改？

能，它就是 JSON。手改后 `startupctl mode` 会按新内容计算——但空名单仍会被拒绝执行。

## 开发与测试

```bash
bash tests/smoke.sh             # 完整冒烟：语法门 · 单元 · 布局 · 安装 · 更新 · 编码
python3 -I tests/test_smoke.py  # 只跑单元与安全不变量
```

CI 矩阵：`ubuntu-latest` / `macos-latest` / `windows-latest` × Python `3.8` / `3.11` / `3.13`。

## 许可证

MIT
