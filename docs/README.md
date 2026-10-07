# jtool - 统一 Java 版本管理工具

> 一个简单、跨平台的 Java 版本管理命令行工具，支持 macOS、Linux、Windows。

## 安装

### 命令行一键安装

macOS / Linux（安装后自动刷新当前终端，无需手动 source）：

```bash
source <(curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/jtool/installer/install.sh)
```

Windows（PowerShell）：

```powershell
irm https://raw.githubusercontent.com/CK627/MyProject/jtool/installer/install.ps1 | iex
```

macOS 下载最新 Release 的 `.dmg`（内含 `.pkg`，双击安装）；Linux 下载 `.tar.gz` 解压后安装；
Windows 下载 `.exe` 静默安装。

### macOS / Linux

```bash
cd /path/to/jtool
./installer/install-from-source.sh install
```

安装完成后执行 `source ~/.zshrc`（或 `source ~/.bashrc`）或重新打开终端。

### Windows

在 `installer\windows\` 下右键 `install.bat`，选择 **以管理员身份运行**。

安装完成后重新打开 CMD 窗口。

---

> 安装过程中会引导输入 Java 安装路径，回车使用默认值即可。
> 安装后的路径见下方「跨平台支持」表格。

## 卸载

### macOS / Linux

```bash
./installer/install-from-source.sh uninstall
```

### Windows

在 `installer\windows\` 下右键 `uninstall.bat`，选择 **以管理员身份运行**。

> 卸载会删除安装目录（含配置文件）、`~/.devtools/jtool/` 下的 shim / 补全脚本 / repo 缓存，
> 并清理 shell 配置里由 jtool 写入的 PATH 行与补全 source 行（不触碰其他配置）。
> 确认后会立即执行，请提前备份自定义配置。

---

## 功能特性

- 🚀 一行命令运行任意版本的 Java 工具
- 🔄 快速切换默认 Java 版本
- 📂 配置驱动，支持自定义 Java 安装路径
- 🔍 自动识别 JDK 目录布局（macOS bundle / Linux 平铺 / 非标准命名）
- 🖥️ 跨平台：macOS / Linux / Windows
- 📦 零依赖，无需安装额外软件

## 使用方法

### 运行 Java 工具

```bash
# 运行指定版本
jtool java 26 -version
jtool javac 21 -d out MyClass.java
jtool jar 8 cf test.jar *.class

