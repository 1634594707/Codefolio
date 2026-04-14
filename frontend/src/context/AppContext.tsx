import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import type { GenerateResponse } from '../types/generate'
import type { BenchmarkResponse } from '../types/benchmark'
import { githubLoginEquals } from '../utils/githubLogin'
import { validateGitHubUsername } from '../utils/githubInput'

export type ContentLanguage = 'en' | 'zh'

export type GenerateCacheEntry = {
  username: string
  contentLanguage: ContentLanguage
  data: GenerateResponse
  cachedAt: number
}

export type ResumeProject = {
  user: string
  repoName: string
  description: string
  language: string
  stars: number
  forks: number
  url: string
  pushed_at?: string
  has_readme?: boolean
  has_license?: boolean
  analysisTitle: string
  analysisSummary: string
  highlights: string[]
  keywords: string[]
}

export type BenchmarkWorkspaceEntry = {
  username: string
  mine: string
  benchmarks: string[]
  language: ContentLanguage
  result: BenchmarkResponse
  savedAt: number
}

function readStoredCurrentUser(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem('codefolio-current-user')?.trim() ?? ''
}

/** 与界面语言同源：仅读 `codefolio-language`，由 Layout 在挂载/切换时与 UI 对齐 */
function readInitialContentLanguage(): ContentLanguage {
  if (typeof window === 'undefined') return 'en'
  const savedUi = localStorage.getItem('codefolio-language')
  if (savedUi === 'en' || savedUi === 'zh') return savedUi
  return navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en'
}

interface AnalysisResult {
  username: string
  avatarUrl: string
  gitscore: number
  bio: string
  timestamp: number
}

interface AppContextType {
  currentUser: string
  setCurrentUser: (user: string) => void
  lastResult: AnalysisResult | null
  setLastResult: (result: AnalysisResult | null) => void
  contentLanguage: ContentLanguage
  setContentLanguage: (lang: ContentLanguage) => void
  generateCacheEntries: GenerateCacheEntry[]
  cacheGenerateResult: (entry: Omit<GenerateCacheEntry, 'cachedAt'>) => void
  getGenerateCache: (username: string, lang: ContentLanguage) => GenerateCacheEntry | null
  clearGenerateCacheForUser: (username: string) => void
  getResumeProjects: (username: string) => ResumeProject[]
  toggleResumeProject: (project: ResumeProject) => void
  removeResumeProject: (username: string, repoName: string) => void
  saveBenchmarkWorkspaceEntry: (entry: Omit<BenchmarkWorkspaceEntry, 'savedAt'>) => void
  getLatestBenchmarkWorkspaceEntryForUser: (username: string) => BenchmarkWorkspaceEntry | null
  compareList: string[]
  setCompareList: (list: string[]) => void
  addToCompare: (username: string) => void
  removeFromCompare: (username: string) => void
}

const AppContext = createContext<AppContextType | undefined>(undefined)

const GENERATE_CACHE_STORAGE_KEY = 'codefolio-generate-cache'
const RESUME_PROJECTS_STORAGE_KEY = 'codefolio-resume-projects'
const BENCHMARK_WORKSPACE_STORAGE_KEY = 'codefolio-benchmark-workspace'

function readStoredGenerateCache(): GenerateCacheEntry[] {
  if (typeof window === 'undefined') return []
  const saved = localStorage.getItem(GENERATE_CACHE_STORAGE_KEY)
  if (!saved) return []

  try {
    const parsed = JSON.parse(saved) as GenerateCacheEntry[]
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter((item) => item?.username && item?.contentLanguage && item?.data)
      .slice(0, 24)
  } catch {
    return []
  }
}

