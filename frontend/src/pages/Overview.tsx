import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useApp } from '../context'
import type { GenerateResponse } from '../types/generate'
import {
  buildResumeProject,
  buildResumeProjectFromAnalysis,
  type RepositoryAnalysisPayload,
} from '../utils/resumeProjects'

interface HistoryItem {
  id: string
  username: string
  avatarUrl: string
  gitscore: number
  timestamp: number
  language: 'en' | 'zh'
}

interface OverviewProps {
  language: 'en' | 'zh'
}

type RepositoryItem = GenerateResponse['user']['repositories'][number]

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const labels = {
  en: {
    title: 'Overview',
    heroBadge: 'Repo Resume Workflow',
    heroTitle: 'Turn GitHub repositories into resume-ready project stories',
    heroBody:
      'Analyze a developer, inspect repository content, let AI summarize the strongest projects, and curate the final selection for resume export.',
    heroPrimary: 'Start Picking Repositories',
    heroSecondary: 'Open Resume Export',
    workflowTitle: 'How it works',
    workflowStepOne: 'Analyze a GitHub user or open an existing workspace',
    workflowStepTwo: 'Review repositories with README, topics, and file structure signals',
    workflowStepThree: 'Run AI repo analysis, then pin the best projects into the resume',
    candidateTitle: 'Best candidates right now',
    candidateSubtitle: 'These repositories already look promising for resume use.',
    candidateAction: 'Review in Repositories',
    analyzeRepo: 'Analyze with AI',
    analyzingRepo: 'Analyzing...',
    addToResume: 'Add to resume',
    addedToResume: 'Added',
    candidateEmpty: 'Analyze a user first and Codefolio will surface repository candidates here.',
    currentStateTitle: 'Current workspace',
    stateReady: 'Ready to curate',
    stateIdle: 'Waiting for a GitHub user',
    projectCountLabel: 'Projects selected',
    candidateCountLabel: 'Promising repos',
    lastUserLabel: 'Active profile',
    history: 'Recent History',
    emptyHistory: 'No history yet. Search for a GitHub user to get started.',
    clearHistory: 'Clear All',
    deleteItem: 'Remove',
    refreshCache: 'Refresh Cache',
    cacheCleared: 'Cache refreshed',
    cacheClearFailed: 'Failed to refresh cache',
    removedFromHistory: 'Removed from history',
    viewedAt: 'Viewed',
    totalAnalyzed: 'Users Analyzed',
    avgScore: 'Average Score',
    topLanguage: 'Resume Projects',
    repos: 'Repositories',
    aiAnalysis: 'AI Analysis',
    addToCompare: 'Compare',
    added: 'Added',
    resumeHub: 'Resume Builder',
    resumeSubtitle: 'Pick standout repositories, review their resume value, and send them into export.',
    selectedProjects: 'Selected projects',
    openRepos: 'Pick Repositories',
    openExport: 'Open Resume Export',
    currentUser: 'Current user',
    noActiveUser: 'Analyze a GitHub user first to start selecting repositories for the resume.',
    noProjects: 'No repositories pinned yet. Head to Repositories and start curating your best work.',
    suggestedProjects: 'Suggested repos to review',
    noDescription: 'No description provided.',
    structureReady: 'Structure ready',
  },
  zh: {
    title: '总览',
    heroBadge: '仓库简历工作流',
    heroTitle: '把 GitHub 仓库变成可以写进简历的代表项目',
    heroBody:
      '先分析 GitHub 用户，再结合 README、topics、关键文件结构和 AI 分析，挑出最适合写进简历的仓库。',
    heroPrimary: '开始挑仓库',
    heroSecondary: '打开简历导出',
    workflowTitle: '使用流程',
    workflowStepOne: '先分析一个 GitHub 用户，或打开已有工作区',
    workflowStepTwo: '查看仓库的 README、topics 和关键文件结构信号',
    workflowStepThree: '运行 AI 仓库分析，把最值得写进简历的项目加入工作台',
    candidateTitle: '当前最值得看的仓库',
    candidateSubtitle: '这些仓库已经有比较好的简历候选特征。',
    candidateAction: '去仓库页查看',
    analyzeRepo: 'AI 分析',
    analyzingRepo: '分析中...',
    addToResume: '加入简历',
    addedToResume: '已加入',
    candidateEmpty: '先分析一个 GitHub 用户，这里会自动推荐可以写进简历的仓库。',
    currentStateTitle: '当前工作区',
    stateReady: '可以开始挑选项目',
    stateIdle: '等待分析 GitHub 用户',
    projectCountLabel: '已选项目',
    candidateCountLabel: '值得先看的仓库',
    lastUserLabel: '当前 Profile',
    history: '最近历史',
    emptyHistory: '暂无历史记录。搜索 GitHub 用户开始使用。',
    clearHistory: '清空全部',
    deleteItem: '移出历史',
    refreshCache: '刷新缓存',
    cacheCleared: '缓存已刷新',
    cacheClearFailed: '刷新缓存失败',
    removedFromHistory: '已从历史移除',
    viewedAt: '查看于',
    totalAnalyzed: '已分析用户',
    avgScore: '平均分数',
    topLanguage: '简历项目',
    repos: '仓库',
    aiAnalysis: 'AI 分析',
    addToCompare: '对比',
    added: '已添加',
    resumeHub: '简历项目工作台',
    resumeSubtitle: '挑选代表仓库，先看简历价值，再带去导出页做最终简历。',
    selectedProjects: '已选项目',
    openRepos: '去挑仓库',
    openExport: '打开简历导出',
    currentUser: '当前用户',
    noActiveUser: '先分析一个 GitHub 用户，再开始挑选适合进简历的项目。',
    noProjects: '还没有加入简历的仓库，先去仓库页挑几个代表项目。',
    suggestedProjects: '建议先看的仓库',
    noDescription: '暂无描述',
    structureReady: '结构信息已就绪',
  },
} as const

