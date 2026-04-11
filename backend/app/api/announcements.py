from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from math import ceil
from datetime import datetime

from ..database import get_db
from ..models.models import User, Announcement, AnnouncementRead
from ..schemas.announcement import (
    AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse, 
    AnnouncementListResponse
)
from ..schemas.common import SuccessResponse
from ..core.deps import get_current_user, get_current_admin_user

router = APIRouter(prefix="/announcements", tags=["公告"])


@router.get("/public", response_model=AnnouncementListResponse, summary="获取公开公告列表")
async def get_public_announcements(
    type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取公开公告列表（无需登录）"""
    query = db.query(Announcement).filter(Announcement.status == "published")
    
    if type:
        query = query.filter(Announcement.type == type)
    
    total = query.count()
    total_pages = ceil(total / page_size)
    
    # Order by is_pinned first, then by publish_date
    announcements = query.order_by(
        desc(Announcement.is_pinned),
        desc(Announcement.publish_date)
    ).offset((page - 1) * page_size).limit(page_size).all()
    
    return AnnouncementListResponse(
        items=announcements,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("", response_model=AnnouncementListResponse, summary="获取公告列表")
async def get_announcements(
    type: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取公告列表"""
    query = db.query(Announcement).filter(Announcement.status == "published")
    
    if type:
        query = query.filter(Announcement.type == type)
    
    if keyword:
        query = query.filter(
            (Announcement.title.contains(keyword)) |
            (Announcement.content.contains(keyword))
        )
    
    total = query.count()
    total_pages = ceil(total / page_size)
    
    # Order by is_pinned first, then by publish_date
    announcements = query.order_by(
        desc(Announcement.is_pinned),
        desc(Announcement.publish_date)
    ).offset((page - 1) * page_size).limit(page_size).all()
    
    # Check read status for current user
    read_ids = set(
        r.announcement_id for r in db.query(AnnouncementRead).filter(
            AnnouncementRead.user_id == current_user.id,
            AnnouncementRead.announcement_id.in_([a.id for a in announcements])
        ).all()
    )
    
    for announcement in announcements:
        announcement.is_read = announcement.id in read_ids
    
    return AnnouncementListResponse(
        items=announcements,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{announcement_id}", response_model=AnnouncementResponse, summary="获取公告详情")
async def get_announcement(
    announcement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取公告详情"""
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id,
        Announcement.status == "published"
    ).first()
    
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在"
        )
    
    # Increment view count
    announcement.view_count += 1
    
    # Mark as read
    existing_read = db.query(AnnouncementRead).filter(
        AnnouncementRead.announcement_id == announcement_id,
        AnnouncementRead.user_id == current_user.id
    ).first()
    
    if not existing_read:
        read_record = AnnouncementRead(
            announcement_id=announcement_id,
            user_id=current_user.id
        )
        db.add(read_record)
    
    db.commit()
    
    announcement.is_read = True
    
    return announcement


@router.post("/{announcement_id}/read", response_model=SuccessResponse, summary="标记为已读")
async def mark_as_read(
    announcement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """标记公告为已读"""
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id
    ).first()
    
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在"
        )
    
    existing_read = db.query(AnnouncementRead).filter(
        AnnouncementRead.announcement_id == announcement_id,
        AnnouncementRead.user_id == current_user.id
    ).first()
    
    if not existing_read:
        read_record = AnnouncementRead(
            announcement_id=announcement_id,
            user_id=current_user.id
        )
        db.add(read_record)
        db.commit()
    
    return SuccessResponse(message="已标记为已读")


# Admin endpoints
@router.post("", response_model=AnnouncementResponse, summary="发布公告")
async def create_announcement(
    announcement_data: AnnouncementCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """发布新公告（管理员）"""
    announcement = Announcement(
        title=announcement_data.title,
        content=announcement_data.content,
        type=announcement_data.type.value,
        is_pinned=announcement_data.is_pinned,
        publisher_id=current_user.id,
        status=announcement_data.status.value,
        publish_date=datetime.utcnow() if announcement_data.status.value == "published" else None
    )
    
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    
    return announcement


@router.put("/{announcement_id}", response_model=AnnouncementResponse, summary="更新公告")
async def update_announcement(
    announcement_id: int,
    announcement_data: AnnouncementUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """更新公告（管理员）"""
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id
    ).first()
    
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在"
        )
    
    update_data = announcement_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field in ["type", "status"] and value:
            value = value.value
        setattr(announcement, field, value)
    
    # Set publish_date if publishing
    if announcement_data.status and announcement_data.status.value == "published" and not announcement.publish_date:
        announcement.publish_date = datetime.utcnow()
    
    db.commit()
    db.refresh(announcement)
    
    return announcement


@router.delete("/{announcement_id}", response_model=SuccessResponse, summary="删除公告")
async def delete_announcement(
    announcement_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """删除公告（管理员）"""
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id
    ).first()
    
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在"
        )
    
    announcement.status = "archived"
    db.commit()
    
    return SuccessResponse(message="公告已删除")
