# Codefolio

<p align="center">
  <a href="README.md">English</a> |
  <a href="https://github.com/1634594707/Codefolio/releases">发布版本</a> |
  <a href="LICENSE">许可证</a>
</p>

Codefolio 可以把 GitHub 公开资料转成简历、社交分享卡片、AI 技术画像和仓库对标报告。

## 功能概览

| 功能 | 说明 |
|---|---|
| GitScore | 多维度开发者评分 |
| AI 洞察 | 风格标签、吐槽文案、技术总结 |
| 简历导出 | Markdown / PDF 导出 |
| 社交卡片 | 适合分享的图片卡片 |
| 开发者对比 | 最多 3 个 GitHub 用户并排对比 |
| 仓库对标 | 我的仓库与同类项目差距分析 |
| 仓库推荐 | 自动推荐可对标的仓库 |
| 工作区隔离 | AI 与 benchmark 结果按浏览器工作区隔离 |
| Docker 部署 | 提供本地和生产环境容器编排 |

## 技术栈

- 前端：React 18、Vite、Tailwind CSS
- 后端：FastAPI、Python 3.11
- 缓存：Redis
- 存储：SQLite 快照库
- 上游接口：GitHub REST / GraphQL、兼容 OpenAI 的 LLM API

## 本地开发

### 环境要求

- Python 3.11+
- Node.js 18+
- Redis 7+

### 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Windows 激活虚拟环境：

```powershell
venv\Scripts\activate
```

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认地址：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`

## Docker

### 开发环境

```bash
docker compose up --build
```

服务说明：

- 前端：`http://localhost:8080`
- 后端：容器内 `backend:8000`
- Redis：容器内 `redis:6379`

### 生产环境

1. 准备后端密钥文件：

```bash
cp backend/.env.example backend/.env
```

2. 准备生产环境变量：

```bash
cp .env.production.example .env.production
```

3. 修改以下内容：

- `backend/.env`：填写 `GITHUB_TOKEN`、`AI_API_KEY`、`AI_MODEL`
- `.env.production`：填写你的域名、对外端口

4. 启动生产环境：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

生产说明：

- 前端由 Nginx 提供静态资源
- `/api/*` 会被代理到后端容器
- `backend-data` 卷负责持久化 SQLite 数据
- `redis-data` 卷负责持久化 Redis 数据
- Compose 会等待 Redis 和后端健康后再拉起前端

更详细的上线说明见 [DEPLOYMENT.md](/D:/Administrator/Desktop/Project/Codefolio/DEPLOYMENT.md)。

## 生产部署检查清单

- 设置有效的 `GITHUB_TOKEN`
- 设置有效的 `AI_API_KEY`
- 将 `CORS_ORIGINS` 收敛到真实域名
- 不要提交 `backend/.env` 和 `.env.production`
- 定期备份 `backend-data` 卷
- 对公网部署时务必接入 HTTPS

## 工作区隔离

Codefolio 现在会为浏览器生成一个工作区 id，并通过 `X-Codefolio-Workspace` 传给后端。

- GitHub 原始公共数据仍然可以共享缓存
- AI 总结、仓库分析和 benchmark 报告按工作区单独存储
- 后端会登记活跃工作区，为后续升级成账号体系或团队体系做准备

## 环境变量

常用后端变量：

```env
GITHUB_TOKEN=your_github_token
AI_API_KEY=your_ai_api_key
AI_API_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat
AI_REQUEST_TIMEOUT=60.0
REDIS_URL=redis://localhost:6379
REDIS_DB=0
DATABASE_PATH=/app/data/codefolio.db
CORS_ORIGINS=http://localhost:8080,https://your-domain.com
GITHUB_CACHE_TTL=86400
AI_CACHE_TTL=604800
REPOSITORY_METADATA_TTL=3600
REPOSITORY_README_TTL=21600
REPOSITORY_STAR_HISTORY_TTL=86400
BENCHMARK_RATE_LIMIT_MAX_REQUESTS=10
BENCHMARK_RATE_LIMIT_WINDOW_SECONDS=60
LLM_NARRATIVE_ENABLED=true
LLM_MAX_README_CHARS_PER_REPO=12000
```

完整模板见 [backend/.env.example](/D:/Administrator/Desktop/Project/Codefolio/backend/.env.example)。

## API

### 核心接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/health` | 服务健康检查 |
| `POST` | `/api/generate` | 生成开发者画像 |
| `POST` | `/api/workspaces/ensure` | 注册或刷新工作区 |

### 仓库对标接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/repos/profile` | 获取或缓存仓库画像 |
| `POST` | `/api/repos/benchmark` | 执行仓库对标分析 |
| `GET` | `/api/repos/suggest-benchmarks` | 推荐相似仓库 |
| `DELETE` | `/api/repos/cache/{owner}/{repo}` | 清理仓库缓存 |

## 已验证内容

当前仓库里已经验证：

- 前端生产构建通过
- 前端 benchmark 相关测试通过
- 后端 Python 语法检查通过
- `docker compose config` 通过

当前环境限制：

- 后端完整 pytest 依赖本机安装 `hypothesis`
- `docker compose build` 仍可能因为当前机器无法访问 Docker Hub 而失败

## 许可证

项目使用 [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)。
