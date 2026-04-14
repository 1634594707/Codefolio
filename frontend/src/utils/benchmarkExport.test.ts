/**
 * Tests for benchmarkExport.ts
 *
 * Task 21.3 - Property 24: Markdown Export Completeness
 *   Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5
 *
 * Task 21.4 - Unit tests for export functionality
 *   Validates: Requirements 12.1, 12.2
 */

import fc from 'fast-check'
import { describe, it, expect } from 'vitest'
import {
  generateBenchmarkMarkdown,
  type BenchmarkExportReport,
  type BenchmarkExportProfile,
  type BenchmarkExportRow,
  type BenchmarkExportAction,
  type BenchmarkExportHypothesis,
} from './benchmarkExport'

// ─── Helpers ────────────────────────────────────────────────────────────────

function makeProfile(fullName: string): BenchmarkExportProfile {
  return {
    full_name: fullName,
    description: `Description for ${fullName}`,
    stars: 100,
    forks: 10,
    language: 'TypeScript',
    topics: ['web', 'react'],
    workflow_file_count: 2,
    pushed_at: '2024-01-01T00:00:00Z',
  }
}

function makeRow(label: string, repos: string[]): BenchmarkExportRow {
  return {
    dimension_id: label.toLowerCase().replace(/\s/g, '_'),
    label_key: `benchmark.dimension.${label}`,
    label,
    cells: repos.map((repo) => ({
      repo,
      level: 'medium',
      score: 2,
      raw: { example: true },
    })),
  }
}

function makeAction(index: number): BenchmarkExportAction {
  return {
    action_id: `a${index}`,
    dimension: 'first_impression',
    title: `Action ${index}`,
    rationale: `Rationale ${index}`,
    effort: 'S',
    impact: 4,
    priority_score: 4.0,
    checklist: [`Step 1 for action ${index}`, `Step 2 for action ${index}`],
    suggested_deadline: '7d',
  }
}

function makeHypothesis(index: number): BenchmarkExportHypothesis {
  return {
    hypothesis_id: `h${index}`,
    title: `Hypothesis ${index}`,
    category: 'positioning',
    evidence: [{ type: 'metric', detail: 'readme_h2_count: 12 vs 3', repo: 'org/repo' }],
    transferability: 'high',
    caveats: ['Author influence not measured'],
    confidence: 'rule_based',
  }
}

function makeReport(overrides: Partial<BenchmarkExportReport> = {}): BenchmarkExportReport {
  const repos = ['user/mine', 'org/benchmark']
  return {
    bucket: { label: 'TypeScript · shared topic: react', warning: null },
    profiles: Object.fromEntries(repos.map((r) => [r, makeProfile(r)])),
    feature_matrix: {
      rows: [
        makeRow('First Impression', repos),
        makeRow('Engineering Quality', repos),
      ],
    },
    hypotheses: [makeHypothesis(1)],
    actions: [makeAction(1), makeAction(2)],
    narrative: null,
    generated_at: '2024-01-15T12:00:00Z',
    llm_calls: 0,
    ...overrides,
  }
}

// ─── Arbitraries ─────────────────────────────────────────────────────────────

const repoNameArb = fc
  .tuple(
    fc.stringMatching(/^[a-zA-Z0-9-]{1,15}$/),
    fc.stringMatching(/^[a-zA-Z0-9-]{1,15}$/),
  )
  .map(([o, r]) => `${o}/${r}`)

const levelArb = fc.constantFrom('missing', 'weak', 'medium', 'strong') as fc.Arbitrary<
  'missing' | 'weak' | 'medium' | 'strong'
>

const effortArb = fc.constantFrom('S', 'M', 'L') as fc.Arbitrary<'S' | 'M' | 'L'>

