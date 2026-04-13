"""配置管理模块"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml


class ConfigError(Exception):
    """配置错误异常"""
    pass


class Config:
    """配置类，加载和验证YAML配置"""

    # 默认配置值
    DEFAULTS = {
        "llm": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "model": "gpt-3.5-turbo",
        },
        "paths": {
            "raw_dir": "./raw_docs",
            "output_dir": "./output",
        },
        "processing": {
            "chunk_size": 4000,
            "max_concurrent": 3,
        },
    }

    # 环境变量映射
    ENV_OVERRIDES = {
        "DOCS2KNOW_API_KEY": ("llm", "api_key"),
        "DOCS2KNOW_RAW_DIR": ("paths", "raw_dir"),
        "DOCS2KNOW_OUTPUT_DIR": ("paths", "output_dir"),
    }

    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化配置

        Args:
            config_path: 配置文件路径，默认为当前目录的config.yaml
        """
        self._config: Dict[str, Any] = {}
        self._config_path = config_path

        # 加载默认配置
        self._load_defaults()

        # 加载YAML配置
        self._load_yaml_config(config_path)

        # 加载环境变量覆盖
        self._load_env_overrides()

        # 验证配置
        self.validate()

    def _load_defaults(self) -> None:
        """加载默认配置"""
        self._config = {
            "llm": self.DEFAULTS["llm"].copy(),
            "paths": self.DEFAULTS["paths"].copy(),
            "processing": self.DEFAULTS["processing"].copy(),
        }

    def _load_yaml_config(self, config_path: str) -> None:
        """
        从YAML文件加载配置

        Args:
            config_path: 配置文件路径
        """
        # 如果路径是相对路径，尝试从当前工作目录和脚本所在目录查找
        paths_to_try = [Path(config_path)]

        # 如果配置文件不存在，尝试从当前工作目录查找
        if not paths_to_try[0].is_absolute():
            paths_to_try.insert(0, Path.cwd() / config_path)

        yaml_config = None
        for path in paths_to_try:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        yaml_config = yaml.safe_load(f)
                    break
                except yaml.YAMLError as e:
                    raise ConfigError(f"配置文件格式错误: {e}")
                except IOError as e:
                    raise ConfigError(f"无法读取配置文件: {e}")

        # 如果找到配置文件，合并配置
        if yaml_config:
            self._deep_merge(self._config, yaml_config)

    def _load_env_overrides(self) -> None:
        """从环境变量加载覆盖值"""
        for env_var, (section, key) in self.ENV_OVERRIDES.items():
            value = os.environ.get(env_var)
            if value is not None:
                if section not in self._config:
                    self._config[section] = {}
                self._config[section][key] = value

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """
        深度合并两个字典

        Args:
            base: 基础字典
            override: 覆盖字典
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def validate(self) -> None:
        """
        验证所有配置项

        Raises:
            ConfigError: 验证失败时抛出
        """
        self._validate_api_key()
        self._validate_directories()

    def _validate_api_key(self) -> None:
        """
        验证API密钥

        Raises:
            ConfigError: API密钥未配置或格式错误
        """
        api_key = self._config.get("llm", {}).get("api_key", "")

        # 检查是否为空
        if not api_key:
            raise ConfigError(
                "API密钥未配置或格式错误，请在config.yaml中设置llm.api_key"
            )

        # 检查长度是否合理（API密钥通常有一定长度）
        if len(api_key) < 8:
            raise ConfigError(
                "API密钥未配置或格式错误，请在config.yaml中设置llm.api_key"
            )

        # 检查是否为占位符
        placeholder_values = ["your-api-key", "your_api_key", "placeholder", "xxx"]
        if api_key.lower() in placeholder_values:
            raise ConfigError(
                "API密钥未配置或格式错误，请在config.yaml中设置llm.api_key"
            )

    def _validate_directories(self) -> None:
        """
        验证目录权限

        Raises:
            ConfigError: 目录权限验证失败
        """
        paths = self._config.get("paths", {})

        # 验证raw_dir可读
        raw_dir = paths.get("raw_dir", "./raw_docs")
        raw_path = Path(raw_dir)

        # 如果目录不存在，尝试创建
        if not raw_path.exists():
            try:
                raw_path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ConfigError(f"无法读取输入目录: {raw_dir}")

        # 检查是否可读
        if not raw_path.exists() or not os.access(raw_path, os.R_OK):
            raise ConfigError(f"无法读取输入目录: {raw_dir}")

        # 验证output_dir可写
        output_dir = paths.get("output_dir", "./output")
        output_path = Path(output_dir)

        # 如果目录不存在，尝试创建
        if not output_path.exists():
            try:
                output_path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ConfigError(f"无法写入输出目录: {output_dir}")

        # 检查是否可写
        if not os.access(output_path, os.W_OK):
            raise ConfigError(f"无法写入输出目录: {output_dir}")

    def get(self, section: str, key: Optional[str] = None) -> Any:
        """
        获取配置值

        Args:
            section: 配置节名称
            key: 配置键名称，如果为None则返回整个节

        Returns:
            配置值

        Raises:
            ConfigError: 配置节或键不存在
        """
        if section not in self._config:
            raise ConfigError(f"配置节不存在: {section}")

        if key is None:
            return self._config[section]

        if key not in self._config[section]:
            raise ConfigError(f"配置键不存在: {section}.{key}")

        return self._config[section][key]

    @property
    def llm(self) -> Dict[str, Any]:
        """获取LLM配置"""
        return self._config.get("llm", {}).copy()

    @property
    def paths(self) -> Dict[str, Any]:
        """获取路径配置"""
        return self._config.get("paths", {}).copy()

    @property
    def processing(self) -> Dict[str, Any]:
        """获取处理配置"""
        return self._config.get("processing", {}).copy()

    @property
    def api_key(self) -> str:
        """获取API密钥"""
        return self._config.get("llm", {}).get("api_key", "")

    @property
    def base_url(self) -> str:
        """获取API基础URL"""
        return self._config.get("llm", {}).get("base_url", "")

    @property
    def model(self) -> str:
        """获取模型名称"""
        return self._config.get("llm", {}).get("model", "")

    @property
    def raw_dir(self) -> str:
        """获取输入目录"""
        return self._config.get("paths", {}).get("raw_dir", "")

    @property
    def output_dir(self) -> str:
        """获取输出目录"""
        return self._config.get("paths", {}).get("output_dir", "")

    @property
    def chunk_size(self) -> int:
        """获取分块大小"""
        return self._config.get("processing", {}).get("chunk_size", 4000)

    @property
    def max_concurrent(self) -> int:
        """获取最大并发数"""
        return self._config.get("processing", {}).get("max_concurrent", 3)

    @property
    def split_strategy(self) -> str:
        """获取智能拆分策略"""
        return self._config.get("processing", {}).get("split_strategy", "conservative")

    def to_dict(self) -> Dict[str, Any]:
        """
        导出配置为字典

        Returns:
            配置字典的深拷贝
        """
        import copy
        return copy.deepcopy(self._config)