# 设置默认版本后可省略版本号
jtool use 21
jtool java -version
```

### 版本管理

```bash
jtool list              # 列出所有已安装的 JDK
jtool use 21            # 设置默认版本
jtool current           # 查看当前默认版本
```

### 信息查询

```bash
jtool info 21           # 显示详细信息
jtool tools 26          # 列出可用工具
jtool home 26           # 输出 JAVA_HOME 路径
jtool config            # 查看配置信息
```

### 编译并运行

```bash
jtool run 26 Hello.java  # 一步到位：编译 + 运行
```

### 帮助

```bash
jtool help
```

## 命令速查表

| 命令 | 说明 | 示例 |
|------|------|------|
| `jtool <工具> <版本> [参数]` | 运行指定版本的工具 | `jtool java 26 -version` |
| `jtool list` | 列出所有已安装的 JDK | `jtool list` |
| `jtool use <版本>` | 设置默认版本 | `jtool use 21` |
| `jtool current` | 查看当前默认版本 | `jtool current` |
| `jtool home <版本>` | 输出 JAVA_HOME 路径 | `jtool home 26` |
| `jtool info <版本>` | 显示详细信息 | `jtool info 21` |
| `jtool tools <版本>` | 列出可用工具 | `jtool tools 26` |
| `jtool run <版本> <文件>` | 编译并运行 | `jtool run 26 Hello.java` |
| `jtool config` | 查看配置信息 | `jtool config` |
| `jtool scan` | 重新扫描 Java 路径 | `jtool scan` |
| `jtool install` | 完整安装 | `jtool install` |
| `jtool update` | 检查并更新 jtool | `jtool update` |
| `jtool shim` | 重建 shim 脚本 | `jtool shim` |
| `jtool help` | 显示帮助 | `jtool help` |

> 三个平台统一使用 `jtool`（无后缀）。macOS / Linux 上真实脚本装在 `jtool/lib/jtool.sh`，
> `jtool/bin/jtool` 是指向它的软链接——`bin/` 在 PATH 上，若把 `jtool.sh` 也放在那里，
> 命令名补全就会同时列出 `jtool` 和 `jtool.sh`。所以 `jtool.sh` **不在 PATH 上**，
> 需要时用完整路径调用：`/Library/devtools/jtool/lib/jtool.sh`。
>
> `jtool scan` 会更新 `JAVA_BASE_DIR`，但会**保留**已设置的默认版本与版本记录。

## Tab 补全

安装时会自动生成补全脚本并写入 shell 配置（zsh / bash 均支持），重开终端即生效。

```bash
jtool <TAB>          # 子命令 + 工具名（java / javac / jar / jshell / javadoc / javap）
jtool use <TAB>      # 已安装的 JDK 版本
jtool java <TAB>     # 已安装的 JDK 版本
jtool run 21 <TAB>   # .java 文件
```

### 更新后无需手动 source

安装时会在补全脚本里定义一个 `jtool` 包装函数（`.zshrc` / `.bashrc` 只负责 source 它）。
函数在**父 shell** 中执行，
所以 `jtool update` / `jtool install` 跑完后会立刻重新加载补全——不需要手动
`source ~/.zshrc`，也不需要重开终端。

> 原理：脚本本身是子进程，无法修改父 shell 的环境，所以 `install.sh` 里调用
> `source ~/.zshrc` 是无效的（只影响脚本自己的 subshell）。只有 shell 函数
> 才能真正在当前终端里生效。
>
> 例外：**首次安装**时函数还没被定义（`.zshrc` 正在被写入），所以第一次仍需
> 重开终端或 `source ~/.zshrc`。之后的每次 update 都是自动的。

补全脚本位于 `~/.devtools/jtool/completions/`，由 `jtool install` / `jtool update` 自动刷新。
版本列表是直接扫描 `JAVA_BASE_DIR` 下的 `jdk-*` 目录得到的，**不会执行 java**，所以按 `<TAB>` 没有延迟。

## 跨平台支持

| 系统 | 主脚本 | 安装路径 | 配置文件 | 入口 |
|------|--------|----------|----------|------|
| macOS | `jtool` | `/Library/devtools/jtool/` | `/Library/devtools/jtool/config/jtool.conf` | `installer/` |
| Linux | `jtool` | `/usr/local/devtools/jtool/` | `/usr/local/devtools/jtool/config/jtool.conf` | `installer/` |
| Windows | `jtool.bat` | `C:\Program Files\devtools\jtool\` | `C:\Program Files\devtools\jtool\config\jtool.conf` | `installer/windows/` |

macOS / Linux 还会在 `~/.devtools/jtool/shims` 下生成 `java` / `javac` / `jar` / `jshell` /
`javadoc` / `javap` 包装脚本，它们按当前默认版本转发调用。`jtool update` 使用的仓库缓存
在 `~/.devtools/jtool/repo`。

### 各系统默认 Java 路径

| 系统 | 默认路径 |
|------|----------|
| macOS | `/Library/Java/JavaVirtualMachines` |
| Linux | `/usr/lib/jvm` |
| Windows | `C:\Program Files\Java` |

## 配置文件说明

配置文件位于安装目录内的 `config/jtool.conf`（完整路径见上方「跨平台支持」表格）。

```bash
# Java 安装路径（父目录）
JAVA_BASE_DIR="/Library/Java/JavaVirtualMachines"

# 默认 Java 版本（设置后可省略版本号）
# JTOOL_DEFAULT_VERSION="21"