function readStoredResumeProjects(): ResumeProject[] {
  if (typeof window === 'undefined') return []
  const saved = localStorage.getItem(RESUME_PROJECTS_STORAGE_KEY)
  if (!saved) return []

  try {
    const parsed = JSON.parse(saved) as ResumeProject[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function readStoredBenchmarkWorkspace(): BenchmarkWorkspaceEntry[] {
  if (typeof window === 'undefined') return []
  const saved = localStorage.getItem(BENCHMARK_WORKSPACE_STORAGE_KEY)
  if (!saved) return []

  try {
    const parsed = JSON.parse(saved) as BenchmarkWorkspaceEntry[]
    return Array.isArray(parsed)
      ? parsed.filter((item) => item?.username && item?.mine && item?.benchmarks && item?.result).slice(0, 12)
      : []
  } catch {
    return []
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [currentUser, _setCurrentUser] = useState(readStoredCurrentUser)
  const setCurrentUser = useCallback((user: string) => {
    const u = user.trim()
    _setCurrentUser(u)
    if (typeof window === 'undefined') return
    if (u) localStorage.setItem('codefolio-current-user', u)
    else localStorage.removeItem('codefolio-current-user')
  }, [])

  const [lastResult, setLastResult] = useState<AnalysisResult | null>(null)
  const [contentLanguage, setContentLanguage] = useState<ContentLanguage>(readInitialContentLanguage)
  const [generateCacheEntries, setGenerateCacheEntries] = useState<GenerateCacheEntry[]>(readStoredGenerateCache)
  const [resumeProjects, setResumeProjects] = useState<ResumeProject[]>(readStoredResumeProjects)
  const [benchmarkWorkspaceEntries, setBenchmarkWorkspaceEntries] =
    useState<BenchmarkWorkspaceEntry[]>(readStoredBenchmarkWorkspace)

  const cacheGenerateResult = useCallback((entry: Omit<GenerateCacheEntry, 'cachedAt'>) => {
    const normalizedUsername = entry.username.trim()
    if (!normalizedUsername) return
    setGenerateCacheEntries((prev) => {
      const nextEntry: GenerateCacheEntry = {
        ...entry,
        username: normalizedUsername,
        cachedAt: Date.now(),
      }
      const filtered = prev.filter(
        (item) =>
          !(
            item.contentLanguage === nextEntry.contentLanguage &&
            item.username.trim().toLowerCase() === normalizedUsername.toLowerCase()
          ),
      )
      return [nextEntry, ...filtered].slice(0, 24)
    })
  }, [])

  const getGenerateCache = useCallback(
    (username: string, lang: ContentLanguage) => {
      const normalizedUsername = username.trim().toLowerCase()
      if (!normalizedUsername) return null
      return (
        generateCacheEntries.find(
          (entry) =>
            entry.contentLanguage === lang &&
            entry.username.trim().toLowerCase() === normalizedUsername,
        ) ?? null
      )
    },
    [generateCacheEntries],
  )

  const clearGenerateCacheForUser = useCallback((username: string) => {
    const parsed = validateGitHubUsername(username)
    if (!parsed.valid) return

    setGenerateCacheEntries((prev) =>
      prev.filter((entry) => !githubLoginEquals(entry.username, parsed.username)),
    )
  }, [])

  useEffect(() => {
    localStorage.setItem('codefolio-content-language', contentLanguage)
  }, [contentLanguage])

  useEffect(() => {
    localStorage.setItem(GENERATE_CACHE_STORAGE_KEY, JSON.stringify(generateCacheEntries))
  }, [generateCacheEntries])

  useEffect(() => {
    localStorage.setItem(RESUME_PROJECTS_STORAGE_KEY, JSON.stringify(resumeProjects))
  }, [resumeProjects])

  useEffect(() => {
    localStorage.setItem(BENCHMARK_WORKSPACE_STORAGE_KEY, JSON.stringify(benchmarkWorkspaceEntries))
  }, [benchmarkWorkspaceEntries])

  const getResumeProjects = useCallback(
    (username: string) => resumeProjects.filter((project) => githubLoginEquals(project.user, username)),
    [resumeProjects],
  )

  const toggleResumeProject = useCallback((project: ResumeProject) => {
    setResumeProjects((prev) => {
      const exists = prev.some(
        (item) => githubLoginEquals(item.user, project.user) && item.repoName === project.repoName,
      )
      if (exists) {
        return prev.filter(
          (item) => !(githubLoginEquals(item.user, project.user) && item.repoName === project.repoName),
        )
      }

      const sameUserProjects = prev.filter((item) => githubLoginEquals(item.user, project.user))
      const otherProjects = prev.filter((item) => !githubLoginEquals(item.user, project.user))
      const nextForUser = [project, ...sameUserProjects].slice(0, 4)
      return [...otherProjects, ...nextForUser]
    })
  }, [])

  const removeResumeProject = useCallback((username: string, repoName: string) => {
    setResumeProjects((prev) =>
      prev.filter((item) => !(githubLoginEquals(item.user, username) && item.repoName === repoName)),
    )
  }, [])

  const saveBenchmarkWorkspaceEntry = useCallback((entry: Omit<BenchmarkWorkspaceEntry, 'savedAt'>) => {
    const parsed = validateGitHubUsername(entry.username)
    if (!parsed.valid) return

    setBenchmarkWorkspaceEntries((prev) => {
      const nextEntry: BenchmarkWorkspaceEntry = {
        ...entry,
        username: parsed.username,
        savedAt: Date.now(),
      }
      const filtered = prev.filter(
        (item) =>
          !(
            githubLoginEquals(item.username, parsed.username) &&
            item.mine.toLowerCase() === nextEntry.mine.toLowerCase() &&
            item.language === nextEntry.language
          ),
      )
      return [nextEntry, ...filtered].slice(0, 12)
    })
  }, [])

  const getLatestBenchmarkWorkspaceEntryForUser = useCallback(
    (username: string) => {
      const parsed = validateGitHubUsername(username)
      if (!parsed.valid) return null
      return benchmarkWorkspaceEntries.find((entry) => githubLoginEquals(entry.username, parsed.username)) ?? null
    },
    [benchmarkWorkspaceEntries],
  )

  const [compareList, setCompareList] = useState<string[]>(() => {
    // Load from localStorage on init
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('codefolio-compare-list')
      if (saved) {
        try {
          return JSON.parse(saved)
        } catch {
          return []
        }
      }
    }
    return []
  })

  // Persist compareList to localStorage
  useEffect(() => {
    localStorage.setItem('codefolio-compare-list', JSON.stringify(compareList))
  }, [compareList])

  const addToCompare = (username: string) => {
    const parsed = validateGitHubUsername(username)
    if (!parsed.valid) return

    setCompareList((prev) => {
      if (prev.some((item) => githubLoginEquals(item, parsed.username))) return prev
      if (prev.length >= 3) return prev // Max 3 users
      return [...prev, parsed.username]
    })
  }

  const removeFromCompare = (username: string) => {
    setCompareList((prev) => prev.filter((u) => !githubLoginEquals(u, username)))
  }

  return (
    <AppContext.Provider
      value={{
        currentUser,
        setCurrentUser,
        lastResult,
        setLastResult,
        contentLanguage,
        setContentLanguage,
        generateCacheEntries,
        cacheGenerateResult,
        getGenerateCache,
        clearGenerateCacheForUser,
        getResumeProjects,
        toggleResumeProject,
        removeResumeProject,
        saveBenchmarkWorkspaceEntry,
        getLatestBenchmarkWorkspaceEntryForUser,
        compareList,
        setCompareList,
        addToCompare,
        removeFromCompare,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within AppProvider')
  }
  return context
}
