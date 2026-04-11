from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from typing import Optional
from math import ceil

from ..database import get_db
from ..models.models import (
    User, Post, PostTag, PostLike, PostComment, UserProfile,
    CommentLike, CommentDislike, CommentReviewerDelete, Notification
)
from ..schemas.post import (
    PostCreate, PostUpdate, PostResponse, PostListResponse,
    CommentCreate, CommentResponse, PostTagResponse
)
from ..schemas.common import SuccessResponse
from ..core.deps import get_current_user, get_current_admin_user

# 评论删除条件：拉踩数 > 点赞数 * 2 + 5
DISLIKE_DELETE_THRESHOLD_MULTIPLIER = 2
DISLIKE_DELETE_THRESHOLD_BASE = 5
# 审核员删除所需投票数
REVIEWER_DELETE_VOTES_REQUIRED = 3

router = APIRouter(prefix="/posts", tags=["校园墙"])

# 审核员所需的最低信誉分
REVIEWER_MIN_CREDIT_SCORE = 98


def is_user_reviewer(user: User, db: Session) -> bool:
    """检查用户是否有审核员权限（信誉分>98或管理员）"""
    if user.role == "admin":
        return True
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile and profile.credit_score > REVIEWER_MIN_CREDIT_SCORE:
        return True
    return False


@router.get("/tags", response_model=list[PostTagResponse], summary="获取所有标签")
async def get_all_tags(db: Session = Depends(get_db)):
    """获取所有帖子标签"""
    tags = db.query(PostTag).all()
    return tags


@router.post("", response_model=PostResponse, summary="发布帖子")
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发布新帖子（需要审核后才能显示）"""
    new_post = Post(
        content=post_data.content,
        images=post_data.images,
        is_anonymous=post_data.is_anonymous,
        user_id=current_user.id,
        status="pending"  # 新帖子默认待审核状态
    )
    
    db.add(new_post)
    db.flush()
    
    # Add tags
    if post_data.tag_ids:
        for tag_id in post_data.tag_ids:
            tag = PostTag(post_id=new_post.id, tag_name=f"tag_{tag_id}")
            db.add(tag)
    
    db.commit()
    db.refresh(new_post)
    
    return new_post


@router.get("/hot", response_model=PostListResponse, summary="获取热门帖子")
async def get_hot_posts(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """获取热门帖子（按点赞数+评论数排序）"""
    query = db.query(Post).filter(Post.status.in_(["published", "approved"]))
    
    total = query.count()
    
    # 按热度排序（点赞数 + 评论数）
    posts = query.options(
        joinedload(Post.author),
        joinedload(Post.tags)
    ).order_by(
        desc(Post.likes_count + Post.comments_count),
        desc(Post.created_at)
    ).limit(limit).all()
    
    return PostListResponse(
        items=posts,
        total=total,
        page=1,
        page_size=limit,
        total_pages=1
    )


@router.get("", response_model=PostListResponse, summary="获取帖子列表")
async def get_posts(
    tag_id: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取帖子列表"""
    query = db.query(Post).filter(Post.status == "approved")
    
    if tag_id:
        query = query.join(PostTag).filter(PostTag.id == tag_id)
    
    if keyword:
        query = query.filter(Post.content.contains(keyword))
    
    total = query.count()
    total_pages = ceil(total / page_size)
    
    posts = query.options(
        joinedload(Post.author),
        joinedload(Post.tags)
    ).order_by(desc(Post.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    return PostListResponse(
        items=posts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/my", response_model=PostListResponse, summary="获取我的帖子")
async def get_my_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的帖子"""
    query = db.query(Post).filter(
        Post.user_id == current_user.id,
        Post.status != "deleted"
    )
    
    total = query.count()
    total_pages = ceil(total / page_size)
    
    posts = query.options(
        joinedload(Post.tags)
    ).order_by(desc(Post.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    return PostListResponse(
        items=posts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{post_id}", response_model=PostResponse, summary="获取帖子详情")
async def get_post(
    post_id: int,
    db: Session = Depends(get_db)
):
    """获取帖子详情"""
    post = db.query(Post).options(
        joinedload(Post.author),
        joinedload(Post.tags)
    ).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="帖子不存在"
        )
    
    return post


@router.put("/{post_id}", response_model=PostResponse, summary="更新帖子")
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新帖子"""
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="帖子不存在"
        )
    
    if post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改此帖子"
        )
    
    update_data = post_data.model_dump(exclude_unset=True, exclude={"tag_ids"})
    for field, value in update_data.items():
        if hasattr(post, field):
            setattr(post, field, value)
    
    if post_data.tag_ids is not None:
        # Delete old tags and add new ones
        db.query(PostTag).filter(PostTag.post_id == post_id).delete()
        for tag_id in post_data.tag_ids:
            tag = PostTag(post_id=post_id, tag_name=f"tag_{tag_id}")
            db.add(tag)
    
    db.commit()
    db.refresh(post)
    
    return post


@router.delete("/{post_id}", response_model=SuccessResponse, summary="删除帖子")
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除帖子（软删除）"""
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="帖子不存在"
        )
    
    if post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此帖子"
        )
    
    post.status = "deleted"
    db.commit()
    
    return SuccessResponse(message="帖子删除成功")


# Comments
@router.post("/{post_id}/comments", response_model=CommentResponse, summary="发表评论")
async def create_comment(
    post_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发表评论"""
    post = db.query(Post).filter(Post.id == post_id, Post.status.in_(["published", "approved"])).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="帖子不存在"
        )
    
    comment = PostComment(
        post_id=post_id,
        user_id=current_user.id,
        content=comment_data.content,
        parent_id=comment_data.parent_id
    )
    
    db.add(comment)
    post.comments_count += 1
    db.commit()
    db.refresh(comment)
    
    return comment


