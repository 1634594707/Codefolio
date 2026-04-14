export interface RepoProfile {
  full_name: string
  description: string | null
  stars: number
  forks: number
  language: string | null
  topics: string[]
  license: string | null
  default_branch: string | null
  created_at: string | null
  pushed_at: string | null
  has_readme: boolean
  readme_sections: string[]
  has_license_file: boolean
  workflow_file_count: number
  has_contributing: boolean
  has_code_of_conduct: boolean
  has_security_policy: boolean
  has_issue_templates: boolean
  has_screenshot: boolean
  has_quickstart: boolean
  has_examples_dir: boolean
  has_docs_dir: boolean
  homepage: string | null
  open_issues_count: number
  fetched_at: string
}

export interface FeatureCell {
  repo: string
  level: 'missing' | 'weak' | 'medium' | 'strong'
  score: number
  raw: Record<string, boolean | number | string>
}

export interface FeatureRow {
  dimension_id: string
  label_key: string
  label: string
  cells: FeatureCell[]
}

export interface HypothesisEvidence {
  type: string
  detail: string
  repo: string
}

export interface Hypothesis {
  hypothesis_id: string
  title: string
  category: string
  evidence: HypothesisEvidence[]
  transferability: 'high' | 'medium' | 'low'
  caveats: string[]
  confidence: string
}

export interface ActionItem {
  action_id: string
  dimension: string
  title: string
  rationale: string
  effort: 'S' | 'M' | 'L'
  impact: number
  priority_score: number
  checklist: string[]
  suggested_deadline: string
}

export interface BenchmarkResponse {
  bucket: {
    label: string
    warning: string | null
  }
  profiles: Record<string, RepoProfile>
  feature_matrix: {
    rows: FeatureRow[]
  }
  hypotheses: Hypothesis[]
  actions: ActionItem[]
  narrative: {
    summary: string
    disclaimer: string
  } | null
  generated_at: string
  llm_calls: number
}
