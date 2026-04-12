import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import axios from 'axios'
import { isRequestAborted } from '../utils/axiosAbort'
import { parseGitHubRepoInput } from '../utils/githubInput'
import { generateBenchmarkMarkdown } from '../utils/benchmarkExport'

interface CompareReposProps {
  language: 'en' | 'zh'
}

interface RepoProfile {
  full_name: string
  description: string | null
  stars: number
  forks: number
  language: string | null
  topics: string[]
  license: string | null
  default_branch: string | null
  created_at: string | null
  pushed_at: string | null
  has_readme: boolean
  readme_sections: string[]
  has_license_file: boolean
  workflow_file_count: number
  has_contributing: boolean
  has_code_of_conduct: boolean
  has_security_policy: boolean
  has_issue_templates: boolean
  has_screenshot: boolean
  has_quickstart: boolean
  has_examples_dir: boolean
  has_docs_dir: boolean
  homepage: string | null
  open_issues_count: number
  fetched_at: string
}

interface FeatureCell {
  repo: string
  level: 'missing' | 'weak' | 'medium' | 'strong'
  score: number
  raw: Record<string, boolean | number | string>
}

interface FeatureRow {
  dimension_id: string
  label_key: string
  label: string
  cells: FeatureCell[]
}

interface Hypothesis {
  hypothesis_id: string
  title: string
  category: string
  evidence: Array<{
    type: string
    detail: string
    repo: string
  }>
  transferability: 'high' | 'medium' | 'low'
  caveats: string[]
  confidence: string
}

interface ActionItem {
  action_id: string
  dimension: string
  title: string
  rationale: string
  effort: 'S' | 'M' | 'L'
  impact: number
  priority_score: number
  checklist: string[]
  suggested_deadline: string
}

