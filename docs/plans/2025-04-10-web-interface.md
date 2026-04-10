# Doc2Know Web Interface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 Doc2Know CLI 工具构建一个现代化的 Web 界面，包含 Python FastAPI 后端和 Next.js + Tailwind CSS 前端

**Architecture:**
- 后端: FastAPI REST API，复用现有 CLI 核心逻辑（parser/analyzer/generator/indexer）
- 前端: Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui
- 通信: REST API + Server-Sent Events (SSE) 用于实时进度推送

**Tech Stack:**
- Backend: Python 3.9+, FastAPI, Uvicorn, python-multipart
- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS, shadcn/ui, Axios

---

## 目录结构规划

```
/Users/zhongwei9/Documents/gitlab/joyway1978/Doc2Know/
├── doc2know/                    # 现有CLI核心模块
├── web/                         # 新增Web目录
│   ├── backend/                 # FastAPI后端
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py          # FastAPI入口
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── documents.py # 文档处理API
│   │   │   │   ├── knowledge.py # 知识库API
│   │   │   │   └── config.py    # 配置API
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   └── processor.py # 文档处理封装
│   │   │   └── models/
│   │   │       ├── __init__.py
│   │   │       ├── document.py  # 数据模型
│   │   │       └── responses.py
│   │   ├── requirements.txt
│   │   └── README.md
│   └── frontend/                # Next.js前端
│       ├── app/                 # Next.js 14 App Router
│       │   ├── layout.tsx
│       │   ├── page.tsx         # 首页
│       │   ├── documents/
│       │   │   └── page.tsx     # 文档管理页
│       │   └── knowledge/
│       │       └── page.tsx     # 知识库浏览页
│       ├── components/
│       │   ├── ui/              # shadcn/ui组件
│       │   ├── upload.tsx       # 文件上传组件
│       │   ├── document-list.tsx
│       │   └── progress.tsx     # 进度显示
│       ├── lib/
│       │   ├── api.ts           # API客户端
│       │   └── utils.ts
│       ├── types/
│       │   └── index.ts         # TypeScript类型定义
│       ├── public/
│       ├── package.json
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       └── next.config.js
├── docs/plans/
│   └── 2025-04-10-web-interface.md  # 本计划
└── package.json                 # 根目录启动脚本
```

---

## Task 1: 创建后端基础结构

**Files:**
- Create: `web/backend/requirements.txt`
- Create: `web/backend/app/__init__.py`
- Create: `web/backend/app/main.py`
- Create: `web/backend/app/models/__init__.py`
- Create: `web/backend/app/models/document.py`
- Create: `web/backend/app/api/__init__.py`

**Step 1: 创建后端依赖文件**

```bash
mkdir -p web/backend/app/{api,core,models}
touch web/backend/app/__init__.py
touch web/backend/app/api/__init__.py
touch web/backend/app/core/__init__.py
touch web/backend/app/models/__init__.py
```

**Step 2: 编写 requirements.txt**

```text
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-docx>=0.8.11
openai>=1.0.0
pyyaml>=6.0
click>=8.0
tenacity>=8.0.0
aiofiles>=23.0.0
aiosqlite>=0.19.0
```

**Step 3: 编写数据模型 (app/models/document.py)**

```python
"""数据模型定义"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """文档处理状态"""
    PENDING = "pending"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentUpload(BaseModel):
    """文档上传请求"""
    filename: str
    content_type: str


class DocumentResponse(BaseModel):
    """文档响应模型"""
    id: str = Field(..., description="文档ID")
    filename: str = Field(..., description="原始文件名")
    status: DocumentStatus = Field(..., description="处理状态")
    title: Optional[str] = Field(None, description="文档标题")
    summary: Optional[str] = Field(None, description="文档摘要")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    output_file: Optional[str] = Field(None, description="生成的Markdown文件路径")
    error_message: Optional[str] = Field(None, description="错误信息")

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    total: int
    documents: List[DocumentResponse]


class KnowledgeItem(BaseModel):
    """知识库条目"""
    title: str
    file_path: str
    summary: str
    tags: List[str]
    updated_at: str


class KnowledgeIndexResponse(BaseModel):
    """知识库索引响应"""
    total: int
    items: List[KnowledgeItem]
    generated_at: datetime


class ProcessingProgress(BaseModel):
    """处理进度"""
    document_id: str
    status: DocumentStatus
    progress: int = Field(..., ge=0, le=100, description="进度百分比")
    message: str
    timestamp: datetime


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    llm: Optional[Dict[str, Any]] = None
    paths: Optional[Dict[str, str]] = None
    processing: Optional[Dict[str, int]] = None


class ConfigResponse(BaseModel):
    """配置响应"""
    llm: Dict[str, Any]
    paths: Dict[str, str]
    processing: Dict[str, int]
```

**Step 4: Commit**

```bash
git add web/backend/
git commit -m "feat(web): initialize FastAPI backend structure with models"
```

---

## Task 2: 实现后端核心API

**Files:**
- Create: `web/backend/app/main.py`
- Create: `web/backend/app/api/documents.py`
- Create: `web/backend/app/core/processor.py`

**Step 1: 编写主入口 (app/main.py)**

```python
"""FastAPI主入口"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.backend.app.api import documents, knowledge, config


from web.backend.app.core.database import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时创建必要的目录和数据库
    output_dir = Path("output")
    raw_dir = Path("raw_docs")
    upload_dir = Path("uploads")

    for dir_path in [output_dir, raw_dir, upload_dir, output_dir / "topics"]:
        dir_path.mkdir(parents=True, exist_ok=True)

    # 初始化数据库
    await init_database()

    yield

    # 关闭时的清理（如果需要）


app = FastAPI(
    title="Doc2Know Web API",
    description="文档转知识库 Web API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(config.router, prefix="/api/config", tags=["config"])

# 静态文件服务（用于访问生成的Markdown）
if Path("output").exists():
    app.mount("/output", StaticFiles(directory="output"), name="output")


@app.get("/")
async def root():
    """根路径"""
    return {"message": "Doc2Know Web API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
```

**Step 2: 添加数据库模块 (app/core/database.py)**