const reportArb = fc
  .array(repoNameArb, { minLength: 2, maxLength: 4 })
  .chain((repos) => {
    const uniqueRepos = Array.from(new Set(repos))
    if (uniqueRepos.length < 2) return fc.constant(makeReport())

    return fc
      .record({
        rows: fc.array(
          fc.record({
            label: fc.string({ minLength: 1, maxLength: 30 }),
          }),
          { minLength: 1, maxLength: 8 },
        ),
        actions: fc.array(
          fc.record({
            title: fc.string({ minLength: 1, maxLength: 50 }),
            rationale: fc.string({ minLength: 1, maxLength: 100 }),
            effort: effortArb,
            impact: fc.integer({ min: 1, max: 5 }),
            checklist: fc.array(fc.string({ minLength: 1, maxLength: 50 }), { minLength: 1, maxLength: 5 }),
            suggested_deadline: fc.constantFrom('7d', '30d', '90d'),
          }),
          { minLength: 0, maxLength: 5 },
        ),
        hypotheses: fc.array(
          fc.record({
            title: fc.string({ minLength: 1, maxLength: 50 }),
            transferability: fc.constantFrom('high', 'medium', 'low'),
            confidence: fc.constantFrom('rule_based', 'llm_summarized'),
          }),
          { minLength: 0, maxLength: 5 },
        ),
        includeNarrative: fc.boolean(),
        generatedAt: fc
          .integer({ min: new Date('2020-01-01').getTime(), max: new Date('2030-01-01').getTime() })
          .map((ms) => new Date(ms).toISOString()),
      })
      .map(({ rows, actions, hypotheses, includeNarrative, generatedAt }) => {
        const report: BenchmarkExportReport = {
          bucket: { label: 'TypeScript · react', warning: null },
          profiles: Object.fromEntries(uniqueRepos.map((r) => [r, makeProfile(r)])),
          feature_matrix: {
            rows: rows.map((r, i) => ({
              dimension_id: `dim_${i}`,
              label_key: `benchmark.dimension.dim_${i}`,
              label: r.label,
              cells: uniqueRepos.map((repo) => ({
                repo,
                level: 'medium' as const,
                score: 2,
                raw: {},
              })),
            })),
          },
          hypotheses: hypotheses.map((h, i) => ({
            hypothesis_id: `h${i}`,
            title: h.title,
            category: 'positioning',
            evidence: [{ type: 'metric', detail: 'x: 1 vs 2', repo: uniqueRepos[1] }],
            transferability: h.transferability,
            caveats: ['caveat'],
            confidence: h.confidence,
          })),
          actions: actions.map((a, i) => ({
            action_id: `a${i}`,
            dimension: 'first_impression',
            title: a.title,
            rationale: a.rationale,
            effort: a.effort,
            impact: a.impact,
            priority_score: a.impact / ({ S: 1, M: 2, L: 3 }[a.effort] ?? 1),
            checklist: a.checklist,
            suggested_deadline: a.suggested_deadline,
          })),
          narrative: includeNarrative
            ? { summary: 'Summary text', disclaimer: 'Disclaimer text' }
            : null,
          generated_at: generatedAt,
          llm_calls: includeNarrative ? 1 : 0,
        }
        return report
      })
  })

// ─── Property 24: Markdown Export Completeness ───────────────────────────────

describe('Property 24: Markdown Export Completeness', () => {
  it('exported Markdown contains Feature_Matrix as a table', () => {
    /**
     * Feature: repo-benchmark, Property 24
     * Validates: Requirements 12.3
     */
    fc.assert(
      fc.property(reportArb, (report) => {
        const md = generateBenchmarkMarkdown(report, 'en')
        // A Markdown table has rows starting with |
        const tableLines = md.split('\n').filter((l) => l.startsWith('|'))
        expect(tableLines.length).toBeGreaterThan(0)
        // Header separator row must exist (| --- | ... |)
        const separatorLines = tableLines.filter((l) => l.includes('---'))
        expect(separatorLines.length).toBeGreaterThan(0)
      }),
      { numRuns: 100 },
    )
  })

  it('exported Markdown contains Action_Items as a numbered list', () => {
    /**
     * Feature: repo-benchmark, Property 24
     * Validates: Requirements 12.4
     */
    fc.assert(
      fc.property(
        reportArb.filter((r) => r.actions.length > 0),
        (report) => {
          const md = generateBenchmarkMarkdown(report, 'en')
          // Numbered list items start with "1. ", "2. ", etc.
          const numberedItems = md.split('\n').filter((l) => /^\d+\. /.test(l))
          expect(numberedItems.length).toBe(report.actions.length)
        },
      ),
      { numRuns: 100 },
    )
  })

  it('exported Markdown contains Success_Hypothesis cards as sections', () => {
    /**
     * Feature: repo-benchmark, Property 24
     * Validates: Requirements 12.5
     */
    fc.assert(
      fc.property(
        reportArb.filter((r) => r.hypotheses.length > 0),
        (report) => {
          const md = generateBenchmarkMarkdown(report, 'en')
          // Each hypothesis title appears as a ### heading
          for (const hypothesis of report.hypotheses) {
            expect(md).toContain(`### ${hypothesis.title}`)
          }
        },
      ),
      { numRuns: 100 },
    )
  })

  it('exported Markdown contains the generated_at timestamp', () => {
    /**
     * Feature: repo-benchmark, Property 24
     * Validates: Requirements 12.2
     */
    fc.assert(
      fc.property(reportArb, (report) => {
        const md = generateBenchmarkMarkdown(report, 'en')
        expect(md).toContain(report.generated_at)
      }),
      { numRuns: 100 },
    )
  })

  it('exported Markdown contains narrative when present', () => {
    /**
     * Feature: repo-benchmark, Property 24
     * Validates: Requirements 12.1
     */
    fc.assert(
      fc.property(
        reportArb.filter((r) => r.narrative !== null),
        (report) => {
          const md = generateBenchmarkMarkdown(report, 'en')
          expect(md).toContain(report.narrative!.summary)
          expect(md).toContain(report.narrative!.disclaimer)
        },
      ),
      { numRuns: 100 },
    )
  })

  it('exported Markdown starts with a top-level heading', () => {
    /**
     * Feature: repo-benchmark, Property 24
     * Validates: Requirements 12.1
     */
    fc.assert(
      fc.property(reportArb, (report) => {
        const md = generateBenchmarkMarkdown(report, 'en')
        expect(md.startsWith('# ')).toBe(true)
      }),
      { numRuns: 100 },
    )
  })
})

