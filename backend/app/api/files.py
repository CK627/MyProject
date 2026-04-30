from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path

from ..database import get_db
from ..models.models import User
from ..core.deps import get_current_user
from ..utils.file_manager import file_manager
from ..schemas.common import SuccessResponse


router = APIRouter(prefix="/files", tags=["文件管理"])


@router.post("/upload", summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    message_id: int = 0,  # 临时消息ID,实际应该由消息API提供
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传文件到服务器
    - 自动去重(相同文件只存储一次)
    - 支持硬链接引用计数
    """
    try:
        file_data = await file.read()
        mime_type = file.content_type or "application/octet-stream"
        
        metadata = await file_manager.save_file(
            file_data=file_data,
            message_id=message_id,
            mime_type=mime_type,
            db=db
        )
        
        return {
            "file_id": metadata.id,
            "file_hash": metadata.file_hash,
            "file_size": metadata.file_size,
            "mime_type": metadata.mime_type,
            "reference_count": metadata.reference_count
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}"
        )


@router.get("/{file_id}", summary="下载/获取文件")
async def get_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """获取文件(用于下载或预览) - 公开访问，无需认证"""
    try:
        file_path = file_manager.get_file_path(file_id, db)
        
        if not file_path or not Path(file_path).exists():
            print(f"File not found: {file_path}") # Debug log
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        return FileResponse(file_path)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件失败: {str(e)}"
        )


@router.get("/stats", summary="获取存储统计")
async def get_storage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文件存储统计信息"""
    stats = await file_manager.get_storage_stats(db)
    return stats


@router.post("/cleanup", summary="手动触发清理")
async def manual_cleanup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """手动触发过期文件清理"""
    deleted_count = await file_manager.cleanup_expired_files(db)
    return SuccessResponse(
        message=f"已清理 {deleted_count} 个过期文件"
    )
