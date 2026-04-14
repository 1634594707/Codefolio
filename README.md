# Codefolio

<p align="center">
  <a href="README.zh-CN.md">中文版</a> ·
  <a href="https://github.com/1634594707/Codefolio/releases">Releases</a> ·
  <a href="LICENSE">License</a>
</p>

Transform your GitHub footprint into professional resumes, shareable social cards, and actionable repository benchmarks.

---

## Features

| Feature | Description |
|---|---|
| **GitScore** | Multi-dimensional developer scoring (0–100) |
| **AI Insights** | Style tags and tech summaries powered by LLM |
| **Resume Generation** | Professional Markdown / PDF resumes |
| **Social Cards** | Shareable PNG cards for social media |
| **Developer Compare** | Side-by-side comparison of up to 3 GitHub profiles |
| **Repository Benchmark** | Compare your repo against peers — gap matrix, action items, hypothesis cards |
| **Benchmark Recommendations** | Auto-suggest similar repos via GitHub Search API |
| **Export** | One-click Markdown export of benchmark reports (EN / ZH) |
| **Caching** | Redis-based caching with differential TTL per data type |
| **i18n** | English and Chinese UI + content |
| **Theme** | Light and dark mode |

---

## What's New in v1.1.0

- **Repository Benchmark** is now fully shipped — gap matrix, 8-dimension analysis, action items, success hypothesis cards, and optional LLM narrative
- **Suggest Benchmarks** button auto-finds similar repos by language, topics, and size category
- **Markdown export** of full benchmark reports (EN/ZH)
- **Staleness warning** when cached data is older than 7 days
- **Rate limiting** per IP to protect benchmark endpoints
- **Token redaction** — GitHub tokens are never exposed in logs or error responses
- **Full test suite** — 36 property-based tests (Hypothesis) + frontend unit/property tests (Vitest + fast-check)

See [CHANGELOG.md](CHANGELOG.md) for the full list.

---

## Architecture

- **Frontend**: React 18 + Vite + Tailwind CSS
- **Backend**: Python 3.11+ + FastAPI
- **Cache**: Redis 7+
- **APIs**: GitHub REST/GraphQL API, DeepSeek / GPT-4o-mini

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis 7+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # fill in your API keys
redis-server &
python main.py
```

Backend runs at `http://localhost:8000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

---

## Environment Variables

```env
# GitHub API
GITHUB_TOKEN=your_github_token

# AI API
AI_API_KEY=your_ai_api_key
AI_API_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat

# Redis
REDIS_URL=redis://localhost:6379
REDIS_DB=0

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Cache TTL (seconds)
GITHUB_CACHE_TTL=86400
AI_CACHE_TTL=604800

# Rate limiting (benchmark endpoints)
RATE_LIMIT_MAX_REQUESTS=10
RATE_LIMIT_WINDOW_SECONDS=60
```

---

## API Endpoints

### Core
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/generate` | Generate developer profile |

### Repository Benchmark
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/repos/profile` | Fetch / cache a repository profile |
| `POST` | `/api/repos/benchmark` | Run multi-repo comparison (1–3 benchmarks) |
| `GET` | `/api/repos/suggest-benchmarks` | Auto-suggest similar benchmark repos |
| `DELETE` | `/api/repos/cache/{owner}/{repo}` | Invalidate repository cache |

---

## Project Structure

```
codefolio/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── benchmark_models.py          # Pydantic / dataclass models
│   ├── cache_keys.py                # Centralised Redis key definitions
│   ├── i18n/                        # EN / ZH translation files
│   ├── routers/
│   │   └── repos_benchmark.py       # Benchmark API router
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

## License

Licensed under the **[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)**.

- ✅ Personal use, education, research, qualifying nonprofits
- ❌ Commercial use without separate written permission

See [`LICENSE`](LICENSE) for full terms.  
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
