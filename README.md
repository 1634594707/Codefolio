# Codefolio

Transform your GitHub footprint into professional resumes and shareable social cards—and understand how you stack up against other developers and (planned) benchmark repositories.

## Vision

Codefolio helps developers turn public GitHub activity into **resume-ready narratives** and **shareable assets**. The product direction includes deeper **comparison**: not only multi-user GitScore and radar charts, but eventually **repository-level benchmarking**—using observable signals (README quality, topics, releases, activity) plus structured AI output to surface **gaps, actionable tasks, and strategy options**, without promising viral growth. See the design draft for scope, data model, and phased delivery: [`docs/design-compare-repo-growth.md`](docs/design-compare-repo-growth.md).

## Features

- **GitScore**: Multi-dimensional developer scoring (0-100)
- **AI Insights**: Style tags and tech summaries powered by LLM
- **Resume Generation**: Professional Markdown/PDF resumes
- **Social Cards**: Shareable PNG cards for social media
- **Compare**: Side-by-side comparison of up to three GitHub profiles (GitScore, dimensions, languages, summaries)
- **Repositories & export flow**: Curate standout repos and export Markdown / social card previews
- **Caching**: Redis-based caching for performance
- **i18n**: English and Chinese language support
- **Theme**: Light and dark mode support

### Roadmap (design)

- **Repository benchmark mode**: Compare your repo to peers (same language/topics and similar scale), hypothesis cards with evidence, gap matrix, and prioritized action lists—see [`docs/design-compare-repo-growth.md`](docs/design-compare-repo-growth.md) (database and storage options included).

## Architecture

- **Frontend**: React 18 + Vite + Tailwind CSS
- **Backend**: Python 3.11+ + FastAPI
- **Cache**: Redis 7+
- **APIs**: GitHub GraphQL API v4, DeepSeek/GPT-4o-mini

Future benchmark features may add **PostgreSQL** (or SQLite for small deployments) for repository snapshots and reports—details in the design doc above.

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis 7+

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. Start Redis (if not running):
```bash
redis-server
```

6. Run the backend:
```bash
python main.py
```

Backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`

## Environment Variables

### Backend (.env)

```env
# GitHub API
GITHUB_TOKEN=your_github_token_here

# AI API
AI_API_KEY=your_ai_api_key_here
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
```

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/generate` - Generate profile (username, language)
- `GET /api/export/pdf` - Export resume as PDF

## Project Structure

```
codefolio/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── requirements.txt     # Python dependencies
│   ├── services/            # Business logic services
│   │   └── __init__.py
│   └── utils/               # Utility modules
│       ├── __init__.py
│       └── redis_client.py  # Redis connection manager
├── docs/
│   └── design-compare-repo-growth.md  # Compare & repo benchmark design (draft)
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main React component
│   │   ├── main.tsx         # Entry point
│   │   └── index.css        # Global styles with theme
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── LICENSE                  # PolyForm Noncommercial 1.0.0 (no commercial use)
├── README.md
└── README.zh-CN.md
```

## Development

### Backend Development

```bash
cd backend
source venv/bin/activate
python main.py
```

### Frontend Development

```bash
cd frontend
npm run dev
```

### Building for Production

Frontend:
```bash
cd frontend
npm run build
```

## License

This project is licensed under the **[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)**.

- **Non-commercial use** is allowed under the terms in [`LICENSE`](LICENSE) (personal use, education, qualifying nonprofits, etc.).
- **Commercial use** (e.g. selling the product, offering it as part of a paid service, or internal use primarily for commercial advantage outside the license’s exceptions) **is not permitted** without separate written permission from the copyright holder.

This is not legal advice. For commercial licensing, contact the project authors.

SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
