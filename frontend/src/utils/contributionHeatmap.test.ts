import fc from 'fast-check'
import { describe, expect, it } from 'vitest'
import { formatContributionTooltip } from './contributionHeatmap'

describe('Property 13: heatmap tooltip formatting completeness', () => {
  it('always includes the input date and contribution count in the active language', () => {
    fc.assert(
      fc.property(
        fc.constantFrom<'en' | 'zh'>('en', 'zh'),
        fc.integer({ min: 0, max: 4_102_444_800_000 }).map((value) => new Date(value).toISOString().slice(0, 10)),
        fc.integer({ min: 0, max: 100000 }),
        (language, date, count) => {
          const tooltip = formatContributionTooltip(language, date, count)
          expect(tooltip).toContain(date)
          expect(tooltip).toContain(String(count))
          expect(tooltip).toContain(language === 'zh' ? '次贡献' : 'contributions')
        },
      ),
      { numRuns: 200 },
    )
  })
})
