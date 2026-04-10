"""配置 API 路由"""

import os
from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from app.models.document import ConfigResponse, ConfigUpdateRequest, StatsResponse
from app.core.processor import get_processor

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=ConfigResponse)
async def get_config():
    """
    获取当前配置

    返回非敏感的配置信息（不包含 API Key）
    """
    processor = get_processor()
    config = processor.config

    return ConfigResponse(
        llm={
            "base_url": config.base_url,
            "model": config.model,
            "api_key": mask_api_key(config.api_key) if config.api_key else ""
        },
        paths={
            "raw_dir": config.raw_dir,
            "output_dir": config.output_dir
        },
        processing={
            "chunk_size": config.chunk_size,
            "max_concurrent": config.max_concurrent
        }
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """获取系统统计信息"""
    processor = get_processor()
    stats = processor.get_stats()

    from datetime import datetime

    return StatsResponse(
        total_documents=stats.get("total_documents", 0),
        completed=stats.get("completed", 0),
        processing=stats.get("processing", 0),
        failed=stats.get("failed", 0),
        total_knowledge_items=stats.get("total_knowledge_items", 0),
        last_updated=datetime.fromisoformat(stats.get("last_updated")) if stats.get("last_updated") else None
    )


@router.get("/health")
async def health_check():
    """健康检查接口"""
    from datetime import datetime

    processor = get_processor()
    config = processor.config

    # 检查必要的配置
    issues = []

    if not config.api_key:
        issues.append("API Key 未配置")

    # 检查目录权限
    try:
        raw_dir = config.raw_dir
        if not os.path.exists(raw_dir):
            os.makedirs(raw_dir, exist_ok=True)
        if not os.access(raw_dir, os.W_OK):
            issues.append(f"无法写入输入目录: {raw_dir}")
    except Exception as e:
        issues.append(f"输入目录错误: {str(e)}")

    try:
        output_dir = config.output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        if not os.access(output_dir, os.W_OK):
            issues.append(f"无法写入输出目录: {output_dir}")
    except Exception as e:
        issues.append(f"输出目录错误: {str(e)}")

    health_status = "healthy" if not issues else "degraded"

    return {
        "status": health_status,
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0",
        "issues": issues if issues else None
    }


@router.post("/update")
async def update_config(update: ConfigUpdateRequest):
    """
    更新配置

    注意：此配置仅保存在内存中，重启后失效
    """
    # 注意：当前实现仅更新内存中的配置
    # 如需持久化，需要修改配置文件

    processor = get_processor()
    config = processor.config

    if update.llm:
        if "base_url" in update.llm:
            config._config["llm"]["base_url"] = update.llm["base_url"]
        if "model" in update.llm:
            config._config["llm"]["model"] = update.llm["model"]
        if "api_key" in update.llm and update.llm["api_key"]:
            config._config["llm"]["api_key"] = update.llm["api_key"]

    if update.paths:
        if "raw_dir" in update.paths:
            config._config["paths"]["raw_dir"] = update.paths["raw_dir"]
        if "output_dir" in update.paths:
            config._config["paths"]["output_dir"] = update.paths["output_dir"]

    if update.processing:
        if "chunk_size" in update.processing:
            config._config["processing"]["chunk_size"] = update.processing["chunk_size"]
        if "max_concurrent" in update.processing:
            config._config["processing"]["max_concurrent"] = update.processing["max_concurrent"]

    # 重新确保目录存在
    processor._ensure_directories()

    return {
        "success": True,
        "message": "配置已更新（重启后失效）"
    }


@router.get("/environment")
async def get_environment_info():
    """获取环境信息"""
    import sys
    import platform

    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "node": platform.node(),
        "environment_variables": {
            "DOCS2KNOW_API_KEY": "已设置" if os.getenv("DOCS2KNOW_API_KEY") else "未设置",
            "DOCS2KNOW_BASE_URL": os.getenv("DOCS2KNOW_BASE_URL", "未设置"),
            "DOCS2KNOW_MODEL": os.getenv("DOCS2KNOW_MODEL", "未设置"),
            "DOCS2KNOW_RAW_DIR": os.getenv("DOCS2KNOW_RAW_DIR", "未设置"),
            "DOCS2KNOW_OUTPUT_DIR": os.getenv("DOCS2KNOW_OUTPUT_DIR", "未设置"),
        }
    }


def mask_api_key(api_key: str) -> str:
    """遮盖 API Key，只显示前 8 位和后 4 位"""
    if not api_key or len(api_key) < 12:
        return "***"
    return f"{api_key[:8]}...{api_key[-4:]}"
