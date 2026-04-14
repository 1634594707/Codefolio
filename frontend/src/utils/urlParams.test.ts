/**
 * Feature: repo-benchmark, Property 23: URL Parameter Isolation
 *
 * For any request to repository benchmarking endpoints, the System should use
 * "mine" and "b" parameters and should not conflict with or be affected by
 * "users" parameter used in user comparison mode.
 *
 * Validates: Requirements 8.1
 */

import fc from 'fast-check'
import { describe, it, expect } from 'vitest'

/**
 * Simulates how CompareRepos.tsx reads its URL parameters.
 * Returns the mine/b values from the search params.
 */
function readBenchmarkParams(params: URLSearchParams): { mine: string; benchmarks: string[] } {
  const mine = params.get('mine') ?? ''
  const benchmarks = (params.get('b') ?? '').split(',').filter(Boolean).slice(0, 3)
  return { mine, benchmarks }
}

/**
 * Simulates how the user-comparison page reads its URL parameters.
 * Returns the users value from the search params.
 */
function readUserCompareParams(params: URLSearchParams): { users: string[] } {
  const users = (params.get('users') ?? '').split(',').filter(Boolean)
  return { users }
}

/**
 * Simulates building the search params that CompareRepos.tsx sets via setSearchParams.
 */
function buildBenchmarkParams(mine: string, benchmarks: string[], includeNarrative: boolean): URLSearchParams {
  const params = new URLSearchParams()
  if (mine) params.set('mine', mine)
  if (benchmarks.length > 0) params.set('b', benchmarks.join(','))
  if (includeNarrative) params.set('n', '1')
  return params
}

// Arbitrary for a valid-ish repo name (owner/repo)
const repoArb = fc.tuple(
  fc.stringMatching(/^[a-zA-Z0-9-]{1,20}$/),
  fc.stringMatching(/^[a-zA-Z0-9-]{1,20}$/),
).map(([owner, repo]) => `${owner}/${repo}`)

// Arbitrary for a GitHub username
const usernameArb = fc.stringMatching(/^[a-zA-Z0-9-]{1,20}$/)

describe('Property 23: URL Parameter Isolation', () => {
  it('benchmark params (mine, b) do not affect users param', () => {
    /**
     * Validates: Requirements 8.1
     * When mine/b params are present, the users param should be unaffected.
     */
    fc.assert(
      fc.property(
        repoArb,
        fc.array(repoArb, { minLength: 1, maxLength: 3 }),
        fc.array(usernameArb, { minLength: 1, maxLength: 3 }),
        fc.boolean(),
        (mine, benchmarks, users, includeNarrative) => {
          // Build benchmark params (as CompareRepos would)
          const benchmarkParams = buildBenchmarkParams(mine, benchmarks, includeNarrative)

          // Separately, a user-comparison URL has a "users" param
          const userCompareParams = new URLSearchParams()
          userCompareParams.set('users', users.join(','))

          // Reading benchmark params from benchmark URL should not see "users"
          const benchmarkResult = readBenchmarkParams(benchmarkParams)
          expect(benchmarkResult.mine).toBe(mine)
          expect(benchmarkResult.benchmarks).toEqual(benchmarks.slice(0, 3))

          // The benchmark URL should not contain "users"
          expect(benchmarkParams.has('users')).toBe(false)

          // Reading user-compare params from user-compare URL should not see "mine" or "b"
          const userResult = readUserCompareParams(userCompareParams)
          expect(userResult.users).toEqual(users)
          expect(userCompareParams.has('mine')).toBe(false)
          expect(userCompareParams.has('b')).toBe(false)
        },
      ),
      { numRuns: 100 },
    )
  })

  it('users param does not affect benchmark params (mine, b)', () => {
    /**
     * Validates: Requirements 8.1
     * When users param is present, mine/b params should not be affected.
     */
    fc.assert(
      fc.property(
        repoArb,
        fc.array(repoArb, { minLength: 1, maxLength: 3 }),
        fc.array(usernameArb, { minLength: 1, maxLength: 3 }),
        (mine, benchmarks, users) => {
          // A URL that has both benchmark params AND a users param (edge case)
          const mixedParams = new URLSearchParams()
          mixedParams.set('mine', mine)
          mixedParams.set('b', benchmarks.join(','))
          mixedParams.set('users', users.join(','))

          // Benchmark reader should only read mine/b, ignoring users
          const benchmarkResult = readBenchmarkParams(mixedParams)
          expect(benchmarkResult.mine).toBe(mine)
          expect(benchmarkResult.benchmarks).toEqual(benchmarks.slice(0, 3))

          // User-compare reader should only read users, ignoring mine/b
          const userResult = readUserCompareParams(mixedParams)
          expect(userResult.users).toEqual(users)
        },
      ),
      { numRuns: 100 },
    )
  })

  it('benchmark params are limited to at most 3 benchmarks regardless of b param content', () => {
    /**
     * Validates: Requirements 8.1, 3.4
     * The b param is capped at 3 entries.
     */
    fc.assert(
      fc.property(
        fc.array(repoArb, { minLength: 0, maxLength: 10 }),
        (repos) => {
          const params = new URLSearchParams()
          params.set('b', repos.join(','))
          const result = readBenchmarkParams(params)
          expect(result.benchmarks.length).toBeLessThanOrEqual(3)
        },
      ),
      { numRuns: 100 },
    )
  })

  it('narrative param n does not interfere with mine/b/users params', () => {
    /**
     * Validates: Requirements 8.1
     * The n param is specific to benchmark mode and does not affect user comparison.
     */
    fc.assert(
      fc.property(
        repoArb,
        fc.array(repoArb, { minLength: 1, maxLength: 3 }),
        fc.boolean(),
        (mine, benchmarks, includeNarrative) => {
          const params = buildBenchmarkParams(mine, benchmarks, includeNarrative)

          // n param should only be set when includeNarrative is true
          if (includeNarrative) {
            expect(params.get('n')).toBe('1')
          } else {
            expect(params.has('n')).toBe(false)
          }

          // users param should never be set by benchmark builder
          expect(params.has('users')).toBe(false)
        },
      ),
      { numRuns: 100 },
    )
  })
})