function readHistoryItems(): HistoryItem[] {
  const saved = localStorage.getItem('codefolio-history')
  if (!saved) return []

  try {
    return JSON.parse(saved) as HistoryItem[]
  } catch {
    return []
  }
}

function getRepositoryResumeScore(repo: RepositoryItem): number {
  const community = repo.stars * 2 + repo.forks
  const docs = (repo.has_readme ? 24 : 0) + (repo.has_license ? 10 : 0)
  const topics = (repo.topics?.length ?? 0) * 4
  const structure = Math.min((repo.file_tree?.length ?? 0) * 2, 24)
  const description = repo.description ? 12 : 0
  return community + docs + topics + structure + description
}

export function getCandidateSignals(repo: RepositoryItem, language: 'en' | 'zh'): string[] {
  const signals: string[] = []

  if (repo.has_readme) signals.push(language === 'zh' ? 'README 完整' : 'README ready')
  if ((repo.topics?.length ?? 0) >= 2) signals.push(language === 'zh' ? '方向清晰' : 'Clear positioning')
  if ((repo.file_tree?.length ?? 0) >= 4) signals.push(language === 'zh' ? '结构清晰' : 'Structured repo')
  if (repo.stars + repo.forks >= 5) signals.push(language === 'zh' ? '有外部反馈' : 'Community proof')

  if (!signals.length) {
    signals.push(language === 'zh' ? '适合补充项目经历' : 'Useful project evidence')
  }

  return signals.slice(0, 3)
}

