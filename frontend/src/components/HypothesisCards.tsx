import { useMemo, useState } from 'react'
import type { Hypothesis } from '../types/benchmark'

interface HypothesisCardsProps {
  hypotheses: Hypothesis[]
  language?: 'en' | 'zh'
  labels: {
    transferability: string
    confidence: string
    disclaimer: string
    filterCategory: string
    filterTransferability: string
    allCategories: string
    allTransferability: string
    evidence: string
    noHypotheses: string
  }
}

const TRANSFERABILITY_COLORS: Record<Hypothesis['transferability'], string> = {
  high: 'repo-flag active',
  medium: 'repo-flag repo-flag-medium',
  low: 'repo-flag repo-flag-low',
}

const TRANSFERABILITY_ICONS: Record<Hypothesis['transferability'], string> = {
  high: '▲',
  medium: '●',
  low: '▼',
}

export function HypothesisCards({ hypotheses, language = 'en', labels }: HypothesisCardsProps) {
  const [openCards, setOpenCards] = useState<Record<string, boolean>>({})
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [transferabilityFilter, setTransferabilityFilter] = useState('all')

  const categories = useMemo(
    () => Array.from(new Set(hypotheses.map((h) => h.category))).sort(),
    [hypotheses],
  )

  const filtered = useMemo(
    () =>
      hypotheses.filter((h) => {
        const matchesCategory = categoryFilter === 'all' || h.category === categoryFilter
        const matchesTransferability = transferabilityFilter === 'all' || h.transferability === transferabilityFilter
        return matchesCategory && matchesTransferability
      }),
    [categoryFilter, hypotheses, transferabilityFilter],
  )

  const groupedByCategory = useMemo(() => {
    const groups: Record<string, Hypothesis[]> = {}
    for (const h of filtered) {
      if (!groups[h.category]) groups[h.category] = []
      groups[h.category].push(h)
    }
    return groups
  }, [filtered])

  const toggleCard = (id: string) => {
    setOpenCards((current) => ({ ...current, [id]: !current[id] }))
  }

  const regionLabel = language === 'zh' ? '成功假设卡片' : 'Success hypothesis cards'

  if (hypotheses.length === 0) {
    return <p className="compare-hint">{labels.noHypotheses}</p>
  }

  return (
    <div className="repo-hypothesis-list" role="region" aria-label={regionLabel}>
      <div className="repo-action-toolbar">
        <label className="repo-benchmark-field">
          <span>{labels.filterCategory}</span>
          <select
            value={categoryFilter}
            onChange={(event) => setCategoryFilter(event.target.value)}
            className="compare-input"
            aria-label={labels.filterCategory}
          >
            <option value="all">{labels.allCategories}</option>
            {categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </label>
        <label className="repo-benchmark-field">
          <span>{labels.filterTransferability}</span>
          <select
            value={transferabilityFilter}
            onChange={(event) => setTransferabilityFilter(event.target.value)}
            className="compare-input"
            aria-label={labels.filterTransferability}
          >
            <option value="all">{labels.allTransferability}</option>
            <option value="high">{TRANSFERABILITY_ICONS.high} high</option>
            <option value="medium">{TRANSFERABILITY_ICONS.medium} medium</option>
            <option value="low">{TRANSFERABILITY_ICONS.low} low</option>
          </select>
        </label>
      </div>

      {filtered.length === 0 && (
        <p className="compare-hint">{labels.noHypotheses}</p>
      )}

      {Object.entries(groupedByCategory).map(([category, items]) => (
        <section key={category} className="repo-hypothesis-category" aria-label={category}>
          <h5 className="repo-hypothesis-category-label">{category}</h5>
          <div className="repo-hypothesis-grid">
            {items.map((hypothesis) => {
              const isOpen = Boolean(openCards[hypothesis.hypothesis_id])
              return (
                <article
                  key={hypothesis.hypothesis_id}
                  className="repo-hypothesis-card"
                  aria-label={hypothesis.title}
                >
                  <div className="repo-action-head">
                    <h4>{hypothesis.title}</h4>
                  </div>

                  <div className="repo-profile-flags">
                    <span
                      className={TRANSFERABILITY_COLORS[hypothesis.transferability]}
                      aria-label={`${labels.transferability}: ${hypothesis.transferability}`}
                    >
                      {TRANSFERABILITY_ICONS[hypothesis.transferability]} {hypothesis.transferability}
                    </span>
                    <span className="repo-flag" aria-label={`${labels.confidence}: ${hypothesis.confidence}`}>
                      {hypothesis.confidence}
                    </span>
                  </div>

                  <button
                    type="button"
                    className="compare-remove-btn"
                    onClick={() => toggleCard(hypothesis.hypothesis_id)}
                    aria-expanded={isOpen}
                    aria-controls={`evidence-${hypothesis.hypothesis_id}`}
                  >
                    {labels.evidence}
                  </button>

                  <div
                    id={`evidence-${hypothesis.hypothesis_id}`}
                    hidden={!isOpen}
                  >
                    <div className="repo-evidence-list" role="list" aria-label={language === 'zh' ? '依据' : 'Evidence'}>
                      {hypothesis.evidence.map((ev) => (
                        <div
                          key={`${hypothesis.hypothesis_id}-${ev.repo}-${ev.detail}`}
                          className="repo-evidence-item"
                          role="listitem"
                        >
                          <strong>{ev.repo}</strong>
                          <span>{ev.detail}</span>
                        </div>
                      ))}
                    </div>

                    {hypothesis.caveats.length > 0 && (
                      <div className="repo-evidence-list" role="list" aria-label={labels.disclaimer}>
                        {hypothesis.caveats.map((caveat) => (
                          <div key={caveat} className="repo-evidence-item" role="listitem">
                            <strong>{labels.disclaimer}</strong>
                            <span>{caveat}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </article>
              )
            })}
          </div>
        </section>
      ))}
    </div>
  )
}
