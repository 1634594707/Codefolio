import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import axios from 'axios'
import { useApp, type ResumeProject } from '../context'
import { isRequestAborted } from '../utils/axiosAbort'
import {
  buildResumeProject,
  buildResumeProjectFromAnalysis,
  type RepositoryAnalysisPayload,
} from '../utils/resumeProjects'

interface Repo {
  name: string
  description: string
  stars: number
  forks: number
  language: string
  url: string
  pushed_at?: string
  has_readme?: boolean
  has_license?: boolean
  topics?: string[]
  readme_text?: string
  file_tree?: string[]
}

interface UserData {
  username: string
  avatar_url: string
  bio: string
  followers: number
  following: number
  repositories: Repo[]
}

interface RepositoriesProps {
  language: 'en' | 'zh'
}

type SortMode = 'stars' | 'updated' | 'forks'
type RepoViewMode = 'featured' | 'active' | 'maintained'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const labels = {
  en: {
    title: 'Repositories',
    searchPlaceholder: 'Search repositories...',
    stars: 'Stars',
    forks: 'Forks',
    updated: 'Updated',
    noDescription: 'No description provided.',
    loading: 'Loading...',
    error: 'Failed to load repositories',
    noUser: 'Enter a GitHub username to view repositories',
    visibleRepos: 'Visible repositories',
    featuredView: 'Featured',
    activeView: 'Recently active',
    maintainedView: 'Well documented',
    readyBadge: 'Ready',
    readmeBadge: 'README',
    licenseBadge: 'License',
    lastPush: 'Last push',
    emptyResults: 'No repositories matched this view.',
    analyzeRepo: 'Analyze for resume',
    benchmarkRepo: 'Benchmark repo',
    analyzingRepo: 'Analyzing repository...',
    addToResume: 'Add to resume',
    addedToResume: 'Added',
    selectedProjects: 'Selected projects',
    structure: 'Key files',
    topics: 'Topics',
  },
  zh: {
    title: '仓库',
    searchPlaceholder: '搜索仓库...',
    stars: '星标',
    forks: 'Forks',
    updated: '最近更新',
    noDescription: '暂无描述',
    loading: '加载中...',
    error: '加载仓库失败',
    noUser: '输入 GitHub 用户名查看仓库',
    visibleRepos: '当前显示仓库',
    featuredView: '精选',
    activeView: '最近活跃',
    maintainedView: '资料完整',
    readyBadge: '完善',
    readmeBadge: 'README',
    licenseBadge: '许可证',
    lastPush: '最近推送',
    emptyResults: '当前视图下没有匹配仓库。',
    analyzeRepo: '分析到简历',
    analyzingRepo: '正在分析仓库...',
    addToResume: '加入简历',
    addedToResume: '已加入',
    selectedProjects: '已选项目',
    structure: '关键文件',
    topics: 'Topics',
  },
} as const

const langColors: Record<string, string> = {
  JavaScript: '#f1e05a',
  TypeScript: '#3178c6',
  Python: '#3572A5',
  Java: '#b07219',
  Go: '#00ADD8',
  Rust: '#dea584',
  'C++': '#f34b7d',
  C: '#555555',
  'C#': '#178600',
  Ruby: '#701516',
  PHP: '#4F5D95',
  Swift: '#ffac45',
  Kotlin: '#A97BFF',
}

function pushedAtTime(value: string | undefined): number {
  if (!value?.trim()) return 0
  const t = Date.parse(value.length <= 10 ? `${value}T00:00:00Z` : value)
  return Number.isFinite(t) ? t : 0
}

