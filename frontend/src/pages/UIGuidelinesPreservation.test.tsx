import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import fc from 'fast-check'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { Compare } from './Compare'
import { Repositories } from './Repositories'
import { Overview } from './Overview'
import { Export } from './Export'

const compareApp = {
  compareList: [] as string[],
  setCompareList: vi.fn(),
  addToCompare: vi.fn(),
  removeFromCompare: vi.fn(),
  contentLanguage: 'en' as const,
  getGenerateCache: vi.fn().mockReturnValue(null),
  cacheGenerateResult: vi.fn(),
}

const repositoriesApp = {
  contentLanguage: 'en' as const,
  getGenerateCache: vi.fn(),
  cacheGenerateResult: vi.fn(),
  getResumeProjects: vi.fn().mockReturnValue([]),
  toggleResumeProject: vi.fn(),
  setRepoAnalysis: vi.fn(),
  getRepoAnalysis: vi.fn().mockReturnValue(null),
}

const overviewApp = {
  addToCompare: vi.fn(),
  compareList: [] as string[],
  currentUser: 'octocat',
  setCurrentUser: vi.fn(),
  clearGenerateCacheForUser: vi.fn(),
  getGenerateCache: vi.fn(),
  getResumeProjects: vi.fn().mockReturnValue([]),
  toggleResumeProject: vi.fn(),
}

const exportApp = {
  contentLanguage: 'en' as const,
  getGenerateCache: vi.fn(),
  cacheGenerateResult: vi.fn(),
  getResumeProjects: vi.fn().mockReturnValue([]),
  getLatestBenchmarkWorkspaceEntryForUser: vi.fn().mockReturnValue(null),
}

vi.mock('../context', () => ({
  useApp: () => {
    const mode = (globalThis as typeof globalThis & { __uiTestMode?: string }).__uiTestMode
    if (mode === 'compare') return compareApp
    if (mode === 'repositories') return repositoriesApp
    if (mode === 'overview') return overviewApp
    if (mode === 'export') return exportApp
    throw new Error(`Unexpected test mode: ${mode}`)
  },
}))

vi.mock('axios', async () => {
  const actual = await vi.importActual<typeof import('axios')>('axios')
  return {
    default: {
      ...actual.default,
      post: vi.fn(() => new Promise(() => {})),
      delete: vi.fn().mockResolvedValue({}),
      isAxiosError: actual.default.isAxiosError,
    },
  }
})

function setMode(mode: 'compare' | 'repositories' | 'overview' | 'export') {
  ;(globalThis as typeof globalThis & { __uiTestMode?: string }).__uiTestMode = mode
}

function renderCompare() {
  setMode('compare')
  return render(
    <MemoryRouter initialEntries={['/compare']}>
      <Routes>
        <Route path="/compare" element={<Compare language="en" />} />
      </Routes>
    </MemoryRouter>,
  )
}

function renderRepositories() {
  setMode('repositories')
  return render(
    <MemoryRouter initialEntries={['/repositories?user=octocat']}>
      <Routes>
        <Route path="/repositories" element={<Repositories language="en" />} />
      </Routes>
    </MemoryRouter>,
  )
}

