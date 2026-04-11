import { Fragment, useEffect, useState } from 'react'

export type ProgressStep = 'fetching' | 'scoring' | 'polishing'

interface ProgressIndicatorProps {
  currentStep: ProgressStep
  estimatedTimeRemaining?: number
  language: 'en' | 'zh'
  labels: {
    progressFetching: string
    progressScoring: string
    progressPolishing: string
    progressTimeRemaining: string
  }
}

const funFacts = {
  en: [
    'Did you know? The first GitHub commit was made on April 10, 2008.',
    'Fun fact: GitHub has over 100 million repositories.',
    'GitHub tip: You can use keyboard shortcuts to navigate faster.',
    'Did you know? GitHub Copilot can suggest code based on comments.',
    'Fun fact: The GitHub mascot is Octocat, an octopus cat hybrid.',
    'GitHub tip: You can create GitHub Actions to automate workflows.',
    'Did you know? GitHub Pages can host static websites for free.',
    'Fun fact: GitHub has a dark mode to reduce eye strain.',
    'GitHub tip: Use git rebase to keep your history clean.',
    'Did you know? GitHub supports over 200 programming languages.',
  ],
  zh: [
    '你知道吗？第一个 GitHub 提交是在 2008 年 4 月 10 日进行的。',
    '有趣的事实：GitHub 拥有超过 1 亿个仓库。',
    'GitHub 小贴士：你可以使用键盘快捷键更快地导航。',
    '你知道吗？GitHub Copilot 可以根据注释建议代码。',
    '有趣的事实：GitHub 的吉祥物是 Octocat，一个章鱼猫混合体。',
    'GitHub 小贴士：你可以创建 GitHub Actions 来自动化工作流。',
    '你知道吗？GitHub Pages 可以免费托管静态网站。',
    '有趣的事实：GitHub 有深色模式来减少眼睛疲劳。',
    'GitHub 小贴士：使用 git rebase 来保持历史记录整洁。',
    '你知道吗？GitHub 支持超过 200 种编程语言。',
  ],
}

const stepOrder: ProgressStep[] = ['fetching', 'scoring', 'polishing']

const copy = {
  en: {
    headline: 'Analyzing profile',
    subline: 'Pulling public data, scoring activity, and polishing insights.',
    tipLabel: 'While you wait',
  },
  zh: {
    headline: '正在分析档案',
    subline: '拉取公开数据、计算 GitScore，并生成洞察。',
    tipLabel: '等待间隙',
  },
} as const

function IconFetch({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function IconScore({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path d="M4 19V5M9 19V9M14 19v-6M19 19V8" strokeLinecap="round" />
    </svg>
  )
}

function IconPolish({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path
        d="M12 3l1.1 3.2L16.5 8l-3.4 1.5L12 12.5 10.9 9.5 7.5 8l3.4-1.5L12 3z"
        strokeLinejoin="round"
      />
      <path
        d="M18.5 14l.4 1.2 1.2.4-1.2.4-.4 1.2-.4-1.2-1.2-.4 1.2-.4.4-1.2z"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function IconCheck({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" aria-hidden>
      <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

const stepIcons: Record<ProgressStep, typeof IconFetch> = {
  fetching: IconFetch,
  scoring: IconScore,
  polishing: IconPolish,
}

function roundEtaSeconds(value: number | undefined): number {
  if (value == null || !Number.isFinite(value) || value <= 0) return 0
  return Math.max(0, Math.round(value))
}

export function ProgressIndicator({
  currentStep,
  estimatedTimeRemaining,
  language,
  labels,
}: ProgressIndicatorProps) {
  const roundedFromParent = roundEtaSeconds(estimatedTimeRemaining)
  const [displayTime, setDisplayTime] = useState(roundedFromParent)
  const [currentFactIndex, setCurrentFactIndex] = useState(0)
  const currentStepIndex = stepOrder.indexOf(currentStep)
  const progressRatio = (currentStepIndex + 1) / stepOrder.length
  const facts = funFacts[language]
  const t = copy[language]

  const stepLabelMap = {
    fetching: labels.progressFetching,
    scoring: labels.progressScoring,
    polishing: labels.progressPolishing,
  }

  useEffect(() => {
    if (roundedFromParent <= 0) {
      setDisplayTime(0)
      return
    }

    setDisplayTime(roundedFromParent)
    const interval = setInterval(() => {
      setDisplayTime((prev) => Math.max(0, prev - 1))
    }, 1000)

    return () => clearInterval(interval)
  }, [roundedFromParent])

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentFactIndex((prev) => (prev + 1) % facts.length)
    }, 5000)

    return () => clearInterval(interval)
  }, [facts.length])

  const formatTime = (seconds: number): string => {
    const s = roundEtaSeconds(seconds)
    if (s <= 0) return '0s'
    if (s < 60) return `${s}s`
    const minutes = Math.floor(s / 60)
    const secs = s % 60
    return `${minutes}m ${secs}s`
  }

  return (
    <section className="analysis-progress-card" role="status" aria-live="polite" aria-busy="true">
      <div className="analysis-progress-header">
        <div className="analysis-progress-visual" aria-hidden>
          <div className="analysis-progress-orbit" />
          <div className="analysis-progress-core" />
        </div>
        <div className="analysis-progress-titles">
          <h2 className="analysis-progress-headline">{t.headline}</h2>
          <p className="analysis-progress-subline">{t.subline}</p>
        </div>
        {displayTime > 0 ? (
          <div className="analysis-progress-eta">
            <span className="analysis-progress-eta-label">{labels.progressTimeRemaining}</span>
            <span className="analysis-progress-eta-value">{formatTime(displayTime)}</span>
          </div>
        ) : null}
      </div>

      <div className="analysis-pipeline" aria-label={t.headline}>
        {stepOrder.map((step, index) => {
          const done = index < currentStepIndex
          const active = index === currentStepIndex
          const Icon = stepIcons[step]
          return (
            <Fragment key={step}>
              {index > 0 ? (
                <div
                  className="analysis-pipeline-rail"
                  data-active={index <= currentStepIndex ? 'true' : 'false'}
                  aria-hidden
                />
              ) : null}
              <div
                className={`analysis-pipeline-step ${done ? 'is-done' : ''} ${active ? 'is-active' : ''}`}
              >
                <div className="analysis-pipeline-node">
                  {done ? <IconCheck className="analysis-pipeline-icon" /> : <Icon className="analysis-pipeline-icon" />}
                  {active ? <span className="analysis-pipeline-spinner" /> : null}
                </div>
                <span className="analysis-pipeline-caption">{stepLabelMap[step]}</span>
              </div>
            </Fragment>
          )
        })}
      </div>

      <div className="analysis-progress-track" aria-hidden>
        <div className="analysis-progress-track-fill" style={{ transform: `scaleX(${progressRatio})` }} />
        <div className="analysis-progress-track-shimmer" />
      </div>

      <div className="analysis-tip">
        <span className="analysis-tip-kicker">{t.tipLabel}</span>
        <p key={currentFactIndex} className="analysis-tip-text">
          {facts[currentFactIndex]}
        </p>
      </div>
    </section>
  )
}
