"""文档处理器核心 - 封装 CLI 逻辑供 API 使用"""

import os
import sys
import uuid
import shutil
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

# 添加项目根目录到路径，以便导入 CLI 模块
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from doc2know.config import Config, ConfigError
from doc2know.parser import DocxParser, PdfParser, get_parser_for_file
from doc2know.analyzer import LLMAnalyzer, AnalyzerError
from doc2know.generator import MarkdownGenerator
from doc2know.indexer import Indexer


@dataclass
class ProcessingTask:
    """处理任务状态"""
    id: str
    filename: str
    file_path: str
    file_size: int
    file_type: str
    status: str = "pending"  # pending, uploading, processing, completed, failed
    progress: int = 0
    error_message: Optional[str] = None
    output_file: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    _progress_callbacks: List[Callable] = field(default_factory=list)


class DocumentProcessor:
    """文档处理器 - API 层封装"""

    def __init__(self, config: Optional[Config] = None):
        """
        初始化文档处理器

        Args:
            config: 配置对象，如果为 None 则自动加载默认配置
        """
        if config is None:
            try:
                # 尝试从项目根目录加载配置
                config_path = str(project_root / "config.yaml")
                config = Config(config_path)
            except ConfigError:
                # 使用最小化配置
                config = self._create_minimal_config()

        self.config = config
        self.docx_parser = DocxParser()
        self.pdf_parser = PdfParser()
        self.analyzer = LLMAnalyzer(config)
        self.generator = MarkdownGenerator(config.output_dir)
        self.indexer = Indexer(config.output_dir)

        # 内存中的任务存储
        self._tasks: Dict[str, ProcessingTask] = {}

        # 确保目录存在
        self._ensure_directories()

    def _create_minimal_config(self) -> Config:
        """创建最小化配置"""
        config = Config.__new__(Config)
        config._config = {
            "llm": {
                "base_url": os.getenv("DOCS2KNOW_BASE_URL", "https://api.openai.com/v1"),
                "api_key": os.getenv("DOCS2KNOW_API_KEY", ""),
                "model": os.getenv("DOCS2KNOW_MODEL", "gpt-3.5-turbo"),
            },
            "paths": {
                "raw_dir": os.getenv("DOCS2KNOW_RAW_DIR", "./raw_docs"),
                "output_dir": os.getenv("DOCS2KNOW_OUTPUT_DIR", "./output"),
            },
            "processing": {
                "chunk_size": int(os.getenv("DOCS2KNOW_CHUNK_SIZE", "4000")),
                "max_concurrent": int(os.getenv("DOCS2KNOW_MAX_CONCURRENT", "3")),
            },
        }
        return config

    def _ensure_directories(self) -> None:
        """确保必要的目录存在"""
        Path(self.config.raw_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

    def create_task(self, filename: str, file_size: int, file_type: str) -> ProcessingTask:
        """
        创建新的处理任务

        Args:
            filename: 原始文件名
            file_size: 文件大小
            file_type: 文件类型

        Returns:
            新创建的任务对象
        """
        task_id = str(uuid.uuid4())
        task = ProcessingTask(
            id=task_id,
            filename=filename,
            file_path="",
            file_size=file_size,
            file_type=file_type,
        )
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[ProcessingTask]:
        """获取任务状态"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[ProcessingTask]:
        """获取所有任务"""
        return list(self._tasks.values())

    async def process_file(
        self,
        task: ProcessingTask,
        file_content: bytes,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> ProcessingTask:
        """
        处理上传的文件

        Args:
            task: 处理任务
            file_content: 文件内容字节
            progress_callback: 进度回调函数 (progress, message)

        Returns:
            更新后的任务对象
        """
        try:
            # 更新状态为处理中
            task.status = "processing"
            task.progress = 10
            task.updated_at = datetime.now()
            if progress_callback:
                progress_callback(10, "保存文件...")

            # 保存上传的文件
            raw_path = Path(self.config.raw_dir) / f"{task.id}_{task.filename}"
            raw_path.write_bytes(file_content)
            task.file_path = str(raw_path)

            task.progress = 20
            task.updated_at = datetime.now()
            if progress_callback:
                progress_callback(20, "解析文档...")

            # 解析文档
            parser = get_parser_for_file(str(raw_path))
            parsed_content = parser.parse(str(raw_path))

            task.progress = 40
            task.updated_at = datetime.now()
            if progress_callback:
                progress_callback(40, "AI 分析中...")

            # AI 分析
            analysis_result = self.analyzer.analyze(parsed_content)

            task.progress = 70
            task.updated_at = datetime.now()
            if progress_callback:
                progress_callback(70, "生成知识库...")

            # 生成 Markdown
            output_file = self.generator.generate(analysis_result, str(raw_path))
            task.output_file = output_file

            # 提取元数据
            task.title = analysis_result.get("title", task.filename)
            task.summary = analysis_result.get("summary", "")
            task.tags = analysis_result.get("tags", [])

            task.progress = 90
            task.updated_at = datetime.now()
            if progress_callback:
                progress_callback(90, "更新索引...")

            # 更新索引
            self.indexer.update_index()

            # 完成任务
            task.status = "completed"
            task.progress = 100
            task.updated_at = datetime.now()
            if progress_callback:
                progress_callback(100, "处理完成")

            return task

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            task.updated_at = datetime.now()
            if progress_callback:
                progress_callback(task.progress, f"处理失败: {str(e)}")
            return task

    async def process_file_stream(
        self,
        task: ProcessingTask,
        file_content: bytes
    ):
        """
        处理文件并生成进度流（用于 SSE）

        Args:
            task: 处理任务
            file_content: 文件内容字节

        Yields:
            进度更新字典
        """
        def progress_callback(progress: int, message: str):
            return {
                "document_id": task.id,
                "progress": progress,
                "status": "processing" if progress < 100 else "completed",
                "message": message,
                "timestamp": datetime.now().isoformat()
            }

        try:
            # 开始
            yield progress_callback(5, "开始处理...")
            await asyncio.sleep(0.1)

            # 保存文件
            yield progress_callback(10, "保存文件...")
            raw_path = Path(self.config.raw_dir) / f"{task.id}_{task.filename}"
            raw_path.write_bytes(file_content)
            task.file_path = str(raw_path)
            await asyncio.sleep(0.1)

            # 解析文档
            yield progress_callback(25, "解析文档...")
            parser = get_parser_for_file(str(raw_path))
            parsed_content = parser.parse(str(raw_path))
            await asyncio.sleep(0.1)

            # AI 分析
            yield progress_callback(50, "AI 分析中...")
            analysis_result = self.analyzer.analyze(parsed_content)
            await asyncio.sleep(0.1)

            # 生成 Markdown
            yield progress_callback(75, "生成知识库...")
            output_file = self.generator.generate(analysis_result, str(raw_path))
            task.output_file = output_file

            # 提取元数据
            task.title = analysis_result.get("title", task.filename)
            task.summary = analysis_result.get("summary", "")
            task.tags = analysis_result.get("tags", [])
            await asyncio.sleep(0.1)

            # 更新索引
            yield progress_callback(90, "更新索引...")
            self.indexer.update_index()
            await asyncio.sleep(0.1)

            # 完成
            task.status = "completed"
            task.progress = 100
            task.updated_at = datetime.now()
            yield progress_callback(100, "处理完成")

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            task.updated_at = datetime.now()
            yield {
                "document_id": task.id,
                "progress": task.progress,
                "status": "failed",
                "message": f"处理失败: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    def delete_task(self, task_id: str) -> bool:
        """
        删除任务及其相关文件

        Args:
            task_id: 任务 ID

        Returns:
            是否成功删除
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        try:
            # 删除原始文件
            if task.file_path and Path(task.file_path).exists():
                Path(task.file_path).unlink()

            # 删除输出文件
            if task.output_file and Path(task.output_file).exists():
                Path(task.output_file).unlink()

            # 从内存中移除
            del self._tasks[task_id]

            # 更新索引
            self.indexer.update_index()

            return True
        except Exception:
            return False

    def get_knowledge_items(self) -> List[Dict[str, Any]]:
        """
        获取知识库条目列表

        Returns:
            知识库条目列表
        """
        topics = []
        topics_dir = Path(self.config.output_dir) / "topics"

        if not topics_dir.exists():
            return topics

        import re
        import yaml

        for md_file in sorted(topics_dir.glob("*.md")):
            if md_file.name == "index.md":
                continue

            try:
                content = md_file.read_text(encoding="utf-8")

                # 解析 YAML frontmatter
                frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

                if frontmatter_match:
                    yaml_content = frontmatter_match.group(1)
                    data = yaml.safe_load(yaml_content) or {}

                    stat = md_file.stat()
                    topics.append({
                        "id": md_file.stem,
                        "title": data.get("title", md_file.stem),
                        "summary": data.get("summary", ""),
                        "tags": data.get("tags", []),
                        "file_path": f"topics/{md_file.name}",
                        "updated_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
                        "source": data.get("source", ""),
                    })
            except Exception:
                continue

        return topics

    def get_knowledge_detail(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        获取知识库条目详情

        Args:
            item_id: 条目 ID（文件名不含扩展名）

        Returns:
            条目详情字典
        """
        md_file = Path(self.config.output_dir) / "topics" / f"{item_id}.md"

        if not md_file.exists():
            return None

        try:
            import re
            import yaml

            content = md_file.read_text(encoding="utf-8")

            # 解析 YAML frontmatter
            frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

            if frontmatter_match:
                yaml_content = frontmatter_match.group(1)
                data = yaml.safe_load(yaml_content) or {}

                # 提取正文内容（去掉 frontmatter）
                body_content = content[frontmatter_match.end():]

                stat = md_file.stat()
                return {
                    "id": item_id,
                    "title": data.get("title", item_id),
                    "summary": data.get("summary", ""),
                    "tags": data.get("tags", []),
                    "content": body_content,
                    "file_path": f"topics/{md_file.name}",
                    "updated_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
                    "source": data.get("source", ""),
                    "generated_at": data.get("generated_at", ""),
                }
        except Exception:
            pass

        return None

    def get_stats(self) -> Dict[str, Any]:
        """
        获取处理统计信息

        Returns:
            统计信息字典
        """
        tasks = list(self._tasks.values())

        return {
            "total_documents": len(tasks),
            "completed": sum(1 for t in tasks if t.status == "completed"),
            "processing": sum(1 for t in tasks if t.status == "processing"),
            "failed": sum(1 for t in tasks if t.status == "failed"),
            "pending": sum(1 for t in tasks if t.status == "pending"),
            "total_knowledge_items": len(self.get_knowledge_items()),
            "last_updated": datetime.now().isoformat()
        }

    def rebuild_index(self) -> bool:
        """
        重建知识库索引

        Returns:
            是否成功
        """
        try:
            self.indexer.update_index()
            return True
        except Exception:
            return False


# 全局处理器实例（单例模式）
_processor: Optional[DocumentProcessor] = None


def get_processor() -> DocumentProcessor:
    """获取全局处理器实例"""
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor
