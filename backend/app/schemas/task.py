from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .user import UserBrief


class TaskCategory(str, Enum):
    delivery = "delivery"
    purchase = "purchase"
    study = "study"
    errand = "errand"
    other = "other"


class TaskStatus(str, Enum):
    open = "open"
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class ApplicationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


# Task schemas
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    category: TaskCategory
    reward: float = Field(..., ge=0)
    location: Optional[str] = Field(None, max_length=200)
    deadline: Optional[datetime] = None


class TaskCreate(TaskBase):
    private_info: Optional[str] = Field(None, max_length=500, description="私密信息，仅接单者可见（如快递码、手机尾号等）")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    category: Optional[TaskCategory] = None
    reward: Optional[float] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=200)
    deadline: Optional[datetime] = None
    status: Optional[TaskStatus] = None


class TaskResponse(TaskBase):
    id: int
    publisher_id: int
    assignee_id: Optional[int] = None
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    publisher: Optional[UserBrief] = None
    assignee: Optional[UserBrief] = None
    application_count: int = 0
    private_info: Optional[str] = None  # 私密信息，仅接单者和发布者可见

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    items: List[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Task Application schemas
class ApplicationCreate(BaseModel):
    message: Optional[str] = Field(None, max_length=500)


class ApplicationResponse(BaseModel):
    id: int
    task_id: int
    applicant_id: int
    status: ApplicationStatus
    message: Optional[str] = None
    created_at: datetime
    applicant: Optional[UserBrief] = None
    priority_score: Optional[int] = None  # 优先分 = (信誉分 + 好评率 * 100) // 2

    class Config:
        from_attributes = True


# Task Review schemas
class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)


class ReviewResponse(BaseModel):
    id: int
    task_id: int
    reviewer_id: int
    reviewee_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    reviewer: Optional[UserBrief] = None
    reviewee: Optional[UserBrief] = None

    class Config:
        from_attributes = True
