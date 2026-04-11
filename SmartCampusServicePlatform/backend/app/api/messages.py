from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc, func, case
from typing import Optional
from math import ceil

from ..database import get_db
from ..models.models import User, Message, Notification, Blacklist
from ..schemas.message import (
    MessageCreate, MessageResponse, MessageListResponse,
    ConversationResponse, ConversationListResponse,
    NotificationResponse, NotificationListResponse
)
from ..schemas.common import SuccessResponse
from ..core.deps import get_current_user
from ..websocket.connection_manager import manager

router = APIRouter(prefix="/messages", tags=["消息"])


@router.get("/conversations", response_model=ConversationListResponse, summary="获取会话列表")
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取会话列表"""
    try:
        # Get distinct conversation partners
        subquery = db.query(
            case(
                (Message.sender_id == current_user.id, Message.receiver_id),
                else_=Message.sender_id
            ).label('partner_id'),
            func.max(Message.id).label('last_message_id')
        ).filter(
            or_(
                Message.sender_id == current_user.id,
                Message.receiver_id == current_user.id
            )
        ).group_by('partner_id').subquery()
        
        # Get last messages with user info
        conversations = []
        partners = db.query(subquery.c.partner_id, subquery.c.last_message_id).all()
        
        for partner_id, last_message_id in partners:
            partner = db.query(User).filter(User.id == partner_id).first()
            last_message = db.query(Message).filter(Message.id == last_message_id).first()
            
            unread_count = db.query(Message).filter(
                Message.sender_id == partner_id,
                Message.receiver_id == current_user.id,
                Message.is_read == False
            ).count()
            
            if partner:
                conversations.append(ConversationResponse(
                    user=partner,
                    last_message=last_message,
                    unread_count=unread_count
                ))
        
        # Sort by last message time
        conversations.sort(key=lambda x: x.last_message.created_at if x.last_message else '', reverse=True)
        
        return ConversationListResponse(
            items=conversations,
            total=len(conversations)
        )
    except Exception as e:
        # 打印错误信息以便调试
        import traceback
        traceback.print_exc()
        print(f"获取会话列表失败: {str(e)}")
        # 如果出错,返回空列表
        return ConversationListResponse(
            items=[],
            total=0
        )


@router.get("/with/{user_id}", response_model=MessageListResponse, summary="获取与某用户的消息")
async def get_messages_with_user(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取与某用户的消息历史"""
    try:
        query = db.query(Message).filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
                and_(Message.sender_id == user_id, Message.receiver_id == current_user.id)
            )
        )
        
        total = query.count()
        total_pages = ceil(total / page_size)
        
        messages = query.options(
            joinedload(Message.sender),
            joinedload(Message.receiver)
        ).order_by(desc(Message.created_at)).offset((page - 1) * page_size).limit(page_size).all()
        
        # Mark as read
        db.query(Message).filter(
            Message.sender_id == user_id,
            Message.receiver_id == current_user.id,
            Message.is_read == False
        ).update({"is_read": True})
        db.commit()
        
        return MessageListResponse(
            items=list(reversed(messages)),
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        # 如果出错,返回空列表
        return MessageListResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0
        )


@router.post("", response_model=MessageResponse, summary="发送消息")
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发送消息"""
    try:
        if message_data.receiver_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能给自己发消息"
            )
        
        # Check if receiver exists
        receiver = db.query(User).filter(User.id == message_data.receiver_id).first()
        if not receiver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # Check if blocked
        blocked = db.query(Blacklist).filter(
            Blacklist.user_id == message_data.receiver_id,
            Blacklist.blocked_user_id == current_user.id
        ).first()
        
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="对方已将你拉黑，无法发送消息"
            )
        
        # 获取消息类型
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
        
        # 构造消息数据（包含双方用户信息，用于前端创建新会话）
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
                "sender": {
                    "id": current_user.id,
                    "name": current_user.name,
                    "avatar": current_user.avatar
                },
                "receiver": {
                    "id": receiver.id,
                    "name": receiver.name,
                    "avatar": receiver.avatar
                }
            }
        }
        
        # 通过WebSocket推送消息给接收者
        await manager.send_personal_message(ws_message, message_data.receiver_id)
        
        # 同时推送给发送者（支持多端同步，会话列表实时更新）
        await manager.send_personal_message(ws_message, current_user.id)
        
        return message
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送消息失败: {str(e)}"
        )


@router.post("/{message_id}/read", response_model=SuccessResponse, summary="标记消息已读")
async def mark_message_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """标记消息为已读"""
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.receiver_id == current_user.id
    ).first()
    
    if message:
        message.is_read = True
        db.commit()
    
    return SuccessResponse(message="已标记为已读")


@router.delete("/conversations/{user_id}", response_model=SuccessResponse, summary="删除会话")
async def delete_conversation(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除与某用户的会话（删除所有聊天记录）"""
    # 删除双方的所有消息记录
    deleted_count = db.query(Message).filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
            and_(Message.sender_id == user_id, Message.receiver_id == current_user.id)
        )
    ).delete()
    
    db.commit()
    
    return SuccessResponse(message=f"会话已删除，共删除 {deleted_count} 条消息")


@router.delete("/with/{user_id}/clear", response_model=SuccessResponse, summary="清除聊天记录")
async def clear_chat_history(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """清除与某用户的聊天记录"""
    # 删除双方的所有消息记录
    deleted_count = db.query(Message).filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
            and_(Message.sender_id == user_id, Message.receiver_id == current_user.id)
        )
    ).delete()
    
    db.commit()
    
    return SuccessResponse(message=f"聊天记录已清除，共删除 {deleted_count} 条消息")


# Notifications
@router.get("/notifications", response_model=NotificationListResponse, summary="获取通知列表")
async def get_notifications(
    type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取通知列表"""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if type:
        query = query.filter(Notification.type == type)
    
    total = query.count()
    unread_count = query.filter(Notification.is_read == False).count()
    
    notifications = query.order_by(desc(Notification.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return NotificationListResponse(
        items=notifications,
        total=total,
        unread_count=unread_count
    )


@router.post("/notifications/read-all", response_model=SuccessResponse, summary="全部标记已读")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """将所有通知标记为已读"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    
    return SuccessResponse(message="已全部标记为已读")
