from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import Optional
from math import ceil
from datetime import datetime
from decimal import Decimal

from ..database import get_db
from ..models.models import User, HelpTask, TaskApplication, TaskReview, Wallet, Transaction, TransactionType, TaskStatus, UserProfile
from ..schemas.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse,
    ApplicationCreate, ApplicationResponse, ReviewCreate, ReviewResponse
)
from ..schemas.common import SuccessResponse
from ..core.deps import get_current_user, get_optional_user

router = APIRouter(prefix="/tasks", tags=["互帮互助"])


@router.post("", response_model=TaskResponse, summary="发布任务")
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发布新任务"""
    # Check wallet balance
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    reward_amount = Decimal(str(task_data.reward))
    if not wallet or wallet.balance < reward_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="余额不足，请先充值"
        )
    
    # Freeze the reward amount
    wallet.balance -= reward_amount
    wallet.frozen_amount += reward_amount
    
    new_task = HelpTask(
        title=task_data.title,
        description=task_data.description,
        category=task_data.category.value,
        reward=task_data.reward,
        location=task_data.location,
        deadline=task_data.deadline,
        publisher_id=current_user.id,
        status="open",
        private_info=task_data.private_info  # 私密信息
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    return new_task


@router.get("", response_model=TaskListResponse, summary="获取任务列表")
async def get_tasks(
    category: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取任务列表"""
    query = db.query(HelpTask).filter(HelpTask.status != "cancelled")
    
    if category:
        query = query.filter(HelpTask.category == category)
    if status:
        query = query.filter(HelpTask.status == status)
    if keyword:
        query = query.filter(
            (HelpTask.title.contains(keyword)) |
            (HelpTask.description.contains(keyword))
        )
    
    total = query.count()
    total_pages = ceil(total / page_size)
    
    tasks = query.options(
        joinedload(HelpTask.publisher),
        joinedload(HelpTask.assignee)
    ).order_by(desc(HelpTask.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    # Add application count
    for task in tasks:
        task.application_count = db.query(TaskApplication).filter(
            TaskApplication.task_id == task.id
        ).count()
    
    return TaskListResponse(
        items=tasks,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/my/published", response_model=TaskListResponse, summary="我发布的任务")
async def get_my_published_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我发布的任务"""
    query = db.query(HelpTask).filter(HelpTask.publisher_id == current_user.id)
    
    total = query.count()
    total_pages = ceil(total / page_size)
    
    tasks = query.options(
        joinedload(HelpTask.assignee)
    ).order_by(desc(HelpTask.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    return TaskListResponse(
        items=tasks,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/my/accepted", response_model=TaskListResponse, summary="我接受的任务")
async def get_my_accepted_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我接受的任务"""
    query = db.query(HelpTask).filter(HelpTask.assignee_id == current_user.id)
    
    total = query.count()
    total_pages = ceil(total / page_size)
    
    tasks = query.options(
        joinedload(HelpTask.publisher)
    ).order_by(desc(HelpTask.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    return TaskListResponse(
        items=tasks,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/my/applied-ids", summary="我申请过的任务ID列表")
async def get_my_applied_task_ids(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我申请过的任务ID列表"""
    applications = db.query(TaskApplication.task_id).filter(
        TaskApplication.applicant_id == current_user.id,
        TaskApplication.status == "pending"
    ).all()
    
    return {"task_ids": [app.task_id for app in applications]}


@router.get("/{task_id}", response_model=TaskResponse, summary="获取任务详情")
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """获取任务详情，私密信息仅发布者和接单者可见"""
    task = db.query(HelpTask).options(
        joinedload(HelpTask.publisher),
        joinedload(HelpTask.assignee)
    ).filter(HelpTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    task.application_count = db.query(TaskApplication).filter(
        TaskApplication.task_id == task.id
    ).count()
    
    # 私密信息仅对发布者和接单者可见
    is_authorized = current_user and (
        current_user.id == task.publisher_id or 
        current_user.id == task.assignee_id
    )
    if not is_authorized:
        task.private_info = None
    
    return task


@router.put("/{task_id}", response_model=TaskResponse, summary="更新任务")
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新任务"""
    task = db.query(HelpTask).filter(HelpTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    if task.publisher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改此任务"
        )
    
    if task.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能修改未被接受的任务"
        )
    
    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "category" and value:
            value = value.value
        setattr(task, field, value)
    
    db.commit()
    db.refresh(task)
    
    return task


@router.delete("/{task_id}", response_model=SuccessResponse, summary="取消任务")
async def cancel_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消任务"""
    task = db.query(HelpTask).filter(HelpTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    if task.publisher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权取消此任务"
        )
    
    if task.status not in ["open", "assigned"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法取消进行中或已完成的任务"
        )
    
    # Refund the frozen amount
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if wallet:
        reward_amount = Decimal(str(task.reward))
        wallet.frozen_amount -= reward_amount
        wallet.balance += reward_amount
    
    task.status = "cancelled"
    db.commit()
    
    return SuccessResponse(message="任务取消成功")


# Applications
@router.post("/{task_id}/apply", response_model=ApplicationResponse, summary="申请任务")
async def apply_task(
    task_id: int,
    application_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """申请接受任务"""
    task = db.query(HelpTask).filter(HelpTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    if task.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该任务已被接受或已关闭"
        )
    
    if task.publisher_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能申请自己发布的任务"
        )
    
    existing = db.query(TaskApplication).filter(
        TaskApplication.task_id == task_id,
        TaskApplication.applicant_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已经申请过该任务"
        )
    
    application = TaskApplication(
        task_id=task_id,
        applicant_id=current_user.id,
        message=application_data.message,
        status="pending"
    )
    
    db.add(application)
    db.commit()
    db.refresh(application)
    
    return application


@router.get("/{task_id}/applications", response_model=list[ApplicationResponse], summary="获取申请列表")
async def get_applications(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务申请列表，按优先分排序（信誉分+好评率*100）//2"""
    task = db.query(HelpTask).filter(HelpTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    if task.publisher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有任务发布者可以查看申请"
        )
    
    applications = db.query(TaskApplication).options(
        joinedload(TaskApplication.applicant)
    ).filter(TaskApplication.task_id == task_id).all()
    
    # 计算每个申请者的优先分并排序
    def get_priority_score(application):
        profile = db.query(UserProfile).filter(
            UserProfile.user_id == application.applicant_id
        ).first()
        
        if not profile:
            # 默认值：信誉60，好评率100%，优先分80
            return 80
        
        credit_score = profile.credit_score or 60
        # 计算好评率
        approval_rate = 1.0
        if profile.total_reviews and profile.total_reviews > 0:
            approval_rate = (profile.positive_reviews or 0) / profile.total_reviews
        
        # 优先分 = (信誉分 + 好评率 * 100) // 2
        priority_score = (credit_score + int(approval_rate * 100)) // 2
        return priority_score
    
    # 按优先分降序排序
    applications_sorted = sorted(applications, key=get_priority_score, reverse=True)
    
    # 为每个申请添加优先分信息
    for app in applications_sorted:
        app.priority_score = get_priority_score(app)
    
    return applications_sorted


@router.post("/{task_id}/applications/{application_id}/accept", response_model=SuccessResponse, summary="接受申请")
async def accept_application(
    task_id: int,
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """接受申请"""
    task = db.query(HelpTask).filter(HelpTask.id == task_id).first()
    
    if not task or task.publisher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作"
        )
    
    # Check task status - use string comparison
    task_status_str = task.status.value if hasattr(task.status, 'value') else str(task.status)
    if task_status_str != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="任务已被接受"
        )
    
    application = db.query(TaskApplication).filter(
        TaskApplication.id == application_id,
        TaskApplication.task_id == task_id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="申请不存在"
        )
    
    # Accept this application
    application.status = "accepted"
    task.assignee_id = application.applicant_id
    task.status = TaskStatus.assigned  # Use enum value for assignment
    
    # Reject other applications
    db.query(TaskApplication).filter(
        TaskApplication.task_id == task_id,
        TaskApplication.id != application_id
    ).update({"status": "rejected"})
    
    db.commit()
    
    return SuccessResponse(message="已接受申请")


@router.post("/{task_id}/complete", response_model=SuccessResponse, summary="完成任务")
async def complete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """确认任务完成（发布者操作）"""
    task = db.query(HelpTask).filter(HelpTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    if task.publisher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有任务发布者可以确认完成"
        )
    
    if task.status not in ["assigned", "in_progress"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="任务状态不正确"
        )
    
    # Transfer reward
    publisher_wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    assignee_wallet = db.query(Wallet).filter(Wallet.user_id == task.assignee_id).first()
    reward_amount = Decimal(str(task.reward))
    
    if publisher_wallet:
        publisher_wallet.frozen_amount -= reward_amount
    
    if assignee_wallet:
        assignee_wallet.balance += reward_amount
        assignee_wallet.total_income = (assignee_wallet.total_income or Decimal('0')) + reward_amount
        
        # Create transaction record
        transaction = Transaction(
            wallet_id=assignee_wallet.id,
            user_id=task.assignee_id,
            type=TransactionType.task_reward,
            amount=task.reward,
            balance_after=assignee_wallet.balance,
            related_task_id=task.id,
            description=f"任务奖励：{task.title}",
            status="completed"
        )
        db.add(transaction)
    
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    
    db.commit()
    
    return SuccessResponse(message="任务完成，奖励已发放")


# Reviews
@router.post("/{task_id}/review", response_model=ReviewResponse, summary="评价任务")
async def create_review(
    task_id: int,
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """评价任务（双方互评）"""
    task = db.query(HelpTask).filter(HelpTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    if task.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能评价已完成的任务"
        )
    
    if current_user.id not in [task.publisher_id, task.assignee_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有任务相关方可以评价"
        )
    
    # Determine reviewee
    if current_user.id == task.publisher_id:
        reviewee_id = task.assignee_id
    else:
        reviewee_id = task.publisher_id
    
    # Check existing review
    existing = db.query(TaskReview).filter(
        TaskReview.task_id == task_id,
        TaskReview.reviewer_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已经评价过了"
        )
    
    review = TaskReview(
        task_id=task_id,
        reviewer_id=current_user.id,
        reviewee_id=reviewee_id,
        rating=review_data.rating,
        comment=review_data.comment
    )
    
    db.add(review)
    db.commit()
    db.refresh(review)
    
    return review
