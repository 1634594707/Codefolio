import { act, render, waitFor } from '@testing-library/react'
import fc from 'fast-check'
import axios from 'axios'
import { createRef } from 'react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { AppProvider, useApp } from './AppContext'
import type { GenerateResponse } from '../types/generate'

vi.mock('axios', () => ({
  default: {
    post: vi.fn(),
  },
}))

type AppContextHandle = ReturnType<typeof useApp>

function makeGenerateResponse(username: string, language: 'en' | 'zh'): GenerateResponse {
  return {
    user: {
      username,
      name: username,
      avatar_url: `https://example.com/${username}.png`,
      bio: '',
      followers: 0,
      following: 0,
      languages: {},
      repositories: [],
    },
    resume_markdown: `# ${username}`,
    gitscore: {
      total: 80,
      dimensions: {},
    },
    ai_insights: {
      style_tags: [],
      roast_comment: '',
      tech_summary: '',
    },
    card_data: {
      username,
      avatar_url: `https://example.com/${username}.png`,
      gitscore: 80,
      radar_chart_data: [],
      style_tags: [],
      roast_comment: '',
      tech_icons: [],
    },
    localized_outputs: {
      [language]: {
        resume_markdown: `# ${username}`,
        ai_insights: {
          style_tags: [],
          roast_comment: '',
          tech_summary: '',
        },
        card_data: {
          username,
          avatar_url: `https://example.com/${username}.png`,
          gitscore: 80,
          radar_chart_data: [],
          style_tags: [],
          roast_comment: '',
          tech_icons: [],
        },
        social_card_html: '<div />',
      },
    },
    available_content_languages: [language],
  }
}

function renderAppContext() {
  const ref = createRef<AppContextHandle>()

  function Probe() {
    ref.current = useApp()
    return null
  }

  const view = render(
    <AppProvider>
      <Probe />
    </AppProvider>,
  )

  if (!ref.current) {
    throw new Error('Failed to capture AppContext')
  }

  return { ref, unmount: view.unmount }
}

describe('Property 1: request deduplication consistency', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('shares one HTTP request across concurrent generateWithDedup calls', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.stringMatching(/^[a-zA-Z0-9-]{1,20}$/),
        fc.constantFrom<'en' | 'zh'>('en', 'zh'),
        fc.integer({ min: 2, max: 6 }),
        async (username, language, callCount) => {
          vi.mocked(axios.post).mockReset()
          const response = makeGenerateResponse(username, language)
          vi.mocked(axios.post).mockResolvedValueOnce({ data: response } as never)

          const { ref, unmount } = renderAppContext()
          try {
            let results: GenerateResponse[] = []
            await act(async () => {
              const pendingCalls = Array.from({ length: callCount }, () =>
                ref.current!.generateWithDedup(username, language),
              )
              results = await Promise.all(pendingCalls)
            })

            expect(axios.post).toHaveBeenCalledTimes(1)
            results.forEach((result) => expect(result).toEqual(response))
          } finally {
            unmount()
          }
        },
      ),
      { numRuns: 50 },
    )
  })
})

describe('Property 2: requests can retry after failure', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('clears the pending request after an error so the next call can issue a new request', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.stringMatching(/^[a-zA-Z0-9-]{1,20}$/),
        fc.constantFrom<'en' | 'zh'>('en', 'zh'),
        async (username, language) => {
          vi.mocked(axios.post).mockReset()
          vi.mocked(axios.post)
            .mockRejectedValueOnce(new Error('boom'))
            .mockResolvedValueOnce({ data: makeGenerateResponse(username, language) } as never)

          const { ref, unmount } = renderAppContext()
          try {
            await act(async () => {
              await expect(ref.current!.generateWithDedup(username, language)).rejects.toThrow('boom')
            })
            await waitFor(() => {
              expect(ref.current!.getPendingRequest(username, language)).toBeNull()
            })

            let retried: GenerateResponse | null = null
            await act(async () => {
              retried = await ref.current!.generateWithDedup(username, language)
            })
            expect(retried?.user.username).toBe(username)
            expect(axios.post).toHaveBeenCalledTimes(2)
          } finally {
            unmount()
          }
        },
      ),
      { numRuns: 50 },
    )
  })
})
