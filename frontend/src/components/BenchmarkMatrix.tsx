import { KeyboardEvent, useMemo, useRef, useState } from 'react'
import type { FeatureCell, FeatureRow } from '../types/benchmark'

interface BenchmarkMatrixProps {
  rows: FeatureRow[]
  language?: 'en' | 'zh'
  scoreLabel?: string
  detailsLabel?: string
  emptyLabel?: string
}

const defaultLabels = {
  en: { score: 'Score', details: 'View details', empty: 'No raw signals available.' },
  zh: { score: '评分', details: '查看详情', empty: '暂无原始信号。' },
}

function levelClass(level: FeatureCell['level']): string {
  if (level === 'strong') return 'compare-level-strong'
  if (level === 'medium') return 'compare-level-medium'
  if (level === 'weak') return 'compare-level-weak'
  return 'compare-level-missing'
}

function levelAriaLabel(level: FeatureCell['level']): string {
  return `Level: ${level}`
}

function formatRawValue(value: boolean | number | string): string {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}

export function BenchmarkMatrix({
  rows,
  language = 'en',
  scoreLabel,
  detailsLabel,
  emptyLabel,
}: BenchmarkMatrixProps) {
  const lang = defaultLabels[language]
  const resolvedScoreLabel = scoreLabel ?? lang.score
  const resolvedDetailsLabel = detailsLabel ?? lang.details
  const resolvedEmptyLabel = emptyLabel ?? lang.empty
  const [expandedCells, setExpandedCells] = useState<Record<string, boolean>>({})
  const gridRef = useRef<HTMLDivElement>(null)
  const cellIndex = useMemo(
    () => rows.flatMap((row, rowIndex) => row.cells.map((_, cellIndex) => ({ rowIndex, cellIndex }))),
    [rows],
  )

  const toggleCell = (cellId: string) => {
    setExpandedCells((current) => ({ ...current, [cellId]: !current[cellId] }))
  }

  const handleGridKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement | null
    const currentIndex = Number(target?.dataset.cellIndex ?? '-1')
    if (currentIndex < 0) return

    const current = cellIndex[currentIndex]
    if (!current) return

    let nextIndex = -1
    if (event.key === 'ArrowRight') nextIndex = currentIndex + 1
    if (event.key === 'ArrowLeft') nextIndex = currentIndex - 1
    if (event.key === 'ArrowDown') {
      nextIndex = cellIndex.findIndex(
        (entry) => entry.rowIndex === current.rowIndex + 1 && entry.cellIndex === current.cellIndex,
      )
    }
    if (event.key === 'ArrowUp') {
      nextIndex = cellIndex.findIndex(
        (entry) => entry.rowIndex === current.rowIndex - 1 && entry.cellIndex === current.cellIndex,
      )
    }

    if (nextIndex < 0) return
    event.preventDefault()
    const nextCell = gridRef.current?.querySelector<HTMLElement>(`[data-cell-index="${nextIndex}"]`)
    nextCell?.focus()
  }

  return (
    <div className="benchmark-matrix-shell">
      <div
        ref={gridRef}
        className="repo-matrix repo-matrix-grid"
        role="grid"
        aria-label="Repository benchmark matrix"
        onKeyDown={handleGridKeyDown}
      >
        {rows.map((row, rowIndex) => (
          <div key={row.dimension_id} className="repo-matrix-row" role="row">
            <div className="repo-matrix-label" role="rowheader">
              {row.label}
            </div>
            <div className="repo-matrix-cells">
              {row.cells.map((cell, columnIndex) => {
                const cellId = `${row.dimension_id}-${cell.repo}`
                const rawEntries = Object.entries(cell.raw)
                const flatIndex = cellIndex.findIndex(
                  (entry) => entry.rowIndex === rowIndex && entry.cellIndex === columnIndex,
                )

                return (
                  <button
                    key={cellId}
                    type="button"
                    className={`repo-matrix-cell repo-matrix-cell-button ${levelClass(cell.level)}`}
                    onClick={() => toggleCell(cellId)}
                    aria-expanded={expandedCells[cellId] ?? false}
                    aria-label={`${cell.repo} ${row.label} ${levelAriaLabel(cell.level)}`}
                    data-cell-index={flatIndex}
                    role="gridcell"
                  >
                    <strong>{cell.repo}</strong>
                    <span>{resolvedScoreLabel}: {cell.score}</span>
                    <span className="repo-matrix-level">{cell.level}</span>
                    <span className="repo-matrix-toggle">{resolvedDetailsLabel}</span>
                    {expandedCells[cellId] && (
                      <div className="repo-matrix-raw" aria-label={resolvedDetailsLabel}>
                        {rawEntries.length > 0 ? (
                          rawEntries.map(([key, value]) => (
                            <div key={key} className="repo-matrix-raw-item">
                              <span>{key}</span>
                              <strong>{formatRawValue(value)}</strong>
                            </div>
                          ))
                        ) : (
                          <span>{resolvedEmptyLabel}</span>
                        )}
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