```python
"""SQLite数据库管理 - 文档状态持久化"""

import aiosqlite
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

DATABASE_PATH = Path("web/backend/data/documents.db")


async def init_database():
    """初始化数据库"""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                message TEXT DEFAULT '',
                title TEXT,
                summary TEXT,
                tags TEXT,  -- JSON array
                output_file TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def create_document(doc_id: str, filename: str) -> Dict[str, Any]:
    """创建文档记录"""
    doc = {
        "id": doc_id,
        "filename": filename,
        "status": "pending",
        "progress": 0,
        "message": "等待处理",
        "title": None,
        "summary": None,
        "tags": "[]",
        "output_file": None,
        "error_message": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        await db.execute(
            """INSERT INTO documents
                (id, filename, status, progress, message, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (doc_id, filename, "pending", 0, "等待处理", "[]",
             doc["created_at"], doc["updated_at"])
        )
        await db.commit()

    return doc


async def update_document(doc_id: str, **kwargs):
    """更新文档记录"""
    allowed_fields = {"status", "progress", "message", "title", "summary",
                      "tags", "output_file", "error_message"}

    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not updates:
        return

    # 处理tags列表转JSON
    if "tags" in updates and isinstance(updates["tags"], list):
        updates["tags"] = json.dumps(updates["tags"], ensure_ascii=False)

    updates["updated_at"] = datetime.now().isoformat()

    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [doc_id]
        await db.execute(
            f"UPDATE documents SET {set_clause} WHERE id = ?",
            values
        )
        await db.commit()


async def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """获取文档记录"""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        async with db.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None

            columns = [description[0] for description in cursor.description]
            doc = dict(zip(columns, row))

            # 解析tags JSON
            if doc.get("tags"):
                try:
                    doc["tags"] = json.loads(doc["tags"])
                except json.JSONDecodeError:
                    doc["tags"] = []

            return doc


async def list_documents(limit: int = 100) -> List[Dict[str, Any]]:
    """列出所有文档"""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        async with db.execute(
            "SELECT * FROM documents ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]

            docs = []
            for row in rows:
                doc = dict(zip(columns, row))
                if doc.get("tags"):
                    try:
                        doc["tags"] = json.loads(doc["tags"])
                    except json.JSONDecodeError:
                        doc["tags"] = []
                docs.append(doc)

            return docs


async def delete_document(doc_id: str) -> bool:
    """删除文档记录"""
    async with aiosqlite.connect(str(DATABASE_PATH)) as db:
        cursor = await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        await db.commit()
        return cursor.rowcount > 0
```

**Step 3: 编写文档处理核心 (app/core/processor.py)**

```python
"""文档处理封装 - 桥接CLI核心与Web API"""

import uuid
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from fastapi import BackgroundTasks

# 导入CLI核心模块
import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from doc2know.config import Config, ConfigError
from doc2know.parser import DocxParser, PdfParser
from doc2know.analyzer import LLMAnalyzer
from doc2know.generator import MarkdownGenerator
from doc2know.indexer import Indexer

from web.backend.app.core.database import (
    create_document, update_document, get_document, list_documents, delete_document
)

# 配置日志
logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """文档处理错误"""
    pass


class DocumentProcessor:
    """文档处理器 - Web版本"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.config = Config()
        self.docx_parser = DocxParser()
        self.pdf_parser = PdfParser()
        self.analyzer = LLMAnalyzer(self.config)
        self.generator = MarkdownGenerator(self.config.output_dir)
        self.indexer = Indexer(self.config.output_dir)

        self._progress_callbacks: Dict[str, Callable] = {}

        self._initialized = True

    def register_progress_callback(self, doc_id: str, callback: Callable):
        """注册进度回调"""
        self._progress_callbacks[doc_id] = callback

    async def _update_progress(self, doc_id: str, status: str, progress: int, message: str):
        """更新进度"""
        await update_document(doc_id, status=status, progress=progress, message=message)

        # 触发回调
        if doc_id in self._progress_callbacks:
            try:
                self._progress_callbacks[doc_id]({
                    "document_id": doc_id,
                    "status": status,
                    "progress": progress,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception:
                pass

    async def process_document(
        self,
        file_path: str,
        original_filename: str,
        background_tasks: BackgroundTasks
    ) -> str:
        """
        异步处理文档 - 使用FastAPI BackgroundTasks

        Returns:
            文档ID
        """
        doc_id = str(uuid.uuid4())

        # 创建文档记录
        await create_document(doc_id, original_filename)

        # 使用BackgroundTasks后台处理
        background_tasks.add_task(
            self._process_in_background,
            doc_id,
            file_path,
            original_filename
        )

        return doc_id

    async def _process_in_background(self, doc_id: str, file_path: str, original_filename: str):
        """后台处理文档"""
        try:
            logger.info(f"开始处理文档: {doc_id} - {original_filename}")

            # 1. 解析
            await self._update_progress(doc_id, "parsing", 10, "正在解析文档...")

            ext = Path(file_path).suffix.lower()
            if ext == '.pdf':
                parsed_content = self.pdf_parser.parse(file_path)
            else:
                parsed_content = self.docx_parser.parse(file_path)

            # 2. 分析
            await self._update_progress(doc_id, "analyzing", 40, "AI正在分析内容...")
            analysis_result = self.analyzer.analyze(parsed_content)

            # 3. 生成
            await self._update_progress(doc_id, "generating", 70, "正在生成知识库...")
            output_file = self.generator.generate(analysis_result, file_path)

            # 4. 更新索引
            await self._update_progress(doc_id, "generating", 90, "正在更新索引...")
            self.indexer.update_index()

            # 完成
            await update_document(
                doc_id,
                status="completed",
                progress=100,
                message="处理完成",
                output_file=output_file,
                title=analysis_result.get("title"),
                summary=analysis_result.get("summary"),
                tags=analysis_result.get("tags", [])
            )

            logger.info(f"文档处理完成: {doc_id}")

        except Exception as e:
            logger.error(f"文档处理失败 {doc_id}: {str(e)}")
            await update_document(
                doc_id,
                status="failed",
                progress=0,
                message=f"处理失败: {str(e)}",
                error_message=str(e)
            )

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取文档状态"""
        return await get_document(doc_id)

    async def list_documents(self) -> list:
        """列出所有文档"""
        return await list_documents()

    async def delete_document(self, doc_id: str) -> bool:
        """删除文档记录"""
        return await delete_document(doc_id)


# 全局处理器实例
processor = DocumentProcessor()
```

**Step 3: 编写文档API (app/api/documents.py)**

