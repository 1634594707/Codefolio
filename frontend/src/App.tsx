import axios from 'axios'
import { FormEvent, Suspense, lazy, useEffect, useLayoutEffect, useRef, useState } from 'react'
import {
  Link,
  Navigate,
  Route,
  BrowserRouter as Router,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router-dom'
import { AppProvider, useApp } from './context'
import { ProgressIndicator, type ProgressStep } from './ProgressIndicator'
import { SkeletonScreen } from './SkeletonScreen'
import type { GenerateResponse } from './types/generate'
import { isRequestAborted } from './utils/axiosAbort'
import { normalizeGitHubUsernameInput, parseGitHubInput, validateGitHubUsername } from './utils/githubInput'

const Overview = lazy(() => import('./pages/Overview').then((module) => ({ default: module.Overview })))
const Repositories = lazy(() =>
  import('./pages/Repositories').then((module) => ({ default: module.Repositories })),
)
const AIAnalysis = lazy(() => import('./pages/AIAnalysis').then((module) => ({ default: module.AIAnalysis })))
const Export = lazy(() => import('./pages/Export').then((module) => ({ default: module.Export })))
const Compare = lazy(() => import('./pages/Compare').then((module) => ({ default: module.Compare })))
const CompareRepos = lazy(() =>
  import('./pages/CompareRepos').then((module) => ({ default: module.CompareRepos })),
)

type Language = 'en' | 'zh'
type Theme = 'light' | 'dark'

type ValidationState = 'idle' | 'valid' | 'invalid' | 'checking'

interface HistoryItem {
  id: string
  username: string
  avatarUrl: string
  gitscore: number
  timestamp: number
  language: Language
}

function readHistoryItems(): HistoryItem[] {
  if (typeof window === 'undefined') return []
  const saved = localStorage.getItem('codefolio-history')
  if (!saved) return []

  try {
    return JSON.parse(saved) as HistoryItem[]
  } catch {
    return []
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const labels = {
  en: {
    brand: 'Codefolio',
    eyebrow: 'GitHub repo-to-resume studio',
    navOverview: 'Overview',
    navRepositories: 'Repositories',
    navInsights: 'AI Analysis',
    navExport: 'Export',
    navCompare: 'Compare',
    navBenchmark: 'Benchmark Repos',
    workspaceSynced: 'Workspace Synced',
    placeholder: 'Paste @username, profile URL, or repo URL...',
    generate: 'Analyze',
    generating: 'Analyzing...',
    uiLang: 'Language',
    theme: 'Theme',
    themeLight: 'Light',
    themeDark: 'Dark',
    dashboard: 'Resume Workspace',
    settings: 'Settings',
    search: 'Search',
    errorFallback: 'Something went wrong.',
    errorRetry: 'Try again',
    errorDismiss: 'Dismiss',
    errorNetwork: 'Network error. Check your connection and API base URL.',
    validationInvalid: 'Use letters, numbers, or hyphens only (GitHub username rules).',
    inputHintUser: 'Will analyze GitHub user',
    inputHintRepo: 'Will jump to repository and expand analysis',
    inputHintInvalid: 'Input is not a valid GitHub username or repository URL.',
    quickActionRepo: 'Open target repo',
    progressFetching: 'Fetching GitHub data...',
    progressScoring: 'Calculating score...',
    progressPolishing: 'Generating insights...',
    progressTimeRemaining: 'Estimated time remaining',
    recentSearches: 'Recent',
    useSuggestion: 'Open',
  },
  zh: {
    brand: 'Codefolio',
    eyebrow: 'GitHub 作品集工作台',
    navOverview: '总览',
    navRepositories: '仓库',
    navInsights: 'AI 分析',
    navExport: '导出',
    navCompare: '对比',
    navBenchmark: '仓库对标',
    workspaceSynced: '工作区已同步',
    placeholder: '搜索 GitHub 用户名...',
    generate: '分析',
    generating: '分析中...',
    uiLang: '语言',
    theme: '主题',
    themeLight: '浅色',
    themeDark: '深色',
    dashboard: '仪表盘',
    settings: '设置',
    search: '搜索',
    errorFallback: '出现问题。',
    errorRetry: '重试',
    errorDismiss: '关闭',
    errorNetwork: '网络异常，请检查连接与接口地址。',
    validationInvalid: '用户名仅支持字母、数字与连字符（需符合 GitHub 规则）。',
    progressFetching: '正在抓取 GitHub 数据...',
    progressScoring: '正在计算评分...',
    progressPolishing: '正在生成洞察...',
    progressTimeRemaining: '预计剩余时间',
  },
} as const

const errorByCode = {
  en: {
    invalid_input: 'Invalid username or request.',
    invalid_username: 'Invalid username format.',
    user_not_found: 'This GitHub user was not found.',
    rate_limit_exceeded: 'Too many requests. Wait a moment and try again.',
    authentication_error: 'GitHub authentication failed (check server token).',
    timeout_error: 'The request timed out. Try again shortly.',
    api_error: 'GitHub API error. Try again later.',
    unknown_error: 'An unexpected error occurred.',
  },
  zh: {
    invalid_input: '用户名或请求无效。',
    invalid_username: '用户名格式无效。',
    user_not_found: '未找到该 GitHub 用户。',
    rate_limit_exceeded: '请求过于频繁，请稍后再试。',
    authentication_error: 'GitHub 鉴权失败（请检查服务端 Token）。',
    timeout_error: '请求超时，请稍后重试。',
    api_error: 'GitHub 接口异常，请稍后再试。',
    unknown_error: '发生未知错误。',
  },
} as const

function getAnalyzeErrorMessage(err: unknown, lang: Language): string {
  if (!axios.isAxiosError(err)) return labels[lang].errorFallback
  if (!err.response && (err.code === 'ERR_NETWORK' || err.message === 'Network Error')) {
    return labels[lang].errorNetwork
  }
  const raw = err.response?.data?.detail
  const obj = typeof raw === 'object' && raw !== null ? (raw as { code?: string; message?: string }) : undefined
  const serverMsg = typeof obj?.message === 'string' ? obj.message.trim() : ''
  if (serverMsg) return serverMsg
  const code = typeof obj?.code === 'string' ? obj.code : 'unknown_error'
  const bucket = errorByCode[lang] as Record<string, string>
  return bucket[code] ?? labels[lang].errorFallback
}

// Navigation icons as SVG components
const DashboardIcon = () => (
  <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="14" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" />
  </svg>
)

const RepoIcon = () => (
  <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M4 20V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v15" />
    <path d="M12 10v6" />
    <path d="M8 10v6" />
    <path d="M16 10v6" />
  </svg>
)

const AIIcon = () => (
  <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 2a10 10 0 1 0 10 10H12V2z" />
    <path d="M12 12L2.5 12" />
    <circle cx="12" cy="12" r="3" />
  </svg>
)

const ExportIcon = () => (
  <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
)

const CompareIcon = () => (
  <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 2v20M2 12h20M4 4l16 16M20 4L4 20" />
  </svg>
)

const BenchmarkIcon = () => (
  <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="12" width="4" height="9" rx="1" />
    <rect x="10" y="7" width="4" height="14" rx="1" />
    <rect x="17" y="3" width="4" height="18" rx="1" />
  </svg>
)

const SearchIcon = () => (
  <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="11" cy="11" r="8" />
    <path d="m21 21-4.35-4.35" />
  </svg>
)

const SettingsIcon = () => (
  <svg className="settings-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </svg>
)

function addToHistory(result: GenerateResponse, language: Language) {
  const activeOutput = result.localized_outputs[language]
  if (!activeOutput) return

  const newItem: HistoryItem = {
    id: `${result.user.username}-${Date.now()}`,
    username: result.user.username,
    avatarUrl: result.user.avatar_url,
    gitscore: activeOutput.card_data.gitscore,
    timestamp: Date.now(),
    language,
  }

  const saved = localStorage.getItem('codefolio-history')
  const history: HistoryItem[] = saved ? JSON.parse(saved) : []
  const filtered = history.filter((h) => h.username !== newItem.username)
  const updated = [newItem, ...filtered].slice(0, 20)
  localStorage.setItem('codefolio-history', JSON.stringify(updated))
}

function PageFallback({ language }: { language: Language }) {
  return (
    <div className="page-container">
      <div className="loading-state">
        <p>{language === 'zh' ? '页面加载中...' : 'Loading page...'}</p>
      </div>
    </div>
  )
}

// Layout component with router
function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const {
    currentUser,
    setCurrentUser,
    setLastResult,
    contentLanguage,
    setContentLanguage,
    cacheGenerateResult,
  } = useApp()
  const [theme, setTheme] = useState<Theme>('dark')
  const [language, setLanguage] = useState<Language>('en')
  const [username, setUsername] = useState('')
  const [validationState, setValidationState] = useState<ValidationState>('idle')
  const [validationIssue, setValidationIssue] = useState<'invalid' | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastFailedUsername, setLastFailedUsername] = useState<string | null>(null)
  const [currentStep, setCurrentStep] = useState<ProgressStep>('fetching')
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState(0)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [searchSuggestions, setSearchSuggestions] = useState<string[]>([])
  const [showSearchSuggestions, setShowSearchSuggestions] = useState(false)
  const settingsWrapRef = useRef<HTMLDivElement>(null)
  const searchWrapRef = useRef<HTMLFormElement>(null)
  const didRestoreTopbarUser = useRef(false)
  /** 防止多次「分析」并发：仅最后一次请求允许写入缓存、跳转与结束 loading */
  const generateRequestSeqRef = useRef(0)
  const generateAbortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const savedTheme = localStorage.getItem('codefolio-theme') as Theme | null
    const savedLanguage = localStorage.getItem('codefolio-language') as Language | null
    const initialTheme = savedTheme ?? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    const browserLanguage = navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en'
    const initialLanguage = savedLanguage ?? browserLanguage

    setTheme(initialTheme)
    setLanguage(initialLanguage)
    setContentLanguage(initialLanguage)
    setSearchSuggestions(readHistoryItems().map((item) => item.username))
    document.documentElement.classList.toggle('dark', initialTheme === 'dark')
  }, [])

  useLayoutEffect(() => {
    const userRoutes = ['/repositories', '/analysis', '/export']
    const onUserRoute = userRoutes.some((p) => location.pathname.startsWith(p))
    const fromUrl = new URLSearchParams(location.search).get('user')?.trim()
    if (onUserRoute && fromUrl) {
      setUsername(fromUrl)
      const v = validateGitHubUsername(fromUrl)
      setValidationState(v.valid ? 'valid' : 'invalid')
      setValidationIssue(v.valid ? null : 'invalid')
      return
    }
    if (!didRestoreTopbarUser.current && currentUser) {
      didRestoreTopbarUser.current = true
      setUsername(currentUser)
      const v = validateGitHubUsername(currentUser)
      setValidationState(v.valid ? 'valid' : 'idle')
      setValidationIssue(null)
    }
  }, [location.pathname, location.search, currentUser])

  useEffect(() => {
    return () => {
      generateAbortRef.current?.abort()
    }
  }, [])

  useEffect(() => {
    if (!showSettings) return
    const onPointerDown = (e: PointerEvent) => {
      const el = settingsWrapRef.current
      if (el && !el.contains(e.target as Node)) setShowSettings(false)
    }
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowSettings(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [showSettings])

  useEffect(() => {
    if (!showSearchSuggestions) return
    const onPointerDown = (e: PointerEvent) => {
      const el = searchWrapRef.current
      if (el && !el.contains(e.target as Node)) setShowSearchSuggestions(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
    }
  }, [showSearchSuggestions])

  const text = labels[language]
  const quickActionsText = language === 'zh' ? '快捷操作' : 'Quick Actions'
  const analyzeNowText = language === 'zh' ? '立即分析' : 'Analyze now'
  const textMap = text as Record<string, string>
  const recentSearchesText = textMap.recentSearches ?? (language === 'zh' ? '近期' : 'Recent')
  const useSuggestionText = textMap.useSuggestion ?? (language === 'zh' ? '打开' : 'Open')

  const quickActionRepoText = language === 'zh' ? '打开目标仓库' : 'Open target repo'
  const repoScopeText = language === 'zh' ? 'README / Topics / 结构 / AI 分析' : 'README / Topics / Structure / AI analysis'
  const userScopeText = language === 'zh' ? 'GitScore / AI 洞察 / 仓库概览' : 'GitScore / AI insights / Repo overview'

  const toggleTheme = () => {
    const nextTheme = theme === 'light' ? 'dark' : 'light'
    setTheme(nextTheme)
    localStorage.setItem('codefolio-theme', nextTheme)
    document.documentElement.classList.toggle('dark', nextTheme === 'dark')
  }

  const toggleLanguage = () => {
    const nextLanguage = language === 'en' ? 'zh' : 'en'
    setLanguage(nextLanguage)
    setContentLanguage(nextLanguage)
    localStorage.setItem('codefolio-language', nextLanguage)
  }

  const handleUsernameChange = (value: string) => {
    setUsername(value)
    setShowSearchSuggestions(true)
    if (!value.trim()) {
      setValidationState('idle')
      setValidationIssue(null)
    } else {
      const validation = validateGitHubUsername(value)
      if (validation.valid) {
        setValidationState('valid')
        setValidationIssue(null)
      } else {
        setValidationState('invalid')
        setValidationIssue('invalid')
      }
    }
  }

  const runGenerate = async (explicitUsername?: string) => {
    const parsedInput = parseGitHubInput(explicitUsername ?? username)
    if (parsedInput.kind === 'empty' || parsedInput.kind === 'invalid') {
      setValidationState(parsedInput.kind === 'empty' ? 'idle' : 'invalid')
      setValidationIssue(parsedInput.kind === 'invalid' ? 'invalid' : null)
      return
    }
    const resolved = parsedInput.username

    const seq = ++generateRequestSeqRef.current

    generateAbortRef.current?.abort()
    const abortController = new AbortController()
    generateAbortRef.current = abortController

    setLoading(true)
    setError('')
    setLastFailedUsername(null)

    const startTime = Date.now()
    const progressInterval = setInterval(() => {
      const elapsed = (Date.now() - startTime) / 1000
      if (elapsed < 2) {
        setCurrentStep('fetching')
        setEstimatedTimeRemaining(Math.max(0, 8 - elapsed))
      } else if (elapsed < 5) {
        setCurrentStep('scoring')
        setEstimatedTimeRemaining(Math.max(0, 8 - elapsed))
      } else {
        setCurrentStep('polishing')
        setEstimatedTimeRemaining(Math.max(0, 8 - elapsed))
      }
    }, 100)

    try {
      const response = await axios.post<GenerateResponse>(
        `${API_BASE_URL}/api/generate`,
        {
          username: resolved,
          language: contentLanguage,
        },
        { signal: abortController.signal },
      )

      if (seq !== generateRequestSeqRef.current) return

      const result = response.data
      const activeOutput = result.localized_outputs[contentLanguage]

      setCurrentUser(result.user.username)
      setUsername(result.user.username)
      setShowSearchSuggestions(false)
      setValidationState('valid')
      setValidationIssue(null)
      if (activeOutput) {
        setLastResult({
          username: result.user.username,
          avatarUrl: result.user.avatar_url,
          gitscore: activeOutput.card_data.gitscore,
          bio: result.user.bio,
          timestamp: Date.now(),
        })
      }

      cacheGenerateResult({
        username: result.user.username,
        contentLanguage,
        data: result,
      })

      addToHistory(result, contentLanguage)
      setSearchSuggestions(readHistoryItems().map((item) => item.username))

      if (parsedInput.kind === 'repo') {
        navigate(
          `/repositories?user=${encodeURIComponent(result.user.username)}&repo=${encodeURIComponent(parsedInput.repo)}`,
        )
      } else {
        navigate(`/analysis?user=${encodeURIComponent(result.user.username)}`)
      }
    } catch (requestError) {
      if (isRequestAborted(requestError)) return
      if (seq !== generateRequestSeqRef.current) return
      setLastFailedUsername(resolved)
      setError(getAnalyzeErrorMessage(requestError, language))
    } finally {
      clearInterval(progressInterval)
      if (seq === generateRequestSeqRef.current) {
        setLoading(false)
        setEstimatedTimeRemaining(0)
      }
    }
  }

  const handleGenerate = (event?: FormEvent) => {
    event?.preventDefault()
    void runGenerate()
  }

  const recentSuggestions = searchSuggestions
    .map((item) => normalizeGitHubUsernameInput(item))
    .filter(Boolean)
    .filter((item, index, list) => list.indexOf(item) === index)
    .slice(0, 5)

  const parsedInput = parseGitHubInput(username)
  const validatedInput = validateGitHubUsername(username)
  const actionUsername =
    parsedInput.kind === 'user' || parsedInput.kind === 'repo'
      ? parsedInput.username
      : normalizeGitHubUsernameInput(username)
  const filteredRecentSuggestions = recentSuggestions.filter((item) =>
    !actionUsername ? true : item.toLowerCase().includes(actionUsername.toLowerCase()),
  )
  const inputRecognitionHint =
    parsedInput.kind === 'repo'
      ? `${language === 'zh' ? '将跳转到仓库并展开分析' : 'Will jump to repository and expand analysis'}: ${parsedInput.username}/${parsedInput.repo}`
      : parsedInput.kind === 'user'
        ? `${language === 'zh' ? '将分析 GitHub 用户' : 'Will analyze GitHub user'}: @${parsedInput.username}`
        : parsedInput.kind === 'invalid' && username.trim()
          ? language === 'zh'
            ? '输入不是有效的 GitHub 用户名或仓库地址。'
            : 'Input is not a valid GitHub username or repository URL.'
          : ''

  const openUserRoute = (path: string, targetUsername: string) => {
    setUsername(targetUsername)
    setCurrentUser(targetUsername)
    setValidationState('valid')
    setValidationIssue(null)
    setShowSearchSuggestions(false)
    navigate(`${path}?user=${encodeURIComponent(targetUsername)}`)
  }

  const getActiveNav = () => {
    const path = location.pathname
    if (path === '/' || path === '/overview') return 'overview'
    if (path.startsWith('/repositories')) return 'repositories'
    if (path.startsWith('/analysis')) return 'analysis'
    if (path.startsWith('/export')) return 'export'
    if (path === '/compare/repos') return 'benchmark'
    if (path.startsWith('/compare')) return 'compare'
    return 'overview'
  }

  const activeNav = getActiveNav()

  // Generate nav links with current user param if available
  const getNavLink = (path: string) => {
    if (currentUser) {
      return `${path}?user=${currentUser}`
    }
    return path
  }

  return (
    <div className="app-layout">
      {/* Side Navigation */}
      <aside className="side-nav">
        <div className="side-brand">
          <h2 className="brand">{text.brand}</h2>
          <p className="eyebrow">{text.eyebrow}</p>
        </div>

        <nav className="side-links">
          <Link
            to="/"
            className={`side-link ${activeNav === 'overview' ? 'side-link-active' : ''}`}
          >
            <DashboardIcon />
            <span>{text.navOverview}</span>
          </Link>
          <Link
            to={getNavLink('/repositories')}
            className={`side-link ${activeNav === 'repositories' ? 'side-link-active' : ''}`}
          >
            <RepoIcon />
            <span>{text.navRepositories}</span>
          </Link>
          <Link
            to={getNavLink('/analysis')}
            className={`side-link ${activeNav === 'analysis' ? 'side-link-active' : ''}`}
          >
            <AIIcon />
            <span>{text.navInsights}</span>
          </Link>
          <Link
            to={getNavLink('/export')}
            className={`side-link ${activeNav === 'export' ? 'side-link-active' : ''}`}
          >
            <ExportIcon />
            <span>{text.navExport}</span>
          </Link>
          <Link
            to="/compare"
            className={`side-link ${activeNav === 'compare' ? 'side-link-active' : ''}`}
          >
            <CompareIcon />
            <span>{text.navCompare}</span>
          </Link>
          <Link
            to="/compare/repos"
            className={`side-link ${activeNav === 'benchmark' ? 'side-link-active' : ''}`}
          >
            <BenchmarkIcon />
            <span>{text.navBenchmark}</span>
          </Link>
        </nav>

        <div className="side-footer-area">
          <div className="side-footer">{text.workspaceSynced}</div>
        </div>
      </aside>

      {/* Main Canvas */}
      <main className="main-canvas">
        {/* Top Navigation Bar */}
        <header className="topbar">
          <div className="topbar-left">
            <span className="topbar-brand-text">{text.brand}</span>
            <nav className="topbar-nav">
              <span className="topbar-nav-item active">{text.dashboard}</span>
            </nav>
          </div>

          <form className="topbar-search" onSubmit={handleGenerate} ref={searchWrapRef}>
            <div className="topbar-search-row">
              <div className="search-input-wrapper">
                <SearchIcon />
                <input
                  value={username}
                  onChange={(e) => handleUsernameChange(e.target.value)}
                  onFocus={() => setShowSearchSuggestions(true)}
                  placeholder={text.placeholder}
                  list="topbar-search-history"
                  className={`topbar-search-input${validationState === 'invalid' ? ' topbar-search-input--invalid' : ''}`}
                  aria-invalid={validationState === 'invalid'}
                  aria-describedby={validationIssue ? 'topbar-username-hint' : undefined}
                />
                <datalist id="topbar-search-history">
                  {searchSuggestions.map((item) => {
                    const normalized = normalizeGitHubUsernameInput(item)
                    return normalized ? <option key={normalized} value={normalized} /> : null
                  })}
                </datalist>
              </div>
              <button
                type="submit"
                className="topbar-generate-btn"
                disabled={loading || validationState === 'invalid' || !username.trim()}
              >
                {loading ? text.generating : text.generate}
              </button>
            </div>
            {showSearchSuggestions && (filteredRecentSuggestions.length > 0 || Boolean(actionUsername)) && (
              <div className="topbar-search-suggestions" role="list" aria-label={recentSearchesText}>
                {actionUsername && validatedInput.valid && (
                  <>
                    <span className="topbar-search-suggestions-label">{quickActionsText}</span>
                    <div className="topbar-search-suggestions-list">
                      <button
                        type="button"
                        className="topbar-search-suggestion topbar-search-suggestion--primary"
                        onMouseDown={(e) => {
                          e.preventDefault()
                          void runGenerate(actionUsername)
                        }}
                      >
                        <span>{parsedInput.kind === 'repo' ? quickActionRepoText : analyzeNowText}</span>
                        <span>{parsedInput.kind === 'repo' ? `${actionUsername}/${parsedInput.repo}` : `@${actionUsername}`}</span>
                      </button>
                      <button
                        type="button"
                        className="topbar-search-suggestion"
                        onMouseDown={(e) => {
                          e.preventDefault()
                          openUserRoute('/analysis', actionUsername)
                        }}
                      >
                        <span>{text.navInsights}</span>
                        <span>@{actionUsername}</span>
                      </button>
                      <button
                        type="button"
                        className="topbar-search-suggestion"
                        onMouseDown={(e) => {
                          e.preventDefault()
                          if (parsedInput.kind === 'repo') {
                            navigate(
                              `/repositories?user=${encodeURIComponent(actionUsername)}&repo=${encodeURIComponent(parsedInput.repo)}`,
                            )
                            setUsername(actionUsername)
                            setCurrentUser(actionUsername)
                            setValidationState('valid')
                            setValidationIssue(null)
                            setShowSearchSuggestions(false)
                          } else {
                            openUserRoute('/repositories', actionUsername)
                          }
                        }}
                      >
                        <span>{text.navRepositories}</span>
                        <span>{parsedInput.kind === 'repo' ? `${actionUsername}/${parsedInput.repo}` : `@${actionUsername}`}</span>
                      </button>
                    </div>
                    <p className="topbar-search-scope">
                      {parsedInput.kind === 'repo' ? repoScopeText : userScopeText}
                    </p>
                  </>
                )}
                {filteredRecentSuggestions.length > 0 && (
                  <>
                    <span className="topbar-search-suggestions-label">{recentSearchesText}</span>
                    <div className="topbar-search-suggestions-list">
                      {filteredRecentSuggestions.map((item) => (
                        <button
                          key={item}
                          type="button"
                          className="topbar-search-suggestion"
                          onMouseDown={(e) => {
                            e.preventDefault()
                            setUsername(item)
                            setValidationState('valid')
                            setValidationIssue(null)
                            void runGenerate(item)
                          }}
                        >
                          <span>@{item}</span>
                          <span>{useSuggestionText}</span>
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
            {inputRecognitionHint && validationIssue !== 'invalid' && (
              <p className="topbar-search-recognition" role="status">
                {inputRecognitionHint}
              </p>
            )}
            {validationIssue === 'invalid' && (
              <p id="topbar-username-hint" className="topbar-search-hint" role="status">
                {text.validationInvalid}
              </p>
            )}
          </form>

          <div className="topbar-right" ref={settingsWrapRef}>
            <button
              type="button"
              className="settings-btn"
              aria-expanded={showSettings}
              aria-haspopup="true"
              aria-label={text.settings}
              onClick={() => setShowSettings(!showSettings)}
            >
              <SettingsIcon />
            </button>

            {showSettings && (
              <div className="settings-dropdown">
                <div className="settings-item">
                  <span>{text.uiLang}</span>
                  <button type="button" className="chip-button" onClick={toggleLanguage}>
                    {language === 'en' ? 'English' : '中文'}
                  </button>
                </div>
                <div className="settings-item">
                  <span>{text.theme}</span>
                  <button type="button" className="chip-button" onClick={toggleTheme}>
                    {theme === 'dark' ? text.themeDark : text.themeLight}
                  </button>
                </div>
              </div>
            )}
          </div>

          <button
            type="button"
            className="mobile-menu-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? '✕' : '☰'}
          </button>
        </header>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="mobile-menu">
            <nav className="mobile-nav">
              <Link to="/" onClick={() => setMobileMenuOpen(false)}>{text.navOverview}</Link>
              <Link to={getNavLink('/repositories')} onClick={() => setMobileMenuOpen(false)}>{text.navRepositories}</Link>
              <Link to={getNavLink('/analysis')} onClick={() => setMobileMenuOpen(false)}>{text.navInsights}</Link>
              <Link to={getNavLink('/export')} onClick={() => setMobileMenuOpen(false)}>{text.navExport}</Link>
              <Link to="/compare" onClick={() => setMobileMenuOpen(false)}>{text.navCompare}</Link>
            </nav>
            <div className="mobile-controls">
              <button type="button" onClick={toggleLanguage}>
                {text.uiLang}: {language === 'en' ? 'English' : '中文'}
              </button>
              <button type="button" onClick={toggleTheme}>
                {text.theme}: {theme === 'dark' ? text.themeDark : text.themeLight}
              </button>
            </div>
          </div>
        )}

        {/* Content Shell */}
        <div className="content-shell">
          {error && (
            <div className="error-banner">
              <span className="error-icon">⚠️</span>
              <span className="error-message">{error}</span>
              <div className="error-banner-actions">
                {lastFailedUsername && (
                  <button
                    type="button"
                    className="error-retry"
                    onClick={() => void runGenerate(lastFailedUsername)}
                  >
                    {text.errorRetry}
                  </button>
                )}
                <button
                  type="button"
                  className="error-dismiss"
                  onClick={() => {
                    setError('')
                    setLastFailedUsername(null)
                  }}
                >
                  {text.errorDismiss}
                </button>
              </div>
            </div>
          )}

          {loading && (
            <section className="loading-section">
              <ProgressIndicator
                currentStep={currentStep}
                estimatedTimeRemaining={estimatedTimeRemaining}
                language={language}
                labels={{
                  progressFetching: text.progressFetching,
                  progressScoring: text.progressScoring,
                  progressPolishing: text.progressPolishing,
                  progressTimeRemaining: text.progressTimeRemaining,
                }}
              />
              <SkeletonScreen language={language} />
            </section>
          )}

          {!loading && (
            <Suspense fallback={<PageFallback language={language} />}>
              <Routes>
                <Route path="/" element={<Overview language={language} />} />
                <Route path="/repositories" element={<Repositories language={language} />} />
                <Route path="/analysis" element={<AIAnalysis language={language} />} />
                <Route path="/export" element={<Export language={language} />} />
                <Route path="/compare" element={<Navigate to="/compare/users" replace />} />
                <Route path="/compare/users" element={<Compare language={language} />} />
                <Route path="/compare/repos" element={<CompareRepos language={language} />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          )}
        </div>
      </main>
    </div>
  )
}

function App() {
  return (
    <Router>
      <AppProvider>
        <Layout />
      </AppProvider>
    </Router>
  )
}

export default App
