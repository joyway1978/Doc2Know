# Doc2Know Web 界面

Doc2Know 的 Web 界面，包含 FastAPI 后端和 Next.js 前端。

## 快速开始

### 1. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # 或 venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --port 8000
```

后端将在 http://localhost:8000 运行

### 2. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 http://localhost:3000 运行

### 3. 配置

确保项目根目录有有效的 `config.yaml` 文件：

```yaml
llm:
  base_url: "https://api.openai.com/v1"
  api_key: "your-api-key-here"
  model: "gpt-3.5-turbo"

paths:
  raw_dir: "./raw_docs"
  output_dir: "./output"
```

## 目录结构

```
web/
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── api/      # API 路由
│   │   ├── core/     # 文档处理器
│   │   └── models/   # 数据模型
│   └── requirements.txt
└── frontend/         # Next.js 前端
    ├── app/          # 页面
    ├── components/   # 组件
    └── lib/          # 工具库
```

## 功能特性

- 📄 **文档上传**: 支持 .docx, .doc, .pdf 格式
- 📊 **实时进度**: Server-Sent Events 实时推送处理进度
- 🔍 **知识库搜索**: 全文搜索和标签筛选
- 🏷️ **自动标签**: AI 自动生成文档标签
- 📈 **统计仪表板**: 系统状态一目了然

## API 文档

启动后端后访问 http://localhost:8000/docs

## 部署

### 使用 Docker（推荐）

```bash
# 构建镜像
docker build -t doc2know-web .

# 运行
docker run -p 8000:8000 -p 3000:3000 doc2know-web
```

### 手动部署

1. 后端：使用 Gunicorn + Uvicorn 部署
2. 前端：构建静态文件，使用 Nginx 托管

```bash
# 后端生产部署
cd backend
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 前端生产构建
cd frontend
npm run build
# 将 out/ 目录部署到 Nginx
```
