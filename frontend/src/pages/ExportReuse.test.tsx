import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import axios from 'axios'
import { Export } from './Export'

const appContextValue = {
  contentLanguage: 'en' as const,
  getGenerateCache: vi.fn(),
  cacheGenerateResult: vi.fn(),
  getResumeProjects: vi.fn(),
  getLatestBenchmarkWorkspaceEntryForUser: vi.fn(),
}

vi.mock('../context', () => ({
  useApp: () => appContextValue,
}))

vi.mock('axios', async () => {
  const actual = await vi.importActual<typeof import('axios')>('axios')
  return {
    default: {
      ...actual.default,
      post: vi.fn(),
      get: vi.fn(),
      isAxiosError: actual.default.isAxiosError,
    },
  }
})

describe('Export PDF reuse flow', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    appContextValue.getResumeProjects.mockReturnValue([
      {
        user: 'octocat',
        repoName: 'hello-world',
        description: 'A sample repository',
        language: 'TypeScript',
        stars: 42,
        forks: 7,
        url: 'https://github.com/octocat/hello-world',
        analysisTitle: 'Resume-ready project',
        analysisSummary: 'Strong enough to pin on the resume.',
        highlights: ['Clear README', 'Healthy activity'],
        keywords: ['TypeScript'],
      },
    ])
    appContextValue.getLatestBenchmarkWorkspaceEntryForUser.mockReturnValue({
      username: 'octocat',
      mine: 'octocat/hello-world',
      benchmarks: ['org/bench'],
      language: 'en',
      savedAt: Date.now(),
      result: {
        bucket: { label: 'TypeScript / react', warning: null },
        profiles: {
          'octocat/hello-world': {
            full_name: 'octocat/hello-world',
            description: 'Mine',
            stars: 42,
            forks: 7,
            language: 'TypeScript',
            topics: ['react'],
            workflow_file_count: 1,
            pushed_at: '2024-01-01T00:00:00Z',
          },
          'org/bench': {
            full_name: 'org/bench',
            description: 'Benchmark',
            stars: 4200,
            forks: 300,
            language: 'TypeScript',
            topics: ['react'],
            workflow_file_count: 2,
            pushed_at: '2024-02-01T00:00:00Z',
          },
        },
        feature_matrix: {
          rows: [
            {
              dimension_id: 'docs',
              label_key: 'benchmark.dimension.docs',
              label: 'Documentation',
              cells: [
                { repo: 'octocat/hello-world', level: 'weak', score: 1, raw: {} },
                { repo: 'org/bench', level: 'strong', score: 4, raw: {} },
              ],
            },
          ],
        },
        hypotheses: [],
        actions: [],
        narrative: null,
        generated_at: '2024-06-01T10:00:00Z',
        llm_calls: 0,
      },
    })
    appContextValue.getGenerateCache.mockReturnValue({
      data: {
        user: {
          username: 'octocat',
          avatar_url: 'https://example.com/avatar.png',
        },
        localized_outputs: {
          en: {
            resume_markdown: '# Resume',
            social_card_html: '<div>card</div>',
            ai_insights: {
              style_tags: ['Builder'],
              roast_comment: 'Ships quickly',
              tech_summary: 'TypeScript and React',
            },
            card_data: {
              avatar_url: 'https://example.com/avatar.png',
              username: 'octocat',
              gitscore: 88,
              style_tags: ['Builder'],
              roast_comment: 'Ships quickly',
              tech_icons: ['TypeScript'],
              radar_chart_data: [1, 2, 3, 4, 5],
            },
          },
        },
      },
    })

    globalThis.URL.createObjectURL = vi.fn(() => 'blob:pdf')
    globalThis.URL.revokeObjectURL = vi.fn()
    vi.mocked(axios.post).mockResolvedValue({ data: new Blob(['pdf']) } as never)
  })

  it('reuses cached markdown when exporting PDF and appends benchmark markdown', async () => {
    render(
      <MemoryRouter initialEntries={['/export?user=octocat']}>
        <Routes>
          <Route path="/export" element={<Export language="en" />} />
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByLabelText('Include benchmark report'))
    fireEvent.click(screen.getByRole('button', { name: 'Download PDF' }))

    await waitFor(() => {
      expect(vi.mocked(axios.post)).toHaveBeenCalledWith(
        expect.stringContaining('/api/export/pdf'),
        expect.objectContaining({
          username: 'octocat',
          language: 'en',
          resume_markdown: '# Resume',
          extra_markdown: expect.stringContaining('# Repository Benchmark Report'),
        }),
        expect.objectContaining({ responseType: 'blob' }),
      )
    })
  })
})
