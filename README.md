# startupctl - 启动项扫描与管理

> 看清开机自启了什么 · 管住不该常驻的 · 保住自己要留的。

一台用久了的机器，开机自启项会被各种软件悄悄塞满。本项目解决的就是这件事：
把散落在 **launchd / systemd / XDG autostart / 注册表 / 服务 / 计划任务 / cron**
里的启动项和随之常驻的第三方进程，扫成一张说得清的清单，并提供**可回退**的禁用与清理。

```bash
startupctl list --third-party     # 看清有哪些
startupctl check                  # 只读体检：干不干净
startupctl clean --dry-run        # 先看会动哪些，不动手
startupctl whitelist add homebrew.mxcl.mysql   # 要留的留下来
```

- **零第三方依赖**，纯 Python 3.8+ 标准库（`plistlib` / `configparser` / `winreg` / `/proc`）。
- **三平台**：macOS（launchd · 登录项 · BTM）· Linux（systemd · XDG · cron）· Windows（注册表 · 服务 · 计划任务）。
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
startupctl uninstall -y            # 用户级
sudo startupctl uninstall -y       # 系统级
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

### 数据一律保留

无论哪个平台，卸载都**不动数据目录**：`whitelist.json`（你逐条确认过的允许清单）、
`backups/`（`restore` 的唯一来源）、`scans/`（快照）。要清得显式执行
`whitelist remove` / `backup prune` / `clear`。

## 功能特性

### 为什么它只碰第三方项

本机实测：**第三方启动项 40 个，而系统自带的有 911 个**。靠肉眼从 911 里挑出那 40 个
是不现实的，所以分类是自动的——而分类一旦出错，代价不对称：

| 出错方向 | 后果 |
|---|---|
| 系统项被误判为第三方 | 它变成可清理，`clean` 可能动它 → **有害且难恢复** |
| 第三方项被误判为系统项 | 用户加 `--include-unknown` 就能处理 → **只是麻烦** |

所以工具一律往安全那侧倒，并把这条规则**写成了结构性防线**：

> 分类不确定时返回 `unknown`，而 `unknown` 被当作系统项处理；
> 位于系统级、非用户可写路径的项，**结论永不为第三方**。

几条具体的判据：

- **`com.apple.*` 一律按系统项**——哪怕它是伪装的。改不动真系统项 vs 可能动到伪装项，
  前者代价小得多（fail-closed）；真正的信号交给「身份与文件名不一致」那条警告让人去看。
- **`uid == 0` 不是判据**——`com.docker.vmnetd`、ClashX 的 helper 都以 root 跑，都是第三方。
- **`program` 落在 `/usr/bin` 不是系统项的证据**——三方守护进程经常 exec `/usr/bin/python3`。
- 每一项都带**分类依据**（`list --long` / `show` 打印），可以复核：

```
$ startupctl show docker.vmnetd
来源判定      第三方 / high
判定依据      位于 /Library/PrivilegedHelperTools（第三方特权 helper）
可被本工具改动 是
```

### 安全模型

工具会改**用户的系统启动状态**，所以规矩是不协商的：

| 规矩 | 具体做法 |
|---|---|
| **预览在前** | 改动类命令一律先打印计划再动手；**加不加 `-y` 都打印**（`-y` 的意思是"我审过计划了"）。计划由后端的纯函数 `plan()` 生成，预览与执行**共用同一份实现**，不可能漂移。 |
| **管道里必须显式确认** | 非交互环境且没给 `-y` → 拒绝执行、退出 1、零改动。 |
| **先备份再变更** | 备份写盘后立即校验 sha1；校验不过**中止该项**，绝不带着坏备份下手。 |
| **remove 是搬移不是删除** | 文件移进 `<数据根>/backups/`，`restore` 能拿回来——这是 `clean` 敢做的全部理由。 |
| **系统项是拒绝，不是警告** | 退出码 **3**，与"失败"(1)、"用法错"(2) 区分开，脚本能识别。 |
| **不谎报做不到的事** | 改不动就报 `已跳过（需要 root）` 并给出确切命令，**绝不报"已禁用"**。 |
| **绝不自行提权** | 不在 `clean` 循环中途弹密码（那会训练用户条件反射输密码）。需要时用一次 `--sudo`，或按提示自己 `sudo` 重跑。 |
| **残缺视图上不动手** | 有读不到的根（`needs_root`）时 `clean` 直接拒绝。 |

