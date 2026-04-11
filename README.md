# 智慧校园服务平台 (Smart Campus Service Platform)

> 一个集成了校园动态、互助任务、电子钱包和即时通讯的一站式数字化校园解决方案。

## 📖 项目简介

**智慧校园服务平台** 采用现代化的前后端分离架构（B/S架构）设计，旨在解决高校校园内资源信息分散、互助需求难以满足等问题。平台为师生提供了一个安全、稳定且易扩展的数字化社区。

核心业务包含用户认证体系、信息发布（校园墙）、任务大厅（发布/接单互助）、即时消息（WebSocket）以及带信誉评价系统的虚拟钱包机制。

## 🌟 主要功能与特性

- **双重认证与安全**：基于 JWT 令牌的鉴权机制，并使用 bcrypt 算法进行密码安全加密。
- **第三方登录集成**：支持通过 **GitHub OAuth** 进行快速注册与登录，降低用户注册门槛。
- **校园动态（校园墙）**：用户可以发布图文动态，并支持点赞、评论等基础互动。
- **互助任务大厅**：校园内的悬赏任务平台。用户可发布求助（如代取快递、借用物品等）并附带赏金，其他用户接单完成。
- **即时通讯 (IM)**：基于 WebSocket 的实时在线消息系统，用于接单人与发单人的沟通。
- **电子钱包系统**：内置虚拟钱包，支持平台内模拟充值、任务悬赏冻结、以及完单后的转账结算。
- **信誉与社区治理机制**：
  - 基于完单质量计算好评率和信誉分。
  - 社区自治模式：评论区内容可通过社区投票判定进行软删除。

## 🛠 技术架构与核心栈

### 前端 (Frontend)
- **框架**: Next.js 14+ (React 18)
- **语言**: TypeScript
- **UI 库**: Tailwind CSS
- **通信**: Fetch API / 原生 WebSocket API

### 后端 (Backend)
- **框架**: FastAPI (Python 3.8+)
- **ORM**: SQLAlchemy 2.0 (支持异步)
- **数据库**: MySQL 8.0+ (也支持配置为 SQLite 或 PostgreSQL)
- **其他库**: passlib (加密), python-jose (JWT), pymysql

## ⚙️ 环境配置与部署

本项目需要分别启动后端服务和前端服务。

### 1. 数据库准备 (MySQL)
1. 安装并启动 MySQL。
2. 创建数据库（建议名为 `smart_campus`，字符集为 `utf8mb4`）。

### 2. 后端配置与运行
1. 进入 `backend/` 目录：
   ```bash
   cd backend
   ```
2. 创建 Python 虚拟环境并激活：
   ```bash
   python -m venv venv
   # Windows: venv\Scripts\activate
   # Linux/Mac: source venv/bin/activate
   ```
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
4. 配置环境变量：
   将 `backend/.env.example` 复制为 `backend/.env`，并将占位符替换为你的实际信息：
   ```env
   DB_HOST=<YOUR_DB_HOST>
   DB_PORT=3306
   DB_USER=<YOUR_DB_USER>
   DB_PASSWORD=<YOUR_DB_PASSWORD>
   DB_NAME=<YOUR_DB_NAME>
   SECRET_KEY=<生成一个强随机的字符串作为JWT秘钥>
   GITHUB_CLIENT_ID=<你的GitHub_OAuth_APP_ID>
   GITHUB_CLIENT_SECRET=<你的GitHub_OAuth_SECRET>
   ```
5. 启动后端服务 (FastAPI)：
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   *(启动后，可访问 `http://localhost:8000/docs` 查看自动生成的 Swagger 接口文档)*

### 3. 前端配置与运行
1. 确保已安装 Node.js (v18+)。
2. 回到项目根目录（或 `frontend/`，视具体 `package.json` 位置而定）：
   ```bash
   npm install
   # 或 yarn install
   ```
3. 启动前端开发服务器：
   ```bash
   npm run dev
   ```
4. 在浏览器中访问：`http://localhost:3000`（或控制台提示的端口）。

## 📁 目录结构概览

```text
SmartCampusServicePlatform/
├── backend/               # FastAPI 后端源码
│   ├── app/
│   │   ├── main.py        # 后端入口
│   │   ├── config.py      # 配置管理 (Pydantic)
│   │   ├── models/        # SQLAlchemy 数据库模型
│   │   ├── routers/       # 业务 API 路由
│   │   └── ...
│   ├── requirements.txt
│   └── .env.example
├── components/            # React 业务与 UI 组件
├── lib/                   # 前端工具库 (WebSocket/API)
├── app/                   # Next.js App Router 页面路由
├── public/                # 静态资源
├── package.json           # 前端依赖配置
└── tailwind.config.ts     # Tailwind 样式配置
```

## 📅 未来规划 (Roadmap)

- [ ] **接入真实支付**：当前钱包为模拟充值，未来可接入微信支付或支付宝沙箱环境。
- [ ] **Redis 缓存集成**：对于热门的校园墙动态，引入 Redis 缓存以提升读取速度。
- [ ] **分布式 WebSocket**：在多实例部署时，使用 Redis Pub/Sub 解决跨节点的 WebSocket 消息推送问题。
- [ ] **管理员后台仪表盘**：增加独立的管理员后台前端界面，方便对用户信誉、恶意发帖等进行集中管理。
