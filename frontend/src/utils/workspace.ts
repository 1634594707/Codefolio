const WORKSPACE_STORAGE_KEY = 'codefolio-workspace-id'

function createWorkspaceId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '')
  }
  return `ws_${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`
}

export function getOrCreateWorkspaceId(): string {
  if (typeof window === 'undefined') return 'global'
  const existing = localStorage.getItem(WORKSPACE_STORAGE_KEY)?.trim()
  if (existing) return existing
  const next = createWorkspaceId()
  localStorage.setItem(WORKSPACE_STORAGE_KEY, next)
  return next
}
