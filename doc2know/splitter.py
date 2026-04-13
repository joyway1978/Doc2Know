"""智能文档拆分模块 - 将单个文档拆分为多个主题文档"""

import asyncio
import logging
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from pydantic import BaseModel, Field, ValidationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .config import Config
from .utils import parse_json_response, safe_filename

logger = logging.getLogger(__name__)


class SplitStrategy(str, Enum):
    """文档拆分策略"""
    CONSERVATIVE = "conservative"  # 3-5个大类
    AGGRESSIVE = "aggressive"      # 6-10个专题


class Topic(BaseModel):
    """细粒度主题模型"""
    topic_id: str = Field(..., description="主题唯一标识")
    topic_name: str = Field(..., description="主题名称")
    related_sections: List[str] = Field(default_factory=list, description="相关原文段落引用")


class Category(BaseModel):
    """大分类模型"""
    category_name: str = Field(..., description="分类名称")
    topic_ids: List[str] = Field(..., description="包含的主题ID列表")


class CategoryContent(BaseModel):
    """分类内容模型"""
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="Markdown格式内容")
    source_refs: List[str] = Field(default_factory=list, description="来源引用")


class SplitResult(BaseModel):
    """拆分结果模型"""
    version_dir: str = Field(..., description="版本目录路径")
    categories: List[str] = Field(default_factory=list, description="生成的分类名称列表")
    files: List[str] = Field(default_factory=list, description="生成的文件路径列表")
    errors: List[str] = Field(default_factory=list, description="错误信息列表")


class SplitterError(Exception):
    """拆分器错误异常"""
    pass


