"""PDF文档解析模块"""
import os
import re
from typing import Dict, Any, List
from pathlib import Path


class ParserError(Exception):
    """解析错误异常"""
    pass


class PdfParser:
    """PDF文档解析器，使用PyMuPDF (fitz)"""

    def __init__(self):
        pass

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析PDF文档，返回结构化的内容

        Args:
            file_path: PDF文档路径

        Returns:
            {
                "title": "文档标题（从第一页或文件名推断）",
                "paragraphs": [
                    {"text": "段落文本", "style": "样式名", "level": 层级},
                    ...
                ]
            }
        """
        file_path = Path(file_path)

        if not file_path.suffix.lower() == '.pdf':
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise ImportError("请先安装PyMuPDF: pip install PyMuPDF") from e

        try:
            doc = fitz.open(str(file_path))
        except Exception as e:
            raise ParserError(f"无法打开PDF文档: {e}") from e

        try:
            paragraphs = []
            title = self._extract_title(doc, file_path)

            for page_num, page in enumerate(doc):
                page_paragraphs = self._extract_page_paragraphs(page, page_num)
                paragraphs.extend(page_paragraphs)

            # 如果没有从内容中提取到标题，使用文件名
            if title is None:
                title = self._extract_title_from_filename(file_path)

            return {
                "title": title,
                "paragraphs": paragraphs
            }
        finally:
            doc.close()

    def _extract_title(self, doc, file_path: Path) -> str:
        """
        从第一页提取标题

        Args:
            doc: fitz文档对象
            file_path: 文件路径

        Returns:
            标题字符串，如果未找到则返回None
        """
        if len(doc) == 0:
            return None

        first_page = doc[0]

        # 获取带有字体信息的文本块
        blocks = first_page.get_text("dict").get("blocks", [])

        title_candidates = []

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue

                    font_size = span.get("size", 12)
                    flags = span.get("flags", 0)
                    is_bold = bool(flags & 2**4)  # 检查粗体标志

                    # 评分：字体越大、越粗，越可能是标题
                    score = font_size + (5 if is_bold else 0)

                    title_candidates.append({
                        "text": text,
                        "size": font_size,
                        "is_bold": is_bold,
                        "score": score
                    })

        if not title_candidates:
            return None

        # 按分数排序，选择最可能是标题的
        title_candidates.sort(key=lambda x: x["score"], reverse=True)

        # 选择分数最高且长度适中的文本作为标题
        for candidate in title_candidates:
            text = candidate["text"]
            # 标题通常不太长也不太短
            if 5 <= len(text) <= 100 and candidate["score"] >= 14:
                return text

        # 如果没有合适的，返回第一个非空文本（如果它看起来像标题）
        for candidate in title_candidates:
            text = candidate["text"]
            if len(text) <= 100 and not text.endswith((".", "。", "!", "！", "?", "？")):
                return text

        return None

    def _extract_page_paragraphs(self, page, page_num: int) -> List[Dict[str, Any]]:
        """
        从页面提取段落

        Args:
            page: fitz页面对象
            page_num: 页码（从0开始）

        Returns:
            段落列表
        """
        paragraphs = []

        # 获取文本块
        blocks = page.get_text("dict").get("blocks", [])

        # 收集所有文本块及其位置信息
        text_blocks = []

        for block in blocks:
            if "lines" not in block:
                continue

            block_text = []
            max_font_size = 0
            is_bold = False

            for line in block["lines"]:
                line_text = []
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    line_text.append(text)
                    font_size = span.get("size", 12)
                    flags = span.get("flags", 0)

                    if font_size > max_font_size:
                        max_font_size = font_size
                    if flags & 2**4:  # 粗体
                        is_bold = True

                block_text.append("".join(line_text))

            full_text = " ".join(block_text).strip()
            if full_text:
                text_blocks.append({
                    "text": full_text,
                    "font_size": max_font_size,
                    "is_bold": is_bold,
                    "bbox": block.get("bbox", [0, 0, 0, 0])
                })

        # 按垂直位置排序（从上到下）
        text_blocks.sort(key=lambda x: x["bbox"][1])

        # 分析文本块并分类
        avg_font_size = sum(b["font_size"] for b in text_blocks) / len(text_blocks) if text_blocks else 12

        for block in text_blocks:
            text = block["text"]
            font_size = block["font_size"]
            is_bold = block["is_bold"]

            # 启发式判断是否为标题
            level = self._detect_heading_level(text, font_size, is_bold, avg_font_size)

            if level > 0:
                style = f"Heading {level}"
            else:
                style = "Normal"

            paragraphs.append({
                "text": text,
                "style": style,
                "level": level
            })

        return paragraphs

    def _detect_heading_level(self, text: str, font_size: float, is_bold: bool, avg_font_size: float) -> int:
        """
        检测文本是否为标题及其层级

        Args:
            text: 文本内容
            font_size: 字体大小
            is_bold: 是否粗体
            avg_font_size: 平均字体大小

        Returns:
            标题层级（1-3），如果不是标题则返回0
        """
        # 清理文本用于判断
        clean_text = text.strip()

        # 空文本或太短的文本不太可能是标题
        if len(clean_text) < 3:
            return 0

        # 太长的文本不太可能是标题
        if len(clean_text) > 200:
            return 0

        # 以标点符号结尾的通常不是标题
        if clean_text.endswith((".", "。", "!", "！", "?", "？", ",", "，", ";", "；")):
            return 0

        score = 0

        # 字体大小判断
        if font_size > avg_font_size * 1.5:
            score += 3
        elif font_size > avg_font_size * 1.2:
            score += 2
        elif font_size > avg_font_size:
            score += 1

        # 粗体加分
        if is_bold:
            score += 2

        # 长度判断（标题通常较短）
        if len(clean_text) <= 50:
            score += 1
        if len(clean_text) <= 30:
            score += 1

        # 数字开头（如 "1. Introduction"）可能是标题
        if re.match(r'^\d+[\.\s]', clean_text):
            score += 1

        # 根据分数判断层级
        if score >= 5:
            return 1
        elif score >= 3:
            return 2
        elif score >= 2:
            return 3

        return 0

    def _extract_title_from_filename(self, file_path: Path) -> str:
        """从文件名提取标题"""
        # 去掉扩展名
        name = file_path.stem
        # 替换下划线和连字符为空格
        name = re.sub(r'[_\-]+', ' ', name)
        # 首字母大写
        return name.strip().title()


def parse_pdf(file_path: str) -> Dict[str, Any]:
    """
    便捷函数：解析PDF文档

    Args:
        file_path: PDF文档路径

    Returns:
        解析后的结构化内容
    """
    parser = PdfParser()
    return parser.parse(file_path)
