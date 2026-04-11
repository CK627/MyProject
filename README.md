# 福建师范大学广东校友会一周年庆典晚会系统

> 为大型校友会活动（如周年庆典、晚会等）定制开发的综合活动管理系统。提供从前期报名、座位分配到活动现场二维码签到、照片直播的一站式数字化解决方案。

## 📖 项目简介

**SchoolConferenceSystem** 是一个典型的 B/S 架构全栈 Web 系统，主要服务于“福建师范大学广东校友会一周年庆典”。系统设计充分考虑了移动端（微信生态）和 PC 端后台管理的不同使用场景，致力于提高大型活动的组织效率。

项目分为三个主要部分：
1. **PC 端前端 (`frontend/`)**：提供活动主页展示、报名入口等功能。
2. **移动端前端 (`frontend/mobile/`)**：专为微信环境优化的移动端页面，支持扫码签到、座位查询以及实时的照片/视频直播。
3. **后台管理端 (`backend/`)**：供活动组织者使用，涵盖报名审核、动态座位图分配、数据导出及数据大屏统计等功能。

## 🌟 主要功能与特性

- **报名与信息收集**：用户可在线填写报名表、上传缴费截图、申报才艺节目等。
- **智能化座位管理**：后台提供可视化的座位分配系统，管理员可根据报名情况灵活排座，用户可通过手机端输入手机号查询自己的具体桌号和座位号。
- **二维码电子签到**：系统生成带有用户标识的专属签到二维码，现场工作人员扫码或用户自助扫码即可完成签到，签到状态实时同步至后台。
- **多媒体直播支持**：集成照片直播和视频直播功能，未到场校友也可在线观看活动盛况。
- **后台数据大屏 (Dashboard)**：通过 Chart.js 实现多维度的数据统计与可视化（如报名人数趋势、签到率、费用统计等）。
- **数据导出**：支持将报名数据一键导出为 Excel/CSV 格式，方便线下核对。

## 🛠 技术架构与核心栈

- **前端技术**：HTML5, CSS3, 原生 JavaScript, Bootstrap 5, Chart.js (后台图表)
- **后端技术**：PHP 7.4+ (基于 PDO 安全操作数据库)
- **数据库**：MySQL 8.0 (推荐)
- **运行环境**：Nginx/Apache (支持 URL Rewrite)

## ⚙️ 环境配置与部署指南

### 1. 数据库准备
1. 建立 MySQL 数据库：
   ```sql
   CREATE DATABASE <DB_NAME> CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
2. 导入项目提供的数据库结构文件：
   - 寻找 `docs/school_conference.sql` 并在数据库中执行导入。

### 2. 数据库连接配置
为了让前后端正确连接数据库，你需要修改以下三个文件中的配置占位符（将其替换为你本地的真实信息）：
- `frontend/api/database.php`
- `frontend/mobile/api/database.php`
- `backend/api/database.php`

将文件中的配置修改为：
```php
define('DB_HOST', '<DB_HOST>');
define('DB_USERNAME', '<DB_USER>');
define('DB_PASSWORD', '<DB_PASSWORD>');
define('DB_NAME', '<DB_NAME>');
```

### 3. 微信 API 配置 (可选)
如果需要使用微信分享或特定接口功能，请配置 `frontend/mobile/api/weixin-secret.php`：
```php
'appId' => '<WECHAT_APP_ID>',
'appSecret' => '<WECHAT_APP_SECRET>',
```

## 🚀 启动与使用

1. 将整个项目部署到你的 PHP Web 服务器的根目录（如 `htdocs` 或 Nginx `html` 目录）。
2. **访问前端主页**：
   - 浏览器打开 `http://localhost/SchoolConferenceSystem/frontend/index.html`
3. **访问移动端**：
   - 浏览器打开 `http://localhost/SchoolConferenceSystem/frontend/mobile/index.html`（建议使用浏览器的移动端模拟模式查看）
4. **访问后台管理**：
   - 浏览器打开 `http://localhost/SchoolConferenceSystem/backend/login.html`
   - 默认测试账号：`admin`
   - 默认测试密码：`admin123` （*请在部署到生产环境前修改*）

## 📁 目录结构概览

```text
SchoolConferenceSystem/
├── backend/            # PC端后台管理系统
│   ├── api/            # 后台专用的 PHP 接口
│   ├── css/            # 后台样式表
│   ├── js/             # 后台逻辑脚本
│   └── index.html      # 后台控制台页面
├── frontend/           # PC端前台页面
│   ├── api/            # PC端前台交互 PHP 接口
│   ├── mobile/         # 移动端页面 (H5)
│   │   ├── api/        # 移动端专用的 PHP 接口 (含微信交互)
│   │   └── index.html  # 移动端首页
│   ├── css/            
│   └── js/             
└── docs/               # 数据库文件及开发文档
```

## 📅 未来规划 (Roadmap)

- [ ] **在线支付集成**：接入微信支付 / 支付宝 API，替换目前的人工上传付款截图模式，实现全自动缴费确认。
- [ ] **更强大的扫码枪支持**：优化后台签到接口，适配硬件扫码枪的连续输入。
- [ ] **照片直播自动化**：引入云存储（如 OSS/COS），并增加现场摄影师实时传图的客户端接口。
