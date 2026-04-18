import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, vi } from 'vitest'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { Repositories } from './Repositories'

const analyzeResponse = {
  repository: {
    name: 'hello-world',
    description: 'A sample repository',
    stars: 42,
    forks: 7,
    language: 'TypeScript',
    url: 'https://github.com/octocat/hello-world',
    pushed_at: '2024-01-01T00:00:00Z',
    topics: ['demo', 'sample'],
    has_readme: true,
    has_license: true,
    file_tree: ['src/index.ts', 'README.md'],
  },
  analysis: {
    repo_name: 'hello-world',
    title: 'Resume-ready project',
    summary: 'Strong enough to pin on the resume.',
    highlights: ['Clear README', 'Healthy activity'],
    keywords: ['TypeScript', 'Open source'],
  },
}

const appContextValue = {
  contentLanguage: 'en' as const,
  getGenerateCache: vi.fn(),
  cacheGenerateResult: vi.fn(),
  getResumeProjects: vi.fn().mockReturnValue([]),
  toggleResumeProject: vi.fn(),
  setRepoAnalysis: vi.fn(),
  getRepoAnalysis: vi.fn().mockReturnValue(null),
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
      isAxiosError: actual.default.isAxiosError,
    },
  }
})

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location-search">{location.search}</output>
}

async function renderRepositories(initialEntry = '/repositories?user=octocat') {
  const axios = (await import('axios')).default
  return {
    ...(render(
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route
            path="/repositories"
            element={
              <>
                <Repositories language="en" />
                <LocationProbe />
              </>
            }
          />
        </Routes>
      </MemoryRouter>,
    )),
    axiosPost: vi.mocked(axios.post),
  }
}

describe('Repositories URL persistence', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    appContextValue.getRepoAnalysis.mockReturnValue(null)
    appContextValue.getGenerateCache.mockReturnValue({
      data: {
        user: {
          username: 'octocat',
          avatar_url: 'https://example.com/avatar.png',
          bio: 'octocat bio',
          followers: 10,
          following: 5,
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
    const axios = (await import('axios')).default
    vi.mocked(axios.post).mockResolvedValue({ data: analyzeResponse } as never)
  })

  it('pushes the selected repository into the URL when analysis is opened', async () => {
    await renderRepositories()

    fireEvent.click(screen.getByRole('button', { name: 'Analyze for resume' }))

    await waitFor(() => {
      expect(screen.getByTestId('location-search').textContent).toContain('repo=hello-world')
    })
    expect(screen.getByText('Strong enough to pin on the resume.')).toBeInTheDocument()
  })

  it('removes the repository query param when the same analysis is collapsed', async () => {
    await renderRepositories()

    fireEvent.click(screen.getByRole('button', { name: 'Analyze for resume' }))
    await screen.findByText('Strong enough to pin on the resume.')

    fireEvent.click(screen.getByRole('button', { name: 'Analyze for resume' }))

    await waitFor(() => {
      expect(screen.getByTestId('location-search').textContent).toBe('?user=octocat')
    })
  })

  it('restores repository analysis from the URL on first render', async () => {
    await renderRepositories('/repositories?user=octocat&repo=hello-world')

    expect(await screen.findByText('Strong enough to pin on the resume.')).toBeInTheDocument()
    expect(screen.getByTestId('location-search').textContent).toContain('repo=hello-world')
  })

  it('ignores invalid repository params without breaking browsing', async () => {
    await renderRepositories('/repositories?user=octocat&repo=missing-repo')

    expect(screen.getByRole('link', { name: /hello-world/i })).toBeInTheDocument()
    expect(screen.queryByText('Strong enough to pin on the resume.')).not.toBeInTheDocument()
  })
})
