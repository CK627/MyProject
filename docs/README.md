# ptool - 统一 Python 版本管理工具

> 一个简单、跨平台的 Python 版本管理命令行工具，支持 macOS、Linux、Windows。

## 安装

### 命令行一键安装

macOS / Linux（安装后自动刷新当前终端，无需手动 source）：

```bash
source <(curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/ptool/installer/install.sh)
```

Windows（PowerShell）：

```powershell
irm https://raw.githubusercontent.com/CK627/MyProject/ptool/installer/install.ps1 | iex
```

macOS 下载最新 Release 的 `.pkg` 安装；Linux 下载源码安装；Windows 下载 `.exe` 静默安装。

### macOS / Linux

```bash
cd /path/to/ptool

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

> 安装过程中会自动扫描并写入配置文件，安装后的路径见下方「跨平台支持」表格。

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

---

> 卸载会删除安装目录（含配置文件）、`~/.devtools/ptool/` 下的 shim / 补全脚本 / repo 缓存，
> 并清理 shell 配置里由 ptool 写入的 PATH 行与补全 source 行（不触碰其他配置）。
> 确认后会立即执行，请提前备份自定义配置。

## 功能特性

- 🚀 一行命令运行任意版本的 Python
- 🔄 快速切换默认 Python 版本
- 📂 自动扫描已安装版本，可自定义 Python 安装目录
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
| `ptool scan` | 重新扫描 Python 路径 | `ptool scan` |
| `ptool install` | 完整安装 | `ptool install` |
| `ptool update` | 检查并更新 ptool | `ptool update` |
| `ptool shim` | 重建 shim 脚本 | `ptool shim` |
| `ptool help` | 显示帮助 | `ptool help` |

> 三个平台统一使用 `ptool`（无后缀）。macOS / Linux 上真实脚本装在 `ptool/lib/ptool.sh`，
> `ptool/bin/ptool` 是指向它的软链接——`bin/` 在 PATH 上，若把 `ptool.sh` 也放在那里，
> 命令名补全就会同时列出 `ptool` 和 `ptool.sh`。所以 `ptool.sh` **不在 PATH 上**，
> 需要时用完整路径调用：`/Library/devtools/ptool/lib/ptool.sh`。
>
> `ptool scan` 会更新 `PYTHON_BASE_DIR`，但会**保留**已设置的默认版本与版本记录。

## Tab 补全

安装时会自动生成补全脚本并写入 shell 配置（zsh / bash 均支持），重开终端即生效。

```bash
ptool <TAB>          # 子命令 + 工具名
ptool use <TAB>      # 已安装的 Python 版本
ptool python <TAB>   # 已安装的 Python 版本
ptool run 3.11 <TAB> # .py 文件
```

### 更新后无需手动 source

安装时会在补全脚本里定义一个 `ptool` 包装函数（`.zshrc` / `.bashrc` 只负责 source 它）。
函数在**父 shell** 中执行，
所以 `ptool update` / `ptool install` 跑完后会立刻重新加载补全——不需要手动
`source ~/.zshrc`，也不需要重开终端。

> 原理：脚本本身是子进程，无法修改父 shell 的环境，所以 `install.sh` 里调用
> `source ~/.zshrc` 是无效的（只影响脚本自己的 subshell）。只有 shell 函数
> 才能真正在当前终端里生效。
>
> 例外：**首次安装**时函数还没被定义（`.zshrc` 正在被写入），所以第一次仍需
> 重开终端或 `source ~/.zshrc`。之后的每次 update 都是自动的。

补全脚本位于 `~/.devtools/ptool/completions/`，由 `ptool install` / `ptool update` 自动刷新，
不需要手动维护。修改过 `PYTHON_BASE_DIR` 后补全列表会自动跟着变（每次补全都重新读取配置）。

## 配置文件

配置文件位于安装目录内（见下方「跨平台支持」表格），Windows 与 macOS / Linux 路径不同。

```bash
# Python 安装路径（父目录）
PYTHON_BASE_DIR="/usr/local/bin"

# 默认版本
# PTOOL_DEFAULT_VERSION="3.11"

# ptool 版本（由 install / update 维护，请勿手动修改）
PTOOL_VERSION="2.1.0"
```

`ptool scan` 会自动扫描以下路径查找 Python 安装目录：

| 系统 | 搜索路径 |
|------|----------|
| macOS / Linux | `/usr/local/bin`（优先）, `/usr/bin` |
| Windows | `C:\Python*`, `%LOCALAPPDATA%\Programs\Python` |

> ptool 以 `PYTHON_BASE_DIR` 作为唯一基准目录，按 `python<版本号>` 拼接可执行文件路径
> （例如 `PYTHON_BASE_DIR=/usr/local/bin` + 版本 `3.11` → `/usr/local/bin/python3.11`）。
> 如需使用其他安装位置（如 pyenv、Framework 构建），执行 `ptool scan` 后手动修改 `PYTHON_BASE_DIR` 即可。

## 跨平台支持

| 系统 | 主脚本 | 安装路径 | 配置文件 | 入口 |
|------|--------|----------|----------|------|
| macOS | `ptool` | `/Library/devtools/ptool/` | `/Library/devtools/ptool/config/ptool.conf` | `scripts/macOS/` |
| Linux | `ptool` | `/usr/local/devtools/ptool/` | `/usr/local/devtools/ptool/config/ptool.conf` | `scripts/Linux/` |
| Windows | `ptool.bat` | `C:\Program Files\devtools\ptool\` | `C:\Program Files\devtools\ptool\config\ptool.conf` | `scripts/Windows/` |

macOS / Linux 还会在 `~/.devtools/ptool/shims` 下生成 `python` / `python3` / `pip` / `pip3` 包装脚本，
它们优先于系统 Python，并按当前默认版本转发调用。`ptool update` 使用的仓库缓存在 `~/.devtools/ptool/repo`。

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
├── VERSION                     # 版本号，ptool update 据此判断是否需要更新
├── bin/
│   ├── ptool.sh                # 主脚本 (macOS / Linux)
│   └── ptool.bat               # 主脚本 (Windows)
├── config/
│   └── ptool.conf              # 配置文件模板（首次安装时复制）
├── completions/
│   ├── ptool.zsh               # zsh 补全模板（安装时替换 @CONFIG_FILE@）
│   └── ptool.bash              # bash 补全模板
├── module/
│   └── common.sh               # 安装 / 扫描 / 更新 / 卸载逻辑（被 ptool.sh source）
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

> 注意仓库布局与**安装后**布局不同：安装时 `bin/ptool.sh` 会被复制到 `ptool/lib/ptool.sh`，
> 并在 `ptool/bin/ptool` 建立指向它的软链接。`bin/` 在 PATH 上、`lib/` 不在，
> 这样保证 PATH 里只有无后缀的 `ptool` 一个名字（见上方命名说明）。

## 常见问题

### Q: 提示 "permission denied"

用安装脚本重新安装（需要 sudo），或手动补权限：

```bash
# macOS
sudo chmod +x /Library/devtools/ptool/lib/ptool.sh

# Linux
sudo chmod +x /usr/local/devtools/ptool/lib/ptool.sh
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

ptool 只认一个基准目录 `PYTHON_BASE_DIR`。先执行 `ptool config` 查看当前配置文件路径，
再手动修改其中的 `PYTHON_BASE_DIR` 指向你的 Python 安装目录即可，例如：

```bash
PYTHON_BASE_DIR="/Users/yourname/.pyenv/versions"
```

修改后可用 `ptool list` 验证能否扫描到版本。

## 许可证

MIT License
