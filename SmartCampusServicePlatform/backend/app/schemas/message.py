from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .user import UserBrief


class MessageType(str, Enum):
    text = "text"
    image = "image"
    file = "file"


class NotificationType(str, Enum):
    system = "system"
    task = "task"
    friend = "friend"
    post = "post"
    wallet = "wallet"


# Message schemas
class MessageCreate(BaseModel):
    receiver_id: int
    content: str = Field(..., min_length=1, max_length=2000)
    type: MessageType = MessageType.text


class MessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    message_type: MessageType
    is_read: bool
    created_at: datetime
    sender: Optional[UserBrief] = None
    receiver: Optional[UserBrief] = None

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    items: List[MessageResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Conversation schemas
class ConversationResponse(BaseModel):
    user: UserBrief
    last_message: Optional[MessageResponse] = None
    unread_count: int = 0


class ConversationListResponse(BaseModel):
    items: List[ConversationResponse]
    total: int


# Notification schemas
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: NotificationType
    title: str
    content: str
    is_read: bool
    related_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


# Report schemas
class ReportType(str, Enum):
    post = "post"
    comment = "comment"
    user = "user"
    task = "task"


class ReportStatus(str, Enum):
    pending = "pending"
    resolved = "resolved"
    rejected = "rejected"


class ReportCreate(BaseModel):
    target_type: ReportType
    target_id: int
    reason: str = Field(..., min_length=1, max_length=500)


class ReportResponse(BaseModel):
    id: int
    reporter_id: int
    target_type: ReportType
    target_id: int
    reason: str
    status: ReportStatus
    created_at: datetime
    resolved_at: Optional[datetime] = None
    reporter: Optional[UserBrief] = None

    class Config:
        from_attributes = True
