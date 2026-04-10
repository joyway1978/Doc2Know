"""配置模块测试"""
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from doc2know.config import Config, ConfigError


class TestConfigDefaults:
    """测试配置默认值"""

    def test_default_values(self):
        """测试默认配置值是否正确"""
        # 创建一个临时配置文件，包含有效的API密钥
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                'llm': {'api_key': 'sk-test1234567890'}
            }, f)
            config_path = f.name

        try:
            config = Config(config_path)

            # 测试LLM默认值
            assert config.base_url == "https://api.openai.com/v1"
            assert config.model == "gpt-3.5-turbo"

            # 测试路径默认值
            assert config.raw_dir == "./raw_docs"
            assert config.output_dir == "./output"

            # 测试处理默认值
            assert config.chunk_size == 4000
            assert config.max_concurrent == 3
        finally:
            os.unlink(config_path)


class TestConfigValidation:
    """测试配置验证"""

    def test_missing_api_key(self):
        """测试缺少API密钥时抛出错误"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'llm': {}}, f)
            config_path = f.name

        try:
            with pytest.raises(ConfigError) as exc_info:
                Config(config_path)
            assert "API密钥" in str(exc_info.value)
        finally:
            os.unlink(config_path)

    def test_invalid_api_key_placeholder(self):
        """测试使用占位符API密钥时抛出错误"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'llm': {'api_key': 'your-api-key'}}, f)
            config_path = f.name

        try:
            with pytest.raises(ConfigError) as exc_info:
                Config(config_path)
            assert "API密钥" in str(exc_info.value)
        finally:
            os.unlink(config_path)

    def test_api_key_too_short(self):
        """测试API密钥太短时抛出错误"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'llm': {'api_key': 'short'}}, f)
            config_path = f.name

        try:
            with pytest.raises(ConfigError) as exc_info:
                Config(config_path)
            assert "API密钥" in str(exc_info.value)
        finally:
            os.unlink(config_path)

    def test_valid_api_key(self):
        """测试有效的API密钥通过验证"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'llm': {'api_key': 'sk-test1234567890'}}, f)
            config_path = f.name

        try:
            config = Config(config_path)
            assert config.api_key == "sk-test1234567890"
        finally:
            os.unlink(config_path)


class TestConfigLoading:
    """测试配置加载"""

    def test_yaml_config_loading(self):
        """测试从YAML文件加载配置"""
        config_data = {
            'llm': {
                'api_key': 'sk-test1234567890',
                'model': 'gpt-4',
                'base_url': 'https://custom.api.com/v1'
            },
            'paths': {
                'raw_dir': './custom_input',
                'output_dir': './custom_output'
            },
            'processing': {
                'chunk_size': 2000,
                'max_concurrent': 5
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = Config(config_path)

            assert config.api_key == 'sk-test1234567890'
            assert config.model == 'gpt-4'
            assert config.base_url == 'https://custom.api.com/v1'
            assert config.raw_dir == './custom_input'
            assert config.output_dir == './custom_output'
            assert config.chunk_size == 2000
            assert config.max_concurrent == 5
        finally:
            os.unlink(config_path)

    def test_deep_merge(self):
        """测试配置深度合并"""
        config_data = {
            'llm': {
                'api_key': 'sk-test1234567890',
                'model': 'gpt-4'  # 只覆盖model，保留其他默认值
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = Config(config_path)

            # 验证覆盖的值
            assert config.model == 'gpt-4'
            # 验证保留的默认值
            assert config.base_url == 'https://api.openai.com/v1'
        finally:
            os.unlink(config_path)


class TestConfigEnvironmentVariables:
    """测试环境变量覆盖"""

    def test_env_override_api_key(self, monkeypatch):
        """测试环境变量覆盖API密钥"""
        monkeypatch.setenv('DOCS2KNOW_API_KEY', 'sk-env-key123456')

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'llm': {'api_key': 'sk-test1234567890'}}, f)
            config_path = f.name

        try:
            config = Config(config_path)
            assert config.api_key == 'sk-env-key123456'
        finally:
            os.unlink(config_path)

    def test_env_override_paths(self, monkeypatch, tmp_path):
        """测试环境变量覆盖路径"""
        raw_dir = str(tmp_path / "env_input")
        output_dir = str(tmp_path / "env_output")

        monkeypatch.setenv('DOCS2KNOW_API_KEY', 'sk-test1234567890')
        monkeypatch.setenv('DOCS2KNOW_RAW_DIR', raw_dir)
        monkeypatch.setenv('DOCS2KNOW_OUTPUT_DIR', output_dir)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'llm': {'api_key': 'sk-test1234567890'}}, f)
            config_path = f.name

        try:
            config = Config(config_path)
            assert config.raw_dir == raw_dir
            assert config.output_dir == output_dir
        finally:
            os.unlink(config_path)


