# jtool - 统一 Java 版本管理工具

> 一个简单、跨平台的 Java 版本管理命令行工具，支持 macOS、Linux、Windows。

## 安装

### 命令行一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/jtool/installer/install.sh | bash
```

macOS 会下载最新 Release 的 `.pkg` 安装；Linux 会下载源码安装。

### macOS / Linux

```bash
cd /path/to/jtool

# macOS
./scripts/macOS/install.sh

# Linux
./scripts/Linux/install.sh
```

安装完成后执行 `source ~/.zshrc`（或 `source ~/.bashrc`）或重新打开终端。

### Windows

在 `scripts\Windows\` 下右键 `install.bat`，选择 **以管理员身份运行**。

安装完成后重新打开 CMD 窗口。

---

> 安装过程中会引导输入 Java 安装路径，回车使用默认值即可。
> 安装后的路径见下方「跨平台支持」表格。

## 卸载

### macOS / Linux

```bash
# macOS
./scripts/macOS/uninstall.sh

# Linux
./scripts/Linux/uninstall.sh
```

### Windows

在 `scripts\Windows\` 下右键 `uninstall.bat`，选择 **以管理员身份运行**。

> 卸载会删除安装目录（含配置文件）、`~/.devtools/jtool/` 下的 shim / 补全脚本 / repo 缓存，
> 并清理 shell 配置里由 jtool 写入的 PATH 行与补全 source 行（不触碰其他配置）。
> 确认后会立即执行，请提前备份自定义配置。

---

## 功能特性

- 🚀 一行命令运行任意版本的 Java 工具
- 🔄 快速切换默认 Java 版本
- 📂 配置驱动，支持自定义 Java 安装路径
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
| macOS | `jtool` | `/Library/devtools/jtool/` | `/Library/devtools/jtool/config/jtool.conf` | `scripts/macOS/` |
| Linux | `jtool` | `/usr/local/devtools/jtool/` | `/usr/local/devtools/jtool/config/jtool.conf` | `scripts/Linux/` |
| Windows | `jtool.bat` | `C:\Program Files\devtools\jtool\` | `C:\Program Files\devtools\jtool\config\jtool.conf` | `scripts/Windows/` |

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
JTOOL_VERSION="2.1.0"
```

> jtool 以 `JAVA_BASE_DIR` 作为唯一基准目录，按 `jdk-<版本>.jdk/Contents/Home` 拼接 JDK 路径
> （Linux 下为 `jdk-<版本>`）。若 JDK 装在别处（如 Eclipse Adoptium、SDKMAN），
> 执行 `jtool scan` 后手动修改 `JAVA_BASE_DIR` 即可。

## 版本号说明

| 输入版本 | 实际 JDK 目录 |
|----------|---------------|
| `8` | `jdk-1.8.jdk` |
| `11` | `jdk-11.jdk` |
| `17` | `jdk-17.jdk` |
| `21` | `jdk-21.jdk` |
| `26` | `jdk-26.jdk` |

> 版本号 `8` 会自动映射为 `1.8`，其他版本直接使用。

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
├── scripts/
│   ├── macOS/
│   │   ├── install.sh
│   │   └── uninstall.sh
│   ├── Linux/
│   │   ├── install.sh
│   │   └── uninstall.sh
│   └── Windows/
│       ├── install.bat
│       └── uninstall.bat
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
