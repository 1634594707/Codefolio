interface SkeletonScreenProps {
  language: 'en' | 'zh'
}

export function SkeletonScreen(_props: SkeletonScreenProps) {
  return (
    <div className="skeleton-screen">
      <div className="skeleton-container">
        {/* Score Panel Skeleton */}
        <div className="skeleton-card skeleton-score-panel">
          <div className="skeleton-header">
            <div className="skeleton-avatar" />
            <div className="skeleton-text-group">
              <div className="skeleton-text skeleton-text-sm" />
              <div className="skeleton-text skeleton-text-md" style={{ marginTop: '8px' }} />
            </div>
          </div>
          <div className="skeleton-score-number" />
          <div className="skeleton-text skeleton-text-lg" style={{ marginTop: '16px' }} />
          <div className="skeleton-meta-row">
            <div className="skeleton-text skeleton-text-sm" style={{ flex: 1 }} />
            <div className="skeleton-text skeleton-text-sm" style={{ flex: 1 }} />
          </div>
        </div>

        {/* Breakdown Panel Skeleton */}
        <div className="skeleton-card">
          <div className="skeleton-text skeleton-text-sm" />
          <div className="skeleton-chart" />
          <div className="skeleton-metric-grid">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="skeleton-metric-card" />
            ))}
          </div>
        </div>

        {/* Insights Panel Skeleton */}
        <div className="skeleton-card">
          <div className="skeleton-text skeleton-text-sm" />
          <div className="skeleton-tags">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton-tag" />
            ))}
          </div>
          <div className="skeleton-text skeleton-text-lg" style={{ marginTop: '16px' }} />
          <div className="skeleton-text skeleton-text-md" style={{ marginTop: '8px' }} />
        </div>

        {/* Projects Panel Skeleton */}
        <div className="skeleton-card">
          <div className="skeleton-text skeleton-text-sm" />
          <div className="skeleton-projects">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="skeleton-project-card">
                <div className="skeleton-text skeleton-text-md" />
                <div className="skeleton-text skeleton-text-sm" style={{ marginTop: '8px' }} />
                <div className="skeleton-text skeleton-text-sm" style={{ marginTop: '8px', width: '60%' }} />
              </div>
            ))}
          </div>
        </div>

        {/* Resume Panel Skeleton */}
        <div className="skeleton-card skeleton-wide">
          <div className="skeleton-text skeleton-text-sm" />
          <div className="skeleton-resume">
            <div className="skeleton-text skeleton-text-lg" />
            <div className="skeleton-text skeleton-text-md" style={{ marginTop: '12px' }} />
            <div className="skeleton-text skeleton-text-md" style={{ marginTop: '12px' }} />
            <div className="skeleton-text skeleton-text-md" style={{ marginTop: '12px', width: '80%' }} />
          </div>
        </div>

        {/* Social Card Panel Skeleton */}
        <div className="skeleton-card skeleton-wide">
          <div className="skeleton-text skeleton-text-sm" />
          <div className="skeleton-social-card">
            <div className="skeleton-social-header">
              <div className="skeleton-avatar skeleton-large-avatar" />
              <div className="skeleton-social-score" />
            </div>
            <div className="skeleton-tags">
              {[1, 2, 3].map((i) => (
                <div key={i} className="skeleton-tag" />
              ))}
            </div>
            <div className="skeleton-tech-icons">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="skeleton-tech-icon" />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Animated background pulse */}
      <div className="skeleton-pulse-bg" />
    </div>
  )
}
