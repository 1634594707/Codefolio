import { describe, expect, it } from 'vitest'
import fc from 'fast-check'
import fs from 'node:fs'
import path from 'node:path'

const pagesDir = path.resolve(__dirname)

const pageFiles = {
  CompareRepos: path.join(pagesDir, 'CompareRepos.tsx'),
  Compare: path.join(pagesDir, 'Compare.tsx'),
  Repositories: path.join(pagesDir, 'Repositories.tsx'),
  Export: path.join(pagesDir, 'Export.tsx'),
  AIAnalysis: path.join(pagesDir, 'AIAnalysis.tsx'),
  Overview: path.join(pagesDir, 'Overview.tsx'),
} as const

type PageName = keyof typeof pageFiles

function readSource(pageName: PageName) {
  return fs.readFileSync(pageFiles[pageName], 'utf8')
}

function compact(value: string) {
  return value.replace(/\s+/g, ' ').trim()
}

function findImgsMissingDimensions(source: string) {
  const matches = source.matchAll(/<img\b[\s\S]*?\/>/g)
  const violations: string[] = []

  for (const match of matches) {
    const tag = match[0]
    if (!/\bwidth[=\s{]/.test(tag) || !/\bheight[=\s{]/.test(tag)) {
      violations.push(compact(tag))
    }
  }

  return violations
}

function findButtonsMissingType(source: string) {
  const matches = source.matchAll(/<button\b[\s\S]*?>/g)
  const violations: string[] = []

  for (const match of matches) {
    const tag = match[0]
    if (!/\btype[=\s{]/.test(tag)) {
      violations.push(compact(tag))
    }
  }

  return violations
}

function findNonSemanticClickHandlers(source: string) {
  return source
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => /<(div|span)\b/.test(line) && /\bonClick=/.test(line))
    .map(compact)
}

function findTextInputsWithoutAccessibleName(source: string) {
  const violations: string[] = []
  const labelRanges = Array.from(source.matchAll(/<label\b[\s\S]*?<\/label>/g)).map((match) => ({
    start: match.index ?? 0,
    end: (match.index ?? 0) + match[0].length,
    content: match[0],
  }))

  for (const match of source.matchAll(/<input\b[\s\S]*?\/>/g)) {
    const tag = match[0]
    const index = match.index ?? 0
    const typeMatch = tag.match(/\btype=(?:"([^"]+)"|'([^']+)'|\{([^}]+)\})/)
    const inputType = (typeMatch?.[1] ?? typeMatch?.[2] ?? typeMatch?.[3] ?? 'text').replace(/['"]/g, '')
    if (!['text', 'search'].includes(inputType)) continue

    const hasAriaLabel = /\baria-label[=\s{]/.test(tag)
    const idMatch = tag.match(/\bid=(?:"([^"]+)"|'([^']+)')/)
    const inputId = idMatch?.[1] ?? idMatch?.[2] ?? ''
    const isWrappedByLabel = labelRanges.some((range) => index >= range.start && index <= range.end && /<input\b/.test(range.content))
    const hasAssociatedLabel =
      inputId !== '' &&
      new RegExp(`<label\\b[^>]*htmlFor=["']${inputId}["'][\\s\\S]*?<\\/label>`).test(source)

    if (!hasAriaLabel && !isWrappedByLabel && !hasAssociatedLabel) {
      violations.push(compact(tag))
    }
  }

  return violations
}

describe('UI guidelines compliance bug-condition exploration', () => {
  it('surfaces img counterexamples across affected pages', () => {
    const affectedPages: PageName[] = ['Compare', 'Repositories', 'Export', 'AIAnalysis', 'Overview']

    fc.assert(
      fc.property(fc.constantFrom(...affectedPages), (pageName) => {
        expect(findImgsMissingDimensions(readSource(pageName)), pageName).toHaveLength(0)
      }),
      { numRuns: affectedPages.length },
    )
  })

  it('surfaces button counterexamples across affected pages', () => {
    const affectedPages: PageName[] = ['Compare', 'Export', 'Overview']

    fc.assert(
      fc.property(fc.constantFrom(...affectedPages), (pageName) => {
        expect(findButtonsMissingType(readSource(pageName)), pageName).toHaveLength(0)
      }),
      { numRuns: affectedPages.length },
    )
  })

  it('surfaces div/span onClick counterexamples', () => {
    const affectedPages: PageName[] = ['Overview']

    fc.assert(
      fc.property(fc.constantFrom(...affectedPages), (pageName) => {
        expect(findNonSemanticClickHandlers(readSource(pageName)), pageName).toHaveLength(0)
      }),
      { numRuns: affectedPages.length },
    )
  })

  it('surfaces unlabeled text input counterexamples', () => {
    const affectedPages: PageName[] = ['Repositories']

    fc.assert(
      fc.property(fc.constantFrom(...affectedPages), (pageName) => {
        expect(findTextInputsWithoutAccessibleName(readSource(pageName)), pageName).toHaveLength(0)
      }),
      { numRuns: affectedPages.length },
    )
  })
})
