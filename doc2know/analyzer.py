"""内容分析模块 - LLM调用和JSON解析"""

import json
import re
import time
from typing import Dict, Any, List, Optional

from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

from .config import Config

logger = logging.getLogger(__name__)


class AnalyzerError(Exception):
    """分析器错误异常"""
    pass


class LLMAnalyzer:
    """LLM文档分析器，封装OpenAI API调用和JSON解析"""

    # 系统Prompt，用于指导LLM分析文档
    SYSTEM_PROMPT = """你是一个文档结构分析师。请将输入的文档内容分析整理成结构化格式。

要求：
1. 识别文档的主要主题和子主题
2. 提取关键信息点，去除冗余内容
3. 保持原文的准确性，不添加未提及的内容
4. 为文档生成一个简短的标题（不超过20字）
5. 生成一段摘要（不超过100字）
6. 给文档打上3-5个标签（标签由LLM根据内容自动生成）

输出必须是JSON格式：
{
  "title": "文档标题",
  "summary": "文档摘要",
  "tags": ["标签1", "标签2"],
  "sections": [
    {
      "heading": "一级标题",
      "subsections": [
        {"heading": "二级标题", "content": "内容..."}
      ]
    }
  ]
}

如果内容无法解析为结构化格式，返回：
{"error": "无法解析的原因说明", "raw_excerpt": "原文前200字"}"""

    def __init__(self, config: Config):
        """
        初始化LLM分析器

        Args:
            config: Config对象，包含API配置
        """
        self.config = config
        self.chunk_size = config.chunk_size

        # 初始化OpenAI客户端
        llm_config = config.llm
        self.client = OpenAI(
            base_url=llm_config.get("base_url", "https://api.openai.com/v1"),
            api_key=llm_config.get("api_key", ""),
            timeout=60.0,
        )
        self.model = llm_config.get("model", "gpt-3.5-turbo")

    def analyze(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用LLM分析文档内容

        Args:
            content: parser返回的结构（title, paragraphs）

        Returns:
            JSON解析后的结构（title, summary, tags, sections）

        Raises:
            AnalyzerError: 分析失败时抛出
        """
        title = content.get("title", "未命名文档")
        paragraphs = content.get("paragraphs", [])

        if not paragraphs:
            return {
                "title": title,
                "summary": "文档内容为空",
                "tags": ["空文档"],
                "sections": [],
            }

        # 将段落转换为文本
        text_content = self._paragraphs_to_text(paragraphs)

        # 检查是否需要分块处理
        if len(text_content) > self.chunk_size:
            return self._analyze_chunks(text_content, title)
        else:
            return self._analyze_single(text_content, title)

    def _paragraphs_to_text(self, paragraphs: List[Dict[str, Any]]) -> str:
        """将段落列表转换为文本"""
        lines = []
        for para in paragraphs:
            text = para.get("text", "").strip()
            if not text:
                continue

            level = para.get("level", 0)
            if level > 0:
                # 标题添加标记
                lines.append(f"{'#' * level} {text}")
            else:
                lines.append(text)

        return "\n\n".join(lines)

    def _analyze_single(self, text: str, title: str) -> Dict[str, Any]:
        """分析单个文本块"""
        prompt = self._build_prompt(text, title)

        try:
            response = self._call_llm(prompt)
            return self._parse_json_response(response)
        except Exception as e:
            logger.error(f"分析文档失败: {e}")
            return {
                "title": title,
                "summary": f"分析失败: {str(e)}",
                "tags": ["分析失败"],
                "sections": [],
                "error": str(e),
            }

    def _analyze_chunks(self, text: str, title: str) -> Dict[str, Any]:
        """
        分块分析长文档

        策略：
        1. 按段落分割文档
        2. 累积段落直到接近chunk_size
        3. 每次调用LLM处理一个块
        4. 最后汇总所有块的结构信息
        """
        chunks = self._split_into_chunks(text)
        logger.info(f"文档'{title}'被分割为{len(chunks)}个块进行处理")

        results = []
        for i, chunk in enumerate(chunks):
            logger.info(f"处理第{i+1}/{len(chunks)}个块")
            chunk_result = self._analyze_single(chunk, f"{title} (部分{i+1})")
            results.append(chunk_result)

        # 合并所有块的结果
        return self._merge_results(results, title)

    def _split_into_chunks(self, text: str) -> List[str]:
        """将文本分割成多个块"""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            # 如果单个段落就超过chunk_size，直接作为一个块
            if para_size > self.chunk_size:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_size = 0
                chunks.append(para)
                continue

            # 如果添加这个段落会超过chunk_size，先保存当前块
            if current_size + para_size + 2 > self.chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_size = 0

            current_chunk.append(para)
            current_size += para_size + 2  # +2 for "\n\n"

        # 添加最后一个块
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def _merge_results(self, results: List[Dict[str, Any]], title: str) -> Dict[str, Any]:
        """合并多个块的分析结果"""
        if not results:
            return {
                "title": title,
                "summary": "无内容",
                "tags": [],
                "sections": [],
            }

        if len(results) == 1:
            result = results[0].copy()
            result["title"] = title
            return result

        # 合并所有标签（去重）
        all_tags = set()
        for r in results:
            tags = r.get("tags", [])
            all_tags.update(tags)

        # 限制标签数量
        tags = list(all_tags)[:5]

        # 合并所有章节
        all_sections = []
        for r in results:
            sections = r.get("sections", [])
            all_sections.extend(sections)

        # 合并摘要
        summaries = [r.get("summary", "") for r in results if r.get("summary")]
        merged_summary = " ".join(summaries)[:100] if summaries else "长文档，内容较多"

        return {
            "title": title,
            "summary": merged_summary,
            "tags": tags,
            "sections": all_sections,
        }

    def _build_prompt(self, text: str, title: str) -> str:
        """构建LLM提示词"""
        return f"""请分析以下文档内容：

文档标题：{title}

文档内容：
{text}

请按照系统指令返回JSON格式的分析结果。"""

    @retry(
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _call_llm(self, prompt: str) -> str:
        """
        调用OpenAI API，带重试机制

        重试策略：
        - API限流：指数退避重试（1s, 2s, 4s, 8s）
        - 网络超时：重试4次后抛出异常

        Args:
            prompt: 提示词

        Returns:
            API响应文本

        Raises:
            AnalyzerError: API调用失败时抛出
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # 低温度以获得更确定的输出
                max_tokens=2000,
            )

            if not response.choices or not response.choices[0].message:
                raise AnalyzerError("API返回空响应")

            return response.choices[0].message.content or ""

        except RateLimitError as e:
            logger.warning(f"API限流，将进行重试: {e}")
            raise
        except APITimeoutError as e:
            logger.warning(f"API超时，将进行重试: {e}")
            raise
        except APIError as e:
            logger.error(f"API错误: {e}")
            raise AnalyzerError(f"API调用失败: {e}") from e
        except Exception as e:
            logger.error(f"调用LLM时发生未知错误: {e}")
            raise AnalyzerError(f"调用LLM失败: {e}") from e

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        解析JSON响应，处理格式错误

        错误处理策略：
        - 尝试直接解析JSON
        - 如果失败，使用正则提取JSON块
        - 如果仍失败，标记需人工检查

        Args:
            response: LLM响应文本

        Returns:
            解析后的字典

        Raises:
            AnalyzerError: JSON解析失败时抛出
        """
        if not response or not response.strip():
            raise AnalyzerError("LLM返回空响应")

        # 尝试直接解析
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # 尝试提取JSON代码块
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取花括号包围的内容
        json_match = re.search(r'(\{[\s\S]*\})', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败，尝试清理后重试: {e}")
                # 尝试清理常见错误
                cleaned = self._clean_json_text(json_match.group(1))
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    pass

        # 所有解析尝试失败，返回错误信息
        logger.error(f"无法解析JSON响应: {response[:200]}...")
        return {
            "error": "JSON解析失败",
            "raw_excerpt": response[:200],
            "title": "解析失败",
            "summary": "无法解析LLM返回的内容",
            "tags": ["解析错误"],
            "sections": [],
        }

    def _clean_json_text(self, text: str) -> str:
        """清理JSON文本中的常见错误"""
        # 移除尾部逗号
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        # 修复单引号
        text = text.replace("'", '"')
        return text


def analyze_content(content: Dict[str, Any], config: Config) -> Dict[str, Any]:
    """
    便捷函数：分析文档内容

    Args:
        content: parser返回的结构
        config: Config对象

    Returns:
        分析后的结构化结果
    """
    analyzer = LLMAnalyzer(config)
    return analyzer.analyze(content)
