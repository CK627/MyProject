# 局域网聊天室 (ChatRoom)

> 一个基于 Python 和 Flask-SocketIO 的局域网点对点聊天与文件传输工具。

## 项目简介

**ChatRoom** 是一个专为同一局域网（同一网段）设计的轻量级聊天应用程序。它能够自动扫描并发现网络中的其他在线用户，支持实时的文字通讯与文件共享，且无需中心化服务器进行消息中转（采用 P2P 模式进行直接通信）。

该项目不仅提供了简单易用的 Web 界面，还在底层实现了硬链接（Hard Links）与异步删除等机制，以最大化节约本地存储空间并提升文件管理效率。

## 🌟 主要功能与特性

1. **自动网络扫描与发现 (Network Scanning)**
   - 自动检测本机的网络接口与 IP 地址。
   - 通过 UDP 广播自动发现同一网段内正在运行该程序的其他用户。
2. **实时点对点通信 (P2P Messaging)**
   - 采用 HTTP/WebSocket 进行数据传输，消息直接在两个客户端之间传递，保障局域网内的隐私与极低延迟。
3. **Web 浏览器界面 (Web Interface)**
   - 采用现代化、响应式的 Web UI，直接在浏览器中打开即可使用，无需安装额外的桌面客户端。
4. **本地存储与文件管理 (Local Storage)**
   - 所有聊天记录和传输的文件均加密或分类保存在本地。
   - 支持在 Web 界面中自定义存储路径。
5. **高效存储机制 (Efficient Storage)**
   - 采用文件硬链接（Hard Links）技术，相同文件不占用多余磁盘空间。
   - 实现异步文件删除队列，避免删除大文件时阻塞主线程。

## 🛠 技术架构与核心模块

项目采用 Python 作为后端，并结合 Web 技术构建前端：

- **核心语言与框架**: Python 3.x, Flask
- **实时通信**: Flask-SocketIO (基于 WebSocket), eventlet
- **网络与系统**: netifaces (网卡信息获取), requests (HTTP 请求)
- **前端技术**: HTML/CSS/JS (原生)

**核心模块说明**：
- `app.py`: Flask 主程序入口，包含 HTTP 路由、WebSocket 事件处理与 P2P 消息收发逻辑。
- `scanner.py`: 网络扫描模块，负责组播探测与局域网节点发现。
- `storage.py`: 存储管理模块，负责聊天记录持久化、文件保存、硬链接创建与异步删除清理。
- `static/` & `templates/`: 存放前端静态资源（JS/CSS）与 HTML 渲染模板。

## ⚙️ 环境配置与安装

### 1. 前置要求
- **Python 3.7+**
- 建议使用虚拟环境（Virtual Environment）运行以避免依赖冲突。

### 2. 安装依赖
克隆或下载本分支代码后，在项目根目录下执行：
```bash
pip install -r requirements.txt
```
*(依赖项包括：`flask`, `flask-socketio`, `eventlet`, `netifaces`, `requests`)*

## 🚀 启动与使用步骤

### 1. 修改配置（可选）
如果需要修改默认端口或网络设置，请在 `app.py` 中寻找以下占位符并替换为您实际需要的值：
```python
DISCOVERY_PORT = "<DISCOVERY_PORT>" # 默认可改为 5555
WEB_PORT = "<WEB_PORT>"             # 默认可改为 8080
```

### 2. 运行程序
在命令行中执行：
```bash
python app.py
```
*(程序启动后，会自动尝试使用默认浏览器打开应用界面)*

### 3. 使用操作
1. 在浏览器中访问 `http://localhost:<WEB_PORT>`（如果未自动跳转）。
2. 点击界面上的 **"Scan" (扫描)** 按钮，程序将搜索同一局域网下的其他节点。
3. 在左侧列表中点击发现的其他用户 IP，即可打开聊天窗口开始通讯。

## 📁 数据存储说明

聊天历史与文件将默认保存在以下系统路径中：
- **Windows**: `C:\Users\<用户名>\Documents\SmartCampusServicePlatform\<用户唯一ID>`
- **macOS/Linux**: `/Users/<用户名>/Documents/SmartCampusServicePlatform/<用户唯一ID>`

> **提示**：可以在 Web 界面中的设置面板更改此默认存储路径。

## 📅 未来规划 (Roadmap)

- [ ] **用户昵称与头像**：目前基于 IP 识别，计划加入自定义昵称广播功能。
- [ ] **群聊功能**：支持创建局域网多人群组进行广播通信。
- [ ] **端到端加密 (E2EE)**：在 P2P 通信链路中加入非对称加密，进一步保障局域网通信安全。
- [ ] **跨平台打包**：使用 PyInstaller 完善一键打包配置，提供开箱即用的 `.exe` / `.app` 安装包。