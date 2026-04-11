import { useMemo } from 'react'

interface ContributionHeatmapProps {
  /** Daily contribution counts in calendar order (GitHub API order). Empty = no data. */
  contributions: number[]
  language: 'en' | 'zh'
}

const labels = {
  en: {
    less: 'Less',
    more: 'More',
    contributions: 'contributions',
    pastYear: 'Past Year',
    total: 'Total',
    longestStreak: 'Longest Streak',
    currentStreak: 'Current Streak',
    days: 'days',
    noData: 'No contribution calendar data for this profile.',
  },
  zh: {
    less: '较少',
    more: '较多',
    contributions: '次贡献',
    pastYear: '过去一年',
    total: '总计',
    longestStreak: '最长连续',
    currentStreak: '当前连续',
    days: '天',
    noData: '暂无贡献日历数据。',
  },
}

export function ContributionHeatmap({ contributions, language }: ContributionHeatmapProps) {
  const text = labels[language]

  const { grid, stats, hasData } = useMemo(() => {
    const data = contributions.length > 0 ? contributions : []

    const total = data.reduce((a, b) => a + b, 0)
    let longestStreak = 0
    let currentStreak = 0
    let tempStreak = 0

    for (let i = 0; i < data.length; i++) {
      if (data[i] > 0) {
        tempStreak++
        longestStreak = Math.max(longestStreak, tempStreak)
      } else {
        tempStreak = 0
      }
    }

    // Calculate current streak (from end)
    for (let i = data.length - 1; i >= 0; i--) {
      if (data[i] > 0) {
        currentStreak++
      } else {
        break
      }
    }

    // Organize into weeks (7 days per week, 53 weeks max)
    const weeks: number[][] = []
    for (let i = 0; i < data.length; i += 7) {
      weeks.push(data.slice(i, i + 7))
    }

    return {
      grid: weeks,
      stats: { total, longestStreak, currentStreak },
      hasData: data.length > 0,
    }
  }, [contributions])

  if (!hasData) {
    return (
      <div className="contribution-heatmap">
        <p className="heatmap-empty" style={{ color: 'var(--color-on-surface-variant)', margin: 0 }}>
          {text.noData}
        </p>
      </div>
    )
  }

  const getLevel = (count: number): number => {
    if (count === 0) return 0
    if (count === 1) return 1
    if (count <= 3) return 2
    if (count <= 5) return 3
    return 4
  }

  const getColor = (level: number): string => {
    const colors = [
      'var(--color-outline-variant)', // 0
      'rgba(31, 158, 81, 0.3)', // 1
      'rgba(31, 158, 81, 0.5)', // 2
      'rgba(31, 158, 81, 0.7)', // 3
      'rgba(31, 158, 81, 1)', // 4
    ]
    return colors[level]
  }

  const months = language === 'zh' 
    ? ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    : ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

  const weekDays = language === 'zh'
    ? ['一', '三', '五']
    : ['Mon', 'Wed', 'Fri']

  return (
    <div className="contribution-heatmap">
      {/* Stats */}
      <div className="heatmap-stats">
        <div className="heatmap-stat">
          <span className="heatmap-stat-value">{stats.total.toLocaleString()}</span>
          <span className="heatmap-stat-label">{text.contributions} {text.pastYear}</span>
        </div>
        <div className="heatmap-stat">
          <span className="heatmap-stat-value">{stats.longestStreak}</span>
          <span className="heatmap-stat-label">{text.longestStreak} {text.days}</span>
        </div>
        <div className="heatmap-stat">
          <span className="heatmap-stat-value">{stats.currentStreak}</span>
          <span className="heatmap-stat-label">{text.currentStreak} {text.days}</span>
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="heatmap-container">
        {/* Month labels */}
        <div className="heatmap-months">
          {months.map((month) => (
            <span key={month} className="heatmap-month-label">{month}</span>
          ))}
        </div>

        <div className="heatmap-grid-wrapper">
          {/* Week day labels */}
          <div className="heatmap-weekdays">
            {weekDays.map((day) => (
              <span key={day} className="heatmap-weekday-label">{day}</span>
            ))}
          </div>

          {/* Grid */}
          <div className="heatmap-grid">
            {grid.map((week, weekIndex) => (
              <div key={weekIndex} className="heatmap-week">
                {week.map((count, dayIndex) => {
                  const level = getLevel(count)
                  return (
                    <div
                      key={`${weekIndex}-${dayIndex}`}
                      className="heatmap-cell"
                      style={{ backgroundColor: getColor(level) }}
                      title={`${count} ${text.contributions}`}
                    />
                  )
                })}
              </div>
            ))}
          </div>
        </div>

        {/* Legend */}
        <div className="heatmap-legend">
          <span>{text.less}</span>
          {[0, 1, 2, 3, 4].map((level) => (
            <div
              key={level}
              className="heatmap-legend-cell"
              style={{ backgroundColor: getColor(level) }}
            />
          ))}
          <span>{text.more}</span>
        </div>
      </div>
    </div>
  )
}
