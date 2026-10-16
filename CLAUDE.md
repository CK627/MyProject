# CLAUDE.md — startupctl

给在这个仓库里干活的 Claude Code 看的约定与坑。**动手前先读这一份。**

## 这是什么

跨平台启动项扫描与管理 CLI。安装形态与 `jtool` / `ptool` / `CtfSweep` 同规，
框架是从 `CtfSweep` 克隆来的（那份本身就是"对齐 jtool/ptool"的形态）。

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

`.bat` / `.ps1` 必须 **纯 ASCII + CRLF**：cmd 用**调用方**的代码页解码被 call 的批处理，
UTF-8 中文注释在 GBK 控制台上会跨行错位，cmd 会去执行文本碎片。所有面向用户的中文都由
Python 打印（它自己管控制台编码）。CI 的 `contract` job 验这两条，**并且单独验一遍
`git archive` 导出物**——GitHub 生成的 tarball 不套用 `.gitattributes`，而 `update`
正是从那里取文件的。

### 3. 数据目录永不自动删除

`<数据根>`（`~/.devtools/startupctl`，用户级安装下**就是安装根**）住着三样：

```
whitelist.json   白名单（安全产物 · 用户逐条确认过）
backups/         备份（restore 的唯一来源）
scans/           扫描快照（纯缓存）
```

安装、更新、卸载**都不碰**它们。`clear` **只清 `scans/`**，而且代码里把删除范围**写死为
那一个目录**，不是"遍历数据根再跳过保留清单"——保留清单漏写一项就会误删，写死一个目录
则不可能删到别处（这类代码，白名单不如不需要白名单）。

---

## 安全模型（改这里之前先读完）

**唯一咽喉**：`core/manage.py::_dispatch` / `run_batch`。所有 `_do_*` 只从这里被调用。
九道闸的顺序**就是**安全属性：

1. 溯源（uid 必须在本次扫到的集合里）
2. ★ **硬闸：`origin != 'third_party'` → `Refused`**
3. `mutable`（dataclass 默认 `False`——后端忘了设就落在安全那侧）
4. 置信度阈值
5. **白名单不在这里** —— 它只收窄 `clean` 的候选集，绝不参与放行
6. `reclassify` 重读活源（TOCTOU 防线）
7. 先备份 → sha1 校验 → 才变更
8. `dry_run` 闸
9. 到这一步才 `getattr(backend, '_do_' + op)`

改动这一带时**必须保持的四条**：

- **闸门先于确认**。`run_batch` 先跑 `check_gates` 把必然被拒的挑出来，**再**问确认。
  顺序反了会让"安全拒绝"(退出 3) 被"非交互请加 -y"(退出 1) 盖掉，脚本就识别不出来了；
  而且工具会先征求一个它根本不打算执行的许可。
- **每个 `_do_*` 自己第一行再查一次 `self._guard(item)`**。这是纵深防御，与第 2 道闸
  **故意重复**：它让"绕过 manage 直接调后端"也改不动系统项。反射测试遍历
  `backends.MUTATORS` × 每个后端断言这一点——**新后端漏写守卫会立刻测试失败**。
- **白名单只能收窄，永远不能放宽**。有专门的测试（把系统项写进白名单，仍须被拒）。
  任何让白名单参与"放行"的改动都是把允许清单变成提权原语。
- **绝不谎报做不到的事**。改不动就报 `已跳过（需要 root）`，绝不报"已禁用"。
  `_needs_root` 按**实际可写性**判断（`os.access`），不只看 `scope`——只看 scope 会让
  所有夹具测试都跑不到执行路径，而测试跑不到的路等于没写。

### `_require_root_for` / `_needs_root` 为什么按可写性判

与 `installer/install-from-source.sh` 的 `run_priv` 同口径：目标可写就直接做，不可写才提权。
另外它让"系统级的项位于用户可写位置"（夹具全部如此）能真正跑通执行路径——
备份、搬移、还原这三条逻辑全靠它才被测试覆盖到。

---

## 进程守护（guard）：三种模式 + 系统基础进程的硬保护

`core/guard.py`（策略与决策）· `core/picker.py`（窗口选择器）· `core/enforce.py`（执行）。

**模式与选择分开**（用户明确要求）：`mode` 只决定用哪一份清单，`choose` 才是往清单里填。
**白名单与黑名单是两份独立的清单**（`Guard.whitelist` / `Guard.blacklist`），
不是"一份 entries、含义随模式解释"——后者会让切模式把刚挑好的东西变成另一套语义。

