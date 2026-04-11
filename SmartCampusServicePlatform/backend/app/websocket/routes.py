"""
WebSocket路由
处理WebSocket连接和消息推送
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import User

from .connection_manager import manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/{token}")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket连接端点
    客户端需要传递JWT token进行身份验证
    """
    try:
        # 验证token并获取用户
        from ..core.security import decode_token
        payload = decode_token(token)
        if not payload:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        user_id = int(payload.get("sub"))
        
        # 验证用户是否存在
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # 建立连接
        await manager.connect(websocket, user_id)
        
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": "WebSocket连接成功"
        })
        
        try:
            # 保持连接并处理客户端消息
            while True:
                # 接收客户端消息（用于心跳检测）
                data = await websocket.receive_text()
                
                # 处理ping消息
                if data == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": str(int(time.time()))
                    })
        
        except WebSocketDisconnect:
            manager.disconnect(websocket, user_id)
            logger.info(f"用户 {user_id} WebSocket连接已断开")
        
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass


import time
