interface SanitizeConfig {
  ALLOWED_TAGS?: string[]
  ALLOWED_ATTR?: string[]
  FORBID_TAGS?: string[]
  FORBID_ATTR?: string[]
}

export const ALLOWED_TAGS_CONFIG: SanitizeConfig = {
  ALLOWED_TAGS: ['h1', 'h2', 'h3', 'p', 'ul', 'ol', 'li', 'strong', 'em', 'code', 'pre', 'hr', 'a', 'br', 'blockquote'],
  ALLOWED_ATTR: ['href', 'target', 'rel'],
  FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed'],
  FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover'],
}

export function escapeHtml(unsafe: string): string {
  return unsafe
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

export async function sanitizeHtml(html: string): Promise<string> {
  try {
    const { default: DOMPurify } = await import('dompurify')
    return DOMPurify.sanitize(html, ALLOWED_TAGS_CONFIG) as string
  } catch {
    console.warn('[Export] DOMPurify failed to load, falling back to plain text')
    return escapeHtml(html)
  }
}
