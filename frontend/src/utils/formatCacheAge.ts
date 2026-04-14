const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000

/**
 * Returns true if the ISO timestamp is older than 7 days.
 */
export function isStale(isoString: string): boolean {
  const date = new Date(isoString)
  if (Number.isNaN(date.getTime())) return false
  return Date.now() - date.getTime() > SEVEN_DAYS_MS
}

/**
 * Formats an ISO timestamp as a human-readable cache age string.
 * e.g. "Updated 2 hours ago", "Updated 3 days ago"
 */
export function formatCacheAge(isoString: string): string {
  const date = new Date(isoString)
  if (Number.isNaN(date.getTime())) return isoString

  const diffMs = Date.now() - date.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)

  if (diffSeconds < 60) return 'Updated just now'

  const diffMinutes = Math.floor(diffSeconds / 60)
  if (diffMinutes < 60) return `Updated ${diffMinutes} ${diffMinutes === 1 ? 'minute' : 'minutes'} ago`

  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `Updated ${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`

  const diffDays = Math.floor(diffHours / 24)
  return `Updated ${diffDays} ${diffDays === 1 ? 'day' : 'days'} ago`
}