# jtool 版本（由 install / update 维护，请勿手动修改）
JTOOL_VERSION="2.2.11"
```

> jtool 以 `JAVA_BASE_DIR` 作为唯一基准目录，并**按目录的真实布局**解析 JDK 路径，分两段：
>
> 1. **快路径**（不启动 java）：按序试 `<base>/jdk-<版本>.jdk`（macOS）、`<base>/jdk-<版本>`
>    （Linux / Windows）、`<base>/<版本>`，取其中有 `bin/java` 的那个作为 JDK home。
>    macOS 的 bundle 布局会自动落到其 `Contents/Home`。
> 2. **回落**（自动探测）：快路径都没命中时，扫描 `<base>/jdk*`，对每个候选执行
>    `java -version` 读出**真实版本号**再匹配——这样 `jdk-21.0.1`、`jdk1.8.0_392`
>    这类不规范的名字也能被 `jtool use 21` / `jtool use 8` 命中。
>
> 常规命名（`jdk-21`、`jdk-21.jdk`）在第一段就结束，**不会额外启动进程**，所以 `java` shim
> 这类热路径没有探测开销。
>
> 若 JDK 装在别处（如 Eclipse Adoptium、SDKMAN），执行 `jtool scan` 后手动修改
> `JAVA_BASE_DIR` 即可。

## 版本号说明

输入版本会先归一化，再按上面的两段解析去找目录：

| 输入版本 | 可能命中的目录 | 说明 |
|----------|----------------|------|
| `8` | `jdk-1.8.jdk`、`jdk1.8.0_392` | `8` 自动映射为 `1.8` |
| `11` | `jdk-11.jdk`、`jdk-11.0.20` | 直接匹配 |
| `17` | `jdk-17.jdk`、`jdk-17.0.9` | 直接匹配 |
| `21` | `jdk-21.jdk`、`jdk-21.0.1` | 前缀匹配：`21` 命中 `21.x.y` |
| `26` | `jdk-26.jdk` | 直接匹配 |

> **前缀匹配**：版本号可以只写到主版本，`21` 能命中真实版本 `21.0.7`；
> 但写全了就按全的比，`21.0.1` **不会**命中 `21.0.7`。
>
> `jtool list` 显示的版本号取自**目录名**，`jtool use` 接受的版本号则按上表匹配。
> 目录名不规范时两者字面可能不同——例如目录叫 `jdk-21.0.1` 时 `list` 显示 `21.0.1`，
> 而 `jtool use 21` 一样能命中，属预期行为。

## 在脚本中使用

```bash
#!/bin/bash

# 获取 JAVA_HOME
JAVA_HOME=$(jtool home 21)
export JAVA_HOME

# 使用指定版本编译
jtool javac 21 -d out src/*.java

# 使用指定版本运行
jtool java 21 -cp out Main

# 或者直接设置 PATH
export PATH="$(jtool home 26)/bin:$PATH"
java -version
```

## 项目结构

```
jtool/
├── VERSION                     # 版本号，jtool update 据此判断是否需要更新
├── bin/
│   ├── jtool.sh                # 主脚本 (macOS / Linux)
│   └── jtool.bat               # 主脚本 (Windows)
├── config/
│   └── jtool.conf              # 配置文件模板（首次安装时复制）
├── completions/
│   ├── jtool.zsh               # zsh 补全模板（安装时替换 @CONFIG_FILE@）
│   └── jtool.bash              # bash 补全模板
├── module/
│   └── common.sh               # 安装 / 扫描 / 更新 / 卸载逻辑（被 jtool.sh source）
├── installer/
│   ├── install.sh              # 一键安装（macOS / Linux）
│   ├── install.ps1             # 一键安装（Windows）
│   ├── install-from-source.sh  # 从源码安装 / 卸载（macOS / Linux）
│   ├── linux-build.sh          # 打 Linux .tar.gz 安装包
│   ├── macos/
│   │   ├── build.sh            # 打包 .pkg / .dmg（.pkg 打进 dmg，不单独发布）
│   │   ├── distribution.xml.in
│   │   ├── postinstall.in
│   │   └── uninstall.in
│   └── windows/
│       ├── install.bat         # Windows 安装（也是 module/install.bat 的来源）
│       ├── uninstall.bat
│       ├── build-from-mac.sh
│       ├── build-remote.bat
│       └── jtool.iss.in
└── docs/
    └── README.md               # 本文档
```

> 注意仓库布局与**安装后**布局不同：安装时 `bin/jtool.sh` 会被复制到 `jtool/lib/jtool.sh`，
> 并在 `jtool/bin/jtool` 建立指向它的软链接。`bin/` 在 PATH 上、`lib/` 不在，
> 这样保证 PATH 里只有无后缀的 `jtool` 一个名字（见上方命名说明）。

## 常见问题

### Q: 提示 "permission denied"

用安装脚本重新安装（需要 sudo），或手动补权限：

```bash
# macOS
sudo chmod +x /Library/devtools/jtool/lib/jtool.sh

# Linux
sudo chmod +x /usr/local/devtools/jtool/lib/jtool.sh
```

### Q: 提示 "command not found"

检查 PATH 是否正确配置：

```bash
echo $PATH | grep jtool
```

### Q: 如何查看所有可用的 JDK？

```bash
jtool list
```

### Q: 如何临时使用某个版本而不修改默认设置？

直接指定版本号即可：

```bash
jtool java 26 -version
```

## 许可证

MIT License
