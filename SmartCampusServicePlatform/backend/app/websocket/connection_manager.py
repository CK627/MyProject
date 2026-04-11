"""
WebSocket连接管理器
管理所有WebSocket连接，支持用户级别的消息推送
"""
from typing import Dict, Set
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


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
        logger.info(f"用户 {user_id} 已连接WebSocket，当前连接数: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """断开WebSocket连接"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # 如果用户没有任何连接了，删除该用户记录
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            logger.info(f"用户 {user_id} 断开WebSocket连接")
    
    async def send_personal_message(self, message: dict, user_id: int):
        """发送消息给指定用户的所有连接"""
        if user_id not in self.active_connections:
            logger.debug(f"用户 {user_id} 当前未连接WebSocket")
            return
        
        # 移除已断开的连接
        disconnected = set()
        
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"发送消息到用户 {user_id} 失败: {e}")
                disconnected.add(websocket)
        
        # 清理断开的连接
        for websocket in disconnected:
            self.disconnect(websocket, user_id)
    
    async def broadcast_to_users(self, message: dict, user_ids: list[int]):
        """广播消息给多个用户"""
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)
    
    def get_online_users(self) -> list[int]:
        """获取所有在线用户ID"""
        return list(self.active_connections.keys())
    
    def is_user_online(self, user_id: int) -> bool:
        """检查用户是否在线"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0


# 全局连接管理器实例
manager = ConnectionManager()
