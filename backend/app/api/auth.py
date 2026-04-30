from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..database import get_db
from ..models.models import User, Wallet, UserLike, UserProfile
from ..schemas.auth import (
    Token, LoginRequest, RegisterRequest, ChangePasswordRequest,
    ResetPasswordRequest, ResetPasswordConfirm, GitHubCallbackRequest
)
from ..schemas.user import UserResponse, UserCreate
from ..schemas.common import SuccessResponse
from ..core.security import verify_password, get_password_hash, create_access_token, generate_reset_token
from ..core.deps import get_current_user
from ..core.email import send_password_reset_email
from ..core.oauth import exchange_github_code, get_github_user_info
from ..config import settings

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=Token, summary="用户登录")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录获取token"""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账号使用GitHub登录，请点击GitHub按钮登录"
        )
    
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )
    
    # Update last login time and online status
    user.last_login = datetime.utcnow()
    user.online_status = 'online'
    user.last_active = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/login/json", response_model=Token, summary="JSON格式登录")
async def login_json(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """JSON格式的用户登录"""
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )
    
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账号使用GitHub登录，请点击GitHub按钮登录"
        )
    
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )
    
    if user.status == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )
    
    user.last_login = datetime.utcnow()
    user.online_status = 'online'
    user.last_active = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/register", response_model=UserResponse, summary="用户注册")
async def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """用户注册"""
    # Check if email exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        name=user_data.name,
        phone=user_data.phone,
        role="student",
        status="active"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create wallet for new user
    wallet = Wallet(user_id=new_user.id, balance=0.0, frozen_amount=0.0)
    db.add(wallet)
    db.commit()
    
    return new_user


@router.post("/change-password", response_model=SuccessResponse, summary="修改密码")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改当前用户密码"""
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="第三方登录账号无法修改密码"
        )
    
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )
    
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return SuccessResponse(message="密码修改成功")


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前登录用户信息"""
    return current_user


@router.post("/logout", response_model=SuccessResponse, summary="退出登录")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """退出登录（客户端需要删除token）"""
    return SuccessResponse(message="退出登录成功")


@router.post("/forgot-password", response_model=SuccessResponse, summary="忘记密码")
async def forgot_password(
    data: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """发送密码重置邮件"""
    user = db.query(User).filter(User.email == data.email).first()

    if user:
        # OAuth用户无需密码重置
        if user.github_id and not user.password_hash:
            return SuccessResponse(message="该账号使用GitHub登录，无需重置密码")

        # 生成重置token
        token = generate_reset_token()
        user.password_reset_token = token
        user.password_reset_expires = datetime.utcnow() + timedelta(minutes=30)
        db.commit()
        
        # 尝试从请求中获取前端源地址，否则回退到配置
        origin = request.headers.get("origin")
        frontend_url = origin if origin else settings.FRONTEND_URL

        # 发送邮件
        send_password_reset_email(user.email, token, frontend_url)

    # 无论用户是否存在都返回相同消息，防止邮箱探测
    return SuccessResponse(message="如果该邮箱已注册，重置链接已发送到您的邮箱")


@router.post("/reset-password", response_model=SuccessResponse, summary="重置密码")
async def reset_password(
    data: ResetPasswordConfirm,
    db: Session = Depends(get_db)
):
    """通过重置token设置新密码"""
    user = db.query(User).filter(User.password_reset_token == data.token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的重置链接"
        )

    if not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
        # 清理过期token
        user.password_reset_token = None
        user.password_reset_expires = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置链接已过期，请重新申请"
        )

    # 更新密码
    user.password_hash = get_password_hash(data.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()

    return SuccessResponse(message="密码重置成功，请使用新密码登录")


@router.post("/github/callback", response_model=Token, summary="GitHub OAuth回调")
async def github_callback(
    data: GitHubCallbackRequest,
    db: Session = Depends(get_db)
):
    """处理GitHub OAuth授权回调"""
    try:
        # 用授权码换取access_token
        access_token = await exchange_github_code(data.code)
        # 获取GitHub用户信息
        github_user = await get_github_user_info(access_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub登录失败: {str(e)}"
        )

    github_id = github_user["github_id"]
    email = github_user["email"]
    name = github_user["name"]
    avatar_url = github_user.get("avatar_url")

    # 先按github_id查找
    user = db.query(User).filter(User.github_id == github_id).first()

    if not user:
        # 按email查找
        user = db.query(User).filter(User.email == email).first()
        if user:
            # 已有账号，绑定github_id
            if user.github_id and user.github_id != github_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该邮箱已绑定其他GitHub账号"
                )
            user.github_id = github_id
            if avatar_url and not user.avatar:
                user.avatar = avatar_url
        else:
            # 自动注册新用户
            user = User(
                email=email,
                password_hash=None,
                name=name,
                github_id=github_id,
                avatar=avatar_url,
                role="student",
                status="active"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # 创建钱包
            wallet = Wallet(user_id=user.id, balance=0.0, frozen_amount=0.0)
            db.add(wallet)

    if user.status == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )

    # 更新登录状态
    user.last_login = datetime.utcnow()
    user.online_status = 'online'
    user.last_active = datetime.utcnow()
    db.commit()

    # 生成JWT
    jwt_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value if hasattr(user.role, 'value') else user.role}
    )

    return Token(access_token=jwt_token, token_type="bearer")


@router.post("/users/{user_id}/like", response_model=SuccessResponse, summary="点赞用户")
async def like_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """给用户点赞"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能给自己点赞"
        )
    
    # 检查目标用户是否存在
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 检查是否已点赞
    existing_like = db.query(UserLike).filter(
        UserLike.from_user_id == current_user.id,
        UserLike.to_user_id == user_id
    ).first()
    
    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已经点赞过了"
        )
    
    # 添加点赞记录
    new_like = UserLike(
        from_user_id=current_user.id,
        to_user_id=user_id
    )
    db.add(new_like)
    
    # 更新被点赞用户的点赞数
    target_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if target_profile:
        target_profile.like_count = (target_profile.like_count or 0) + 1
    else:
        # 如果用户没有profile，创建一个
        target_profile = UserProfile(
            user_id=user_id,
            like_count=1,
            credit_score=60
        )
        db.add(target_profile)
    
    db.commit()
    
    return SuccessResponse(message="点赞成功")


