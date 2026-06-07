# ptool - 统一 Python 版本管理工具

> 一个简单、跨平台的 Python 版本管理命令行工具，支持 macOS、Linux、Windows。

## 安装

### macOS / Linux

```bash
cd /path/to/ptool
./install.sh
```

安装完成后执行 `source ~/.zshrc`（或 `source ~/.bashrc`）或重新打开终端。

### Windows

右键 `install.bat`，选择 **以管理员身份运行**。

安装完成后重新打开 CMD 窗口。

---

> 安装过程中会自动创建配置文件，如需自定义搜索路径请编辑 `~/.ptool.conf`。

## 卸载

### macOS / Linux

```bash
cd /path/to/ptool
./uninstall.sh
```

### Windows

右键 `uninstall.bat`，选择 **以管理员身份运行**。

---

## 功能特性

- 🚀 一行命令运行任意版本的 Python
- 🔄 快速切换默认 Python 版本
- 📂 支持多个搜索路径，自动扫描已安装版本
- 🖥️ 跨平台：macOS / Linux / Windows
- 📦 零依赖，无需安装额外软件

## 使用方法

### 运行 Python

```bash
# 运行指定版本
ptool python 3.11 --version
ptool pip 3.12 install requests
ptool python 3.11 -m venv myenv

# 设置默认版本后可省略版本号
ptool use 3.11
ptool python --version
```

### 版本管理

```bash
ptool list              # 列出所有已安装的 Python
ptool use 3.11          # 设置默认版本
ptool current           # 查看当前默认版本
```

### 信息查询

```bash
ptool info 3.11         # 显示详细信息
ptool tools 3.11        # 列出可用工具
ptool home 3.11         # 输出安装路径
ptool config            # 查看配置信息
```

### 运行 Python 文件

```bash
ptool run 3.11 hello.py
```

### 帮助

```bash
ptool help
```

## 命令速查表

| 命令 | 说明 | 示例 |
|------|------|------|
| `ptool <工具> <版本> [参数]` | 运行指定版本的工具 | `ptool python 3.11 --version` |
| `ptool list` | 列出所有已安装的 Python | `ptool list` |
| `ptool use <版本>` | 设置默认版本 | `ptool use 3.11` |
| `ptool current` | 查看当前默认版本 | `ptool current` |
| `ptool home <版本>` | 输出安装路径 | `ptool home 3.11` |
| `ptool info <版本>` | 显示详细信息 | `ptool info 3.11` |
| `ptool tools <版本>` | 列出可用工具 | `ptool tools 3.11` |
| `ptool run <版本> <文件>` | 运行 Python 文件 | `ptool run 3.11 hello.py` |
| `ptool config` | 查看配置信息 | `ptool config` |
| `ptool help` | 显示帮助 | `ptool help` |

> macOS / Linux 使用 `ptool.sh`，Windows 使用 `ptool`（无后缀）

## 配置文件

配置文件路径：`~/.ptool.conf`（Windows: `%USERPROFILE%\.ptool.conf`）

```bash
# 默认 Python 版本
# PTOOL_DEFAULT_VERSION="3.11"
```

ptool 会自动扫描以下路径查找 Python：

| 系统 | 搜索路径 |
|------|----------|
| macOS | `/usr/local/bin`, `/usr/bin`, `/Library/Frameworks/Python.framework/Versions`, `/usr/local/Cellar`, `~/.pyenv/versions` |
| Linux | `/usr/local/bin`, `/usr/bin`, `~/.pyenv/versions` |
| Windows | `C:\Python*`, `C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python*` |

## 跨平台支持

| 系统 | 脚本 | 安装路径 | 配置文件 |
|------|------|----------|----------|
| macOS | `ptool.sh` | `/Library/devtools/ptool/` | `/Library/devtools/ptool/ptool.conf` |
| Linux | `ptool.sh` | `/usr/local/devtools/ptool/` | `/usr/local/devtools/ptool/ptool.conf` |
| Windows | `ptool.bat` | `C:\Program Files\devtools\ptool\` | `C:\Program Files\devtools\ptool\ptool.conf` |

## 在脚本中使用

```bash
#!/bin/bash

# 获取 Python 路径
PYTHON_PATH=$(ptool home 3.11)/python3.11
export PYTHON_PATH

# 使用指定版本运行
ptool python 3.11 -m venv myenv
ptool pip 3.11 install -r requirements.txt
ptool run 3.11 main.py
```

## 项目结构

```
ptool/
├── install.sh          # macOS / Linux 安装脚本
├── install.bat         # Windows 安装脚本
├── uninstall.sh        # macOS / Linux 卸载脚本
├── uninstall.bat       # Windows 卸载脚本
├── bin/
│   ├── ptool.sh        # 主脚本 (macOS / Linux)
│   └── ptool.bat       # 主脚本 (Windows)
├── config/
│   └── ptool.conf      # 配置文件模板
└── docs/
    └── README.md        # 本文档
```

## 常见问题

### Q: 提示 "permission denied"

```bash
chmod +x /usr/local/ptool/bin/ptool.sh
```

### Q: 提示 "command not found"

检查 PATH 是否正确配置：

```bash
echo $PATH | grep ptool
```

### Q: 找不到已安装的 Python

检查配置文件中的搜索路径是否包含 Python 的安装目录：

```bash
ptool config
```

### Q: 如何添加自定义搜索路径？

编辑 `~/.ptool.conf`，添加搜索路径。

## 许可证

MIT License
