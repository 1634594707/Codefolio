import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import axios from 'axios'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  Legend,
} from 'recharts'
import { useApp } from '../context'
import { isRequestAborted } from '../utils/axiosAbort'
import { githubLoginEquals } from '../utils/githubLogin'
import { splitGitHubUsernameInputs, validateGitHubUsername } from '../utils/githubInput'

interface CompareUser {
  username: string
  avatar_url: string
  gitscore: number
  dimensions: {
    impact: number
    contribution: number
    community: number
    tech_breadth: number
    documentation: number
  }
  style_tags: string[]
  roast_comment: string
  tech_summary: string
  followers: number
  following: number
  repositories_count: number
  total_stars: number
  languages: Record<string, number>
}

interface CompareProps {
  language: 'en' | 'zh'
}

type DimensionKey = keyof CompareUser['dimensions']

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const dimensionKeys: DimensionKey[] = [
  'impact',
  'contribution',
  'community',
  'tech_breadth',
  'documentation',
]

const labels = {
  en: {
    title: 'Compare Developers',
    subtitle: 'Side-by-side profile comparison',
    tabsUsers: 'Developers',
    tabsRepos: 'Repositories',
    addUser: 'Add User',
    remove: 'Remove',
    comparisonInsights: 'Comparison Insights',
    overallLeader: 'Overall Leader',
    strongestEdge: 'Strongest Edge',
    closeChallenger: 'Closest Challenger',
    strongestDimension: 'Strongest Dimension',
    dimensionWins: 'Dimension Wins',
    topStrengths: 'Top strengths',
    leadBy: 'Lead by',
    points: 'pts',
    tiedMatch: 'This matchup is extremely close.',
    edgeSummary: 'Largest gap currently shows up in',
    dimensions: {
      impact: 'Reach',
      contribution: 'Output',
      community: 'Community',
      breadth: 'Stack Range',
      documentation: 'Documentation',
    },
    stats: 'Statistics',
    followers: 'Followers',
    following: 'Following',
    repos: 'Repositories',
    stars: 'Total Stars',
    loading: 'Loading...',
    error: 'Failed to load',
    empty: 'Add GitHub usernames to compare',
    invalidInput: 'Use GitHub usernames or profile links only.',
    partialFailure: 'Some users could not be loaded',
    maxUsers: 'Maximum 3 users',
  },
  zh: {
    title: '开发者对比',
    subtitle: '并排查看 GitHub 用户画像',
    tabsUsers: '开发者',
    tabsRepos: '仓库对标',
    addUser: '添加用户',
    remove: '移除',
    comparisonInsights: '对比结论',
    overallLeader: '当前领先者',
    strongestEdge: '最强优势',
    closeChallenger: '最接近的挑战者',
    strongestDimension: '最强维度',
    dimensionWins: '维度领先数',
    topStrengths: '核心优势',
    leadBy: '领先',
    points: '分',
    tiedMatch: '这组对比非常接近。',
    edgeSummary: '当前最大的差距出现在',
    dimensions: {
      impact: '影响力',
      contribution: '代码',
      community: '社区',
      breadth: '广度',
      documentation: '文档',
    },
    stats: '统计数据',
    followers: '关注者',
    following: '正在关注',
    repos: '仓库数',
    stars: '总星标',
    loading: '加载中...',
    error: '加载失败',
    empty: '添加 GitHub 用户名进行对比',
    invalidInput: '请输入 GitHub 用户名或主页链接。',
    partialFailure: '以下用户加载失败',
    maxUsers: '最多 3 个用户',
  },
} as const

function CompareModeTabs(_: CompareProps) {
  return null
}

