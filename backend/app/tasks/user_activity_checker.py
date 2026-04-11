"""
用户活跃状态检查定时任务
检查用户最后活跃时间，更新在线状态
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.models import User


def check_user_activity():
    """
    检查用户活跃状态
    - 超过1小时无活动：设为暂时离开(away)
    - 已设为离线(offline)的不修改
    """
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        
        # 查找在线但超过1小时未活跃的用户
        inactive_users = db.query(User).filter(
            User.online_status == 'online',
            User.last_active < one_hour_ago
        ).all()
        
        for user in inactive_users:
            user.online_status = 'away'
        
        db.commit()
        
        if inactive_users:
            print(f"[活跃状态检查] 更新 {len(inactive_users)} 个用户状态为暂时离开")
    except Exception as e:
        print(f"[活跃状态检查] 错误: {e}")
        db.rollback()
    finally:
        db.close()


# 创建调度器
activity_scheduler = BackgroundScheduler()

# 每10分钟检查一次用户活跃状态
activity_scheduler.add_job(
    check_user_activity,
    'interval',
    minutes=10,
    id='check_user_activity',
    replace_existing=True
)