```python
"""文档处理API路由"""

import os
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import asyncio

from web.backend.app.models.document import (
    DocumentResponse, DocumentListResponse, ProcessingProgress
)
from web.backend.app.core.processor import processor

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 文件大小限制: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    上传并处理文档

    支持格式: .docx, .doc, .pdf
    最大文件大小: 50MB
    """
    # 验证文件类型
    allowed_extensions = {'.docx', '.doc', '.pdf'}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}. 仅支持: {', '.join(allowed_extensions)}"
        )

    # 读取并验证文件大小
    try:
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大: {len(contents) / 1024 / 1024:.1f}MB. 最大允许: 50MB"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件读取失败: {str(e)}")

    # 保存上传文件
    import uuid
    temp_id = str(uuid.uuid4())[:8]
    safe_filename = f"{temp_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    # 异步处理文档 - 使用BackgroundTasks
    doc_id = await processor.process_document(
        str(file_path),
        file.filename,
        background_tasks
    )

    doc = await processor.get_document(doc_id)
    return DocumentResponse(**doc)


@router.get("/", response_model=DocumentListResponse)
async def list_documents():
    """获取所有文档列表"""
    docs = await processor.list_documents()
    return DocumentListResponse(
        total=len(docs),
        documents=[DocumentResponse(**doc) for doc in docs]
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    """获取单个文档详情"""
    doc = await processor.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return DocumentResponse(**doc)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档"""
    success = await processor.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"message": "文档已删除"}


@router.get("/{doc_id}/progress")
async def get_progress(doc_id: str):
    """
    获取文档处理进度（SSE流）

    返回Server-Sent Events流，实时推送进度更新
    """
    doc = await processor.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    async def event_generator():
        """生成SSE事件"""
        last_progress = -1
        max_iterations = 300  # 最多等待5分钟

        for _ in range(max_iterations):
            doc = await processor.get_document(doc_id)
            if not doc:
                break

            current_progress = doc.get("progress", 0)

            # 只在进度变化时发送
            if current_progress != last_progress:
                last_progress = current_progress
                yield f"data: {{
                    'document_id': '{doc_id}',
                    'status': '{doc.get('status')}',
                    'progress': {current_progress},
                    'message': '{doc.get('message', '')}'
                }}\n\n"

            # 如果已完成或失败，结束流
            if doc.get("status") in ["completed", "failed"]:
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

**Step 4: Commit**

```bash
git add web/backend/app/
git commit -m "feat(web): implement FastAPI backend with document processing API"
```

---

## Task 3: 实现知识库和配置API

**Files:**
- Create: `web/backend/app/api/knowledge.py`
- Create: `web/backend/app/api/config.py`

**Step 1: 编写知识库API (app/api/knowledge.py)**

```python
"""知识库API路由"""

from pathlib import Path
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from web.backend.app.models.document import KnowledgeIndexResponse, KnowledgeItem

# 导入Indexer
import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from doc2know.indexer import Indexer
from doc2know.config import Config

router = APIRouter()


def get_indexer() -> Indexer:
    """获取Indexer实例"""
    config = Config()
    return Indexer(config.output_dir)


