# 网站状态监控与邮件报警系统 (WebMailMonitor)

> 一个基于 Python 开发的轻量级网站状态监控工具。它能够定时检测指定网站的 HTTP 状态码，当检测到状态异常或恢复正常时，自动发送通知邮件。

## 📖 项目简介

**WebMailMonitor** 专为个人站长或小微团队设计，旨在提供一个极简、开箱即用的网站健康监控方案。相比于庞大的监控系统，它无需复杂的配置，只需简单的脚本运行，即可实现对目标 URL 的定时探测（Ping），并通过标准的 SMTP 协议发送告警邮件。

本项目提供了三种运行模式以满足不同的使用场景：
1. **控制台模式**：纯后台定时轮询，适合部署在 Linux 服务器上使用 `nohup` 或 `systemd` 运行。
2. **GUI 托盘模式**：包含系统托盘图标，适合在 Windows 个人电脑后台运行，可随时右键配置或退出。
3. **Web 面板模式**：内置了一个轻量级的 HTTP 服务器，可以通过浏览器直接查看当前监控日志和状态。

## 🌟 主要功能与特性

- **实时状态监控**：定时发起 HTTP GET 请求，比对实际状态码与预期状态码（默认 200）。
- **智能邮件报警**：
  - **异常通知**：当网站宕机或状态码错误时，立即发送报警邮件。
  - **恢复通知**：当网站从异常状态中恢复正常时，发送恢复通知邮件。
  - **状态防抖**：同一状态持续时不会重复发送邮件，避免邮箱被“轰炸”。
- **多运行模式**：控制台输出、GUI 托盘图标控制、Web 面板查看日志。
- **详尽的日志记录**：将所有的检查结果、网络错误、发信记录保存至本地 `.log` 文件中。

## 🛠 技术架构与核心栈

- **开发语言**: Python 3.6+
- **网络请求**: `requests` (处理 HTTP 探测)
- **邮件服务**: 内置 `smtplib` 与 `email` 模块 (支持 SSL 发信)
- **定时任务**: `schedule` (处理周期性轮询)
- **GUI 托盘**: `pystray` 与 `PIL`
- **Web 面板**: 内置 `http.server` 结合原生 Vue.js (CDN) 进行简单日志渲染。

## ⚙️ 环境配置与安装

### 1. 前置要求
- Python 3.6 或更高版本。
- 建议使用虚拟环境 (Virtual Environment)。

### 2. 安装依赖
克隆项目后，进入目录并安装必须的第三方库：
```bash
pip install requests schedule pystray pillow
```

### 3. 配置文件修改
系统运行依赖于根目录下的 `config.ini` 文件。初次使用前，请使用文本编辑器打开它，并填入你自己的配置：
```ini
[Settings]
url = http://www.your-website.com     # 需要监控的网址
expected_code = 200                   # 期待的 HTTP 状态码
sender_email = <YOUR_EMAIL@example.com> # 你的发信与收信邮箱（自己发给自己）
auth_code = <YOUR_SMTP_AUTH_CODE>       # 邮箱的 SMTP 授权码（注意：不是登录密码）
web_port = 2442                       # Web 面板的端口号
```

*(注意：如果你使用其他邮箱服务商而不是 QQ 邮箱，请在 `common_lib.py` 中修改 `SMTP_SERVER` 变量)*

## 🚀 启动与使用步骤

根据你的需求，选择一个主程序运行：

**方式 1：Web 面板服务器模式 (推荐)**
不仅后台监控，还在指定端口（默认 2442）启动一个可访问的日志面板。
```bash
python web_monitor_server.py
```
*启动后，在浏览器访问 `http://localhost:2442` 查看监控日志大屏。*

**方式 2：纯控制台模式 (适合 Linux 服务器后台运行)**
只在控制台打印日志并发送邮件，没有 Web 面板和 GUI。
```bash
python web_monitor_console.py
# 或在 Linux 下后台运行：
# nohup python web_monitor_console.py >/dev/null 2>&1 &
```

**方式 3：系统托盘 GUI 模式 (适合 Windows 桌面端)**
启动后会隐藏在系统右下角托盘中，可右键进行控制。
```bash
python web_monitor.py
```

## 📁 目录结构说明

```text
WebMailMonitor/
├── config.ini               # 核心配置文件
├── common_lib.py            # 公共核心库（邮件发送、日志记录、配置读取）
├── web_monitor_server.py    # 运行模式 1: 监控 + Web 服务器
├── web_monitor_console.py   # 运行模式 2: 纯控制台后台监控
├── web_monitor.py           # 运行模式 3: 系统托盘 GUI 监控
├── config_gui.py            # 配置修改的 GUI 界面逻辑
├── index.html               # Web 面板的 Vue.js 前端页面
├── logs/                    # 运行时自动生成的日志目录
└── *.sh / *.bat             # 方便在各种系统下一键启动的脚本
```

## 📅 未来规划 (Roadmap)

- [ ] **多站点监控**：支持在 `config.ini` 中配置一个列表，同时对多个不同的 URL 进行轮询。
- [ ] **响应时间监控**：除了状态码，增加对 TTFB (首字节时间) 的监控，当响应过慢时报警。
- [ ] **WebHook 支持**：除了发送邮件，支持推送到企业微信、钉钉、飞书或 Server酱 的机器人。
- [ ] **可视化配置页面**：在 Web 面板中直接提供修改 `config.ini` 配置的表单。
