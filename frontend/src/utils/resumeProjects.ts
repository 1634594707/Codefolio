import type { ResumeProject } from '../context/AppContext'

type RepoLike = {
  name: string
  description: string
  language: string
  stars: number
  forks: number
  url: string
  pushed_at?: string
  has_readme?: boolean
  has_license?: boolean
}

export type RepositoryAnalysisPayload = {
  repository: RepoLike
  analysis: {
    repo_name: string
    title: string
    summary: string
    highlights: string[]
    keywords: string[]
    evidence?: string[]
    strengths?: string[]
    risks?: string[]
    resume_bullets?: string[]
    next_steps?: string[]
    showcase_fit?: string
    confidence?: string
  }
}

function formatPushedLabel(value: string | undefined, language: 'en' | 'zh'): string {
  if (!value) return language === 'zh' ? '最近仍有维护信号' : 'shows signs of recent maintenance'
  return language === 'zh' ? `最近更新于 ${value}` : `last updated on ${value}`
}

export function buildResumeProject(user: string, repo: RepoLike, language: 'en' | 'zh'): ResumeProject {
  const hasStrongCommunity = repo.stars >= 50 || repo.forks >= 10
  const hasProjectSignals = Boolean(repo.has_readme || repo.has_license)

  const analysisTitle =
    language === 'zh'
      ? `${repo.name} 可作为简历代表项目`
      : `${repo.name} is a strong resume project`

  const analysisSummary =
    language === 'zh'
      ? `${repo.language || '多技术栈'} 项目，${formatPushedLabel(repo.pushed_at, language)}，适合作为你能力范围与工程完成度的代表案例。`
      : `${repo.language || 'Multi-stack'} project, ${formatPushedLabel(repo.pushed_at, language)}, and suitable as a representative case for both technical breadth and shipping quality.`

  const highlights =
    language === 'zh'
      ? [
          repo.language ? `主技术栈是 ${repo.language}` : '包含可展示的技术实现',
          hasStrongCommunity
            ? `已有 ${repo.stars} stars 和 ${repo.forks} forks，具备外部认可度`
            : '适合用来补充你的实际项目经历',
          hasProjectSignals
            ? '带有 README / License，工程资料完整度更好'
            : '建议补 README 或 License 后再作为重点项目展示',
        ]
      : [
          repo.language ? `Primary stack: ${repo.language}` : 'Includes implementation detail worth presenting',
          hasStrongCommunity
            ? `${repo.stars} stars and ${repo.forks} forks provide external proof of interest`
            : 'Good candidate for showing practical project execution',
          hasProjectSignals
            ? 'README / License coverage makes the project feel more production ready'
            : 'Consider adding a README or license before making it a headline project',
        ]

  return {
    user,
    repoName: repo.name,
    description: repo.description,
    language: repo.language,
    stars: repo.stars,
    forks: repo.forks,
    url: repo.url,
    pushed_at: repo.pushed_at,
    has_readme: repo.has_readme,
    has_license: repo.has_license,
    analysisTitle,
    analysisSummary,
    highlights,
    keywords: repo.language ? [repo.language] : [],
  }
}

export function buildResumeProjectFromAnalysis(
  user: string,
  repo: RepoLike,
  payload: RepositoryAnalysisPayload,
): ResumeProject {
  return {
    user,
    repoName: repo.name,
    description: repo.description,
    language: repo.language,
    stars: repo.stars,
    forks: repo.forks,
    url: repo.url,
    pushed_at: repo.pushed_at,
    has_readme: repo.has_readme,
    has_license: repo.has_license,
    analysisTitle: payload.analysis.title,
    analysisSummary: payload.analysis.summary,
    highlights: payload.analysis.highlights,
    keywords: payload.analysis.keywords,
    evidence: payload.analysis.evidence,
    strengths: payload.analysis.strengths,
    risks: payload.analysis.risks,
    resumeBullets: payload.analysis.resume_bullets,
    nextSteps: payload.analysis.next_steps,
    showcaseFit: payload.analysis.showcase_fit,
    confidence: payload.analysis.confidence,
  }
}