@router.get("/", response_model=KnowledgeIndexResponse)
async def get_knowledge_index():
    """获取知识库索引"""
    try:
        config = Config()
        output_dir = Path(config.output_dir)
        topics_dir = output_dir / "topics"

        if not topics_dir.exists():
            return KnowledgeIndexResponse(
                total=0,
                items=[],
                generated_at=datetime.now()
            )

        # 扫描所有markdown文件
        items = []
        for md_file in sorted(topics_dir.glob("*.md")):
            if md_file.name == "index.md":
                continue

            # 提取元数据
            indexer = get_indexer()
            metadata = indexer._extract_metadata(str(md_file))

            if metadata:
                stat = md_file.stat()
                items.append(KnowledgeItem(
                    title=metadata.get("title", "未命名"),
                    file_path=f"topics/{md_file.name}",
                    summary=metadata.get("summary", "")[:100],
                    tags=metadata.get("tags", []),
                    updated_at=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
                ))

        return KnowledgeIndexResponse(
            total=len(items),
            items=items,
            generated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识库失败: {str(e)}")


@router.get("/items/{item_path:path}")
async def get_knowledge_item(item_path: str):
    """获取单个知识库条目内容"""
    try:
        config = Config()
        file_path = Path(config.output_dir) / item_path

        # 安全检查：确保在output目录内
        real_path = file_path.resolve()
        output_real = Path(config.output_dir).resolve()

        if not str(real_path).startswith(str(output_real)):
            raise HTTPException(status_code=403, detail="访问被拒绝")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        content = file_path.read_text(encoding="utf-8")
        return {"content": content, "path": item_path}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


@router.post("/reindex")
async def reindex_knowledge():
    """手动触发重新索引"""
    try:
        indexer = get_indexer()
        indexer.update_index()
        return {"message": "索引已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"索引更新失败: {str(e)}")
```

**Step 2: 编写配置API (app/api/config.py)**

```python
"""配置API路由"""

from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from web.backend.app.models.document import ConfigResponse, ConfigUpdateRequest

import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from doc2know.config import Config, ConfigError

router = APIRouter()


@router.get("/", response_model=ConfigResponse)
async def get_config():
    """获取当前配置"""
    try:
        config = Config()
        return ConfigResponse(
            llm=config.llm,
            paths=config.paths,
            processing=config.processing
        )
    except ConfigError as e:
        # 如果配置错误，返回默认配置
        return ConfigResponse(
            llm={
                "base_url": "https://api.openai.com/v1",
                "api_key": "",
                "model": "gpt-3.5-turbo"
            },
            paths={
                "raw_dir": "./raw_docs",
                "output_dir": "./output"
            },
            processing={
                "chunk_size": 4000,
                "max_concurrent": 3
            }
        )


@router.post("/")
async def update_config(config_update: ConfigUpdateRequest):
    """更新配置（保存到config.yaml）"""
    try:
        # 读取现有配置
        config = Config()
        config_dict = config.to_dict()

        # 更新配置
        if config_update.llm:
            config_dict["llm"].update(config_update.llm)
        if config_update.paths:
            config_dict["paths"].update(config_update.paths)
        if config_update.processing:
            config_dict["processing"].update(config_update.processing)

        # 写入config.yaml
        import yaml
        config_path = Path("config.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, allow_unicode=True, sort_keys=False)

        return {"message": "配置已更新"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置更新失败: {str(e)}")


@router.get("/validate")
async def validate_config():
    """验证当前配置"""
    try:
        config = Config()
        config.validate()
        return {"valid": True, "message": "配置有效"}
    except ConfigError as e:
        return {"valid": False, "message": str(e)}
```

**Step 3: Commit**

```bash
git add web/backend/app/api/
git commit -m "feat(web): add knowledge base and config API endpoints"
```

---

## Task 4: 创建Next.js前端基础结构

**Files:**
- Create: `web/frontend/package.json`
- Create: `web/frontend/tsconfig.json`
- Create: `web/frontend/tailwind.config.ts`
- Create: `web/frontend/next.config.js`

**Step 1: 创建前端目录和配置文件**

```bash
mkdir -p web/frontend/app/{documents,knowledge}
mkdir -p web/frontend/components/ui
mkdir -p web/frontend/lib
mkdir -p web/frontend/types
mkdir -p web/frontend/public
```

**Step 2: 编写 package.json**

```json
{
  "name": "doc2know-web",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0",
    "lucide-react": "^0.294.0",
    "@radix-ui/react-slot": "^1.0.2",
    "@radix-ui/react-progress": "^1.0.3",
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-dropdown-menu": "^2.0.6",
    "react-dropzone": "^14.2.3"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.3.6"
  }
}
```

**Step 3: 编写 tsconfig.json**

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

**Step 4: 编写 tailwind.config.ts**

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
}

export default config
```

**Step 5: 编写 next.config.js**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig
```

**Step 6: 编写 lib/utils.ts**

```typescript
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

**Step 7: 编写全局样式 (app/globals.css)**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

**Step 8: Commit**

```bash
git add web/frontend/
git commit -m "feat(web): initialize Next.js frontend structure with Tailwind CSS"
```

---

## Task 5: 实现前端类型定义和API客户端

**Files:**
- Create: `web/frontend/types/index.ts`
- Create: `web/frontend/lib/api.ts`

**Step 1: 编写类型定义 (types/index.ts)**

```typescript
"""类型定义"""

export interface Document {
  id: string;
  filename: string;
  status: 'pending' | 'parsing' | 'analyzing' | 'generating' | 'completed' | 'failed';
  title?: string;
  summary?: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  output_file?: string;
  error_message?: string;
}

export interface DocumentListResponse {
  total: number;
  documents: Document[];
}

export interface KnowledgeItem {
  title: string;
  file_path: string;
  summary: string;
  tags: string[];
  updated_at: string;
}

export interface KnowledgeIndexResponse {
  total: number;
  items: KnowledgeItem[];
  generated_at: string;
}

export interface ProcessingProgress {
  document_id: string;
  status: string;
  progress: number;
  message: string;
  timestamp: string;
}

export interface Config {
  llm: {
    base_url: string;
    api_key: string;
    model: string;
  };
  paths: {
    raw_dir: string;
    output_dir: string;
  };
  processing: {
    chunk_size: number;
    max_concurrent: number;
  };
}
```

**Step 2: 编写API客户端 (lib/api.ts)**

```typescript
"""API客户端"""

import axios, { AxiosInstance } from 'axios';
import type {
  Document,
  DocumentListResponse,
  KnowledgeIndexResponse,
  KnowledgeItem,
  Config,
  ProcessingProgress
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // 文档API
  async uploadDocument(file: File, onProgress?: (progress: number) => void): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post<Document>('/api/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });

    return response.data;
  }

  async listDocuments(): Promise<DocumentListResponse> {
    const response = await this.client.get<DocumentListResponse>('/api/documents/');
    return response.data;
  }

  async getDocument(docId: string): Promise<Document> {
    const response = await this.client.get<Document>(`/api/documents/${docId}`);
    return response.data;
  }

  async deleteDocument(docId: string): Promise<void> {
    await this.client.delete(`/api/documents/${docId}`);
  }

  subscribeToProgress(docId: string, onProgress: (progress: ProcessingProgress) => void): () => void {
    const eventSource = new EventSource(`${API_BASE_URL}/api/documents/${docId}/progress`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onProgress(data);
      } catch (error) {
        console.error('Failed to parse progress update:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('EventSource error:', error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }

  // 知识库API
  async getKnowledgeIndex(): Promise<KnowledgeIndexResponse> {
    const response = await this.client.get<KnowledgeIndexResponse>('/api/knowledge/');
    return response.data;
  }

  async getKnowledgeItem(itemPath: string): Promise<{ content: string; path: string }> {
    const response = await this.client.get(`/api/knowledge/items/${itemPath}`);
    return response.data;
  }

  async reindexKnowledge(): Promise<void> {
    await this.client.post('/api/knowledge/reindex');
  }

  // 配置API
  async getConfig(): Promise<Config> {
    const response = await this.client.get<Config>('/api/config/');
    return response.data;
  }

  async updateConfig(config: Partial<Config>): Promise<void> {
    await this.client.post('/api/config/', config);
  }

  async validateConfig(): Promise<{ valid: boolean; message: string }> {
    const response = await this.client.get('/api/config/validate');
    return response.data;
  }
}

export const api = new ApiClient();
```

**Step 3: Commit**

```bash
git add web/frontend/types/ web/frontend/lib/
git commit -m "feat(web): add TypeScript types and API client"
```

---

## Task 6: 实现前端UI组件

**Files:**
- Create: `web/frontend/components/ui/button.tsx`
- Create: `web/frontend/components/ui/card.tsx`
- Create: `web/frontend/components/ui/progress.tsx`
- Create: `web/frontend/components/ui/badge.tsx`

**Step 1: 编写Button组件**

```typescript
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
```

**Step 2: 编写Card组件**

```typescript
import * as React from "react"

import { cn } from "@/lib/utils"

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-lg border bg-card text-card-foreground shadow-sm",
      className
    )}
    {...props}
  />
))
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "text-2xl font-semibold leading-none tracking-tight",
      className
    )}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
```

**Step 3: 编写Progress组件**

```typescript
"use client"

import * as React from "react"
import * as ProgressPrimitive from "@radix-ui/react-progress"

import { cn } from "@/lib/utils"

const Progress = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root>
>(({ className, value, ...props }, ref) => (
  <ProgressPrimitive.Root
    ref={ref}
    className={cn(
      "relative h-4 w-full overflow-hidden rounded-full bg-secondary",
      className
    )}
    {...props}
  >
    <ProgressPrimitive.Indicator
      className="h-full w-full flex-1 bg-primary transition-all"
      style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
    />
  </ProgressPrimitive.Root>
))
Progress.displayName = ProgressPrimitive.Root.displayName

export { Progress }
```

**Step 4: 编写Badge组件**

```typescript
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
```

**Step 5: Commit**

```bash
git add web/frontend/components/ui/
git commit -m "feat(web): add shadcn/ui base components (Button, Card, Progress, Badge)"
```

---

## Task 7: 实现文件上传组件

**Files:**
- Create: `web/frontend/components/upload.tsx`

**Step 1: 编写上传组件**

```typescript
"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload as UploadIcon, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";
import type { Document, ProcessingProgress } from "@/types";

interface UploadProps {
  onUploadComplete?: (doc: Document) => void;
}

export function Upload({ onUploadComplete }: UploadProps) {
  const [files, setFiles] = useState<Array<{
    file: File;
    id: string;
    status: "uploading" | "processing" | "completed" | "error";
    progress: number;
    message: string;
    docId?: string;
  }>>([]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((file) => ({
      file,
      id: Math.random().toString(36).substring(7),
      status: "uploading" as const,
      progress: 0,
      message: "上传中...",
    }));

    setFiles((prev) => [...prev, ...newFiles]);

    // 处理每个文件
    for (const fileItem of newFiles) {
      try {
        // 1. 上传文件
        const doc = await api.uploadDocument(fileItem.file, (uploadProgress) => {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === fileItem.id
                ? { ...f, progress: uploadProgress * 0.3 }
                : f
            )
          );
        });

        fileItem.docId = doc.id;
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileItem.id
              ? { ...f, status: "processing", progress: 30, message: "处理中..." }
              : f
          )
        );

        // 2. 订阅处理进度
        const unsubscribe = api.subscribeToProgress(doc.id, (progress: ProcessingProgress) => {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === fileItem.id
                ? {
                    ...f,
                    progress: 30 + progress.progress * 0.7,
                    status:
                      progress.status === "completed"
                        ? "completed"
                        : progress.status === "failed"
                        ? "error"
                        : "processing",
                    message: progress.message,
                  }
                : f
            )
          );

          if (progress.status === "completed") {
            unsubscribe();
            api.getDocument(doc.id).then((completedDoc) => {
              onUploadComplete?.(completedDoc);
            });
          } else if (progress.status === "failed") {
            unsubscribe();
          }
        });
      } catch (error) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileItem.id
              ? {
                  ...f,
                  status: "error",
                  message: error instanceof Error ? error.message : "上传失败",
                }
              : f
          )
        );
      }
    }
  }, [onUploadComplete]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'application/pdf': ['.pdf'],
    },
    multiple: true,
  });

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
          isDragActive
            ? "border-primary bg-primary/5"
            : "border-gray-300 hover:border-gray-400"
        )}
      >
        <input {...getInputProps()} />
        <UploadIcon className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-sm text-gray-600">
          {isDragActive ? "释放文件以上传" : "拖放文件到此处，或点击选择文件"}
        </p>
        <p className="mt-1 text-xs text-gray-400">
          支持格式: .docx, .doc, .pdf
        </p>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((fileItem) => (
            <div
              key={fileItem.id}
              className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg"
            >
              <FileText className="h-8 w-8 text-blue-500 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">
                  {fileItem.file.name}
                </p>
                <p className="text-xs text-gray-500">{fileItem.message}</p>
                <Progress
                  value={fileItem.progress}
                  className="h-2 mt-2"
                />
              </div>
              <button
                onClick={() => removeFile(fileItem.id)}
                className="p-1 hover:bg-gray-200 rounded flex-shrink-0"
              >
                <X className="h-4 w-4 text-gray-500" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add web/frontend/components/upload.tsx
git commit -m "feat(web): add file upload component with drag-drop and progress tracking"
```

---

## Task 8: 实现前端页面

**Files:**
- Create: `web/frontend/app/layout.tsx`
- Create: `web/frontend/app/page.tsx`
- Create: `web/frontend/app/documents/page.tsx`
- Create: `web/frontend/app/knowledge/page.tsx`

**Step 1: 编写布局 (app/layout.tsx)**

```typescript
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Doc2Know - 文档转知识库',
  description: '将Word文档转换为结构化Markdown知识库',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          {/* 导航栏 */}
          <nav className="bg-white shadow-sm border-b">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex items-center">
                  <a href="/" className="text-xl font-bold text-gray-900">
                    Doc2Know
                  </a>
                </div>
                <div className="flex items-center space-x-4">
                  <a
                    href="/"
                    className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    首页
                  </a>
                  <a
                    href="/documents"
                    className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    文档管理
                  </a>
                  <a
                    href="/knowledge"
                    className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    知识库
                  </a>
                </div>
              </div>
            </div>
          </nav>

          {/* 主内容 */}
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
```

**Step 2: 编写首页 (app/page.tsx)**

```typescript
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Upload, BookOpen, FileText, Settings } from 'lucide-react';

export default function Home() {
  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center py-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Doc2Know
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          将Word文档智能转换为结构化Markdown知识库
          <br />
          利用AI分析文档结构，自动生成摘要和标签
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link href="/documents">
            <Button size="lg">
              <Upload className="mr-2 h-5 w-5" />
              开始上传
            </Button>
          </Link>
          <Link href="/knowledge">
            <Button variant="outline" size="lg">
              <BookOpen className="mr-2 h-5 w-5" />
              浏览知识库
            </Button>
          </Link>
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <FileText className="h-8 w-8 text-blue-500 mb-2" />
            <CardTitle>文档解析</CardTitle>
            <CardDescription>
              支持 .docx、.doc、.pdf 格式
              <br />
              自动识别文档结构和标题层级
            </CardDescription>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <Settings className="h-8 w-8 text-green-500 mb-2" />
            <CardTitle>AI分析</CardTitle>
            <CardDescription>
              大语言模型智能分析
              <br />
              自动生成标题、摘要和标签
            </CardDescription>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <BookOpen className="h-8 w-8 text-purple-500 mb-2" />
            <CardTitle>知识库管理</CardTitle>
            <CardDescription>
              结构化的Markdown输出
              <br />
              自动生成索引和搜索功能
            </CardDescription>
          </CardHeader>
        </Card>
      </div>

      {/* Workflow */}
      <Card className="mt-8">
        <CardHeader>
          <CardTitle>工作流程</CardTitle>
          <CardDescription>简单三步，将文档转为知识库</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center">
            <div className="p-4">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-blue-600 font-bold">1</span>
              </div>
              <h3 className="font-medium">上传文档</h3>
              <p className="text-sm text-gray-500 mt-1">拖拽或选择Word/PDF文件</p>
            </div>
            <div className="p-4">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-green-600 font-bold">2</span>
              </div>
              <h3 className="font-medium">AI分析</h3>
              <p className="text-sm text-gray-500 mt-1">自动提取结构和关键信息</p>
            </div>
            <div className="p-4">
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-purple-600 font-bold">3</span>
              </div>
              <h3 className="font-medium">生成知识库</h3>
              <p className="text-sm text-gray-500 mt-1">转换为Markdown并建立索引</p>
            </div>
            <div className="p-4">
              <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-orange-600 font-bold">4</span>
              </div>
              <h3 className="font-medium">浏览使用</h3>
              <p className="text-sm text-gray-500 mt-1">在知识库中查看和管理</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 3: 编写文档管理页 (app/documents/page.tsx)**

```typescript
"use client";

import { useEffect, useState } from "react";
import { Upload } from "@/components/upload";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { Document } from "@/types";
import { FileText, Trash2, RefreshCw, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

const statusMap: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  pending: { label: "等待中", variant: "secondary" },
  parsing: { label: "解析中", variant: "default" },
  analyzing: { label: "分析中", variant: "default" },
  generating: { label: "生成中", variant: "default" },
  completed: { label: "已完成", variant: "outline" },
  failed: { label: "失败", variant: "destructive" },
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  const loadDocuments = async () => {
    try {
      const response = await api.listDocuments();
      setDocuments(response.documents);
    } catch (error) {
      console.error("Failed to load documents:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleUploadComplete = (doc: Document) => {
    loadDocuments();
  };

  const handleDelete = async (docId: string) => {
    if (!confirm("确定要删除这个文档吗？")) return;

    try {
      await api.deleteDocument(docId);
      loadDocuments();
    } catch (error) {
      console.error("Failed to delete document:", error);
      alert("删除失败");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">文档管理</h1>
        <Button variant="outline" onClick={loadDocuments} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          刷新
        </Button>
      </div>

      {/* 上传区域 */}
      <Card>
        <CardHeader>
          <CardTitle>上传新文档</CardTitle>
        </CardHeader>
        <CardContent>
          <Upload onUploadComplete={handleUploadComplete} />
        </CardContent>
      </Card>

      {/* 文档列表 */}
      <Card>
        <CardHeader>
          <CardTitle>处理记录</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              暂无文档，请上传文件
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <FileText className="h-8 w-8 text-blue-500 flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium truncate">
                          {doc.title || doc.filename}
                        </p>
                        <Badge variant={statusMap[doc.status]?.variant || "default"}>
                          {statusMap[doc.status]?.label || doc.status}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-500 truncate">
                        {doc.filename} · {new Date(doc.created_at).toLocaleString()}
                      </p>
                      {doc.summary && (
                        <p className="text-sm text-gray-600 mt-1 line-clamp-1">
                          {doc.summary}
                        </p>
                      )}
                      {doc.tags.length > 0 && (
                        <div className="flex gap-1 mt-1">
                          {doc.tags.map((tag) => (
                            <Badge key={tag} variant="secondary" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {doc.status === "completed" ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : doc.status === "failed" ? (
                      <AlertCircle className="h-5 w-5 text-red-500" />
                    ) : null}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(doc.id)}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 4: 编写知识库页 (app/knowledge/page.tsx)**

```typescript
"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { KnowledgeItem } from "@/types";
import { BookOpen, RefreshCw, Loader2, FileText, Tag, Calendar } from "lucide-react";

export default function KnowledgePage() {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedItem, setSelectedItem] = useState<KnowledgeItem | null>(null);
  const [content, setContent] = useState<string>("");
  const [loadingContent, setLoadingContent] = useState(false);

  const loadKnowledge = async () => {
    setLoading(true);
    try {
      const response = await api.getKnowledgeIndex();
      setItems(response.items);
    } catch (error) {
      console.error("Failed to load knowledge:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadKnowledge();
  }, []);

  const handleSelectItem = async (item: KnowledgeItem) => {
    setSelectedItem(item);
    setLoadingContent(true);
    try {
      const response = await api.getKnowledgeItem(item.file_path);
      setContent(response.content);
    } catch (error) {
      console.error("Failed to load content:", error);
      setContent("加载失败");
    } finally {
      setLoadingContent(false);
    }
  };

  const handleReindex = async () => {
    try {
      await api.reindexKnowledge();
      loadKnowledge();
    } catch (error) {
      console.error("Failed to reindex:", error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">知识库</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleReindex}>
            <RefreshCw className="h-4 w-4 mr-2" />
            重建索引
          </Button>
          <Button variant="outline" onClick={loadKnowledge} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            刷新
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧列表 */}
        <div className="lg:col-span-1">
          <Card className="h-[calc(100vh-200px)]">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                文档列表
                <Badge variant="secondary">{items.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="overflow-auto h-[calc(100%-80px)]">
              {loading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                </div>
              ) : items.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  知识库为空，请先上传文档
                </div>
              ) : (
                <div className="space-y-2">
                  {items.map((item) => (
                    <button
                      key={item.file_path}
                      onClick={() => handleSelectItem(item)}
                      className={`w-full text-left p-3 rounded-lg transition-colors ${
                        selectedItem?.file_path === item.file_path
                          ? "bg-blue-50 border-blue-200 border"
                          : "hover:bg-gray-50"
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <FileText className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">
                            {item.title}
                          </p>
                          <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                            {item.summary}
                          </p>
                          <div className="flex items-center gap-2 mt-2">
                            {item.tags.slice(0, 3).map((tag) => (
                              <Badge key={tag} variant="secondary" className="text-xs">
                                <Tag className="h-3 w-3 mr-1" />
                                {tag}
                              </Badge>
                            ))}
                          </div>
                          <p className="text-xs text-gray-400 mt-1 flex items-center">
                            <Calendar className="h-3 w-3 mr-1" />
                            {item.updated_at}
                          </p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 右侧内容 */}
        <div className="lg:col-span-2">
          <Card className="h-[calc(100vh-200px)]">
            <CardHeader>
              <CardTitle>
                {selectedItem ? selectedItem.title : "选择文档查看"}
              </CardTitle>
            </CardHeader>
            <CardContent className="overflow-auto h-[calc(100%-80px)]">
              {loadingContent ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                </div>
              ) : selectedItem ? (
                <div className="prose prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded-lg overflow-auto">
                    {content}
                  </pre>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <BookOpen className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p>从左侧选择一个文档查看内容</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
```

**Step 5: Commit**

```bash
git add web/frontend/app/
git commit -m "feat(web): implement main pages (home, documents, knowledge)"
```

---

## Task 9: 创建启动脚本和文档

**Files:**
- Create: `web/README.md`
- Create: `package.json` (根目录)
- Modify: `web/frontend/next.config.js` (更新代理配置)

**Step 1: 编写根目录 package.json**

```json
{
  "name": "doc2know-web-complete",
  "version": "1.0.0",
  "description": "Doc2Know Web Interface - Next.js frontend + FastAPI backend",
  "scripts": {
    "install:all": "cd web/backend && pip install -r requirements.txt && cd ../frontend && npm install",
    "dev:backend": "cd web/backend && uvicorn app.main:app --reload --port 8000",
    "dev:frontend": "cd web/frontend && npm run dev",
    "dev": "echo '请同时运行: npm run dev:backend 和 npm run dev:frontend'",
    "build:frontend": "cd web/frontend && npm run build",
    "start:backend": "cd web/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000",
    "start": "npm run start:backend"
  }
}
```

**Step 2: 编写 Web 目录 README.md**

```markdown
# Doc2Know Web Interface

Doc2Know 的 Web 界面，包含 FastAPI 后端和 Next.js 前端。

## 项目结构

```
web/
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── api/             # API 路由
│   │   ├── core/            # 核心逻辑
│   │   └── models/          # 数据模型
│   └── requirements.txt
└── frontend/         # Next.js 前端
    ├── app/                 # Next.js 14 App Router
    ├── components/          # React 组件
    ├── lib/                 # 工具库
    └── types/               # TypeScript 类型
```

## 快速开始

### 1. 安装依赖

```bash
# 后端依赖
pip install -r web/backend/requirements.txt

# 前端依赖
cd web/frontend && npm install
```

### 2. 配置

确保项目根目录有有效的 `config.yaml`：

```yaml
llm:
  base_url: "https://api.openai.com/v1"
  api_key: "your-api-key"
  model: "gpt-3.5-turbo"

paths:
  raw_dir: "./raw_docs"
  output_dir: "./output"

processing:
  chunk_size: 4000
  max_concurrent: 3
```

### 3. 启动服务

终端1 - 启动后端:
```bash
cd web/backend
uvicorn app.main:app --reload --port 8000
```

终端2 - 启动前端:
```bash
cd web/frontend
npm run dev
```

### 4. 访问

- Web界面: http://localhost:3000
- API文档: http://localhost:8000/docs

## API 端点

### 文档管理
- `POST /api/documents/upload` - 上传并处理文档
- `GET /api/documents/` - 列出所有文档
- `GET /api/documents/{id}` - 获取文档详情
- `DELETE /api/documents/{id}` - 删除文档
- `GET /api/documents/{id}/progress` - 获取处理进度 (SSE)

### 知识库
- `GET /api/knowledge/` - 获取知识库索引
- `GET /api/knowledge/items/{path}` - 获取条目内容
- `POST /api/knowledge/reindex` - 重新索引

### 配置
- `GET /api/config/` - 获取配置
- `POST /api/config/` - 更新配置
- `GET /api/config/validate` - 验证配置

## 技术栈

- **Backend**: Python 3.9+, FastAPI, Uvicorn
- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS
- **通信**: REST API + Server-Sent Events
```

**Step 3: 更新 next.config.js 以支持代理**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
```

**Step 4: Commit**

```bash
git add web/README.md package.json web/frontend/next.config.js
git commit -m "docs(web): add setup documentation and npm scripts"
```

---

## Task 10: 修复 Python 路径和导入问题

**Files:**
- Modify: `web/backend/app/main.py`
- Modify: `web/backend/app/core/processor.py`
- Modify: `web/backend/app/api/documents.py`
- Modify: `web/backend/app/api/knowledge.py`
- Modify: `web/backend/app/api/config.py`

**Step 1: 验证并修复导入路径**

需要确保所有模块都能正确导入 doc2know 包。需要添加正确的路径处理。

验证文件已正确创建:

```bash
cd /Users/zhongwei9/Documents/gitlab/joyway1978/Doc2Know
python -c "import sys; sys.path.insert(0, '.'); from doc2know.config import Config; print('Config imported successfully')"
```

**Step 2: Commit**

```bash
git add -A
git commit -m "fix(web): fix Python import paths for backend modules"
```

---

## Task 11: 添加后端测试

**Files:**
- Create: `web/backend/tests/__init__.py`
- Create: `web/backend/tests/test_api.py`
- Create: `web/backend/tests/test_processor.py`
- Create: `web/backend/tests/conftest.py`

**Step 1: 创建测试配置 (conftest.py)**

```python
"""测试配置"""

import pytest
import asyncio
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """测试数据库"""
    from web.backend.app.core.database import init_database, DATABASE_PATH

    # 使用测试数据库
    test_db_path = Path("web/backend/data/test_documents.db")
    DATABASE_PATH = test_db_path

    await init_database()
    yield

    # 清理
    if test_db_path.exists():
        test_db_path.unlink()


@pytest.fixture
def test_config():
    """测试配置"""
    return {
        "llm": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "test-key",
            "model": "gpt-3.5-turbo"
        },
        "paths": {
            "raw_dir": "./test_raw_docs",
            "output_dir": "./test_output"
        }
    }
```

**Step 2: 编写 API 测试 (test_api.py)**

```python
"""API 端点测试"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(test_db):
    """测试客户端"""
    from web.backend.app.main import app
    return TestClient(app)


def test_health_check(client):
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_upload_invalid_file_type(client):
    """测试上传无效文件类型"""
    response = client.post(
        "/api/documents/upload",
        files={"file": ("test.txt", b"invalid content", "text/plain")}
    )
    assert response.status_code == 400
    assert "不支持的文件格式" in response.json()["detail"]


def test_upload_file_too_large(client, monkeypatch):
    """测试上传过大文件"""
    # 模拟大文件
    from web.backend.app.api import documents
    monkeypatch.setattr(documents, "MAX_FILE_SIZE", 100)  # 100字节限制

    response = client.post(
        "/api/documents/upload",
        files={"file": ("test.docx", b"x" * 200, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 413
    assert "文件过大" in response.json()["detail"]


def test_get_nonexistent_document(client):
    """测试获取不存在的文档"""
    response = client.get("/api/documents/nonexistent-id")
    assert response.status_code == 404


def test_delete_nonexistent_document(client):
    """测试删除不存在的文档"""
    response = client.delete("/api/documents/nonexistent-id")
    assert response.status_code == 404
```

**Step 3: 编写处理器测试 (test_processor.py)**

```python
"""文档处理器测试"""

import pytest
from unittest.mock import Mock, patch


@pytest.mark.asyncio
async def test_create_document(test_db):
    """测试创建文档记录"""
    from web.backend.app.core.database import create_document, get_document

    doc = await create_document("test-id", "test.docx")
    assert doc["id"] == "test-id"
    assert doc["filename"] == "test.docx"
    assert doc["status"] == "pending"

    # 验证可以从数据库读取
    fetched = await get_document("test-id")
    assert fetched["filename"] == "test.docx"


@pytest.mark.asyncio
async def test_update_document(test_db):
    """测试更新文档记录"""
    from web.backend.app.core.database import create_document, update_document, get_document

    await create_document("test-id", "test.docx")
    await update_document("test-id", status="completed", progress=100)

    doc = await get_document("test-id")
    assert doc["status"] == "completed"
    assert doc["progress"] == 100


@pytest.mark.asyncio
async def test_list_documents(test_db):
    """测试列出文档"""
    from web.backend.app.core.database import create_document, list_documents

    await create_document("id-1", "file1.docx")
    await create_document("id-2", "file2.docx")

    docs = await list_documents()
    assert len(docs) == 2


@pytest.mark.asyncio
async def test_delete_document(test_db):
    """测试删除文档"""
    from web.backend.app.core.database import create_document, delete_document, get_document

    await create_document("test-id", "test.docx")
    success = await delete_document("test-id")
    assert success is True

    doc = await get_document("test-id")
    assert doc is None
```

**Step 4: 运行测试**

```bash
cd web/backend
pip install pytest pytest-asyncio httpx
python -m pytest tests/ -v
```

**Step 5: Commit**

```bash
git add web/backend/tests/
git commit -m "test(web): add backend API and database tests"
```

---

## Task 12: 添加前端测试

**Files:**
- Create: `web/frontend/__tests__/components/upload.test.tsx`
- Create: `web/frontend/__tests__/components/document-list.test.tsx`
- Create: `web/frontend/__tests__/lib/api.test.ts`
- Create: `web/frontend/jest.config.js`

**Step 1: 安装测试依赖**

```bash
cd web/frontend
npm install --save-dev jest @testing-library/react @testing-library/jest-dom @testing-library/user-event jest-environment-jsdom
```

**Step 2: 配置 Jest (jest.config.js)**

```javascript
/** @type {import('jest').Config} */
const config = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testMatch: ['**/__tests__/**/*.test.ts(x)?'],
  collectCoverageFrom: [
    'components/**/*.{ts,tsx}',
    'lib/**/*.{ts,tsx}',
    '!**/*.d.ts',
  ],
}

module.exports = config
```

**Step 3: 创建 Jest 初始化文件 (jest.setup.js)**

```javascript
import '@testing-library/jest-dom'
```

**Step 4: 编写 API 客户端测试**

```typescript
// __tests__/lib/api.test.ts
import { apiClient, documentApi } from '@/lib/api'

describe('API Client', () => {
  beforeEach(() => {
    global.fetch = jest.fn()
  })

  afterEach(() => {
    jest.resetAllMocks()
  })

  test('apiClient makes correct request', async () => {
    const mockResponse = { data: 'test' }
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    })

    const result = await apiClient('/api/test')

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/test',
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      })
    )
    expect(result).toEqual(mockResponse)
  })

  test('apiClient throws on error response', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    })

    await expect(apiClient('/api/test')).rejects.toThrow('API Error: 500')
  })

  test('documentApi.uploadDocument sends FormData', async () => {
    const mockResponse = { id: '123', filename: 'test.docx' }
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    })

    const file = new File(['content'], 'test.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })

    const result = await documentApi.uploadDocument(file)

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/documents/upload',
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    )
    expect(result).toEqual(mockResponse)
  })
})
```

**Step 5: 编写组件测试**

```typescript
// __tests__/components/upload.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UploadArea } from '@/components/upload'

describe('UploadArea', () => {
  const mockOnUpload = jest.fn()

  beforeEach(() => {
    mockOnUpload.mockClear()
  })

  test('renders upload area', () => {
    render(<UploadArea onUpload={mockOnUpload} />)

    expect(screen.getByText('拖放文件到此处')).toBeInTheDocument()
    expect(screen.getByText('或点击选择文件')).toBeInTheDocument()
  })

  test('shows file type restrictions', () => {
    render(<UploadArea onUpload={mockOnUpload} />)

    expect(screen.getByText(/支持格式/)).toHaveTextContent('.docx')
    expect(screen.getByText(/支持格式/)).toHaveTextContent('.pdf')
  })

  test('handles file selection', async () => {
    render(<UploadArea onUpload={mockOnUpload} />)

    const file = new File(['content'], 'test.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })

    const input = screen.getByLabelText(/选择文件/)
    await userEvent.upload(input, file)

    expect(mockOnUpload).toHaveBeenCalledWith(file)
  })

  test('rejects invalid file type', async () => {
    const alertMock = jest.spyOn(window, 'alert').mockImplementation(() => {})
    render(<UploadArea onUpload={mockOnUpload} />)

    const file = new File(['content'], 'test.txt', { type: 'text/plain' })
    const input = screen.getByLabelText(/选择文件/)

    await userEvent.upload(input, file)

    expect(alertMock).toHaveBeenCalledWith(expect.stringContaining('不支持的文件格式'))
    expect(mockOnUpload).not.toHaveBeenCalled()

    alertMock.mockRestore()
  })
})
```

**Step 6: 添加测试脚本到 package.json**

```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage"
  }
}
```

**Step 7: 运行测试**

```bash
npm test
```

**Step 8: Commit**

```bash
git add web/frontend/__tests__/ web/frontend/jest.config.js web/frontend/jest.setup.js web/frontend/package.json
git commit -m "test(web): add frontend component and API tests"
```

---

完成所有任务后，运行以下验证：

```bash
# 1. 后端启动测试
cd web/backend
python -c "import app.main; print('Backend imports OK')"

# 2. 前端依赖安装
cd ../frontend
npm install

# 3. 构建测试
npm run build

# 4. 完整启动测试
cd ../backend && uvicorn app.main:app --port 8000 &
cd ../frontend && npm run dev &
```

访问 http://localhost:3000 验证 Web 界面正常工作。

---

## 总结

此计划将 Doc2Know CLI 工具扩展为完整的 Web 应用：

1. **Backend (FastAPI)**: 复用现有 CLI 核心逻辑，提供 RESTful API 和 SSE 进度推送
2. **Frontend (Next.js)**: 现代化 React 应用，支持文件上传、进度跟踪、知识库浏览
3. **实时通信**: Server-Sent Events 实现处理进度实时更新
4. **完整功能**: 文档上传、AI处理、知识库管理一站式完成

**任务总数**: 12个主要任务，每个任务2-5分钟
**预计总时间**: 40-60分钟（包含测试）

---

## 工程审查修改说明

本次计划已根据 `/plan-eng-review` 的工程审查结果进行以下修改：

### 1. 数据持久化 (SQLite)
- **新增文件**: `web/backend/app/core/database.py`
- **修改**: 使用 `aiosqlite` 替代内存存储，文档状态持久化到 SQLite
- **影响**: Task 2 添加了数据库初始化步骤，processor.py 使用异步数据库操作

### 2. FastAPI BackgroundTasks
- **修改**: `web/backend/app/core/processor.py`
- **变更**: 移除 `ThreadPoolExecutor`，改用 FastAPI 原生的 `BackgroundTasks`
- **优势**: 更好的集成、资源管理、与 FastAPI 生命周期一致

### 3. 结构化错误类型和日志
- **新增**: `ProcessingError` 异常类
- **新增**: 模块级日志配置 (`logging.getLogger(__name__)`)
- **修改**: 所有处理步骤添加结构化日志记录

### 4. 文件验证增强
- **新增**: 文件大小限制 (50MB)
- **新增**: `MAX_FILE_SIZE` 常量
- **修改**: `upload_document` 端点先读取内容验证大小再保存

### 5. 新增测试任务
- **Task 11**: 后端测试 (pytest + async tests)
  - API 端点测试
  - 数据库操作测试
  - 文件上传验证测试
- **Task 12**: 前端测试 (Jest + React Testing Library)
  - 组件渲染测试
  - API 客户端测试
  - 用户交互测试
