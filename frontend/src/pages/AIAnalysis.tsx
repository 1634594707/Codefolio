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
import { API_BASE_URL } from '../config/api'

interface AIInsights {

  style_tags: string[]

  roast_comment: string

  tech_summary: string

}



interface GitScore {

  explanations?: Record<string, GitScoreExplanation>

  total: number

  dimensions: {

    impact: number

    contribution: number

    community: number

    tech_breadth: number

    documentation: number

  }

}

interface GenerateCachePayload {

  gitscore?: GitScore

  ai_insights?: AIInsights

  language_trends?: LanguageTrend[]

  user?: UserData

  card_data?: {

    radar_chart_data?: number[]

  }

}

interface GitScoreExplanation {

  label: string

  score: number

  max_score: number

  status: 'strong' | 'steady' | 'needs_attention' | string

  summary: string

  evidence: string[]

  next_steps: string[]

  low_data: boolean

  confidence: 'high' | 'medium' | 'low' | string

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

    scoreExplainability: 'How This Score Was Calculated',

    strongestDimension: 'Strongest signal',

    weakestDimension: 'Best improvement opportunity',

    evidence: 'Why it scored this way',

    nextSteps: 'How to improve',

    lowData: 'Limited public data',

    confidenceLow: 'Low confidence',

    confidenceMedium: 'Medium confidence',

    dimensions: {

      impact: 'Impact',

      contribution: 'Code',

      community: 'Community',

      breadth: 'Breadth',

      documentation: 'Docs',

    },

    loading: 'Analyzing…',

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

    lowData: '公开数据较少',

    confidenceLow: '置信度较低',

    confidenceMedium: '置信度中等',

    dimensions: {

      impact: '影响力',

      contribution: '代码',

      community: '社区',

      breadth: '广度',

      documentation: '文档',

    },

    loading: '分析中…',

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

  const [radarChartData, setRadarChartData] = useState<number[]>([])

  const [insights, setInsights] = useState<AIInsights | null>(null)

  const [languageTrends, setLanguageTrends] = useState<LanguageTrend[]>([])

  const [loading, setLoading] = useState(true)

  const [error, setError] = useState('')

  const text = labels[language]

  const scoreExplainabilityLabel = language === 'zh' ? '评分解释' : 'How This Score Was Calculated'

  const strongestDimensionLabel = language === 'zh' ? '当前最强维度' : 'Strongest signal'

  const weakestDimensionLabel = language === 'zh' ? '最值得优先提升' : 'Best improvement opportunity'

  const evidenceLabel = language === 'zh' ? '得分依据' : 'Why it scored this way'

  const nextStepsLabel = language === 'zh' ? '提升建议' : 'How to improve'

  const lowDataLabel = language === 'zh' ? '公开数据较少' : 'Limited public data'

  const confidenceLowLabel = language === 'zh' ? '置信度较低' : 'Low confidence'

  const confidenceMediumLabel = language === 'zh' ? '置信度中等' : 'Medium confidence'



