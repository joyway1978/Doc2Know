# Doc2Know Web 前端

Next.js 14 + TypeScript + Tailwind CSS 实现的现代化 Web 界面。

## 技术栈

- **Next.js 14**: React 框架（App Router）
- **TypeScript**: 类型安全
- **Tailwind CSS**: 原子化 CSS
- **Lucide React**: 图标库
- **Axios**: HTTP 客户端

## 目录结构

```
frontend/
├── app/                     # Next.js 14 App Router
│   ├── layout.tsx          # 根布局
│   ├── page.tsx            # 首页 Dashboard
│   ├── documents/
│   │   └── page.tsx        # 文档管理页
│   ├── knowledge/
│   │   ├── page.tsx        # 知识库列表页
│   │   └── [id]/
│   │       └── page.tsx    # 知识详情页
├── components/              # 组件
│   ├── Sidebar.tsx         # 侧边栏导航
│   └── ui/                 # UI 组件
│       ├── Button.tsx
│       ├── Badge.tsx
│       └── Progress.tsx
├── lib/                     # 工具库
│   ├── api.ts              # API 客户端
│   └── utils.ts            # 工具函数
├── styles/                  # 样式
│   └── globals.css         # 全局样式
├── public/                  # 静态资源
├── package.json
├── tsconfig.json
├── next.config.js
├── tailwind.config.ts
└── README.md
```

## 安装

```bash
# 进入前端目录
cd web/frontend

# 安装依赖
npm install

# 或使用 yarn
yarn install

# 或使用 pnpm
pnpm install
```

## 开发

```bash
# 启动开发服务器
npm run dev

# 访问 http://localhost:3000
```

## 构建

```bash
# 构建生产版本
npm run build

# 启动生产服务器
npm start
```

## 配置

前端通过 Next.js 的 `next.config.js` 配置 API 代理：

```javascript
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
};
```

生产环境需要修改代理目标或配置 Nginx 反向代理。

## 页面说明

### 首页 (Dashboard)

- 系统统计概览
- 快速操作入口
- 最近文档列表
- 系统健康状态

### 文档管理页

- 文件上传（支持拖拽）
- 文档列表展示
- 实时进度显示
- 删除/重试操作

### 知识库页

- 知识条目卡片展示
- 搜索功能
- 标签筛选
- 索引重建

### 知识详情页

- 文档元数据展示
- Markdown 内容查看
- 原始文件下载

## 设计系统

参考 `docs/design-preview.html`：

- **颜色**: Primary (#0F172A), Accent (#3B82F6)
- **字体**: Inter
- **间距**: 4px 基准单位
- **圆角**: 4px, 6px, 8px
