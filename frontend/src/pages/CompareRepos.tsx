import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import axios from 'axios'
import { ActionList } from '../components/ActionList'
import { BenchmarkMatrix } from '../components/BenchmarkMatrix'
import { HypothesisCards } from '../components/HypothesisCards'
import { useApp } from '../context'
import type { BenchmarkResponse, RepoProfile } from '../types/benchmark'
import { isRequestAborted } from '../utils/axiosAbort'
import { parseGitHubRepoInput } from '../utils/githubInput'
import { generateBenchmarkMarkdown } from '../utils/benchmarkExport'
import { formatCacheAge, isStale } from '../utils/formatCacheAge'
import { API_BASE_URL } from '../config/api'

interface CompareReposProps {
  language: 'en' | 'zh'
}

interface BenchmarkSuggestion {
  full_name: string
  reason_code: string
  reason_params: Record<string, string | number | string[]>
  stars: number
  reason_title: string
  reason_summary: string
  learn_from: string
  badges: string[]
}

const labels = {
  en: {
    title: 'Benchmark Repositories',
    subtitle: 'Compare one repository against stronger peers and turn visible gaps into action.',
    tabsUsers: 'Developers',
    tabsRepos: 'Repositories',
    mineLabel: 'My repository',
    benchmarkLabel: 'Benchmark repository',
    minePlaceholder: 'owner/repo…',
    benchmarkPlaceholder: 'owner/repo…',
    addBenchmark: 'Add benchmark',
    removeBenchmark: 'Remove',
    compare: 'Generate benchmark',
    comparing: 'Benchmarking…',
    includeNarrative: 'Include narrative summary',
    empty: 'Start with one repository you want to improve, then add up to three benchmark repositories.',
    invalidMine: 'Use a valid GitHub repository like owner/repo.',
    invalidBenchmarks: 'Add at least one valid benchmark repository.',
    duplicateBenchmarks: 'Benchmark repositories must be unique and different from your repository.',
    loadError: 'Failed to generate repository benchmark.',
    overview: 'Overview',
    matrix: 'Gap Matrix',
    actions: 'Action Items',
    evidence: 'Why these repos stand out',
    statusMine: 'Mine',
    score: 'Score',
    quickFacts: 'Quick facts',
    workflows: 'Workflows',
    lastUpdated: 'Last updated',
    noDescription: 'No description provided.',
    disclaimer: 'Boundary',
    quickWin: 'Quick win',
    transferability: 'Transferability',
    confidence: 'Confidence',
    generatedAt: 'Generated',
    copyMarkdown: 'Copy Markdown',
    copied: 'Copied',
    downloadMarkdown: 'Download .md',
    details: 'View details',
    noDetails: 'No raw signals available.',
    sortBy: 'Sort by',
    filterBy: 'Filter by',
    sortPriority: 'Priority',
    sortEffort: 'Effort',
    sortImpact: 'Impact',
    allDimensions: 'All dimensions',
    markComplete: 'Mark complete',
    timeline7d: '7 day focus',
    timeline30d: '30 day plan',
    timeline90d: '90 day backlog',
    noActions: 'No action items generated.',
    filterCategory: 'Category',
    filterTransferability: 'Transferability',
    allCategories: 'All categories',
    allTransferability: 'All levels',
    showEvidence: 'Show evidence',
    noHypotheses: 'No hypotheses generated.',
    staleWarning: 'This data is over 7 days old. Consider refreshing.',
    refresh: 'Refresh',
    suggestBenchmarks: 'Suggest Benchmarks',
    suggesting: 'Finding suggestions…',
    suggestError: 'Failed to fetch suggestions.',
    noSuggestions: 'No suggestions found.',
    addSuggestion: 'Add',
    whyItFits: 'Why it fits',
    whatToLearn: 'What to learn',
  },
  zh: {
    title: '仓库对标',
    subtitle: '把你的仓库与更强的标杆仓库放在一起比较，并直接生成改进行动。',
    tabsUsers: '开发者',
    tabsRepos: '仓库',
    mineLabel: '我的仓库',
    benchmarkLabel: '标杆仓库',
    minePlaceholder: 'owner/repo…',
    benchmarkPlaceholder: 'owner/repo…',
    addBenchmark: '添加标杆',
    removeBenchmark: '移除',
    compare: '生成对标',
    comparing: '对标中…',
    includeNarrative: '包含叙述总结',
    empty: '先输入一个你想提升的仓库，再添加最多 3 个标杆仓库。',
    invalidMine: '请输入有效的 GitHub 仓库，格式如 owner/repo。',
    invalidBenchmarks: '请至少填写一个有效的标杆仓库。',
    duplicateBenchmarks: '标杆仓库必须唯一，且不能与你的仓库相同。',
    loadError: '仓库对标生成失败。',
    overview: '概览',
    matrix: '差距矩阵',
    actions: '行动项',
    evidence: '这些仓库为何更突出',
    statusMine: '我的仓库',
    score: '评分',
    quickFacts: '关键信号',
    workflows: '工作流',
    lastUpdated: '最近更新',
    noDescription: '暂无描述。',
    disclaimer: '边界说明',
    quickWin: '快速收益',
    transferability: '可迁移性',
    confidence: '置信度',
    generatedAt: '生成时间',
    copyMarkdown: '复制 Markdown',
    copied: '已复制',
    downloadMarkdown: '下载 .md',
    details: '查看详情',
    noDetails: '暂无原始信号。',
    sortBy: '排序方式',
    filterBy: '筛选方式',
    sortPriority: '优先级',
    sortEffort: '投入成本',
    sortImpact: '影响',
    allDimensions: '全部维度',
    markComplete: '标记完成',
    timeline7d: '7 天聚焦',
    timeline30d: '30 天计划',
    timeline90d: '90 天积压',
    noActions: '暂无生成的行动项。',
    filterCategory: '类别',
    filterTransferability: '可迁移性',
    allCategories: '全部类别',
    allTransferability: '全部等级',
    showEvidence: '显示依据',
    noHypotheses: '暂无生成的假设。',
    staleWarning: '此数据已超过 7 天，建议刷新。',
    refresh: '刷新',
    suggestBenchmarks: '推荐标杆仓库',
    suggesting: '正在查找推荐…',
    suggestError: '获取推荐失败。',
    noSuggestions: '未找到推荐仓库。',
    addSuggestion: '添加',
  },
} as const