退出码：`0` 成功 · `1` 失败 · `2` 用法错 · `3` **因安全理由被拒绝**。

#### 白名单

```bash
startupctl whitelist add homebrew.mxcl.mysql --reason "本机 MySQL 要常驻"
startupctl whitelist add --glob 'com.docker.*'        # 通配
startupctl whitelist add --vendor com.google          # 整个厂商
startupctl whitelist doctor                           # 报出未命中的条目（**不自动清理**）
```

**不变量（有专门的测试）：白名单只能收窄破坏性集合，永远不能放宽它。**
`origin` 硬闸在代码里独立于、且**先于**白名单求值，所以任何白名单条目都无法让一个
系统项变得可改。

设计上的两个刻意选择：

- **白名单项照常列出**（只标 `[白]`），不隐藏。会隐藏东西的白名单，是用户会忘记自己写过的白名单。
- **`whitelist doctor` 只报告、不自动删**。静默删掉一条允许清单条目，正是本工具要防的那类安全惊吓。

### 改动一定会被核对

怕的是"选了半天其实没生效"——那是最难受的失败形态（选错了看得见，没生效看不见）。
所以**每一次改动都会写盘后重新读回来逐条核对**：

```
$ startupctl guard choose
选择清单已写入并核对无误: 3 条（其中锁定 1）
  文件: ~/.devtools/startupctl/guard.json

现在生效的规则（共 3 条）:
#  匹配方式  值           状态  备注
-  --------  -----------  ----  ----------
0  进程名    mysqld       锁定  guard choose
1  进程名    SomeTool           guard choose
2  进程名    Backend            guard choose
```

磁盘上的内容与预期不符时**直接报错并返回非零**，绝不打出"已更新"就完事。纯文本模式
下打错编号也会明确报「没有生效，可用编号 1-N」，而不是静默跳过。

## 进程守护

启动项管住了，还得管"跑起来之后"。**模式和选择是分开的两件事**：

```
mode       选策略模式 —— 只决定"用哪一份清单"，不改动清单内容
choose     往当前模式对应的那份清单里挑进程 —— 唯一会启动图形窗口的命令
```

| 模式 | 用哪份清单 | 行为 |
|---|---|---|
| `off` | 不用 | **默认**。不干预，只报告 |
| `whitelist` | 白名单 | 只放行挑中的那些，其余结束 |
| `blacklist` | 黑名单 | 只结束挑中的那些，其余放行 |
| `deny_all` | 白名单作**豁免** | 除系统基础进程外一律结束，白名单里的留着 |

```bash
startupctl guard mode whitelist      # 1. 选模式（不动清单内容）
startupctl guard choose              # 2. 打开图形窗口挑进程 → 写进白名单
startupctl guard check               #    只读：现在会结束哪些
startupctl guard arm                 #    执行一轮
startupctl guard arm --watch         #    持续监视新起的进程（Ctrl-C 停）
```

### 白名单和黑名单是两份**互相独立**的清单

以前是一份清单、含义随模式解释 —— 那样你在白名单里挑完要放行的东西，一切到黑名单，
同一批条目**立刻变成"要杀"**。现在两份分开，切模式只是"换用哪一份"：

```
$ startupctl guard list
白名单（1 条）← 当前模式在用
0  进程名    AllowedThing

黑名单（1 条）
0  进程名    BannedThing

两份清单互相独立；锁定条目在任何模式下都不结束。
```

`guard add` 默认加进当前模式那份，用 `--whitelist` / `--blacklist` 显式指定另一份。

### 只有选择的时候才生效

**起作用的那份清单是空的，就不许执行。** 白名单为空时它等于"除系统外全杀"——
你什么都没选，工具不该按最激进的解释动手：

