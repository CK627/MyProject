# jtool

跨平台 Java 版本管理工具，支持 macOS / Linux / Windows：`jtool <工具> <版本>` 直跑指定版本，
`jtool use <版本>` 设置默认版本，并把 `java` / `javac` / `jar` / `jshell` / `javadoc` / `javap` 包装脚本放进 PATH。

> 完整文档：[`docs/README.md`](docs/README.md)（安装、卸载、配置、跨平台差异、常见问题）

```bash
# macOS / Linux 一键安装（安装后自动刷新当前终端）
source <(curl -fsSL https://raw.githubusercontent.com/CK627/MyProject/jtool/installer/install.sh)

# Windows（PowerShell，会弹 UAC）
irm https://raw.githubusercontent.com/CK627/MyProject/jtool/installer/install.ps1 | iex
```

开发与测试见 `docs/README.md` 的「开发与测试」；`bash tests/smoke.sh` 可在本地跑 shell 侧冒烟。