export function Compare({ language }: CompareProps) {
  const [searchParams, setSearchParams] = useSearchParams()
  const {
    compareList,
    setCompareList,
    addToCompare,
    removeFromCompare,
    contentLanguage,
    getGenerateCache,
    cacheGenerateResult,
  } = useApp()
  const [users, setUsers] = useState<CompareUser[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [inputValue, setInputValue] = useState('')
  const [inputError, setInputError] = useState('')
  const [failedUsers, setFailedUsers] = useState<string[]>([])
  const text = labels[language]

  useEffect(() => {
    const urlUsers = splitGitHubUsernameInputs(searchParams.get('users') ?? '')
    const uniqueUsers = urlUsers.filter(
      (item, index, list) => list.findIndex((value) => githubLoginEquals(value, item)) === index,
    )
    if (uniqueUsers.length > 0 && JSON.stringify(uniqueUsers) !== JSON.stringify(compareList)) {
      setCompareList(uniqueUsers.slice(0, 3))
    }
  }, [searchParams, compareList, setCompareList])

  const usernames = compareList

  useEffect(() => {
    if (usernames.length === 0) {
      setUsers([])
      return
    }

    let cancelled = false
    const abortController = new AbortController()

    const fetchUsers = async () => {
      setLoading(true)
      setError('')
      setFailedUsers([])
      try {
        const results = await Promise.allSettled(
          usernames.slice(0, 3).map(async (username) => {
            const cachedEntry = getGenerateCache(username, contentLanguage)
            const data =
              cachedEntry?.data ??
              (
                await axios.post(
                  `${API_BASE_URL}/api/generate`,
                  {
                    username: username.trim(),
                    language: contentLanguage,
                  },
                  { signal: abortController.signal },
                )
              ).data

            if (!cachedEntry) {
              cacheGenerateResult({
                username: data.user.username,
                contentLanguage,
                data,
              })
            }

            const activeOutput = data.localized_outputs[contentLanguage]
            return {
              username: data.user.username,
              avatar_url: data.user.avatar_url,
              gitscore: data.gitscore.total,
              dimensions: {
                impact: data.gitscore.dimensions.impact || 0,
                contribution: data.gitscore.dimensions.contribution || 0,
                community: data.gitscore.dimensions.community || 0,
                tech_breadth: data.gitscore.dimensions.tech_breadth || 0,
                documentation: data.gitscore.dimensions.documentation || 0,
              },
              style_tags: activeOutput?.ai_insights.style_tags || [],
              roast_comment: activeOutput?.ai_insights.roast_comment || '',
              tech_summary: activeOutput?.ai_insights.tech_summary || '',
              followers: data.user.followers,
              following: data.user.following,
              repositories_count: data.user.repositories.length,
              total_stars: data.user.repositories.reduce(
                (sum: number, repository: { stars: number }) => sum + repository.stars,
                0,
              ),
              languages: data.user.languages,
            }
          }),
        )
        if (cancelled) return

        const fulfilledUsers = results
          .filter((result): result is PromiseFulfilledResult<CompareUser> => result.status === 'fulfilled')
          .map((result) => result.value)
        const rejectedUsers = results
          .map((result, index) => (result.status === 'rejected' ? usernames[index] : null))
          .filter(Boolean) as string[]

        setUsers(fulfilledUsers)
        setFailedUsers(rejectedUsers)
        if (fulfilledUsers.length === 0 && rejectedUsers.length > 0) {
          setError(text.error)
        }
      } catch (requestError) {
        if (isRequestAborted(requestError) || cancelled) return
        setError(text.error)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void fetchUsers()
    return () => {
      cancelled = true
      abortController.abort()
    }
  }, [usernames, contentLanguage, getGenerateCache, cacheGenerateResult, text.error])

  const addUser = () => {
    const candidates = splitGitHubUsernameInputs(inputValue)
    if (candidates.length === 0) {
      setInputError(text.invalidInput)
      return
    }
    if (usernames.length >= 3) {
      setInputError(text.maxUsers)
      return
    }

    const validCandidates = candidates
      .map((candidate) => validateGitHubUsername(candidate))
      .filter((item): item is { valid: true; username: string } => item.valid)
      .map((item) => item.username)

    if (validCandidates.length === 0) {
      setInputError(text.invalidInput)
      return
    }

    const mergedUsernames = [...usernames]
    for (const candidate of validCandidates) {
      if (mergedUsernames.some((item) => githubLoginEquals(item, candidate))) continue
      if (mergedUsernames.length >= 3) break
      addToCompare(candidate)
      mergedUsernames.push(candidate)
    }

    if (mergedUsernames.length > 0) {
      setSearchParams({ users: mergedUsernames.join(',') })
    }
    setInputValue('')
    setInputError('')
  }

  const removeUser = (username: string) => {
    removeFromCompare(username)
    const nextUsernames = usernames.filter((user) => user !== username)
    if (nextUsernames.length > 0) {
      setSearchParams({ users: nextUsernames.join(',') })
    } else {
      setSearchParams({})
    }
  }

  const radarData = [
    { subject: text.dimensions.impact, ...Object.fromEntries(users.map((user) => [user.username, user.dimensions.impact])) },
    {
      subject: text.dimensions.contribution,
      ...Object.fromEntries(users.map((user) => [user.username, user.dimensions.contribution])),
    },
    { subject: text.dimensions.community, ...Object.fromEntries(users.map((user) => [user.username, user.dimensions.community])) },
    {
      subject: text.dimensions.breadth,
      ...Object.fromEntries(users.map((user) => [user.username, user.dimensions.tech_breadth])),
    },
    {
      subject: text.dimensions.documentation,
      ...Object.fromEntries(users.map((user) => [user.username, user.dimensions.documentation])),
    },
  ]

  const barData = [
    { name: text.dimensions.impact, ...Object.fromEntries(users.map((user) => [user.username, user.dimensions.impact])) },
    {
      name: text.dimensions.contribution,
      ...Object.fromEntries(users.map((user) => [user.username, user.dimensions.contribution])),
    },
    { name: text.dimensions.community, ...Object.fromEntries(users.map((user) => [user.username, user.dimensions.community])) },
    {
      name: text.dimensions.breadth,
      ...Object.fromEntries(users.map((user) => [user.username, user.dimensions.tech_breadth])),
    },
    {
      name: text.dimensions.documentation,
      ...Object.fromEntries(users.map((user) => [user.username, user.dimensions.documentation])),
    },
  ]

  const statsData = users.map((user) => ({
    username: user.username,
    gitscore: user.gitscore,
    followers: user.followers,
    following: user.following,
    repos: user.repositories_count,
    stars: user.total_stars,
  }))

  const colors = ['#0f766e', '#c2410c', '#1d4ed8']

  const compareInsights = useMemo(() => {
    if (users.length === 0) return null

    const dimensionLabels: Record<DimensionKey, string> = {
      impact: text.dimensions.impact,
      contribution: text.dimensions.contribution,
      community: text.dimensions.community,
      tech_breadth: text.dimensions.breadth,
      documentation: text.dimensions.documentation,
    }

    const rankedUsers = [...users].sort((a, b) => b.gitscore - a.gitscore)
    const leader = rankedUsers[0]
    const runnerUp = rankedUsers[1] ?? null
    const leadMargin = runnerUp ? leader.gitscore - runnerUp.gitscore : 0

    const dimensionLeaders = dimensionKeys.map((key) => {
      const ranked = [...users].sort((a, b) => b.dimensions[key] - a.dimensions[key])
      return {
        key,
        label: dimensionLabels[key],
        winner: ranked[0],
        margin: ranked[1] ? ranked[0].dimensions[key] - ranked[1].dimensions[key] : ranked[0].dimensions[key],
      }
    })

    const winsByUser = new Map<string, number>()
    const strongestByUser = new Map<string, string>()
    const topStrengthsByUser = new Map<string, string[]>()

    for (const item of dimensionLeaders) {
      winsByUser.set(item.winner.username, (winsByUser.get(item.winner.username) ?? 0) + 1)
    }

    for (const user of users) {
      const rankedDimensions = dimensionKeys
        .map((key) => ({
          label: dimensionLabels[key],
          value: user.dimensions[key],
        }))
        .sort((a, b) => b.value - a.value)
      strongestByUser.set(user.username, rankedDimensions[0].label)
      topStrengthsByUser.set(
        user.username,
        rankedDimensions.slice(0, 2).map((item) => item.label),
      )
    }

    const dominantDimension = [...dimensionLeaders].sort((a, b) => b.margin - a.margin)[0]

    return {
      leader,
      runnerUp,
      leadMargin,
      dominantDimension,
      winsByUser,
      strongestByUser,
      topStrengthsByUser,
    }
  }, [users, text])

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">{text.title}</h1>
        <p className="page-subtitle">{text.subtitle}</p>
      </div>

      <CompareModeTabs language={language} />

      <div className="compare-input-section">
        <div className="compare-input-wrapper">
          <input
            type="text"
            value={inputValue}
            onChange={(event) => {
              setInputValue(event.target.value)
              if (inputError) setInputError('')
            }}
            placeholder={text.addUser}
            className="compare-input"
            onKeyDown={(event) => event.key === 'Enter' && addUser()}
          />
          <button className="compare-add-btn" onClick={addUser} disabled={usernames.length >= 3}>
            {text.addUser}
          </button>
        </div>
        {inputError && <p className="compare-hint">{inputError}</p>}
        {usernames.length === 0 && <p className="compare-hint">{text.empty}</p>}
      </div>

      {loading && (
        <div className="loading-state">
          <p>{text.loading}</p>
        </div>
      )}

      {error && (
        <div className="error-state">
          <p>{error}</p>
        </div>
      )}

      {!loading && failedUsers.length > 0 && (
        <div className="error-state">
          <p>{`${text.partialFailure}: ${failedUsers.map((user) => `@${user}`).join(', ')}`}</p>
        </div>
      )}

      {!loading && users.length > 0 && compareInsights && (
        <>
          <section className="compare-insights-grid">
            <article className="compare-insight-card">
              <span className="compare-insight-kicker">{text.overallLeader}</span>
              <div className="compare-insight-main">
                <strong>@{compareInsights.leader.username}</strong>
                <span>{compareInsights.leader.gitscore.toFixed(0)} GitScore</span>
              </div>
              <p className="compare-insight-body">
                {compareInsights.runnerUp
                  ? `${text.leadBy} ${compareInsights.leadMargin.toFixed(1)} ${text.points}`
                  : text.tiedMatch}
              </p>
            </article>

            <article className="compare-insight-card">
              <span className="compare-insight-kicker">{text.strongestEdge}</span>
              <div className="compare-insight-main">
                <strong>@{compareInsights.dominantDimension.winner.username}</strong>
                <span>{compareInsights.dominantDimension.label}</span>
              </div>
              <p className="compare-insight-body">
                {text.edgeSummary} {compareInsights.dominantDimension.label.toLowerCase()}
              </p>
            </article>

            <article className="compare-insight-card">
              <span className="compare-insight-kicker">{text.closeChallenger}</span>
              <div className="compare-insight-main">
                <strong>
                  {compareInsights.runnerUp
                    ? `@${compareInsights.runnerUp.username}`
                    : `@${compareInsights.leader.username}`}
                </strong>
                <span>
                  {compareInsights.runnerUp
                    ? `${compareInsights.runnerUp.gitscore.toFixed(0)} GitScore`
                    : text.tiedMatch}
                </span>
              </div>
              <p className="compare-insight-body">
                {compareInsights.runnerUp
                  ? `${text.leadBy} ${compareInsights.leadMargin.toFixed(1)} ${text.points}`
                  : text.tiedMatch}
              </p>
            </article>
          </section>

          <div className="compare-user-cards">
            {users.map((user, index) => (
              <div key={user.username} className="compare-user-card" style={{ borderColor: colors[index] }}>
                <div className="compare-user-header">
                  <img src={user.avatar_url} alt={user.username} className="compare-avatar" />
                  <div className="compare-user-info">
                    <h3>@{user.username}</h3>
                    <span className="compare-gitscore" style={{ color: colors[index] }}>
                      {user.gitscore.toFixed(0)}
                    </span>
                  </div>
                  <button className="compare-remove-btn" onClick={() => removeUser(user.username)}>
                    {text.remove}
                  </button>
                </div>
                <div className="compare-tags">
                  {user.style_tags.slice(0, 3).map((tag) => (
                    <span key={tag} className="compare-tag" style={{ background: `${colors[index]}18`, color: colors[index] }}>
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="compare-advantage-grid">
                  <div className="compare-advantage-card">
                    <span className="compare-advantage-label">{text.strongestDimension}</span>
                    <strong>{compareInsights.strongestByUser.get(user.username)}</strong>
                  </div>
                  <div className="compare-advantage-card">
                    <span className="compare-advantage-label">{text.dimensionWins}</span>
                    <strong>{compareInsights.winsByUser.get(user.username) ?? 0}</strong>
                  </div>
                </div>
                <p className="compare-strengths">
                  {text.topStrengths}: {(compareInsights.topStrengthsByUser.get(user.username) ?? []).join(' / ')}
                </p>
                <p className="compare-summary">{user.tech_summary}</p>
                {user.roast_comment && <blockquote className="compare-roast">"{user.roast_comment}"</blockquote>}
              </div>
            ))}
          </div>

          <div className="compare-chart-section">
            <h3 className="compare-chart-title">{text.comparisonInsights}</h3>
            <div className="compare-radar-wrapper">
              <ResponsiveContainer width="100%" height={400}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="var(--color-outline-variant)" />
                  <PolarAngleAxis
                    dataKey="subject"
                    tick={{ fill: 'var(--color-on-surface-variant)', fontSize: 12 }}
                  />
                  {users.map((user, index) => (
                    <Radar
                      key={user.username}
                      name={user.username}
                      dataKey={user.username}
                      stroke={colors[index]}
                      fill={colors[index]}
                      fillOpacity={0.1}
                    />
                  ))}
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="compare-chart-section">
            <h3 className="compare-chart-title">{text.stats}</h3>
            <div className="compare-bar-wrapper">
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={barData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" />
                  <XAxis dataKey="name" tick={{ fill: 'var(--color-on-surface-variant)', fontSize: 12 }} />
                  <YAxis tick={{ fill: 'var(--color-on-surface-variant)', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--color-surface-container)',
                      border: '1px solid var(--color-outline-variant)',
                      borderRadius: '8px',
                    }}
                  />
                  {users.map((user, index) => (
                    <Bar key={user.username} dataKey={user.username} fill={colors[index]} radius={[4, 4, 0, 0]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="compare-stats-section">
            <div className="compare-stats-grid">
              {statsData.map((stat, index) => (
                <div key={stat.username} className="compare-stat-card" style={{ borderColor: colors[index] }}>
                  <div className="compare-stat-header" style={{ color: colors[index] }}>
                    @{stat.username}
                  </div>
                  <div className="compare-stat-row">
                    <span>GitScore</span>
                    <strong>{stat.gitscore.toFixed(0)}</strong>
                  </div>
                  <div className="compare-stat-row">
                    <span>{text.followers}</span>
                    <strong>{stat.followers.toLocaleString()}</strong>
                  </div>
                  <div className="compare-stat-row">
                    <span>{text.following}</span>
                    <strong>{stat.following.toLocaleString()}</strong>
                  </div>
                  <div className="compare-stat-row">
                    <span>{text.repos}</span>
                    <strong>{stat.repos}</strong>
                  </div>
                  <div className="compare-stat-row">
                    <span>{text.stars}</span>
                    <strong>{stat.stars.toLocaleString()}</strong>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