```
$ startupctl guard arm
错误: 拒绝执行：白名单是空的 —— 此时白名单模式等于"除系统外全杀"。
      请先选择要放行的进程: startupctl guard choose
  白名单模式下空清单等于"除系统外全杀"，所以这里先拦住你。
      → 退出码 3
```

### 图形窗口只在 `guard choose` 时启动

GUI 不是常态 —— 一个日常命令突然弹出窗口既唐突，又会挡住脚本化使用。
所以只有 `guard choose` 会开窗，其余走终端界面/纯文本：

```bash
startupctl guard choose              # 图形窗口（tkinter，勾选框）
startupctl guard choose --tui        # 强制终端界面（curses）
startupctl guard choose --plain      # 强制纯文本编号清单
```

三种界面**共用同一份"能不能选"的规则**：

| 开关 | 界面 |
|---|---|
| （默认） | 图形窗口 → 无图形环境时自动退到终端界面 → 再退到纯文本，**并说明为什么退** |
| `--tui` | 只用终端界面（curses：空格选中、`L` 锁定、`a` 全选、`/` 筛选） |
| `--plain` | 只用纯文本编号清单（`1,3,5-8`，编号后加 `!` 表示锁定） |

窗口长这样（点「选择」列勾选、点「锁定」列钉住，双击整行也能勾）：

```
┌ startupctl — 选择进程 ─────────────────────────────────────────┐
│ 勾选要纳入策略的进程。灰底的「系统」行是系统基础进程，          │
│ 任何模式下都不会被结束，也点不动。                              │
│ 筛选: [ mysqld          ]   （按进程名或路径过滤）             │
├──────┬──────┬───────────────┬────────┬────────────────────────┤
│ 选择 │ 锁定 │ 进程名        │ PID    │ 可执行文件 / 命令行    │
├──────┼──────┼───────────────┼────────┼────────────────────────┤
│ 系统 │      │ WindowServer  │ 100    │ /System/Library/...    │ ← 灰底，点不动
│  ✓   │  锁  │ mysqld        │ 200    │ /opt/db/bin/mysqld     │ ← 浅黄=锁定
│  ✓   │      │ SomeTool      │ 201    │ /opt/homebrew/bin/tool │
│      │      │ AdobeIPCBroker│ 1603   │ /Library/Application…  │
├──────┴──────┴───────────────┴────────┴────────────────────────┤
│ [全选可选] [全不选] [反选]   共 903 · 已选 2 · 锁定 1 · 系统 765 │
│                                        [取消]  [确定]          │
└───────────────────────────────────────────────────────────────┘
```

**不用记键盘、不用打编号**——这正是要图形窗口的原因：编号打错是看不见的失败。

### ★ 系统基础进程在三种模式下都不会被结束

**「全部拒绝」不是"什么都杀"**——它和另外两个模式一样保留系统基础进程。
本机实测：903 个进程里 765 个是系统基础进程，在任何模式下都受保护。

这不是每个模式各自写了一遍的规则，而是决策函数里**先于模式判断**的一道硬闸
（`guard.verdict()` 第一步就查 `is_protected()`）：

```
受保护 → 直接返回 PROTECTED（无论什么模式）
否则   → 才按模式判定 allow / deny
```

所以将来新增模式会自动继承这条保证。判据全部走"判不准就当受保护"的方向：

- pid ≤ 1、内核线程、系统账户（`_windowserver` 之类）
- 权威名表（`WindowServer` · `launchd` · `systemd` · `csrss.exe` · …）
- 可执行文件在系统路径（`/System/` · `%SystemRoot%` · `/lib/systemd/` …）
- 分类判定为系统自带
- **root 拥有且出处无法判定**的进程
- **本工具自身的进程链**（否则等于锯自己脚下的地板）
- **shell / 终端 / 会话**（否则你会被锁在门外，连关掉它都做不到）
- **你锁定的条目**（见下）

