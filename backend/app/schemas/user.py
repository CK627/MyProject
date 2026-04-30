from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Union
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    banned = "banned"


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"


# Base schema
class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


# Create schema
class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=50)
    role: UserRole = UserRole.student


# Update schema
class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    avatar: Optional[str] = Field(None, description="Base64 encoded image data or URL")


# Response schema
class UserResponse(UserBase):
    id: int
    avatar: Optional[str] = None
    role: UserRole
    status: UserStatus
    online_status: Optional[str] = None
    last_active: Optional[datetime] = None
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


# Brief user info for lists
class UserBrief(BaseModel):
    id: int
    name: str
    avatar: Optional[str] = None
    role: UserRole

    class Config:
        from_attributes = True


# User profile schemas
class UserProfileBase(BaseModel):
    student_id: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    major: Optional[str] = Field(None, max_length=100)
    grade: Optional[str] = Field(None, max_length=20)
    gender: Optional[Gender] = None
    birthday: Optional[str] = None  # 接受字符串格式的日期
    bio: Optional[str] = Field(None, max_length=500)
    dormitory: Optional[str] = Field(None, max_length=100)


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int
    enroll_year: Optional[int] = None  # 数据库字段名
    birthday: Optional[Union[str, datetime]] = None  # 兼容datetime和str
    
    class Config:
        from_attributes = True


# Full user with profile
class UserWithProfile(UserResponse):
    profile: Optional[UserProfileResponse] = None

    class Config:
        from_attributes = True
