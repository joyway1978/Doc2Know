"""通用工具模块 - JSON解析、重试等共享功能"""

import json
import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """解析错误异常"""
    pass


def parse_json_response(response: str) -> Dict[str, Any]:
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
        ParseError: JSON解析失败时抛出
    """
    if not response or not response.strip():
        raise ParseError("LLM返回空响应")

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
            cleaned = clean_json_text(json_match.group(1))
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

    # 所有解析尝试失败，返回错误信息
    logger.error(f"无法解析JSON响应: {response[:200]}...")
    return {
        "error": "JSON解析失败",
        "raw_excerpt": response[:200],
    }


def clean_json_text(text: str) -> str:
    """清理JSON文本中的常见错误"""
    # 移除尾部逗号
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    # 修复单引号
    text = text.replace("'", '"')
    return text


def safe_filename(name: str) -> str:
    """
    将名称转换为安全的文件名

    处理规则：
    - 保留中文字符
    - 替换非法字符为连字符
    - 限制长度

    Args:
        name: 原始名称

    Returns:
        安全的文件名（不含扩展名）
    """
    if not name:
        return "untitled"

    # 定义非法字符
    illegal_chars = r'[<>:"/\\|?*]'

    # 替换非法字符为连字符
    safe = re.sub(illegal_chars, '-', name)

    # 替换多个连续连字符为单个
    safe = re.sub(r'-+', '-', safe)

    # 移除首尾连字符和空白
    safe = safe.strip('- ')

    # 限制长度（保留中文字符，所以按字符数而非字节数）
    if len(safe) > 50:
        safe = safe[:50].rsplit('-', 1)[0]

    return safe or "untitled"
