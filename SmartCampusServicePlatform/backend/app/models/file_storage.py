from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from ..database import Base


class FileMetadata(Base):
    """文件元数据表 - 用于硬链接和引用计数"""
    __tablename__ = "file_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    file_hash = Column(String(64), unique=True, index=True, nullable=False)  # 文件SHA256哈希
    file_path = Column(String(500), nullable=False)  # 物理存储路径
    file_size = Column(Integer, nullable=False)  # 文件大小(字节)
    mime_type = Column(String(100))  # MIME类型
    reference_count = Column(Integer, default=1, nullable=False)  # 引用计数
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    

class FileReference(Base):
    """文件引用表 - 记录哪些消息引用了哪些文件"""
    __tablename__ = "file_references"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, index=True, nullable=False)  # 对应FileMetadata.id
    message_id = Column(Integer, index=True, nullable=False)  # 对应Message.id
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DeletedFile(Base):
    """待删除文件队列 - 软删除后的文件"""
    __tablename__ = "deleted_files"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, index=True, nullable=False)  # FileMetadata.id
    file_path = Column(String(500), nullable=False)  # 物理路径
    deleted_at = Column(DateTime(timezone=True), server_default=func.now())
    scheduled_deletion = Column(DateTime(timezone=True), nullable=False)  # 计划删除时间
    is_deleted = Column(Boolean, default=False)  # 是否已物理删除
