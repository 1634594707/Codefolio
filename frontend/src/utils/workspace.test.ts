import fc from 'fast-check'
import { describe, expect, it } from 'vitest'
import { importWorkspace, validateWorkspaceSnapshot, type WorkspaceSnapshot } from './workspace'
import type { GenerateResponse } from '../types/generate'

function makeGenerateResponse(username: string): GenerateResponse {
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
      total: 50,
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
      gitscore: 50,
      radar_chart_data: [],
      style_tags: [],
      roast_comment: '',
      tech_icons: [],
    },
    localized_outputs: {},
    available_content_languages: ['en'],
  }
}

const usernameArb = fc.stringMatching(/^[a-zA-Z0-9-]{1,20}$/)
const isoDateArb = fc
  .integer({ min: -8_640_000_000_000_000, max: 8_640_000_000_000_000 })
  .map((value) => new Date(value).toISOString())

const workspaceSnapshotArb: fc.Arbitrary<WorkspaceSnapshot> = fc.record({
  version: fc.constant<1>(1),
  generateCacheEntries: fc.array(
    fc.record({
      username: usernameArb,
      contentLanguage: fc.constantFrom<'en' | 'zh'>('en', 'zh'),
      data: usernameArb.map((username) => makeGenerateResponse(username)),
      cachedAt: fc.integer({ min: 0, max: Number.MAX_SAFE_INTEGER }),
    }),
    { maxLength: 8 },
  ),
  resumeProjects: fc.array(
    fc.record({
      user: usernameArb,
      repoName: fc.stringMatching(/^[a-zA-Z0-9_.-]{1,30}$/),
      description: fc.string(),
      language: fc.string(),
      stars: fc.integer({ min: 0, max: 100000 }),
      forks: fc.integer({ min: 0, max: 100000 }),
      url: fc.webUrl(),
      pushed_at: fc.option(isoDateArb, { nil: undefined }),
      has_readme: fc.option(fc.boolean(), { nil: undefined }),
      has_license: fc.option(fc.boolean(), { nil: undefined }),
      analysisTitle: fc.string(),
      analysisSummary: fc.string(),
      highlights: fc.array(fc.string(), { maxLength: 5 }),
      keywords: fc.array(fc.string(), { maxLength: 5 }),
    }),
    { maxLength: 8 },
  ),
  benchmarkWorkspaceEntries: fc.array(
    fc.record({
      username: usernameArb,
      mine: fc.stringMatching(/^[a-zA-Z0-9-]{1,20}\/[a-zA-Z0-9_.-]{1,30}$/),
      benchmarks: fc.array(fc.stringMatching(/^[a-zA-Z0-9-]{1,20}\/[a-zA-Z0-9_.-]{1,30}$/), {
        maxLength: 3,
      }),
      language: fc.constantFrom<'en' | 'zh'>('en', 'zh'),
      result: fc.record({
        bucket: fc.record({
          label: fc.string(),
          warning: fc.option(fc.string(), { nil: null }),
        }),
        profiles: fc.dictionary(fc.string(), fc.record({ full_name: fc.string() })),
        feature_matrix: fc.record({ rows: fc.constant([]) }),
        hypotheses: fc.constant([]),
        actions: fc.constant([]),
        narrative: fc.constant(null),
        generated_at: isoDateArb,
        llm_calls: fc.integer({ min: 0, max: 10 }),
      }) as never,
      savedAt: fc.integer({ min: 0, max: Number.MAX_SAFE_INTEGER }),
    }),
    { maxLength: 4 },
  ),
  compareList: fc.array(usernameArb, { maxLength: 3 }),
  exportedAt: fc.integer({ min: 0, max: Number.MAX_SAFE_INTEGER }),
})

describe('Property 4: workspace serialization round-trip', () => {
  it('keeps any valid workspace snapshot equivalent through JSON serialization', () => {
    fc.assert(
      fc.property(workspaceSnapshotArb, (snapshot) => {
        const roundTripped = JSON.parse(JSON.stringify(snapshot)) as unknown
        expect(validateWorkspaceSnapshot(roundTripped)).toBe(true)
        expect(roundTripped).toEqual(snapshot)
      }),
      { numRuns: 200 },
    )
  })
})

describe('Property 5: invalid workspace import does not produce a valid snapshot', () => {
  it('rejects malformed JSON inputs', async () => {
    await fc.assert(
      fc.asyncProperty(fc.string().filter((value) => value.trim() !== ''), async (raw) => {
        const file = new File([raw], 'workspace.json', { type: 'application/json' })
        let parsedSuccessfully = false

        try {
          await importWorkspace(file)
          parsedSuccessfully = true
        } catch {
          parsedSuccessfully = false
        }

        if (parsedSuccessfully) {
          const parsed = JSON.parse(raw) as unknown
          expect(validateWorkspaceSnapshot(parsed)).toBe(true)
        } else {
          expect(parsedSuccessfully).toBe(false)
        }
      }),
      { numRuns: 200 },
    )
  })
})
