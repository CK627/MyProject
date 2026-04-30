"""
智慧校园服务平台 - 统一配置文件
所有前后端配置参数都在这个文件中集中管理

使用方法:
1. 复制本文件内容,根据需要修改配置项
2. 前端配置在 FRONTEND_CONFIG 部分
3. 后端配置在 BACKEND_CONFIG 部分
4. 敏感信息(密码、密钥)请使用环境变量
"""

# ============================================================
# 前端配置 (TypeScript/JavaScript)
# ============================================================

FRONTEND_CONFIG = {
    # ========== API配置 ==========
    "apiBaseUrl": "http://localhost:8000",  # 后端API地址
    "appUrl": "http://localhost:3000",      # 前端应用地址
    
    # ========== 存储配置 ==========
    "tokenStorageKey": "smart_campus_token",
    "userStorageKey": "smart_campus_user",
    "userExpireKey": "smart_campus_user_expire",
    "pageStorageKey": "smart_campus_current_page",
    "sessionExpireTime": 86400000,  # 1天 (毫秒)
    
    # ========== IndexedDB配置 ==========
    "indexedDB": {
        "dbName": "SmartCampusDB",
        "version": 1,
        "stores": {
            "messages": "messages",
            "conversations": "conversations",
            "files": "files",
            "metadata": "metadata"
        }
    },
    
    # ========== 文件缓存配置 ==========
    "fileCache": {
        "maxAge": 30,              # 文件过期天数
        "softDeleteDelay": 24,     # 软删除延迟小时数
        "cleanupInterval": 3600000 # 清理任务间隔(毫秒) 1小时
    }
}


# ============================================================
# 后端配置 (Python)
# ============================================================

BACKEND_CONFIG = {
    # ========== 应用配置 ==========
    "APP_NAME": "智慧校园服务平台",
    "APP_VERSION": "1.0.0",
    "DEBUG": False,
    
    # ========== 服务器配置 ==========
    "HOST": "0.0.0.0",
    "PORT": 8000,
    "WORKERS": 4,
    
    # ========== 数据库配置 ==========
    # SQLite配置 (开发环境推荐)
    "DATABASE_URL": "sqlite:///./smart_campus.db",
    
    # PostgreSQL配置 (生产环境推荐)
    # "DB_HOST": "localhost",
    # "DB_PORT": 5432,
    # "DB_USERNAME": "postgres",
    # "DB_PASSWORD": "your_password",
    # "DB_NAME": "smart_campus",
    
    "DB_ECHO": False,  # 是否打印SQL语句
    
    # ========== JWT配置 ==========
    "JWT_SECRET_KEY": "<JWT_SECRET_KEY>",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRE_MINUTES": 10080,  # 7天
    
    # ========== 文件存储配置 ==========
    "STORAGE_PATH": "./storage/files",
    "MAX_FILE_SIZE": 52428800,  # 50MB
    "ALLOWED_FILE_TYPES": [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain"
    ],
    "FILE_SOFT_DELETE_HOURS": 24,
    "FILE_CLEANUP_INTERVAL": 3600,
    
    # ========== CORS配置 ==========
    "CORS_ORIGINS": ["http://localhost:3000", "http://localhost:3001"],
    "CORS_ALLOW_CREDENTIALS": True,
    "CORS_ALLOW_METHODS": ["*"],
    "CORS_ALLOW_HEADERS": ["*"],
    
    # ========== Redis配置 (可选) ==========
    "REDIS_HOST": "localhost",
    "REDIS_PORT": 6379,
    "REDIS_PASSWORD": "",
    "REDIS_DB": 0,
    
    # ========== 邮件配置 (可选) ==========
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": 587,
    "SMTP_USER": "",
    "SMTP_PASSWORD": "",
    "EMAIL_FROM": "noreply@smartcampus.com",
    
    # ========== 业务配置 ==========
    # 用户配置
    "MIN_PASSWORD_LENGTH": 6,
    "MAX_PASSWORD_LENGTH": 32,
    "DEFAULT_USER_ROLE": "student",
    
    # 帖子配置
    "MAX_POST_CONTENT_LENGTH": 5000,
    "MAX_POST_IMAGES": 9,
    "MAX_POST_TAGS": 5,
    "REVIEW_THRESHOLD": 3,
    
    # 评论配置
    "MAX_COMMENT_LENGTH": 500,
    "COMMENT_DISLIKE_THRESHOLD": 5,
    "COMMENT_DISLIKE_RATIO": 2,
    
    # 任务配置
    "MAX_TASK_REWARD": 1000,
    "MIN_TASK_REWARD": 1,
    
    # 钱包配置
    "INITIAL_BALANCE": 0,
    "MIN_BALANCE": 0,
    "MAX_BALANCE": 999999,
    "MIN_TRANSFER_AMOUNT": 1,
    
    # 好友配置
    "MAX_FRIENDS_COUNT": 500,
    
    # 消息配置
    "MAX_MESSAGE_LENGTH": 2000,
    "MAX_CONVERSATIONS": 100,
    
    # ========== 功能开关 ==========
    "ENABLE_REGISTRATION": True,
    "ENABLE_EMAIL_VERIFICATION": False,
    "ENABLE_FILE_UPLOAD": True,
    "ENABLE_REVIEWER": True,
    "ENABLE_WALLET": True,
    "ENABLE_CACHE": False,
    "ENABLE_RATE_LIMIT": True,
    "ENABLE_AUDIT_LOG": True,
}


# ============================================================
# 配置使用说明
# ============================================================

"""
前端使用方法 (TypeScript):
------------------------
// 将 FRONTEND_CONFIG 复制到 config.ts 文件中
export const config = {
  frontend: {
    apiBaseUrl: "http://localhost:8000",
    appUrl: "http://localhost:3000",
    // ... 其他配置
  }
}

// 在代码中使用
import config from '@/config'
const apiUrl = config.frontend.apiBaseUrl


后端使用方法 (Python):
---------------------
# 方法1: 直接使用字典
from config_all import BACKEND_CONFIG
database_url = BACKEND_CONFIG["DATABASE_URL"]

# 方法2: 使用pydantic-settings (推荐)
# 创建 backend/app/config.py 并从 BACKEND_CONFIG 读取默认值


环境变量覆盖:
-----------
所有配置都可以通过环境变量覆盖,优先级为:
环境变量 > .env文件 > 配置文件默认值

例如:
export JWT_SECRET_KEY="production-secret-key"
export DATABASE_URL="postgresql://user:pass@localhost/db"


生产环境部署检查清单:
-------------------
✅ 1. JWT_SECRET_KEY - 使用强随机密钥
✅ 2. DATABASE_URL - 使用生产数据库
✅ 3. CORS_ORIGINS - 限制允许的源
✅ 4. DEBUG - 设为 False
✅ 5. 数据库密码 - 使用强密码
✅ 6. STORAGE_PATH - 确保路径可写
✅ 7. 邮件配置 - 配置真实SMTP服务


常见配置修改:
-----------
1. 修改API地址: apiBaseUrl
2. 切换数据库: DATABASE_URL
3. 修改文件存储路径: STORAGE_PATH
4. 修改JWT过期时间: JWT_EXPIRE_MINUTES
5. 修改CORS允许源: CORS_ORIGINS
6. 开关功能: ENABLE_* 系列配置
"""
