from pydantic import BaseModel
from typing import Optional, Any


class ResponseBase(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20


class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "操作成功"


class ErrorResponse(BaseModel):
    code: int
    message: str
    detail: Optional[str] = None
