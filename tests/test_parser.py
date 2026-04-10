"""解析模块测试"""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from doc2know.parser import DocxParser, parse_docx


class TestDocxParserInit:
    """测试DocxParser初始化"""

    def test_init(self):
        """测试初始化"""
        parser = DocxParser()
        assert parser._pandoc_available is None


class TestDocxParserFileValidation:
    """测试文件格式验证"""

    def test_unsupported_format(self):
        """测试不支持的文件格式"""
        parser = DocxParser()

        with pytest.raises(ValueError) as exc_info:
            parser.parse("test.txt")
        assert "不支持的文件格式" in str(exc_info.value)

    def test_nonexistent_file(self):
        """测试文件不存在"""
        parser = DocxParser()

        with pytest.raises(FileNotFoundError) as exc_info:
            parser.parse("/nonexistent/file.docx")
        assert "文件不存在" in str(exc_info.value)


class TestDocxParserHeadingLevel:
    """测试标题层级提取"""

    def test_extract_english_heading(self):
        """测试英文标题样式"""
        parser = DocxParser()

        assert parser._extract_heading_level("Heading 1") == 1
        assert parser._extract_heading_level("Heading 2") == 2
        assert parser._extract_heading_level("Heading 9") == 9
        assert parser._extract_heading_level("heading 1") == 1
        assert parser._extract_heading_level("Heading1") == 1

    def test_extract_chinese_heading(self):
        """测试中文标题样式"""
        parser = DocxParser()

        assert parser._extract_heading_level("标题 1") == 1
        assert parser._extract_heading_level("标题 2") == 2
        assert parser._extract_heading_level("标题1") == 1

    def test_extract_special_headings(self):
        """测试特殊标题样式"""
        parser = DocxParser()

        assert parser._extract_heading_level("Title") == 1
        assert parser._extract_heading_level("title") == 1
        assert parser._extract_heading_level("标题") == 1

    def test_extract_normal_style(self):
        """测试普通样式"""
        parser = DocxParser()

        assert parser._extract_heading_level("Normal") == 0
        assert parser._extract_heading_level("正文") == 0
        assert parser._extract_heading_level("") == 0
        assert parser._extract_heading_level(None) == 0

    def test_extract_out_of_range(self):
        """测试超出范围的标题层级"""
        parser = DocxParser()

        assert parser._extract_heading_level("Heading 10") == 0
        assert parser._extract_heading_level("Heading 0") == 0


class TestDocxParserFilenameExtraction:
    """测试文件名标题提取"""

    def test_extract_from_filename_simple(self):
        """测试简单文件名"""
        parser = DocxParser()

        path = Path("document.docx")
        assert parser._extract_title_from_filename(path) == "Document"

    def test_extract_from_filename_with_underscores(self):
        """测试带下划线的文件名"""
        parser = DocxParser()

        path = Path("my_document_file.docx")
        assert parser._extract_title_from_filename(path) == "My Document File"

    def test_extract_from_filename_with_hyphens(self):
        """测试带连字符的文件名"""
        parser = DocxParser()

        path = Path("my-document-file.docx")
        assert parser._extract_title_from_filename(path) == "My Document File"

    def test_extract_from_filename_mixed(self):
        """测试混合分隔符的文件名"""
        parser = DocxParser()

        path = Path("my_document-file.docx")
        assert parser._extract_title_from_filename(path) == "My Document File"


class TestDocxParserMarkdownParsing:
    """测试Markdown解析"""

    def test_parse_markdown_headings(self):
        """测试解析Markdown标题"""
        parser = DocxParser()

        markdown = """# Main Title

## Section 1

Content here.

## Section 2

More content."""

        result = parser._parse_markdown(markdown, Path("test.docx"))

        assert result["title"] == "Main Title"
        assert len(result["paragraphs"]) == 5

        # 检查标题
        assert result["paragraphs"][0]["text"] == "Main Title"
        assert result["paragraphs"][0]["style"] == "Heading 1"
        assert result["paragraphs"][0]["level"] == 1

        assert result["paragraphs"][1]["text"] == "Section 1"
        assert result["paragraphs"][1]["style"] == "Heading 2"
        assert result["paragraphs"][1]["level"] == 2

    def test_parse_markdown_no_headings(self):
        """测试没有标题的Markdown"""
        parser = DocxParser()

        markdown = """This is just some content.

More content here."""

        result = parser._parse_markdown(markdown, Path("my_document.docx"))

        # 应该使用文件名作为标题
        assert result["title"] == "My Document"
        assert len(result["paragraphs"]) == 2

    def test_parse_markdown_empty_lines(self):
        """测试带空行的Markdown"""
        parser = DocxParser()

        markdown = """# Title



Content after empty lines.


"""

        result = parser._parse_markdown(markdown, Path("test.docx"))

        # 空行应该被跳过
        assert result["title"] == "Title"
        assert len(result["paragraphs"]) == 2


