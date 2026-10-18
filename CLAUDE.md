# CLAUDE.md — startupctl

给在这个仓库里干活的 Claude Code 看的约定与坑。**动手前先读这一份。**

## 这是什么

跨平台启动项扫描与进程策略 CLI。安装形态与 `jtool` / `ptool` / `CtfSweep` 同规。

**2.0 起只做两件事**：把启动项扫出来给人看，以及按三种模式结束进程。
禁/启用、删除、备份、还原已整体移除——不要再把它们加回来（用户明确要求过）。

```bash
bash tests/smoke.sh            # 完整冒烟（CI 的唯一门禁）
python3 -I tests/test_smoke.py # 只跑单元冒烟 + 安全不变量
./bin/startupctl.sh list       # 仓库启动器
```

---

## 三条不可协商的硬约定

### 1. 零第三方依赖，Python 3.8 起步

只用标准库（`plistlib` / `configparser` / `winreg` / `xml.etree` / `/proc`）。
**不写 3.9+ 语法**：不用 `list[int]`、不用 `match`、不用 `dict |`、不用
`functools.cache`。`typing.List/Optional/Tuple` 是标准写法。
`tests/smoke.sh` 第 1 段会 grep 这些写法，CI 矩阵里有 3.8 runner 兜底。

### 2. 安装布局：`bin/` 是素材目录，绝不能整体进 PATH

安装时真实启动器被复制到 `<安装根>/lib/startupctl.sh`，`bin/` 里**只有**一个无后缀软链
`startupctl → ../lib/startupctl.sh`。

> ⚠️ 仓库 `bin/` 同时放 `startupctl.sh` **和** `startupctl.bat`（靠扩展名区分系统）。
> 整体挂上 PATH 会让 zsh 补全同时列出 `startupctl` 与 `startupctl.bat`——**zsh 的命令名
> 补全走 `$commands` 哈希，不检查可执行位**。所以 `installer/deploy.sh` 用**白名单拷贝**，
> 绝不 `cp -R bin`。冒烟测试断言 `ls -A <安装根>/bin | wc -l` == 1。

### 2.1 文本编码契约：UTF-8，声明行 + 按类型的落地机制

**编码统一为 UTF-8 无 BOM，每个文本文件首部写一行编码声明**，由
`tests/check_text_encoding.py` 逐条核对「声明 = 实际字节」。但声明**只是契约**，
各运行环境并没有共通的 pragma，真正的解码机制必须按类型分开：

| 文件 | 声明 | 落地机制 |
|---|---|---|
| `.py` | `# -*- coding: utf-8 -*-` | Python 3 默认 UTF-8；PEP 263 声明真实生效 |
| `.sh` | `# encoding: utf-8`（可选） | shell 字节透明，UTF-8 天然可用 |
| `.bat` | `@rem encoding: utf-8` | **`chcp 65001` 必须在第一处非 ASCII 之前**；无 BOM；全部 CRLF |
| `.ps1`（`irm\|iex` 分发） | `# encoding: ascii-b64` | 正文**必须纯 ASCII**；中文以 UTF-8 Base64 内嵌，运行时 `T()` 解码 |
| `.ps1`（磁盘执行） | `# encoding: utf-8-bom` | **必须带 BOM**（Windows PowerShell 5.1 无 BOM 会按 ANSI/GBK 读） |
| `.iss` | `; encoding: utf-8` | ISCC 6.7.3 默认按 UTF-8 读（有无 BOM 均可，实测） |

`.bat` 的规则是实测出来的（Windows 10 / 代码页 936）：带 BOM 第一行直接报
`'?@echo' 不是内部或外部命令`；LF-only 会碎片化解析（`'not' 不是内部或外部命令`）；
UTF-8 无 BOM + CRLF + `chcp 65001` 在直接调用与 `call` 两种方式下都正常。

`.ps1` 走 `irm … | iex` 时，响应体被当作**字符串**交给 Invoke-Expression：BOM 会并进
第一行去执行一个叫 `<BOM>#` 的命令；非 ASCII 按 ANSI 解码后变成 `ä¸æ` 那类乱码
（2026-10 在中文 Windows 上实测）。所以这一条只能纯 ASCII + Base64——**没有第二种
正确写法**，也没有任何声明能让它变好。

