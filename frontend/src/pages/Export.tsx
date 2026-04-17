import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import axios from 'axios'
import { useApp } from '../context'
import { isRequestAborted } from '../utils/axiosAbort'
import type { GenerateResponse, LocalizedOutput as FullLocalizedOutput } from '../types/generate'
import type { BenchmarkResponse } from '../types/benchmark'
import { generateBenchmarkMarkdown } from '../utils/benchmarkExport'
import { sanitizeHtml } from '../utils/exportSanitizer'
import { API_BASE_URL } from '../config/api'

interface ExportProps {
  language: 'en' | 'zh'
}

const labels = {
  en: {
    title: 'Export',
    subtitle: 'Download your profile assets',
    pdfTitle: 'PDF Resume',
    pdfDesc: 'Download a professionally formatted PDF resume',
    cardTitle: 'Social Card',
    cardDesc: 'Generate a shareable image for social media',
    downloadPdf: 'Download PDF',
    downloadCard: 'Download Card',
    markdownTitle: 'Markdown',
    markdownDesc: 'Copy resume in Markdown format',
    copyMarkdown: 'Copy Markdown',
    markdownCopied: 'Markdown Copied!',
    loading: 'Loading…',
    error: 'Failed to load data',
    noUser: 'Enter a GitHub username to export',
    preview: 'Preview',
    benchmarkTitle: 'Repository Benchmark',
    benchmarkDesc: 'Append a benchmark report to your export',
    includeBenchmark: 'Include benchmark report',
    benchmarkLoading: 'Loading benchmark…',
    benchmarkError: 'Failed to load benchmark report',
    benchmarkNone: 'No benchmark available. Run a comparison on the Repositories tab first.',
  },
  zh: {
    title: '导出',
    subtitle: '下载你的个人资料',
    pdfTitle: 'PDF 简历',
    pdfDesc: '下载专业格式的 PDF 简历',
    cardTitle: '社交卡片',
    cardDesc: '生成可分享到社交媒体的图片',
    downloadPdf: '下载 PDF',
    downloadCard: '下载卡片',
    markdownTitle: 'Markdown',
    markdownDesc: '复制 Markdown 格式简历',
    copyMarkdown: '复制 Markdown',
    markdownCopied: 'Markdown 已复制!',
    loading: '加载中…',
    error: '加载数据失败',
    noUser: '输入 GitHub 用户名以导出',
    preview: '预览',
    benchmarkTitle: '仓库对标',
    benchmarkDesc: '将对标报告附加到导出内容',
    includeBenchmark: '包含对标报告',
    benchmarkLoading: '加载对标报告中…',
    benchmarkError: '加载对标报告失败',
    benchmarkNone: '暂无对标报告。请先在仓库页面运行对标分析。',
  },
}

