import { useEffect, useMemo, useState } from 'react'
import type { ActionItem } from '../types/benchmark'

interface ActionListProps {
  actions: ActionItem[]
  language: 'en' | 'zh'
  labels: {
    sortBy: string
    filterBy: string
    sortPriority: string
    sortEffort: string
    sortImpact: string
    allDimensions: string
    quickWin: string
    complete: string
    timeline7d: string
    timeline30d: string
    timeline90d: string
    noActions: string
  }
}

type SortMode = 'priority' | 'effort' | 'impact'

const STORAGE_PREFIX = 'benchmark-action-complete-'

function effortScore(value: ActionItem['effort']): number {
  if (value === 'S') return 1
  if (value === 'M') return 2
  return 3
}

function getTimelineKey(deadline: string): '7d' | '30d' | '90d' {
  if (deadline.includes('7')) return '7d'
  if (deadline.includes('30')) return '30d'
  return '90d'
}

function loadCompleted(actionIds: string[]): Record<string, boolean> {
  const result: Record<string, boolean> = {}
  for (const id of actionIds) {
    try {
      result[id] = localStorage.getItem(`${STORAGE_PREFIX}${id}`) === 'true'
    } catch {
      result[id] = false
    }
  }
  return result
}

export function ActionList({ actions, language, labels }: ActionListProps) {
  const [sortMode, setSortMode] = useState<SortMode>('priority')
  const [dimensionFilter, setDimensionFilter] = useState('all')
  const [completed, setCompleted] = useState<Record<string, boolean>>({})
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({
    '7d': false,
    '30d': false,
    '90d': false,
  })

  // Load per-item completion state from localStorage on mount / when actions change
  useEffect(() => {
    setCompleted(loadCompleted(actions.map((a) => a.action_id)))
  }, [actions])

  const toggleCompleted = (actionId: string, value: boolean) => {
    try {
      localStorage.setItem(`${STORAGE_PREFIX}${actionId}`, String(value))
    } catch {
      // ignore storage errors
    }
    setCompleted((current) => ({ ...current, [actionId]: value }))
  }

  const dimensions = useMemo(
    () => Array.from(new Set(actions.map((action) => action.dimension))).sort(),
    [actions],
  )

  const filteredActions = useMemo(() => {
    const base =
      dimensionFilter === 'all'
        ? actions
        : actions.filter((action) => action.dimension === dimensionFilter)

    return [...base].sort((left, right) => {
      if (sortMode === 'impact') return right.impact - left.impact
      if (sortMode === 'effort') return effortScore(left.effort) - effortScore(right.effort)
      return right.priority_score - left.priority_score
    })
  }, [actions, dimensionFilter, sortMode])

  const grouped = useMemo(
    () => ({
      '7d': filteredActions.filter((action) => getTimelineKey(action.suggested_deadline) === '7d'),
      '30d': filteredActions.filter((action) => getTimelineKey(action.suggested_deadline) === '30d'),
      '90d': filteredActions.filter((action) => getTimelineKey(action.suggested_deadline) === '90d'),
    }),
    [filteredActions],
  )

  const timelineLabels: Record<'7d' | '30d' | '90d', string> = {
    '7d': labels.timeline7d,
    '30d': labels.timeline30d,
    '90d': labels.timeline90d,
  }

  if (actions.length === 0) {
    return <p className="compare-hint">{labels.noActions}</p>
  }

  return (
    <div className="repo-action-list" role="region" aria-label={language === 'zh' ? '行动项列表' : 'Action items list'}>
      <div className="repo-action-toolbar">
        <label className="repo-benchmark-field">
          <span>{labels.sortBy}</span>
          <select
            value={sortMode}
            onChange={(event) => setSortMode(event.target.value as SortMode)}
            className="compare-input"
            aria-label={labels.sortBy}
          >
            <option value="priority">{labels.sortPriority}</option>
            <option value="effort">{labels.sortEffort}</option>
            <option value="impact">{labels.sortImpact}</option>
          </select>
        </label>
        <label className="repo-benchmark-field">
          <span>{labels.filterBy}</span>
          <select
            value={dimensionFilter}
            onChange={(event) => setDimensionFilter(event.target.value)}
            className="compare-input"
            aria-label={labels.filterBy}
          >
            <option value="all">{labels.allDimensions}</option>
            {dimensions.map((dimension) => (
              <option key={dimension} value={dimension}>
                {dimension}
              </option>
            ))}
          </select>
        </label>
      </div>

      {(['7d', '30d', '90d'] as const).map((groupKey) => (
        <section key={groupKey} className="repo-action-group" aria-label={timelineLabels[groupKey]}>
          <button
            type="button"
            className="repo-action-group-toggle"
            onClick={() =>
              setCollapsedGroups((current) => ({ ...current, [groupKey]: !current[groupKey] }))
            }
            aria-expanded={!collapsedGroups[groupKey]}
            aria-controls={`action-group-${groupKey}`}
          >
            <strong>{timelineLabels[groupKey]}</strong>
            <span aria-label={`${grouped[groupKey].length} items`}>{grouped[groupKey].length}</span>
          </button>
          {!collapsedGroups[groupKey] && (
            <div id={`action-group-${groupKey}`} className="repo-actions-grid">
              {grouped[groupKey].map((action) => {
                const quickWin = action.effort === 'S' && action.impact >= 4
                const isDone = Boolean(completed[action.action_id])
                return (
                  <article
                    key={action.action_id}
                    className={`repo-action-card${isDone ? ' repo-action-card-done' : ''}`}
                    aria-label={action.title}
                  >
                    <div className="repo-action-head">
                      <h4>{action.title}</h4>
                      <span aria-label={`Effort ${action.effort}, impact ${action.impact}`}>
                        {action.effort} / {action.impact}
                      </span>
                    </div>
                    <p>{action.rationale}</p>
                    <div className="repo-profile-flags">
                      {quickWin && (
                        <span className="repo-flag active" aria-label={labels.quickWin}>
                          {labels.quickWin}
                        </span>
                      )}
                      <span className="repo-flag">{action.dimension}</span>
                      <span className="repo-flag">{action.suggested_deadline}</span>
                      <span className="repo-flag" aria-label={`Priority score ${action.priority_score.toFixed(1)}`}>
                        P{action.priority_score.toFixed(1)}
                      </span>
                    </div>
                    <label className="repo-action-checkbox">
                      <input
                        type="checkbox"
                        checked={isDone}
                        onChange={(event) => toggleCompleted(action.action_id, event.target.checked)}
                        aria-label={`${labels.complete}: ${action.title}`}
                      />
                      <span>{labels.complete}</span>
                    </label>
                    <div className="repo-action-checks" role="list" aria-label={language === 'zh' ? '子任务' : 'Checklist'}>
                      {action.checklist.map((item) => (
                        <span key={`${action.action_id}-${item}`} className="repo-check-item" role="listitem">
                          {item}
                        </span>
                      ))}
                    </div>
                  </article>
                )
              })}
            </div>
          )}
        </section>
      ))}
      <span className="repo-action-storage-note" aria-live="polite">
        {language === 'zh' ? '完成状态已保存在此浏览器中。' : 'Completion state is stored in this browser.'}
      </span>
    </div>
  )
}
