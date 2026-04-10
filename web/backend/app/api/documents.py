"""文档处理 API 路由"""

import asyncio
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.models.document import (
    DocumentResponse,
    DocumentListResponse,
    UploadResponse,
    ProcessingProgress,
    ErrorResponse,
)
from app.core.processor import get_processor, ProcessingTask

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    上传文档进行异步处理

    支持 .docx, .doc, .pdf 格式
    """
    processor = get_processor()

    # 验证文件类型
    allowed_types = ['.docx', '.doc', '.pdf']
    filename = file.filename or "unnamed"
    file_ext = filename.lower()

    if not any(file_ext.endswith(ext) for ext in allowed_types):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。支持: {', '.join(allowed_types)}"
        )

    # 读取文件内容
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 创建任务
    task = processor.create_task(
        filename=filename,
        file_size=file_size,
        file_type=file_ext.split('.')[-1].lower()
    )

    # 在后台处理
    background_tasks.add_task(
        processor.process_file,
        task,
        content
    )

    return UploadResponse(
        success=True,
        document_id=task.id,
        message="文件上传成功，开始处理"
    )


@router.post("/upload/stream")
async def upload_document_stream(
    file: UploadFile = File(...)
):
    """
    上传文档并流式返回处理进度（SSE）

    支持 .docx, .doc, .pdf 格式
    """
    processor = get_processor()

    # 验证文件类型
    allowed_types = ['.docx', '.doc', '.pdf']
    filename = file.filename or "unnamed"
    file_ext = filename.lower()

    if not any(file_ext.endswith(ext) for ext in allowed_types):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。支持: {', '.join(allowed_types)}"
        )

    # 读取文件内容
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 创建任务
    task = processor.create_task(
        filename=filename,
        file_size=file_size,
        file_type=file_ext.split('.')[-1].lower()
    )

    async def event_generator():
        """生成 SSE 事件"""
        try:
            async for progress in processor.process_file_stream(task, content):
                yield f"data: {progress.model_dump_json()}\n\n"
        except Exception as e:
            error_data = ProcessingProgress(
                document_id=task.id,
                status="failed",
                progress=0,
                message=f"处理失败: {str(e)}"
            )
            yield f"data: {error_data.model_dump_json()}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None
):
    """获取文档列表"""
    processor = get_processor()
    tasks = processor.get_all_tasks()

    # 过滤状态
    if status:
        tasks = [t for t in tasks if t.status == status]

    # 按时间倒序
    tasks.sort(key=lambda x: x.created_at, reverse=True)

    # 分页
    total = len(tasks)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_tasks = tasks[start:end]

    items = [
        DocumentResponse(
            id=task.id,
            filename=task.filename,
            file_size=task.file_size,
            file_type=task.file_type,
            status=task.status,
            progress=task.progress,
            created_at=task.created_at,
            updated_at=task.updated_at,
            error_message=task.error_message,
            output_file=task.output_file
        )
        for task in paginated_tasks
    ]

    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """获取文档详情"""
    processor = get_processor()
    task = processor.get_task(document_id)

    if not task:
        raise HTTPException(status_code=404, detail="文档不存在")

    return DocumentResponse(
        id=task.id,
        filename=task.filename,
        file_size=task.file_size,
        file_type=task.file_type,
        status=task.status,
        progress=task.progress,
        created_at=task.created_at,
        updated_at=task.updated_at,
        error_message=task.error_message,
        output_file=task.output_file
    )


@router.get("/{document_id}/progress")
async def get_document_progress(document_id: str):
    """获取文档处理进度（SSE 流）"""
    processor = get_processor()
    task = processor.get_task(document_id)

    if not task:
        raise HTTPException(status_code=404, detail="文档不存在")

    async def event_generator():
        """生成进度事件"""
        last_progress = -1

        while True:
            task = processor.get_task(document_id)
            if not task:
                break

            # 只在进度变化时发送
            if task.progress != last_progress:
                last_progress = task.progress
                progress_data = ProcessingProgress(
                    document_id=task.id,
                    status=task.status,
                    progress=task.progress,
                    message=get_status_message(task)
                )
                yield f"data: {progress_data.model_dump_json()}\n\n"

            # 如果已完成或失败，结束流
            if task.status in ["completed", "failed"]:
                break

            await asyncio.sleep(0.5)

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


def get_status_message(task: ProcessingTask) -> str:
    """根据任务状态获取状态消息"""
    messages = {
        "pending": "等待处理",
        "uploading": "上传中",
        "processing": f"处理中 ({task.progress}%)",
        "completed": "处理完成",
        "failed": f"处理失败: {task.error_message or '未知错误'}"
    }
    return messages.get(task.status, "未知状态")


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """删除文档"""
    processor = get_processor()

    if not processor.get_task(document_id):
        raise HTTPException(status_code=404, detail="文档不存在")

    success = processor.delete_task(document_id)

    if not success:
        raise HTTPException(status_code=500, detail="删除失败")

    return {"success": True, "message": "文档已删除"}


@router.post("/{document_id}/retry")
async def retry_document(
    document_id: str,
    background_tasks: BackgroundTasks
):
    """重试处理失败的文档"""
    processor = get_processor()
    task = processor.get_task(document_id)

    if not task:
        raise HTTPException(status_code=404, detail="文档不存在")

    if task.status != "failed":
        raise HTTPException(status_code=400, detail="只有失败的文档可以重试")

    # 重新读取文件内容
    if not task.file_path:
        raise HTTPException(status_code=400, detail="无法找到原始文件")

    file_path = task.file_path
    content = open(file_path, "rb").read()

    # 重置任务状态
    task.status = "processing"
    task.progress = 0
    task.error_message = None

    # 重新处理
    background_tasks.add_task(
        processor.process_file,
        task,
        content
    )

    return {"success": True, "message": "重新开始处理"}