@router.get("/{post_id}/comments", response_model=list[CommentResponse], summary="获取评论列表")
async def get_comments(
    post_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取帖子评论"""
    comments = db.query(PostComment).options(
        joinedload(PostComment.user)
    ).filter(
        PostComment.post_id == post_id
    ).order_by(PostComment.created_at).offset((page - 1) * page_size).limit(page_size).all()
    
    return comments


@router.delete("/{post_id}/comments/{comment_id}", response_model=SuccessResponse, summary="删除评论")
async def delete_comment(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除评论"""
    comment = db.query(PostComment).filter(
        PostComment.id == comment_id,
        PostComment.post_id == post_id
    ).first()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在"
        )
    
    if comment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此评论"
        )
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if post:
        post.comments_count = max(0, post.comments_count - 1)
    
    db.delete(comment)
    db.commit()
    
    return SuccessResponse(message="评论删除成功")


# Likes
@router.post("/{post_id}/like", response_model=SuccessResponse, summary="点赞")
async def like_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """点赞帖子"""
    post = db.query(Post).filter(Post.id == post_id, Post.status.in_(["published", "approved"])).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="帖子不存在"
        )
    
    existing_like = db.query(PostLike).filter(
        PostLike.post_id == post_id,
        PostLike.user_id == current_user.id
    ).first()
    
    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已经点过赞了"
        )
    
    like = PostLike(post_id=post_id, user_id=current_user.id)
    db.add(like)
    post.likes_count += 1
    db.commit()
    
    return SuccessResponse(message="点赞成功")


@router.delete("/{post_id}/like", response_model=SuccessResponse, summary="取消点赞")
async def unlike_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消点赞"""
    like = db.query(PostLike).filter(
        PostLike.post_id == post_id,
        PostLike.user_id == current_user.id
    ).first()
    
    if not like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="还没有点赞"
        )
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if post:
        post.likes_count = max(0, post.likes_count - 1)
    
    db.delete(like)
    db.commit()
    
    return SuccessResponse(message="取消点赞成功")


@router.get("/{post_id}/like-status", summary="检查点赞状态")
async def check_like_status(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查当前用户是否已点赞该帖子"""
    existing_like = db.query(PostLike).filter(
        PostLike.post_id == post_id,
        PostLike.user_id == current_user.id
    ).first()
    return {"liked": existing_like is not None}


# ============ 审核相关 API ============

