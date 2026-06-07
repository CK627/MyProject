# 我的项目集 (My Projects)

这个仓库包含了我近期完成的多个独立项目。为了方便管理和查阅，**每个项目都已分别存放在此仓库的独立分支中**，分支名称与项目名称相同。你可以切换到对应的分支查看各个项目的完整源代码。

## 📁 项目列表

### 1. 智慧校园服务平台 (Smart Campus Service Platform)
- **分支名**: `SmartCampusServicePlatform`
- **描述**: 一个综合性的智慧校园服务平台，集成了校园墙、互帮互助任务、电子钱包、社交好友及消息通知等功能，旨在为师生提供便捷的校园生活服务。
- **主要功能**: 校园墙（发帖/评论/点赞）、互助任务（发布/接单）、钱包系统（充值/转账）、好友社交、实时消息、后台管理。支持 GitHub OAuth 快捷登录。
- **技术栈**: Next.js, React, Tailwind CSS (前端); Python FastAPI, MySQL, SQLAlchemy (后端)。

### 2. 福建师范大学广东校友会一周年庆典晚会系统 (School Conference System)
- **分支名**: `SchoolConferenceSystem`
- **描述**: 为福建师范大学广东校友会一周年庆典开发的综合活动管理系统。它处理活动报名、座位安排和照片/视频直播。
- **主要功能**: 活动报名、座位可视化安排、二维码电子签到、照片/视频直播、后台数据大屏。
- **技术栈**: PHP, MySQL, Bootstrap 5, Chart.js。

### 3. 局域网聊天室 (ChatRoom)
- **分支名**: `ChatRoom`
- **描述**: 一个局域网聊天应用程序，能够自动发现同一网段的其他用户并进行实时通信。
- **主要功能**: 局域网网络扫描、P2P 消息传输、本地存储、Web 界面。
- **技术栈**: Python, Flask, SocketIO, WebSockets。

### 4. 飞控板维修工单管理系统 (Flight Control Board Maintenance Work Order System)
- **分支名**: `FlightControlBoardMaintenanceWorkOrderSystem`
- **描述**: 一个基于 Web 的维修工单管理系统，专门用于追踪和管理飞控板的维修记录。
- **主要功能**: 维修工单发布与管理、状态追踪、用户认证、数据库自动初始化、RESTful API。
- **技术栈**: PHP, MySQL。

### 5. 宁波旅游宣传网站 (Ningbo Travel Guide Website)
- **分支名**: `NingboTravelGuideWebsite`
- **描述**: 一个完整的旅游信息展示平台，致力于向游客全面展示宁波的文化底蕴、自然风光、美食住宿等旅游资源。
- **主要功能**: 前后端分离、响应式设计、内容管理后台、用户互动（留言板/评论）、图片懒加载。
- **技术栈**: HTML/CSS/Vanilla JavaScript (前端), PHP, MySQL (后端)。

### 6. 网站状态监控与邮件报警系统 (WebMailMonitor)
- **分支名**: `WebMailMonitor`
- **描述**: 一个基于 Python 开发的轻量级网站状态监控工具。它能够定时检测指定网站的 HTTP 状态码，当检测到异常时自动发送报警邮件，恢复正常时也会发送通知。
- **主要功能**: 实时监控、智能防抖报警（异常/恢复通知）、多模式运行（GUI托盘/控制台/Web可视化面板）、详细日志记录。
- **技术栈**: Python 3.6+, requests, pystray, schedule。

### 7. 衢州古城文化旅游信息平台 (Responsive Qujiang Travel Information Platform)
- **分支名**: `ResponsiveQujiangTravelInformationPlatform`
- **描述**: 一个为衢州衢江区设计的纯前端响应式文化旅游信息平台。它通过现代化的响应式用户界面展示了当地的景点、美食、旅游线路和民俗文化。
- **主要功能**: 100% 响应式设计、透明沉浸式导航栏、Tab 切换、图片懒加载、平滑滚动。
- **技术栈**: HTML5, CSS3, JavaScript, Vue.js (CDN)。

### 8. 区块链式随机数生成器 (Blockchain Random Number Generator)
- **分支名**: `BlockchainRandomNumberGenerator`
- **描述**: 这是一个极简的区块链概念演示项目。它在后端维护了一条简单的内存区块链结构，通过模拟挖矿（工作量证明 Proof of Work）生成新区块，并利用区块哈希特征生成随机数。
- **主要功能**: 区块链核心机制模拟、简易工作量证明 (PoW)、伪随机数生成、Web 界面交互。
- **技术栈**: Python, Flask。

### 9. 浏览器端二进制定位小工具 (BitTally)
- **分支名**: `BitTally`
- **描述**: 一个纯前端、单 HTML 文件的小工具：在浏览器中选择一个本地二进制文件（如镜像、固件等），程序会从文件开头开始扫描，找到第一个非 0 字节的位置并输出扇区和偏移量。
- **主要功能**: 纯前端 FileReader 处理、分片读取防卡顿、TypedArray 二进制分析、代码压缩极简写法。
- **技术栈**: HTML5, Vanilla JavaScript, FileReader API。

### 10. 文件管理与毕业提交系统 (FileUpload)
- **分支名**: `FileUpload`
- **描述**: 一个基于 PHP + MySQL 的 Web 文件管理系统，支持普通文件传输、毕业生材料提交与教师审批流程，采用毛玻璃（Glassmorphism）视觉风格。
- **主要功能**: 文件管理（上传/下载/重命名/移动/共享）、大文件分片上传、毕业生 12 种文档分类提交、教师审批批阅（通过/不通过自动跳转）、Excel 名单导入、批量打包下载。
- **技术栈**: PHP, MySQL, HTML/CSS/Vanilla JavaScript。

### 11. Java 版本管理工具 (jtool)
- **分支名**: `jtool`
- **描述**: 一个简单、跨平台的 Java 版本管理命令行工具，支持一行命令运行任意版本的 Java 工具，快速切换默认版本。
- **主要功能**: 指定版本运行 Java 工具、版本切换、自动扫描已安装 JDK、编译并运行一步到位。
- **技术栈**: Bash / Batch Shell 脚本。

### 12. Python 版本管理工具 (ptool)
- **分支名**: `ptool`
- **描述**: 一个简单、跨平台的 Python 版本管理命令行工具，支持多个搜索路径，自动扫描已安装版本。
- **主要功能**: 指定版本运行 Python/pip、版本切换、自定义搜索路径、跨平台支持。
- **技术栈**: Bash / Batch Shell 脚本。

---

## 📌 如何查看源码

你可以通过 Git 命令切换到你想查看的项目分支：

```bash
# 查看所有可用分支
git branch -a

# 切换到对应的项目分支，例如切换到局域网聊天室项目
git checkout ChatRoom
```
或者在 GitHub 的仓库页面左上角的 **Branch (分支)** 下拉菜单中直接点击对应的项目名称即可浏览代码。
