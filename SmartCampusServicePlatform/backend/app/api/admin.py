from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from typing import Optional
from math import ceil
from datetime import datetime

from ..database import get_db
from ..models.models import User, Post, HelpTask, Report, Announcement
from ..schemas.message import ReportCreate, ReportResponse
from ..schemas.common import SuccessResponse
from ..core.deps import get_current_user, get_current_admin_user

router = APIRouter(prefix="/admin", tags=["管理"])


@router.get("/public-stats", summary="获取公开平台统计")
async def get_public_stats(db: Session = Depends(get_db)):
    """获取公开的平台统计数据（无需登录）"""
    user_count = db.query(User).filter(User.status == "active").count()
    post_count = db.query(Post).filter(Post.status.in_(["published", "approved"])).count()
    task_count = db.query(HelpTask).count()
    open_task_count = db.query(HelpTask).filter(HelpTask.status == "open").count()
    
    return {
        "user_count": user_count,
        "post_count": post_count,
        "task_count": task_count,
        "open_task_count": open_task_count
    }


@router.get("/stats", summary="获取平台统计")
async def get_platform_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取平台统计数据"""
    user_count = db.query(User).count()
    active_user_count = db.query(User).filter(User.status == "active").count()
    post_count = db.query(Post).filter(Post.status == "published").count()
    task_count = db.query(HelpTask).count()
    open_task_count = db.query(HelpTask).filter(HelpTask.status == "open").count()
    pending_report_count = db.query(Report).filter(Report.status == "pending").count()
    
    return {
        "user_count": user_count,
        "active_user_count": active_user_count,
        "post_count": post_count,
        "task_count": task_count,
        "open_task_count": open_task_count,
        "pending_report_count": pending_report_count
    }


# Reports
@router.post("/reports", response_model=ReportResponse, summary="提交举报")
async def create_report(
    report_data: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """提交举报"""
    # Check if already reported
    existing = db.query(Report).filter(
        Report.reporter_id == current_user.id,
        Report.target_type == report_data.target_type.value,
        Report.target_id == report_data.target_id,
        Report.status == "pending"
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已举报过该内容"
        )
    
    report = Report(
        reporter_id=current_user.id,
        target_type=report_data.target_type.value,
        target_id=report_data.target_id,
        reason=report_data.reason,
        status="pending"
    )
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return report


@router.get("/reports", response_model=list[ReportResponse], summary="获取举报列表")
async def get_reports(
    status: Optional[str] = "pending",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取举报列表（管理员）"""
    query = db.query(Report)
    
    if status:
        query = query.filter(Report.status == status)
    
    reports = query.options(
        joinedload(Report.reporter)
    ).order_by(desc(Report.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return reports


@router.post("/reports/{report_id}/resolve", response_model=SuccessResponse, summary="处理举报")
async def resolve_report(
    report_id: int,
    action: str = Query(..., description="处理动作: approve, reject"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """处理举报（管理员）"""
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="举报不存在"
        )
    
    if report.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该举报已处理"
        )
    
    if action == "approve":
        report.status = "resolved"
        
        # Handle the reported content
        if report.target_type == "post":
            post = db.query(Post).filter(Post.id == report.target_id).first()
            if post:
                post.status = "hidden"
        elif report.target_type == "user":
            user = db.query(User).filter(User.id == report.target_id).first()
            if user:
                user.status = "banned"
        elif report.target_type == "task":
            task = db.query(HelpTask).filter(HelpTask.id == report.target_id).first()
            if task:
                task.status = "cancelled"
    else:
        report.status = "rejected"
    
    report.resolved_at = datetime.utcnow()
    db.commit()
    
    return SuccessResponse(message="举报已处理")


# Content moderation
@router.get("/posts", summary="获取帖子列表（管理）")
async def admin_get_posts(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取帖子列表（管理员）"""
    query = db.query(Post)
    
    if status:
        query = query.filter(Post.status == status)
    
    total = query.count()
    
    posts = query.options(
        joinedload(Post.author)
    ).order_by(desc(Post.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return {
        "items": posts,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.put("/posts/{post_id}/status", response_model=SuccessResponse, summary="修改帖子状态")
async def admin_update_post_status(
    post_id: int,
    status: str = Query(..., description="新状态: published, hidden, deleted"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """修改帖子状态（管理员）"""
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="帖子不存在"
        )
    
    post.status = status
    db.commit()
    
    return SuccessResponse(message="状态修改成功")


@router.get("/tasks", summary="获取任务列表（管理）")
async def admin_get_tasks(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取任务列表（管理员）"""
    query = db.query(HelpTask)
    
    if status:
        query = query.filter(HelpTask.status == status)
    
    total = query.count()
    
    tasks = query.options(
        joinedload(HelpTask.publisher)
    ).order_by(desc(HelpTask.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return {
        "items": tasks,
        "total": total,
        "page": page,
        "page_size": page_size
    }
