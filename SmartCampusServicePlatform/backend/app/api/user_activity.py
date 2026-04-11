"""
用户活跃状态管理API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from ..models.models import User
from ..core.deps import get_current_user

router = APIRouter(prefix="/activity", tags=["用户活跃"])


@router.post("/heartbeat", summary="用户心跳")
async def heartbeat(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新用户最后活跃时间
    前端定期调用此接口表示用户在线
    """
    current_user.last_active = datetime.utcnow()
    current_user.online_status = 'online'
    db.commit()
    
    return {"status": "ok"}


@router.post("/logout", summary="用户退出登录")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """用户退出登录，更新在线状态为离线"""
    current_user.online_status = 'offline'
    db.commit()
    
    return {"status": "ok", "message": "已退出登录"}
