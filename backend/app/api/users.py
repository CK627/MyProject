from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from ..database import get_db
from ..models.models import User, UserProfile
from ..schemas.user import (
    UserResponse, UserUpdate, UserBrief, UserWithProfile,
    UserProfileUpdate, UserProfileResponse
)
from ..schemas.common import SuccessResponse
from ..core.deps import get_current_user, get_current_admin_user

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/me", response_model=UserWithProfile, summary="获取当前用户详细信息")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的完整信息（包括档案）"""
    # 显式加载profile关系
    user = db.query(User).options(joinedload(User.profile)).filter(User.id == current_user.id).first()
    return user


@router.put("/me", response_model=UserResponse, summary="更新当前用户信息")
async def update_my_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新当前用户基本信息"""
    update_data = user_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.put("/me/profile", response_model=UserProfileResponse, summary="更新用户档案")
async def update_my_detail_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新当前用户的详细档案"""
    from datetime import datetime as dt
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    
    if not profile:
        # Create new profile
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    
    update_data = profile_data.model_dump(exclude_unset=True)
    
    # 处理字段映射和类型转换
    for field, value in update_data.items():
        if field == 'birthday' and value:
            # 将字符串日期转换为datetime
            try:
                value = dt.strptime(value, '%Y-%m-%d')
            except (ValueError, TypeError):
                pass
        elif field == 'grade' and value:
            # grade映射到enroll_year
            try:
                # 从"2024级"或"2024"中提取年份
                year_str = ''.join(filter(str.isdigit, str(value)))
                if year_str:
                    setattr(profile, 'enroll_year', int(year_str))
            except (ValueError, TypeError):
                pass
            continue
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    
    return profile


@router.get("/{user_id}", response_model=UserBrief, summary="获取用户信息")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取指定用户的基本信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user


@router.get("/{user_id}/detail", response_model=UserWithProfile, summary="获取用户详细信息")
async def get_user_detail(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取指定用户的完整信息（包括档案）"""
    user = db.query(User).options(joinedload(User.profile)).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user


@router.get("", response_model=List[UserBrief], summary="搜索用户")
async def search_users(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """搜索用户"""
    query = db.query(User).filter(User.status == "active")
    
    if keyword:
        query = query.filter(
            (User.name.contains(keyword)) | 
            (User.email.contains(keyword))
        )
    
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return users


# Admin endpoints
@router.get("/admin/list", response_model=List[UserResponse], summary="管理员-获取用户列表")
async def admin_get_users(
    status: Optional[str] = None,
    role: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """管理员获取用户列表"""
    query = db.query(User)
    
    if status:
        query = query.filter(User.status == status)
    if role:
        query = query.filter(User.role == role)
    
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return users


@router.put("/admin/{user_id}/status", response_model=SuccessResponse, summary="管理员-修改用户状态")
async def admin_update_user_status(
    user_id: int,
    status: str = Query(..., description="新状态: active, inactive, banned"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """管理员修改用户状态"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自己的状态"
        )
    
    user.status = status
    db.commit()
    
    return SuccessResponse(message="状态修改成功")