**系统基础进程与已锁定条目是真的选不了，不是只显示成灰的**——`Rows.toggle()` 会拒绝，
返回前再过一遍 `is_protected()`。UI 上的灰与 `[系统]` 标记只是提示；真正的防线在
`guard.is_protected()`，而执行器动手前**会再查一次**（预览到执行之间进程表会变，
而且 `guard.json` 是可以手改的）。`guard add WindowServer` 同样会被结构性拒绝，退出码 3。

### 全部拒绝**绝不含你自己**

否则第一次 `arm` 下去 shell 和终端一起没了，你连"关掉它"都做不到——
一个把自己锁在门外的工具，安全性是负的。

所以 **shell · 终端 · 会话**一律受保护，任何模式下都不结束：

```
-zsh  bash  sh  fish  pwsh  cmd          ← shell
Terminal  iTerm2  WezTerm  Alacritty …   ← 终端
tmux  screen  sshd  login  sudo          ← 会话
```

`guard check` 会把它们单独点出来："其中 N 个是 shell / 终端 / 会话——保证你还能操作"。

代价要说清楚：**恶意程序若把自己命名成 `bash`，就能躲过这一条**。这是刻意取舍——
宁可放过一个改名的进程（它还有别的判据可能命中，而且你在 `guard check` 里看得见），
也不能让工具把用户锁在门外。

### 锁定条目

普通条目在各模式下含义不同（黑名单里是"要杀"、白名单里是"放行"）。
**锁定条目的含义与模式无关——一律"别动它"**，等价于你自己钉住的东西：

```bash
startupctl guard lock mysqld        # 锁定：任何模式下都不结束
startupctl guard unlock mysqld      # 解除
startupctl guard add --value foo --lock   # 加的时候直接锁定
```

选择器里按 **`L`** 也可以直接锁定/解锁。锁定行与系统基础进程一样置灰、选不动：

```
选择进程 — 共 903，已选 2，系统 765（不可选），锁定 1
[系统] WindowServer   /System/Library/...      ← 系统，永远选不动
[锁定] mysqld         /opt/db/bin/mysqld       ← 你锁的，按 L 解锁
[x]   SomeTool       /opt/homebrew/bin/tool
```

### 另两点提醒

1. 全部拒绝会拒绝**任何**新起的非系统进程——**包括你自己刚敲的命令**（但 shell 本身
   在上面那层保护里，所以你还敲得进命令）。这是它的设计意图，确实会妨碍干活，
   所以必须由你显式启动。
2. 它**绝不使用 sudo**：root 或他人的进程会被跳过并提示，而不是偷偷提权。
   在一个自动循环里提权，等于让工具替你做你没批准的破坏。

## 使用方法

### 查看与体检

```bash
startupctl list                      # 只列第三方（默认）
startupctl list --all --long         # 含系统项，并显示分类依据
startupctl list --vendor com.docker  # 按厂商
startupctl list --running            # 只看正在跑的
startupctl show com.docker.vmnetd    # 单项详情（来源 · 命令 · 分类依据 · 原始内容）
startupctl show docker.vmnetd --raw  # 附上原始 plist / 注册表内容
startupctl check                     # 只读体检（干净退 0，有可清理项退 1）
startupctl proc --third-party        # 三方进程与启动项聚合
startupctl proc --orphans            # 没有对应启动项的三方进程
```

### 让一个项目开机自启

```bash
startupctl add 我的服务 /path/to/run.sh --run-at-load
```

默认只写**用户级**位置（`~/Library/LaunchAgents` / `~/.config/systemd/user` /
`HKCU\...\Run`），并且会先把要写入的内容打印出来给你看。

### 载荷漂移

保留 `Label` 却换掉 `ProgramArguments`，是持久化植入的典型手法——**身份没变，行为变了**。
`scan --save` 存快照，`scan --diff` 报这种变化：

```bash
startupctl scan --save
# ... 过一段时间 ...
startupctl scan --diff
# 新增 1 · 消失 0 · 载荷变化 1
# 载荷漂移（身份没变，但「要执行什么」变了）:
#   · com.example.thing
#       旧: /opt/thing/bin/thing --serve
#       新: /tmp/payload
```

## 命令速查表

