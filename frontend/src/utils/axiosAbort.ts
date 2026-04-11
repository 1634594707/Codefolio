import axios from 'axios'

/** 请求被 AbortController / axios 取消（不计入业务错误）。 */
export function isRequestAborted(err: unknown): boolean {
  if (axios.isCancel(err)) return true
  if (typeof err !== 'object' || err === null) return false
  const e = err as { code?: string; name?: string }
  return e.code === 'ERR_CANCELED' || e.name === 'CanceledError' || e.name === 'AbortError'
}