@router.delete("/users/{user_id}/like", response_model=SuccessResponse, summary="取消点赞")
async def unlike_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消对用户的点赞"""
    existing_like = db.query(UserLike).filter(
        UserLike.from_user_id == current_user.id,
        UserLike.to_user_id == user_id
    ).first()
    
    if not existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="还没有点赞"
        )
    
    db.delete(existing_like)
    
    # 更新被点赞用户的点赞数
    target_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if target_profile and target_profile.like_count > 0:
        target_profile.like_count -= 1
    
    db.commit()
    
    return SuccessResponse(message="取消点赞成功")


@router.get("/users/{user_id}/like-status", summary="获取点赞状态")
async def get_like_status(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查当前用户是否已点赞某用户"""
    existing_like = db.query(UserLike).filter(
        UserLike.from_user_id == current_user.id,
        UserLike.to_user_id == user_id
    ).first()
    
    return {"liked": existing_like is not None}


@router.get("/users/{user_id}/profile", summary="获取用户信誉信息")
async def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db)
):
    """获取用户的信誉、好评率等信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    if not profile:
        # 返回默认值
        return {
            "user_id": user_id,
            "name": user.name,
            "credit_score": 60,
            "like_count": 0,
            "approval_rate": 1.0,
            "priority_score": 80
        }
    
    # 计算好评率
    approval_rate = 1.0
    if profile.total_reviews and profile.total_reviews > 0:
        approval_rate = (profile.positive_reviews or 0) / profile.total_reviews
    
    # 计算优先分
    priority_score = ((profile.credit_score or 60) + int(approval_rate * 100)) // 2
    
    return {
        "user_id": user_id,
        "name": user.name,
        "credit_score": profile.credit_score or 60,
        "like_count": profile.like_count or 0,
        "approval_rate": approval_rate,
        "priority_score": priority_score
    }