- `active_list_name()` 决定当前模式用哪份：`whitelist`/`deny_all` → 白名单；
  `blacklist` → 黑名单；`off` → 无。`deny_all` 把白名单当**豁免**用。
- **锁定跨两份清单查**（`matches_locked` 遍历两份）：锁定 = "别动它"，与它在哪份无关。
- **`ready_to_enforce()`**：清单为空就不许执行。白名单为空等于"除系统外全杀"，
  用户什么都没选，工具不该按最激进的解释动手。`arm` 据此拒绝并退出 3。
  这是「只有选择的时候才生效」的实现。
- **`SCHEMA_VERSION = 2`**：`load()` 要把 v1 的单份 `entries` 迁到当前模式对应的那份，
  **不能丢**（用户挑过的条目不该因为升级消失）。
- **`_save_and_verify` 必须核两份清单 + 模式**。只核当前那份的话，"另一份被悄悄改了"
  这类 bug 会静默通过——而它恰恰最难发现（你正在看的是当前那份）。
- **`picker.pick(allow_gui=False)` 默认不开窗**：只有 `guard choose` 传 `allow_gui=True`。
  日常命令突然弹窗既唐突又会挡住脚本化使用。

三种模式 `off` / `deny_all`（全部拒绝）/ `blacklist` / `whitelist`。
**三种模式一律保留系统基础进程**——这不是每个模式各写一遍的规则，而是
`Guard.verdict()` 里**先于模式判断**的一道闸：

```python
protected, why = is_protected(proc, platform, own_pids)
if protected:
    return PROTECTED, why          # ← 任何模式都走不到下面
... 再按 mode 判 allow/deny
```

**改这里时必须保住的四条**：

1. **`is_protected()` 永远在模式判断之前。** 顺序反了，「全部拒绝」和白名单模式下
   系统基础进程会被判成 `deny`，而 deny 就是被结束。「三种模式都保留系统进程」
   这条保证就是这个顺序本身，不是巧合。
2. **决策只有一个入口 `verdict()`**。别在 enforce.py 或 cli.py 里再写一套 if。
   `plan` 与 `apply` 共用同一份决策，才不可能出现"预览说不会杀、执行却杀了"。
3. **动手前再查一次 `is_protected()`**（`enforce.apply_decisions` 里）。预览到执行
   之间进程表会变，而且 **`guard.json` 是可以手改的**。纵深防御在这里不是重复。
4. **`is_protected` 的"判不准"要收敛**。曾经写成 `origin in ('os','unknown')` 一律保护，
   结果本机 906 个进程里 808 个受保护、连用户 `~/bin` 里的工具都杀不了，
   「全部拒绝」成了废功能。现在只兜「**root 拥有 + 出身说不清**」，普通用户拥有的
   进程用户本来就有权结束。改这条前先想清楚"用户想管的是哪些"。

**选择器**：`Rows.toggle()` 对受保护行返回 `(False, 原因)`——系统进程是**真的选不了**，
不是只画成灰的。`pick()` 返回前再过一遍 `is_protected()`。`_pick_plain` 返回的是
**proc 而不是 Row**（曾经返回 Row，导致选完写进清单 0 条——`g.add` 从 Row 上取不到
`comm`，静默 `ValueError` 被吞）。

**`own_pid_chain()` 必须跨平台**：早先只读 `/proc`，macOS 上没有 `/proc`，集合退化成
"只有自己"，用户的登录 shell 不再受保护、在选择器里能被选中。现在 `/proc` 优先、
`ps -o ppid=` 回退。

**`guard` 的默认模式是 `off`**：装上不会自己开始杀进程。`arm` 要显式敲，
且 `--dry-run` 必须中和它。

### 「还能操作」保障（改 guard 时最容易踩的坑）

全部拒绝模式**绝不含用户自己**——否则第一次 arm 下去 shell 和终端一起没了，
用户连"关掉它"都做不到，工具就成了把自己锁在门外的东西。

`_SESSION_SAFETY`（shell + 终端 + 会话）在 `is_protected()` 里，**任何模式都保护**。
匹配时注意登录 shell 的 comm 形如 `-zsh`，要先 `lstrip('-')`。

