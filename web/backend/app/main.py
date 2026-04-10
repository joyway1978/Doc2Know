"""FastAPI 主入口"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import documents, knowledge, config

# 创建 FastAPI 应用
app = FastAPI(
    title="Doc2Know API",
    description="Doc2Know Web 接口 - 将 Word 文档转换为结构化知识库",
    version="0.1.0",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(documents.router)
app.include_router(knowledge.router)
app.include_router(config.router)

# 尝试挂载静态文件（输出目录）
try:
    from app.core.processor import get_processor
    processor = get_processor()
    output_dir = processor.config.output_dir

    if Path(output_dir).exists():
        app.mount("/files", StaticFiles(directory=output_dir), name="files")
except Exception:
    pass


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "Doc2Know API",
        "version": "0.1.0",
        "description": "将 Word 文档转换为结构化知识库",
        "docs": "/docs",
        "health": "/config/health"
    }


@app.get("/api")
async def api_info():
    """API 信息"""
    return {
        "version": "v1",
        "endpoints": {
            "documents": "/documents",
            "knowledge": "/knowledge",
            "config": "/config"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
