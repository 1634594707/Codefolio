import React from 'react'

interface Props {
  children: React.ReactNode
  language?: 'en' | 'zh'
}

interface State {
  hasError: boolean
  errorMessage: string
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, errorMessage: '' }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message || 'An unexpected error occurred.' }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error('[ErrorBoundary] Caught error:', error, info)
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      const isZh = this.props.language === 'zh'
      return (
        <div className="error-boundary-fallback" style={{ padding: '2rem', textAlign: 'center' }}>
          <h2>{isZh ? '页面出现错误' : 'Something went wrong'}</h2>
          <p style={{ color: 'var(--color-on-surface-variant)', marginBottom: '1.5rem' }}>
            {isZh ? '请尝试重新加载页面。' : 'Please try reloading the page.'}
          </p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
            <button
              onClick={() => window.location.reload()}
              style={{ padding: '0.5rem 1.5rem', cursor: 'pointer' }}
            >
              {isZh ? '重新加载' : 'Reload'}
            </button>
            <a href="/" style={{ padding: '0.5rem 1.5rem' }}>
              {isZh ? '返回首页' : 'Go Home'}
            </a>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
