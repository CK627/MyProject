from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AnnouncementType(str, Enum):
    notice = "notice"
    news = "news"
    activity = "activity"
    emergency = "emergency"


class AnnouncementStatus(str, Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


# Announcement schemas
class AnnouncementBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    type: AnnouncementType
    is_pinned: bool = False


class AnnouncementCreate(AnnouncementBase):
    status: AnnouncementStatus = AnnouncementStatus.published


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    type: Optional[AnnouncementType] = None
    is_pinned: Optional[bool] = None
    status: Optional[AnnouncementStatus] = None


class AnnouncementResponse(BaseModel):
    id: int
    title: str
    content: str
    type: str
    is_pinned: bool = False
    publisher_id: Optional[int] = None
    status: str
    view_count: int
    publish_date: Optional[datetime] = None
    expire_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_read: bool = False

    class Config:
        from_attributes = True


class AnnouncementListResponse(BaseModel):
    items: List[AnnouncementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# School Info schemas
class SchoolInfoResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo: Optional[str] = None
    founded_year: Optional[int] = None

    class Config:
        from_attributes = True


# Department schemas
class DepartmentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    student_count: Optional[int] = None
    ranking: Optional[str] = None

    class Config:
        from_attributes = True


# Facility schemas
class FacilityType(str, Enum):
    library = "library"
    canteen = "canteen"
    gym = "gym"
    dormitory = "dormitory"
    teaching = "teaching"
    lab = "lab"
    other = "other"


class FacilityResponse(BaseModel):
    id: int
    name: str
    type: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    open_time: Optional[str] = None
    image: Optional[str] = None

    class Config:
        from_attributes = True