function CompareModeTabs({ language }: CompareReposProps) {
  const text = labels[language]
  return (
    <div className="repo-view-switcher" role="tablist" aria-label={text.title}>
      <Link to="/compare/users" className="repo-view-chip" role="tab" aria-selected="false">
        {text.tabsUsers}
      </Link>
      <Link to="/compare/repos" className="repo-view-chip active" role="tab" aria-selected="true">
        {text.tabsRepos}
      </Link>
    </div>
  )
}

function formatDate(value: string | null, language: 'en' | 'zh'): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) return fallback
  const detail = error.response?.data?.detail
  if (typeof detail?.message === 'string' && detail.message) return detail.message
  return fallback
}

export function CompareRepos({ language }: CompareReposProps) {
  const { saveBenchmarkWorkspaceEntry } = useApp()
  const [searchParams, setSearchParams] = useSearchParams()
  const text = labels[language]
  const [mineInput, setMineInput] = useState(searchParams.get('mine') ?? '')
  const [benchmarkInputs, setBenchmarkInputs] = useState<string[]>(() => {
    const fromUrl = (searchParams.get('b') ?? '').split(',').filter(Boolean).slice(0, 3)
    return fromUrl.length > 0 ? fromUrl : ['']
  })
  const [includeNarrative, setIncludeNarrative] = useState(searchParams.get('n') !== '0')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<BenchmarkResponse | null>(null)
  const [markdownCopied, setMarkdownCopied] = useState(false)
  const [suggestions, setSuggestions] = useState<BenchmarkSuggestion[]>([])
  const [suggestLoading, setSuggestLoading] = useState(false)
  const [suggestError, setSuggestError] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const filledBenchmarkCount = benchmarkInputs.filter((item) => item.trim()).length
  const whyItFitsLabel = language === 'zh' ? '推荐理由' : text.whyItFits
  const whatToLearnLabel = language === 'zh' ? '可以重点学什么' : text.whatToLearn

  useEffect(() => {
    setMineInput(searchParams.get('mine') ?? '')
    const fromUrl = (searchParams.get('b') ?? '').split(',').filter(Boolean).slice(0, 3)
    setBenchmarkInputs(fromUrl.length > 0 ? fromUrl : [''])
    setIncludeNarrative(searchParams.get('n') !== '0')
  }, [searchParams])

  useEffect(() => {
    const mine = searchParams.get('mine') ?? ''
    const benchmarks = (searchParams.get('b') ?? '').split(',').filter(Boolean)
    if (!mine || benchmarks.length === 0) return

    let cancelled = false
    const abortController = new AbortController()

    const fetchBenchmark = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await axios.post<BenchmarkResponse>(
          `${API_BASE_URL}/api/repos/benchmark`,
          {
            mine,
            benchmarks,
            language,
            options: {
              include_narrative: searchParams.get('n') === '1',
              max_readme_chars_per_repo: 12000,
            },
          },
          { signal: abortController.signal },
        )
        if (!cancelled) {
          setResult(response.data)
          saveBenchmarkWorkspaceEntry({
            username: mine.split('/')[0],
            mine,
            benchmarks,
            language,
            result: response.data,
          })
        }
      } catch (requestError) {
        if (isRequestAborted(requestError) || cancelled) return
        if (!cancelled) {
          setResult(null)
          setError(extractErrorMessage(requestError, text.loadError))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void fetchBenchmark()
    return () => {
      cancelled = true
      abortController.abort()
    }
  }, [language, searchParams, text.loadError])

  const addBenchmarkField = () => {
    setBenchmarkInputs((current) => {
      if (current.length >= 3) return current
      // don't add another empty field if the last one is already empty
      if (current[current.length - 1] === '') return current
      return [...current, '']
    })
  }

  const updateBenchmarkField = (index: number, value: string) => {
    setBenchmarkInputs((current) => current.map((item, itemIndex) => (itemIndex === index ? value : item)))
  }

  const removeBenchmarkField = (index: number) => {
    setBenchmarkInputs((current) => current.filter((_, itemIndex) => itemIndex !== index))
  }

  const handleSuggest = async () => {
    const parsedMine = parseGitHubRepoInput(mineInput)
    if (parsedMine.kind !== 'repo') {
      setError(text.invalidMine)
      return
    }
    setSuggestLoading(true)
    setSuggestError('')
    setShowSuggestions(true)
    try {
      const response = await axios.get<{ suggestions: BenchmarkSuggestion[] }>(
        `${API_BASE_URL}/api/repos/suggest-benchmarks`,
        { params: { mine: parsedMine.fullName, limit: 3 } },
      )
      setSuggestions(response.data.suggestions)
    } catch (requestError) {
      if (!isRequestAborted(requestError)) {
        setSuggestError(extractErrorMessage(requestError, text.suggestError))
        setSuggestions([])
      }
    } finally {
      setSuggestLoading(false)
    }
  }

  const addSuggestionAsBenchmark = (fullName: string) => {
    if (benchmarkInputs.some((item) => item.toLowerCase() === fullName.toLowerCase())) return
    setBenchmarkInputs((current) => {
      const next = [...current]
      const emptyIndex = next.findIndex((item) => !item.trim())
      if (emptyIndex >= 0) {
        next[emptyIndex] = fullName
        return next
      }
      if (next.length >= 3) return next
      return [...next, fullName]
    })
    setShowSuggestions(false)
  }

  const handleSubmit = () => {
    const parsedMine = parseGitHubRepoInput(mineInput)
    if (parsedMine.kind !== 'repo') {
      setError(text.invalidMine)
      return
    }

    const normalizedBenchmarks = benchmarkInputs
      .map((item) => parseGitHubRepoInput(item))
      .filter((item): item is Extract<ReturnType<typeof parseGitHubRepoInput>, { kind: 'repo' }> => item.kind === 'repo')
      .map((item) => item.fullName)
      .slice(0, 3)

    if (normalizedBenchmarks.length === 0) {
      setError(text.invalidBenchmarks)
      return
    }

    const uniqueBenchmarks = Array.from(new Set(normalizedBenchmarks))
    if (uniqueBenchmarks.length !== normalizedBenchmarks.length || uniqueBenchmarks.includes(parsedMine.fullName)) {
      setError(text.duplicateBenchmarks)
      return
    }

    setError('')
    setSearchParams({
      mine: parsedMine.fullName,
      b: uniqueBenchmarks.join(','),
      ...(includeNarrative ? { n: '1' } : {}),
    })
  }

  const handleRefresh = () => {
    const mine = searchParams.get('mine') ?? ''
    const benchmarks = (searchParams.get('b') ?? '').split(',').filter(Boolean)
    if (!mine || benchmarks.length === 0) return
    setResult(null)
    setSearchParams({
      mine,
      b: benchmarks.join(','),
      ...(searchParams.get('n') === '1' ? { n: '1' } : {}),
      force: Date.now().toString(),
    })
  }

  const orderedProfiles = useMemo<RepoProfile[]>(() => {
    if (!result) return []
    const mine = searchParams.get('mine') ?? ''
    const benchmarks = (searchParams.get('b') ?? '').split(',').filter(Boolean)
    return [mine, ...benchmarks]
      .map((name) => result.profiles[name.toLowerCase()] ?? result.profiles[name])
      .filter((profile): profile is RepoProfile => Boolean(profile))
  }, [result, searchParams])

  const visibleBenchmarkInputs = benchmarkInputs
  const markdown = result ? generateBenchmarkMarkdown(result, language) : ''

  const copyMarkdown = async () => {
    if (!markdown) return
    await navigator.clipboard.writeText(markdown)
    setMarkdownCopied(true)
    window.setTimeout(() => setMarkdownCopied(false), 2000)
  }

  const downloadMarkdown = () => {
    if (!markdown) return
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${(searchParams.get('mine') ?? 'benchmark').replace('/', '-')}-benchmark.md`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">{text.title}</h1>
        <p className="page-subtitle">{text.subtitle}</p>
      </div>

      <CompareModeTabs language={language} />

      <section className="repo-benchmark-hero">
        <div className="repo-benchmark-form repo-benchmark-form-stacked">
          <label className="repo-benchmark-field">
            <span>{text.mineLabel}</span>
            <input
              className="compare-input"
              value={mineInput}
              onChange={(event) => setMineInput(event.target.value)}
              placeholder={text.minePlaceholder}
              autoComplete="off"
              name="mine-repo"
              spellCheck={false}
            />
          </label>

          <div className="repo-benchmark-list">
            {visibleBenchmarkInputs.map((value, index) => (
              <div key={`benchmark-${index}`} className="repo-benchmark-list-item">
                <label className="repo-benchmark-field">
                  <span>{text.benchmarkLabel} {index + 1}</span>
                  <input
                    className="compare-input"
                    value={value}
                    onChange={(event) => updateBenchmarkField(index, event.target.value)}
                    placeholder={text.benchmarkPlaceholder}
                    autoComplete="off"
                    name={`benchmark-repo-${index}`}
                    spellCheck={false}
                  />
                </label>
                {visibleBenchmarkInputs.length > 1 && (
                  <button type="button" className="compare-remove-btn" onClick={() => removeBenchmarkField(index)}>
                    {text.removeBenchmark}
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="repo-benchmark-actions">
            <label className="repo-benchmark-toggle" htmlFor="include-narrative">
              <input
                id="include-narrative"
                type="checkbox"
                checked={includeNarrative}
                onChange={(event) => setIncludeNarrative(event.target.checked)}
              />
              <span>{text.includeNarrative}</span>
            </label>

            <div className="repo-benchmark-buttons">
              <button type="button" className="compare-remove-btn" onClick={addBenchmarkField} disabled={benchmarkInputs.length >= 3}>
                {text.addBenchmark}
              </button>
              <button type="button" className="compare-remove-btn" onClick={handleSuggest} disabled={suggestLoading}>
                {suggestLoading ? text.suggesting : text.suggestBenchmarks}
              </button>
              <button type="button" className="compare-add-btn repo-benchmark-submit" onClick={handleSubmit} disabled={loading}>
                {loading ? text.comparing : text.compare}
              </button>
            </div>
          </div>

          {showSuggestions && (
            <div className="repo-suggestions-panel">
              {suggestLoading && <p className="compare-hint">{text.suggesting}</p>}
              {suggestError && <p className="compare-hint">{suggestError}</p>}
              {!suggestLoading && !suggestError && suggestions.length === 0 && (
                <p className="compare-hint">{text.noSuggestions}</p>
              )}
              {!suggestLoading && suggestions.length > 0 && (
                <ul className="repo-suggestions-list">
                  {suggestions.map((s) => (
                    <li key={s.full_name} className="repo-suggestion-item">
                      <div className="repo-suggestion-info">
                        <strong>{s.full_name}</strong>
                        <span className="compare-tag">{s.reason_code}</span>
                        <span className="compare-hint">★{s.stars.toLocaleString()}</span>
                        <div className="repo-suggestion-copy">
                          <div className="repo-suggestion-tags">
                            {(s.badges ?? []).map((badge) => (
                              <span key={`${s.full_name}-${badge}`} className="compare-tag">
                                {badge}
                              </span>
                            ))}
                          </div>
                          <p className="repo-suggestion-title">{s.reason_title || s.reason_code}</p>
                          <p className="repo-suggestion-summary">
                            <strong>{whyItFitsLabel}:</strong> {s.reason_summary}
                          </p>
                          <p className="repo-suggestion-summary">
                            <strong>{whatToLearnLabel}:</strong> {s.learn_from}
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        className="compare-remove-btn"
                        onClick={() => addSuggestionAsBenchmark(s.full_name)}
                        disabled={
                          (filledBenchmarkCount >= 3 && benchmarkInputs.every((item) => item.trim())) ||
                          benchmarkInputs.some((item) => item.toLowerCase() === s.full_name.toLowerCase())
                        }
                      >
                        {text.addSuggestion}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        {!result && !loading && !error && <p className="compare-hint">{text.empty}</p>}
        {error && (
          <div className="error-state" role="alert">
            <p>{error}</p>
          </div>
        )}
      </section>

      {loading && (
        <div className="loading-state" aria-live="polite">
          <p>{text.comparing}</p>
        </div>
      )}

      {result && (
        <>
          {isStale(result.generated_at) && (
            <div className="repo-stale-warning" role="alert">
              <span>{text.staleWarning}</span>
              <button type="button" className="compare-remove-btn" onClick={handleRefresh}>
                {text.refresh}
              </button>
            </div>
          )}
          <section className="repo-benchmark-summary">
            <article className="repo-summary-card repo-summary-card-primary">
              <span className="compare-insight-kicker">{text.overview}</span>
              <h3>{result.bucket.label}</h3>
              <p>{result.narrative?.summary ?? result.bucket.warning ?? text.empty}</p>
            </article>
            <article className="repo-summary-card">
              <span className="compare-insight-kicker">{text.quickFacts}</span>
              <p>{result.bucket.warning ?? result.narrative?.disclaimer ?? '-'}</p>
              <p>{text.generatedAt}: {formatDate(result.generated_at, language)} · {formatCacheAge(result.generated_at)}</p>
              <div className="repo-benchmark-buttons">
                <button type="button" className="compare-remove-btn" onClick={copyMarkdown}>
                  {markdownCopied ? text.copied : text.copyMarkdown}
                </button>
                <button type="button" className="compare-add-btn" onClick={downloadMarkdown}>
                  {text.downloadMarkdown}
                </button>
              </div>
            </article>
          </section>

          <section className="repo-profile-grid">
            {orderedProfiles.map((profile, index) => (
              <article key={profile.full_name} className={`repo-profile-card${index === 0 ? ' repo-profile-card-mine' : ''}`}>
                <div className="repo-profile-head">
                  <div>
                    <span className="compare-insight-kicker">{index === 0 ? text.statusMine : `${text.benchmarkLabel} ${index}`}</span>
                    <h3>{profile.full_name}</h3>
                  </div>
                  <span className="repo-profile-stars">★{profile.stars.toLocaleString()}</span>
                </div>
                <p>{profile.description || text.noDescription}</p>
                <div className="repo-profile-meta">
                  <span>{profile.language || 'Code'}</span>
                  <span>{text.workflows}: {profile.workflow_file_count}</span>
                  <span>{text.lastUpdated}: {formatDate(profile.pushed_at, language)}</span>
                </div>
                <div className="repo-profile-meta">
                  <span className="repo-profile-fetched-at">{formatCacheAge(profile.fetched_at)}</span>
                </div>
                <div className="repo-profile-tags">
                  {(profile.topics ?? []).slice(0, 6).map((topic) => (
                    <span key={topic} className="compare-tag">
                      {topic}
                    </span>
                  ))}
                </div>
                <div className="repo-profile-flags">
                  <span className={`repo-flag${profile.has_readme ? ' active' : ''}`}>README</span>
                  <span className={`repo-flag${profile.has_license_file ? ' active' : ''}`}>License</span>
                  <span className={`repo-flag${profile.has_quickstart ? ' active' : ''}`}>Quickstart</span>
                  <span className={`repo-flag${profile.has_screenshot ? ' active' : ''}`}>Visual</span>
                </div>
              </article>
            ))}
          </section>

          <section className="compare-chart-section">
            <h3 className="compare-chart-title">{text.matrix}</h3>
            <BenchmarkMatrix
              rows={result.feature_matrix.rows}
              scoreLabel={text.score}
              detailsLabel={text.details}
              emptyLabel={text.noDetails}
            />
          </section>

          <section className="compare-chart-section">
            <h3 className="compare-chart-title">{text.actions}</h3>
            <ActionList
              actions={result.actions}
              language={language}
              labels={{
                sortBy: text.sortBy,
                filterBy: text.filterBy,
                sortPriority: text.sortPriority,
                sortEffort: text.sortEffort,
                sortImpact: text.sortImpact,
                allDimensions: text.allDimensions,
                quickWin: text.quickWin,
                complete: text.markComplete,
                timeline7d: text.timeline7d,
                timeline30d: text.timeline30d,
                timeline90d: text.timeline90d,
                noActions: text.noActions,
              }}
            />
          </section>

          <section className="compare-chart-section">
            <h3 className="compare-chart-title">{text.evidence}</h3>
            <HypothesisCards
              hypotheses={result.hypotheses}
              labels={{
                transferability: text.transferability,
                confidence: text.confidence,
                disclaimer: text.disclaimer,
                filterCategory: text.filterCategory,
                filterTransferability: text.filterTransferability,
                allCategories: text.allCategories,
                allTransferability: text.allTransferability,
                evidence: text.showEvidence,
                noHypotheses: text.noHypotheses,
              }}
            />
          </section>

          {result.narrative && (
            <section className="repo-disclaimer">
              <span className="compare-insight-kicker">{text.disclaimer}</span>
              <p>{result.narrative.disclaimer}</p>
            </section>
          )}
        </>
      )}
    </div>
  )
}
