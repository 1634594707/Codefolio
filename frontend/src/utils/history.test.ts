import fc from 'fast-check'
import { beforeEach, describe, expect, it } from 'vitest'
import { readHistoryItems, type HistoryItem } from './history'

function readHistoryItemsLegacy(): HistoryItem[] {
  const saved = localStorage.getItem('codefolio-history')
  if (!saved) return []

  try {
    return JSON.parse(saved) as HistoryItem[]
  } catch {
    return []
  }
}

const historyItemArb = fc.record({
  id: fc.uuid(),
  username: fc.stringMatching(/^[a-zA-Z0-9-]{1,20}$/),
  avatarUrl: fc.webUrl(),
  gitscore: fc.integer({ min: 0, max: 100 }),
  timestamp: fc.integer({ min: 0, max: Number.MAX_SAFE_INTEGER }),
  language: fc.constantFrom<'en' | 'zh'>('en', 'zh'),
})

describe('Property 12: readHistoryItems behavior consistency', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('matches the legacy implementation for any localStorage content', () => {
    fc.assert(
      fc.property(
        fc.option(fc.array(historyItemArb, { maxLength: 12 }), { nil: undefined }),
        fc.string(),
        fc.boolean(),
        (historyItems, rawValue, useValidJson) => {
          if (historyItems === undefined) {
            localStorage.removeItem('codefolio-history')
          } else if (useValidJson) {
            localStorage.setItem('codefolio-history', JSON.stringify(historyItems))
          } else {
            localStorage.setItem('codefolio-history', rawValue)
          }

          expect(readHistoryItems()).toEqual(readHistoryItemsLegacy())
        },
      ),
      { numRuns: 200 },
    )
  })
})
