"""Word文档解析模块"""
import os
import re
import subprocess
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path

from .pdf_parser import PdfParser, parse_pdf


class DocxParser:
    """Word文档解析器，支持python-docx和pandoc两种解析方式"""

    def __init__(self):
        self._pandoc_available = None

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析Word文档，返回结构化的内容

        Args:
            file_path: Word文档路径

        Returns:
            {
                "title": "文档标题（从第一段或文件名推断）",
                "paragraphs": [
                    {"text": "段落文本", "style": "样式名", "level": 层级},
                    ...
                ]
            }
        """
        file_path = Path(file_path)

        if not file_path.suffix.lower() in ('.docx', '.doc'):
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 优先使用pandoc（如果可用）
        if self._is_pandoc_available():
            try:
                return self._parse_with_pandoc(file_path)
            except Exception as e:
                # pandoc失败时回退到python-docx
                pass

        return self._parse_with_python_docx(file_path)

    def _is_pandoc_available(self) -> bool:
        """检查pandoc是否可用"""
        if self._pandoc_available is None:
            self._pandoc_available = shutil.which("pandoc") is not None
        return self._pandoc_available

    def _parse_with_pandoc(self, file_path: Path) -> Dict[str, Any]:
        """使用pandoc解析docx文件"""
        try:
            result = subprocess.run(
                ["pandoc", "-f", "docx", "-t", "markdown", str(file_path)],
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=True
            )
            markdown_content = result.stdout
            return self._parse_markdown(markdown_content, file_path)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"pandoc解析失败: {e.stderr}") from e
        except UnicodeDecodeError as e:
            raise RuntimeError(f"文档编码错误: {e}") from e

    def _parse_markdown(self, content: str, file_path: Path) -> Dict[str, Any]:
        """解析markdown内容，提取结构和标题层级"""
        paragraphs = []
        lines = content.split('\n')

        title = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测标题
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()
                paragraphs.append({
                    "text": text,
                    "style": f"Heading {level}",
                    "level": level
                })
                # 第一个标题作为文档标题
                if title is None:
                    title = text
            else:
                # 普通段落
                paragraphs.append({
                    "text": line,
                    "style": "Normal",
                    "level": 0
                })

        # 如果没有找到标题，使用文件名
        if title is None:
            title = self._extract_title_from_filename(file_path)

        return {
            "title": title,
            "paragraphs": paragraphs
        }

    def _parse_with_python_docx(self, file_path: Path) -> Dict[str, Any]:
        """使用python-docx解析docx文件"""
        try:
            from docx import Document
        except ImportError as e:
            raise ImportError("请先安装python-docx: pip install python-docx") from e

        try:
            doc = Document(str(file_path))
        except Exception as e:
            raise RuntimeError(f"无法打开文档: {e}") from e

        paragraphs = []
        title = None

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            style_name = para.style.name if para.style else "Normal"
            level = self._extract_heading_level(style_name)

            paragraphs.append({
                "text": text,
                "style": style_name,
                "level": level
            })

            # 第一个标题或第一段作为文档标题
            if title is None and (level > 0 or len(paragraphs) == 1):
                title = text

        # 如果没有找到标题，使用文件名
        if title is None:
            title = self._extract_title_from_filename(file_path)

        return {
            "title": title,
            "paragraphs": paragraphs
        }

    def _extract_heading_level(self, style_name: str) -> int:
        """
        从样式名提取标题层级

        Args:
            style_name: Word样式名（如"Heading 1", "标题 1"等）

        Returns:
            标题层级（1-9），如果不是标题则返回0
        """
        if not style_name:
            return 0

        style_name = style_name.strip()

        # 匹配英文样式名: Heading 1, Heading1, heading 1等
        english_match = re.match(r'^[Hh]eading\s*(\d+)$', style_name)
        if english_match:
            level = int(english_match.group(1))
            return level if 1 <= level <= 9 else 0

        # 匹配中文样式名: 标题 1, 标题1等
        chinese_match = re.match(r'^标题\s*(\d+)$', style_name)
        if chinese_match:
            level = int(chinese_match.group(1))
            return level if 1 <= level <= 9 else 0

        # 匹配其他常见标题样式
        if style_name.lower() in ('title', '标题'):
            return 1

        return 0

    def _extract_title_from_filename(self, file_path: Path) -> str:
        """从文件名提取标题"""
        # 去掉扩展名
        name = file_path.stem
        # 替换下划线和连字符为空格
        name = re.sub(r'[_\-]+', ' ', name)
        # 首字母大写
        return name.strip().title()


def parse_docx(file_path: str) -> Dict[str, Any]:
    """
    便捷函数：解析Word文档

    Args:
        file_path: Word文档路径

    Returns:
        解析后的结构化内容
    """
    parser = DocxParser()
    return parser.parse(file_path)


def get_parser_for_file(file_path: str):
    """根据文件扩展名返回相应的解析器"""
    ext = Path(file_path).suffix.lower()
    if ext == '.pdf':
        return PdfParser()
    elif ext in ['.docx', '.doc']:
        return DocxParser()
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def parse_document(file_path: str) -> Dict[str, Any]:
    """自动检测文件类型并解析"""
    parser = get_parser_for_file(file_path)
    return parser.parse(file_path)
