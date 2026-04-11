# Design Document: Codefolio

## Overview

Codefolio is a GitHub profile analyzer that transforms developer data into professional artifacts. The system follows a modular monolithic architecture with clear separation between data fetching, scoring, AI generation, and rendering layers. The frontend is built with React and Tailwind CSS, while the backend uses Python with FastAPI for high-performance async operations.

The core workflow: User inputs GitHub username → System fetches data from GitHub GraphQL API → GitScore engine calculates multi-dimensional score → AI service generates insights → Render service produces Markdown resume and PNG social card → Results displayed to user with download options.

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend Layer                         │
│              React + Vite + Tailwind CSS                 │
│  Pages: Input → Loading → Results (Resume + Card)       │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP/REST
┌─────────────────────────▼───────────────────────────────┐
│                   Backend Layer                          │
│                 Python + FastAPI                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │ API Router Layer                                     ││
│  │  • POST /api/generate                                ││
│  │  • GET /api/export/pdf                               ││
│  └─────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────┐│
│  │ Service Layer                                        ││
│  │  • GitHubService: GraphQL queries + rate limiting    ││
│  │  • ScoreEngine: Multi-dimensional scoring algorithm  ││
│  │  • AIService: LLM integration for insights          ││
│  │  • RenderService: Markdown/HTML/PNG generation      ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                 Data & Cache Layer                       │
│  • PostgreSQL: Persistent app data                       │
│  • Redis: Cache GitHub API responses (24h TTL)          │
│  • Redis: Cache AI-generated content                    │
│  • Object Storage (S3/R2): Store generated images       │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

**Frontend:**
- React 18 with Vite for fast development
- Tailwind CSS for styling
- html2canvas for client-side PNG generation
- Recharts for radar chart visualization
- Axios for API communication

**Backend:**
- Python 3.11+
- FastAPI for async REST API
- httpx for async HTTP requests
- Playwright for server-side rendering (optional)
- WeasyPrint or ReportLab for PDF generation

**Data Layer:**
- PostgreSQL 15+ for persistent relational data
- Redis 7+ for caching
- Cloudflare R2 or AWS S3 for image storage

**External Services:**
- GitHub GraphQL API v4
- DeepSeek-V3 or GPT-4o-mini for AI generation

**Deployment:**
- Vercel for frontend hosting
- Railway or Fly.io for backend hosting

## Components and Interfaces

### 1. GitHubService

**Responsibility:** Fetch and normalize GitHub user data via GraphQL API.

**Interface:**
```python
class GitHubService:
    async def fetch_user_data(username: str) -> UserData:
        """
        Fetch comprehensive user data from GitHub GraphQL API.
        
        Returns UserData containing:
        - profile: user info (name, avatar, bio, followers, following)
        - repositories: list of repos with stars, forks, language, has_readme, has_license
        - contributions: total commits and PRs in last year
        - languages: distribution of programming languages
        """
        pass
    
    async def check_rate_limit() -> RateLimitInfo:
        """Check current GitHub API rate limit status."""
        pass
```

**GraphQL Query Structure:**
```graphql
query($username: String!) {
  user(login: $username) {
    name
    avatarUrl
    bio
    followers { totalCount }
    following { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes {
        name
        description
        stargazerCount
        forkCount
        primaryLanguage { name }
        languages(first: 10) {
          edges {
            size
            node { name }
          }
        }
        object(expression: "HEAD:README.md") { ... }
        licenseInfo { name }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
    }
  }
}
```

**Caching Strategy:**
- Check Redis cache before API call
- Cache key: `github:user:{username}`
- TTL: 24 hours
- Store normalized JSON response

### 2. ScoreEngine

**Responsibility:** Calculate GitScore from GitHub data using multi-dimensional algorithm.

**Interface:**
```python
class ScoreEngine:
    def calculate_gitscore(user_data: UserData) -> GitScore:
        """
        Calculate 0-100 GitScore with dimension breakdown.
        
        Returns GitScore containing:
        - total: float (0-100)
        - dimensions: dict with 5 dimension scores
          - impact: 0-35 (stars + forks)
          - contribution: 0-25 (commits + PRs)
          - community: 0-20 (followers + following)
          - tech_breadth: 0-15 (language diversity)
          - documentation: 0-5 (README + LICENSE)
        """
        pass
    
    def _calculate_impact_score(repos: List[Repository]) -> float:
        """Calculate project impact from stars and forks."""
        pass
    
    def _calculate_contribution_score(contributions: Contributions) -> float:
        """Calculate code contribution from commits and PRs."""
        pass
    
    def _calculate_community_score(followers: int, following: int) -> float:
        """Calculate community activity score."""
        pass
    
    def _calculate_tech_breadth_score(languages: Set[str]) -> float:
        """Calculate tech breadth from language diversity."""
        pass
    
    def _calculate_documentation_score(repos: List[Repository]) -> float:
        """Calculate documentation quality score."""
        pass
```

