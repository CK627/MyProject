/**
 * 智慧校园服务平台 - 统一配置文件
 * 所有需要配置的参数都在这里集中管理
 */

export const config = {
  // ========== 前端配置 ==========
  frontend: {
    // API基础地址
    apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
    
    // 前端服务器地址
    appUrl: process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000',
    
    // Token存储key
    tokenStorageKey: 'smart_campus_token',
    
    // 用户信息存储key
    userStorageKey: 'smart_campus_user',
    userExpireKey: 'smart_campus_user_expire',
    
    // 页面状态存储key
    pageStorageKey: 'smart_campus_current_page',
    
    // 会话过期时间(毫秒)
    sessionExpireTime: 24 * 60 * 60 * 1000, // 1天
    
    // IndexedDB配置
    indexedDB: {
      dbName: 'SmartCampusDB',
      version: 1,
      stores: {
        messages: 'messages',
        conversations: 'conversations',
        files: 'files',
        metadata: 'metadata'
      }
    },
    
    // 文件缓存配置
    fileCache: {
      maxAge: 30, // 文件过期天数
      softDeleteDelay: 24, // 软删除延迟小时数
      cleanupInterval: 3600000 // 清理任务间隔(毫秒) 1小时
    }
  },

  // ========== 后端配置 ==========
  backend: {
    // 服务器配置
    server: {
      host: '0.0.0.0',
      port: 8000,
      workers: 4
    },
    
    // 数据库配置
    database: {
      type: 'postgresql',
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT || '5432'),
      username: process.env.DB_USERNAME || 'postgres',
      password: process.env.DB_PASSWORD || 'password',
      database: process.env.DB_NAME || 'smart_campus',
      
      // SQLite配置(如使用SQLite)
      sqliteUrl: process.env.DATABASE_URL || 'sqlite:///./smart_campus.db'
    },
    
    // JWT配置
    jwt: {
      secretKey: process.env.JWT_SECRET_KEY || 'your-secret-key-change-in-production',
      algorithm: 'HS256',
      expireMinutes: 60 * 24 * 7 // 7天
    },
    
    // 文件存储配置
    storage: {
      basePath: process.env.STORAGE_PATH || './storage/files',
      maxFileSize: 50 * 1024 * 1024, // 50MB
      allowedTypes: [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain'
      ],
      
      // 文件清理配置
      cleanup: {
        softDeleteHours: 24, // 软删除后24小时物理删除
        schedulerInterval: 3600 // 每小时检查一次(秒)
      }
    },
    
    // Redis配置(如使用缓存)
    redis: {
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379'),
      password: process.env.REDIS_PASSWORD || '',
      db: parseInt(process.env.REDIS_DB || '0')
    },
    
    // CORS配置
    cors: {
      allowOrigins: process.env.CORS_ORIGINS?.split(',') || ['http://localhost:3000', 'http://localhost:3001'],
      allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
      allowHeaders: ['Content-Type', 'Authorization']
    },
    
    // 邮件配置(如需要)
    email: {
      smtpHost: process.env.SMTP_HOST || 'smtp.gmail.com',
      smtpPort: parseInt(process.env.SMTP_PORT || '587'),
      smtpUser: process.env.SMTP_USER || '',
      smtpPassword: process.env.SMTP_PASSWORD || '',
      fromAddress: process.env.EMAIL_FROM || 'noreply@smartcampus.com'
    }
  },

  // ========== 业务配置 ==========
  business: {
    // 用户配置
    user: {
      minPasswordLength: 6,
      maxPasswordLength: 32,
      defaultRole: 'student',
      roles: ['student', 'teacher', 'admin', 'reviewer']
    },
    
    // 帖子配置
    post: {
      maxContentLength: 5000,
      maxImagesCount: 9,
      maxTagsCount: 5,
      reviewThreshold: 3 // 审核员投票阈值
    },
    
    // 评论配置
    comment: {
      maxContentLength: 500,
      dislikeThreshold: 5, // 拉踩自动删除阈值
      dislikeRatio: 2 // 点赞数的2倍
    },
    
    // 任务配置
    task: {
      maxReward: 1000,
      minReward: 1,
      categories: ['errand', 'purchase', 'study', 'other']
    },
    
    // 钱包配置
    wallet: {
      initialBalance: 0,
      minBalance: 0,
      maxBalance: 999999,
      minTransferAmount: 1
    },
    
    // 好友配置
    friend: {
      maxFriendsCount: 500,
      requestExpireDays: 30
    },
    
    // 消息配置
    message: {
      maxContentLength: 2000,
      maxConversations: 100,
      types: ['text', 'image', 'file']
    }
  },

  // ========== 功能开关 ==========
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
}

export default config
