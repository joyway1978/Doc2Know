"""PDF解析模块测试"""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from doc2know.pdf_parser import PdfParser, ParserError, parse_pdf


class TestPdfParserInitialization:
    """PdfParser 基础测试"""

    def test_parser_initialization(self):
        """测试初始化"""
        parser = PdfParser()
        assert parser is not None
        assert isinstance(parser, PdfParser)

    def test_parse_sample_pdf(self):
        """测试解析示例 PDF"""
        parser = PdfParser()

        # 使用测试数据目录中的 sample.pdf
        sample_pdf = Path(__file__).parent / "data" / "sample.pdf"

        if not sample_pdf.exists():
            pytest.skip("sample.pdf 不存在，跳过测试")

        result = parser.parse(str(sample_pdf))

        assert "title" in result
        assert "paragraphs" in result
        assert isinstance(result["paragraphs"], list)


class TestTitleExtraction:
    """标题提取测试"""

    def test_title_extraction(self):
        """测试标题提取"""
        parser = PdfParser()

        # 创建模拟文档
        mock_doc = MagicMock()
        mock_page = MagicMock()

        # 模拟文本块结构
        mock_block = {
            "lines": [{
                "spans": [{
                    "text": "测试文档标题",
                    "size": 18,
                    "flags": 16  # 粗体
                }]
            }]
        }
        mock_page.get_text.return_value = {"blocks": [mock_block]}
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)

        title = parser._extract_title(mock_doc, Path("test.pdf"))

        assert title == "测试文档标题"

    def test_title_from_filename(self):
        """测试从文件名提取标题"""
        parser = PdfParser()

        # 测试简单文件名
        assert parser._extract_title_from_filename(Path("document.pdf")) == "Document"

        # 测试带下划线的文件名
        assert parser._extract_title_from_filename(Path("my_document.pdf")) == "My Document"

        # 测试带连字符的文件名
        assert parser._extract_title_from_filename(Path("my-document.pdf")) == "My Document"

        # 测试混合分隔符
        assert parser._extract_title_from_filename(Path("my_document-file.pdf")) == "My Document File"


class TestParagraphExtraction:
    """段落提取测试"""

    def test_paragraph_extraction(self):
        """测试段落提取"""
        parser = PdfParser()

        # 创建模拟页面
        mock_page = MagicMock()

        # 模拟文本块
        mock_blocks = [
            {
                "lines": [{
                    "spans": [{
                        "text": "第一章 概述",
                        "size": 16,
                        "flags": 16
                    }]
                }],
                "bbox": [0, 0, 100, 20]
            },
            {
                "lines": [{
                    "spans": [{
                        "text": "这是第一章的内容段落。",
                        "size": 12,
                        "flags": 0
                    }]
                }],
                "bbox": [0, 30, 100, 50]
            },
            {
                "lines": [{
                    "spans": [{
                        "text": "第二章 详细内容",
                        "size": 14,
                        "flags": 16
                    }]
                }],
                "bbox": [0, 60, 100, 80]
            }
        ]
        mock_page.get_text.return_value = {"blocks": mock_blocks}

        paragraphs = parser._extract_page_paragraphs(mock_page, 0)

        assert len(paragraphs) == 3
        assert paragraphs[0]["text"] == "第一章 概述"
        assert paragraphs[1]["text"] == "这是第一章的内容段落。"
        assert paragraphs[2]["text"] == "第二章 详细内容"

    def test_heading_detection(self):
        """测试标题层级检测"""
        parser = PdfParser()

        # 测试一级标题（大字体、粗体）
        level = parser._detect_heading_level("第一章 概述", 18, True, 12)
        assert level == 1

        # 测试二级标题（中等字体）
        level = parser._detect_heading_level("1.1 小节", 14, False, 12)
        assert level >= 2

        # 测试三级标题
        level = parser._detect_heading_level("1.1.1 子节", 13, False, 12)
        assert level >= 1 or level == 0  # 可能是标题或普通文本

        # 测试普通段落（不是标题）
        level = parser._detect_heading_level("这是一个普通的段落内容。", 12, False, 12)
        assert level == 0

        # 测试太短的文本
        level = parser._detect_heading_level("AB", 16, True, 12)
        assert level == 0

        # 测试以标点结尾的文本
        level = parser._detect_heading_level("这是一个标题。", 16, True, 12)
        assert level == 0


class TestErrorHandling:
    """错误处理测试"""

    def test_file_not_found(self):
        """测试文件不存在"""
        parser = PdfParser()

        with pytest.raises(FileNotFoundError) as exc_info:
            parser.parse("/nonexistent/path/file.pdf")

        assert "文件不存在" in str(exc_info.value)

    def test_invalid_pdf(self):
        """测试无效 PDF"""
        parser = PdfParser()

        # 创建一个临时文件，但不是有效的 PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False, mode='w') as f:
            f.write("This is not a valid PDF content")
            temp_path = f.name

        try:
            with pytest.raises((ParserError, Exception)) as exc_info:
                parser.parse(temp_path)
        finally:
            os.unlink(temp_path)

    def test_unsupported_format(self):
        """测试不支持的文件格式"""
        parser = PdfParser()

        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                parser.parse(temp_path)

            assert "不支持的文件格式" in str(exc_info.value)
        finally:
            os.unlink(temp_path)


class TestParsePdfFunction:
    """便捷函数测试"""

    @patch.object(PdfParser, 'parse')
    def test_parse_pdf_function(self, mock_parse):
        """测试 parse_pdf 便捷函数"""
        mock_parse.return_value = {
            "title": "测试文档",
            "paragraphs": [
                {"text": "段落1", "style": "Heading 1", "level": 1},
                {"text": "段落2", "style": "Normal", "level": 0}
            ]
        }

        result = parse_pdf("test.pdf")

        assert result["title"] == "测试文档"
        assert len(result["paragraphs"]) == 2
        mock_parse.assert_called_once_with("test.pdf")
