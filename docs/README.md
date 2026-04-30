# Smart Campus Service Platform

智慧校园服务平台 - 面向高校数字化场景的全栈应用

## 项目概述

Smart Campus Platform 是一个现代化的智慧校园服务平台，旨在为高校师生提供一站式的数字化校园体验。平台涵盖社交互动、任务协作、信息发布、即时通讯等核心功能，采用前后端分离架构，具备完善的安全控制和审核治理机制。

## 本次文档更新（对比旧版）

| 模块 | 旧版文档问题/缺失 | 本次更新内容 |
|:-----|:-----------------|:-------------|
| 用户体系 | 将 reviewer 作为用户角色枚举，和实际模型不一致 | 修正为 reviewer 为“信誉分达标后的权限身份”，用户角色仅包含 student/teacher/admin |
| 认证系统 | “找回/重置密码”仅有描述，缺少后端核心实现代码段；GitHub 回调代码段与实际实现略有出入 | 补充 forgot-password/reset-password 关键代码段；同步 GitHub OAuth 回调实现细节 |
| 信誉系统 | 缺少互赞相关接口的完整闭环描述 | 增补 like/unlike/like-status/profile 等接口与核心逻辑说明 |
| 互助任务 | 申请列表排序逻辑未体现 priority_score 回填 | 同步 tasks.py 实际实现（包含 priority_score 字段回填） |
| 即时通讯 | 消息推送示例未体现“发送者自身多端同步” | 同步 messages.py：消息通过 WebSocket 同时推送给接收者与发送者 |
| 文件管理 | 将“硬链接”作为已实现特性，但代码实际为“Hash 去重 + 引用计数 + 延迟清理” | 修正文档表述；同步 FileStorageManager 的实际实现片段 |
| 安全/运维 | “HTTPS 强制 / 密钥轮换”等在架构图中被描述为已实现 | 调整为部署建议，不在“已实现能力”中宣称 |

### 功能架构图

```mermaid
graph TD
    A[智慧校园平台] --> B[用户体系]
    A --> C[内容社区]
    A --> D[即时通讯]
    A --> E[校园服务]
    A --> F[审核治理]
    A --> G[文件管理]
    A --> H[安全控制]
    B --> B1[用户注册登录]
    B --> B2[个人资料]
    B --> B3[好友关系]
    C --> C1[公告发布]
    C --> C2[校园墙]
    C --> C3[互助任务]
    C --> C4[评论互动]
    D --> D1[消息收发]
    D --> D2[在线状态]
    E --> E1[学校介绍]
    E --> E2[钱包系统]
    E --> E3[用户活跃度]
    F --> F1[审核员启用]
    F --> F2[内容审核]
    F --> F3[任务审核]
    G --> G1[文件上传]
    G --> G2[文件下载]
    G --> G3[IndexedDB缓存]
    G --> G4[引用计数]
    G --> G5[延迟清理]
    H --> H1[JWT鉴权]
    H --> H2[CORS限制]
    H --> H3[bcrypt密码加密]
    H --> H4[邮件重置密码]
```

---

## 技术栈

### 前端技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Next.js | Latest | React全栈框架，支持SSR/SSG |
| React | Latest | UI组件库 |
| TypeScript | Latest | 类型安全 |
| Tailwind CSS | ^3.4.0 | 原子化CSS框架 |
| lucide-react | Latest | 现代图标库 |
| class-variance-authority | Latest | CSS类变体工具 |
| clsx | Latest | 条件类名工具 |
| tailwind-merge | Latest | Tailwind类合并 |
| tailwindcss-animate | Latest | Tailwind动画扩展 |

### 后端技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| FastAPI | 0.109.0 | 高性能Python Web框架 |
| Uvicorn | 0.27.0 | ASGI服务器 |
| SQLAlchemy | 2.0.25 | ORM框架 |
| PyMySQL | 1.1.0 | MySQL驱动 |
| python-jose | 3.3.0 | JWT实现 |
| passlib[bcrypt] | 1.7.4 | 密码加密 |
| Pydantic | 2.5.3 | 数据验证 |
| pydantic-settings | 2.1.0 | 配置管理 |
| Redis | 5.0.1 | 缓存支持 |
| APScheduler | 3.10.4 | 定时任务调度 |

### 数据库支持

- **SQLite**: 开发环境默认数据库
- **PostgreSQL**: 生产环境推荐
- **MySQL**: 生产环境支持

---

## 项目结构

