# Doc2Know Web 后端

FastAPI 实现的 RESTful API，提供文档上传、处理和知识库管理功能。

## 技术栈

- **FastAPI**: 现代、快速的 Web 框架
- **Uvicorn**: ASGI 服务器
- **Pydantic**: 数据验证
- **SSE**: Server-Sent Events 实时进度推送

## 目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── api/                 # API 路由
│   │   ├── __init__.py
│   │   ├── documents.py     # 文档处理 API
│   │   ├── knowledge.py     # 知识库 API
│   │   └── config.py        # 配置 API
│   ├── core/                # 核心逻辑
│   │   ├── __init__.py
│   │   └── processor.py     # 文档处理器
│   └── models/              # 数据模型
│       ├── __init__.py
│       ├── document.py      # 文档模型
│       └── responses.py     # 响应模型
├── requirements.txt
└── README.md
```

## 安装

```bash
# 进入后端目录
cd web/backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

## 配置

后端复用 CLI 的配置系统。确保项目根目录存在有效的 `config.yaml`：

```yaml
llm:
  base_url: "https://api.openai.com/v1"
  api_key: "your-api-key"
  model: "gpt-3.5-turbo"

paths:
  raw_dir: "./raw_docs"
  output_dir: "./output"

processing:
  chunk_size: 4000
  max_concurrent: 3
```

或通过环境变量配置：

```bash
export DOCS2KNOW_API_KEY="your-api-key"
export DOCS2KNOW_BASE_URL="https://api.openai.com/v1"
export DOCS2KNOW_MODEL="gpt-3.5-turbo"
export DOCS2KNOW_RAW_DIR="./raw_docs"
export DOCS2KNOW_OUTPUT_DIR="./output"
```

## 启动

### 开发模式

```bash
# 自动重载
uvicorn app.main:app --reload --port 8000
```

### 生产模式

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API 文档

启动后访问：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API 端点

### 文档管理

- `POST /documents/upload` - 上传文档
- `POST /documents/upload/stream` - 上传并流式返回进度
- `GET /documents` - 获取文档列表
- `GET /documents/{id}` - 获取文档详情
- `GET /documents/{id}/progress` - 获取处理进度 (SSE)
- `DELETE /documents/{id}` - 删除文档
- `POST /documents/{id}/retry` - 重试处理

### 知识库

- `GET /knowledge` - 获取知识库列表
- `GET /knowledge/tags` - 获取标签列表
- `GET /knowledge/{id}` - 获取知识详情
- `GET /knowledge/{id}/content` - 获取 Markdown 内容
- `POST /knowledge/rebuild-index` - 重建索引

### 配置

- `GET /config` - 获取配置
- `GET /config/stats` - 获取统计信息
- `GET /config/health` - 健康检查

## 测试

```bash
# 测试 API 是否运行
curl http://localhost:8000/

# 测试健康检查
curl http://localhost:8000/config/health

# 上传文档
curl -X POST -F "file=@test.docx" http://localhost:8000/documents/upload
```
