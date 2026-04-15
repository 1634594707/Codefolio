import type { GenerateCacheEntry, ResumeProject, BenchmarkWorkspaceEntry } from '../context/AppContext'

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

export type WorkspaceSnapshot = {
  version: 1
  generateCacheEntries: GenerateCacheEntry[]
  resumeProjects: ResumeProject[]
  benchmarkWorkspaceEntries: BenchmarkWorkspaceEntry[]
  compareList: string[]
  exportedAt: number
}

export function exportWorkspace(state: WorkspaceSnapshot): void {
  const json = JSON.stringify(state, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `codefolio-workspace-${Date.now()}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function importWorkspace(file: File): Promise<WorkspaceSnapshot> {
  const text = await file.text()
  let data: unknown
  try {
    data = JSON.parse(text)
  } catch {
    throw new Error('Invalid JSON: failed to parse workspace file')
  }
  if (!validateWorkspaceSnapshot(data)) {
    throw new Error('Invalid workspace snapshot: missing or incorrect fields')
  }
  return data
}

export function validateWorkspaceSnapshot(data: unknown): data is WorkspaceSnapshot {
  if (typeof data !== 'object' || data === null) return false
  const d = data as Record<string, unknown>
  if (d.version !== 1) return false
  if (!Array.isArray(d.generateCacheEntries)) return false
  if (!Array.isArray(d.resumeProjects)) return false
  if (!Array.isArray(d.benchmarkWorkspaceEntries)) return false
  if (!Array.isArray(d.compareList)) return false
  if (typeof d.exportedAt !== 'number') return false
  return true
}