```
SmartCampusServicePlatform/
├── app/                        # Next.js 前端应用
│   ├── auth/
│   │   └── github/
│   │       └── callback/
│   │           └── page.tsx     # GitHub OAuth 回调页面
│   ├── reset-password/
│   │   └── page.tsx            # 重置密码页面
│   ├── globals.css            # 全局样式
│   ├── layout.tsx             # 根布局
│   └── page.tsx               # 主页面
├── components/                 # React组件
│   ├── ui/                    # 基础UI组件
│   ├── LoginPage.tsx          # 登录页
│   ├── CampusWall.tsx         # 校园墙
│   ├── MutualHelp.tsx         # 互助任务
│   ├── Friends.tsx            # 好友模块
│   ├── Messages.tsx           # 消息中心
│   ├── ChatWindow.tsx         # 聊天窗口
│   ├── Profile.tsx            # 个人中心
│   ├── WalletPage.tsx         # 钱包页面
│   └── ...                    # 其他组件
├── lib/                        # 工具库
│   ├── api.ts                 # API服务层
│   ├── websocket.ts           # 前端 WebSocket 管理器
│   ├── messageStorage.ts      # IndexedDB 消息缓存
│   └── ...                    # 其他工具模块
├── backend/                    # FastAPI 后端服务
│   ├── app/
│   │   ├── api/               # API路由模块
│   │   │   ├── auth.py        # 认证接口（含 GitHub OAuth/找回密码/点赞）
│   │   │   ├── users.py       # 用户管理
│   │   │   ├── posts.py       # 校园墙（评论拉踩/审核员投票）
│   │   │   ├── tasks.py       # 互帮互助（冻结/结算/优先分排序）
│   │   │   ├── wallet.py      # 钱包系统
│   │   │   ├── friends.py     # 好友系统（在线好友）
│   │   │   ├── messages.py    # 消息接口（多端同步推送）
│   │   │   ├── announcements.py # 公告系统（含阅读状态）
│   │   │   ├── school.py      # 学校信息
│   │   │   ├── files.py       # 文件管理（Hash去重/引用计数/清理）
│   │   │   ├── user_activity.py # 活跃度
│   │   │   └── admin.py       # 管理后台
│   │   ├── core/              # 核心能力（安全/邮件/OAuth等）
│   │   ├── models/            # 数据模型
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── tasks/             # 定时任务（文件清理/活跃度检查）
│   │   ├── utils/             # 工具（文件管理等）
│   │   ├── websocket/         # WebSocket（连接管理/路由）
│   │   ├── config.py          # 后端配置（BaseSettings）
│   │   ├── database.py        # 数据库连接
│   │   └── main.py            # 应用入口（API_PREFIX=/api/v1）
│   ├── storage/               # 后端文件存储目录（分层哈希）
│   ├── .env.example           # 后端环境变量示例
│   ├── requirements.txt       # Python依赖
│   └── campus.db              # 开发数据库（示例/本地）
├── docs/                       # 毕设/文档
│   ├── README.md
│   ├── 摘要.md
│   ├── 1.md
│   ├── 2.md
│   ├── 3.md
│   ├── 4.md
│   └── 结论.md
├── scripts/                    # 一键脚本（按平台区分）
│   ├── MacOS/
│   ├── Linux/
│   └── Windows/
├── config.ts                   # 前端统一配置
├── package.json
├── next.config.mjs
├── tailwind.config.ts
├── .env.local.example          # 前端环境变量示例
└── README.md                   # 项目根说明
```

---

## 核心功能详解

### 1. 用户认证系统

#### 1.1 用户注册、登录与找回密码

支持邮箱注册，密码使用bcrypt加密存储，JWT令牌认证。同时集成了 **GitHub OAuth** 第三方登录，并支持基于邮件发送重置链接的密码找回功能。

**后端实现 - 用户注册** (`backend/app/api/auth.py`):

```python
@router.post("/register", response_model=UserResponse, summary="用户注册")
async def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """用户注册"""
    # Check if email exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        name=user_data.name,
        phone=user_data.phone,
        role="student",
        status="active"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create wallet for new user
    wallet = Wallet(user_id=new_user.id, balance=0.0, frozen_amount=0.0)
    db.add(wallet)
    db.commit()
    
    return new_user
```

**后端实现 - GitHub OAuth登录** (`backend/app/api/auth.py`):

```python
@router.post("/github/callback", response_model=Token, summary="GitHub OAuth回调")
async def github_callback(
    data: GitHubCallbackRequest,
    db: Session = Depends(get_db)
):
    """处理GitHub OAuth授权回调"""
    try:
        # 用授权码换取access_token并获取GitHub用户信息
        access_token = await exchange_github_code(data.code)
        github_user = await get_github_user_info(access_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub登录失败: {str(e)}"
        )

    github_id = github_user["github_id"]
    email = github_user["email"]
    name = github_user["name"]
    avatar_url = github_user.get("avatar_url")

    # 先按github_id查找
    user = db.query(User).filter(User.github_id == github_id).first()

    if not user:
        # 按email查找
        user = db.query(User).filter(User.email == email).first()
        if user:
            # 已有账号，绑定github_id
            if user.github_id and user.github_id != github_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该邮箱已绑定其他GitHub账号"
                )
            user.github_id = github_id
            if avatar_url and not user.avatar:
                user.avatar = avatar_url
        else:
            # 自动注册新用户
            user = User(
                email=email,
                password_hash=None,
                name=name,
                github_id=github_id,
                avatar=avatar_url,
                role="student",
                status="active"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # 创建钱包
            wallet = Wallet(user_id=user.id, balance=0.0, frozen_amount=0.0)
            db.add(wallet)

    if user.status == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )

    # 更新登录状态
    user.last_login = datetime.utcnow()
    user.online_status = 'online'
    user.last_active = datetime.utcnow()
    db.commit()

    # 生成JWT
    jwt_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else user.role
        }
    )
    return Token(access_token=jwt_token, token_type="bearer")
```

**后端实现 - 忘记密码（发送重置邮件）** (`backend/app/api/auth.py`):

```python
@router.post("/forgot-password", response_model=SuccessResponse, summary="忘记密码")
async def forgot_password(
    data: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """发送密码重置邮件"""
    user = db.query(User).filter(User.email == data.email).first()

    if user:
        # OAuth用户无需密码重置
        if user.github_id and not user.password_hash:
            return SuccessResponse(message="该账号使用GitHub登录，无需重置密码")

        token = generate_reset_token()
        user.password_reset_token = token
        user.password_reset_expires = datetime.utcnow() + timedelta(minutes=30)
        db.commit()

        origin = request.headers.get("origin")
        frontend_url = origin if origin else settings.FRONTEND_URL
        send_password_reset_email(user.email, token, frontend_url)

    return SuccessResponse(message="如果该邮箱已注册，重置链接已发送到您的邮箱")
```

**后端实现 - 重置密码（通过 token 设置新密码）** (`backend/app/api/auth.py`):

