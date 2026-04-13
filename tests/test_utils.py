"""测试 utils.py 模块"""

import pytest
from doc2know.utils import parse_json_response, clean_json_text, safe_filename, ParseError


class TestCleanJsonText:
    """测试 clean_json_text 函数"""

    def test_remove_trailing_comma_in_object(self):
        """测试移除对象中的尾部逗号"""
        input_text = '{"key": "value",}'
        result = clean_json_text(input_text)
        assert result == '{"key": "value"}'

    def test_remove_trailing_comma_in_array(self):
        """测试移除数组中的尾部逗号"""
        input_text = '["a", "b",]'
        result = clean_json_text(input_text)
        assert result == '["a", "b"]'

    def test_replace_single_quotes(self):
        """测试替换单引号为双引号"""
        input_text = "{'key': 'value'}"
        result = clean_json_text(input_text)
        assert result == '{"key": "value"}'

    def test_combined_cleaning(self):
        """测试组合清理"""
        input_text = "{'key': 'value',}"
        result = clean_json_text(input_text)
        assert result == '{"key": "value"}'


class TestParseJsonResponse:
    """测试 parse_json_response 函数"""

    def test_parse_valid_json(self):
        """测试解析有效的JSON"""
        response = '{"title": "测试", "tags": ["a", "b"]}'
        result = parse_json_response(response)
        assert result["title"] == "测试"
        assert result["tags"] == ["a", "b"]

    def test_parse_json_with_code_block(self):
        """测试解析代码块中的JSON"""
        response = '```json\n{"title": "测试"}\n```'
        result = parse_json_response(response)
        assert result["title"] == "测试"

    def test_parse_json_with_plain_code_block(self):
        """测试解析无语言标识的代码块"""
        response = '```\n{"title": "测试"}\n```'
        result = parse_json_response(response)
        assert result["title"] == "测试"

    def test_parse_json_with_extra_text(self):
        """测试解析带额外文本的JSON"""
        response = '这是一些说明\n{"title": "测试"}\n更多说明'
        result = parse_json_response(response)
        assert result["title"] == "测试"

    def test_parse_json_with_trailing_comma(self):
        """测试解析带尾部逗号的JSON"""
        response = '{"key": "value",}'
        result = parse_json_response(response)
        assert result["key"] == "value"

    def test_parse_empty_response(self):
        """测试解析空响应"""
        with pytest.raises(ParseError, match="空响应"):
            parse_json_response("")

    def test_parse_whitespace_response(self):
        """测试解析空白响应"""
        with pytest.raises(ParseError, match="空响应"):
            parse_json_response("   \n\t  ")

    def test_parse_invalid_json(self):
        """测试解析无效的JSON返回错误信息"""
        response = "这不是JSON"
        result = parse_json_response(response)
        assert "error" in result
        assert "JSON解析失败" in result["error"]


class TestSafeFilename:
    """测试 safe_filename 函数"""

    def test_chinese_filename(self):
        """测试中文字符文件名"""
        result = safe_filename("安装指南")
        assert result == "安装指南"

    def test_chinese_filename_with_extension(self):
        """测试带扩展名的中文文件名"""
        result = safe_filename("安装指南.md")
        assert result == "安装指南.md"

    def test_illegal_characters(self):
        """测试非法字符替换"""
        result = safe_filename('Test: File*Name?')
        assert ":" not in result
        assert "*" not in result
        assert "?" not in result

    def test_multiple_dashes(self):
        """测试多个连字符合并"""
        result = safe_filename("Test---File")
        assert "---" not in result

    def test_leading_trailing_dashes(self):
        """测试首尾连字符移除"""
        result = safe_filename("-Test File-")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_empty_string(self):
        """测试空字符串"""
        result = safe_filename("")
        assert result == "untitled"

    def test_whitespace_string(self):
        """测试空白字符串"""
        result = safe_filename("   ")
        assert result == "untitled"

    def test_long_filename(self):
        """测试长文件名截断"""
        long_name = "A" * 100
        result = safe_filename(long_name)
        assert len(result) <= 50

    def test_complex_chinese_filename(self):
        """测试复杂中文文件名"""
        result = safe_filename("API 参考文档 (v2.0)")
        assert "API 参考文档 (v2.0)" == result or "API-参考文档-(v2.0)" == result
