"""测试 splitter.py 模块"""

import asyncio
import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from doc2know.splitter import (
    DocumentSplitter,
    SplitStrategy,
    Topic,
    Category,
    CategoryContent,
    SplitResult,
    SplitterError,
)
from doc2know.config import Config
from doc2know.utils import ParseError


class TestSplitStrategy:
    """测试 SplitStrategy 枚举"""

    def test_conservative_value(self):
        """测试保守策略值"""
        assert SplitStrategy.CONSERVATIVE == "conservative"

    def test_aggressive_value(self):
        """测试激进策略值"""
        assert SplitStrategy.AGGRESSIVE == "aggressive"

    def test_from_config(self):
        """测试从配置字符串创建"""
        assert SplitStrategy("conservative") == SplitStrategy.CONSERVATIVE
        assert SplitStrategy("aggressive") == SplitStrategy.AGGRESSIVE


class TestTopic:
    """测试 Topic Pydantic 模型"""

    def test_create_topic(self):
        """测试创建主题"""
        topic = Topic(
            topic_id="t1",
            topic_name="安装步骤",
            related_sections=["1.1", "2.3"]
        )
        assert topic.topic_id == "t1"
        assert topic.topic_name == "安装步骤"
        assert topic.related_sections == ["1.1", "2.3"]

    def test_create_topic_without_sections(self):
        """测试创建无段落引用的主题"""
        topic = Topic(
            topic_id="t2",
            topic_name="功能介绍"
        )
        assert topic.related_sections == []


class TestCategory:
    """测试 Category Pydantic 模型"""

    def test_create_category(self):
        """测试创建分类"""
        category = Category(
            category_name="安装指南",
            topic_ids=["t1", "t2"]
        )
        assert category.category_name == "安装指南"
        assert category.topic_ids == ["t1", "t2"]


class TestCategoryContent:
    """测试 CategoryContent Pydantic 模型"""

    def test_create_content(self):
        """测试创建内容"""
        content = CategoryContent(
            title="安装指南",
            content="# 安装指南\n\n这是安装说明。",
            source_refs=["第1章", "第2章"]
        )
        assert content.title == "安装指南"
        assert "# 安装指南" in content.content


class TestDocumentSplitterInit:
    """测试 DocumentSplitter 初始化"""

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Mock(spec=Config)
        config.chunk_size = 4000
        config.max_concurrent = 3
        config.llm = {
            "base_url": "https://api.test.com/v1",
            "api_key": "test-key",
            "model": "gpt-3.5-turbo"
        }
        config.output_dir = "./test_output"
        config.split_strategy = "conservative"
        return config

    def test_init_with_conservative_strategy(self, mock_config):
        """测试使用保守策略初始化"""
        splitter = DocumentSplitter(mock_config, SplitStrategy.CONSERVATIVE)
        assert splitter.strategy == SplitStrategy.CONSERVATIVE
        assert splitter.chunk_size == 4000
        assert splitter.max_concurrent == 3

    def test_init_with_aggressive_strategy(self, mock_config):
        """测试使用激进策略初始化"""
        splitter = DocumentSplitter(mock_config, SplitStrategy.AGGRESSIVE)
        assert splitter.strategy == SplitStrategy.AGGRESSIVE


