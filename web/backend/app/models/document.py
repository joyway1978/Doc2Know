"""文档数据模型"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """文档处理状态"""
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentBase(BaseModel):
    """文档基础模型"""
    filename: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    file_type: str = Field(..., description="文件类型（docx/pdf等）")


class DocumentCreate(DocumentBase):
    """文档创建请求模型"""
    pass


class DocumentUpdate(BaseModel):
    """文档更新请求模型"""
    status: Optional[DocumentStatus] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    error_message: Optional[str] = None


class DocumentResponse(DocumentBase):
    """文档响应模型"""
    id: str = Field(..., description="文档唯一ID")
    status: DocumentStatus = Field(default=DocumentStatus.PENDING)
    progress: int = Field(default=0, ge=0, le=100)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None
    output_file: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentDetailResponse(DocumentResponse):
    """文档详情响应模型"""
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source_path: Optional[str] = None


class DocumentListResponse(BaseModel):
    """文档列表响应模型"""
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int


class KnowledgeItem(BaseModel):
    """知识库条目模型"""
    id: str = Field(..., description="知识条目ID")
    title: str = Field(..., description="文档标题")
    summary: str = Field(..., description="文档摘要")
    tags: List[str] = Field(default_factory=list)
    file_path: str = Field(..., description="文件路径")
    updated_at: str = Field(..., description="更新时间")
    source: Optional[str] = Field(None, description="源文件")


class KnowledgeListResponse(BaseModel):
    """知识库列表响应模型"""
    items: List[KnowledgeItem]
    total: int


class ProcessingProgress(BaseModel):
    """处理进度模型（用于SSE）"""
    document_id: str
    status: DocumentStatus
    progress: int = Field(..., ge=0, le=100)
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class UploadResponse(BaseModel):
    """文件上传响应模型"""
    success: bool
    document_id: str
    message: str


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class ConfigResponse(BaseModel):
    """配置响应模型"""
    llm: Dict[str, Any]
    paths: Dict[str, str]
    processing: Dict[str, int]


class ConfigUpdateRequest(BaseModel):
    """配置更新请求模型"""
    llm: Optional[Dict[str, Any]] = None
    paths: Optional[Dict[str, str]] = None
    processing: Optional[Dict[str, int]] = None


class StatsResponse(BaseModel):
    """统计信息响应模型"""
    total_documents: int
    completed: int
    processing: int
    failed: int
    total_knowledge_items: int
    last_updated: Optional[datetime] = None
