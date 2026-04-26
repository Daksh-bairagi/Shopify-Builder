import { useState } from 'react'
import type { ProductSummary, Finding } from '../api/client'

interface Props {
  products: ProductSummary[]
  findings: Finding[]
}

const COLUMNS: { id: string; label: string; pillar: string }[] = [
  { id: 'D1b',  label: 'Catalog',    pillar: 'D' },
  { id: 'D2',   label: 'Sitemap',    pillar: 'D' },
  { id: 'C1',   label: 'Taxonomy',   pillar: 'C' },
  { id: 'C2',   label: 'Title',      pillar: 'C' },
  { id: 'C3',   label: 'Variants',   pillar: 'C' },
  { id: 'C4',   label: 'GTIN',       pillar: 'C' },
  { id: 'C5',   label: 'Metafields', pillar: 'C' },
  { id: 'C6',   label: 'Alt Text',   pillar: 'C' },
  { id: 'Con1', label: 'Price',      pillar: 'Con' },
  { id: 'Con2', label: 'Stock',      pillar: 'Con' },
  { id: 'T1',   label: 'Returns',    pillar: 'T' },
  { id: 'A1',   label: 'Tracked',    pillar: 'A' },
  { id: 'A2',   label: 'Oversell',   pillar: 'A' },
]

const PILLAR_COLORS: Record<string, string> = {
  D:   'rgba(143,184,154,0.5)',
  C:   'rgba(180,160,214,0.5)',
  Con: 'rgba(212,169,107,0.5)',
  T:   'rgba(107,169,212,0.5)',
  A:   'rgba(213,122,120,0.5)',
}

