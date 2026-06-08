import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..utils.file_manager import file_manager


class FileCleanupScheduler:
    """文件清理调度器 - 定期执行异步删除任务"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        
    async def cleanup_task(self):
        """清理任务 - 删除过期文件"""
        db: Session = SessionLocal()
        try:
            deleted_count = await file_manager.cleanup_expired_files(db)
            if deleted_count > 0:
                print(f"[{datetime.utcnow()}] 清理了 {deleted_count} 个过期文件")
        except Exception as e:
            print(f"文件清理任务失败: {e}")
        finally:
            db.close()
    
    def start(self):
        """启动调度器 - 每小时执行一次清理"""
        self.scheduler.add_job(
            self.cleanup_task,
            trigger=IntervalTrigger(hours=1),
            id='file_cleanup',
            name='清理过期文件',
            replace_existing=True
        )
        self.scheduler.start()
        print("文件清理调度器已启动")
    
    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()


# 全局调度器实例
cleanup_scheduler = FileCleanupScheduler()
