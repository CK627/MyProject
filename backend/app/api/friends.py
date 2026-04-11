from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from typing import Optional, List
from math import ceil
from datetime import datetime, timedelta

from ..database import get_db
from ..models.models import User, Friendship, FriendRequest, Blacklist
from ..schemas.friend import (
    FriendResponse, FriendListResponse, 
    FriendRequestCreate, FriendRequestResponse, FriendRequestListResponse,
    BlacklistCreate, BlacklistResponse, BlacklistListResponse
)
from ..schemas.common import SuccessResponse
from ..core.deps import get_current_user
from ..websocket.connection_manager import manager

router = APIRouter(prefix="/friends", tags=["好友"])


@router.get("/online", summary="获取在线好友ID列表")
async def get_online_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[int]:
    """获取当前用户的好友中哪些在线"""
    # 获取好友ID列表
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
    online_friends = list(db_online_ids | ws_online_ids)
    
    return online_friends


@router.get("", response_model=FriendListResponse, summary="获取好友列表")
async def get_friends(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取好友列表"""
    query = db.query(Friendship).filter(Friendship.user_id == current_user.id)
    
    total = query.count()
    total_pages = ceil(total / page_size)
    
    friendships = query.options(
        joinedload(Friendship.friend)
    ).offset((page - 1) * page_size).limit(page_size).all()
    
    return FriendListResponse(
        items=friendships,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.delete("/{friend_id}", response_model=SuccessResponse, summary="删除好友")
async def remove_friend(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除好友"""
    # Delete both directions
    db.query(Friendship).filter(
        or_(
            and_(Friendship.user_id == current_user.id, Friendship.friend_id == friend_id),
            and_(Friendship.user_id == friend_id, Friendship.friend_id == current_user.id)
        )
    ).delete()
    
    db.commit()
    
    return SuccessResponse(message="好友已删除")


# Friend Requests
@router.get("/requests/received", response_model=FriendRequestListResponse, summary="收到的好友请求")
async def get_received_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取收到的好友请求"""
    requests = db.query(FriendRequest).options(
        joinedload(FriendRequest.from_user)
    ).filter(
        FriendRequest.to_user_id == current_user.id,
        FriendRequest.status == "pending"
    ).all()
    
    return FriendRequestListResponse(
        items=requests,
        total=len(requests)
    )


@router.get("/requests/sent", response_model=FriendRequestListResponse, summary="发出的好友请求")
async def get_sent_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取发出的好友请求"""
    requests = db.query(FriendRequest).options(
        joinedload(FriendRequest.to_user)
    ).filter(
        FriendRequest.from_user_id == current_user.id,
        FriendRequest.status == "pending"
    ).all()
    
    return FriendRequestListResponse(
        items=requests,
        total=len(requests)
    )


@router.post("/requests", response_model=FriendRequestResponse, summary="发送好友请求")
async def send_friend_request(
    request_data: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发送好友请求"""
    if request_data.to_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能添加自己为好友"
        )
    
    # Check if user exists
    target_user = db.query(User).filter(User.id == request_data.to_user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # Check if already friends
    existing_friendship = db.query(Friendship).filter(
        Friendship.user_id == current_user.id,
        Friendship.friend_id == request_data.to_user_id
    ).first()
    
    if existing_friendship:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已经是好友了"
        )
    
    # Check if in blacklist
    in_blacklist = db.query(Blacklist).filter(
        Blacklist.user_id == request_data.to_user_id,
        Blacklist.blocked_user_id == current_user.id
    ).first()
    
    if in_blacklist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="对方已将你拉黑"
        )
    
    # Check existing pending request
    existing_request = db.query(FriendRequest).filter(
        FriendRequest.from_user_id == current_user.id,
        FriendRequest.to_user_id == request_data.to_user_id,
        FriendRequest.status == "pending"
    ).first()
    
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已发送过好友请求"
        )
    
    # Check if target user sent request to us
    reverse_request = db.query(FriendRequest).filter(
        FriendRequest.from_user_id == request_data.to_user_id,
        FriendRequest.to_user_id == current_user.id,
        FriendRequest.status == "pending"
    ).first()
    
    if reverse_request:
        # Auto accept
        reverse_request.status = "accepted"
        
        # Create friendship both ways
        db.add(Friendship(user_id=current_user.id, friend_id=request_data.to_user_id))
        db.add(Friendship(user_id=request_data.to_user_id, friend_id=current_user.id))
        
        db.commit()
        db.refresh(reverse_request)
        
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
    db.refresh(friend_request)
    
    return friend_request


@router.post("/requests/{request_id}/accept", response_model=SuccessResponse, summary="接受好友请求")
async def accept_friend_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """接受好友请求"""
    friend_request = db.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.to_user_id == current_user.id,
        FriendRequest.status == "pending"
    ).first()
    
    if not friend_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="好友请求不存在"
        )
    
    # Update request status
    friend_request.status = "accepted"
    
    # Create friendship both ways
    db.add(Friendship(user_id=current_user.id, friend_id=friend_request.from_user_id))
    db.add(Friendship(user_id=friend_request.from_user_id, friend_id=current_user.id))
    
    db.commit()
    
    return SuccessResponse(message="好友请求已接受")


@router.post("/requests/{request_id}/reject", response_model=SuccessResponse, summary="拒绝好友请求")
async def reject_friend_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """拒绝好友请求"""
    friend_request = db.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.to_user_id == current_user.id,
        FriendRequest.status == "pending"
    ).first()
    
    if not friend_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="好友请求不存在"
        )
    
    friend_request.status = "rejected"
    db.commit()
    
    return SuccessResponse(message="好友请求已拒绝")


# Blacklist
@router.get("/blacklist", response_model=BlacklistListResponse, summary="获取黑名单")
async def get_blacklist(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取黑名单列表"""
    query = db.query(Blacklist).filter(Blacklist.user_id == current_user.id)
    
    total = query.count()
    total_pages = ceil(total / page_size)
    
    blacklist = query.options(
        joinedload(Blacklist.blocked_user)
    ).offset((page - 1) * page_size).limit(page_size).all()
    
    return BlacklistListResponse(
        items=blacklist,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("/blacklist", response_model=BlacklistResponse, summary="添加黑名单")
async def add_to_blacklist(
    blacklist_data: BlacklistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """将用户加入黑名单"""
    if blacklist_data.blocked_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能拉黑自己"
        )
    
    # Check if user exists
    target_user = db.query(User).filter(User.id == blacklist_data.blocked_user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # Check if already in blacklist
    existing = db.query(Blacklist).filter(
        Blacklist.user_id == current_user.id,
        Blacklist.blocked_user_id == blacklist_data.blocked_user_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户已在黑名单中"
        )
    
    # Remove friendship if exists
    db.query(Friendship).filter(
        or_(
            and_(Friendship.user_id == current_user.id, Friendship.friend_id == blacklist_data.blocked_user_id),
            and_(Friendship.user_id == blacklist_data.blocked_user_id, Friendship.friend_id == current_user.id)
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
    db.refresh(blacklist)
    
    return blacklist


@router.delete("/blacklist/{blocked_user_id}", response_model=SuccessResponse, summary="移出黑名单")
async def remove_from_blacklist(
    blocked_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """将用户移出黑名单"""
    result = db.query(Blacklist).filter(
        Blacklist.user_id == current_user.id,
        Blacklist.blocked_user_id == blocked_user_id
    ).delete()
    
    if result == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该用户不在黑名单中"
        )
    
    db.commit()
    
    return SuccessResponse(message="已移出黑名单")