function renderOverview() {
  setMode('overview')
  return render(
    <MemoryRouter initialEntries={['/overview']}>
      <Routes>
        <Route path="/overview" element={<Overview language="en" />} />
        <Route path="/analysis" element={<div>AI analysis route</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

function renderExport() {
  setMode('export')
  return render(
    <MemoryRouter initialEntries={['/export?user=octocat']}>
      <Routes>
        <Route path="/export" element={<Export language="en" />} />
      </Routes>
    </MemoryRouter>,
  )
}

const usernameArb = fc
  .tuple(
    fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'),
    fc.stringMatching(/^[a-zA-Z0-9-]{0,18}$/),
    fc.constantFrom('', ...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'),
  )
  .map(([start, middle, end]) => `${start}${middle}${end}`)
  .filter((value) => value.length <= 20)

describe('UI guidelines preservation', () => {
  beforeEach(() => {
    compareApp.addToCompare.mockReset()
    compareApp.removeFromCompare.mockReset()
    compareApp.setCompareList.mockReset()
    compareApp.compareList = []

    repositoriesApp.toggleResumeProject.mockReset()
    repositoriesApp.setRepoAnalysis.mockReset()
    repositoriesApp.getRepoAnalysis.mockReset()
    repositoriesApp.getResumeProjects.mockReturnValue([])
    repositoriesApp.getGenerateCache.mockReturnValue({
      data: {
        user: {
          username: 'octocat',
          avatar_url: 'https://example.com/avatar.png',
          repositories: [
            {
              name: 'hello-world',
              description: 'A sample repository',
              stars: 42,
              forks: 7,
              language: 'TypeScript',
              url: 'https://github.com/octocat/hello-world',
              pushed_at: '2024-01-01T00:00:00Z',
              has_readme: true,
              has_license: true,
              topics: ['demo', 'sample'],
              file_tree: ['src/index.ts', 'README.md'],
            },
          ],
        },
      },
    })

    overviewApp.addToCompare.mockReset()
    overviewApp.setCurrentUser.mockReset()
    overviewApp.clearGenerateCacheForUser.mockReset()
    overviewApp.toggleResumeProject.mockReset()
    overviewApp.compareList = []
    overviewApp.currentUser = 'octocat'
    overviewApp.getGenerateCache.mockReturnValue({
      data: {
        user: {
          repositories: [
            {
              name: 'hello-world',
              description: 'A sample repository',
              stars: 42,
              forks: 7,
              language: 'TypeScript',
              url: 'https://github.com/octocat/hello-world',
              has_readme: true,
              has_license: true,
              topics: ['demo', 'sample'],
              file_tree: ['src/index.ts', 'README.md', 'package.json', '.github/workflows/ci.yml'],
            },
          ],
        },
      },
    })

    exportApp.getResumeProjects.mockReturnValue([])
    exportApp.getLatestBenchmarkWorkspaceEntryForUser.mockReturnValue(null)
    exportApp.getGenerateCache.mockReturnValue({
      data: {
        user: {
          username: 'octocat',
          avatar_url: 'https://example.com/avatar.png',
        },
        localized_outputs: {
          en: {
            resume_markdown: '# Resume',
            card_data: {
              avatar_url: 'https://example.com/avatar.png',
              username: 'octocat',
              gitscore: 88,
              style_tags: ['Builder'],
              roast_comment: 'Ships quickly',
            },
          },
        },
      },
    })

    localStorage.setItem(
      'codefolio-history',
      JSON.stringify([
        {
          id: '1',
          username: 'octocat',
          avatarUrl: 'https://example.com/avatar.png',
          gitscore: 88,
          timestamp: 1713350400000,
          language: 'en',
          bio: 'octocat bio',
        },
      ]),
    )
  })

  it('preserves compare input entry and enter-to-add behavior', async () => {
    await fc.assert(
      fc.asyncProperty(usernameArb, async (username) => {
        cleanup()
        const view = renderCompare()
        const input = view.getAllByRole('textbox')[0]

        fireEvent.change(input, { target: { value: username } })
        expect(input).toHaveValue(username)

        fireEvent.keyDown(input, { key: 'Enter' })

        await waitFor(() => {
          expect(compareApp.addToCompare).toHaveBeenCalledWith(username)
        })

        view.unmount()
        cleanup()
        compareApp.addToCompare.mockReset()
      }),
      { numRuns: 10 },
    )
  })

  it('preserves repository link and action button independence', () => {
    renderRepositories()

    expect(screen.getByRole('link', { name: /hello-world/i })).toHaveAttribute(
      'href',
      'https://github.com/octocat/hello-world',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Add to resume' }))
    expect(repositoriesApp.toggleResumeProject).toHaveBeenCalledTimes(1)
  })

  it('preserves overview history activation to AI analysis navigation', () => {
    renderOverview()

    fireEvent.click(screen.getByText('@octocat'))

    expect(overviewApp.setCurrentUser).toHaveBeenCalledWith('octocat')
    expect(screen.getByText('AI analysis route')).toBeInTheDocument()
  })

  it('preserves loading copy semantics while allowing ellipsis normalization', () => {
    exportApp.getGenerateCache.mockReturnValue(null)
    renderExport()
    expect(screen.getByText((content) => content.replace(/…/g, '...').trim() === 'Loading...')).toBeInTheDocument()
  })
})
