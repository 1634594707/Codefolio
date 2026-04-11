import { useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  AreaChart,
  Area,
} from 'recharts'

interface LanguageTrend {
  language: string
  data: { month: string; percentage: number }[]
}

interface SkillTrendsProps {
  trends: LanguageTrend[]
  language: 'en' | 'zh'
}

const labels = {
  en: {
    title: 'Language Trends',
    subtitle: '12-month trend from public repo language bytes and last push dates',
    topLanguages: 'Top Languages',
    evolution: 'Evolution',
    usage: 'Usage %',
    months: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    emptyState:
      'Not enough GitHub language data to plot trends. Ensure your token can read your repos and that they report languages.',
    insights: {
      growing: 'Growing',
      declining: 'Declining',
      stable: 'Stable',
      new: 'New Adoption',
    },
  },
  zh: {
    title: '语言趋势',
    subtitle: '基于公开仓库语言字节与最后推送时间的近 12 个月趋势',
    topLanguages: '主要语言',
    evolution: '演变',
    usage: '使用占比 %',
    months: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
    emptyState:
      '暂无可用语言趋势数据。请确认 Token 可读取仓库，且仓库能返回语言统计。',
    insights: {
      growing: '增长中',
      declining: '下降中',
      stable: '稳定',
      new: '新采用',
    },
  },
}

export function SkillTrends({ trends: propTrends, language }: SkillTrendsProps) {
  const text = labels[language]

  const trends = useMemo(() => {
    if (propTrends && propTrends.length > 0) return propTrends
    return []
  }, [propTrends])

  // Combine all trends into chart data
  const chartData = useMemo(() => {
    if (trends.length === 0) return []
    
    const months = trends[0].data.map((d) => d.month)
    return months.map((month, index) => {
      const point: Record<string, number | string> = { month }
      trends.forEach((trend) => {
        point[trend.language] = trend.data[index]?.percentage || 0
      })
      return point
    })
  }, [trends])

  // Calculate insights
  const insights = useMemo(() => {
    return trends.map((trend) => {
      const first = trend.data[0]?.percentage || 0
      const last = trend.data[trend.data.length - 1]?.percentage || 0
      const change = last - first
      const max = Math.max(...trend.data.map((d) => d.percentage))
      
      let status: 'growing' | 'declining' | 'stable' | 'new' = 'stable'
      if (first < 5 && last > 10) status = 'new'
      else if (change > 5) status = 'growing'
      else if (change < -5) status = 'declining'
      
      return {
        language: trend.language,
        change,
        max,
        current: last,
        status,
      }
    })
  }, [trends])

  const colors = ['#2a6edb', '#6f4bd8', '#1f9e51', '#f59e0b', '#ef4444']

  if (trends.length === 0) {
    return (
      <div className="skill-trends">
        <div className="trends-header">
          <h3 className="trends-title">{text.title}</h3>
          <p className="trends-subtitle">{text.subtitle}</p>
        </div>
        <p className="trends-empty" style={{ color: 'var(--color-on-surface-variant)', marginTop: '0.75rem' }}>
          {text.emptyState}
        </p>
      </div>
    )
  }

  return (
    <div className="skill-trends">
      {/* Header */}
      <div className="trends-header">
        <h3 className="trends-title">{text.title}</h3>
        <p className="trends-subtitle">{text.subtitle}</p>
      </div>

      {/* Insights Cards */}
      <div className="trends-insights">
        {insights.map((insight, index) => (
          <div
            key={insight.language}
            className={`trend-insight-card trend-${insight.status}`}
            style={{ borderColor: colors[index % colors.length] }}
          >
            <div className="trend-insight-header">
              <span className="trend-language" style={{ color: colors[index % colors.length] }}>
                {insight.language}
              </span>
              <span className={`trend-status trend-status-${insight.status}`}>
                {text.insights[insight.status]}
              </span>
            </div>
            <div className="trend-insight-stats">
              <div className="trend-stat">
                <span className="trend-stat-value">{insight.current.toFixed(1)}%</span>
                <span className="trend-stat-label">{text.usage}</span>
              </div>
              <div className="trend-stat">
                <span className={`trend-stat-value ${insight.change >= 0 ? 'trend-up' : 'trend-down'}`}>
                  {insight.change >= 0 ? '+' : ''}{insight.change.toFixed(1)}%
                </span>
                <span className="trend-stat-label">YoY</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Line Chart */}
      <div className="trends-chart-section">
        <h4 className="trends-chart-title">{text.evolution}</h4>
        <div className="trends-chart-wrapper">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" />
              <XAxis
                dataKey="month"
                tick={{ fill: 'var(--color-on-surface-variant)', fontSize: 12 }}
              />
              <YAxis
                tick={{ fill: 'var(--color-on-surface-variant)', fontSize: 12 }}
                unit="%"
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--color-surface-container)',
                  border: '1px solid var(--color-outline-variant)',
                  borderRadius: '8px',
                }}
              />
              <Legend />
              {trends.map((trend, index) => (
                <Line
                  key={trend.language}
                  type="monotone"
                  dataKey={trend.language}
                  stroke={colors[index % colors.length]}
                  strokeWidth={2}
                  dot={{ fill: colors[index % colors.length], strokeWidth: 0, r: 3 }}
                  activeDot={{ r: 5 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Stacked Area Chart */}
      <div className="trends-chart-section">
        <h4 className="trends-chart-title">{text.topLanguages}</h4>
        <div className="trends-chart-wrapper">
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" />
              <XAxis
                dataKey="month"
                tick={{ fill: 'var(--color-on-surface-variant)', fontSize: 12 }}
              />
              <YAxis
                tick={{ fill: 'var(--color-on-surface-variant)', fontSize: 12 }}
                unit="%"
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--color-surface-container)',
                  border: '1px solid var(--color-outline-variant)',
                  borderRadius: '8px',
                }}
              />
              <Legend />
              {trends.slice(0, 4).map((trend, index) => (
                <Area
                  key={trend.language}
                  type="monotone"
                  dataKey={trend.language}
                  stackId="1"
                  stroke={colors[index % colors.length]}
                  fill={colors[index % colors.length]}
                  fillOpacity={0.3}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
