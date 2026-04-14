# Codefolio

<p align="center">
  <a href="README.zh-CN.md">中文文档</a> |
  <a href="https://github.com/1634594707/Codefolio/releases">Releases</a> |
  <a href="LICENSE">License</a>
</p>

Codefolio turns a GitHub profile into resumes, social cards, AI summaries, and repository benchmark reports.

## Features

| Feature | Description |
|---|---|
| GitScore | Multi-dimensional developer scoring |
| AI Insights | Style tags, roast comments, and technical summaries |
| Resume Export | Markdown and PDF export |
| Social Cards | Shareable image cards |
| Developer Compare | Side-by-side comparison for up to 3 GitHub users |
| Repository Benchmark | Compare one repo against peers with gap analysis |
| Benchmark Suggestions | Auto-discover comparable repositories |
| Workspace Isolation | Browser workspace scoped AI and benchmark artifacts |
| Docker Deployment | Full stack container setup for local and production use |

## Stack

- Frontend: React 18, Vite, Tailwind CSS
- Backend: FastAPI, Python 3.11
- Cache: Redis
- Storage: SQLite snapshot store
- Upstream APIs: GitHub REST/GraphQL, OpenAI-compatible LLM APIs

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis 7+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Windows activate command:

```powershell
venv\Scripts\activate
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Default URLs:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

## Docker

### Development compose

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:8080`
- Backend: internal `backend:8000`
- Redis: internal `redis:6379`

### Production compose

1. Prepare backend secrets:

```bash
cp backend/.env.example backend/.env
```

2. Prepare production variables:

```bash
cp .env.production.example .env.production
```

3. Update:

- `backend/.env` with `GITHUB_TOKEN`, `AI_API_KEY`, and model settings
- `.env.production` with your real domain and public port

4. Start production services:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

Production notes:

- Frontend is served by Nginx.
- `/api/*` is proxied from Nginx to the backend container.
- Backend data persists in the `backend-data` volume.
- Redis data persists in the `redis-data` volume.
- Compose health checks wait for Redis and the backend before exposing the frontend.

### PostgreSQL upgrade path

Codefolio now supports a database compatibility layer for SQLite and PostgreSQL.

- Default mode keeps using `DATABASE_PATH` with SQLite
- PostgreSQL mode is enabled by setting `DATABASE_URL=postgresql://...`
- PostgreSQL runtime now uses a connection pool controlled by `POSTGRES_POOL_MIN_SIZE` and `POSTGRES_POOL_MAX_SIZE`
- Business code still uses the same snapshot store API

Compose example with PostgreSQL:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml -f docker-compose.postgres.yml up -d --build
```

Files related to this path:

- [docker-compose.postgres.yml](/D:/Administrator/Desktop/Project/Codefolio/docker-compose.postgres.yml)
- [backend/scripts/migrate_sqlite_to_postgres.py](/D:/Administrator/Desktop/Project/Codefolio/backend/scripts/migrate_sqlite_to_postgres.py)
- [backend/scripts/migrate_postgres_to_sqlite.py](/D:/Administrator/Desktop/Project/Codefolio/backend/scripts/migrate_postgres_to_sqlite.py)
- [backend/scripts/backup_postgres.py](/D:/Administrator/Desktop/Project/Codefolio/backend/scripts/backup_postgres.py)
- [backend/scripts/restore_postgres.py](/D:/Administrator/Desktop/Project/Codefolio/backend/scripts/restore_postgres.py)
- [scripts/deploy-prod.ps1](/D:/Administrator/Desktop/Project/Codefolio/scripts/deploy-prod.ps1)
- [scripts/deploy-prod.sh](/D:/Administrator/Desktop/Project/Codefolio/scripts/deploy-prod.sh)
- [scripts/rollback-to-sqlite.ps1](/D:/Administrator/Desktop/Project/Codefolio/scripts/rollback-to-sqlite.ps1)
- [scripts/rollback-to-sqlite.sh](/D:/Administrator/Desktop/Project/Codefolio/scripts/rollback-to-sqlite.sh)
- [deploy/Caddyfile.example](/D:/Administrator/Desktop/Project/Codefolio/deploy/Caddyfile.example)
- [deploy/nginx.codefolio.conf](/D:/Administrator/Desktop/Project/Codefolio/deploy/nginx.codefolio.conf)

### One-command production flow

PowerShell:

```powershell
./scripts/deploy-prod.ps1 -DatabaseBackend postgres -MigrateSqliteToPostgres -PostgresUrl "postgresql://codefolio:change-me@127.0.0.1:5432/codefolio"
```

Shell:

```bash
DATABASE_BACKEND=postgres \
MIGRATE_SQLITE_TO_POSTGRES=true \
POSTGRES_URL=postgresql://codefolio:change-me@127.0.0.1:5432/codefolio \
./scripts/deploy-prod.sh
```

Rollback to SQLite:

```powershell
./scripts/rollback-to-sqlite.ps1 -PostgresUrl "postgresql://codefolio:change-me@127.0.0.1:5432/codefolio"
```

## Deployment Checklist

- Set a valid `GITHUB_TOKEN`
- Set a valid `AI_API_KEY` or accept local fallback summaries
- Restrict `CORS_ORIGINS` to your real domain
- Keep `backend/.env` out of Git
- Back up the `backend-data` Docker volume
- Put HTTPS in front of the public endpoint if you deploy to the internet
- Run through [PRE_RELEASE_CHECKLIST.md](/D:/Administrator/Desktop/Project/Codefolio/PRE_RELEASE_CHECKLIST.md) before switching traffic

## Workspace Isolation

Codefolio now assigns a browser-scoped workspace id and sends it in `X-Codefolio-Workspace`.

- Public GitHub source data can still use shared cache paths
- AI summaries, repository analysis, and benchmark snapshots are stored per workspace
- The backend records active workspaces for future user-account and team upgrades

## Environment Variables

Key backend variables:

```env
GITHUB_TOKEN=your_github_token
AI_API_KEY=your_ai_api_key
AI_API_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat
AI_REQUEST_TIMEOUT=60.0
REDIS_URL=redis://localhost:6379
REDIS_DB=0
DATABASE_PATH=/app/data/codefolio.db
DATABASE_URL=postgresql://codefolio:change-me@postgres:5432/codefolio
POSTGRES_POOL_MIN_SIZE=1
POSTGRES_POOL_MAX_SIZE=10
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

See [backend/.env.example](/D:/Administrator/Desktop/Project/Codefolio/backend/.env.example) for the full template.

## API

### Core endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status |
| `POST` | `/api/generate` | Generate developer profile data |
| `POST` | `/api/workspaces/ensure` | Register or refresh a workspace scope |

### Repository benchmark endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/repos/profile` | Fetch or cache repository profile |
| `POST` | `/api/repos/benchmark` | Compare one repository against peers |
| `GET` | `/api/repos/suggest-benchmarks` | Recommend similar repositories |
| `DELETE` | `/api/repos/cache/{owner}/{repo}` | Invalidate repository cache |

## Verification

Validated in this repository:

- Frontend production build passes
- Frontend benchmark-related tests pass
- Backend Python syntax checks pass
- `docker compose config` passes

Current environment limitations:

- Full backend pytest requires `hypothesis` installed locally
- `docker compose build` can still fail if the host cannot reach Docker Hub

## License

Licensed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/).
