/**
 * Feature: repo-benchmark, Property 33: Staleness Warning Display
 *
 * For any cached data where the fetched_at or generated_at timestamp is older
 * than 7 days from the current time, the System should display a staleness
 * warning to the user indicating the data age.
 *
 * Validates: Requirements 18.5
 */

import fc from 'fast-check'
import { describe, it, expect } from 'vitest'
import { isStale } from './formatCacheAge'

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000

describe('Property 33: Staleness Warning Display', () => {
  it('data older than 7 days is always stale', () => {
    /**
     * Validates: Requirements 18.5
     * For any timestamp older than 7 days, isStale() must return true.
     */
    fc.assert(
      fc.property(
        // Generate offsets strictly greater than 7 days (in ms)
        fc.integer({ min: 1, max: 365 * 24 * 60 * 60 * 1000 }),
        (extraMs) => {
          const olderThan7Days = new Date(Date.now() - SEVEN_DAYS_MS - extraMs)
          expect(isStale(olderThan7Days.toISOString())).toBe(true)
        },
      ),
      { numRuns: 100 },
    )
  })

  it('data newer than 7 days is never stale', () => {
    /**
     * Validates: Requirements 18.5
     * For any timestamp within the last 7 days, isStale() must return false.
     */
    fc.assert(
      fc.property(
        // Generate offsets strictly less than 7 days (in ms), at least 1 second ago
        fc.integer({ min: 1000, max: SEVEN_DAYS_MS - 1000 }),
        (offsetMs) => {
          const recentTimestamp = new Date(Date.now() - offsetMs)
          expect(isStale(recentTimestamp.toISOString())).toBe(false)
        },
      ),
      { numRuns: 100 },
    )
  })

  it('exactly 7 days ago is stale (boundary: > 7 days means stale)', () => {
    // The implementation uses strict >, so exactly 7 days is NOT stale
    // but just over 7 days IS stale. Test the boundary.
    const exactly7Days = new Date(Date.now() - SEVEN_DAYS_MS)
    // At exactly 7 days, Date.now() - date.getTime() === SEVEN_DAYS_MS, which is NOT > SEVEN_DAYS_MS
    expect(isStale(exactly7Days.toISOString())).toBe(false)

    const justOver7Days = new Date(Date.now() - SEVEN_DAYS_MS - 1000)
    expect(isStale(justOver7Days.toISOString())).toBe(true)
  })

  it('future timestamps are never stale', () => {
    /**
     * Validates: Requirements 18.5
     * Future timestamps (e.g., clock skew) should not be considered stale.
     */
    fc.assert(
      fc.property(
        fc.integer({ min: 1000, max: 30 * 24 * 60 * 60 * 1000 }),
        (futureOffsetMs) => {
          const futureTimestamp = new Date(Date.now() + futureOffsetMs)
          expect(isStale(futureTimestamp.toISOString())).toBe(false)
        },
      ),
      { numRuns: 100 },
    )
  })

  it('invalid timestamps are never stale', () => {
    // isStale returns false for invalid ISO strings (NaN date)
    expect(isStale('not-a-date')).toBe(false)
    expect(isStale('')).toBe(false)
    expect(isStale('invalid')).toBe(false)
  })
})