interface BenchmarkResponse {
  bucket: {
    label: string
    warning: string | null
  }
  profiles: Record<string, RepoProfile>
  feature_matrix: {
    rows: FeatureRow[]
  }
  hypotheses: Hypothesis[]
  actions: ActionItem[]
  narrative: {
    summary: string
    disclaimer: string
  } | null
  generated_at: string
  llm_calls: number
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const labels = {
  en: {
    title: 'Benchmark Repositories',
    subtitle: 'Compare one repository against stronger peers and turn visible gaps into action.',
    tabsUsers: 'Developers',
    tabsRepos: 'Repositories',
    mineLabel: 'My repository',
    benchmarkLabel: 'Benchmark repository',
    minePlaceholder: 'owner/repo',
    benchmarkPlaceholder: 'owner/repo',
    addBenchmark: 'Add benchmark',
    removeBenchmark: 'Remove',
    compare: 'Generate benchmark',
    comparing: 'Benchmarking...',
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
  },
  zh: {
    title: '仓库对标',
    subtitle: '把你的仓库与更强的标杆仓库放在一起比较，并直接生成改进动作。',
    tabsUsers: '开发者',
    tabsRepos: '仓库',
    mineLabel: '我的仓库',
    benchmarkLabel: '标杆仓库',
    minePlaceholder: 'owner/repo',
    benchmarkPlaceholder: 'owner/repo',
    addBenchmark: '添加标杆',
    removeBenchmark: '移除',
    compare: '生成对标',
    comparing: '对标中...',
    includeNarrative: '包含叙述总结',
    empty: '先输入一个你想提升的仓库，再添加最多 3 个标杆仓库。',
    invalidMine: '请输入有效的 GitHub 仓库，格式如 owner/repo。',
    invalidBenchmarks: '请至少填写一个有效的标杆仓库。',
    duplicateBenchmarks: '标杆仓库必须唯一，且不能与我的仓库相同。',
    loadError: '仓库对标生成失败。',
    overview: '概览',
    matrix: '差距矩阵',
    actions: '行动项',
    evidence: '这些仓库为什么更突出',
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
  },
} as const

function CompareModeTabs({ language }: CompareReposProps) {
  const text = labels[language]

  return (
    <div className="compare-mode-tabs" role="tablist" aria-label={text.title}>
      <Link to="/compare/users" className="compare-mode-tab">
        {text.tabsUsers}
      </Link>
      <Link to="/compare/repos" className="compare-mode-tab compare-mode-tab-active">
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

function levelClass(level: FeatureCell['level']): string {
  if (level === 'strong') return 'compare-level-strong'
  if (level === 'medium') return 'compare-level-medium'
  if (level === 'weak') return 'compare-level-weak'
  return 'compare-level-missing'
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) return fallback
  const detail = error.response?.data?.detail
  if (typeof detail?.message === 'string' && detail.message) return detail.message
  return fallback
}

export function CompareRepos({ language }: CompareReposProps) {
  const [searchParams, setSearchParams] = useSearchParams()
  const text = labels[language]
  const [mineInput, setMineInput] = useState(searchParams.get('mine') ?? '')
  const [benchmarkInputs, setBenchmarkInputs] = useState<string[]>(
    (searchParams.get('b') ?? '').split(',').filter(Boolean).slice(0, 3),
  )
  const [includeNarrative, setIncludeNarrative] = useState(searchParams.get('n') === '1')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<BenchmarkResponse | null>(null)
  const [markdownCopied, setMarkdownCopied] = useState(false)

  useEffect(() => {
    setMineInput(searchParams.get('mine') ?? '')
    setBenchmarkInputs((searchParams.get('b') ?? '').split(',').filter(Boolean).slice(0, 3))
    setIncludeNarrative(searchParams.get('n') === '1')
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
        if (!cancelled) setResult(response.data)
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
    setBenchmarkInputs((current) => (current.length >= 3 ? current : [...current, '']))
  }

  const updateBenchmarkField = (index: number, value: string) => {
    setBenchmarkInputs((current) => current.map((item, itemIndex) => (itemIndex === index ? value : item)))
  }

  const removeBenchmarkField = (index: number) => {
    setBenchmarkInputs((current) => current.filter((_, itemIndex) => itemIndex !== index))
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

  const orderedProfiles = useMemo(() => {
    if (!result) return []
    const mine = searchParams.get('mine') ?? ''
    const benchmarks = (searchParams.get('b') ?? '').split(',').filter(Boolean)
    return [mine, ...benchmarks].map((name) => result.profiles[name.toLowerCase()] ?? result.profiles[name]).filter(Boolean)
  }, [result, searchParams])

  const visibleBenchmarkInputs = benchmarkInputs.length > 0 ? benchmarkInputs : ['']
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
            <label className="repo-benchmark-toggle">
              <input type="checkbox" checked={includeNarrative} onChange={(event) => setIncludeNarrative(event.target.checked)} />
              <span>{text.includeNarrative}</span>
            </label>

            <div className="repo-benchmark-buttons">
              <button type="button" className="compare-remove-btn" onClick={addBenchmarkField} disabled={benchmarkInputs.length >= 3}>
                {text.addBenchmark}
              </button>
              <button type="button" className="compare-add-btn repo-benchmark-submit" onClick={handleSubmit} disabled={loading}>
                {loading ? text.comparing : text.compare}
              </button>
            </div>
          </div>
        </div>

        {!result && !loading && !error && <p className="compare-hint">{text.empty}</p>}
        {error && (
          <div className="error-state">
            <p>{error}</p>
          </div>
        )}
      </section>

      {loading && (
        <div className="loading-state">
          <p>{text.comparing}</p>
        </div>
      )}

      {result && (
        <>
          <section className="repo-benchmark-summary">
            <article className="repo-summary-card repo-summary-card-primary">
              <span className="compare-insight-kicker">{text.overview}</span>
              <h3>{result.bucket.label}</h3>
              <p>{result.narrative?.summary ?? result.bucket.warning ?? text.empty}</p>
            </article>
            <article className="repo-summary-card">
              <span className="compare-insight-kicker">{text.quickFacts}</span>
              <p>{result.bucket.warning ?? result.narrative?.disclaimer ?? '-'}</p>
              <p>{text.generatedAt}: {formatDate(result.generated_at, language)}</p>
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
                  <span className="repo-profile-stars">★ {profile.stars.toLocaleString()}</span>
                </div>
                <p>{profile.description || text.noDescription}</p>
                <div className="repo-profile-meta">
                  <span>{profile.language || 'Code'}</span>
                  <span>{text.workflows}: {profile.workflow_file_count}</span>
                  <span>{text.lastUpdated}: {formatDate(profile.pushed_at, language)}</span>
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
            <div className="repo-matrix">
              {result.feature_matrix.rows.map((row) => (
                <div key={row.dimension_id} className="repo-matrix-row">
                  <div className="repo-matrix-label">{row.label}</div>
                  <div className="repo-matrix-cells">
                    {row.cells.map((cell) => (
                      <div key={`${row.dimension_id}-${cell.repo}`} className={`repo-matrix-cell ${levelClass(cell.level)}`}>
                        <strong>{cell.repo}</strong>
                        <span>{text.score}: {cell.score}</span>
                        <span>{cell.level}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="compare-chart-section">
            <h3 className="compare-chart-title">{text.actions}</h3>
            <div className="repo-actions-grid">
              {result.actions.map((action) => (
                <article key={action.action_id} className="repo-action-card">
                  <div className="repo-action-head">
                    <h4>{action.title}</h4>
                    <span>{action.effort} / {action.impact}</span>
                  </div>
                  <p>{action.rationale}</p>
                  <div className="repo-profile-flags">
                    {action.effort === 'S' && action.impact >= 4 && <span className="repo-flag active">{text.quickWin}</span>}
                    <span className="repo-flag">{action.suggested_deadline}</span>
                  </div>
                  <div className="repo-action-checks">
                    {action.checklist.map((item) => (
                      <span key={item} className="repo-check-item">
                        {item}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="compare-chart-section">
            <h3 className="compare-chart-title">{text.evidence}</h3>
            <div className="repo-hypothesis-grid">
              {result.hypotheses.map((hypothesis) => (
                <article key={hypothesis.hypothesis_id} className="repo-hypothesis-card">
                  <h4>{hypothesis.title}</h4>
                  <div className="repo-profile-flags">
                    <span className="repo-flag">{text.transferability}: {hypothesis.transferability}</span>
                    <span className="repo-flag">{text.confidence}: {hypothesis.confidence}</span>
                  </div>
                  <div className="repo-evidence-list">
                    {hypothesis.evidence.map((evidence) => (
                      <div key={`${hypothesis.hypothesis_id}-${evidence.repo}-${evidence.detail}`} className="repo-evidence-item">
                        <strong>{evidence.repo}</strong>
                        <span>{evidence.detail}</span>
                      </div>
                    ))}
                  </div>
                  {hypothesis.caveats.length > 0 && (
                    <div className="repo-evidence-list">
                      {hypothesis.caveats.map((caveat) => (
                        <div key={caveat} className="repo-evidence-item">
                          <strong>{text.disclaimer}</strong>
                          <span>{caveat}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </article>
              ))}
            </div>
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
