/**
 * Unit tests for Export page - benchmark integration
 * Task 27.2 - Validates: Requirements 12.1
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { generateBenchmarkMarkdown, type BenchmarkExportReport } from '../utils/benchmarkExport'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function makeMinimalReport(overrides: Partial<BenchmarkExportReport> = {}): BenchmarkExportReport {
  return {
    bucket: { label: 'TypeScript · react', warning: null },
    profiles: {
      'user/mine': {
        full_name: 'user/mine',
        description: 'My repo',
        stars: 50,
        forks: 5,
        language: 'TypeScript',
        topics: ['react'],
        workflow_file_count: 1,
        pushed_at: '2024-01-01T00:00:00Z',
      },
      'org/bench': {
        full_name: 'org/bench',
        description: 'Benchmark repo',
        stars: 5000,
        forks: 500,
        language: 'TypeScript',
        topics: ['react'],
        workflow_file_count: 3,
        pushed_at: '2024-03-01T00:00:00Z',
      },
    },
    feature_matrix: {
      rows: [
        {
          dimension_id: 'first_impression',
          label_key: 'benchmark.dimension.first_impression',
          label: 'First Impression',
          cells: [
            { repo: 'user/mine', level: 'weak', score: 1, raw: {} },
            { repo: 'org/bench', level: 'strong', score: 4, raw: {} },
          ],
        },
      ],
    },
    hypotheses: [
      {
        hypothesis_id: 'h1',
        title: 'Better README drives engagement',
        category: 'positioning',
        evidence: [{ type: 'metric', detail: 'readme_h2_count: 10 vs 2', repo: 'org/bench' }],
        transferability: 'high',
        caveats: ['Author influence not measured'],
        confidence: 'rule_based',
      },
    ],
    actions: [
      {
        action_id: 'a1',
        dimension: 'first_impression',
        title: 'Improve README structure',
        rationale: 'Add more sections',
        effort: 'S',
        impact: 4,
        priority_score: 4.0,
        checklist: ['Add quickstart section', 'Add badges'],
        suggested_deadline: '7d',
      },
    ],
    narrative: null,
    generated_at: '2024-06-01T10:00:00Z',
    llm_calls: 0,
    ...overrides,
  }
}

// ─── Export utility unit tests ────────────────────────────────────────────────

describe('generateBenchmarkMarkdown - export integration (Requirement 12.1)', () => {
  it('generates Markdown with a top-level heading', () => {
    const report = makeMinimalReport()
    const md = generateBenchmarkMarkdown(report, 'en')
    expect(md.startsWith('# Repository Benchmark Report')).toBe(true)
  })

  it('includes all repo names in the output', () => {
    const report = makeMinimalReport()
    const md = generateBenchmarkMarkdown(report, 'en')
    expect(md).toContain('user/mine')
    expect(md).toContain('org/bench')
  })

  it('includes the feature matrix as a Markdown table', () => {
    const report = makeMinimalReport()
    const md = generateBenchmarkMarkdown(report, 'en')
    const lines = md.split('\n')
    const tableLines = lines.filter((l) => l.startsWith('|'))
    expect(tableLines.length).toBeGreaterThan(0)
    // Separator row
    expect(tableLines.some((l) => l.includes('---'))).toBe(true)
    // Dimension label in table
    expect(md).toContain('First Impression')
  })

  it('includes action items as a numbered list', () => {
    const report = makeMinimalReport()
    const md = generateBenchmarkMarkdown(report, 'en')
    expect(md).toContain('1. Improve README structure')
    expect(md).toContain('  - Add quickstart section')
    expect(md).toContain('  - Add badges')
  })

  it('includes hypothesis sections', () => {
    const report = makeMinimalReport()
    const md = generateBenchmarkMarkdown(report, 'en')
    expect(md).toContain('### Better README drives engagement')
  })

  it('includes the generated_at timestamp', () => {
    const report = makeMinimalReport()
    const md = generateBenchmarkMarkdown(report, 'en')
    expect(md).toContain('2024-06-01T10:00:00Z')
  })

  it('does NOT include narrative section when narrative is null', () => {
    const report = makeMinimalReport({ narrative: null })
    const md = generateBenchmarkMarkdown(report, 'en')
    expect(md).not.toContain('## Narrative')
  })

  it('includes narrative section when narrative is present', () => {
    const report = makeMinimalReport({
      narrative: {
        summary: 'Your repo lags in first impression.',
        disclaimer: 'Correlation does not imply causation.',
      },
    })
    const md = generateBenchmarkMarkdown(report, 'en')
    expect(md).toContain('## Narrative')
    expect(md).toContain('Your repo lags in first impression.')
    expect(md).toContain('Correlation does not imply causation.')
  })

  it('generates Chinese Markdown when language is zh', () => {
    const report = makeMinimalReport()
    const md = generateBenchmarkMarkdown(report, 'zh')
    expect(md.startsWith('# 仓库对标报告')).toBe(true)
    expect(md).toContain('## 差距矩阵')
    expect(md).toContain('## 行动项')
  })

  it('includes bucket label in the output', () => {
    const report = makeMinimalReport({
      bucket: { label: 'TypeScript · react', warning: 'Size disparity detected' },
    })
    const md = generateBenchmarkMarkdown(report, 'en')
    expect(md).toContain('TypeScript · react')
    expect(md).toContain('Size disparity detected')
  })

  it('handles empty actions list without errors', () => {
    const report = makeMinimalReport({ actions: [] })
    const md = generateBenchmarkMarkdown(report, 'en')
    expect(md).toContain('## Action Items')
    const numberedItems = md.split('\n').filter((l) => /^\d+\. /.test(l))
    expect(numberedItems.length).toBe(0)
  })

  it('handles empty hypotheses list without errors', () => {
    const report = makeMinimalReport({ hypotheses: [] })
    const md = generateBenchmarkMarkdown(report, 'en')
    expect(md).toContain('## Success Hypotheses')
  })

  it('escapes pipe characters in dimension labels', () => {
    const report = makeMinimalReport({
      feature_matrix: {
        rows: [
          {
            dimension_id: 'test',
            label_key: 'benchmark.dimension.test',
            label: 'A | B',
            cells: [
              { repo: 'user/mine', level: 'weak', score: 1, raw: {} },
              { repo: 'org/bench', level: 'strong', score: 4, raw: {} },
            ],
          },
        ],
      },
    })
    const md = generateBenchmarkMarkdown(report, 'en')
    expect(md).toContain('A \\| B')
  })
})

// ─── Export page benchmark section (UI integration) ──────────────────────────

// Mock axios and AppContext for Export page rendering
vi.mock('axios', async () => {
  const actual = await vi.importActual<typeof import('axios')>('axios')
  return {
    default: {
      ...actual.default,
      post: vi.fn().mockReturnValue(new Promise(() => {})),
      get: vi.fn().mockReturnValue(new Promise(() => {})),
      isAxiosError: actual.default.isAxiosError,
    },
  }
})

vi.mock('../context', () => ({
  useApp: () => ({
    contentLanguage: 'en',
    getGenerateCache: vi.fn().mockReturnValue(null),
    cacheGenerateResult: vi.fn(),
    getResumeProjects: vi.fn().mockReturnValue([]),
  }),
}))

// Lazy import Export after mocks are set up
async function renderExport(url = '/?user=testuser') {
  const { Export } = await import('./Export')
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Export language="en" />
    </MemoryRouter>,
  )
}

describe('Export page - benchmark section (Requirement 12.1)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the Export page loading state when user is provided', async () => {
    const { container } = await renderExport()
    // Should show loading state since axios.post is pending
    expect(container.querySelector('.loading-state')).toBeInTheDocument()
  })

  it('renders the no-user state when no user param is provided', async () => {
    const { Export } = await import('./Export')
    render(
      <MemoryRouter initialEntries={['/']}>
        <Export language="en" />
      </MemoryRouter>,
    )
    expect(screen.getByText('Enter a GitHub username to export')).toBeInTheDocument()
  })
})