```python
@router.post("/reset-password", response_model=SuccessResponse, summary="重置密码")
async def reset_password(
    data: ResetPasswordConfirm,
    db: Session = Depends(get_db)
):
    """通过重置token设置新密码"""
    user = db.query(User).filter(User.password_reset_token == data.token).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的重置链接")

    if not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
        user.password_reset_token = None
        user.password_reset_expires = None
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="重置链接已过期，请重新申请")

    user.password_hash = get_password_hash(data.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()

    return SuccessResponse(message="密码重置成功，请使用新密码登录")
```

**后端实现 - JWT令牌生成** (`backend/app/core/security.py`):

```python
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
```

**前端实现 - 登录页面** (`components/LoginPage.tsx`):

```tsx
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault()
  setLoading(true)
  setError('')
  
  try {
    if (isLogin) {
      // 登录
      const tokenResponse = await authApi.login({
        username: formData.email,
        password: formData.password
      })
      
      // 保存token
      setToken(tokenResponse.access_token)
      
      // 获取用户信息
      const user = await authApi.getCurrentUser()
      
      onLogin({
        name: user.name,
        role: user.role,
        avatar: user.avatar
      })
    } else {
      // 注册逻辑...
    }
  } catch (err: any) {
    setError(err.message || '操作失败，请重试')
  } finally {
    setLoading(false)
  }
}
```

#### 1.2 用户角色与权限

系统支持三种用户角色（与数据模型 `UserRole` 一致）：

| 角色 | 枚举值 | 说明 |
|------|--------|------|
| 学生 | `student` | 默认角色 |
| 教师 | `teacher` | 教职工 |
| 管理员 | `admin` | 系统管理 |

审核员（Reviewer）不是 `UserRole` 中的固定角色，而是依据信誉分自动获得的“权限身份”（见 2.2 与校园墙模块中的 `is_user_reviewer` 实现）。

**数据模型定义** (`backend/app/models/models.py`):

```python
class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"

class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    banned = "banned"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, comment="用户ID")
    email = Column(String(255), unique=True, index=True, nullable=False, comment="邮箱，唯一标识")
    password_hash = Column(String(255), nullable=True, comment="密码哈希值，OAuth用户可为空")
    name = Column(String(100), nullable=False, comment="用户姓名")
    phone = Column(String(20), comment="手机号码")
    avatar = Column(Text(length=4294967295), comment="头像Base64或URL")
    role = Column(Enum(UserRole), default=UserRole.student, comment="用户角色：student/teacher/admin")
    status = Column(Enum(UserStatus), default=UserStatus.active, comment="账户状态：active/inactive/banned")
    online_status = Column(String(20), default='offline', comment="在线状态: online/away/offline")
    last_active = Column(DateTime, comment="最后活跃时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    last_login = Column(DateTime, comment="最后登录时间")
    github_id = Column(String(100), nullable=True, unique=True, index=True, comment="GitHub OAuth用户ID")
    password_reset_token = Column(String(255), nullable=True, comment="密码重置token")
    password_reset_expires = Column(DateTime, nullable=True, comment="密码重置token过期时间")
    
    # 关系
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    posts = relationship("Post", back_populates="author")
    wallet = relationship("Wallet", back_populates="user", uselist=False)
```

---

### 2. 信誉系统

#### 2.1 信誉分与获赞机制

每个用户有一个信誉分（初始60分）及获赞数，通过以下方式变化：

- **增加信誉**: 完成任务、获得好评
- **减少信誉**: 违规被删除评论（-2~-10分）、被举报处理
- **用户点赞**: 其他用户可以为该用户点赞，增加其档案中的 `like_count`，进一步提升用户在社区内的受欢迎度。

**后端实现 - 用户点赞功能** (`backend/app/api/auth.py`):

```python
@router.post("/users/{user_id}/like", response_model=SuccessResponse, summary="点赞用户")
async def like_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """给用户点赞"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能给自己点赞"
        )
    
    # 检查目标用户是否存在
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 检查是否已点赞
    existing_like = db.query(UserLike).filter(
        UserLike.from_user_id == current_user.id,
        UserLike.to_user_id == user_id
    ).first()
    
    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已经点赞过了"
        )
    
    # 添加点赞记录
    new_like = UserLike(from_user_id=current_user.id, to_user_id=user_id)
    db.add(new_like)
    
    # 更新被点赞用户的点赞数
    target_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if target_profile:
        target_profile.like_count = (target_profile.like_count or 0) + 1
    else:
        # 如果用户没有profile，创建一个
        target_profile = UserProfile(user_id=user_id, like_count=1, credit_score=60)
        db.add(target_profile)
    
    db.commit()
    return SuccessResponse(message="点赞成功")
```

**其他相关接口**（同属 `backend/app/api/auth.py`，路由前缀 `/auth`）：

- `DELETE /auth/users/{user_id}/like`：取消点赞（同步减少 `like_count`）
- `GET /auth/users/{user_id}/like-status`：查询是否已点赞
- `GET /auth/users/{user_id}/profile`：获取信誉分、好评率与优先分等档案信息

**用户档案模型** (`backend/app/models/models.py`):

```python
class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True, comment="用户资料ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, comment="关联用户ID")
    student_id = Column(String(50), comment="学号")
    department = Column(String(100), comment="院系")
    major = Column(String(100), comment="专业")
    enroll_year = Column(Integer, comment="入学年份")
    bio = Column(Text, comment="个人简介")
    gender = Column(String(10), comment="性别")
    birthday = Column(DateTime, comment="生日")
    dormitory = Column(String(100), comment="宿舍")
    rating = Column(DECIMAL(3, 2), default=5.00, comment="用户评分")
    total_tasks_completed = Column(Integer, default=0, comment="完成任务总数")
    total_tasks_published = Column(Integer, default=0, comment="发布任务总数")
    
    # 信誉系统字段
    credit_score = Column(Integer, default=60, comment="信誉分，初始60分（及格）")
    like_count = Column(Integer, default=0, comment="获赞数")
    total_reviews = Column(Integer, default=0, comment="被评价总数，用于计算好评率")
    positive_reviews = Column(Integer, default=0, comment="好评数")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    @property
    def approval_rate(self):
        """好评率"""
        if self.total_reviews == 0:
            return 1.0  # 无评价时默认100%好评率
        return self.positive_reviews / self.total_reviews
    
    @property
    def priority_score(self):
        """优先分 = (信誉分 + 好评率 * 100) // 2"""
        return (self.credit_score + int(self.approval_rate * 100)) // 2
```