function applyInlineMarkdown(text: string): string {
  return text
    .replace(
      /\[([^\]]+)\]\(([^)\s]+)\)/gim,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
    )
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/`([^`]+)`/gim, '<code>$1</code>')
}

/** Line-based conversion so each list becomes its own <ul> (avoids one giant <ul> for the whole doc). */
function markdownToHtml(markdown: string): string {
  const lines = markdown.split(/\r?\n/)
  const parts: string[] = []
  let listOpen = false

  const closeList = () => {
    if (listOpen) {
      parts.push('</ul>')
      listOpen = false
    }
  }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd()
    const trimmed = line.trim()
    if (trimmed === '') {
      closeList()
      continue
    }
    if (/^---+$/.test(trimmed)) {
      closeList()
      parts.push('<hr />')
      continue
    }
    if (line.startsWith('### ')) {
      closeList()
      parts.push(`<h3>${applyInlineMarkdown(line.slice(4))}</h3>`)
      continue
    }
    if (line.startsWith('## ')) {
      closeList()
      parts.push(`<h2>${applyInlineMarkdown(line.slice(3))}</h2>`)
      continue
    }
    if (line.startsWith('# ')) {
      closeList()
      parts.push(`<h1>${applyInlineMarkdown(line.slice(2))}</h1>`)
      continue
    }
    if (line.startsWith('- ')) {
      if (!listOpen) {
        parts.push('<ul>')
        listOpen = true
      }
      parts.push(`<li>${applyInlineMarkdown(line.slice(2))}</li>`)
      continue
    }
    closeList()
    parts.push(`<p>${applyInlineMarkdown(line)}</p>`)
  }
  closeList()
  return parts.join('')
}

export function Export({ language }: ExportProps) {
  const {
    contentLanguage,
    getGenerateCache,
    cacheGenerateResult,
    getResumeProjects,
    getLatestBenchmarkWorkspaceEntryForUser,
  } = useApp()
  const [searchParams] = useSearchParams()
  const username = searchParams.get('user') || ''
  const [data, setData] = useState<GenerateResponse | null>(null)
  const [activeOutput, setActiveOutput] = useState<FullLocalizedOutput | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [markdownCopied, setMarkdownCopied] = useState(false)
  const [safeHtml, setSafeHtml] = useState('')
  const [exportingPdf, setExportingPdf] = useState(false)
  const [pdfError, setPdfError] = useState('')
  const [exportingCard, setExportingCard] = useState(false)
  const [includeBenchmark, setIncludeBenchmark] = useState(false)
  const [benchmarkResult, setBenchmarkResult] = useState<BenchmarkResponse | null>(null)
  const [benchmarkLoading, setBenchmarkLoading] = useState(false)
  const [benchmarkError, setBenchmarkError] = useState('')
  const resumeRef = useRef<HTMLDivElement>(null)
  const cardRef = useRef<HTMLDivElement>(null)
  const text = labels[language]
  const selectedProjects = getResumeProjects(username)
  const savedBenchmarkEntry = username ? getLatestBenchmarkWorkspaceEntryForUser(username) : null

  useEffect(() => {
    if (!username) return

    const cachedEntry = getGenerateCache(username, contentLanguage)
    if (cachedEntry) {
      const d = cachedEntry.data
      setData(d)
      setActiveOutput(d.localized_outputs[contentLanguage] || null)
      setLoading(false)
      setError('')
      return
    }

    let cancelled = false
    const abortController = new AbortController()

    const fetchData = async () => {
      setLoading(true)
      setError('')
      setData(null)
      setActiveOutput(null)
      try {
        const response = await axios.post<GenerateResponse>(
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
        setData(response.data)
        setActiveOutput(response.data.localized_outputs[contentLanguage] || null)
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

  // Fetch benchmark report when user opts in, using mine/b URL params
  useEffect(() => {
    const mine = searchParams.get('mine') ?? ''
    const benchmarks = (searchParams.get('b') ?? '').split(',').filter(Boolean)
    if (!includeBenchmark) {
      setBenchmarkResult(null)
      setBenchmarkError('')
      return
    }
    if (!mine || benchmarks.length === 0) {
      setBenchmarkResult(savedBenchmarkEntry?.result ?? null)
      setBenchmarkError('')
      return
    }

    let cancelled = false
    const abortController = new AbortController()

    const fetchBenchmark = async () => {
      setBenchmarkLoading(true)
      setBenchmarkError('')
      try {
        const response = await axios.post<BenchmarkResponse>(
          `${API_BASE_URL}/api/repos/benchmark`,
          {
            mine,
            benchmarks,
            language: contentLanguage,
            options: { include_narrative: false, max_readme_chars_per_repo: 12000 },
          },
          { signal: abortController.signal },
        )
        if (!cancelled) setBenchmarkResult(response.data)
      } catch (err) {
        if (isRequestAborted(err) || cancelled) return
        if (!cancelled) setBenchmarkError(text.benchmarkError)
      } finally {
        if (!cancelled) setBenchmarkLoading(false)
      }
    }

    void fetchBenchmark()
    return () => {
      cancelled = true
      abortController.abort()
    }
  }, [includeBenchmark, searchParams, contentLanguage, text.benchmarkError, savedBenchmarkEntry])

  const selectedProjectsMarkdown =
    selectedProjects.length > 0
      ? `\n\n## ${language === 'zh' ? '精选项目' : 'Selected Projects'}\n\n${selectedProjects
          .map(
            (project) =>
              `### ${project.repoName}\n- ${project.analysisSummary}\n- ${project.highlights.join('\n- ')}\n- ${language === 'zh' ? '项目地址' : 'Project URL'}: ${project.url}`,
          )
          .join('\n\n')}`
      : ''

  const benchmarkMarkdown =
    includeBenchmark && benchmarkResult
      ? `\n\n---\n\n${generateBenchmarkMarkdown(benchmarkResult, language)}`
      : ''

  const resumeMarkdown = `${activeOutput?.resume_markdown ?? ''}${selectedProjectsMarkdown}${benchmarkMarkdown}`
  const resumeHtml = markdownToHtml(resumeMarkdown)

  useEffect(() => {
    void sanitizeHtml(resumeHtml).then(setSafeHtml)
  }, [resumeHtml])

  const exportPdf = async () => {
    if (!data) return

    setExportingPdf(true)
    setPdfError('')

    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/export/pdf`,
        {
          username,
          language: contentLanguage,
          extra_markdown: selectedProjectsMarkdown || undefined,
        },
        { responseType: 'blob' },
      )

      const url = URL.createObjectURL(response.data as Blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `codefolio-${username}-${contentLanguage}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (err) {
      if (!isRequestAborted(err)) {
        setPdfError(language === 'zh' ? 'PDF 导出失败，请重试' : 'PDF export failed, please try again')
      }
    } finally {
      setExportingPdf(false)
    }
  }

  const downloadCard = async () => {
    if (!cardRef.current || !activeOutput) return

    const source = cardRef.current
    const rect = source.getBoundingClientRect()
    const clone = source.cloneNode(true) as HTMLDivElement
    clone.classList.add('is-exporting')
    clone.style.position = 'fixed'
    clone.style.left = '-9999px'
    clone.style.width = `${rect.width}px`
    document.body.appendChild(clone)
    setExportingCard(true)

    try {
      await document.fonts.ready
      const { default: html2canvas } = await import('html2canvas')
      const canvas = await html2canvas(clone, {
        backgroundColor: getComputedStyle(clone).backgroundColor,
        scale: 2,
        useCORS: true,
        logging: false,
      })

      const link = document.createElement('a')
      link.download = `codefolio-${activeOutput.card_data.username}-${contentLanguage}.png`
      link.href = canvas.toDataURL('image/png')
      link.click()
    } finally {
      setExportingCard(false)
      document.body.removeChild(clone)
    }
  }

  const copyMarkdown = () => {
    if (resumeMarkdown) {
      navigator.clipboard.writeText(resumeMarkdown)
      setMarkdownCopied(true)
      setTimeout(() => setMarkdownCopied(false), 2000)
    }
  }

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

  if (error || !data || !activeOutput) {
    return (
      <div className="page-container">
        <div className="error-state">
          <p>{error || text.error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">{text.title}</h1>
        <p className="page-subtitle">{text.subtitle}</p>
      </div>

      <div className="export-grid">
        <div className="export-card">
          <div className="export-icon pdf-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </div>
          <h3 className="export-title">{text.pdfTitle}</h3>
          <p className="export-desc">{text.pdfDesc}</p>
          <button type="button" className="export-btn primary" onClick={exportPdf} disabled={exportingPdf}>
            {exportingPdf ? text.loading : text.downloadPdf}
          </button>
          {pdfError && (
            <div style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
              <p style={{ color: 'var(--color-error, #ef4444)', marginBottom: '0.25rem' }}>{pdfError}</p>
              <button
                type="button"
                className="export-btn secondary"
                style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem' }}
                onClick={() => { setPdfError(''); void exportPdf() }}
              >
                {language === 'zh' ? '重试' : 'Retry'}
              </button>
            </div>
          )}
        </div>

        <div className="export-card">
          <div className="export-icon card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
          </div>
          <h3 className="export-title">{text.cardTitle}</h3>
          <p className="export-desc">{text.cardDesc}</p>
          <button type="button" className="export-btn primary" onClick={downloadCard}>
            {exportingCard ? text.loading : text.downloadCard}
          </button>
        </div>

        <div className="export-card">
          <div className="export-icon markdown-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <line x1="10" y1="9" x2="8" y2="9" />
            </svg>
          </div>
          <h3 className="export-title">{text.markdownTitle}</h3>
          <p className="export-desc">{text.markdownDesc}</p>
          <button type="button" className="export-btn secondary" onClick={copyMarkdown}>
            {markdownCopied ? text.markdownCopied : text.copyMarkdown}
          </button>
        </div>
      </div>

      <div className="export-card" style={{ marginBottom: '1.5rem' }}>
        <div className="export-icon markdown-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <line x1="3" y1="9" x2="21" y2="9" />
            <line x1="9" y1="21" x2="9" y2="9" />
          </svg>
        </div>
        <h3 className="export-title">{text.benchmarkTitle}</h3>
        <p className="export-desc">{text.benchmarkDesc}</p>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginTop: '0.5rem' }}>
          <input
            type="checkbox"
            checked={includeBenchmark}
            onChange={(e) => setIncludeBenchmark(e.target.checked)}
          />
          <span>{text.includeBenchmark}</span>
        </label>
        {includeBenchmark && (
          <div style={{ marginTop: '0.5rem', fontSize: '0.875rem' }} aria-live="polite">
            {benchmarkLoading && <p>{text.benchmarkLoading}</p>}
            {benchmarkError && <p style={{ color: 'var(--color-error, #ef4444)' }}>{benchmarkError}</p>}
            {!benchmarkLoading && !benchmarkError && !benchmarkResult && (
              <p style={{ opacity: 0.7 }}>{text.benchmarkNone}</p>
            )}
            {benchmarkResult && (
              <p style={{ opacity: 0.7 }}>
                {Object.keys(benchmarkResult.profiles).join(' vs ')}
              </p>
            )}
          </div>
        )}
      </div>

      <div className="preview-section">
        <h2 className="preview-title">{text.preview}</h2>

        <div className="preview-card">
          <div className="markdown-frame" ref={resumeRef}>
            <div className="markdown-paper">
              <article
                className="markdown-preview"
                dangerouslySetInnerHTML={{ __html: safeHtml }}
              />
            </div>
          </div>
        </div>

        <div className="preview-card">
          <div className="social-card-preview" ref={cardRef}>
            <div className="social-card-content">
              <div className="social-card-header">
                <img
                  src={activeOutput.card_data.avatar_url}
                  alt={activeOutput.card_data.username}
                  className="social-card-avatar"
                  width={64}
                  height={64}
                />
                <div className="social-card-info">
                  <h3>@{activeOutput.card_data.username}</h3>
                  <p>Codefolio Developer</p>
                </div>
                <div className="social-card-score">
                  <span className="score-value">{activeOutput.card_data.gitscore.toFixed(0)}</span>
                  <span className="score-label">GitScore</span>
                </div>
              </div>
              <div className="social-card-tags">
                {[...activeOutput.card_data.style_tags.slice(0, 2), ...selectedProjects.flatMap((project) => project.keywords).slice(0, 2)].map((tag) => (
                  <span key={tag} className="social-tag">
                    {tag}
                  </span>
                ))}
              </div>
              {activeOutput.card_data.roast_comment && (
                <p className="social-card-quote">"{activeOutput.card_data.roast_comment}"</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