CI 的 `contract` job 跑同一个检查器，**并且单独验一遍 `git archive` 导出物**——
GitHub 生成的 tarball 不套用 `.gitattributes`，而 `update` 正是从那里取文件的。

### 3. 数据跟着项目走：`<安装根>/data/`

名单与模式住在**安装根下的 `data/guard.json`**（用户明确要求，不放在
`~/.devtools` 里另开目录）：

- 装到哪、数据就在哪——`/Library/devtools/startupctl/data/`、仓库里的 `data/`、
  Windows 的 `C:\Program Files\devtools\startupctl\data\` 是同一个规则；
- **卸载连安装根一起删**（`rm -rf`，但先检查 `VERSION` / `lib/startupctl` 标记，
  不按路径无脑删），删掉项目不留无主文件；
- **升级不删** `data/`：`deploy.sh` 只删功能项（bin lib config completions VERSION
  uninstall deploy.sh shell-setup.sh）。
- Windows 的安装根是 `C:\Program Files\devtools\startupctl`（机器级，与 ptool/jtool 同规），
  `data/` 由安装器授 `BUILTIN\Users:(OI)(CI)(M)`——Program Files 默认只有管理员可写，
  而存名单是普通用户的事。
- `data/` 必须归**登录用户**：系统级安装以 root 部署，deploy.sh 用
  `STARTUPCTL_DATA_OWNER`（pkg postinstall 传）/ `SUDO_USER` / 控制台用户 依次兜底
  chown；否则普通用户存名单会被拒。
- 仓库里的 `data/` 已在 `.gitignore`。
- 旧位置 `~/.devtools/startupctl/guard.json` 只做**一次性迁移**（读到就按新位置存一份，
  旧文件不删，由用户自己清）。

## 安全模型（改这里之前先读完）

**本工具不修改启动项。** 它只做两件事：把启动项扫出来给人看，以及按模式结束进程。
禁/启用、删除、备份、还原那一整套在 2.0 里**整体移除**了（用户要求：
"多余的备份根本没必要"）。所以这里没有 manage.py，也没有 mutator。

四条不变的保证：

1. **保护先于模式**。`Guard.verdict()` 里 `is_protected()` 永远是第一道，之后才查
   锁定条目，最后才按模式判。三种模式都保留系统基础进程与你的 shell / 终端 / 会话。
   这条顺序**就是**那条保证本身，不是巧合——将来新增模式会自动继承。
2. **空名单不许执行**。`ready_to_enforce()`：白名单 / 黑名单为空时拒绝切模式（退出 3）。
   空名单的白名单模式等于"除系统外全杀"；用户什么都没选，工具不该按最激进的解释动手。
3. **决策只有一个入口** `verdict()`。`enforce.plan()`（预览）与执行共用它，所以不可能
   出现"预览说不会杀、执行却杀了"。
4. **执行前再查一次保护**。`enforce.apply_decisions()` 对每个待结束进程再跑一遍
   `is_protected()`——预览到执行之间进程表会变，而且 `guard.json` 是可以手改的。

退出码：`0` 成功 · `1` 失败 · `2` 用法错 · `3` **因安全理由被拒绝**。

- **函数里任何位置出现 `from .core import guard as guard_mod`，整个函数里这个名字
  就是局部变量**。`cmd_mode` 曾把导入写在 `if arg != 'off'` 里，于是 `mode off`
  走不到那条分支 → `UnboundLocalError`。导入放函数顶部。
- `enforce.apply_decisions()` 返回 `(成功, 失败, 跳过)` **三元组**，别把返回值直接
  `%d` 格式化（会 `TypeError`）；要显式解包。
**别把 3 合并进 1**：脚本靠它区分"安全拒绝"和"执行失败"。

## 进程守护：三种模式 × 两套名单 × 两个维度

`core/guard.py`（策略）· `core/picker.py`（选择器）· `core/gui.py`（窗口）·
`core/enforce.py`（执行）。

- **模式与选择分开**：`mode` 决定用哪份名单，`whitelist` / `blacklist` 才是往里填。
- **两份名单互相独立**：切模式只换用哪一份，内容原样留着。
- **每份名单分两个维度**（`DIM_STARTUP` / `DIM_PROCESS`）。判定时**命中任一即算命中**。
  这是用户明确要求的：Windows 上组策略、服务、注册表、启动文件夹都能自启，
  只看启动项会漏；只看进程又分不清"开机自己起的"和"你刚手敲的"。
- **`SCHEMA_VERSION = 3`**：v1（`entries`）与 v2（扁平 `whitelist`/`blacklist`）都得能读，
  v2 的条目迁到 **process 维度**——用户挑过的东西不能因为升级就消失。
- **`ready_to_enforce()` 按两个维度合计**判空。只选了启动项、没选进程也算非空：
  白名单模式下没关联到那些启动项的进程都会被结束，这**是**白名单模式的语义，
  但 `mode` 的预览必须把"将结束 N 个"打出来让人看见。

### 「还能操作」保障（改 guard 时最容易踩的坑）

全部拒绝模式**绝不含你自己**——否则第一次切下去 shell 和终端一起没了，用户连
"关掉它"都做不到，工具就成了把自己锁在门外的东西。

`_SESSION_SAFETY`（shell + 终端 + 会话）在 `is_protected()` 里，**任何模式都保护**。
匹配时注意登录 shell 的 comm 形如 `-zsh`，要先 `lstrip('-')`。

**代价是明确的**：恶意程序命名成 `bash` 就能躲过这一条。这是**刻意取舍**——
宁可放过一个改名的进程（它还有别的判据可能命中、且用户看得见），也不能让工具把
用户锁在门外。别"顺手"把这条保护删掉。

### 锁定条目（locked）

条目上的 `locked` 字段：**语义与模式无关**，一律"别动它"——在 `verdict()` 里
**先于模式判断**返回 PROTECTED（与系统进程同一道闸）。

- 不是 ALLOW：白名单模式下它是"受保护"而不是"放行"。
- 锁定跨两份名单、两个维度查：锁定 = 别碰，与它在哪份名单无关。

### 图形选择器（`core/gui.py`）

两个窗口，都用 tkinter 标准库：

- `gui.pick(rows, ...)` **选择器**：勾选加入名单。返回选中行的下标；取消返回 `None`。
- `gui.manage(tabs, ...)` **管理窗口**：`ttk.Notebook` 两个页签（启动项 / 进程），
  列出条目、可删除。

要点：

- **用原生 `ttk.Checkbutton`**（用户明确要原生控件，不要自绘的字符/图标）。
  实测 900 个 `ttk.Checkbutton` 建好只要 0.03 秒——早年"上千行会卡"的判断过时了。
  分组用可折叠标题行；"部分选中"用 `ttk.Checkbutton` 的 `alternate` 状态表达，
  比自己画三态图标更原生。
- **只在交互式终端下弹窗**（`gui.available()` 里查 `isatty`）。CI/管道里弹一个等人点的
  窗口会让任务**直接挂住**，而且没有输出、没有报错，极难归因。
- **两种"没结果"必须分清**：窗口打不开 → `GuiUnavailable`（调用方回退）；
  用户点取消 → 返回 `None`（就此打住，不该偷偷换个界面再来一次）。
- 回退链 窗口 → curses → 编号清单，每一步都**说明原因**，绝不静默换界面。
- **系统行在点击处理里就忽略**，不只是画成灰的；`picker.pick_processes` 返回前
  再过一遍 `is_protected()`。
- **勾选是原生复选框**，系统项与锁定项 `state(['disabled'])`（选不动）。
  纯文本/TUI 兜底里仍用 `☐/☑/⊘/▣` 字符——那里没有图形控件。
- **按应用分组**：进程用 `picker.app_group()`（`.app` 包路径优先），启动项用
  `picker.startup_group()`（反域名取前两段 / 去单元扩展名 / 登录项按应用名）。
  启动项的名称列用 `display_name`（应用名/可执行名），不是包名。
- **单击与双击靠"列"区分，不靠计时**：单击勾选列**立即**切换；双击名称/说明列
  展开折叠分组；点三角只折叠。**别再加 `after()` 延迟**——用户明确说"240ms
  都太长"，手感不能靠等。
- 测试接缝 `STARTUPCTL_GUI_SELFTEST=<N>`：窗口弹出后自动"选前 N 个可选项并确定"。
  没有它，"GUI 真的能选出结果"就只能靠人手点，于是 CI 永远验不到这条路径。

### 启动项选择器与进程选择器是**两个**

用户明确要求分开：启动项是一层、进程是一层。命令也按这个分：

    startupctl whitelist startup selector
    startupctl whitelist process selector

启动项选择器只列第三方项（系统项永远受保护，加进名单只是噪声）；
进程选择器里系统基础进程与锁定项**不可选**。

## 分类：不确定就倒向安全那侧

`core/classify.py`。返回 `os` / `third_party` / `unknown` **三值**，且
`origin_evidence` **永远非空**（用户必须能复核判定依据——不可审计的分类就是不可信任的分类）。

两个方向的代价不对称：系统项被误判为三方 → `clean` 可能动它（有害）；三方项被误判为
系统项 → 加 `--include-unknown` 即可（只是麻烦）。所以：

- 不确定返回 `unknown`，而 `unknown` 一律**不可改**。
- **非对称规则**（`_apply_asymmetry`）：不确定 + 系统级非用户可写路径 → **永不为三方**。
- **`com.apple.*` 一律按系统项**，哪怕它是伪装的（fail-closed）；真信号交给
  「身份与文件名不一致」那条警告。
- **判据优先用 `item.root`（逻辑根）而不是路径子串**。路径子串（`/LaunchAgents/`）
  只在真机上成立，夹具树用逻辑名——靠子串匹配会让全部夹具项落进 `unknown`，
  于是"分类逻辑可测"变成空话。
- **`uid == 0`、`program` 在 `/usr/bin` 都不是系统项的证据**（docker/ClashX 的 helper
  都以 root 跑；三方守护进程经常 exec `/usr/bin/python3`）。

---

## 测试：绝不碰真机

这是整套安全断言可信的前提。机制：

- **`STARTUPCTL_ROOTS=<dir>`** 把所有扫描根重映射到夹具树（逻辑名换 `_` 作相对路径）。
  唯一的重映射点在 `core/roots.py`——后端硬编码路径会立刻在夹具测试里失败。
- **`STARTUPCTL_DATA_DIR`** 隔离数据目录。
- **`SCAN_SYSTEM`/`STARTUPCTL_PLATFORM`**：`STARTUPCTL_PLATFORM` 可强制后端，用于
  在 Linux/macOS 上测 Windows 后端。
- **注册表 shim**：`backends/windows.py::_reg` 在非 Windows 或夹具模式下读
  `tests/fixtures/roots/registry.json`。**别把它当测试临时代码简化掉**——少了它，
  三个平台里风险最高的 Windows 后端在 3 个 runner 里只有 1 个会跑到。
- **CI 全局 `STARTUPCTL_DRY_RUN=1`**：即使测试写漏，也不会真结束进程。
- **`backends/darwin.py` 在夹具模式下跳过 osascript / BTM / crontab**：那三项读的是
  系统自己的数据库，`STARTUPCTL_ROOTS` 对它们无效。不跳过就会去读**真机**的登录项。
  （安全不变量第 12 条——"输出里不得出现夹具之外的路径"——正是它抓出来的。）

**子进程 env 要先清 `STARTUPCTL_PLATFORM` / `STARTUPCTL_DRY_RUN` 再应用覆盖**：
进程内测试会改 `os.environ` 切平台，`dict(os.environ)` 会把它带进子进程，
于是扫描跑在错误的后端上、退 2，看起来像"解析失败"，实际是环境串味。

---

## 持续监视与开机自启（`watch` / `starting`）

`core/watch.py`（循环）· `core/autostart.py`（用户级自启注册）。用户要的是
「开了黑名单模式就自动盯着，进程一出现就清理」。

- 循环**只结束进程**，复用 `guard.verdict()`（唯一决策入口）。启动项文件仍然一律不改。
- **每轮重读 `guard.json`**：改名单不用重启，下一轮生效。模式 `off` 时空转。
- **`starting` 与 `mode` 是两件独立的事**：mode 变化绝不注册/摘除自启，也绝不停止
  循环。只有 `starting false` 才停止并摘除。`mode off` 时循环照常跑（空转）——
  否则"把模式设成 off"就等于顺手把自启弄丢了，用户明确要求不能这样。
- **单实例**靠 `data/watch.pid`：第二个进程看到活着的 pid 直接退出（launchd 重载、
  计划任务重叠、用户手滑都可能起出第二个）。两个循环同时杀进程是事故。
- 服务管理器是**异步**启动的：`starting true` 之后要用 `autostart.wait_running()`
  等 pid 出现，不能立刻读。Windows 的计划任务还要显式 `schtasks /run`。
- 服务进程拿到的是最小环境 → plist / unit 里必须显式写 `PYTHONPATH` 与
  `STARTUPCTL_DATA_DIR`，否则 pid/日志会落到与 CLI 不同的目录（踩过一次）。
- **不要用 `subprocess` 另起一个循环去"帮"服务管理器启动**：那会变成两个循环。
- `watch.log` 同时是 stdout（launchd 重定向到同一文件）→ 日志函数只在交互终端才
  同时 print，否则每行出现两次。

## CLI / 帮助文本

- **`HELP` 由数据表构建**（`help.py`），不手写对齐——手写的会漂移。冒烟断言行数 **≤ 50**
  与各节描述列对齐（用 `output.dw` 复算，CJK 计 2 列）。
- **顶层帮助与 ptool 同形**：`用法:` 本身就是命令清单，**一行一条、全部可见**；
  不设「子命令:」分区，也不用 `whitelist ...` 这类省略号（分组命令把动作名写进描述）。
  冒烟有一条专门断言"用法里没有 ` ... ` 省略条目"——它防的就是帮助退化成目录摘录。
- **本工具没有 `--` 旗标**（用户明确要求）。`cli.main()` 第一件事就是把任何 `-` 开头的
  参数判为用法错并退出 2——**不要为了"顺手"加回 `-y` / `--all`**。
- **`startupctl <命令> ?` 打印该位置的可填值**（`help.HINTS`），层级与
  Tab 补全一致。cmd / Windows PowerShell 5.1 没有可用的补全，这是它们的替代；
  zsh 里 `?` 是通配符，所以 `help` 作为最后一个词也同义（`whitelist help`）。
  改命令层级时**三处同步**：`cli.py`、`help.HINTS`、`completions/*`。
- 每个子命令的完整说明放 `SUB_HELP`，由 `startupctl help <子命令>` 打印。
  **改 CLI 要同步四处**：`cli.py` 的分发、`help.COMMANDS`/`SUB_HELP`、
  `completions/startupctl.{zsh,bash}`、README 的命令速查表。
- 帮助里**不设「选项:」分区**（没有选项），冒烟有一条专门断言这一点。

---

## 版本与发布

- 改版本号要**同步两处**：根 `VERSION` 与 `startupctl/__init__.py::__version__`。
  `test_smoke.py` 逐字断言。`pyproject.toml` 走 dynamic version（读 `__init__`）。
- 发布：`installer/publish-mirror.sh`。镜像布局：
  `<base>/VERSION` · `<base>/startupctl-src.tar.gz`（顶层目录必须叫
  `MyProject-StartupItemManagement`）· `<base>/<version>/<asset>`。
  **快照内部的 VERSION 必须与镜像的 VERSION 一致**——`selfmgr` 有"半发布防护"，
  两者不符就拒绝落盘（防止有人装到正在发布中的半成品）。

---

## 平台实现里的坑（都踩过了）

**macOS**
- `plistlib` 在真实文件上会失败：Apple 自己的 `com.apple.familycircled.plist` 的 XML
  声明里**属性没加引号**。回退是 `/usr/bin/plutil -convert xml1 -o -`（系统自带）。
  **"去掉 prolog 重试"无效**。
- 有解析成**空 dict** 的 plist（Google keystone 的 181 字节占位文件）→ 缺 `Label` 时
  回落到文件名词干，绝不 `KeyError`。
- 必须**跟随符号链接**（`/System/Library/LaunchAgents` 里有 11 个）。
- **`enabled` 是三态**：`launchctl print-disabled` 只列**有覆盖记录**的标签，
  `=> enabled` 表示"被显式重新启用"；**不在表里 = 没有覆盖 = 回落到 plist 的 `Disabled`**。
  把"在表里"当成"已禁用"会把结论整个弄反。
- **`launchctl print` 无需 root**（只有变更需要），所以系统守护进程的关联是**可用**的。
- **BTM 直读数据库，绝不调 `sfltool`**：实测非交互下挂起 >120 秒（授权/性能双重问题）。
  数据库是 NSKeyedArchiver plist：`identifier` 本身是 `UID` 要二次解引用；
  标识里的数字前缀是**标志位**不是 generation（实测 1/82 巧合相等）；
  `disposition` 的 **bit0 = 启用**（与 sfltool 的 `0xb`/`0b0010` 对照吻合）；
  开发者容器（`type=0x20`）要滤掉；空 url 是字符串 `'$null'`（**真值**）不是 None。
- 登录项走 `osascript`，会触发 TCC「自动化」授权；无头环境下失败并返回 **-1743**，
  必须当一等公民的预期失败处理（给出授权指引），绝不崩。

**Linux**
- `static` 单元**永远无法启用**（无 `[Install]`）→ 报 `enabled=None`，不能报成"未启用/损坏"。
- **drop-in 会改 `ExecStart`**（`<unit>.d/*.conf`）→ 不看就会报出**过期的命令行**。
- XDG 生效态是**算出来的**：目录优先级 → `Hidden` → `OnlyShowIn`/`TryExec`。
- `configparser` 三个坑：必须覆盖 `optionxform`（否则 `X-GNOME-*` 被小写化）、
  `delimiters=('=',)`、`strict=False`。
- `/proc/<pid>/stat` 的 `comm` **带括号且自身可能含空格与括号**（`(tmux: server)`）
  → **从最后一个 `)` 切**。
- `hidepid=2` 会让别人的 `/proc/<pid>` 整个不可见 → 进程列表**静默变成子集**，
  必须从 `/proc/mounts` 检出并明说降级。

**Windows**
- **绝不解析本地化输出**（`tasklist`/`sc query`/`schtasks /fo CSV` 在中文系统上列名与
  偏移都不同）→ 读注册表 `Services\<name>` 的 `Start` DWORD、读 `System32\Tasks` 的 XML。
- **WOW64 只影响 HKLM**：`HKCU\...\Run` 在共享列表上**不被重定向**，对它枚举双视图
  只会拿到重复项。
- **`StartupApproved` 是"任务管理器 → 启动"开关的真实存储**，是 macOS
  `print-disabled` 的对偶：Run 项能"存在但已禁用"，只有这张表能告诉你
  （byte0 `0x03`/`0x07` = 禁用；不存在 = 默认启用）。值是二进制，夹具里是整数数组。
- **`Start=0/1` 是驱动不是启动项** → 过滤掉。
- **计划任务在磁盘上是嵌套目录树**（`Tasks\Microsoft\Windows\Defrag\Defrag`）→
  `iter_scan_files` 是非递归的，用它只能扫到根目录那几个，系统任务会**全部漏掉**。
- `winreg.EnumValue` 的默认值名是**空串**，极易被顺手丢掉。
- `.lnk` 的目标要靠 COM `IShellLink`，标准库做不到 → 只做尽力而为的字符串提取并
  **标注为推测**。决策上无所谓：disable/remove 对 `.lnk` 就是同一个文件搬移。
