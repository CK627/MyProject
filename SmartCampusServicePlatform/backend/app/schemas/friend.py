from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .user import UserBrief


class FriendRequestStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


# Friend schemas
class FriendResponse(BaseModel):
    id: int
    user_id: int
    friend_id: int
    created_at: datetime
    friend: Optional[UserBrief] = None

    class Config:
        from_attributes = True


class FriendListResponse(BaseModel):
    items: List[FriendResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Friend Request schemas
class FriendRequestCreate(BaseModel):
    to_user_id: int
    message: Optional[str] = Field(None, max_length=200)


class FriendRequestResponse(BaseModel):
    id: int
    from_user_id: int
    to_user_id: int
    status: FriendRequestStatus
    message: Optional[str] = None
    created_at: datetime
    from_user: Optional[UserBrief] = None
    to_user: Optional[UserBrief] = None

    class Config:
        from_attributes = True


class FriendRequestListResponse(BaseModel):
    items: List[FriendRequestResponse]
    total: int


# Blacklist schemas
class BlacklistCreate(BaseModel):
    blocked_user_id: int
    reason: Optional[str] = Field(None, max_length=200)


class BlacklistResponse(BaseModel):
    id: int
    user_id: int
    blocked_user_id: int
    reason: Optional[str] = None
    created_at: datetime
    blocked_user: Optional[UserBrief] = None

    class Config:
        from_attributes = True


class BlacklistListResponse(BaseModel):
    items: List[BlacklistResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