class DocumentSplitter:
    """智能文档拆分器，实现三阶段分析流程"""

    def __init__(self, config: Config, strategy: SplitStrategy = SplitStrategy.CONSERVATIVE):
        """
        初始化文档拆分器

        Args:
            config: 配置对象
            strategy: 拆分策略，默认为保守策略
        """
        self.config = config
        self.strategy = strategy
        self.chunk_size = config.chunk_size
        self.max_concurrent = config.max_concurrent

        # 初始化OpenAI客户端
        llm_config = config.llm
        self.client = OpenAI(
            base_url=llm_config.get("base_url", "https://api.openai.com/v1"),
            api_key=llm_config.get("api_key", ""),
            timeout=60.0,
        )
        self.model = llm_config.get("model", "gpt-3.5-turbo")

        # 加载提示词
        self._load_prompts()

        # 并发控制
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

    def _load_prompts(self) -> None:
        """加载提示词文件"""
        prompts_dir = Path(__file__).parent.parent / "prompts"

        # 阶段1: 主题提取
        extract_topics_path = prompts_dir / "extract_topics.txt"
        if extract_topics_path.exists():
            self._prompt_extract_topics = extract_topics_path.read_text(encoding="utf-8")
        else:
            self._prompt_extract_topics = self._default_extract_topics_prompt()

        # 阶段2: 分类合并
        merge_categories_path = prompts_dir / "merge_categories.txt"
        if merge_categories_path.exists():
            self._prompt_merge_categories = merge_categories_path.read_text(encoding="utf-8")
        else:
            self._prompt_merge_categories = self._default_merge_categories_prompt()

        # 阶段3: 内容提取
        extract_content_path = prompts_dir / "extract_content.txt"
        if extract_content_path.exists():
            self._prompt_extract_content = extract_content_path.read_text(encoding="utf-8")
        else:
            self._prompt_extract_content = self._default_extract_content_prompt()

    def _default_extract_topics_prompt(self) -> str:
        """默认主题提取提示词"""
        return """请分析以下文档内容，识别其中所有独立的内容主题。

要求：
1. 提取文档中所有具体的、独立的内容主题
2. 不要合并或归类，保持主题的原始粒度
3. 每个主题应该代表一个完整的内容单元
4. 记录主题相关的原文段落位置（如果有明确的章节编号）

输出JSON格式：
{
  "topics": [
    {
      "topic_id": "t1",
      "topic_name": "主题名称（简洁明了）",
      "related_sections": ["1.1", "3.2"]
    }
  ]
}

文档标题：{title}

文档内容：
{content}"""

    def _default_merge_categories_prompt(self) -> str:
        """默认分类合并提示词"""
        if self.strategy == SplitStrategy.CONSERVATIVE:
            category_range = "3-5个"
            strategy_desc = "合并为较少的主要类别"
        else:
            category_range = "6-10个"
            strategy_desc = "拆分为较多的专题"

        return f"""请分析以下细粒度主题列表，将语义相关的主题合并为{category_range}个大分类。

策略：{strategy_desc}
- conservative模式：生成3-5个大类，每个类包含多个相关主题
- aggressive模式：生成6-10个专题，每个专题更聚焦

要求：
1. 基于主题名称的语义相似度进行合并
2. 每个分类应该有一个清晰、描述性的名称
3. 确保分类之间的边界清晰
4. 当前策略: {self.strategy.value}

输出JSON格式：
{{
  "categories": [
    {{
      "category_name": "分类名称",
      "topic_ids": ["t1", "t5"]
    }}
  ]
}}

主题列表：
{{topics_json}}"""

    def _default_extract_content_prompt(self) -> str:
        """默认内容提取提示词"""
        return """请从以下文档中提取与指定分类相关的内容，生成完整的Markdown文档。

要求：
1. 只提取与该分类主题相关的内容
2. 保持原文的准确性，不添加未提及的内容
3. 生成标准的Markdown格式，包含适当的标题层级
4. 记录内容来源的原文位置

输出JSON格式：
{
  "title": "文档标题",
  "content": "Markdown格式的完整内容...",
  "source_refs": ["原文段落引用"]
}

原始文档标题：{title}

分类名称：{category_name}

分类包含的主题：{topic_names}

原始文档内容：
{content}"""

    @retry(
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        异步调用LLM

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）

        Returns:
            LLM响应文本
        """
        async with self._semaphore:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            try:
                # 使用线程池执行同步的OpenAI调用
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=0.3,
                        max_tokens=2000,
                    )
                )

                if not response.choices or not response.choices[0].message:
                    raise SplitterError("API返回空响应")

                return response.choices[0].message.content or ""

            except RateLimitError as e:
                logger.warning(f"API限流，将进行重试: {e}")
                raise
            except APITimeoutError as e:
                logger.warning(f"API超时，将进行重试: {e}")
                raise
            except APIError as e:
                logger.error(f"API错误: {e}")
                raise SplitterError(f"API调用失败: {e}") from e

    async def extract_topics(self, content: Dict[str, Any]) -> Tuple[List[Topic], Optional[str]]:
        """
        阶段1: 提取细粒度主题

        Args:
            content: 解析后的文档内容

        Returns:
            (主题列表, 错误信息)
        """
        title = content.get("title", "未命名文档")
        paragraphs = content.get("paragraphs", [])

        if not paragraphs:
            return [], "文档内容为空"

        # 将段落转换为文本
        text_content = self._paragraphs_to_text(paragraphs)

        # 检查是否需要分块
        if len(text_content) > self.chunk_size:
            return await self._extract_topics_chunked(text_content, title)

        prompt = self._prompt_extract_topics.format(
            title=title,
            content=text_content
        )

        try:
            response = await self._call_llm(prompt)
            result = parse_json_response(response)

            if "error" in result:
                return [], f"主题提取失败: {result.get('error')}"

            topics_data = result.get("topics", [])
            topics = [Topic(**t) for t in topics_data]

            return topics, None

        except Exception as e:
            logger.error(f"主题提取失败: {e}")
            return [], f"主题提取失败: {str(e)}"

    def _paragraphs_to_text(self, paragraphs: List[Dict[str, Any]]) -> str:
        """将段落列表转换为文本"""
        lines = []
        for para in paragraphs:
            text = para.get("text", "").strip()
            if not text:
                continue

            level = para.get("level", 0)
            if level > 0:
                lines.append(f"{'#' * level} {text}")
            else:
                lines.append(text)

        return "\n\n".join(lines)

    async def _extract_topics_chunked(self, text: str, title: str) -> Tuple[List[Topic], Optional[str]]:
        """分块提取主题"""
        chunks = self._split_into_chunks(text)
        logger.info(f"文档'{title}'被分割为{len(chunks)}个块进行主题提取")

        all_topics = []
        for i, chunk in enumerate(chunks):
            logger.info(f"处理第{i+1}/{len(chunks)}个块")
            prompt = self._prompt_extract_topics.format(
                title=f"{title} (部分{i+1})",
                content=chunk
            )

            try:
                response = await self._call_llm(prompt)
                result = parse_json_response(response)

                if "error" not in result:
                    topics_data = result.get("topics", [])
                    # 为每个块的主题添加前缀以避免ID冲突
                    for t in topics_data:
                        t["topic_id"] = f"chunk{i}_{t.get('topic_id', 'unknown')}"
                    all_topics.extend([Topic(**t) for t in topics_data])

            except Exception as e:
                logger.warning(f"第{i+1}个块主题提取失败: {e}")

        if not all_topics:
            return [], "所有块的主题提取都失败了"

        return all_topics, None

    def _split_into_chunks(self, text: str) -> List[str]:
        """将文本分割成多个块"""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            if para_size > self.chunk_size:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_size = 0
                chunks.append(para)
                continue

            if current_size + para_size + 2 > self.chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_size = 0

            current_chunk.append(para)
            current_size += para_size + 2

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    async def merge_categories(self, topics: List[Topic]) -> Tuple[List[Category], Optional[str]]:
        """
        阶段2: 合并主题为大分类

        Args:
            topics: 细粒度主题列表

        Returns:
            (分类列表, 错误信息)
        """
        if not topics:
            return [], "没有主题可以合并"

        # 构建主题JSON
        topics_json = []
        for t in topics:
            topics_json.append({
                "topic_id": t.topic_id,
                "topic_name": t.topic_name,
            })

        import json
        prompt = self._prompt_merge_categories.format(
            topics_json=json.dumps({"topics": topics_json}, ensure_ascii=False)
        )

        try:
            response = await self._call_llm(prompt)
            result = parse_json_response(response)

            if "error" in result:
                return [], f"分类合并失败: {result.get('error')}"

            categories_data = result.get("categories", [])
            categories = [Category(**c) for c in categories_data]

            # 验证分类数量
            if self.strategy == SplitStrategy.CONSERVATIVE:
                if len(categories) < 3 or len(categories) > 5:
                    logger.warning(f"保守策略下分类数量为{len(categories)}，不符合预期范围3-5")
            else:
                if len(categories) < 6 or len(categories) > 10:
                    logger.warning(f"激进策略下分类数量为{len(categories)}，不符合预期范围6-10")

            return categories, None

        except Exception as e:
            logger.error(f"分类合并失败: {e}")
            return [], f"分类合并失败: {str(e)}"

    async def extract_content_for_category(
        self,
        content: Dict[str, Any],
        category: Category,
        topics: List[Topic]
    ) -> Tuple[Optional[CategoryContent], Optional[str]]:
        """
        阶段3: 为单个分类提取内容

        Args:
            content: 原始文档内容
            category: 目标分类
            topics: 所有主题（用于查找分类包含的主题名称）

        Returns:
            (分类内容, 错误信息)
        """
        title = content.get("title", "未命名文档")
        paragraphs = content.get("paragraphs", [])

        if not paragraphs:
            return None, "文档内容为空"

        # 获取分类包含的主题名称
        topic_names = []
        for topic_id in category.topic_ids:
            for t in topics:
                if t.topic_id == topic_id:
                    topic_names.append(t.topic_name)
                    break

        text_content = self._paragraphs_to_text(paragraphs)

        # 如果内容太长，可能需要分块处理
        if len(text_content) > self.chunk_size * 2:  # 阶段3允许更大的内容
            return await self._extract_content_chunked(content, category, topics)

        prompt = self._prompt_extract_content.format(
            title=title,
            category_name=category.category_name,
            topic_names=", ".join(topic_names),
            content=text_content
        )

        try:
            response = await self._call_llm(prompt)
            result = parse_json_response(response)

            if "error" in result:
                return None, f"内容提取失败: {result.get('error')}"

            content_data = CategoryContent(**result)
            return content_data, None

        except ValidationError as e:
            logger.error(f"内容格式验证失败: {e}")
            return None, f"内容格式验证失败: {str(e)}"
        except Exception as e:
            logger.error(f"内容提取失败: {e}")
            return None, f"内容提取失败: {str(e)}"

    async def _extract_content_chunked(
        self,
        content: Dict[str, Any],
        category: Category,
        topics: List[Topic]
    ) -> Tuple[Optional[CategoryContent], Optional[str]]:
        """分块提取分类内容"""
        title = content.get("title", "未命名文档")
        paragraphs = content.get("paragraphs", [])
        text_content = self._paragraphs_to_text(paragraphs)

        # 分块处理
        chunks = self._split_into_chunks(text_content)
        logger.info(f"分类'{category.category_name}'内容分{len(chunks)}个块处理")

        all_contents = []
        all_refs = []

        topic_names = []
        for topic_id in category.topic_ids:
            for t in topics:
                if t.topic_id == topic_id:
                    topic_names.append(t.topic_name)
                    break

        for i, chunk in enumerate(chunks):
            prompt = self._prompt_extract_content.format(
                title=f"{title} (部分{i+1})",
                category_name=category.category_name,
                topic_names=", ".join(topic_names),
                content=chunk
            )

            try:
                response = await self._call_llm(prompt)
                result = parse_json_response(response)

                if "error" not in result:
                    all_contents.append(result.get("content", ""))
                    all_refs.extend(result.get("source_refs", []))

            except Exception as e:
                logger.warning(f"分类'{category.category_name}'第{i+1}块处理失败: {e}")

        if not all_contents:
            return None, "所有块的内容提取都失败了"

        combined_content = "\n\n".join(all_contents)
        return CategoryContent(
            title=category.category_name,
            content=combined_content,
            source_refs=list(set(all_refs))  # 去重
        ), None

    async def split_document(self, content: Dict[str, Any]) -> SplitResult:
        """
        执行完整的三阶段文档拆分流程

        Args:
            content: 解析后的文档内容

        Returns:
            拆分结果
        """
        result = SplitResult(version_dir="", categories=[], files=[], errors=[])

        # 创建版本目录
        version_dir = self._create_version_dir()
        result.version_dir = str(version_dir)

        topics_dir = version_dir / "topics"
        topics_dir.mkdir(exist_ok=True)

        # 阶段1: 提取主题
        logger.info("阶段1: 提取细粒度主题...")
        topics, error = await self.extract_topics(content)

        if error:
            logger.error(f"阶段1失败: {error}")
            # 降级策略: 回退到单文件模式
            return await self._fallback_single_file(content, version_dir)

        logger.info(f"提取到 {len(topics)} 个主题")

        # 阶段2: 合并分类
        logger.info("阶段2: 合并主题为大分类...")
        categories, error = await self.merge_categories(topics)

        if error:
            logger.error(f"阶段2失败: {error}")
            # 降级策略: 使用原始主题作为分类
            categories = [Category(category_name=t.topic_name, topic_ids=[t.topic_id]) for t in topics]
            result.errors.append(f"分类合并失败，使用原始主题: {error}")

        logger.info(f"合并为 {len(categories)} 个分类")
        result.categories = [c.category_name for c in categories]

        # 阶段3: 提取内容（并行处理）
        logger.info("阶段3: 为每个分类提取内容...")
        content_tasks = [
            self.extract_content_for_category(content, cat, topics)
            for cat in categories
        ]

        contents_results = await asyncio.gather(*content_tasks, return_exceptions=True)

        # 生成文件
        for i, (cat_content, error) in enumerate(contents_results):
            if isinstance(cat_content, Exception):
                error_msg = f"分类 '{categories[i].category_name}' 处理异常: {str(cat_content)}"
                logger.error(error_msg)
                result.errors.append(error_msg)
                continue

            if error:
                error_msg = f"分类 '{categories[i].category_name}' 提取失败: {error}"
                logger.error(error_msg)
                result.errors.append(error_msg)
                continue

            if cat_content:
                # 生成文件名
                filename = safe_filename(cat_content.title) + ".md"
                filepath = topics_dir / filename

                # 写入文件
                self._write_markdown_file(filepath, cat_content, content.get("title", ""))
                result.files.append(str(filepath))
                logger.info(f"生成文件: {filepath}")

        # 更新latest软链接
        self._update_latest_symlink(version_dir)

        return result

    async def _fallback_single_file(self, content: Dict[str, Any], version_dir: Path) -> SplitResult:
        """降级策略: 生成单个Markdown文件"""
        from .generator import MarkdownGenerator

        result = SplitResult(version_dir=str(version_dir), categories=[], files=[], errors=[])

        # 使用原有的生成器
        generator = MarkdownGenerator(str(version_dir))

        # 构建简化分析结果
        analysis_result = {
            "title": content.get("title", "未命名文档"),
            "summary": "智能拆分失败，生成单文件版本",
            "tags": ["单文件版本"],
            "sections": [{"heading": "内容", "subsections": [{"heading": "", "content": self._paragraphs_to_text(content.get("paragraphs", []))}]}]
        }

        output_file = generator.generate(analysis_result, content.get("source_file", "unknown"))
        result.files.append(output_file)
        result.errors.append("智能拆分失败，已生成单文件版本")

        return result

    def _create_version_dir(self) -> Path:
        """创建版本目录"""
        base_output = Path(self.config.output_dir)
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
        version_dir = base_output / timestamp

        # 原子性目录创建
        temp_dir = base_output / f".{timestamp}.tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        (temp_dir / "topics").mkdir(exist_ok=True)

        # 原子重命名
        temp_dir.rename(version_dir)

        return version_dir

    def _update_latest_symlink(self, version_dir: Path) -> None:
        """更新latest软链接"""
        base_output = Path(self.config.output_dir)
        latest_link = base_output / "latest"

        try:
            # 删除旧链接
            if latest_link.exists() or latest_link.is_symlink():
                latest_link.unlink()

            # 创建相对路径的软链接
            relative_target = version_dir.relative_to(base_output)
            latest_link.symlink_to(relative_target)

        except OSError as e:
            logger.warning(f"无法更新latest软链接: {e}")

    def _write_markdown_file(self, filepath: Path, content: CategoryContent, source_title: str) -> None:
        """写入Markdown文件"""
        from datetime import datetime

        frontmatter = f"""---
title: "{content.title}"
source: "{source_title}"
generated_at: "{datetime.now().isoformat()}"
---

"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter)
            f.write(content.content)


async def split_document(content: Dict[str, Any], config: Config, strategy: SplitStrategy = SplitStrategy.CONSERVATIVE) -> SplitResult:
    """
    便捷函数：拆分文档

    Args:
        content: 解析后的文档内容
        config: 配置对象
        strategy: 拆分策略

    Returns:
        拆分结果
    """
    splitter = DocumentSplitter(config, strategy)
    return await splitter.split_document(content)
