# Codefolio

将 GitHub 上的公开足迹转化为专业简历与可分享社交卡片，并支持开发者之间的能力对比；未来计划扩展「仓库对标」，帮助你理解差距与可执行的改进方向。

## 产品愿景

Codefolio 的核心是：把 **可观测的 GitHub 数据** 变成 **能写进简历的叙事** 和 **可导出的素材**。产品演进方向包括在现有 **多人对比（GitScore / 雷达图）** 之上，逐步增加 **仓库级对标**：在同类可比（语言、topic、体量分桶）的前提下，结合规则特征与结构化 AI 输出，呈现 **证据链、差距矩阵、行动清单与策略选项**，并明确 **相关≠因果**、不承诺「必火」。完整范围、数据与存储选型、分期交付见设计草案：[`docs/design-compare-repo-growth.md`](docs/design-compare-repo-growth.md)。

## 功能特性

- **GitScore**：多维度开发者评分（0–100）
- **AI 洞察**：大语言模型生成的风格标签与技术摘要
- **简历生成**：Markdown / PDF 等专业简历输出
- **社交卡片**：适合社交媒体分享的 PNG 卡片
- **对比模式**：最多三名 GitHub 用户并排对比（分数、维度、语言分布、摘要等）
- **仓库与导出流程**：挑选代表仓库、预览与导出 Markdown / 社交卡片
- **缓存**：基于 Redis，降低 GitHub 与 AI 调用成本
- **国际化**：中英文界面与内容语言
- **主题**：亮色 / 暗色模式

### 路线图（设计中）

- **仓库对标模式**：我的仓库 vs 同类标杆，成功假设卡片（带证据）、差距表、按优先级排序的改进项；存储与数据库方案见 [`docs/design-compare-repo-growth.md`](docs/design-compare-repo-growth.md)。

## 技术架构

- **前端**：React 18 + Vite + Tailwind CSS
- **后端**：Python 3.11+ + FastAPI
- **缓存**：Redis 7+
- **API**：GitHub GraphQL API v4、DeepSeek / GPT-4o-mini 等

仓库对标等后续能力可能引入 **PostgreSQL**（或小型部署使用 **SQLite**）存放仓库画像与报告快照，详见上述设计文档。

## 安装配置

### 环境要求

- Python 3.11+
- Node.js 18+
- Redis 7+

### 后端配置

1. 进入后端目录：
```bash
cd backend
```

2. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Windows 系统: venv\Scripts\activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥
```

5. 启动 Redis（如果未运行）：
```bash
redis-server
```

6. 运行后端服务：
```bash
python main.py
```

后端服务将在 `http://localhost:8000` 运行

### 前端配置

1. 进入前端目录：
```bash
cd frontend
```

2. 安装依赖：
```bash
npm install
```

3. 启动开发服务器：
```bash
npm run dev
```

前端服务将在 `http://localhost:5173` 运行

## 环境变量配置

### 后端配置文件 (.env)

```env
# GitHub API
GITHUB_TOKEN=你的_github_token

# AI API
AI_API_KEY=你的_ai_api_key
AI_API_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat

# Redis
REDIS_URL=redis://localhost:6379
REDIS_DB=0

# CORS 跨域配置
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# 缓存过期时间（秒）
GITHUB_CACHE_TTL=86400
AI_CACHE_TTL=604800
```

## API 接口

- `GET /api/health` - 健康检查
- `POST /api/generate` - 生成开发者档案（参数：username, language）
- `GET /api/export/pdf` - 导出 PDF 简历

## 项目结构

```
codefolio/
├── backend/
│   ├── main.py              # FastAPI 应用主文件
│   ├── config.py            # 配置设置
│   ├── requirements.txt     # Python 依赖
│   ├── services/            # 业务逻辑服务
│   │   └── __init__.py
│   └── utils/               # 工具模块
│       ├── __init__.py
│       └── redis_client.py  # Redis 连接管理器
├── docs/
│   └── design-compare-repo-growth.md  # 对比与仓库对标设计草案
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # React 主组件
│   │   ├── main.tsx         # 入口文件
│   │   └── index.css        # 全局样式（含主题）
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── LICENSE                  # PolyForm 非商业许可（禁止未授权的商用）
├── README.md
└── README.zh-CN.md
```

## 开发指南

### 后端开发

```bash
cd backend
source venv/bin/activate
python main.py
```

### 前端开发

```bash
cd frontend
npm run dev
```

### 生产环境构建

前端构建：
```bash
cd frontend
npm run build
```

## 许可证

本项目采用 **[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)**（非商业许可），完整条文见仓库根目录 [`LICENSE`](LICENSE)。

- **允许**：在许可条款范围内的**非商业**使用（例如个人学习、研究、符合条件的非营利/教育/公共机构等，以英文许可证全文为准）。
- **不允许**：**商业使用**——包括但不限于将本软件作为收费产品或服务对外提供、在超出许可例外的场景下用于营利目的等，除非另行获得版权方**书面授权**。

以下为便于理解的摘要，**不构成法律意见**；权利义务以 `LICENSE` 英文原文为准。商用合作请联系项目作者。

SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
