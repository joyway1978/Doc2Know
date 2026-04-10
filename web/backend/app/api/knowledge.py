"""知识库 API 路由"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.document import KnowledgeItem, KnowledgeListResponse
from app.core.processor import get_processor

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=KnowledgeListResponse)
async def list_knowledge(
    search: Optional[str] = Query(None, description="搜索关键词"),
    tag: Optional[str] = Query(None, description="标签筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取知识库条目列表

    支持按关键词搜索和标签筛选
    """
    processor = get_processor()
    items = processor.get_knowledge_items()

    # 搜索筛选
    if search:
        search_lower = search.lower()
        items = [
            item for item in items
            if search_lower in item.get("title", "").lower()
            or search_lower in item.get("summary", "").lower()
        ]

    # 标签筛选
    if tag:
        items = [
            item for item in items
            if tag in item.get("tags", [])
        ]

    # 按更新时间倒序
    items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

    # 分页
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_items = items[start:end]

    # 转换为响应模型
    knowledge_items = [
        KnowledgeItem(
            id=item.get("id", ""),
            title=item.get("title", ""),
            summary=item.get("summary", ""),
            tags=item.get("tags", []),
            file_path=item.get("file_path", ""),
            updated_at=item.get("updated_at", ""),
            source=item.get("source")
        )
        for item in paginated_items
    ]

    return KnowledgeListResponse(
        items=knowledge_items,
        total=total
    )


@router.get("/tags")
async def get_all_tags():
    """获取所有标签列表"""
    processor = get_processor()
    items = processor.get_knowledge_items()

    # 收集所有标签
    all_tags = set()
    for item in items:
        tags = item.get("tags", [])
        all_tags.update(tags)

    # 统计每个标签的文档数量
    tag_counts = {}
    for item in items:
        for tag in item.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    return {
        "tags": sorted(list(all_tags)),
        "tag_counts": tag_counts
    }


@router.get("/{item_id}")
async def get_knowledge_detail(item_id: str):
    """
    获取知识库条目详情

    包含完整内容
    """
    processor = get_processor()
    detail = processor.get_knowledge_detail(item_id)

    if not detail:
        raise HTTPException(status_code=404, detail="知识条目不存在")

    return detail


@router.get("/{item_id}/content")
async def get_knowledge_content(item_id: str):
    """
    获取知识库条目的 Markdown 内容

    返回原始 Markdown 文本
    """
    processor = get_processor()
    detail = processor.get_knowledge_detail(item_id)

    if not detail:
        raise HTTPException(status_code=404, detail="知识条目不存在")

    return {
        "id": item_id,
        "title": detail.get("title", ""),
        "content": detail.get("content", ""),
        "markdown": detail.get("content", "")
    }


@router.post("/rebuild-index")
async def rebuild_index():
    """
    重建知识库索引

    重新扫描所有知识条目并更新索引文件
    """
    processor = get_processor()
    success = processor.rebuild_index()

    if not success:
        raise HTTPException(status_code=500, detail="重建索引失败")

    # 获取统计信息
    items = processor.get_knowledge_items()

    return {
        "success": True,
        "message": "索引重建完成",
        "total_items": len(items)
    }


@router.get("/{item_id}/related")
async def get_related_knowledge(
    item_id: str,
    limit: int = Query(5, ge=1, le=20)
):
    """
    获取相关知识点

    基于标签相似度推荐相关内容
    """
    processor = get_processor()

    # 获取当前条目
    current = processor.get_knowledge_detail(item_id)
    if not current:
        raise HTTPException(status_code=404, detail="知识条目不存在")

    current_tags = set(current.get("tags", []))

    # 获取所有条目并计算相似度
    all_items = processor.get_knowledge_items()
    scored_items = []

    for item in all_items:
        if item.get("id") == item_id:
            continue

        item_tags = set(item.get("tags", []))
        # 计算共同标签数量
        common_tags = current_tags & item_tags
        score = len(common_tags)

        if score > 0:
            scored_items.append((score, item))

    # 按相似度排序
    scored_items.sort(key=lambda x: x[0], reverse=True)

    # 取前 N 个
    related = scored_items[:limit]

    return {
        "item_id": item_id,
        "related_items": [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "summary": item.get("summary"),
                "tags": item.get("tags"),
                "similarity_score": score
            }
            for score, item in related
        ]
    }
