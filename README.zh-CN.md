# Codefolio

<p align="center">
  <a href="README.md">English</a> ·
  <a href="https://github.com/1634594707/Codefolio/releases">发布版本</a> ·
  <a href="LICENSE">许可证</a>
</p>

将 GitHub 公开足迹转化为专业简历、可分享社交卡片，以及可执行的仓库对标报告。

---

## 功能特性

| 功能 | 说明 |
|---|---|
| **GitScore** | 多维度开发者评分（0–100） |
| **AI 洞察** | 大语言模型生成的风格标签与技术摘要 |
| **简历生成** | Markdown / PDF 专业简历输出 |
| **社交卡片** | 适合社交媒体分享的 PNG 卡片 |
| **开发者对比** | 最多三名 GitHub 用户并排对比 |
| **仓库对标** | 我的仓库 vs 同类标杆——差距矩阵、行动项、成功假设卡片 |
| **推荐标杆** | 通过 GitHub Search API 自动推荐相似仓库 |
| **导出** | 一键导出完整对标报告（Markdown，中英文） |
| **缓存** | Redis 缓存，按数据类型差异化 TTL |
| **国际化** | 中英文界面与内容 |
| **主题** | 亮色 / 暗色模式 |

---

## v1.1.0 更新内容

- **仓库对标**正式上线——8 维度差距矩阵、行动项、成功假设卡片、可选 LLM 叙述摘要
- **推荐标杆**按语言、话题、规模自动推荐相似仓库
- **Markdown 导出**完整对标报告（中英文）
- **过期警告**：缓存数据超过 7 天时提示刷新
- **速率限制**：per-IP 滑动窗口，保护 benchmark 接口
- **Token 脱敏**：GitHub Token 不会出现在日志或错误响应中
- **完整测试套件**：36 个属性测试（Hypothesis）+ 前端单元/属性测试（Vitest + fast-check）

完整变更记录见 [CHANGELOG.md](CHANGELOG.md)。

---

## 技术架构

- **前端**：React 18 + Vite + Tailwind CSS
- **后端**：Python 3.11+ + FastAPI
- **缓存**：Redis 7+
- **API**：GitHub REST/GraphQL API、DeepSeek / GPT-4o-mini

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Redis 7+

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # 填入你的 API 密钥
redis-server &
python main.py
```

后端服务运行在 `http://localhost:8000`

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端服务运行在 `http://localhost:5173`

---

## 环境变量

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

# CORS 跨域
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# 缓存过期时间（秒）
GITHUB_CACHE_TTL=86400
AI_CACHE_TTL=604800

# 速率限制（benchmark 接口）
RATE_LIMIT_MAX_REQUESTS=10
RATE_LIMIT_WINDOW_SECONDS=60
```

---

## API 接口

### 核心接口
| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/generate` | 生成开发者档案 |

### 仓库对标接口
| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/repos/profile` | 获取 / 缓存仓库画像 |
| `POST` | `/api/repos/benchmark` | 多仓库对比（1–3 个标杆） |
| `GET` | `/api/repos/suggest-benchmarks` | 自动推荐相似标杆仓库 |
| `DELETE` | `/api/repos/cache/{owner}/{repo}` | 清除仓库缓存 |

---

## 项目结构

```
codefolio/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── benchmark_models.py          # 数据模型
│   ├── cache_keys.py                # Redis 键统一定义
│   ├── i18n/                        # 中英文翻译文件
│   ├── routers/
│   │   └── repos_benchmark.py       # 对标 API 路由
│   ├── services/
│   │   ├── benchmark_analysis_service.py
│   │   ├── benchmark_recommendation_service.py
│   │   ├── bucket_service.py
│   │   ├── dimension_analyzer.py
│   │   ├── action_generator.py
│   │   ├── repository_profile_service.py
│   │   ├── github_service.py
│   │   └── ai_service.py
│   └── utils/
│       ├── rate_limiter.py
│       ├── token_redaction.py
│       └── redis_client.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── BenchmarkMatrix.tsx
│       │   ├── ActionList.tsx
│       │   └── HypothesisCards.tsx
│       ├── pages/
│       │   ├── CompareRepos.tsx
│       │   └── Export.tsx
│       ├── utils/
│       │   ├── benchmarkExport.ts
│       │   └── formatCacheAge.ts
│       └── types/
│           └── benchmark.ts
├── CHANGELOG.md
├── LICENSE
├── README.md
└── README.zh-CN.md
```

---

## 许可证

本项目采用 **[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)**，完整条文见 [`LICENSE`](LICENSE)。

- ✅ 个人学习、研究、教育、符合条件的非营利机构
- ❌ 商业使用需另行获得版权方书面授权

SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