export function Overview({ language }: OverviewProps) {
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [addedUsers, setAddedUsers] = useState<Set<string>>(new Set())
  const [feedback, setFeedback] = useState('')
  const [candidateAnalysisMap, setCandidateAnalysisMap] = useState<Record<string, RepositoryAnalysisPayload>>({})
  const [candidateLoadingRepo, setCandidateLoadingRepo] = useState<string | null>(null)
  const [expandedCandidateRepo, setExpandedCandidateRepo] = useState<string | null>(null)
  const {
    addToCompare,
    compareList,
    currentUser,
    setCurrentUser,
    clearGenerateCacheForUser,
    getGenerateCache,
    getResumeProjects,
    toggleResumeProject,
  } = useApp()
  const navigate = useNavigate()
  const text = labels[language]

  useEffect(() => {
    setHistory(readHistoryItems())
  }, [])

  useEffect(() => {
    setAddedUsers(new Set(compareList))
  }, [compareList])

  const writeHistory = (items: HistoryItem[]) => {
    localStorage.setItem('codefolio-history', JSON.stringify(items))
    setHistory(items)
  }

  const clearHistory = () => {
    localStorage.removeItem('codefolio-history')
    setHistory([])
    setFeedback('')
  }

  const deleteHistoryItem = (item: HistoryItem) => {
    const updated = readHistoryItems().filter((historyItem) => historyItem.id !== item.id)
    writeHistory(updated)
    setFeedback(text.removedFromHistory)
  }

  const refreshUserCache = async (username: string) => {
    try {
      await axios.delete(`${API_BASE_URL}/api/cache/${username}`)
      clearGenerateCacheForUser(username)
      setFeedback(text.cacheCleared)
    } catch {
      setFeedback(text.cacheClearFailed)
    }
  }

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp)
    return date.toLocaleDateString(language === 'zh' ? 'zh-CN' : 'en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const handleAddToCompare = (username: string) => {
    addToCompare(username)
    navigate(`/compare?users=${[...compareList, username].join(',')}`)
  }

  const handleOpenAnalysis = (username: string) => {
    setCurrentUser(username)
    navigate(`/analysis?user=${encodeURIComponent(username)}`)
  }

  const handleOpenRepos = (username: string) => {
    setCurrentUser(username)
    navigate(`/repositories?user=${encodeURIComponent(username)}`)
  }

  const avgScore =
    history.length > 0
      ? Math.round(history.reduce((sum, item) => sum + item.gitscore, 0) / history.length)
      : 0

  const selectedProjects = currentUser ? getResumeProjects(currentUser) : []
  const cachedCurrentUser = currentUser ? getGenerateCache(currentUser, language) : null
  const currentRepositories: RepositoryItem[] = cachedCurrentUser?.data?.user?.repositories ?? []
  const suggestedRepos = useMemo(() => {
    if (!currentRepositories.length) return []
    return [...currentRepositories]
      .sort((a, b) => getRepositoryResumeScore(b) - getRepositoryResumeScore(a))
      .slice(0, 4)
  }, [currentRepositories])

  const lastHistoryUser = history[0]?.username ?? ''
  const workspaceState = currentUser ? text.stateReady : text.stateIdle
  const launchUser = currentUser || lastHistoryUser

  const analyzeCandidateRepo = async (repo: RepositoryItem) => {
    if (!currentUser) return

    if (candidateAnalysisMap[repo.name]) {
      setExpandedCandidateRepo((current) => (current === repo.name ? null : repo.name))
      return
    }

    setExpandedCandidateRepo(repo.name)
    setCandidateLoadingRepo(repo.name)
    try {
      const response = await axios.post<RepositoryAnalysisPayload>(`${API_BASE_URL}/api/repository/analyze`, {
        username: currentUser,
        repo_name: repo.name,
        language,
      })
      setCandidateAnalysisMap((prev) => ({ ...prev, [repo.name]: response.data }))
    } catch {
      const fallback = buildResumeProject(currentUser, repo, language)
      setCandidateAnalysisMap((prev) => ({
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
      setCandidateLoadingRepo(null)
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">{text.title}</h1>
      </div>

      <section className="overview-hero">
        <div className="overview-hero-copy">
          <span className="resume-builder-kicker">{text.heroBadge}</span>
          <h2 className="overview-hero-title">{text.heroTitle}</h2>
          <p className="overview-hero-body">{text.heroBody}</p>
          <div className="overview-hero-actions">
            <button
              type="button"
              className="hero-action-btn hero-action-btn-primary"
              onClick={() => {
                if (launchUser) handleOpenRepos(launchUser)
              }}
              disabled={!launchUser}
            >
              {text.heroPrimary}
            </button>
            <button
              type="button"
              className="hero-action-btn"
              onClick={() => {
                if (currentUser) navigate(`/export?user=${encodeURIComponent(currentUser)}`)
              }}
              disabled={!currentUser}
            >
              {text.heroSecondary}
            </button>
          </div>
        </div>

        <div className="overview-hero-panel">
          <div className="overview-hero-state">
            <span className="topbar-search-suggestions-label">{text.currentStateTitle}</span>
            <strong>{workspaceState}</strong>
            <p>
              {text.lastUserLabel}: {launchUser ? `@${launchUser}` : '-'}
            </p>
          </div>

          <div className="overview-state-grid">
            <article className="overview-state-card">
              <span>{text.projectCountLabel}</span>
              <strong>{selectedProjects.length}</strong>
            </article>
            <article className="overview-state-card">
              <span>{text.candidateCountLabel}</span>
              <strong>{suggestedRepos.length}</strong>
            </article>
          </div>

          <div className="overview-workflow">
            <span className="topbar-search-suggestions-label">{text.workflowTitle}</span>
            <ol className="overview-workflow-list">
              <li>{text.workflowStepOne}</li>
              <li>{text.workflowStepTwo}</li>
              <li>{text.workflowStepThree}</li>
            </ol>
          </div>
        </div>
      </section>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-value">{history.length}</span>
          <span className="stat-label">{text.totalAnalyzed}</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{avgScore}</span>
          <span className="stat-label">{text.avgScore}</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{selectedProjects.length}</span>
          <span className="stat-label">{text.topLanguage}</span>
        </div>
      </div>

      <section className="overview-candidates-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">{text.candidateTitle}</h2>
            <p className="page-subtitle">{text.candidateSubtitle}</p>
          </div>
          {currentUser && (
            <button className="history-action-btn" onClick={() => handleOpenRepos(currentUser)}>
              {text.candidateAction}
            </button>
          )}
        </div>

        {suggestedRepos.length > 0 ? (
          <div className="overview-candidate-grid">
            {suggestedRepos.map((repo) => (
              <article key={repo.url} className="overview-candidate-card">
                <div className="overview-candidate-top">
                  <strong>{repo.name}</strong>
                  <span>{repo.language || 'Code'}</span>
                </div>
                <p>{repo.description || text.noDescription}</p>
                <div className="resume-project-highlights">
                  {repo.has_readme && <span className="repo-badge">README</span>}
                  {repo.has_license && <span className="repo-badge">License</span>}
                  {(repo.topics ?? []).slice(0, 3).map((topic) => (
                    <span key={topic} className="repo-badge">
                      {topic}
                    </span>
                  ))}
                </div>
                <div className="overview-candidate-meta">
                  <span>{repo.stars} stars</span>
                  <span>{repo.forks} forks</span>
                  <span>{repo.file_tree?.slice(0, 2).join(' · ') || text.structureReady}</span>
                </div>
                <div className="overview-candidate-actions">
                  <button
                    type="button"
                    className="repo-action-btn"
                    onClick={() => void analyzeCandidateRepo(repo)}
                    disabled={!currentUser}
                  >
                    {candidateLoadingRepo === repo.name ? text.analyzingRepo : text.analyzeRepo}
                  </button>
                  <button
                    type="button"
                    className={`repo-action-btn ${
                      selectedProjects.some((item) => item.repoName === repo.name) ? 'active' : ''
                    }`}
                    onClick={() => {
                      const payload = candidateAnalysisMap[repo.name]
                      const project = payload
                        ? buildResumeProjectFromAnalysis(currentUser, repo, payload)
                        : buildResumeProject(currentUser, repo, language)
                      toggleResumeProject(project)
                    }}
                    disabled={!currentUser}
                  >
                    {selectedProjects.some((item) => item.repoName === repo.name)
                      ? text.addedToResume
                      : text.addToResume}
                  </button>
                </div>
                {expandedCandidateRepo === repo.name && (
                  <div className="overview-candidate-analysis">
                    {(() => {
                      const payload = candidateAnalysisMap[repo.name]
                      const project = payload
                        ? buildResumeProjectFromAnalysis(currentUser, repo, payload)
                        : buildResumeProject(currentUser, repo, language)
                      return (
                        <>
                          <strong>{project.analysisTitle}</strong>
                          <p>{project.analysisSummary}</p>
                          <ul className="repo-analysis-list">
                            {project.highlights.map((highlight) => (
                              <li key={highlight}>{highlight}</li>
                            ))}
                          </ul>
                          {project.keywords.length > 0 && (
                            <div className="resume-project-highlights">
                              {project.keywords.map((keyword) => (
                                <span key={keyword} className="repo-badge">
                                  {keyword}
                                </span>
                              ))}
                            </div>
                          )}
                        </>
                      )
                    })()}
                  </div>
                )}
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state compact">
            <p>{text.candidateEmpty}</p>
          </div>
        )}
      </section>

      <section className="resume-builder-panel">
        <div className="resume-builder-header">
          <div>
            <span className="resume-builder-kicker">{text.currentUser}</span>
            <h2 className="section-title">
              {text.resumeHub}
              {currentUser ? ` · @${currentUser}` : ''}
            </h2>
            <p className="page-subtitle">{currentUser ? text.resumeSubtitle : text.noActiveUser}</p>
          </div>
          <div className="resume-builder-actions">
            {currentUser && (
              <>
                <button className="history-action-btn" onClick={() => handleOpenRepos(currentUser)}>
                  {text.openRepos}
                </button>
                <button
                  className="history-action-btn added"
                  onClick={() => navigate(`/export?user=${encodeURIComponent(currentUser)}`)}
                >
                  {text.openExport}
                </button>
              </>
            )}
          </div>
        </div>

        {currentUser && selectedProjects.length > 0 ? (
          <div className="resume-project-grid">
            {selectedProjects.map((project) => (
              <article key={project.repoName} className="resume-project-card">
                <div className="resume-project-top">
                  <strong>{project.repoName}</strong>
                  <span>{project.language || 'Code'}</span>
                </div>
                <p>{project.analysisSummary}</p>
                <div className="resume-project-highlights">
                  {project.highlights.slice(0, 2).map((highlight) => (
                    <span key={highlight} className="repo-badge">
                      {highlight}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state compact">
            <p>{currentUser ? text.noProjects : text.noActiveUser}</p>
          </div>
        )}

        {currentUser && suggestedRepos.length > 0 && (
          <div className="resume-suggested-strip">
            <span className="topbar-search-suggestions-label">{text.suggestedProjects}</span>
            <div className="topbar-search-suggestions-list">
              {suggestedRepos.map((repo) => (
                <button
                  key={repo.url}
                  type="button"
                  className="topbar-search-suggestion"
                  onClick={() => navigate(`/repositories?user=${encodeURIComponent(currentUser)}`)}
                >
                  <span>{repo.name}</span>
                  <span>{repo.language || 'Code'}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      <div className="history-section">
        <div className="section-header">
          <h2 className="section-title">{text.history}</h2>
          {history.length > 0 && (
            <button className="clear-btn" onClick={clearHistory}>
              {text.clearHistory}
            </button>
          )}
        </div>

        {feedback && (
          <div className="history-feedback" role="status">
            <p>{feedback}</p>
          </div>
        )}

        {history.length === 0 ? (
          <div className="empty-state">
            <p>{text.emptyHistory}</p>
          </div>
        ) : (
          <div className="history-list">
            {history.map((item) => (
              <div key={item.id} className="history-item-with-actions">
                <div
                  className="history-item-main"
                  onClick={() => handleOpenAnalysis(item.username)}
                  style={{ cursor: 'pointer' }}
                >
                  <img src={item.avatarUrl} alt={item.username} className="history-avatar" />
                  <div className="history-info">
                    <span className="history-username">@{item.username}</span>
                    <span className="history-time">
                      {text.viewedAt} {formatTime(item.timestamp)}
                    </span>
                  </div>
                  <div className="history-score">
                    <span className="score-badge">{item.gitscore}</span>
                  </div>
                </div>

                <div className="history-actions">
                  <button
                    className="history-action-btn"
                    onClick={() => handleOpenRepos(item.username)}
                    title={text.repos}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M4 20V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v15" />
                      <path d="M12 10v6" />
                    </svg>
                    <span>{text.repos}</span>
                  </button>

                  <button
                    className="history-action-btn"
                    onClick={() => handleOpenAnalysis(item.username)}
                    title={text.aiAnalysis}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 2a10 10 0 1 0 10 10H12V2z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                    <span>{text.aiAnalysis}</span>
                  </button>

                  <button
                    className={`history-action-btn ${addedUsers.has(item.username) ? 'added' : ''}`}
                    onClick={() => handleAddToCompare(item.username)}
                    disabled={addedUsers.has(item.username) || compareList.length >= 3}
                    title={text.addToCompare}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 5v14M5 12h14" />
                    </svg>
                    <span>{addedUsers.has(item.username) ? text.added : text.addToCompare}</span>
                  </button>

                  <button
                    className="history-action-btn"
                    onClick={() => void refreshUserCache(item.username)}
                    title={text.refreshCache}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 12a9 9 0 1 1-2.64-6.36" />
                      <polyline points="21 3 21 9 15 9" />
                    </svg>
                    <span>{text.refreshCache}</span>
                  </button>

                  <button
                    className="history-action-btn delete-btn"
                    onClick={() => deleteHistoryItem(item)}
                    title={text.deleteItem}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                    <span>{text.deleteItem}</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