  useLayoutEffect(() => {

    if (!username) {

      setLoading(false)

      setUserData(null)

      setGitscore(null)

      setRadarChartData([])

      setInsights(null)

      setLanguageTrends([])

      return

    }

    const cachedEntry = getGenerateCache(username, contentLanguage)

    if (cachedEntry) {

      const d = cachedEntry.data as unknown as GenerateCachePayload

      setUserData(d.user as UserData)

      setGitscore((d.gitscore as GitScore) ?? null)

      setRadarChartData(d.card_data?.radar_chart_data ?? [])

      setInsights(d.ai_insights ?? null)

      setLanguageTrends(d.language_trends ?? [])

      setLoading(false)

      setError('')

      return

    }

    setUserData(null)

    setGitscore(null)

    setRadarChartData([])

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

      setRadarChartData([])

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

        setRadarChartData(response.data.card_data?.radar_chart_data ?? [])

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



  const radarValues =

    gitscore

      ? [

          gitscore.dimensions.impact ?? radarChartData[0] ?? 0,

          gitscore.dimensions.contribution ?? radarChartData[1] ?? 0,

          gitscore.dimensions.community ?? radarChartData[2] ?? 0,

          gitscore.dimensions.tech_breadth ?? radarChartData[3] ?? 0,

          gitscore.dimensions.documentation ?? radarChartData[4] ?? 0,

        ]

      : radarChartData



  const radarData = radarValues.length > 0

    ? [

        {
          subject: text.dimensions.impact,
          value: radarValues[0] ?? 0,
          fullMark: gitscore?.explanations?.impact?.max_score ?? 35,
        },

        {
          subject: text.dimensions.contribution,
          value: radarValues[1] ?? 0,
          fullMark: gitscore?.explanations?.contribution?.max_score ?? 25,
        },

        {
          subject: text.dimensions.community,
          value: radarValues[2] ?? 0,
          fullMark: gitscore?.explanations?.community?.max_score ?? 20,
        },

        {
          subject: text.dimensions.breadth,
          value: radarValues[3] ?? 0,
          fullMark: gitscore?.explanations?.tech_breadth?.max_score ?? 15,
        },

        {
          subject: text.dimensions.documentation,
          value: radarValues[4] ?? 0,
          fullMark: gitscore?.explanations?.documentation?.max_score ?? 5,
        },

      ]

    : []



  const heatmapContributions = useMemo(() => {

    const days = userData?.contributions?.contribution_days

    if (!days?.length) return [] as number[]

    return days.map((d) => d.contribution_count)

  }, [userData])



  const dimensionExplanations = useMemo(() => {

    if (!gitscore?.explanations) return [] as GitScoreExplanation[]

    return [

      gitscore.explanations.impact,

      gitscore.explanations.contribution,

      gitscore.explanations.community,

      gitscore.explanations.tech_breadth,

      gitscore.explanations.documentation,

    ].filter(Boolean) as GitScoreExplanation[]

  }, [gitscore])



  const strongestExplanation = useMemo(() => {

    if (dimensionExplanations.length === 0) return null

    return [...dimensionExplanations].sort((a, b) => (b.score / b.max_score) - (a.score / a.max_score))[0]

  }, [dimensionExplanations])



  const weakestExplanation = useMemo(() => {

    if (dimensionExplanations.length === 0) return null

    return [...dimensionExplanations].sort((a, b) => (a.score / a.max_score) - (b.score / b.max_score))[0]

  }, [dimensionExplanations])



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

            <img src={userData.avatar_url} alt={userData.username} className="header-avatar" width={40} height={40} />

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
            <div
              role="img"
              aria-label={language === 'zh' ? 'GitScore 雷达图' : 'GitScore radar chart'}
              style={{ width: '100%', height: '100%' }}
            >
              <ResponsiveContainer width="100%" height={250}>
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



      {dimensionExplanations.length > 0 && (

        <div className="analysis-section">

          <h3 className="section-title">{scoreExplainabilityLabel}</h3>

          <div className="analysis-explainability-grid">

            {dimensionExplanations.map((explanation) => (

              <article
                key={explanation.label}
                className={`analysis-card explanation-card explanation-${explanation.status}`}
              >

                <div className="explanation-header">

                  <div>

                    <span className="card-kicker">{explanation.label}</span>

                    <h4 className="explanation-title">
                      {explanation.score.toFixed(1)} / {explanation.max_score.toFixed(0)}
                    </h4>

                  </div>

                  <div className="explanation-flags">

                    {strongestExplanation?.label === explanation.label && (

                      <span className="explanation-flag">{strongestDimensionLabel}</span>

                    )}

                    {weakestExplanation?.label === explanation.label && (

                      <span className="explanation-flag">{weakestDimensionLabel}</span>

                    )}

                    {explanation.low_data && (

                      <span className="explanation-flag explanation-flag-muted">{lowDataLabel}</span>

                    )}

                    {explanation.confidence === 'low' && (

                      <span className="explanation-flag explanation-flag-muted">{confidenceLowLabel}</span>

                    )}

                    {explanation.confidence === 'medium' && (

                      <span className="explanation-flag explanation-flag-muted">{confidenceMediumLabel}</span>

                    )}

                  </div>

                </div>

                <p className="explanation-summary">{explanation.summary}</p>

                {explanation.evidence.length > 0 && (

                  <>

                    <h5 className="explanation-subtitle">{evidenceLabel}</h5>

                    <ul className="explanation-list">

                      {explanation.evidence.map((item) => (

                        <li key={item}>{item}</li>

                      ))}

                    </ul>

                  </>

                )}

                {explanation.next_steps.length > 0 && (

                  <>

                    <h5 className="explanation-subtitle">{nextStepsLabel}</h5>

                    <ul className="explanation-list">

                      {explanation.next_steps.map((item) => (

                        <li key={item}>{item}</li>

                      ))}

                    </ul>

                  </>

                )}

              </article>

            ))}

          </div>

        </div>

      )}

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