| 命令 | 说明 | 示例 |
|------|------|------|
| `startupctl list [筛选]` | 扫描并列启动项（默认只列第三方） | `startupctl list --third-party` |
| `startupctl show <项>` | 单项详情：来源 · 命令 · 分类依据 · 原始内容 | `startupctl show docker.vmnetd` |
| `startupctl check` | 只读体检（干净退 0，否则退 1） | `startupctl check` |
| `startupctl scan --save\|--diff` | 存快照 / 比对载荷漂移 | `startupctl scan --diff` |
| `startupctl disable <项>...` | 禁用（可逆） | `startupctl disable com.docker.vmnetd` |
| `startupctl enable <项>...` | 恢复启用 | `startupctl enable com.docker.vmnetd` |
| `startupctl remove <项>...` | 移到备份目录（不删文件） | `startupctl remove netdisk_service` |
| `startupctl add <名> <命令>` | 新建用户级自启项 | `startupctl add 我的服务 /path/run.sh` |
| `startupctl restore [时间]` | 从备份还原**并重新启用** | `startupctl restore last` |
| `startupctl backup list\|prune` | 看备份 / 按保留策略清理 | `startupctl backup list` |
| `startupctl clean [-y]` | 批量禁用第三方项（预览在前） | `startupctl clean --dry-run` |
| `startupctl proc [--orphans]` | 进程视图与启动项聚合 | `startupctl proc --orphans` |
| `startupctl kill <pid\|项>` | 结束进程（先 TERM，`--force` 才 KILL） | `startupctl kill 369` |
| `startupctl whitelist add <项>` | 加入白名单 | `startupctl whitelist add mysqld` |
| `startupctl whitelist doctor` | 报出未命中的条目（不自动清理） | `startupctl whitelist doctor` |
| `startupctl guard mode <模式>` | 看/设进程守护模式 | `startupctl guard mode whitelist` |
| `startupctl guard choose` | 打开选择器挑进程（唯一会开窗的命令） | `startupctl guard choose` |
| `startupctl guard lock <值>` | 锁定：任何模式下都不结束它 | `startupctl guard lock mysqld` |
| `startupctl guard check` | 只读：现在会结束哪些 | `startupctl guard check` |
| `startupctl guard arm [--watch]` | 执行一轮 / 持续监视 | `startupctl guard arm --watch` |
| `startupctl update [--check]` | 拉取最新快照并重装 | `startupctl update --check` |
| `startupctl uninstall [-y]` | 卸载（白名单与备份保留） | `startupctl uninstall -y` |
| `startupctl config` | 显示运行信息与配置 | `startupctl config` |
| `startupctl help` | 显示帮助 | `startupctl help` |

> 三个平台统一使用 `startupctl`（无后缀）。macOS / Linux 上真实脚本装在
> `<安装根>/lib/startupctl.sh`，`<安装根>/bin/startupctl` 是指向它的软链接——
> `bin/` 在 PATH 上，若把 `.sh` 也放在那里，命令名补全就会同时列出两个名字。
>
> 每个子命令的完整选项用 `startupctl <子命令> --help` 查（顶层帮助只是一份 ≤50 行的瘦索引）。

## Tab 补全

安装时会自动接线补全脚本（zsh / bash 均支持），重开终端即生效。

```bash
startupctl <TAB>          # 子命令 + 文件
startupctl list <TAB>     # list 的专属选项（--all/--running/--vendor …）
startupctl guard <TAB>    # status / mode / choose / lock / …
startupctl --kind <TAB>   # 启动项类型清单
startupctl -<TAB>         # 全部选项，同义短/长合并成一行显示（如 "-y --yes"）
```

补全脚本位于安装目录的 `completions/` 下，由安装 / 更新自动刷新，不需要手动维护。
它遵循**位置驱动**：第一个参数位只出「子命令 + 文件」，选项只在当前词以 `-` 开头时出现。

### 更新后无需手动 source

安装时会在补全脚本里定义一个 `startupctl` 包装函数（`.zshrc` / `.bashrc` 只负责 source 它）。
函数在**父 shell**中执行，所以 `startupctl update` 跑完后会立刻重新加载补全——
不需要手动 `source ~/.zshrc`，也不需要重开终端。