@router.get("/review/check", summary="检查审核员权限")
async def check_reviewer_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查当前用户是否有审核员权限"""
    is_reviewer = is_user_reviewer(current_user, db)
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    credit_score = profile.credit_score if profile else 60
    
    return {
        "is_reviewer": is_reviewer,
        "credit_score": credit_score,
        "required_score": REVIEWER_MIN_CREDIT_SCORE,
        "is_admin": current_user.role == "admin"
    }


@router.get("/review/pending", response_model=PostListResponse, summary="获取待审核帖子")
async def get_pending_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取待审核的帖子列表（仅审核员可访问）"""
    if not is_user_reviewer(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要审核员权限（信誉分>98）"
        )
    
    query = db.query(Post).filter(Post.status == "pending")
    
    total = query.count()
    total_pages = ceil(total / page_size)
    
    posts = query.options(
        joinedload(Post.author),
        joinedload(Post.tags)
    ).order_by(desc(Post.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    return PostListResponse(
        items=posts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("/review/{post_id}/approve", response_model=SuccessResponse, summary="通过审核")
async def approve_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """审核通过帖子"""
    if not is_user_reviewer(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要审核员权限（信誉分>98）"
        )
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="帖子不存在"
        )
    
    if post.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该帖子不在待审核状态"
        )
    
    post.status = "approved"
    db.commit()
    
    return SuccessResponse(message="审核通过")


@router.post("/review/{post_id}/reject", response_model=SuccessResponse, summary="拒绝审核")
async def reject_post(
    post_id: int,
    reason: str = Query(None, description="拒绝原因"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """拒绝帖子"""
    if not is_user_reviewer(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要审核员权限（信誉分>98）"
        )
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="帖子不存在"
        )
    
    if post.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该帖子不在待审核状态"
        )
    
    post.status = "rejected"
    db.commit()
    
    return SuccessResponse(message="已拒绝")


@router.get("/review/stats", summary="获取审核统计")
async def get_review_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审核统计数据"""
    if not is_user_reviewer(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要审核员权限（信誉分>98）"
        )
    
    pending_count = db.query(Post).filter(Post.status == "pending").count()
    approved_count = db.query(Post).filter(Post.status == "approved").count()
    rejected_count = db.query(Post).filter(Post.status == "rejected").count()
    
    return {
        "pending": pending_count,
        "approved": approved_count,
        "rejected": rejected_count
    }


# ============ 评论增强功能 API ============

def check_and_delete_comment_by_dislikes(comment: PostComment, db: Session):
    """检查是否满足拉踩删除条件：拉踩数 > 点赞数 * 2 + 5"""
    threshold = comment.likes_count * DISLIKE_DELETE_THRESHOLD_MULTIPLIER + DISLIKE_DELETE_THRESHOLD_BASE
    if comment.dislikes_count > threshold:
        comment.status = "deleted"
        comment.delete_reason = f"社区投票删除（拉踩数{comment.dislikes_count}超过阈值{threshold}）"
        
        # 更新帖子评论数
        post = db.query(Post).filter(Post.id == comment.post_id).first()
        if post:
            post.comments_count = max(0, post.comments_count - 1)
        
        # 创建通知
        notification = Notification(
            user_id=comment.user_id,
            type="comment_deleted",
            title="您的评论已被删除",
            content=f"您的评论因社区投票被删除（原因：拉踩数超过阈值）。惩罚：信誉分-2。原评论内容：「{comment.content[:50]}{'...' if len(comment.content) > 50 else ''}」",
            related_id=comment.id
        )
        db.add(notification)
        
        # 扣除信誉分
        profile = db.query(UserProfile).filter(UserProfile.user_id == comment.user_id).first()
        if profile:
            profile.credit_score = max(0, profile.credit_score - 2)
        
        db.commit()
        return True
    return False


def check_and_delete_comment_by_reviewers(comment: PostComment, db: Session, reason: str):
    """检查是否满足审核员删除条件：3个审核员投票"""
    if comment.reviewer_delete_count >= REVIEWER_DELETE_VOTES_REQUIRED:
        comment.status = "deleted"
        comment.delete_reason = f"审核员投票删除：{reason}"
        
        # 更新帖子评论数
        post = db.query(Post).filter(Post.id == comment.post_id).first()
        if post:
            post.comments_count = max(0, post.comments_count - 1)
        
        # 创建通知
        notification = Notification(
            user_id=comment.user_id,
            type="comment_deleted",
            title="您的评论已被审核员删除",
            content=f"您的评论因违规被审核员删除。原因：{reason}。惩罚：信誉分-5。原评论内容：「{comment.content[:50]}{'...' if len(comment.content) > 50 else ''}」",
            related_id=comment.id
        )
        db.add(notification)
        
        # 扣除信誉分
        profile = db.query(UserProfile).filter(UserProfile.user_id == comment.user_id).first()
        if profile:
            profile.credit_score = max(0, profile.credit_score - 5)
        
        db.commit()
        return True
    return False


@router.post("/{post_id}/comments/{comment_id}/like", response_model=SuccessResponse, summary="点赞评论")
async def like_comment(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """点赞评论"""
    comment = db.query(PostComment).filter(
        PostComment.id == comment_id,
        PostComment.post_id == post_id,
        PostComment.status == "active"
    ).first()
    
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
    
    # 检查是否已点赞
    existing_like = db.query(CommentLike).filter(
        CommentLike.comment_id == comment_id,
        CommentLike.user_id == current_user.id
    ).first()
    
    if existing_like:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已点赞过该评论")
    
    # 如果之前拉踩过，先取消拉踩
    existing_dislike = db.query(CommentDislike).filter(
        CommentDislike.comment_id == comment_id,
        CommentDislike.user_id == current_user.id
    ).first()
    if existing_dislike:
        db.delete(existing_dislike)
        comment.dislikes_count = max(0, comment.dislikes_count - 1)
    
    # 添加点赞
    like = CommentLike(comment_id=comment_id, user_id=current_user.id)
    db.add(like)
    comment.likes_count += 1
    db.commit()
    
    return SuccessResponse(message="点赞成功")


@router.delete("/{post_id}/comments/{comment_id}/like", response_model=SuccessResponse, summary="取消评论点赞")
async def unlike_comment(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消评论点赞"""
    like = db.query(CommentLike).filter(
        CommentLike.comment_id == comment_id,
        CommentLike.user_id == current_user.id
    ).first()
    
    if not like:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未点赞该评论")
    
    comment = db.query(PostComment).filter(PostComment.id == comment_id).first()
    if comment:
        comment.likes_count = max(0, comment.likes_count - 1)
    
    db.delete(like)
    db.commit()
    
    return SuccessResponse(message="取消点赞成功")


@router.post("/{post_id}/comments/{comment_id}/dislike", response_model=SuccessResponse, summary="拉踩评论")
async def dislike_comment(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """拉踩评论（拉踩数 > 点赞数*2+5 时自动删除）"""
    comment = db.query(PostComment).filter(
        PostComment.id == comment_id,
        PostComment.post_id == post_id,
        PostComment.status == "active"
    ).first()
    
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
    
    # 不能拉踩自己的评论
    if comment.user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能拉踩自己的评论")
    
    # 检查是否已拉踩
    existing_dislike = db.query(CommentDislike).filter(
        CommentDislike.comment_id == comment_id,
        CommentDislike.user_id == current_user.id
    ).first()
    
    if existing_dislike:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已拉踩过该评论")
    
    # 如果之前点赞过，先取消点赞
    existing_like = db.query(CommentLike).filter(
        CommentLike.comment_id == comment_id,
        CommentLike.user_id == current_user.id
    ).first()
    if existing_like:
        db.delete(existing_like)
        comment.likes_count = max(0, comment.likes_count - 1)
    
    # 添加拉踩
    dislike = CommentDislike(comment_id=comment_id, user_id=current_user.id)
    db.add(dislike)
    comment.dislikes_count += 1
    db.commit()
    
    # 检查是否满足删除条件
    deleted = check_and_delete_comment_by_dislikes(comment, db)
    
    return SuccessResponse(message="已拉踩" + ("，该评论因拉踩过多已被删除" if deleted else ""))


@router.delete("/{post_id}/comments/{comment_id}/dislike", response_model=SuccessResponse, summary="取消拉踩")
async def undislike_comment(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消拉踩"""
    dislike = db.query(CommentDislike).filter(
        CommentDislike.comment_id == comment_id,
        CommentDislike.user_id == current_user.id
    ).first()
    
    if not dislike:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未拉踩该评论")
    
    comment = db.query(PostComment).filter(PostComment.id == comment_id).first()
    if comment:
        comment.dislikes_count = max(0, comment.dislikes_count - 1)
    
    db.delete(dislike)
    db.commit()
    
    return SuccessResponse(message="取消拉踩成功")


@router.post("/{post_id}/comments/{comment_id}/reviewer-delete", response_model=SuccessResponse, summary="审核员投票删除评论")
async def reviewer_delete_comment(
    post_id: int,
    comment_id: int,
    reason: str = Query(..., description="删除原因"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """审核员投票删除评论（3票删除）"""
    if not is_user_reviewer(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要审核员权限（信誉分>98）"
        )
    
    comment = db.query(PostComment).filter(
        PostComment.id == comment_id,
        PostComment.post_id == post_id,
        PostComment.status == "active"
    ).first()
    
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在或已被删除")
    
    # 检查是否已投票
    existing_vote = db.query(CommentReviewerDelete).filter(
        CommentReviewerDelete.comment_id == comment_id,
        CommentReviewerDelete.reviewer_id == current_user.id
    ).first()
    
    if existing_vote:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="您已投票删除该评论")
    
    # 添加投票
    vote = CommentReviewerDelete(
        comment_id=comment_id,
        reviewer_id=current_user.id,
        reason=reason
    )
    db.add(vote)
    comment.reviewer_delete_count += 1
    db.commit()
    
    # 检查是否满足删除条件
    deleted = check_and_delete_comment_by_reviewers(comment, db, reason)
    
    return SuccessResponse(
        message=f"已投票（{comment.reviewer_delete_count}/{REVIEWER_DELETE_VOTES_REQUIRED}）" + 
                ("，该评论已被删除" if deleted else "")
    )


@router.get("/{post_id}/comments/{comment_id}/interaction-status", summary="获取评论互动状态")
async def get_comment_interaction_status(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户对评论的点赞/拉踩状态"""
    liked = db.query(CommentLike).filter(
        CommentLike.comment_id == comment_id,
        CommentLike.user_id == current_user.id
    ).first() is not None
    
    disliked = db.query(CommentDislike).filter(
        CommentDislike.comment_id == comment_id,
        CommentDislike.user_id == current_user.id
    ).first() is not None
    
    return {"liked": liked, "disliked": disliked}


# ============ 增强版删除评论 API ============

@router.delete("/{post_id}/comments/{comment_id}", response_model=SuccessResponse, summary="删除评论")
async def delete_comment(
    post_id: int,
    comment_id: int,
    reason: str = Query(None, description="删除原因（管理员删除时需要）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除评论
    - 评论作者：可直接删除自己的评论
    - 管理员：可直接删除任何评论
    - 审核员：通过 reviewer-delete 接口投票删除
    - 普通用户：通过 dislike 接口拉踩
    """
    comment = db.query(PostComment).filter(
        PostComment.id == comment_id,
        PostComment.post_id == post_id
    ).first()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在"
        )
    
    # 评论已被删除
    if comment.status == "deleted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="评论已被删除"
        )
    
    # 自己的评论 - 直接删除
    if comment.user_id == current_user.id:
        comment.status = "deleted"
        comment.delete_reason = "用户自行删除"
        
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.comments_count = max(0, post.comments_count - 1)
        
        db.commit()
        return SuccessResponse(message="评论删除成功")
    
    # 管理员 - 直接删除并通知
    if current_user.role == "admin":
        comment.status = "deleted"
        comment.delete_reason = f"管理员删除：{reason or '违规内容'}"
        
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.comments_count = max(0, post.comments_count - 1)
        
        # 创建通知
        notification = Notification(
            user_id=comment.user_id,
            type="comment_deleted",
            title="您的评论已被管理员删除",
            content=f"您的评论因违规被管理员删除。原因：{reason or '违规内容'}。惩罚：信誉分-10。原评论内容：「{comment.content[:50]}{'...' if len(comment.content) > 50 else ''}」",
            related_id=comment.id
        )
        db.add(notification)
        
        # 扣除信誉分
        profile = db.query(UserProfile).filter(UserProfile.user_id == comment.user_id).first()
        if profile:
            profile.credit_score = max(0, profile.credit_score - 10)
        
        db.commit()
        return SuccessResponse(message="评论删除成功，已通知用户")
    
    # 其他情况 - 无权删除
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="无权删除此评论。如需删除，请使用拉踩功能或联系审核员"
    )
