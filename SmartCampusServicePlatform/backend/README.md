# Smart Campus Service Platform Backend

智慧校园服务平台后端API

## 技术栈

- **框架**: FastAPI
- **数据库**: MySQL + SQLAlchemy ORM
- **认证**: JWT (JSON Web Tokens)
- **密码加密**: bcrypt

## 项目结构

```
backend/
├── app/
│   ├── api/                # API路由
│   │   ├── auth.py        # 认证相关
│   │   ├── users.py       # 用户管理
│   │   ├── posts.py       # 校园墙
│   │   ├── tasks.py       # 互帮互助
│   │   ├── wallet.py      # 钱包系统
│   │   ├── friends.py     # 好友系统
│   │   ├── messages.py    # 消息通知
│   │   ├── announcements.py # 公告系统
│   │   ├── school.py      # 学校信息
│   │   └── admin.py       # 管理后台
│   ├── core/              # 核心功能
│   │   ├── security.py    # 安全工具
│   │   └── deps.py        # 依赖注入
│   ├── models/            # 数据模型
│   │   └── models.py      # SQLAlchemy模型
│   ├── schemas/           # Pydantic模式
│   │   ├── user.py
│   │   ├── auth.py
│   │   ├── post.py
│   │   ├── task.py
│   │   ├── wallet.py
│   │   ├── friend.py
│   │   ├── message.py
│   │   └── announcement.py
│   ├── config.py          # 配置管理
│   ├── database.py        # 数据库连接
│   └── main.py            # 主入口
├── .env                   # 环境变量
└── requirements.txt       # 依赖列表
```

## 安装与运行

### 1. 创建虚拟环境

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

本项目使用环境变量注入运行配置，**请不要把真实密码/密钥提交到仓库**。

1) 复制示例文件：

```bash
cp .env.example .env
```

2) 按需修改 `.env`（以下为关键项）：

| 变量 | 说明 |
| --- | --- |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | MySQL 连接信息 |
| `SECRET_KEY` | JWT 签名密钥（生产环境必须是强随机值） |
| `SMTP_*` | 忘记密码邮件发送配置（可选） |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth（可选） |

### 4. 运行服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或直接运行
python -m app.main
```

### 5. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API接口

### 认证 `/api/v1/auth`
- `POST /login` - 用户登录
- `POST /register` - 用户注册
- `POST /change-password` - 修改密码
- `GET /me` - 获取当前用户信息

### 用户 `/api/v1/users`
- `GET /me` - 获取个人详细信息
- `PUT /me` - 更新个人信息
- `PUT /me/profile` - 更新用户档案
- `GET /{user_id}` - 获取用户信息
- `GET /` - 搜索用户

### 校园墙 `/api/v1/posts`
- `POST /` - 发布帖子
- `GET /` - 获取帖子列表
- `GET /{post_id}` - 获取帖子详情
- `PUT /{post_id}` - 更新帖子
- `DELETE /{post_id}` - 删除帖子
- `POST /{post_id}/comments` - 发表评论
- `POST /{post_id}/like` - 点赞
- `DELETE /{post_id}/like` - 取消点赞

### 互帮互助 `/api/v1/tasks`
- `POST /` - 发布任务
- `GET /` - 获取任务列表
- `GET /{task_id}` - 获取任务详情
- `POST /{task_id}/apply` - 申请任务
- `POST /{task_id}/complete` - 完成任务

### 钱包 `/api/v1/wallet`
- `GET /` - 获取钱包信息
- `GET /transactions` - 获取交易记录
- `POST /recharge` - 充值
- `POST /transfer` - 转账

### 好友 `/api/v1/friends`
- `GET /` - 获取好友列表
- `POST /requests` - 发送好友请求
- `GET /requests/received` - 收到的请求
- `POST /requests/{id}/accept` - 接受请求
- `GET /blacklist` - 黑名单列表

### 消息 `/api/v1/messages`
- `GET /conversations` - 获取会话列表
- `GET /with/{user_id}` - 获取聊天记录
- `POST /` - 发送消息
- `GET /notifications` - 获取通知

### 公告 `/api/v1/announcements`
- `GET /` - 获取公告列表
- `GET /{id}` - 获取公告详情

### 学校信息 `/api/v1/school`
- `GET /info` - 获取学校信息
- `GET /departments` - 获取院系列表
- `GET /facilities` - 获取设施列表

### 管理 `/api/v1/admin`
- `GET /stats` - 平台统计
- `GET /reports` - 举报列表
- `POST /reports/{id}/resolve` - 处理举报