#### 2.2 审核员权限自动获取

信誉分超过阈值（默认 98 分）的用户自动获得审核员权限。该机制不改变 `User.role`，而是在需要审核员权限的接口中进行权限判断；核心实现位于校园墙模块 [posts.py](file:///Users/jj/Documents/MyCode/SmartCampusServicePlatform/backend/app/api/posts.py)：

```python
# 审核员所需的最低信誉分
REVIEWER_MIN_CREDIT_SCORE = 98

def is_user_reviewer(user: User, db: Session) -> bool:
    """检查用户是否有审核员权限（信誉分>98或管理员）"""
    if user.role == "admin":
        return True
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile and profile.credit_score > REVIEWER_MIN_CREDIT_SCORE:
        return True
    return False
```

---

### 3. 校园墙（帖子系统）

#### 3.1 帖子发布与审核

帖子发布后需要审核通过才能公开显示：

**帖子模型**:

```python
class PostStatus(str, enum.Enum):
    pending = "pending"     # 待审核
    approved = "approved"   # 已通过
    rejected = "rejected"   # 已拒绝
    deleted = "deleted"     # 已删除

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False, comment="帖子内容")
    images = Column(JSON, comment="图片列表JSON")
    likes_count = Column(Integer, default=0, comment="点赞数")
    comments_count = Column(Integer, default=0, comment="评论数")
    status = Column(Enum(PostStatus), default=PostStatus.approved, comment="审核状态")
    is_anonymous = Column(Boolean, default=False, comment="是否匿名发布")
    created_at = Column(DateTime, server_default=func.now())
    
    author = relationship("User", back_populates="posts")
    tags = relationship("PostTag", back_populates="post")
    comments = relationship("PostComment", back_populates="post")
```

**帖子发布接口**:

```python
@router.post("", response_model=PostResponse, summary="发布帖子")
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发布新帖子（需要审核后才能显示）"""
    new_post = Post(
        content=post_data.content,
        images=post_data.images,
        is_anonymous=post_data.is_anonymous,
        user_id=current_user.id,
        status="pending"  # 新帖子默认待审核状态
    )
    
    db.add(new_post)
    db.flush()
    
    # Add tags
    if post_data.tag_ids:
        for tag_id in post_data.tag_ids:
            tag = PostTag(post_id=new_post.id, tag_name=f"tag_{tag_id}")
            db.add(tag)
    
    db.commit()
    db.refresh(new_post)
    
    return new_post
```

#### 3.2 评论系统（点赞/拉踩机制）

评论支持点赞和拉踩功能，拉踩数达到阈值自动删除：

**删除条件**: `拉踩数 > 点赞数 * 2 + 5`

```python
# 评论删除条件：拉踩数 > 点赞数 * 2 + 5
DISLIKE_DELETE_THRESHOLD_MULTIPLIER = 2
DISLIKE_DELETE_THRESHOLD_BASE = 5

def check_and_delete_comment_by_dislikes(comment: PostComment, db: Session):
    """检查是否满足拉踩删除条件"""
    threshold = comment.likes_count * DISLIKE_DELETE_THRESHOLD_MULTIPLIER + DISLIKE_DELETE_THRESHOLD_BASE
    if comment.dislikes_count > threshold:
        comment.status = "deleted"
        comment.delete_reason = f"社区投票删除（拉踩数{comment.dislikes_count}超过阈值{threshold}）"
        
        # 创建通知
        notification = Notification(
            user_id=comment.user_id,
            type="comment_deleted",
            title="您的评论已被删除",
            content=f"您的评论因社区投票被删除。惩罚：信誉分-2。"
        )
        db.add(notification)
        
        # 扣除信誉分
        profile = db.query(UserProfile).filter(UserProfile.user_id == comment.user_id).first()
        if profile:
            profile.credit_score = max(0, profile.credit_score - 2)
        
        db.commit()
        return True
    return False
```

#### 3.3 审核员投票删除

3个审核员投票可删除违规评论：

```python
REVIEWER_DELETE_VOTES_REQUIRED = 3

@router.post("/{post_id}/comments/{comment_id}/reviewer-delete", summary="审核员投票删除评论")
async def reviewer_delete_comment(
    post_id: int,
    comment_id: int,
    reason: str = Query(..., description="删除原因"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """审核员投票删除评论（3票删除）"""
    if not is_user_reviewer(current_user, db):
        raise HTTPException(status_code=403, detail="需要审核员权限（信誉分>98）")
    
    comment = db.query(PostComment).filter(
        PostComment.id == comment_id,
        PostComment.status == "active"
    ).first()
    
    # 添加投票
    vote = CommentReviewerDelete(
        comment_id=comment_id,
        reviewer_id=current_user.id,
        reason=reason
    )
    db.add(vote)
    comment.reviewer_delete_count += 1
    db.commit()
    
    # 检查是否满足删除条件
    if comment.reviewer_delete_count >= REVIEWER_DELETE_VOTES_REQUIRED:
        comment.status = "deleted"
        # 扣除信誉分-5
        profile = db.query(UserProfile).filter(UserProfile.user_id == comment.user_id).first()
        if profile:
            profile.credit_score = max(0, profile.credit_score - 5)
        db.commit()
```

---

### 4. 互助任务系统

#### 4.1 任务发布与悬赏

发布任务时自动冻结悬赏金额：

**后端实现 - 任务发布功能** (`backend/app/api/tasks.py`):

```python
@router.post("", response_model=TaskResponse, summary="发布任务")
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发布新任务"""
    # Check wallet balance
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    reward_amount = Decimal(str(task_data.reward))
    if not wallet or wallet.balance < reward_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="余额不足，请先充值"
        )
    
    # Freeze the reward amount
    wallet.balance -= reward_amount
    wallet.frozen_amount += reward_amount
    
    new_task = HelpTask(
        title=task_data.title,
        description=task_data.description,
        category=task_data.category.value,
        reward=task_data.reward,
        location=task_data.location,
        deadline=task_data.deadline,
        publisher_id=current_user.id,
        status="open",
        private_info=task_data.private_info  # 私密信息
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    return new_task
```

#### 4.2 任务申请与优先分排序

申请者按优先分排序，优先分 = (信誉分 + 好评率*100) / 2：

**后端实现 - 任务申请者排序** (`backend/app/api/tasks.py`):

```python
@router.get("/{task_id}/applications", response_model=list[ApplicationResponse], summary="获取申请列表")
async def get_applications(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务申请列表，按优先分排序"""
    task = db.query(HelpTask).filter(HelpTask.id == task_id).first()
    if not task or task.publisher_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有任务发布者可以查看申请")
        
    applications = db.query(TaskApplication).options(
        joinedload(TaskApplication.applicant)
    ).filter(TaskApplication.task_id == task_id).all()
    
    def get_priority_score(application):
        profile = db.query(UserProfile).filter(
            UserProfile.user_id == application.applicant_id
        ).first()
        
        if not profile:
            return 80  # 默认值
        
        credit_score = profile.credit_score or 60
        approval_rate = 1.0
        if profile.total_reviews and profile.total_reviews > 0:
            approval_rate = (profile.positive_reviews or 0) / profile.total_reviews
        
        # 优先分 = (信誉分 + 好评率 * 100) // 2
        return (credit_score + int(approval_rate * 100)) // 2
    
    # 按优先分降序排序
    applications_sorted = sorted(applications, key=get_priority_score, reverse=True)
    
    # 为每个申请补充优先分（便于前端直接展示）
    for app in applications_sorted:
        app.priority_score = get_priority_score(app)
    
    return applications_sorted
```

#### 4.3 任务完成与奖励发放

当任务发布者确认任务完成后，系统会自动解冻悬赏金额，并结算至接单者的钱包余额中：

**后端实现 - 任务完成并转账** (`backend/app/api/tasks.py`):

```python
@router.post("/{task_id}/complete", response_model=SuccessResponse, summary="完成任务")
async def complete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """确认任务完成（发布者操作）"""
    task = db.query(HelpTask).filter(HelpTask.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.publisher_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有任务发布者可以确认完成")
    
    if task.status not in ["assigned", "in_progress"]:
        raise HTTPException(status_code=400, detail="任务状态不正确")
    
    # Transfer reward
    publisher_wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    assignee_wallet = db.query(Wallet).filter(Wallet.user_id == task.assignee_id).first()
    reward_amount = Decimal(str(task.reward))
    
    if publisher_wallet:
        publisher_wallet.frozen_amount -= reward_amount
    
    if assignee_wallet:
        assignee_wallet.balance += reward_amount
        assignee_wallet.total_income = (assignee_wallet.total_income or Decimal('0')) + reward_amount
        
        # Create transaction record
        transaction = Transaction(
            wallet_id=assignee_wallet.id,
            user_id=task.assignee_id,
            type=TransactionType.task_reward,
            amount=task.reward,
            balance_after=assignee_wallet.balance,
            related_task_id=task.id,
            description=f"任务奖励：{task.title}",
            status="completed"
        )
        db.add(transaction)
    
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    
    db.commit()
    
    return SuccessResponse(message="任务完成，奖励已发放")
```

---

### 5. 即时通讯系统

#### 5.1 WebSocket连接管理

```python
class ConnectionManager:
    def __init__(self):
        # 存储每个用户的WebSocket连接：{user_id: {websocket1, websocket2, ...}}
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """接受WebSocket连接"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        """断开WebSocket连接"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        """发送消息给指定用户的所有连接（支持多端同步）"""
        if user_id not in self.active_connections:
            return

        disconnected = set()
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.add(websocket)

        for websocket in disconnected:
            self.disconnect(websocket, user_id)
    
    def is_user_online(self, user_id: int) -> bool:
        """检查用户是否在线"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

# 全局连接管理器实例
manager = ConnectionManager()
```

#### 5.2 消息发送与推送

```python
@router.post("", response_model=MessageResponse, summary="发送消息")
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发送消息"""
    # ... 省略：自发消息校验、接收者存在性校验、拉黑校验 ...
    receiver = db.query(User).filter(User.id == message_data.receiver_id).first()
    msg_type = message_data.type.value if hasattr(message_data.type, 'value') else message_data.type

    message = Message(
        sender_id=current_user.id,
        receiver_id=message_data.receiver_id,
        content=message_data.content,
        message_type=msg_type,
        is_read=False
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    ws_message = {
        "type": "new_message",
        "data": {
            "id": message.id,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "content": message.content,
            "message_type": message.message_type,
            "is_read": message.is_read,
            "created_at": message.created_at.isoformat(),
            "sender": {"id": current_user.id, "name": current_user.name, "avatar": current_user.avatar},
            "receiver": {"id": receiver.id, "name": receiver.name, "avatar": receiver.avatar}
        }
    }

    # 推送给接收者与发送者（发送者多端同步，会话列表可实时更新）
    await manager.send_personal_message(ws_message, message_data.receiver_id)
    await manager.send_personal_message(ws_message, current_user.id)

    return message
```

#### 5.3 在线状态检测（在线好友）

在线好友列表接口位于好友模块 [friends.py](file:///Users/jj/Documents/MyCode/SmartCampusServicePlatform/backend/app/api/friends.py)（`/friends/online`），内部同时参考 WebSocket 连接池与数据库的 `online_status/last_active`：

```python
@router.get("/online", summary="获取在线好友ID列表")
async def get_online_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[int]:
    """获取当前用户的好友中哪些在线"""
    friendships = db.query(Friendship).filter(Friendship.user_id == current_user.id).all()
    friend_ids = [f.friend_id for f in friendships]
    
    if not friend_ids:
        return []
    
    # 在线判断：WebSocket连接 或 (数据库状态为online 且 最后活跃时间在5分钟内)
    online_threshold = datetime.utcnow() - timedelta(minutes=5)
    
    # 从数据库查询活跃用户
    db_online_users = db.query(User.id).filter(
        User.id.in_(friend_ids),
        User.online_status == 'online',
        User.last_active >= online_threshold
    ).all()
    db_online_ids = {u.id for u in db_online_users}
    
    # 结合WebSocket状态
    ws_online_ids = {fid for fid in friend_ids if manager.is_user_online(fid)}
    
    # 合并两种在线状态
    return list(db_online_ids | ws_online_ids)
```

---

### 6. 钱包系统

#### 6.1 钱包模型

```python
class Wallet(Base):
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    balance = Column(DECIMAL(12, 2), default=0, comment="可用余额")
    frozen_amount = Column(DECIMAL(12, 2), default=0, comment="冻结金额")
    total_income = Column(DECIMAL(12, 2), default=0, comment="总收入")
    total_expense = Column(DECIMAL(12, 2), default=0, comment="总支出")

class TransactionType(str, enum.Enum):
    recharge = "recharge"           # 充值
    withdraw = "withdraw"           # 提现
    transfer_in = "transfer_in"     # 转入
    transfer_out = "transfer_out"   # 转出
    task_reward = "task_reward"     # 任务奖励
    task_payment = "task_payment"   # 任务支付
    refund = "refund"               # 退款
```

#### 6.2 转账功能

```python
@router.post("/transfer", summary="转账")
async def transfer(
    transfer_data: TransferCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """向其他用户转账"""
    if transfer_data.to_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能给自己转账")
    
    # Check sender balance
    sender_wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not sender_wallet or sender_wallet.balance < transfer_data.amount:
        raise HTTPException(status_code=400, detail="余额不足")
    
    # Get or create recipient wallet
    recipient_wallet = db.query(Wallet).filter(Wallet.user_id == transfer_data.to_user_id).first()
    if not recipient_wallet:
        recipient_wallet = Wallet(user_id=transfer_data.to_user_id, balance=0.0)
        db.add(recipient_wallet)
    
    # Transfer
    sender_wallet.balance -= transfer_data.amount
    recipient_wallet.balance += transfer_data.amount
    
    # Create transaction records
    sender_transaction = Transaction(
        wallet_id=sender_wallet.id,
        amount=transfer_data.amount,
        type="transfer_out",
        status="completed",
        description=f"转账给{recipient.name}"
    )
    
    recipient_transaction = Transaction(
        wallet_id=recipient_wallet.id,
        amount=transfer_data.amount,
        type="transfer_in",
        status="completed",
        description=f"来自{current_user.name}的转账"
    )
    
    db.add_all([sender_transaction, recipient_transaction])
    db.commit()
    
    return SuccessResponse(message="转账成功")
```

---

### 7. 好友系统

#### 7.1 好友请求与自动互加

```python
@router.post("/requests", summary="发送好友请求")
async def send_friend_request(
    request_data: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发送好友请求"""
    # Check if in blacklist
    in_blacklist = db.query(Blacklist).filter(
        Blacklist.user_id == request_data.to_user_id,
        Blacklist.blocked_user_id == current_user.id
    ).first()
    
    if in_blacklist:
        raise HTTPException(status_code=400, detail="对方已将你拉黑")
    
    # Check if target user sent request to us (自动互加)
    reverse_request = db.query(FriendRequest).filter(
        FriendRequest.from_user_id == request_data.to_user_id,
        FriendRequest.to_user_id == current_user.id,
        FriendRequest.status == "pending"
    ).first()
    
    if reverse_request:
        # Auto accept - 双向添加好友
        reverse_request.status = "accepted"
        db.add(Friendship(user_id=current_user.id, friend_id=request_data.to_user_id))
        db.add(Friendship(user_id=request_data.to_user_id, friend_id=current_user.id))
        db.commit()
        return reverse_request
    
    # Create new request
    friend_request = FriendRequest(
        from_user_id=current_user.id,
        to_user_id=request_data.to_user_id,
        message=request_data.message,
        status="pending"
    )
    
    db.add(friend_request)
    db.commit()
    return friend_request
```

#### 7.2 黑名单管理

```python
@router.post("/blacklist", summary="添加黑名单")
async def add_to_blacklist(
    blacklist_data: BlacklistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """将用户加入黑名单"""
    # Remove friendship if exists
    db.query(Friendship).filter(
        or_(
            and_(Friendship.user_id == current_user.id, 
                 Friendship.friend_id == blacklist_data.blocked_user_id),
            and_(Friendship.user_id == blacklist_data.blocked_user_id, 
                 Friendship.friend_id == current_user.id)
        )
    ).delete()
    
    # Add to blacklist
    blacklist = Blacklist(
        user_id=current_user.id,
        blocked_user_id=blacklist_data.blocked_user_id,
        reason=blacklist_data.reason
    )
    
    db.add(blacklist)
    db.commit()
    return blacklist
```

---

### 8. 文件管理系统

#### 8.1 文件上传

```python
@router.post("/upload", summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    message_id: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传文件到服务器
    - 自动去重(相同文件只存储一次)
    - 引用计数与延迟清理（引用归零进入软删除队列，定时任务清理物理文件）
    """
    try:
        file_data = await file.read()
        mime_type = file.content_type or "application/octet-stream"
        
        metadata = await file_manager.save_file(
            file_data=file_data,
            message_id=message_id,
            mime_type=mime_type,
            db=db
        )
        
        return {
            "file_id": metadata.id,
            "file_hash": metadata.file_hash,
            "file_size": metadata.file_size,
            "mime_type": metadata.mime_type,
            "reference_count": metadata.reference_count
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
```

**后端实现 - Hash 去重与引用计数** (`backend/app/utils/file_manager.py`):

```python
class FileStorageManager:
    def _calculate_hash(self, file_data: bytes) -> str:
        return hashlib.sha256(file_data).hexdigest()

    def _get_storage_path(self, file_hash: str) -> Path:
        # 使用哈希前4位分层: ab/cd/abcdef...
        return self.base_path / file_hash[:2] / file_hash[2:4] / file_hash

    async def save_file(self, file_data: bytes, message_id: int, mime_type: str, db: Session) -> FileMetadata:
        file_hash = self._calculate_hash(file_data)

        existing = db.query(FileMetadata).filter(FileMetadata.file_hash == file_hash).first()
        if existing:
            existing.reference_count += 1
            existing.last_accessed = datetime.utcnow()
            db.add(FileReference(file_id=existing.id, message_id=message_id))
            db.commit()
            db.refresh(existing)
            return existing
        # ... 新文件写盘并创建 FileMetadata/FileReference ...
```

---

### 9. 公告系统

#### 9.1 公告发布与展示

平台支持管理员发布公告（通知、活动、警告等类型），支持置顶功能。公告对所有用户（包括未登录用户）可见，用户登录后可以记录阅读状态：

**后端实现 - 公告列表获取** (`backend/app/api/announcements.py`):

```python
@router.get("/public", response_model=AnnouncementListResponse, summary="获取公开公告列表")
async def get_public_announcements(
    type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取公开公告列表（无需登录）"""
    query = db.query(Announcement).filter(Announcement.status == "published")
    
    if type:
        query = query.filter(Announcement.type == type)
    
    total = query.count()
    total_pages = ceil(total / page_size)
    
    # Order by is_pinned first, then by publish_date
    announcements = query.order_by(
        desc(Announcement.is_pinned),
        desc(Announcement.publish_date)
    ).offset((page - 1) * page_size).limit(page_size).all()
    
    return AnnouncementListResponse(
        items=announcements,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
```

#### 9.2 阅读状态追踪

系统记录用户的公告阅读状态，确保重要通知能够被有效传达：

**后端实现 - 阅读记录模型** (`backend/app/models/models.py`):

```python
class AnnouncementRead(Base):
    __tablename__ = "announcement_reads"
    id = Column(Integer, primary_key=True, index=True)
    announcement_id = Column(Integer, ForeignKey("announcements.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    read_at = Column(DateTime, server_default=func.now())
```

**后端实现 - 标记公告已读** (`backend/app/api/announcements.py`):

```python
@router.post("/{announcement_id}/read", response_model=SuccessResponse, summary="标记为已读")
async def mark_as_read(
    announcement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """标记公告为已读"""
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id
    ).first()
    
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在"
        )
    
    existing_read = db.query(AnnouncementRead).filter(
        AnnouncementRead.announcement_id == announcement_id,
        AnnouncementRead.user_id == current_user.id
    ).first()
    
    if not existing_read:
        read_record = AnnouncementRead(
            announcement_id=announcement_id,
            user_id=current_user.id
        )
        db.add(read_record)
        db.commit()
    
    return SuccessResponse(message="已标记为已读")
```

---

### 10. 前端API服务层

**统一的API请求封装** (`lib/api.ts`):

```typescript
// Token管理
export const getToken = (): string | null => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('access_token');
  }
  return null;
};

export const setToken = (token: string): void => {
  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', token);
  }
};

// 通用请求方法
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '请求失败' }));
    throw new Error(error.detail || '请求失败');
  }
  
  return response.json();
}

// ============ API模块示例 ============

export const authApi = {
  login: async (data: LoginRequest): Promise<TokenResponse> => {...},
  register: async (data: RegisterRequest): Promise<User> => {...},
  getCurrentUser: async (): Promise<User> => {...},
  changePassword: async (oldPassword: string, newPassword: string): Promise<void> => {...},
  forgotPassword: async (email: string): Promise<void> => {...},
  resetPassword: async (token: string, newPassword: string): Promise<void> => {...},
  githubCallback: async (code: string): Promise<TokenResponse> => {...},
};

export const postsApi = {
  getPosts: async (page, pageSize, keyword): Promise<PostListResponse> => {...},
  createPost: async (data: CreatePostRequest): Promise<Post> => {...},
  likePost: async (postId: number): Promise<void> => {...},
  // 审核相关
  checkReviewerStatus: async (): Promise<ReviewerStatus> => {...},
  approvePost: async (postId: number): Promise<void> => {...},
  rejectPost: async (postId: number, reason?: string): Promise<void> => {...},
};

export const tasksApi = {
  getTasks: async (page, pageSize, category?, status?): Promise<TaskListResponse> => {...},
  createTask: async (data: CreateTaskRequest): Promise<Task> => {...},
  applyTask: async (taskId: number, message?: string): Promise<void> => {...},
  completeTask: async (taskId: number): Promise<void> => {...},
};

export const walletApi = {
  getWallet: async (): Promise<Wallet> => {...},
  getTransactions: async (page, pageSize, type?): Promise<TransactionListResponse> => {...},
  recharge: async (amount: number, paymentMethod: string): Promise<{ order_no: string }> => {...},
};

export const friendsApi = {
  getFriends: async (page, pageSize): Promise<FriendListResponse> => {...},
  getOnlineFriends: async (): Promise<number[]> => {...},
  sendFriendRequest: async (toUserId: number, message?: string): Promise<void> => {...},
};

export const messagesApi = {
  getConversations: async (): Promise<{ items: Conversation[]; total: number }> => {...},
  sendMessage: async (receiverId: number, content: string, type): Promise<Message> => {...},
};
```

---

## 快速开始

### 环境要求

- Node.js >= 18.x
- Python >= 3.9
- npm 或 yarn

### 1. 克隆项目

```bash
git clone <repository-url>
cd SmartCampusServicePlatform
```

### 2. 配置环境变量

```bash
# 前端（Next.js）
cp .env.local.example .env.local

# 后端（FastAPI）
cp backend/.env.example backend/.env
```

### 3. 安装依赖

```bash
# 前端
npm install

# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 4. 启动服务

```bash
# macOS
./scripts/MacOS/start.sh

# Windows（PowerShell/CMD）
./scripts/Windows/start.bat

# Linux（CentOS 7 示例）
./scripts/Linux/start-CentOS7.sh
```

或手动启动:

```bash
# 后端
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端
npm run dev
```

### 5. 访问应用

- **前端应用**: http://localhost:3000
- **API文档 (Swagger)**: http://localhost:8000/docs
- **API文档 (ReDoc)**: http://localhost:8000/redoc

---

## 配置说明

### 环境变量

**前端（Next.js）**

| 变量名 | 说明 | 默认值（见 config.ts） |
|--------|------|------------------------|
| `NEXT_PUBLIC_API_BASE_URL` | 后端 API 基础地址 | http://localhost:8000 |
| `NEXT_PUBLIC_APP_URL` | 前端应用地址 | http://localhost:3000 |
| `JWT_SECRET_KEY` | 前端配置中使用的 JWT 密钥名（仅用于前端配置展示；后端实际读取 `SECRET_KEY`） | <JWT_SECRET_KEY> |

**后端（FastAPI）**（见 [config.py](file:///Users/jj/Documents/MyCode/MyProject/SmartCampusServicePlatform/backend/app/config.py)）

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DB_HOST` | 数据库主机 | <DB_HOST> |
| `DB_PORT` | 数据库端口 | 3306 |
| `DB_USER` | 数据库用户名 | <DB_USER> |
| `DB_PASSWORD` | 数据库密码 | <DB_PASSWORD> |
| `DB_NAME` | 数据库名 | <DB_NAME> |
| `SECRET_KEY` | JWT 签名密钥 | <SECRET_KEY> |
| `ALGORITHM` | JWT 算法 | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 过期时间（分钟） | 1440 |
| `FRONTEND_URL` | 前端地址（用于密码重置邮件链接拼接） | http://localhost:3000 |
| `SMTP_HOST` `SMTP_PORT` `SMTP_USER` `SMTP_PASSWORD` `SMTP_FROM_EMAIL` | 邮件服务配置 | (空/默认) |
| `GITHUB_CLIENT_ID` `GITHUB_CLIENT_SECRET` `GITHUB_REDIRECT_URI` | GitHub OAuth 登录 | (空/默认) |

### 功能开关

在 `config.ts` 中可配置以下功能开关（其中 `enableRateLimit`、`enableAuditLog` 属于预留项，后端未提供完整实现时不应在生产环境依赖该开关）:

```typescript
features: {
  enableRegistration: true,        // 是否开放注册
  enableEmailVerification: false,  // 是否需要邮箱验证
  enableFileUpload: true,          // 是否允许文件上传
  enableReviewer: true,            // 是否启用审核员系统
  enableWallet: true,              // 是否启用钱包系统
  enableCache: false,              // 是否启用Redis缓存
  enableRateLimit: true,           // 是否启用接口限流
  enableAuditLog: true             // 是否启用审计日志
}
```

### 业务配置

```typescript
business: {
  user: {
    minPasswordLength: 6,
    maxPasswordLength: 32,
    defaultRole: 'student',
    roles: ['student', 'teacher', 'admin', 'reviewer']
  },
  // 注意：reviewer 在后端不是 UserRole 枚举值，而是“信誉分达标后获得的权限身份”
  post: {
    maxContentLength: 5000,
    maxImagesCount: 9,
    reviewThreshold: 3  // 审核员投票阈值
  },
  comment: {
    maxContentLength: 500,
    dislikeThreshold: 5,  // 拉踩自动删除阈值
    dislikeRatio: 2       // 点赞数的2倍
  },
  task: {
    maxReward: 1000,
    minReward: 1,
    categories: ['errand', 'purchase', 'study', 'other']
  },
  wallet: {
    initialBalance: 0,
    minBalance: 0,
    maxBalance: 999999,
    minTransferAmount: 1
  }
}
```

---

## 部署建议

### 生产环境检查清单

- [ ] 修改后端 `SECRET_KEY` 为安全的随机字符串（JWT签名密钥）
- [ ] 配置生产数据库 (PostgreSQL/MySQL)
- [ ] 启用 HTTPS
- [ ] 配置 CORS 白名单
- [ ] 启用 Redis 缓存
- [ ] 配置文件存储路径
- [ ] 设置合适的日志级别
- [ ] 配置反向代理 (Nginx)

---

## License

MIT License

---

**Smart Campus Service Platform** - Building Digital Campus Together
