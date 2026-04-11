from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .user import UserBrief


class PostStatus(str, Enum):
    draft = "draft"
    published = "published"
    hidden = "hidden"
    deleted = "deleted"


# Post Tag schemas
class PostTagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class PostTagCreate(PostTagBase):
    pass


class PostTagResponse(PostTagBase):
    id: int

    class Config:
        from_attributes = True


# Post schemas
class PostBase(BaseModel):
    content: str = Field(..., min_length=1)
    images: Optional[str] = None  # JSON string of image URLs
    is_anonymous: bool = False


class PostCreate(PostBase):
    tag_ids: Optional[List[int]] = None


class PostUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    images: Optional[str] = None
    is_anonymous: Optional[bool] = None
    status: Optional[PostStatus] = None
    tag_ids: Optional[List[int]] = None


class PostResponse(PostBase):
    id: int
    user_id: int
    status: str
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    created_at: datetime
    updated_at: datetime
    author: Optional[UserBrief] = None
    tags: List[PostTagResponse] = []

    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    items: List[PostResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Comment schemas
class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class CommentCreate(CommentBase):
    parent_id: Optional[int] = None


class CommentResponse(CommentBase):
    id: int
    post_id: int
    user_id: int
    parent_id: Optional[int] = None
    likes_count: int = 0
    dislikes_count: int = 0
    reviewer_delete_count: int = 0
    status: str = "active"
    delete_reason: Optional[str] = None
    created_at: datetime
    user: Optional[UserBrief] = None

    class Config:
        from_attributes = True


# Like schemas
class LikeResponse(BaseModel):
    id: int
    post_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