**代价是明确的**：恶意程序命名成 `bash` 就能躲过这一条。这是**刻意取舍**——
宁可放过一个改名的进程（它还有别的判据可能命中、且 `guard check` 里看得见），
也不能让工具把用户锁在门外。别"顺手"把这条保护删掉；要删先想清楚用户怎么关掉它。

### 锁定条目（locked）

条目上的 `locked` 字段：**语义与模式无关**，一律"别动它"——在 `verdict()` 里
**先于模式判断**返回 PROTECTED（与系统进程同一道闸）。

- 不是 ALLOW：白名单模式下它是"受保护"而不是"放行"。锁定 = 别碰，与它在哪个清单无关。
- 选择器里与系统进程一样置灰、选不动（`Row.frozen`），但**可以解锁**（`L` 键）——
  系统进程则永远不行。
- 要改必须先 `guard unlock`。这是"用户亲手钉住"的表达。

### 图形选择器（`core/gui.py`）

`guard pick` 默认弹 tkinter 窗口（标准库）。要点：

- **用 `ttk.Treeview` 而不是一堆 Checkbutton**：900+ 进程若一行两个复选框就是
  1800 个控件，建窗口要好几秒。Treeview 是原生列表，几千行照样顺。
- **只在交互式终端下弹窗**（`gui.available()` 里查 `isatty`）。CI/管道里弹一个等人点的
  窗口会让任务**直接挂住**，而且没有输出、没有报错，极难归因。
- **两种"没结果"必须分清**：窗口打不开 → 抛 `GuiUnavailable`（调用方回退）；
  用户点取消 → 返回 `None`（就此打住，不该偷偷换个界面再来一次）。
- 回退链 gui → tui → plain，每一步都通过 `note` 回调**说明原因**，绝不静默换界面。
- **系统行在点击处理里就忽略**，不只是画成灰的；返回前再过一遍 `is_protected()`。
- 测试接缝 `STARTUPCTL_GUI_SELFTEST=<N>`：窗口弹出后自动"选前 N 个可选项并确定"。
  没有它，"GUI 真的能选出结果"就只能靠人手点，于是 CI 永远验不到这条路径。
  与注册表 shim 同一性质。

### 写回核对（`cli._save_and_verify`）

这份东西的失败形态是"看起来成了、其实没生效"。本项目真出过一次：选择器返回了错的
对象类型，于是写进去 0 条，而提示照样说「已更新」。

所以每个变更路径都：保存 → **从磁盘重新加载** → 逐条比对 `match/value/locked` →
不一致就报错并返回非零。**新增变更入口时必须走它**，别自己 `g.save()` 了事。

### `--value` 允许预先下规则

`guard add --value foo` 不要求 `foo` 现在正在跑（`_synthetic_proc` 造占位记录）。
实际需要它：你知道某个 updater 会自己起来，想先把黑名单写好。
占位记录的 `pid` 为空，调用方据此提示"该规则会在它出现时生效"。

---

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
- **CI 全局 `STARTUPCTL_DRY_RUN=1`**：即使测试写漏，mutator 也无法行动。
- **`backends/darwin.py` 在夹具模式下跳过 osascript / BTM / crontab**：那三项读的是
  系统自己的数据库，`STARTUPCTL_ROOTS` 对它们无效。不跳过就会去读**真机**的登录项。
  （安全不变量第 12 条——"输出里不得出现夹具之外的路径"——正是它抓出来的。）

**子进程 env 要先清 `STARTUPCTL_PLATFORM` / `STARTUPCTL_DRY_RUN` 再应用覆盖**：
进程内测试会改 `os.environ` 切平台，`dict(os.environ)` 会把它带进子进程，
于是 `disable` 跑在错误的后端上、退 2，看起来像"解析失败"，实际是环境串味。

---

## CLI / 帮助文本

- **`HELP` 由数据表构建**（`help.py`），不手写对齐——手写的会漂移。冒烟断言行数 **≤ 50**
  与各节描述列对齐（用 `output.dw` 复算，CJK 计 2 列）。
- 每个子命令的完整选项放 `SUB_HELP`，由 `startupctl <子命令> --help` 打印。
  **改 CLI 选项要同步四处**：`cli.py` 的旗标集合、`help.SUB_HELP`、
  `completions/startupctl.{zsh,bash}`、README 的命令段。
- 退出码：`0` 成功 · `1` 失败 · `2` 用法错 · `3` 安全拒绝。**别把 3 合并进 1。**
- `--version` / `--help` 是旗标（落进 `opts`），必须先于"无位置参数"的早返回检查。

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
