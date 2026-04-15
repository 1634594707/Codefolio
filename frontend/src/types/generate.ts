/** Shared shape for `POST /api/generate` JSON (used by Layout cache and pages). */

export type ApiLanguage = 'en' | 'zh'

export type AIInsights = {
  style_tags: string[]
  roast_comment: string
  tech_summary: string
}

export type CardData = {
  username: string
  avatar_url: string
  gitscore: number
  radar_chart_data: number[]
  style_tags: string[]
  roast_comment: string
  tech_icons: string[]
}

export type LocalizedOutput = {
  resume_markdown: string
  ai_insights: AIInsights
  card_data: CardData
  social_card_html: string
}

export type GenerateResponse = {
  user: {
    username: string
    name: string
    avatar_url: string
    bio: string
    followers: number
    following: number
    location?: string
    blog?: string
    languages: Record<string, number>
    repositories: Array<{
      name: string
      description: string
      stars: number
      forks: number
      language: string
      url: string
      pushed_at?: string
      has_readme?: boolean
      has_license?: boolean
      topics?: string[]
      readme_text?: string
      file_tree?: string[]
      languages?: Record<string, number>
    }>
    contributions?: {
      contribution_days: Array<{ date: string; contribution_count: number }>
    }
  }
  resume_markdown: string
  gitscore: {
    total: number
    dimensions: Record<string, number>
  }
  ai_insights: AIInsights
  card_data: CardData
  localized_outputs: Partial<Record<ApiLanguage, LocalizedOutput>>
  available_content_languages: ApiLanguage[]
  language_trends?: Array<{
    language: string
    data: Array<{ month: string; percentage: number }>
  }>
  star_history?: Array<{ month: string; stars: number }>
}
