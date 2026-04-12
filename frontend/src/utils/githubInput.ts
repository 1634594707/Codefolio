const GITHUB_USERNAME_PATTERN = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$/
const GITHUB_REPO_SEGMENT_PATTERN = /^[A-Za-z0-9._-]+$/

export type GitHubUsernameValidationResult =
  | { valid: true; username: string }
  | { valid: false; message: 'empty' | 'invalid'; username: string }

export type ParsedGitHubInput =
  | { kind: 'empty' }
  | { kind: 'user'; username: string }
  | { kind: 'repo'; username: string; repo: string }
  | { kind: 'invalid'; username: string }

export type ParsedGitHubRepoInput =
  | { kind: 'empty' }
  | { kind: 'repo'; owner: string; repo: string; fullName: string }
  | { kind: 'invalid'; value: string }

function normalizeGitHubUrlCandidate(raw: string): string {
  if (/^https?:\/\//i.test(raw)) return raw
  if (/^github\.com\//i.test(raw) || /^www\.github\.com\//i.test(raw)) {
    return `https://${raw}`
  }
  return raw
}

function extractUsernameFromUrl(raw: string): string | null {
  const normalized = normalizeGitHubUrlCandidate(raw)
  if (!/^https?:\/\//i.test(normalized)) return null

  try {
    const url = new URL(normalized)
    const hostname = url.hostname.toLowerCase()
    if (hostname !== 'github.com' && hostname !== 'www.github.com') return null

    const segments = url.pathname.split('/').filter(Boolean)
    if (segments.length === 0) return ''

    if ((segments[0] === 'orgs' || segments[0] === 'users') && segments[1]) {
      return segments[1]
    }

    return segments[0] ?? ''
  } catch {
    return null
  }
}

function normalizeUsernameLikeInput(raw: string): string {
  const trimmed = raw.trim()
  if (!trimmed) return ''

  const fromUrl = extractUsernameFromUrl(trimmed)
  if (fromUrl !== null) return fromUrl.trim()

  if (trimmed.startsWith('@')) {
    return trimmed.replace(/^@+/, '').trim()
  }

  return trimmed
}

function extractRepoFromUrl(raw: string): { username: string; repo: string } | null {
  const normalized = normalizeGitHubUrlCandidate(raw)
  if (!/^https?:\/\//i.test(normalized)) return null

  try {
    const url = new URL(normalized)
    const hostname = url.hostname.toLowerCase()
    if (hostname !== 'github.com' && hostname !== 'www.github.com') return null

    const segments = url.pathname.split('/').filter(Boolean)
    if (segments.length < 2) return null
    if (segments[0] === 'orgs' || segments[0] === 'users') return null

    return {
      username: segments[0] ?? '',
      repo: segments[1] ?? '',
    }
  } catch {
    return null
  }
}

export function parseGitHubInput(raw: string): ParsedGitHubInput {
  const trimmed = raw.trim()
  if (!trimmed) return { kind: 'empty' }

  const repoFromUrl = extractRepoFromUrl(trimmed)
  if (repoFromUrl) {
    if (!GITHUB_USERNAME_PATTERN.test(repoFromUrl.username) || !repoFromUrl.repo.trim()) {
      return { kind: 'invalid', username: repoFromUrl.username }
    }
    return {
      kind: 'repo',
      username: repoFromUrl.username,
      repo: repoFromUrl.repo.trim(),
    }
  }

  const username = normalizeUsernameLikeInput(trimmed)
  if (!username) return { kind: 'empty' }
  if (!GITHUB_USERNAME_PATTERN.test(username)) {
    return { kind: 'invalid', username }
  }
  return { kind: 'user', username }
}

export function normalizeGitHubUsernameInput(raw: string): string {
  const parsed = parseGitHubInput(raw)
  if (parsed.kind === 'user' || parsed.kind === 'repo') return parsed.username
  return normalizeUsernameLikeInput(raw)
}

export function validateGitHubUsername(raw: string): GitHubUsernameValidationResult {
  const parsed = parseGitHubInput(raw)
  if (parsed.kind === 'empty') {
    return { valid: false, message: 'empty', username: '' }
  }
  if (parsed.kind === 'invalid') {
    return { valid: false, message: 'invalid', username: parsed.username }
  }
  return { valid: true, username: parsed.username }
}

export function splitGitHubUsernameInputs(raw: string): string[] {
  const normalized = raw.trim()
  if (!normalized) return []

  return normalized
    .split(/[\s,;，；\n\r\t]+/)
    .map((item) => normalizeGitHubUsernameInput(item))
    .filter(Boolean)
}

export function parseGitHubRepoInput(raw: string): ParsedGitHubRepoInput {
  const trimmed = raw.trim()
  if (!trimmed) return { kind: 'empty' }

  const fromUrl = extractRepoFromUrl(trimmed)
  const candidate = fromUrl ? `${fromUrl.username}/${fromUrl.repo}` : trimmed.replace(/^@+/, '')
  const segments = candidate
    .split('/')
    .map((item) => item.trim())
    .filter(Boolean)

  if (segments.length !== 2) {
    return { kind: 'invalid', value: trimmed }
  }

  const [owner, repo] = segments
  if (!GITHUB_USERNAME_PATTERN.test(owner) || !GITHUB_REPO_SEGMENT_PATTERN.test(repo)) {
    return { kind: 'invalid', value: trimmed }
  }

  return {
    kind: 'repo',
    owner,
    repo,
    fullName: `${owner}/${repo}`,
  }
}

export function splitGitHubRepoInputs(raw: string): string[] {
  const normalized = raw.trim()
  if (!normalized) return []

  return normalized
    .split(/[\s,;，；\n\r\t]+/)
    .map((item) => parseGitHubRepoInput(item))
    .filter((item): item is Extract<ParsedGitHubRepoInput, { kind: 'repo' }> => item.kind === 'repo')
    .map((item) => item.fullName)
}