class TestDocxParserPandoc:
    """测试Pandoc解析"""

    @patch('shutil.which')
    def test_pandoc_available(self, mock_which):
        """测试pandoc可用性检查"""
        mock_which.return_value = "/usr/bin/pandoc"

        parser = DocxParser()
        assert parser._is_pandoc_available() is True

    @patch('shutil.which')
    def test_pandoc_not_available(self, mock_which):
        """测试pandoc不可用"""
        mock_which.return_value = None

        parser = DocxParser()
        assert parser._is_pandoc_available() is False

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_parse_with_pandoc(self, mock_run, mock_which):
        """测试使用pandoc解析"""
        mock_which.return_value = "/usr/bin/pandoc"
        mock_run.return_value = MagicMock(
            stdout="# Test Document\n\nThis is content.",
            stderr="",
            returncode=0
        )

        parser = DocxParser()

        # 创建一个临时文件
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            temp_path = f.name

        try:
            result = parser._parse_with_pandoc(Path(temp_path))

            assert result["title"] == "Test Document"
            assert len(result["paragraphs"]) == 2

            # 验证pandoc被调用
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "pandoc"
        finally:
            os.unlink(temp_path)


class TestDocxParserPythonDocx:
    """测试python-docx解析"""

    @patch('docx.Document')
    def test_parse_with_python_docx(self, mock_document_class):
        """测试使用python-docx解析"""
        # 创建模拟文档
        mock_doc = MagicMock()

        # 创建模拟段落
        mock_para1 = MagicMock()
        mock_para1.text = "Document Title"
        mock_para1.style.name = "Heading 1"

        mock_para2 = MagicMock()
        mock_para2.text = "Some content here."
        mock_para2.style.name = "Normal"

        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_document_class.return_value = mock_doc

        parser = DocxParser()

        # 创建一个临时文件
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            temp_path = f.name

        try:
            result = parser._parse_with_python_docx(Path(temp_path))

            assert result["title"] == "Document Title"
            assert len(result["paragraphs"]) == 2

            # 验证段落内容
            assert result["paragraphs"][0]["text"] == "Document Title"
            assert result["paragraphs"][0]["style"] == "Heading 1"
            assert result["paragraphs"][0]["level"] == 1

            assert result["paragraphs"][1]["text"] == "Some content here."
            assert result["paragraphs"][1]["style"] == "Normal"
            assert result["paragraphs"][1]["level"] == 0
        finally:
            os.unlink(temp_path)

    @patch('docx.Document')
    def test_parse_empty_paragraphs(self, mock_document_class):
        """测试跳过空段落"""
        mock_doc = MagicMock()

        mock_para1 = MagicMock()
        mock_para1.text = "   "  # 空白内容
        mock_para1.style.name = "Normal"

        mock_para2 = MagicMock()
        mock_para2.text = "Real content"
        mock_para2.style.name = "Normal"

        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_document_class.return_value = mock_doc

        parser = DocxParser()

        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            temp_path = f.name

        try:
            result = parser._parse_with_python_docx(Path(temp_path))

            # 空段落应该被跳过
            assert len(result["paragraphs"]) == 1
            assert result["paragraphs"][0]["text"] == "Real content"
        finally:
            os.unlink(temp_path)

    def test_import_error(self):
        """测试python-docx未安装时的错误"""
        parser = DocxParser()

        # 临时移除docx模块
        with patch.dict('sys.modules', {'docx': None}):
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
                temp_path = f.name

            try:
                with pytest.raises(ImportError) as exc_info:
                    parser._parse_with_python_docx(Path(temp_path))
                assert "python-docx" in str(exc_info.value)
            finally:
                os.unlink(temp_path)


class TestParseDocxFunction:
    """测试parse_docx便捷函数"""

    @patch.object(DocxParser, 'parse')
    def test_parse_docx_function(self, mock_parse):
        """测试便捷函数"""
        mock_parse.return_value = {
            "title": "Test",
            "paragraphs": []
        }

        result = parse_docx("test.docx")

        assert result["title"] == "Test"
        mock_parse.assert_called_once_with("test.docx")