> 原理：脚本本身是子进程，无法修改父 shell 的环境，所以 install.sh 里调用
> `source ~/.zshrc` 是无效的（只影响脚本自己的 subshell）。只有 shell 函数才能真正生效。
>
> 例外：**首次安装**时函数还没被定义（`.zshrc` 正在被写入），所以第一次仍需
> 重开终端或 `source ~/.zshrc`。之后的每次 update 都是自动的。

## 配置文件

`~/.devtools/startupctl/startupctl.conf`（也可以用 `--config` 指定）。完整项见
`config/startupctl.conf`，几个关键的：

```ini
# list 默认只列第三方
SHOW_SYSTEM=false

# clean 默认只处理高置信度
MIN_CONFIDENCE=high

# true = 所有改动只预览
DRY_RUN=false

# 备份保留份数 / 不足这些天的 prune 不删
BACKUP_KEEP=20
BACKUP_MIN_DAYS=7

# 追加"认定为第三方"的厂商前缀（本机自研软件用），如 com.mycorp,org.mylab
EXTRA_VENDORS=
```

> ⚠️ `TRUST_UNKNOWN=true` 会把"判不出来"的项也当作第三方，等于绕过
> 「不确定就倒向安全那侧」的整条防线。只在临时排查时打开。

环境变量（`STARTUPCTL_` 前缀）：`DATA_DIR` · `CONFIG` · `DRY_RUN` · `MIRROR` ·
`GITHUB` · `USER` · `DEVROOT` · `ROOTS`（把扫描根重定向到别处，测试用）。

### 数据目录

`~/.devtools/startupctl/`（用户级安装下就是安装根）：

```
whitelist.json   白名单
backups/         备份 —— restore 的唯一来源
scans/           扫描快照
```

**三样都永不自动删除**：安装、更新、卸载都不碰它们。`clear` 只清 `scans/`；
白名单与备份各有专属命令（`whitelist remove` / `backup prune`）。

## 跨平台支持

| 系统 | 主脚本 | 安装路径 | 配置文件 | 入口 |
|------|--------|----------|----------|------|
| macOS | `startupctl`（→ `lib/startupctl.sh`） | `/Library/devtools/startupctl/` | `…/config/startupctl.conf` | `installer/` |
| Linux | `startupctl`（→ `lib/startupctl.sh`） | `/usr/local/devtools/startupctl/` | `…/config/startupctl.conf` | `installer/` |
| Windows | `startupctl.bat` | `%USERPROFILE%\.devtools\startupctl\` | `…\config\startupctl.conf` | `installer/windows/` |

用户级安装（`STARTUPCTL_USER=1`）三平台都是 `~/.devtools/startupctl`。

> Windows 上是**纯用户级**安装：不需要管理员，PATH 走 `HKCU\Environment`。
> 这与 ptool 不同——ptool 的 shim 必须在机器级 PATH 最前才能生效，所以要提权；
> 本工具没有 shim，一个用户级 `bin` 目录就够了。

### 平台覆盖

| 平台 | 扫描来源 |
|---|---|
| **macOS** | `launchd`（系统 / 全局 / 用户三档）、登录项（AppleScript）、**BTM**（系统设置「登录项与扩展」的同一份数据库）、`crontab`、遗留 `StartupItems` |
| **Linux** | systemd（系统 / 用户 / 发行版 / 本地各层）、XDG autostart（含遮蔽关系）、`init.d`、`/etc/cron.d` 与用户 crontab |
| **Windows** | 注册表 `Run`/`RunOnce`（HKLM 双视图 + HKCU）、`StartupApproved`、启动文件夹、服务、计划任务 |

几个实现上的取舍值得说明：

- **macOS 的 BTM 直接读数据库，不调 `sfltool`**。实测非交互 shell 下 `sfltool dumpbtm`
  挂起超过 120 秒（15 秒到 300 秒以上剧烈波动）；而
  `/private/var/db/com.apple.backgroundtaskmanagement/BackgroundItems-v18*.btm`
  权限是 `644`，`plistlib` 能直接解析（NSKeyedArchiver）。BTM 记录若指向已扫到的 plist，
  会**折进那一项**而不是重复列出。
- **Windows 绝不解析本地化输出**。`tasklist` / `sc query` / `schtasks /fo CSV` 在中文
  Windows 上是本地化的，照着写会在英文系统上"正常"、在中文系统上**静默误解析**。
  所以服务读注册表 `HKLM\SYSTEM\CurrentControlSet\Services\<name>` 的 `Start` DWORD，
  计划任务读 `System32\Tasks\<path>` 的 XML。
- **Linux 用 `/proc` 而非 `ps`**：`cmdline` 是 NUL 分隔 → 精确 argv，且
  `/proc/<pid>/cgroup` 能一次拿到所有进程的所属单元，**扛得住 double-fork 与 setsid**。
- **进程关联是尽力而为**，每条都标注关联方式（`launchctl` / `cgroup` / `parent` / `path`）。
  没能关联上的会如实显示为「无对应启动项」，而不是硬凑一个。

## 在脚本中使用

退出码是给脚本用的接口：`0` 成功 · `1` 失败 · `2` 用法错 · `3` **因安全理由被拒绝**。

```bash
#!/bin/bash

