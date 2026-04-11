import { useEffect, useLayoutEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import axios from 'axios'
import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from 'recharts'
import { ContributionHeatmap } from '../components/ContributionHeatmap'
import { SkillTrends } from '../components/SkillTrends'
import { useApp } from '../context'
import { isRequestAborted } from '../utils/axiosAbort'

interface AIInsights {
  style_tags: string[]
  roast_comment: string
  tech_summary: string
}

interface GitScore {
  total: number
  dimensions: {
    impact: number
    contribution: number
    community: number
    tech_breadth: number
    documentation: number
  }
}

interface ContributionDay {
  date: string
  contribution_count: number
}

interface UserData {
  username: string
  avatar_url: string
  bio: string
  contributions?: {
    contribution_days: ContributionDay[]
  }
}

interface LanguageTrend {
  language: string
  data: { month: string; percentage: number }[]
}

interface AIAnalysisProps {
  language: 'en' | 'zh'
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const labels = {
  en: {
    title: 'AI Analysis',
    subtitle: 'Technical Authority',
    score: 'GitScore',
    insights: 'AI Insights',
    tags: 'Style Tags',
    roast: 'The Roast',
    summary: 'Technical Summary',
    contributions: 'Contributions',
    trends: 'Skill Trends',
    dimensions: {
      impact: 'Impact',
      contribution: 'Code',
      community: 'Community',
      breadth: 'Breadth',
      documentation: 'Docs',
    },
    loading: 'Analyzing...',
    error: 'Failed to load analysis',
    noUser: 'Enter a GitHub username to view AI analysis',
  },
  zh: {
    title: 'AI 分析',
    subtitle: '技术权威指数',
    score: 'GitScore',
    insights: 'AI 洞察',
    tags: '风格标签',
    roast: 'AI 点评',
    summary: '技术总结',
    contributions: '贡献热力图',
    trends: '技能趋势',
    dimensions: {
      impact: '影响力',
      contribution: '代码',
      community: '社区',
      breadth: '广度',
      documentation: '文档',
    },
    loading: '分析中...',
    error: '加载分析失败',
    noUser: '输入 GitHub 用户名查看 AI 分析',
  },
}

export function AIAnalysis({ language }: AIAnalysisProps) {
  const { contentLanguage, getGenerateCache, cacheGenerateResult } = useApp()
  const [searchParams] = useSearchParams()
  const username = searchParams.get('user') || ''
  const [userData, setUserData] = useState<UserData | null>(null)
  const [gitscore, setGitscore] = useState<GitScore | null>(null)
  const [insights, setInsights] = useState<AIInsights | null>(null)
  const [languageTrends, setLanguageTrends] = useState<LanguageTrend[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const text = labels[language]

  useLayoutEffect(() => {
    if (!username) {
      setLoading(false)
      setUserData(null)
      setGitscore(null)
      setInsights(null)
      setLanguageTrends([])
      return
    }
    const cachedEntry = getGenerateCache(username, contentLanguage)
    if (cachedEntry) {
      const d = cachedEntry.data
      setUserData(d.user as UserData)
      setGitscore(d.gitscore as GitScore)
      setInsights(d.ai_insights)
      setLanguageTrends(d.language_trends ?? [])
      setLoading(false)
      setError('')
      return
    }
    setUserData(null)
    setGitscore(null)
    setInsights(null)
    setLanguageTrends([])
    setLoading(true)
    setError('')
  }, [username, contentLanguage, getGenerateCache])

  useEffect(() => {
    if (!username) return
    if (getGenerateCache(username, contentLanguage)) {
      return
    }

    let cancelled = false
    const abortController = new AbortController()

    const fetchData = async () => {
      setLoading(true)
      setError('')
      setUserData(null)
      setGitscore(null)
      setInsights(null)
      setLanguageTrends([])
      try {
        const response = await axios.post(
          `${API_BASE_URL}/api/generate`,
          {
            username,
            language: contentLanguage,
          },
          { signal: abortController.signal },
        )
        if (cancelled) return
        cacheGenerateResult({
          username: response.data.user.username,
          contentLanguage,
          data: response.data,
        })
        setUserData(response.data.user)
        setGitscore(response.data.gitscore)
        setInsights(response.data.ai_insights)
        setLanguageTrends(response.data.language_trends ?? [])
      } catch (err) {
        if (isRequestAborted(err) || cancelled) return
        setError(text.error)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void fetchData()
    return () => {
      cancelled = true
      abortController.abort()
    }
  }, [username, contentLanguage, getGenerateCache, cacheGenerateResult, text.error])

  const radarData = gitscore
    ? [
        { subject: text.dimensions.impact, value: gitscore.dimensions.impact, fullMark: 35 },
        { subject: text.dimensions.contribution, value: gitscore.dimensions.contribution, fullMark: 25 },
        { subject: text.dimensions.community, value: gitscore.dimensions.community, fullMark: 20 },
        { subject: text.dimensions.breadth, value: gitscore.dimensions.tech_breadth, fullMark: 15 },
        { subject: text.dimensions.documentation, value: gitscore.dimensions.documentation, fullMark: 5 },
      ]
    : []

  const heatmapContributions = useMemo(() => {
    const days = userData?.contributions?.contribution_days
    if (!days?.length) return [] as number[]
    return days.map((d) => d.contribution_count)
  }, [userData])

  if (!username) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <p>{text.noUser}</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading-state">
          <p>{text.loading}</p>
        </div>
      </div>
    )
  }

  if (error || !gitscore || !insights) {
    return (
      <div className="page-container">
        <div className="error-state">
          <p>{error || text.error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">{text.title}</h1>
        {userData && (
          <div className="user-header">
            <img src={userData.avatar_url} alt={userData.username} className="header-avatar" />
            <span className="header-username">@{userData.username}</span>
          </div>
        )}
      </div>

      <div className="analysis-grid">
        {/* Score Card */}
        <div className="analysis-card score-card">
          <span className="card-kicker">{text.subtitle}</span>
          <div className="score-display-large">
            <span className="score-number">{gitscore.total.toFixed(0)}</span>
            <span className="score-total">/100</span>
          </div>
          <p className="tech-summary">{insights.tech_summary}</p>
        </div>

        {/* Radar Chart */}
        <div className="analysis-card radar-card">
          <h3 className="card-title">{text.score}</h3>
          <div className="radar-wrapper">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="var(--color-outline-variant)" />
                <PolarAngleAxis
                  dataKey="subject"
                  tick={{ fill: 'var(--color-on-surface-variant)', fontSize: 12 }}
                />
                <Radar
                  name="GitScore"
                  dataKey="value"
                  stroke="var(--color-primary)"
                  fill="var(--color-primary)"
                  fillOpacity={0.3}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Style Tags */}
        <div className="analysis-card tags-card">
          <h3 className="card-title">{text.tags}</h3>
          <div className="tags-cloud">
            {insights.style_tags.map((tag) => (
              <span key={tag} className="style-tag">
                {tag}
              </span>
            ))}
          </div>
        </div>

        {/* Roast */}
        {insights.roast_comment && (
          <div className="analysis-card roast-card">
            <h3 className="card-title">{text.roast}</h3>
            <blockquote className="roast-text">
              "{insights.roast_comment}"
            </blockquote>
          </div>
        )}
      </div>

      {/* Contribution Heatmap */}
      <div className="analysis-section">
        <h3 className="section-title">{text.contributions}</h3>
        <div className="analysis-card full-width">
          <ContributionHeatmap contributions={heatmapContributions} language={language} />
        </div>
      </div>

      {/* Skill Trends */}
      <div className="analysis-section">
        <h3 className="section-title">{text.trends}</h3>
        <div className="analysis-card full-width">
          <SkillTrends trends={languageTrends} language={language} />
        </div>
      </div>
    </div>
  )
}