function formatDate(value: string | undefined, language: 'en' | 'zh'): string {
  if (!value) return '-'
  const date = new Date(value.length <= 10 ? `${value}T00:00:00Z` : value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(language === 'zh' ? 'zh-CN' : 'en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function Repositories({ language }: RepositoriesProps) {
  const {
    contentLanguage,
    getGenerateCache,
    cacheGenerateResult,
    getResumeProjects,
    toggleResumeProject,
  } = useApp()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const username = searchParams.get('user') || ''
  const targetRepo = searchParams.get('repo') || ''
  const [repos, setRepos] = useState<Repo[]>([])
  const [userData, setUserData] = useState<UserData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<SortMode>('stars')
  const [viewMode, setViewMode] = useState<RepoViewMode>('featured')
  const [expandedRepo, setExpandedRepo] = useState<string | null>(null)
  const [analysisLoadingRepo, setAnalysisLoadingRepo] = useState<string | null>(null)
  const [repoAnalysisMap, setRepoAnalysisMap] = useState<Record<string, RepositoryAnalysisPayload>>({})
  const text = labels[language]
  const selectedProjects = getResumeProjects(username)

  useEffect(() => {
    if (!username) return

    const cachedEntry = getGenerateCache(username, contentLanguage)
    if (cachedEntry) {
      const user = cachedEntry.data.user
      setUserData(user as UserData)
      setRepos(user.repositories as Repo[])
      setLoading(false)
      setError('')
      return
    }

    let cancelled = false
    const abortController = new AbortController()

    const fetchData = async () => {
      setLoading(true)
      setError('')
      setUserData(null)
      setRepos([])
      try {
        const response = await axios.post(
          `${API_BASE_URL}/api/generate`,
          {
            username,
            language: contentLanguage,
          },
          { signal: abortController.signal },
        )
        if (cancelled) return
        cacheGenerateResult({
          username: response.data.user.username,
          contentLanguage,
          data: response.data,
        })
        setUserData(response.data.user)
        setRepos(response.data.user.repositories)
      } catch (err) {
        if (isRequestAborted(err) || cancelled) return
        setError(text.error)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void fetchData()
    return () => {
      cancelled = true
      abortController.abort()
    }
  }, [username, contentLanguage, getGenerateCache, cacheGenerateResult, text.error])

  const filteredRepos = useMemo(() => {
    const normalizedTerm = searchTerm.trim().toLowerCase()
    return repos
      .filter((repo) => {
        if (!normalizedTerm) return true
        return (
          repo.name.toLowerCase().includes(normalizedTerm) ||
          repo.description.toLowerCase().includes(normalizedTerm) ||
          repo.language.toLowerCase().includes(normalizedTerm) ||
          (repo.topics ?? []).some((topic) => topic.toLowerCase().includes(normalizedTerm))
        )
      })
      .filter((repo) => {
        if (viewMode === 'active') return pushedAtTime(repo.pushed_at) > 0
        if (viewMode === 'maintained') return Boolean(repo.has_readme || repo.has_license)
        return true
      })
      .sort((a, b) => {
        if (viewMode === 'featured') {
          const featuredDelta = b.stars + b.forks - (a.stars + a.forks)
          if (featuredDelta !== 0) return featuredDelta
        }
        if (viewMode === 'active') {
          const activeDelta = pushedAtTime(b.pushed_at) - pushedAtTime(a.pushed_at)
          if (activeDelta !== 0) return activeDelta
        }
        if (sortBy === 'forks') return b.forks - a.forks
        if (sortBy === 'updated') return pushedAtTime(b.pushed_at) - pushedAtTime(a.pushed_at)
        return b.stars - a.stars
      })
  }, [repos, searchTerm, sortBy, viewMode])

  const formatCompactNumber = (value: number) => {
    if (value >= 1000) return `${(value / 1000).toFixed(1)}k`
    return value.toString()
  }

  const makeResumeProject = (repo: Repo, payload?: RepositoryAnalysisPayload): ResumeProject =>
    payload
      ? buildResumeProjectFromAnalysis(username, repo, payload)
      : buildResumeProject(username, repo, language)

  const analyzeRepo = async (repo: Repo) => {
    if (repoAnalysisMap[repo.name]) {
      setExpandedRepo((current) => (current === repo.name ? null : repo.name))
      return
    }

    setExpandedRepo(repo.name)
    setAnalysisLoadingRepo(repo.name)
    try {
      const response = await axios.post<RepositoryAnalysisPayload>(`${API_BASE_URL}/api/repository/analyze`, {
        username,
        repo_name: repo.name,
        language: contentLanguage,
      })
      setRepoAnalysisMap((prev) => ({ ...prev, [repo.name]: response.data }))
    } catch {
      const fallback = buildResumeProject(username, repo, language)
      setRepoAnalysisMap((prev) => ({
        ...prev,
        [repo.name]: {
          repository: repo,
          analysis: {
            repo_name: repo.name,
            title: fallback.analysisTitle,
            summary: fallback.analysisSummary,
            highlights: fallback.highlights,
            keywords: fallback.keywords,
          },
        },
      }))
    } finally {
      setAnalysisLoadingRepo(null)
    }
  }

  useEffect(() => {
    if (!targetRepo || repos.length === 0 || analysisLoadingRepo) return
    const matchedRepo = repos.find((repo) => repo.name.toLowerCase() === targetRepo.trim().toLowerCase())
    if (!matchedRepo) return
    if (expandedRepo === matchedRepo.name || repoAnalysisMap[matchedRepo.name]) {
      setExpandedRepo(matchedRepo.name)
      return
    }
    void analyzeRepo(matchedRepo)
  }, [targetRepo, repos, repoAnalysisMap, expandedRepo, analysisLoadingRepo])

  if (!username) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <p>{text.noUser}</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading-state">
          <p>{text.loading}</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="error-state">
          <p>{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">{text.title}</h1>
          <p className="page-subtitle">
            {text.visibleRepos}: {filteredRepos.length}
          </p>
        </div>
        {userData && (
          <div className="user-header">
            <img src={userData.avatar_url} alt={userData.username} className="header-avatar" />
            <span className="header-username">@{userData.username}</span>
          </div>
        )}
      </div>

      <div className="repo-view-switcher">
        <button type="button" className={`repo-view-chip ${viewMode === 'featured' ? 'active' : ''}`} onClick={() => setViewMode('featured')}>
          {text.featuredView}
        </button>
        <button type="button" className={`repo-view-chip ${viewMode === 'active' ? 'active' : ''}`} onClick={() => setViewMode('active')}>
          {text.activeView}
        </button>
        <button type="button" className={`repo-view-chip ${viewMode === 'maintained' ? 'active' : ''}`} onClick={() => setViewMode('maintained')}>
          {text.maintainedView}
        </button>
      </div>

      <div className="filter-bar">
        <input
          type="text"
          placeholder={text.searchPlaceholder}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as SortMode)}
          className="sort-select"
        >
          <option value="stars">{text.stars}</option>
          <option value="updated">{text.updated}</option>
          <option value="forks">{text.forks}</option>
        </select>
      </div>

      {filteredRepos.length === 0 ? (
        <div className="empty-state">
          <p>{text.emptyResults}</p>
        </div>
      ) : (
        <div className="repo-grid">
          {filteredRepos.map((repo) => {
            const metadataReady = Boolean(repo.has_readme && repo.has_license)
            const repoAnalysis = repoAnalysisMap[repo.name]
            const project = makeResumeProject(repo, repoAnalysis)
            const isSelected = selectedProjects.some((item) => item.repoName === repo.name)

            return (
              <a key={repo.url} href={repo.url} target="_blank" rel="noreferrer" className="repo-card">
                <div className="repo-card-header">
                  <h3 className="repo-card-name">{repo.name}</h3>
                  {repo.language && (
                    <span className="repo-card-lang" style={{ color: langColors[repo.language] || '#8b949e' }}>
                      <span className="lang-dot" style={{ backgroundColor: langColors[repo.language] || '#8b949e' }} />
                      {repo.language}
                    </span>
                  )}
                </div>

                <p className="repo-card-desc">{repo.description || text.noDescription}</p>

                <div className="repo-card-meta">
                  {metadataReady && <span className="repo-badge repo-badge-ready">{text.readyBadge}</span>}
                  {repo.has_readme && <span className="repo-badge">{text.readmeBadge}</span>}
                  {repo.has_license && <span className="repo-badge">{text.licenseBadge}</span>}
                </div>

                <div className="repo-card-stats">
                  <span className="repo-stat">
                    <svg className="stat-icon" viewBox="0 0 24 24" fill="currentColor">
                      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                    </svg>
                    {formatCompactNumber(repo.stars)}
                  </span>
                  <span className="repo-stat">
                    <svg className="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="18" r="3" />
                      <circle cx="6" cy="6" r="3" />
                      <circle cx="18" cy="6" r="3" />
                      <path d="M6 9v3a3 3 0 0 0 3 3h6a3 3 0 0 0 3-3V9" />
                      <path d="M12 15V9" />
                    </svg>
                    {formatCompactNumber(repo.forks)}
                  </span>
                </div>

                <div className="repo-card-footer">
                  <span className="repo-card-updated">
                    {text.lastPush}: {formatDate(repo.pushed_at, language)}
                  </span>
                </div>

                <div className="repo-card-actions">
                  <button
                    type="button"
                    className="repo-action-btn"
                    onClick={(e) => {
                      e.preventDefault()
                      void analyzeRepo(repo)
                    }}
                  >
                    {analysisLoadingRepo === repo.name ? text.analyzingRepo : text.analyzeRepo}
                  </button>
                  <button
                    type="button"
                    className="repo-action-btn"
                    onClick={(e) => {
                      e.preventDefault()
                      navigate(`/compare/repos?mine=${encodeURIComponent(`${username}/${repo.name}`)}`)
                    }}
                  >
                    {language === 'zh' ? '去做对标' : ((text as typeof labels.en).benchmarkRepo ?? 'Benchmark repo')}
                  </button>
                  <button
                    type="button"
                    className={`repo-action-btn ${isSelected ? 'active' : ''}`}
                    onClick={(e) => {
                      e.preventDefault()
                      toggleResumeProject(project)
                    }}
                  >
                    {isSelected ? text.addedToResume : text.addToResume}
                  </button>
                </div>

                {expandedRepo === repo.name && (
                  <div className="repo-analysis-panel">
                    <strong>{project.analysisTitle}</strong>
                    <p>{project.analysisSummary}</p>
                    <ul className="repo-analysis-list">
                      {project.highlights.map((highlight: string) => (
                        <li key={highlight}>{highlight}</li>
                      ))}
                    </ul>
                    {project.keywords.length > 0 && (
                      <div className="resume-project-highlights">
                        {project.keywords.map((keyword: string) => (
                          <span key={keyword} className="repo-badge">{keyword}</span>
                        ))}
                      </div>
                    )}
                    {repo.topics && repo.topics.length > 0 && (
                      <div className="repo-file-tree">
                        <span className="topbar-search-suggestions-label">{text.topics}</span>
                        <p>{repo.topics.slice(0, 8).join(' · ')}</p>
                      </div>
                    )}
                    {repo.file_tree && repo.file_tree.length > 0 && (
                      <div className="repo-file-tree">
                        <span className="topbar-search-suggestions-label">{text.structure}</span>
                        <p>{repo.file_tree.slice(0, 10).join(' · ')}</p>
                      </div>
                    )}
                  </div>
                )}
              </a>
            )
          })}
        </div>
      )}

      {selectedProjects.length > 0 && (
        <section className="selected-projects-panel">
          <div className="section-header">
            <h2 className="section-title">
              {text.selectedProjects}: {selectedProjects.length}/4
            </h2>
          </div>
          <div className="selected-projects-grid">
            {selectedProjects.map((project) => (
              <article key={project.repoName} className="selected-project-card">
                <div className="selected-project-header">
                  <strong>{project.repoName}</strong>
                  <span>{project.language || 'Code'}</span>
                </div>
                <p>{project.analysisSummary}</p>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