export default function HeatmapGrid({ products, findings }: Props) {
  const [hoveredRow, setHoveredRow] = useState<string | null>(null)
  const [hoveredCell, setHoveredCell] = useState<string | null>(null)

  if (products.length === 0) return null

  const failingByProduct: Record<string, Set<string>> = {}
  for (const finding of findings) {
    for (const pid of finding.affected_products) {
      if (!failingByProduct[pid]) failingByProduct[pid] = new Set()
      failingByProduct[pid].add(finding.check_id)
    }
  }

  const rows = products.slice(0, 25)

  const activeColumns = COLUMNS.filter(col =>
    rows.some(p => failingByProduct[p.product_id]?.has(col.id))
  )
  const displayColumns = activeColumns.length >= 3 ? activeColumns : COLUMNS

  const totalIssues = rows.reduce(
    (acc, p) => acc + (failingByProduct[p.product_id]?.size ?? 0),
    0
  )
  const cellsTotal = rows.length * displayColumns.length
  const redPct = cellsTotal > 0 ? Math.round((totalIssues / cellsTotal) * 100) : 0

  const CELL_W = 32
  const CELL_H = 20
  const CELL_GAP = 3

  return (
    <div style={{ fontFamily: 'var(--font-geist)' }}>
      {/* Legend row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-fg-3)' }}>
            {rows.length} products &times; {displayColumns.length} checks
          </span>
          <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-bad)' }}>
            {redPct}% failing
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--m-fg-3)' }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: 'rgba(213,122,120,0.8)', display: 'inline-block' }} />
            Failing
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--m-fg-3)' }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: 'rgba(143,184,154,0.2)', border: '1px solid rgba(143,184,154,0.3)', display: 'inline-block' }} />
            Passing
          </span>
        </div>
      </div>

      {/* Scrollable grid */}
      <div style={{ overflowX: 'auto', paddingBottom: 4 }}>
        <table style={{ borderCollapse: 'separate', borderSpacing: 0, width: '100%' }}>
          <thead>
            <tr>
              {/* Product name header */}
              <th style={{
                textAlign: 'left', paddingBottom: 10, paddingRight: 16,
                fontFamily: 'var(--font-geist-mono)', fontSize: 10,
                color: 'var(--m-fg-3)', fontWeight: 400,
                minWidth: 160, maxWidth: 200,
              }}>
                Product
              </th>
              {/* Column headers */}
              {displayColumns.map(col => (
                <th
                  key={col.id}
                  title={col.id}
                  style={{
                    paddingBottom: 10, paddingLeft: CELL_GAP / 2, paddingRight: CELL_GAP / 2,
                    textAlign: 'center', fontWeight: 400,
                    minWidth: CELL_W + CELL_GAP,
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                    <span style={{
                      fontFamily: 'var(--font-geist-mono)', fontSize: 9,
                      color: PILLAR_COLORS[col.pillar] ?? 'var(--m-fg-3)',
                      letterSpacing: '0.05em',
                    }}>
                      {col.id}
                    </span>
                    <span style={{
                      fontFamily: 'var(--font-geist-mono)', fontSize: 9,
                      color: 'var(--m-fg-3)', letterSpacing: '0.02em',
                    }}>
                      {col.label}
                    </span>
                  </div>
                </th>
              ))}
              {/* Gap score header */}
              <th style={{
                paddingBottom: 10, paddingLeft: 16, textAlign: 'right',
                fontFamily: 'var(--font-geist-mono)', fontSize: 10,
                color: 'var(--m-fg-3)', fontWeight: 400, whiteSpace: 'nowrap',
              }}>
                Issues
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((product) => {
              const failing = failingByProduct[product.product_id] ?? new Set<string>()
              const issueCount = failing.size
              const isHovered = hoveredRow === product.product_id
              return (
                <tr
                  key={product.product_id}
                  onMouseEnter={() => setHoveredRow(product.product_id)}
                  onMouseLeave={() => setHoveredRow(null)}
                  style={{ transition: 'background 100ms' }}
                >
                  {/* Product title */}
                  <td style={{ paddingTop: CELL_GAP / 2, paddingBottom: CELL_GAP / 2, paddingRight: 16 }}>
                    <span
                      title={product.title}
                      style={{
                        display: 'block',
                        maxWidth: 190,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        fontSize: 12,
                        color: isHovered ? 'var(--m-fg)' : 'var(--m-fg-2)',
                        transition: 'color 100ms',
                      }}
                    >
                      {product.title}
                    </span>
                  </td>
                  {/* Check cells */}
                  {displayColumns.map(col => {
                    const isFailing = failing.has(col.id)
                    const cellKey = `${product.product_id}-${col.id}`
                    const isHoveredCell = hoveredCell === cellKey
                    return (
                      <td
                        key={col.id}
                        style={{ paddingTop: CELL_GAP / 2, paddingBottom: CELL_GAP / 2, paddingLeft: CELL_GAP / 2, paddingRight: CELL_GAP / 2, textAlign: 'center' }}
                      >
                        <div
                          onMouseEnter={() => setHoveredCell(cellKey)}
                          onMouseLeave={() => setHoveredCell(null)}
                          title={isFailing ? `${col.id}: failing` : `${col.id}: passing`}
                          style={{
                            width: CELL_W,
                            height: CELL_H,
                            borderRadius: 4,
                            margin: '0 auto',
                            background: isFailing
                              ? isHoveredCell ? 'rgba(213,122,120,1)' : 'rgba(213,122,120,0.75)'
                              : isHoveredCell ? 'rgba(143,184,154,0.25)' : 'rgba(143,184,154,0.12)',
                            border: isFailing
                              ? '1px solid rgba(213,122,120,0.5)'
                              : '1px solid rgba(143,184,154,0.2)',
                            transition: 'background 120ms, border-color 120ms',
                          }}
                        />
                      </td>
                    )
                  })}
                  {/* Issue count */}
                  <td style={{ paddingTop: CELL_GAP / 2, paddingBottom: CELL_GAP / 2, paddingLeft: 16, textAlign: 'right' }}>
                    <span style={{
                      fontFamily: 'var(--font-geist-mono)', fontSize: 11,
                      color: issueCount === 0 ? 'var(--m-good)' : issueCount >= 5 ? 'var(--m-bad)' : 'var(--m-warn)',
                      opacity: issueCount === 0 ? 0.5 : 1,
                    }}>
                      {issueCount === 0 ? '✓' : issueCount}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {products.length > 25 && (
        <p style={{ marginTop: 10, fontSize: 11, color: 'var(--m-fg-3)', fontFamily: 'var(--font-geist-mono)', textAlign: 'center' }}>
          Showing worst {rows.length} of {products.length} products by issue count
        </p>
      )}
    </div>
  )
}
