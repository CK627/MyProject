import os
import hashlib
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, BinaryIO
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.file_storage import FileMetadata, FileReference, DeletedFile


class FileStorageManager:
    """文件存储管理器 - 实现硬链接和异步删除"""
    
    def __init__(self, base_storage_path: str = "./storage/files"):
        self.base_path = Path(base_storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    def _calculate_hash(self, file_data: bytes) -> str:
        """计算文件SHA256哈希"""
        return hashlib.sha256(file_data).hexdigest()
    
    def _get_storage_path(self, file_hash: str) -> Path:
        """根据哈希值生成存储路径(分层存储)"""
        # 使用哈希前4位分层: ab/cd/abcdef...
        return self.base_path / file_hash[:2] / file_hash[2:4] / file_hash
    
    async def save_file(
        self, 
        file_data: bytes, 
        message_id: int,
        mime_type: str,
        db: Session
    ) -> FileMetadata:
        """
        保存文件(支持硬链接去重)
        - 如果文件已存在(相同哈希),增加引用计数
        - 如果文件不存在,创建新文件
        """
        file_hash = self._calculate_hash(file_data)
        file_size = len(file_data)
        
        # 检查是否已存在
        existing = db.query(FileMetadata).filter(
            FileMetadata.file_hash == file_hash
        ).first()
        
        if existing:
            # 文件已存在,增加引用计数
            existing.reference_count += 1
            existing.last_accessed = datetime.utcnow()
            
            # 创建文件引用记录
            ref = FileReference(
                file_id=existing.id,
                message_id=message_id
            )
            db.add(ref)
            db.commit()
            db.refresh(existing)
            return existing
        
        # 新文件,保存到磁盘
        storage_path = self._get_storage_path(file_hash)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(storage_path, 'wb') as f:
            f.write(file_data)
        
        # 创建元数据记录
        metadata = FileMetadata(
            file_hash=file_hash,
            file_path=str(storage_path),
            file_size=file_size,
            mime_type=mime_type,
            reference_count=1
        )
        db.add(metadata)
        db.flush()
        
        # 创建文件引用记录
        ref = FileReference(
            file_id=metadata.id,
            message_id=message_id
        )
        db.add(ref)
        db.commit()
        db.refresh(metadata)
        
        return metadata
    
    async def decrease_reference(
        self, 
        message_id: int, 
        db: Session,
        soft_delete_hours: int = 24
    ) -> None:
        """
        减少文件引用计数(当消息被删除时)
        - 引用计数降为0时,软删除文件
        - 加入异步删除队列
        """
        # 查找该消息引用的所有文件
        refs = db.query(FileReference).filter(
            FileReference.message_id == message_id
        ).all()
        
        for ref in refs:
            metadata = db.query(FileMetadata).filter(
                FileMetadata.id == ref.file_id
            ).first()
            
            if not metadata:
                continue
            
            # 减少引用计数
            metadata.reference_count -= 1
            
            if metadata.reference_count <= 0:
                # 软删除:加入删除队列
                scheduled_time = datetime.utcnow() + timedelta(hours=soft_delete_hours)
                deleted_file = DeletedFile(
                    file_id=metadata.id,
                    file_path=metadata.file_path,
                    scheduled_deletion=scheduled_time
                )
                db.add(deleted_file)
                
                # 删除元数据记录
                db.delete(metadata)
            
            # 删除引用记录
            db.delete(ref)
        
        db.commit()
    
    async def cleanup_expired_files(self, db: Session) -> int:
        """
        清理过期文件(异步删除任务)
        - 物理删除已过计划删除时间的文件
        - 返回删除的文件数量
        """
        now = datetime.utcnow()
        
        # 查询需要删除的文件
        expired = db.query(DeletedFile).filter(
            and_(
                DeletedFile.scheduled_deletion <= now,
                DeletedFile.is_deleted == False
            )
        ).all()
        
        deleted_count = 0
        
        for file_record in expired:
            try:
                # 物理删除文件
                file_path = Path(file_record.file_path)
                if file_path.exists():
                    file_path.unlink()
                    
                    # 尝试删除空目录
                    try:
                        file_path.parent.rmdir()
                        file_path.parent.parent.rmdir()
                    except OSError:
                        pass  # 目录非空,忽略
                
                # 标记为已删除
                file_record.is_deleted = True
                deleted_count += 1
                
            except Exception as e:
                print(f"删除文件失败 {file_record.file_path}: {e}")
        
        db.commit()
        return deleted_count
    
    def get_file_path(self, file_id: int, db: Session) -> Optional[str]:
        """获取文件物理路径"""
        metadata = db.query(FileMetadata).filter(
            FileMetadata.id == file_id
        ).first()
        
        if metadata:
            metadata.last_accessed = datetime.utcnow()
            db.commit()
            
            # Fix path separators to be OS-independent, especially for paths saved on Windows but read on Mac
            import os
            normalized_path = str(metadata.file_path).replace('\\', '/')
            
            # Since the path is relative, we should ensure it resolves correctly from backend root
            if normalized_path.startswith('storage/files/'):
                # Ensure the path is relative to the current working directory of the FastAPI app
                normalized_path = os.path.join(os.getcwd(), normalized_path)
            
            return normalized_path
        
        return None
    
    async def get_storage_stats(self, db: Session) -> dict:
        """获取存储统计信息"""
        from sqlalchemy import func
        
        total_files = db.query(FileMetadata).count()
        total_size = db.query(FileMetadata).with_entities(
            func.sum(FileMetadata.file_size)
        ).scalar() or 0
        
        pending_delete = db.query(DeletedFile).filter(
            DeletedFile.is_deleted == False
        ).count()
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "pending_deletion": pending_delete
        }


# 全局文件管理器实例
file_manager = FileStorageManager()
