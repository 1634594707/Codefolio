import fc from 'fast-check'
import { describe, expect, it } from 'vitest'
import { RESUME_PROJECTS_MAX_PER_USER } from '../config/constants'
import type { ResumeProject } from '../context'
import type { RepositoryAnalysisPayload } from './resumeProjects'
import { toggleResumeProjectsForUser, upsertRepoAnalysisCache } from './appState'

function makeResumeProject(user: string, repoName: string): ResumeProject {
  return {
    user,
    repoName,
    description: '',
    language: 'TypeScript',
    stars: 0,
    forks: 0,
    url: `https://github.com/${user}/${repoName}`,
    analysisTitle: repoName,
    analysisSummary: repoName,
    highlights: [],
    keywords: [],
  }
}

function makeRepositoryAnalysisPayload(name: string): RepositoryAnalysisPayload {
  return {
    repository: {
      name,
      description: '',
      language: 'TypeScript',
      stars: 0,
      forks: 0,
      url: `https://github.com/acme/${name}`,
    },
    analysis: {
      repo_name: name,
      title: name,
      summary: `${name} summary`,
      highlights: [],
      keywords: [],
    },
  }
}

describe('Property 8: resume project cap remains bounded', () => {
  it('never keeps more than the configured max projects for a user after any toggle sequence', () => {
    fc.assert(
      fc.property(
        fc.array(fc.stringMatching(/^[a-zA-Z0-9_.-]{1,30}$/), { minLength: 1, maxLength: 40 }),
        (repoNames) => {
          const state = repoNames.reduce<ResumeProject[]>(
            (projects, repoName) => toggleResumeProjectsForUser(projects, makeResumeProject('alice', repoName), RESUME_PROJECTS_MAX_PER_USER),
            [],
          )
          const selectedForUser = state.filter((project) => project.user === 'alice')
          expect(selectedForUser.length).toBeLessThanOrEqual(RESUME_PROJECTS_MAX_PER_USER)
        },
      ),
      { numRuns: 200 },
    )
  })
})

describe('Property 6: repository analysis cache round-trip', () => {
  it('returns the same payload immediately after insertion', () => {
    fc.assert(
      fc.property(fc.stringMatching(/^[a-zA-Z0-9_.-]{1,30}$/), (repoName) => {
        const key = `alice/${repoName}`
        const payload = makeRepositoryAnalysisPayload(repoName)
        const cache = upsertRepoAnalysisCache(new Map(), key, payload)
        expect(cache.get(key)).toEqual(payload)
      }),
      { numRuns: 200 },
    )
  })
})

describe('Property 7: repository analysis cache LRU capacity invariant', () => {
  it('never grows beyond 50 entries for any insertion sequence', () => {
    fc.assert(
      fc.property(
        fc.array(fc.stringMatching(/^[a-zA-Z0-9_.-]{1,30}$/), { minLength: 1, maxLength: 200 }),
        (repoNames) => {
          const cache = repoNames.reduce((current, repoName, index) => {
            const key = `alice/${repoName}-${index}`
            return upsertRepoAnalysisCache(current, key, makeRepositoryAnalysisPayload(repoName))
          }, new Map<string, RepositoryAnalysisPayload>())

          expect(cache.size).toBeLessThanOrEqual(50)
        },
      ),
      { numRuns: 200 },
    )
  })
})
