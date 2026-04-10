#!/bin/bash

# Doc2Know Web 启动脚本
# 同时启动后端和前端服务

set -e

echo "========================================"
echo "  Doc2Know Web 启动脚本"
echo "========================================"

# 检查配置
echo ""
echo "[1/3] 检查配置..."
if [ ! -f "config.yaml" ]; then
    echo "警告: 未找到 config.yaml 文件"
    echo "请复制 config.yaml.example 并配置您的 API Key"
    exit 1
fi

# 启动后端
echo ""
echo "[2/3] 启动后端服务..."
cd web/backend

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装后端依赖..."
pip install -q -r requirements.txt

# 启动后端（后台）
echo "启动后端服务 (http://localhost:8000)..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

cd ../..

# 启动前端
echo ""
echo "[3/3] 启动前端服务..."
cd web/frontend

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi

# 启动前端
echo "启动前端服务 (http://localhost:3000)..."
npm run dev &
FRONTEND_PID=$!

cd ../..

# 捕获 Ctrl+C
trap "echo ''; echo '正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

echo ""
echo "========================================"
echo "  Doc2Know Web 已启动!"
echo "========================================"
echo ""
echo "  后端 API:  http://localhost:8000"
echo "  API 文档:   http://localhost:8000/docs"
echo "  前端界面:  http://localhost:3000"
echo ""
echo "  按 Ctrl+C 停止服务"
echo ""

# 等待
wait
