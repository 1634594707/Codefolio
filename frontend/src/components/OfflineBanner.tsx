import { useEffect, useState } from 'react'

interface OfflineBannerProps {
  language?: 'en' | 'zh'
}

export function OfflineBanner({ language = 'en' }: OfflineBannerProps) {
  const [isOffline, setIsOffline] = useState(!navigator.onLine)

  useEffect(() => {
    const handleOnline = () => setIsOffline(false)
    const handleOffline = () => setIsOffline(true)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  if (!isOffline) return null

  return (
    <div
      className="offline-banner"
      role="alert"
      aria-live="polite"
      style={{
        background: 'var(--color-error-container, #fef2f2)',
        color: 'var(--color-on-error-container, #991b1b)',
        padding: '8px 24px',
        fontSize: '0.85rem',
        textAlign: 'center',
        borderBottom: '1px solid var(--color-outline-variant)',
      }}
    >
      {language === 'zh'
        ? '网络已断开，部分功能不可用'
        : 'You are offline. Some features may be unavailable.'}
    </div>
  )
}
