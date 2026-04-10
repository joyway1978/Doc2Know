# Doc2Know

Doc2Know 是一个将 Word 文档自动转换为结构化 Markdown 知识库的工具。它使用 LLM（大型语言模型）智能分析文档内容，提取关键信息并生成易于浏览的知识库。

## 功能特性

- **智能文档解析**：支持使用 python-docx 或 pandoc 解析 Word 文档
- **LLM 内容分析**：自动提取文档标题、摘要、标签和章节结构
- **Markdown 生成**：生成带有 YAML frontmatter 的标准 Markdown 文件
- **自动索引**：扫描生成的文档并创建索引页面
- **灵活配置**：支持 YAML 配置文件和环境变量覆盖

## 安装

### 从源码安装

```bash
# 克隆仓库
git clone <repository-url>
cd Doc2Know

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -e .
```

### 依赖要求

- Python >= 3.9
- python-docx >= 0.8.11
- openai >= 1.0.0
- pyyaml >= 6.0
- click >= 8.0
- tenacity >= 8.0

### 可选依赖

- **pandoc**：如果使用 pandoc 解析文档，需要安装 [pandoc](https://pandoc.org/installing.html)

## 快速开始

### 1. 配置

编辑 `config.yaml`，设置你的 API 密钥：

```yaml
llm:
  base_url: "https://api.openai.com/v1"
  api_key: "your-actual-api-key"  # 替换为你的 OpenAI API 密钥
  model: "gpt-3.5-turbo"
```

### 2. 准备文档

将需要转换的 Word 文档（.docx 或 .doc）放入 `raw_docs` 目录：

```bash
mkdir -p raw_docs
cp your-document.docx raw_docs/
```

### 3. 运行转换

```bash
doc2know
```

转换后的 Markdown 文件将生成在 `output/topics/` 目录，索引文件为 `output/index.md`。

## 配置

配置文件 `config.yaml` 包含以下部分：

### LLM 配置

```yaml
llm:
  base_url: "https://api.openai.com/v1"  # API 基础 URL
  api_key: "your-api-key"                 # API 密钥（必填）
  model: "gpt-3.5-turbo"                  # 使用的模型
```

### 路径配置

```yaml
paths:
  raw_dir: "./raw_docs"    # 输入文档目录
  output_dir: "./output"   # 输出目录
```

### 处理配置

```yaml
processing:
  chunk_size: 4000         # 文档分块大小（字符数）
  max_concurrent: 3        # 最大并发处理数
```

### 环境变量

可以通过环境变量覆盖配置：

| 环境变量 | 说明 | 示例 |
|---------|------|------|
| `DOCS2KNOW_API_KEY` | API 密钥 | `sk-...` |
| `DOCS2KNOW_RAW_DIR` | 输入目录 | `/path/to/docs` |
| `DOCS2KNOW_OUTPUT_DIR` | 输出目录 | `/path/to/output` |

## 使用方法

### 命令行

```bash
# 使用默认配置文件 (config.yaml)
doc2know

# 指定配置文件
doc2know --config /path/to/config.yaml

# 查看帮助
doc2know --help
```

### Python API

```python
from doc2know.config import Config
from doc2know.parser import parse_docx
from doc2know.analyzer import analyze_content
from doc2know.generator import generate_markdown
from doc2know.indexer import update_index

# 加载配置
config = Config("config.yaml")

# 解析文档
content = parse_docx("document.docx")

# 分析内容
result = analyze_content(content, config)

# 生成 Markdown
filepath = generate_markdown(result, "document.docx", config.output_dir)

# 更新索引
update_index(config.output_dir)
```

## 输出格式

生成的 Markdown 文件包含 YAML frontmatter：

```markdown
---
title: "文档标题"
summary: "文档摘要"
tags: ["标签1", "标签2", "标签3"]
source: "原始文档路径"
generated_at: "2024-01-15T10:30:00"
---

# 章节标题

内容...
```

索引文件 `index.md` 包含所有文档的汇总表格：

```markdown
# 知识库索引

| 文档 | 摘要 | 标签 | 更新时间 |
|------|------|------|----------|
| [文档标题](topics/document.md) | 摘要内容 | 标签1, 标签2 | 2024-01-15 |
```

## 开发

### 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=doc2know --cov-report=html
```

### 项目结构

```
Doc2Know/
├── doc2know/           # 主包
│   ├── __init__.py
│   ├── cli.py          # 命令行接口
│   ├── config.py       # 配置管理
│   ├── parser.py       # 文档解析
│   ├── analyzer.py     # LLM 分析
│   ├── generator.py    # Markdown 生成
│   └── indexer.py      # 索引管理
├── tests/              # 测试
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_parser.py
│   └── data/
│       └── sample.docx
├── config.yaml         # 配置文件
├── requirements.txt    # 依赖
├── setup.py           # 安装脚本
└── README.md          # 本文档
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
