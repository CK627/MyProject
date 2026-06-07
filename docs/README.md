# jtool - 统一 Java 版本管理工具

> 一个简单、跨平台的 Java 版本管理命令行工具，支持 macOS、Linux、Windows。

## 安装

### macOS / Linux

```bash
cd /path/to/jtool
./install.sh
```

安装完成后执行 `source ~/.zshrc`（或 `source ~/.bashrc`）或重新打开终端。

### Windows

右键 `install.bat`，选择 **以管理员身份运行**。

安装完成后重新打开 CMD 窗口。

---

> 安装过程中会引导输入 Java 安装路径，回车使用默认值即可。

## 卸载

### macOS / Linux

```bash
cd /path/to/jtool
./uninstall.sh
```

### Windows

右键 `uninstall.bat`，选择 **以管理员身份运行**。

> 卸载脚本会自动删除安装目录、清理环境变量，并询问是否保留配置文件。

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
jtool.sh java 26 -version
jtool.sh javac 21 -d out MyClass.java
jtool.sh jar 8 cf test.jar *.class

# 设置默认版本后可省略版本号
jtool.sh use 21
jtool.sh java -version
```

### 版本管理

```bash
jtool.sh list              # 列出所有已安装的 JDK
jtool.sh use 21            # 设置默认版本
jtool.sh current           # 查看当前默认版本
```

### 信息查询

```bash
jtool.sh info 21           # 显示详细信息
jtool.sh tools 26          # 列出可用工具
jtool.sh home 26           # 输出 JAVA_HOME 路径
jtool.sh config            # 查看配置信息
```

### 编译并运行

```bash
jtool.sh run 26 Hello.java  # 一步到位：编译 + 运行
```

### 帮助

```bash
jtool.sh help
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
| `jtool help` | 显示帮助 | `jtool help` |

> macOS / Linux 使用 `jtool.sh`，Windows 使用 `jtool`（无后缀）

## 跨平台支持

| 系统 | 脚本 | 安装路径 | 配置文件 |
|------|------|----------|----------|
| macOS | `jtool.sh` | `/Library/devtools/jtool/` | `/Library/devtools/jtool/jtool.conf` |
| Linux | `jtool.sh` | `/usr/local/devtools/jtool/` | `/usr/local/devtools/jtool/jtool.conf` |
| Windows | `jtool.bat` | `C:\Program Files\devtools\jtool\` | `C:\Program Files\devtools\jtool\jtool.conf` |

### 各系统默认 Java 路径

| 系统 | 默认路径 |
|------|----------|
| macOS | `/Library/Java/JavaVirtualMachines` |
| Linux | `/usr/lib/jvm` |
| Windows | `C:\Program Files\Java` |

## 配置文件说明

配置文件路径：`~/.jtool.conf`（Windows: `%USERPROFILE%\.jtool.conf`）

```bash
# Java 安装路径（留空自动检测）
JAVA_BASE_DIR="/Library/Java/JavaVirtualMachines"

# 默认 Java 版本（设置后可省略版本号）
# JTOOL_DEFAULT_VERSION="21"
```

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
JAVA_HOME=$(jtool.sh home 21)
export JAVA_HOME

# 使用指定版本编译
jtool.sh javac 21 -d out src/*.java

# 使用指定版本运行
jtool.sh java 21 -cp out Main

# 或者直接设置 PATH
export PATH="$(jtool.sh home 26)/bin:$PATH"
java -version
```

## 项目结构

```
jtool/
├── install.sh          # macOS / Linux 安装脚本
├── install.bat         # Windows 安装脚本
├── uninstall.sh        # macOS / Linux 卸载脚本
├── uninstall.bat       # Windows 卸载脚本
├── bin/
│   ├── jtool.sh        # 主脚本 (macOS / Linux)
│   └── jtool.bat       # 主脚本 (Windows)
├── config/
│   └── jtool.conf      # 配置文件模板
└── docs/
    └── README.md        # 本文档
```

## 常见问题

### Q: 提示 "permission denied"

```bash
chmod +x /usr/local/jtool/bin/jtool.sh
```

### Q: 提示 "command not found"

检查 PATH 是否正确配置：

```bash
echo $PATH | grep jtool
```

### Q: 如何查看所有可用的 JDK？

```bash
jtool.sh list
```

### Q: 如何临时使用某个版本而不修改默认设置？

直接指定版本号即可：

```bash
jtool.sh java 26 -version
```

## 许可证

MIT License
