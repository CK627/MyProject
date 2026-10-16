# startupctl — 启动项扫描与管理

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

---

## 为什么它只碰第三方项

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

---

## 安全模型

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

### 白名单

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

---

## 安装

```bash
# 一键（macOS / Linux）
source <(curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/StartupItemManagement/installer/install.sh)

# 国内镜像
source <(curl -fsSL http://101.132.165.98/dist/startupctl/install.sh)

# 本地源码
bash installer/install.sh
```

默认装到系统级（`/Library/devtools/startupctl`、Linux 为 `/usr/local/devtools/startupctl`）。
只想装给当前用户（不需要密码）：

```bash
STARTUPCTL_USER=1 bash installer/install.sh      # → ~/.devtools/startupctl
```

安装后 `PATH` 上只多一个 `startupctl`。**更新**与**卸载**：

```bash
startupctl update [--check]     # 镜像优先，回退 GitHub
startupctl uninstall [-y]       # 白名单与备份一律保留
```

### 仓库里直接跑（不安装）

```bash
./bin/startupctl.sh list        # 仓库启动器
python3 -m startupctl list      # 或者这样
```

---

## 命令

```
list [筛选]         扫描并列启动项（默认只列第三方，--all 全列）
show <项>           详情：来源 · 命令 · 分类依据 · 原始内容
check               只读体检（干净退 0，有可清理项退 1）
scan --save|--diff  存快照 / 比对**载荷漂移**
disable <项>...     禁用（可逆）
enable <项>...      恢复启用
remove <项>...      移到备份目录（不删文件）
add <名> <命令>     新建用户级自启项（让某项目开机自动运行）
restore [时间]      从备份还原**并重新启用**
backup list|prune   看备份 / 按保留策略清理
clean [-y]          批量禁用第三方项
proc [--orphans]    进程视图：三方进程与启动项聚合
kill <pid|项>       结束进程（先 TERM，--force 才 KILL）
whitelist ...       白名单
update install uninstall config help   自管理
```

每个子命令的完整选项：`startupctl <子命令> --help`。

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

---

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

### 图形窗口长什么样

`guard choose` 打开（tkinter，标准库，不引入依赖）：

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

点「选择」列勾选/取消，点「锁定」列钉住它，双击整行也能勾。**不用记键盘、不用打编号**
——这正是要图形窗口的原因：编号打错是看不见的失败。

三种界面**共用同一份"能不能选"的规则**，所以"系统进程选不了"在哪都一样：

| 开关 | 界面 |
|---|---|
| （默认） | 图形窗口 → 无图形环境时自动退到终端界面 → 再退到纯文本，**并说明为什么退** |
| `--tui` | 只用终端界面（curses：空格选中、`L` 锁定、`a` 全选、`/` 筛选） |
| `--plain` | 只用纯文本编号清单（`1,3,5-8`，编号后加 `!` 表示锁定） |

**系统基础进程与已锁定条目是真的选不了，不是只显示成灰的**——`Rows.toggle()` 会拒绝，
返回前再过一遍 `is_protected()`。UI 上的灰与 `[系统]` 标记只是提示；真正的防线在
`guard.is_protected()`，而执行器动手前**会再查一次**（预览到执行之间进程表会变，
而且 `guard.json` 是可以手改的）。`guard add WindowServer` 同样会被结构性拒绝，退出码 3。

### 改动一定会被核对

怕的是"选了半天其实没生效"——那是最难受的失败形态（选错了看得见，没生效看不见）。
所以**每一次改动都会写盘后重新读回来逐条核对**：

```
$ startupctl guard pick
选择清单已写入并核对无误: 3 条（其中锁定 1）
  文件: ~/.devtools/startupctl/guard.json

现在生效的规则（共 3 条）:
#  匹配方式  值           状态  备注
-  --------  -----------  ----  ----------
0  进程名    mysqld       锁定  guard pick
1  进程名    SomeTool           guard pick
2  进程名    Backend            guard pick

  下一步: startupctl guard check    看这个模式下会结束哪些
          startupctl guard arm      真的执行一轮
```

磁盘上的内容与预期不符时**直接报错并返回非零**，绝不打出"已更新"就完事。纯文本模式
下打错编号也会明确报「没有生效，可用编号 1-N」，而不是静默跳过。

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

纯文本模式（无终端时）用编号加 `!`：`1,3!` = 选 1、选 3 并锁定。

### 另两点提醒

1. 全部拒绝会拒绝**任何**新起的非系统进程——**包括你自己刚敲的命令**（但 shell 本身
   在上面那层保护里，所以你还敲得进命令）。这是它的设计意图，确实会妨碍干活，
   所以必须由你显式启动。
2. 它**绝不使用 sudo**：root 或他人的进程会被跳过并提示，而不是偷偷提权。
   在一个自动循环里提权，等于让工具替你做你没批准的破坏。

---

## 平台覆盖

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

---

## 配置

`~/.devtools/startupctl/startupctl.conf`（也可以用 `--config` 指定）。完整项见
`config/startupctl.conf`，几个关键的：

```ini
SHOW_SYSTEM=false        # list 默认只列第三方
MIN_CONFIDENCE=high      # clean 默认只处理高置信度
DRY_RUN=false            # true = 所有改动只预览
BACKUP_KEEP=20           # 备份保留份数
BACKUP_MIN_DAYS=7        # 不足这些天的备份 prune 不删
EXTRA_VENDORS=           # 追加"认定为第三方"的厂商前缀，如 com.mycorp
```

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

---

## 开发

```bash
python3 -m compileall -q startupctl tests   # 语法门（CI 在 3.8 上也跑一遍）
python3 -I tests/test_smoke.py              # 单元冒烟 + 安全不变量
bash tests/smoke.sh                         # 完整冒烟（含安装/卸载/更新循环）
```

**测试绝不碰真机。** 每个用例通过 `STARTUPCTL_ROOTS` 把扫描根重定向到
`tests/fixtures/roots/` 的夹具树；少数需要走执行路径的用例操作的是夹具树的**临时副本**。
CI 全局设 `STARTUPCTL_DRY_RUN=1` 作为安全带，即使有 bug 摸到 mutator 也无法行动。
其中一条断言专门验证「输出里没有夹具之外的路径」——它是其余安全断言可信的前提。

---

## 许可

MIT