class TestConfigGetters:
    """测试配置获取方法"""

    def test_get_section(self):
        """测试获取整个配置节"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'llm': {'api_key': 'sk-test1234567890'}}, f)
            config_path = f.name

        try:
            config = Config(config_path)

            llm_config = config.get('llm')
            assert isinstance(llm_config, dict)
            assert llm_config['model'] == 'gpt-3.5-turbo'
        finally:
            os.unlink(config_path)

    def test_get_key(self):
        """测试获取具体配置键"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'llm': {'api_key': 'sk-test1234567890'}}, f)
            config_path = f.name

        try:
            config = Config(config_path)

            model = config.get('llm', 'model')
            assert model == 'gpt-3.5-turbo'
        finally:
            os.unlink(config_path)

    def test_get_nonexistent_section(self):
        """测试获取不存在的配置节"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'llm': {'api_key': 'sk-test1234567890'}}, f)
            config_path = f.name

        try:
            config = Config(config_path)

            with pytest.raises(ConfigError) as exc_info:
                config.get('nonexistent')
            assert "配置节不存在" in str(exc_info.value)
        finally:
            os.unlink(config_path)

    def test_get_nonexistent_key(self):
        """测试获取不存在的配置键"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'llm': {'api_key': 'sk-test1234567890'}}, f)
            config_path = f.name

        try:
            config = Config(config_path)

            with pytest.raises(ConfigError) as exc_info:
                config.get('llm', 'nonexistent')
            assert "配置键不存在" in str(exc_info.value)
        finally:
            os.unlink(config_path)

    def test_to_dict(self):
        """测试导出配置为字典"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({'llm': {'api_key': 'sk-test1234567890'}}, f)
            config_path = f.name

        try:
            config = Config(config_path)

            config_dict = config.to_dict()
            assert isinstance(config_dict, dict)
            assert 'llm' in config_dict
            assert 'paths' in config_dict
            assert 'processing' in config_dict
        finally:
            os.unlink(config_path)


class TestConfigProperties:
    """测试配置属性"""

    def test_properties(self):
        """测试所有配置属性"""
        config_data = {
            'llm': {
                'api_key': 'sk-test1234567890',
                'base_url': 'https://test.api.com',
                'model': 'gpt-4'
            },
            'paths': {
                'raw_dir': './test_input',
                'output_dir': './test_output'
            },
            'processing': {
                'chunk_size': 1000,
                'max_concurrent': 2
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = Config(config_path)

            # 测试所有属性
            assert config.api_key == 'sk-test1234567890'
            assert config.base_url == 'https://test.api.com'
            assert config.model == 'gpt-4'
            assert config.raw_dir == './test_input'
            assert config.output_dir == './test_output'
            assert config.chunk_size == 1000
            assert config.max_concurrent == 2

            # 测试返回的是副本
            llm = config.llm
            llm['model'] = 'changed'
            assert config.model == 'gpt-4'  # 原配置不应改变
        finally:
            os.unlink(config_path)