// ─── Unit Tests: Export Functionality (Task 21.4) ────────────────────────────

describe('Unit tests: generateBenchmarkMarkdown', () => {
  it('generates valid Markdown with all required sections for English', () => {
    const report = makeReport()
    const md = generateBenchmarkMarkdown(report, 'en')

    expect(md).toContain('# Repository Benchmark Report')
    expect(md).toContain('## Gap Matrix')
    expect(md).toContain('## Action Items')
    expect(md).toContain('## Success Hypotheses')
    expect(md).toContain('2024-01-15T12:00:00Z')
  })

  it('generates valid Markdown with all required sections for Chinese', () => {
    const report = makeReport()
    const md = generateBenchmarkMarkdown(report, 'zh')

    expect(md).toContain('# 仓库对标报告')
    expect(md).toContain('## 差距矩阵')
    expect(md).toContain('## 行动项')
    expect(md).toContain('## 成功假设')
    expect(md).toContain('2024-01-15T12:00:00Z')
  })

  it('includes narrative summary and disclaimer when narrative is present', () => {
    const report = makeReport({
      narrative: {
        summary: 'The benchmark repository excels in first impression.',
        disclaimer: 'Correlation does not imply causation.',
      },
    })
    const md = generateBenchmarkMarkdown(report, 'en')

    expect(md).toContain('The benchmark repository excels in first impression.')
    expect(md).toContain('Correlation does not imply causation.')
    expect(md).toContain('## Narrative')
  })

  it('does not include narrative section when narrative is null', () => {
    const report = makeReport({ narrative: null })
    const md = generateBenchmarkMarkdown(report, 'en')

    expect(md).not.toContain('## Narrative')
    expect(md).not.toContain('## 叙述总结')
  })

  it('formats Feature_Matrix as a Markdown table with correct columns', () => {
    const repos = ['user/mine', 'org/benchmark']
    const report = makeReport()
    const md = generateBenchmarkMarkdown(report, 'en')

    // Header row should contain repo names
    expect(md).toContain('user/mine')
    expect(md).toContain('org/benchmark')

    // Table separator row
    const lines = md.split('\n')
    const separatorLine = lines.find((l) => l.includes('---'))
    expect(separatorLine).toBeDefined()
  })

  it('formats Action_Items as a numbered list with checklists', () => {
    const report = makeReport()
    const md = generateBenchmarkMarkdown(report, 'en')

    expect(md).toContain('1. Action 1')
    expect(md).toContain('2. Action 2')
    expect(md).toContain('  - Step 1 for action 1')
    expect(md).toContain('  - Step 2 for action 1')
  })

  it('includes bucket label in the output', () => {
    const report = makeReport({
      bucket: { label: 'TypeScript · shared topic: react', warning: 'Size disparity warning' },
    })
    const md = generateBenchmarkMarkdown(report, 'en')

    expect(md).toContain('TypeScript · shared topic: react')
    expect(md).toContain('Size disparity warning')
  })

  it('escapes pipe characters in cell values to avoid breaking Markdown tables', () => {
    const repos = ['user/mine', 'org/benchmark']
    const report = makeReport({
      feature_matrix: {
        rows: [
          {
            dimension_id: 'test',
            label_key: 'benchmark.dimension.test',
            label: 'Test | Dimension',
            cells: repos.map((repo) => ({
              repo,
              level: 'medium' as const,
              score: 2,
              raw: {},
            })),
          },
        ],
      },
    })
    const md = generateBenchmarkMarkdown(report, 'en')

    // Pipe in label should be escaped
    expect(md).toContain('Test \\| Dimension')
  })

  it('handles empty actions list gracefully', () => {
    const report = makeReport({ actions: [] })
    const md = generateBenchmarkMarkdown(report, 'en')

    expect(md).toContain('## Action Items')
    // No numbered items
    const numberedItems = md.split('\n').filter((l) => /^\d+\. /.test(l))
    expect(numberedItems.length).toBe(0)
  })

  it('handles empty hypotheses list gracefully', () => {
    const report = makeReport({ hypotheses: [] })
    const md = generateBenchmarkMarkdown(report, 'en')

    expect(md).toContain('## Success Hypotheses')
  })

  it('includes profile information for each repository', () => {
    const report = makeReport()
    const md = generateBenchmarkMarkdown(report, 'en')

    expect(md).toContain('### user/mine')
    expect(md).toContain('### org/benchmark')
    expect(md).toContain('## Profiles')
  })
})
