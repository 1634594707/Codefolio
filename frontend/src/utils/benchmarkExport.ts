export interface BenchmarkExportProfile {
  full_name: string
  description: string | null
  stars: number
  forks: number
  language: string | null
  topics: string[]
  workflow_file_count: number
  pushed_at: string | null
}

export interface BenchmarkExportCell {
  repo: string
  level: 'missing' | 'weak' | 'medium' | 'strong'
  score: number
  raw: Record<string, string | number | boolean>
}

export interface BenchmarkExportRow {
  dimension_id: string
  label_key: string
  label: string
  cells: BenchmarkExportCell[]
}

export interface BenchmarkExportHypothesis {
  hypothesis_id: string
  title: string
  category: string
  evidence: Array<{
    type: string
    detail: string
    repo: string
  }>
  transferability: string
  caveats: string[]
  confidence: string
}

export interface BenchmarkExportAction {
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

export interface BenchmarkExportReport {
  bucket: {
    label: string
    warning: string | null
  }
  profiles: Record<string, BenchmarkExportProfile>
  feature_matrix: {
    rows: BenchmarkExportRow[]
  }
  hypotheses: BenchmarkExportHypothesis[]
  actions: BenchmarkExportAction[]
  narrative: {
    summary: string
    disclaimer: string
  } | null
  generated_at: string
  llm_calls: number
}

function escapeCell(value: string): string {
  return value.replace(/\|/g, '\\|').replace(/\n/g, ' ')
}

export function generateBenchmarkMarkdown(
  report: BenchmarkExportReport,
  language: 'en' | 'zh',
): string {
  const text = language === 'zh'
    ? {
        title: '仓库对标报告',
        overview: '概览',
        profiles: '仓库概况',
        matrix: '差距矩阵',
        actions: '行动项',
        hypotheses: '成功假设',
        narrative: '叙述总结',
        disclaimer: '边界说明',
        generatedAt: '生成时间',
        warning: '提醒',
        stars: 'Stars',
        forks: 'Forks',
        languageLabel: '语言',
        topics: 'Topics',
        lastUpdated: '最近更新',
        workflows: '工作流',
        level: '等级',
        transferability: '可迁移性',
        confidence: '置信度',
        checklist: '检查清单',
        deadline: '建议期限',
      }
    : {
        title: 'Repository Benchmark Report',
        overview: 'Overview',
        profiles: 'Profiles',
        matrix: 'Gap Matrix',
        actions: 'Action Items',
        hypotheses: 'Success Hypotheses',
        narrative: 'Narrative',
        disclaimer: 'Boundary',
        generatedAt: 'Generated at',
        warning: 'Warning',
        stars: 'Stars',
        forks: 'Forks',
        languageLabel: 'Language',
        topics: 'Topics',
        lastUpdated: 'Last updated',
        workflows: 'Workflows',
        level: 'Level',
        transferability: 'Transferability',
        confidence: 'Confidence',
        checklist: 'Checklist',
        deadline: 'Suggested deadline',
      }

  const repoNames = Object.keys(report.profiles)
  const sections: string[] = [
    `# ${text.title}`,
    '',
    `## ${text.overview}`,
    '',
    `- ${report.bucket.label}`,
    `- ${text.generatedAt}: ${report.generated_at}`,
  ]

  if (report.bucket.warning) sections.push(`- ${text.warning}: ${report.bucket.warning}`)

  sections.push('', `## ${text.profiles}`, '')
  Object.values(report.profiles).forEach((profile) => {
    sections.push(`### ${profile.full_name}`)
    sections.push(`- ${profile.description || '-'}`)
    sections.push(`- ${text.stars}: ${profile.stars}`)
    sections.push(`- ${text.forks}: ${profile.forks}`)
    sections.push(`- ${text.languageLabel}: ${profile.language || '-'}`)
    sections.push(`- ${text.topics}: ${profile.topics.join(', ') || '-'}`)
    sections.push(`- ${text.workflows}: ${profile.workflow_file_count}`)
    sections.push(`- ${text.lastUpdated}: ${profile.pushed_at || '-'}`)
    sections.push('')
  })

  sections.push(`## ${text.matrix}`, '')
  sections.push(`| Dimension | ${repoNames.join(' | ')} |`)
  sections.push(`| --- | ${repoNames.map(() => '---').join(' | ')} |`)
  report.feature_matrix.rows.forEach((row) => {
    sections.push(
      `| ${escapeCell(row.label)} | ${row.cells.map((cell) => escapeCell(`${cell.level} (${cell.score})`)).join(' | ')} |`,
    )
  })

  sections.push('', `## ${text.actions}`, '')
  report.actions.forEach((action, index) => {
    sections.push(`${index + 1}. ${action.title}`)
    sections.push(`- ${action.rationale}`)
    sections.push(`- ${text.level}: ${action.effort} / ${action.impact}`)
    sections.push(`- ${text.deadline}: ${action.suggested_deadline}`)
    sections.push(`- ${text.checklist}:`)
    action.checklist.forEach((item) => sections.push(`  - ${item}`))
    sections.push('')
  })

  sections.push(`## ${text.hypotheses}`, '')
  report.hypotheses.forEach((hypothesis) => {
    sections.push(`### ${hypothesis.title}`)
    sections.push(`- ${text.transferability}: ${hypothesis.transferability}`)
    sections.push(`- ${text.confidence}: ${hypothesis.confidence}`)
    hypothesis.evidence.forEach((item) => sections.push(`- ${item.repo}: ${item.detail}`))
    hypothesis.caveats.forEach((item) => sections.push(`- ${text.disclaimer}: ${item}`))
    sections.push('')
  })

  if (report.narrative) {
    sections.push(`## ${text.narrative}`, '')
    sections.push(report.narrative.summary, '', `## ${text.disclaimer}`, '', report.narrative.disclaimer)
  }

  return sections.join('\n').trim()
}