class TestExtractTopics:
    """测试主题提取功能"""

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Mock(spec=Config)
        config.chunk_size = 4000
        config.max_concurrent = 3
        config.llm = {
            "base_url": "https://api.test.com/v1",
            "api_key": "test-key",
            "model": "gpt-3.5-turbo"
        }
        config.output_dir = "./test_output"
        return config

    @pytest.fixture
    def sample_content(self):
        """创建示例文档内容"""
        return {
            "title": "测试文档",
            "paragraphs": [
                {"text": "第一章：介绍", "level": 1},
                {"text": "这是介绍内容", "level": 0},
                {"text": "第二章：安装", "level": 1},
                {"text": "安装步骤说明", "level": 0},
            ]
        }

    @pytest.mark.asyncio
    async def test_extract_topics_empty_content(self, mock_config):
        """测试空内容返回错误"""
        splitter = DocumentSplitter(mock_config)
        content = {"title": "空文档", "paragraphs": []}

        topics, error = await splitter.extract_topics(content)

        assert topics == []
        assert error == "文档内容为空"

    @pytest.mark.asyncio
    async def test_extract_topics_success(self, mock_config, sample_content):
        """测试成功提取主题"""
        splitter = DocumentSplitter(mock_config)

        mock_response = json.dumps({
            "topics": [
                {"topic_id": "t1", "topic_name": "介绍", "related_sections": ["1"]},
                {"topic_id": "t2", "topic_name": "安装", "related_sections": ["2"]}
            ]
        })

        with patch.object(splitter, '_call_llm', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            topics, error = await splitter.extract_topics(sample_content)

        assert error is None
        assert len(topics) == 2
        assert topics[0].topic_id == "t1"
        assert topics[1].topic_name == "安装"

    @pytest.mark.asyncio
    async def test_extract_topics_parse_error(self, mock_config, sample_content):
        """测试解析错误处理"""
        splitter = DocumentSplitter(mock_config)

        with patch.object(splitter, '_call_llm', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "无效的JSON"
            topics, error = await splitter.extract_topics(sample_content)

        assert error is not None
        assert "失败" in error or len(topics) == 0


class TestMergeCategories:
    """测试分类合并功能"""

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Mock(spec=Config)
        config.chunk_size = 4000
        config.max_concurrent = 3
        config.llm = {
            "base_url": "https://api.test.com/v1",
            "api_key": "test-key",
            "model": "gpt-3.5-turbo"
        }
        config.output_dir = "./test_output"
        return config

    @pytest.fixture
    def sample_topics(self):
        """创建示例主题列表"""
        return [
            Topic(topic_id="t1", topic_name="安装准备"),
            Topic(topic_id="t2", topic_name="安装步骤"),
            Topic(topic_id="t3", topic_name="配置说明"),
        ]

    @pytest.mark.asyncio
    async def test_merge_categories_empty_topics(self, mock_config):
        """测试空主题列表"""
        splitter = DocumentSplitter(mock_config)
        categories, error = await splitter.merge_categories([])

        assert categories == []
        assert error == "没有主题可以合并"

    @pytest.mark.asyncio
    async def test_merge_categories_success(self, mock_config, sample_topics):
        """测试成功合并分类"""
        splitter = DocumentSplitter(mock_config)

        mock_response = json.dumps({
            "categories": [
                {"category_name": "安装指南", "topic_ids": ["t1", "t2"]},
                {"category_name": "配置说明", "topic_ids": ["t3"]}
            ]
        })

        with patch.object(splitter, '_call_llm', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            categories, error = await splitter.merge_categories(sample_topics)

        assert error is None
        assert len(categories) == 2
        assert categories[0].category_name == "安装指南"


class TestSafeFilename:
    """测试安全文件名生成"""

    def test_chinese_filename(self):
        """测试中文字符"""
        from doc2know.utils import safe_filename
        result = safe_filename("安装指南")
        assert result == "安装指南"

    def test_special_characters(self):
        """测试特殊字符处理"""
        from doc2know.utils import safe_filename
        result = safe_filename('Test:File*Name?')
        assert ':' not in result
        assert '*' not in result
        assert '?' not in result


class TestSplitResult:
    """测试 SplitResult 模型"""

    def test_create_result(self):
        """测试创建结果"""
        result = SplitResult(
            version_dir="/path/to/version",
            categories=["安装指南", "配置说明"],
            files=["/path/to/file1.md", "/path/to/file2.md"],
            errors=[]
        )
        assert result.version_dir == "/path/to/version"
        assert len(result.categories) == 2


# 标记需要 LLM 的测试为集成测试
@pytest.mark.integration
class TestIntegration:
    """集成测试 - 需要真实的 LLM 服务"""

    @pytest.mark.skip(reason="需要真实的 LLM 服务")
    def test_full_split_document(self):
        """测试完整文档拆分流程"""
        pass