# 只读体检：干净退 0，有可清理项退 1。适合放进 dotfiles 的 post-install 钩子
if startupctl check >/dev/null; then
    echo "开机启动项是干净的"
fi

# 把第三方启动项喂给别的工具（机器可读）
startupctl list --third-party --json | jq -r '.[].key'

# 批量禁用但先审计划：--dry-run 与真正执行打印的计划逐字相同
startupctl clean --dry-run
startupctl clean -y

# 退出码 3 = 被安全拒绝（"这东西不许动"），不是"命令用错了"
startupctl disable com.apple.Finder; echo $?      # → 3
```

> CI 里可以设 `STARTUPCTL_DRY_RUN=1` 全局强制预览——即使脚本写错，mutator 也无法行动。

## 项目结构

```
startupctl/
├── VERSION                     # 版本号，startupctl update 据此判断是否需要更新
├── README.md                   # 本文档
├── CLAUDE.md                   # 给 AI 协作用的约定与踩坑记录
├── pyproject.toml
├── bin/
│   ├── startupctl.sh           # 主脚本 (macOS / Linux)
│   └── startupctl.bat          # 主脚本 (Windows)
├── config/
│   └── startupctl.conf         # 配置文件模板（首次安装时复制）
├── completions/
│   ├── startupctl.zsh          # zsh 补全（静态素材，安装后整体复制）
│   └── startupctl.bash         # bash 补全
├── startupctl/                 # Python 包
│   ├── cli.py                  # 子命令分发
│   ├── help.py                 # 帮助文本（由数据表构建，行数有上限断言）
│   ├── core/                   # 模型 / 分类 / 安全 / 策略 / 路径 …
│   └── backends/               # darwin · linux · windows 三个后端
├── installer/
│   ├── install.sh              # 一键安装（macOS / Linux）
│   ├── install.ps1             # 一键安装（Windows）
│   ├── install-from-source.sh  # 从源码安装（分三级：DEVROOT / USER / 系统）
│   ├── deploy.sh               # 布局的唯一实现（装 / 更 / 测三处共用）
│   ├── shell-setup.sh          # shell 接线（成对标记，幂等）
│   ├── uninstall.sh            # 卸载
│   ├── publish-mirror.sh       # 发布到国内镜像
│   └── windows/
│       ├── install.bat         # Windows 安装
│       ├── uninstall.bat
│       ├── startupctl.iss.in   # Inno Setup 脚本（打包 .exe）
│       ├── build-from-mac.sh   # 在 macOS 上驱动 exe 构建
│       └── build-remote.bat    # 在 Windows 上跑 ISCC
├── tests/
│   ├── smoke.sh                # 完整冒烟（含安装/卸载/更新循环）
│   ├── test_smoke.py           # 单元冒烟 + 安全不变量
│   └── fixtures/roots/         # 扫描根夹具（测试绝不碰真机）
└── .github/workflows/ci.yml    # CI：三平台 × Python 3.8/3.11/3.13
```

> 注意仓库布局与**安装后**布局不同：安装时 `bin/startupctl.sh` 会被复制到
> `<安装根>/lib/startupctl.sh`，并在 `<安装根>/bin/startupctl` 建立指向它的软链接。
> `bin/` 在 PATH 上、`lib/` 不在，这样保证 PATH 里只有无后缀的 `startupctl` 一个名字。

## 常见问题

### Q: `clean` 说"扫描不完整"拒绝运行

有读不到的扫描根（通常是权限）。这是刻意设计：**不在残缺视图上做安全决定**。
按提示用 `sudo startupctl clean` 重跑，或先 `startupctl list --errors` 看是哪个根读不到。

### Q: 为什么 `disable` 一个明明是第三方的项却退出 3

退出码 3 是**因安全理由被拒绝**。常见两种：判成了系统项（`show` 会打印判定依据），
或者它以 root 运行、当前不是管理员。`startupctl show <项>` 的「判定依据」
就是解释这个的——分类结论永远可复核。

### Q: 会不会误删系统项

不会，而且是**结构性**保证：`origin` 硬闸在 `manage` 里独立于白名单求值，
系统项一律 `Refused`；`mutable` 字段默认 `False`；执行器动手前再查一次。
测试里有一条专门的反射断言，遍历「每个后端 × 每个变更操作」验证它们遇系统项必拒。

### Q: 白名单加了，`clean` 还动它

先确认 `whitelist doctor` 里那条命中了没有（未命中的条目会列出来）。
另外白名单**只影响 `clean` 的候选集**——它是"少动几项"，不是"永远不许动"；
你显式敲 `startupctl disable <项>` 时它不会拦你。

### Q: 更新之后白名单和备份还在吗

在。安装、更新、卸载都不碰数据目录（`whitelist.json` · `backups/` · `scans/`）。
冒烟测试里为此埋了哨兵文件，每次都要断言它们还在。

### Q: 为什么 `guard arm` 要我先 `choose`

因为**空清单不许执行**。白名单为空时它等于"除系统外全杀"——你什么都没选，
工具不该按最激进的解释动手。黑名单为空同理（没有要结束的对象）。

### Q: 图形窗口没弹出来

`guard choose` 只在**交互式终端**下开窗（CI / 管道里弹一个等人点的窗口会让任务直接挂住）。
无图形环境时会自动退到终端界面，再退到纯文本，并说明为什么退。
也可以用 `--tui` / `--plain` 显式指定。

### Q: 提示 "permission denied"

用安装脚本重新安装（系统级需要 sudo），或手动补权限：

```bash
# macOS
sudo chmod +x /Library/devtools/startupctl/lib/startupctl.sh

# Linux
sudo chmod +x /usr/local/devtools/startupctl/lib/startupctl.sh
```

## 开发与测试

```bash
python3 -m compileall -q startupctl tests   # 语法门（CI 在 3.8 上也跑一遍）
python3 -I tests/test_smoke.py              # 单元冒烟 + 安全不变量
bash tests/smoke.sh                         # 完整冒烟（含安装/卸载/更新循环）
```

**测试绝不碰真机。** 每个用例通过 `STARTUPCTL_ROOTS` 把扫描根重定向到
`tests/fixtures/roots/` 的夹具树；少数需要走执行路径的用例操作的是夹具树的**临时副本**。
CI 全局设 `STARTUPCTL_DRY_RUN=1` 作为安全带，即使有 bug 摸到 mutator 也无法行动。
其中一条断言专门验证「输出里没有夹具之外的路径」——它是其余安全断言可信的前提。

改动前请先读 `CLAUDE.md`：里面记着三条硬约定（零依赖 / 安装布局 / 数据目录永不自动删除）、
安全模型的九道闸、以及各平台实现里踩过的坑。

## 许可证

MIT
