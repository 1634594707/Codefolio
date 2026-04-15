import fc from 'fast-check'
import { describe, expect, it } from 'vitest'
import { sanitizeHtml } from './exportSanitizer'

describe('Property 3: XSS sanitization safety', () => {
  it('removes script tags, inline event handlers, and javascript: URLs', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.string(),
        fc.string(),
        fc.string(),
        async (scriptPayload, handlerPayload, urlPayload) => {
          const html = [
            `<script>${scriptPayload}</script>`,
            `<img src="x" onerror="${handlerPayload}">`,
            `<a href="javascript:${urlPayload}">open</a>`,
          ].join('')

          const sanitized = (await sanitizeHtml(html)).toLowerCase()
          expect(sanitized).not.toContain('<script')
          expect(sanitized).not.toContain('onerror=')
          expect(sanitized).not.toContain('javascript:')
        },
      ),
      { numRuns: 200 },
    )
  })
})