**Scoring Formulas:**

1. **Impact Score (0-35):**
   ```
   total_stars = sum(repo.stars for repo in repos)
   total_forks = sum(repo.forks for repo in repos)
   raw_score = (total_stars * 0.3 + total_forks * 0.5) / 15
   impact = min(35.0, raw_score)
   ```

2. **Contribution Score (0-25):**
   ```
   commits = contributions.total_commits_last_year
   prs = contributions.total_prs_last_year
   raw_score = commits * 0.01 + prs * 0.5
   contribution = min(25.0, raw_score)
   ```

3. **Community Score (0-20):**
   ```
   raw_score = followers * 0.05 + following * 0.02
   community = min(20.0, raw_score)
   ```

4. **Tech Breadth Score (0-15):**
   ```
   lang_count = len(unique_languages)
   tech_breadth = min(15.0, lang_count * 1.5)
   ```

5. **Documentation Score (0-5):**
   ```
   has_readme = any(repo.has_readme for repo in repos)
   has_license = any(repo.has_license for repo in repos)
   documentation = (2 if has_readme else 0) + (3 if has_license else 0)
   ```

### 3. AIService

**Responsibility:** Generate AI-powered insights using LLM.

**Interface:**
```python
class AIService:
    async def generate_style_tags(user_data: UserData, gitscore: GitScore) -> List[str]:
        """
        Generate 3-5 style tags describing coding patterns.
        Each tag is 2-4 characters, prefixed with #.
        Example: ["#全栈夜猫子", "#提交狂魔", "#开源强迫症"]
        """
        pass
    
    async def generate_roast_comment(user_data: UserData, gitscore: GitScore) -> str:
        """
        Generate a humorous roast comment (max 30 chars).
        Must be respectful and use programming humor.
        Example: "看来你的周末都献给了React，不愧是组件抽象艺术家。"
        """
        pass
    
    async def generate_tech_summary(user_data: UserData) -> str:
        """
        Generate a brief tech stack summary.
        Example: "Full-stack developer specializing in Python and React, 
                  with strong focus on open-source contributions."
        """
        pass
```

**Prompt Templates:**

*Style Tags Prompt:*
```
You are analyzing a developer's GitHub profile. Generate 3-5 style tags (2-4 characters each) 
that describe their coding patterns. Use # prefix. Be creative and engaging.

Data:
- Primary languages: {languages}
- Commits last year: {commits}
- Longest streak: {streak} days
- Top repo: {top_repo}

Output format: JSON array like ["#全栈夜猫子", "#提交狂魔", "#开源强迫症"]
```

*Roast Comment Prompt:*
```
You are a humorous but friendly code reviewer. Based on the developer's GitHub data, 
write ONE sentence (max 30 characters) that points out their characteristics with 
programming humor. Be respectful, no personal attacks.

Data: {same as above}

Output one sentence only.
```

