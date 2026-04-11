from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from .database import engine
from .models.models import Base
from .models.file_storage import FileMetadata, FileReference, DeletedFile
from .tasks.file_cleanup import cleanup_scheduler
from .tasks.user_activity_checker import activity_scheduler
from .api import (
    auth_router, users_router, posts_router, tasks_router,
    wallet_router, announcements_router, friends_router,
    messages_router, admin_router, school_router, files_router,
    activity_router
)
from .websocket import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup: create tables if not exist
    Base.metadata.create_all(bind=engine)
    
    # 启动文件清理调度器
    cleanup_scheduler.start()
    
    # 启动用户活跃状态检查调度器
    activity_scheduler.start()
    
    yield
    
    # Shutdown
    cleanup_scheduler.shutdown()
    activity_scheduler.shutdown()


# Create FastAPI app
app = FastAPI(
    title="智慧校园服务平台 API",
    description="""
    智慧校园服务平台后端API，提供以下功能：
    
    * **用户认证**: 登录、注册、密码修改
    * **用户管理**: 个人信息、用户档案
    * **校园墙**: 帖子发布、评论、点赞
    * **互帮互助**: 任务发布、申请、完成
    * **好友系统**: 好友请求、黑名单
    * **钱包系统**: 充值、转账、交易记录
    * **消息通知**: 私信、系统通知
    * **公告系统**: 校园公告、活动通知
    * **学校信息**: 院系、设施信息
    * **管理后台**: 内容审核、用户管理
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None  # 禁用默认ReDoc，使用自定义路由
)


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    """自定义ReDoc页面，使用备用CDN避免jsdelivr 404问题"""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="https://unpkg.com/redoc@latest/bundles/redoc.standalone.js",
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API prefix
API_PREFIX = "/api/v1"

# Register routers
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(posts_router, prefix=API_PREFIX)
app.include_router(tasks_router, prefix=API_PREFIX)
app.include_router(wallet_router, prefix=API_PREFIX)
app.include_router(announcements_router, prefix=API_PREFIX)
app.include_router(friends_router, prefix=API_PREFIX)
app.include_router(messages_router, prefix=API_PREFIX)
app.include_router(admin_router, prefix=API_PREFIX)
app.include_router(school_router, prefix=API_PREFIX)
app.include_router(files_router, prefix=API_PREFIX)
app.include_router(activity_router, prefix=API_PREFIX)
app.include_router(websocket_router, prefix=API_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    """API根路径"""
    return {
        "message": "欢迎使用智慧校园服务平台API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
