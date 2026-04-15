type Language = 'en' | 'zh'

export interface HistoryItem {
  id: string
  username: string
  avatarUrl: string
  gitscore: number
  timestamp: number
  language: Language
}

export function readHistoryItems(): HistoryItem[] {
  if (typeof window === 'undefined') return []
  const saved = localStorage.getItem('codefolio-history')
  if (!saved) return []

  try {
    return JSON.parse(saved) as HistoryItem[]
  } catch {
    return []
  }
}