**Caching:**
- Cache key: `ai:{username}:tags`, `ai:{username}:roast`, `ai:{username}:summary`
- TTL: 7 days (AI results don't change frequently)

### 4. RenderService

**Responsibility:** Generate Markdown resumes, HTML, and PNG social cards.

**Interface:**
```python
class RenderService:
    def generate_markdown_resume(
        user_data: UserData,
        gitscore: GitScore,
        ai_insights: AIInsights
    ) -> str:
        """Generate Markdown formatted resume."""
        pass
    
    async def generate_pdf_resume(markdown: str) -> bytes:
        """Convert Markdown to PDF."""
        pass
    
    async def generate_social_card(
        user_data: UserData,
        gitscore: GitScore,
        ai_insights: AIInsights
    ) -> bytes:
        """Generate PNG social card image (1200x630)."""
        pass
```

**Markdown Template Structure:**
```markdown
# {name} (@{username})

{bio}

## GitScore: {total}/100

### Score Breakdown
- 🎯 Project Impact: {impact}/35
- 💻 Code Contribution: {contribution}/25
- 👥 Community Activity: {community}/20
- 🔧 Tech Breadth: {tech_breadth}/15
- 📚 Documentation: {documentation}/5

## Tech Stack
{language_distribution_chart}

## Top Projects
1. **{repo_name}** ⭐ {stars}
   {description}

## AI Insights
**Style Tags:** {tags}
**Summary:** {tech_summary}

## Contribution Stats
- Total Commits (Last Year): {commits}
- Total Pull Requests: {prs}
- Followers: {followers}
```

**Social Card Layout:**
```
┌─────────────────────────────────────────┐
│  [Avatar]  {Username}                   │
│            GitScore: {score}/100        │
│            [Radar Chart]                │
│                                         │
│  {Style Tags}                           │
│  "{Roast Comment}"                      │
│                                         │
│  [Tech Stack Icons]                     │
└─────────────────────────────────────────┘
```

### 5. API Router

**Endpoints:**

```python
@app.post("/api/generate")
async def generate_profile(request: GenerateRequest) -> GenerateResponse:
    """
    Main endpoint for profile generation.
    
    Request: { "username": "string", "language": "en" | "zh" }
    Response: {
        "resume_markdown": "string",
        "gitscore": GitScore,
        "ai_insights": AIInsights,
        "card_data": CardData
    }
    """
    pass

@app.get("/api/export/pdf")
async def export_pdf(username: str, language: str = "en") -> StreamingResponse:
    """Export resume as PDF."""
    pass

@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    pass
```

**Error Handling:**
- 400: Invalid username format
- 404: GitHub user not found
- 429: Rate limit exceeded
- 500: Internal server error
- 503: External service unavailable

### 6. Internationalization Service

**Responsibility:** Manage translations and language-specific content.

**Interface:**
```python
class I18nService:
    def __init__(self, language: str = "en"):
        """Initialize with language code (en or zh)."""
        self.language = language
        self.translations = self._load_translations()
    
    def translate(self, key: str) -> str:
        """Get translated text for a key."""
        pass
    
    def format_number(self, number: int) -> str:
        """Format numbers according to locale (e.g., 1,000 vs 1.000)."""
        pass
    
    def get_ai_prompt_language(self) -> str:
        """Return language instruction for AI prompts."""
        pass
```

**Translation Structure:**
```json
{
  "en": {
    "nav": {
      "dashboard": "Dashboard",
      "projects": "Projects",
      "resume": "Resume",
      "insights": "Insights"
    },
    "hero": {
      "title": "Your code is an Artifact.",
      "subtitle": "Transform your GitHub footprint into a professional showcase",
      "cta": "Generate My Profile"
    },
    "gitscore": {
      "title": "GitScore",
      "impact": "Project Impact",
      "contribution": "Code Contribution",
      "community": "Community Activity",
      "tech_breadth": "Tech Breadth",
      "documentation": "Documentation"
    }
  },
  "zh": {
    "nav": {
      "dashboard": "仪表盘",
      "projects": "项目",
      "resume": "简历",
      "insights": "洞察"
    },
    "hero": {
      "title": "你的代码是艺术品。",
      "subtitle": "将你的GitHub足迹转化为专业展示",
      "cta": "生成我的档案"
    },
    "gitscore": {
      "title": "技术评分",
      "impact": "项目影响力",
      "contribution": "代码贡献",
      "community": "社区活跃度",
      "tech_breadth": "技术广度",
      "documentation": "文档质量"
    }
  }
}
```

### 7. Theme System

**Responsibility:** Manage light/dark theme switching with smooth transitions.

**CSS Variables Structure:**
```css
:root {
  /* Light Mode Colors */
  --color-primary: #005bbf;
  --color-secondary: #5b16c1;
  --color-tertiary: #00902f;
  --color-background: #ffffff;
  --color-surface: #f8fafc;
  --color-surface-container: #f1f5f9;
  --color-on-surface: #0f172a;
  --color-on-surface-variant: #475569;
  --color-outline: #cbd5e1;
  --color-outline-variant: #e2e8f0;
}

.dark {
  /* Dark Mode Colors (existing palette) */
  --color-primary: #acc7ff;
  --color-secondary: #d2bbff;
  --color-tertiary: #67df70;
  --color-background: #10141a;
  --color-surface: #10141a;
  --color-surface-container: #1c2026;
  --color-on-surface: #dfe2eb;
  --color-on-surface-variant: #c6c6cb;
  --color-outline: #8f9095;
  --color-outline-variant: #45474b;
}

/* Smooth transitions */
* {
  transition: background-color 200ms ease, color 200ms ease, border-color 200ms ease;
}

@media (prefers-reduced-motion: reduce) {
  * {
    transition: none !important;
  }
}
```

**Frontend Theme Manager:**
```typescript
class ThemeManager {
  private theme: 'light' | 'dark';
  
  constructor() {
    this.theme = this.getInitialTheme();
    this.applyTheme(this.theme);
  }
  
  private getInitialTheme(): 'light' | 'dark' {
    // 1. Check localStorage
    const stored = localStorage.getItem('theme');
    if (stored === 'light' || stored === 'dark') return stored;
    
    // 2. Check system preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    
    return 'light';
  }
  
  toggleTheme(): void {
    this.theme = this.theme === 'light' ? 'dark' : 'light';
    this.applyTheme(this.theme);
    localStorage.setItem('theme', this.theme);
  }
  
  private applyTheme(theme: 'light' | 'dark'): void {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }
}
```

**Frontend Language Manager:**
```typescript
class LanguageManager {
  private language: 'en' | 'zh';
  private translations: Record<string, any>;
  
  constructor() {
    this.language = this.getInitialLanguage();
    this.translations = this.loadTranslations();
  }
  
  private getInitialLanguage(): 'en' | 'zh' {
    // 1. Check localStorage
    const stored = localStorage.getItem('language');
    if (stored === 'en' || stored === 'zh') return stored;
    
    // 2. Check browser language
    const browserLang = navigator.language.toLowerCase();
    if (browserLang.startsWith('zh')) return 'zh';
    
    return 'en';
  }
  
  setLanguage(lang: 'en' | 'zh'): void {
    this.language = lang;
    localStorage.setItem('language', lang);
    this.updateUI();
  }
  
  translate(key: string): string {
    const keys = key.split('.');
    let value = this.translations[this.language];
    for (const k of keys) {
      value = value?.[k];
    }
    return value || key;
  }
  
  private updateUI(): void {
    // Update all elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (key) {
        el.textContent = this.translate(key);
      }
    });
  }
}
```

## Data Models

### UserData
```python
@dataclass
class UserData:
    username: str
    name: str
    avatar_url: str
    bio: str
    followers: int
    following: int
    repositories: List[Repository]
    contributions: Contributions
    languages: Dict[str, int]  # language -> bytes of code
```

### Repository
```python
@dataclass
class Repository:
    name: str
    description: str
    stars: int
    forks: int
    language: str
    has_readme: bool
    has_license: bool
    url: str
```

### Contributions
```python
@dataclass
class Contributions:
    total_commits_last_year: int
    total_prs_last_year: int
    longest_streak: int
```

### GitScore
```python
@dataclass
class GitScore:
    total: float  # 0-100
    dimensions: Dict[str, float]  # impact, contribution, community, tech_breadth, documentation
```

### AIInsights
```python
@dataclass
class AIInsights:
    style_tags: List[str]
    roast_comment: str
    tech_summary: str
```

### CardData
```python
@dataclass
class CardData:
    username: str
    avatar_url: str
    gitscore: float
    radar_chart_data: List[float]  # 5 dimension values
    style_tags: List[str]
    roast_comment: str
    tech_icons: List[str]  # URLs or names of tech stack icons

@dataclass
class GenerateRequest:
    username: str
    language: str = "en"  # "en" or "zh"

@dataclass
class GenerateResponse:
    resume_markdown: str
    gitscore: GitScore
    ai_insights: AIInsights
    card_data: CardData
```

## Frontend Components

### Theme Toggle Component
```typescript
interface ThemeToggleProps {
  initialTheme?: 'light' | 'dark';
}

const ThemeToggle: React.FC<ThemeToggleProps> = ({ initialTheme }) => {
  const [theme, setTheme] = useState(initialTheme || 'dark');
  
  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', newTheme);
  };
  
  return (
    <button onClick={toggleTheme} className="theme-toggle">
      {theme === 'light' ? '🌙' : '☀️'}
    </button>
  );
};
```

### Language Toggle Component
```typescript
interface LanguageToggleProps {
  initialLanguage?: 'en' | 'zh';
  onLanguageChange?: (lang: 'en' | 'zh') => void;
}

const LanguageToggle: React.FC<LanguageToggleProps> = ({ 
  initialLanguage, 
  onLanguageChange 
}) => {
  const [language, setLanguage] = useState(initialLanguage || 'en');
  
  const toggleLanguage = () => {
    const newLang = language === 'en' ? 'zh' : 'en';
    setLanguage(newLang);
    localStorage.setItem('language', newLang);
    onLanguageChange?.(newLang);
  };
  
  return (
    <button onClick={toggleLanguage} className="language-toggle">
      {language === 'en' ? '中文' : 'EN'}
    </button>
  );
};
```

## Multi-View UI Design (Overview / Repositories / AI Analysis / Export)

### Navigation Information Architecture

The sidebar includes 4 first-level views and each view maps to a dedicated content layout:

- **Overview**: Global KPI + profile summary + quick actions
- **Repositories**: Searchable and filterable repository explorer
- **AI Analysis**: Insight explanations + suggestions + generated writing
- **Export**: Resume/card export config + preview + history

Suggested frontend state model:

```typescript
type ActiveView = "overview" | "repositories" | "analysis" | "export";

interface AppViewState {
  activeView: ActiveView;
  query: string;
  sortBy: "stars" | "forks" | "updated_at";
  sortDirection: "asc" | "desc";
  languageFilter: string[];
  minStars?: number;
}
```

### View-Specific Layout Recommendations

1. **Overview**
   - Hero summary (username, score, core tags)
   - KPI cards (score, followers, commits, top language)
   - Contribution and repository snapshots

2. **Repositories**
   - Top control bar: search + language filter + sort + threshold
   - Main list/table: paginated repository records
   - Side drawer (optional): selected repository detail and quick actions

3. **AI Analysis**
   - Strength/weakness explanation cards with evidence
   - Actionable suggestions grouped by short/mid/long term
   - Generated artifacts panel (resume bullet improvements, social text)

4. **Export**
   - Export options (format, language, theme, sections)
   - Live preview (resume/card)
   - Export task history and downloadable artifacts

## Repository Database Design

### Database Choice

For the repository view and long-term analytics, use **PostgreSQL** as the source of truth and keep Redis as a short-TTL cache layer.

- PostgreSQL: normalized durable data + relational querying
- Redis: hot read cache for profile generation and repository list queries
- Object storage: generated files (card image/PDF) metadata points to URL

### Core ER Model

- One `users` record can have many `repositories`
- One `profile_snapshots` record stores a generation-time snapshot
- `repository_metrics_daily` stores time-series trend data per repo
- `export_jobs` tracks async export tasks and outcomes

### SQL Schema (Recommended)

```sql
-- 1) user profile table
CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  github_user_id BIGINT UNIQUE NOT NULL,
  username VARCHAR(39) UNIQUE NOT NULL,
  display_name VARCHAR(120),
  avatar_url TEXT,
  bio TEXT,
  followers INTEGER NOT NULL DEFAULT 0,
  following INTEGER NOT NULL DEFAULT 0,
  profile_url TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2) repository table
CREATE TABLE repositories (
  id BIGSERIAL PRIMARY KEY,
  github_repo_id BIGINT UNIQUE NOT NULL,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  full_name VARCHAR(200) NOT NULL,
  description TEXT,
  html_url TEXT NOT NULL,
  homepage_url TEXT,
  primary_language VARCHAR(64),
  stars INTEGER NOT NULL DEFAULT 0,
  forks INTEGER NOT NULL DEFAULT 0,
  open_issues INTEGER NOT NULL DEFAULT 0,
  watchers INTEGER NOT NULL DEFAULT 0,
  size_kb INTEGER NOT NULL DEFAULT 0,
  is_fork BOOLEAN NOT NULL DEFAULT FALSE,
  is_private BOOLEAN NOT NULL DEFAULT FALSE,
  has_readme BOOLEAN NOT NULL DEFAULT FALSE,
  has_license BOOLEAN NOT NULL DEFAULT FALSE,
  pushed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, name)
);

-- 3) repository language distribution (normalized)
CREATE TABLE repository_languages (
  id BIGSERIAL PRIMARY KEY,
  repository_id BIGINT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
  language_name VARCHAR(64) NOT NULL,
  bytes_of_code BIGINT NOT NULL DEFAULT 0,
  percentage NUMERIC(5,2) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(repository_id, language_name)
);

-- 4) profile generation snapshots (for reproducible export/history)
CREATE TABLE profile_snapshots (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  source VARCHAR(32) NOT NULL DEFAULT 'github',
  gitscore_total NUMERIC(5,2) NOT NULL,
  dim_impact NUMERIC(5,2) NOT NULL,
  dim_contribution NUMERIC(5,2) NOT NULL,
  dim_community NUMERIC(5,2) NOT NULL,
  dim_tech_breadth NUMERIC(5,2) NOT NULL,
  dim_documentation NUMERIC(5,2) NOT NULL,
  ai_style_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  ai_roast_comment TEXT NOT NULL DEFAULT '',
  ai_tech_summary TEXT NOT NULL DEFAULT '',
  resume_markdown TEXT NOT NULL,
  language_code VARCHAR(8) NOT NULL DEFAULT 'en',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5) daily time-series metrics for trend charts
CREATE TABLE repository_metrics_daily (
  id BIGSERIAL PRIMARY KEY,
  repository_id BIGINT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
  metric_date DATE NOT NULL,
  stars INTEGER NOT NULL DEFAULT 0,
  forks INTEGER NOT NULL DEFAULT 0,
  open_issues INTEGER NOT NULL DEFAULT 0,
  watchers INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(repository_id, metric_date)
);

-- 6) export jobs for async processing
CREATE TABLE export_jobs (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  snapshot_id BIGINT REFERENCES profile_snapshots(id) ON DELETE SET NULL,
  job_type VARCHAR(16) NOT NULL, -- pdf | png | markdown | json
  language_code VARCHAR(8) NOT NULL DEFAULT 'en',
  theme VARCHAR(8) NOT NULL DEFAULT 'dark',
  status VARCHAR(16) NOT NULL DEFAULT 'queued', -- queued|running|done|failed
  file_url TEXT,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ
);
```

### Indexing Strategy

```sql
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_repositories_user_id ON repositories(user_id);
CREATE INDEX idx_repositories_stars_desc ON repositories(user_id, stars DESC);
CREATE INDEX idx_repositories_updated_desc ON repositories(user_id, updated_at DESC);
CREATE INDEX idx_repositories_language ON repositories(user_id, primary_language);
CREATE INDEX idx_repo_metrics_repo_date ON repository_metrics_daily(repository_id, metric_date DESC);
CREATE INDEX idx_snapshots_user_created ON profile_snapshots(user_id, created_at DESC);
CREATE INDEX idx_export_jobs_user_created ON export_jobs(user_id, created_at DESC);
```

### Repository Page Query Patterns

1. **Repository list with filters**
```sql
SELECT
  r.id, r.name, r.description, r.primary_language, r.stars, r.forks, r.updated_at, r.html_url
FROM repositories r
JOIN users u ON u.id = r.user_id
WHERE u.username = $1
  AND ($2::text IS NULL OR r.primary_language = $2)
  AND ($3::int IS NULL OR r.stars >= $3)
  AND ($4::text IS NULL OR r.name ILIKE '%' || $4 || '%' OR r.description ILIKE '%' || $4 || '%')
ORDER BY
  CASE WHEN $5 = 'stars' THEN r.stars END DESC,
  CASE WHEN $5 = 'forks' THEN r.forks END DESC,
  CASE WHEN $5 = 'updated_at' THEN r.updated_at END DESC
LIMIT $6 OFFSET $7;
```

2. **Language distribution for selected user**
```sql
SELECT rl.language_name, SUM(rl.bytes_of_code) AS bytes
FROM repository_languages rl
JOIN repositories r ON r.id = rl.repository_id
JOIN users u ON u.id = r.user_id
WHERE u.username = $1
GROUP BY rl.language_name
ORDER BY bytes DESC;
```

3. **Snapshot history for export and rollback**
```sql
SELECT id, gitscore_total, language_code, created_at
FROM profile_snapshots
WHERE user_id = $1
ORDER BY created_at DESC
LIMIT 20;
```

### Data Freshness and Sync Policy

- If cache hit and age < 24h: serve from Redis + PostgreSQL
- If stale/miss: fetch from GitHub, upsert into PostgreSQL, refresh Redis
- Upsert strategy:
  - `users`: upsert by `github_user_id`
  - `repositories`: upsert by `github_repo_id`
  - `repository_languages`: delete+insert per repo refresh

### Suggested Backend Interfaces for Repository View

```python
@app.get("/api/repositories")
async def list_repositories(
    username: str,
    q: str | None = None,
    language: str | None = None,
    min_stars: int | None = None,
    sort_by: str = "stars",
    page: int = 1,
    page_size: int = 20
) -> RepositoryListResponse:
    pass

@app.get("/api/repositories/{repo_id}")
async def get_repository_detail(repo_id: int) -> RepositoryDetailResponse:
    pass
```
