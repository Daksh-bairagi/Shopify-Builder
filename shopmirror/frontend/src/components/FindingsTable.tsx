import { useState } from 'react'
import type { Finding } from '../api/client'
import { CHECK_LABELS } from '../utils/labels'

interface Props {
  findings: Finding[]
}

type SeverityFilter = 'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM'

const SEVERITY_CFG: Record<string, { color: string; bg: string; border: string; label: string }> = {
  CRITICAL: { color: 'var(--m-bad)',  bg: 'rgba(213,122,120,0.08)', border: 'rgba(213,122,120,0.2)', label: 'Critical' },
  HIGH:     { color: 'var(--m-warn)', bg: 'rgba(212,169,107,0.08)', border: 'rgba(212,169,107,0.2)', label: 'High' },
  MEDIUM:   { color: 'var(--m-info)', bg: 'rgba(107,169,212,0.08)', border: 'rgba(107,169,212,0.2)', label: 'Medium' },
}

const FIX_TYPE_CFG: Record<string, { label: string; color: string; bg: string; border: string }> = {
  auto:      { label: 'Auto-fix',   color: 'var(--m-good)', bg: 'rgba(143,184,154,0.1)', border: 'rgba(143,184,154,0.25)' },
  copy_paste:{ label: 'Paste this', color: 'var(--m-warn)', bg: 'rgba(212,169,107,0.1)', border: 'rgba(212,169,107,0.25)' },
  manual:    { label: 'Manual',     color: 'var(--m-fg-3)', bg: 'transparent',           border: 'var(--ink-line)' },
  developer: { label: 'Dev needed', color: 'var(--m-bad)',  bg: 'rgba(213,122,120,0.08)', border: 'rgba(213,122,120,0.2)' },
}

const FILTERS: { id: SeverityFilter; label: string }[] = [
  { id: 'ALL',      label: 'All' },
  { id: 'CRITICAL', label: 'Critical' },
  { id: 'HIGH',     label: 'High' },
  { id: 'MEDIUM',   label: 'Medium' },
]

export default function FindingsTable({ findings }: Props) {
  const [filter, setFilter] = useState<SeverityFilter>('ALL')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const filtered = filter === 'ALL' ? findings : findings.filter(f => f.severity === filter)

  const counts: Record<string, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0 }
  findings.forEach(f => { counts[f.severity] = (counts[f.severity] || 0) + 1 })

  async function copyContent(id: string, content: string) {
    await navigator.clipboard.writeText(content)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, fontFamily: 'var(--font-geist)' }}>

      {/* Filter pills */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {FILTERS.map(f => {
          const active = filter === f.id
          const count = f.id === 'ALL' ? findings.length : counts[f.id] || 0
          if (f.id !== 'ALL' && count === 0) return null
          return (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                padding: '6px 14px', borderRadius: 100, fontSize: 12, cursor: 'pointer',
                fontFamily: 'var(--font-geist)',
                background: active ? 'var(--m-violet)' : 'var(--ink-3)',
                color: active ? 'white' : 'var(--m-fg-2)',
                border: active ? '1px solid transparent' : '1px solid var(--ink-line)',
                transition: 'all 150ms ease',
              }}
            >
              {f.label}
              <span style={{
                fontFamily: 'var(--font-geist-mono)', fontSize: 10,
                opacity: active ? 0.8 : 0.5,
              }}>
                {count}
              </span>
            </button>
          )
        })}
      </div>

      {/* Finding cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--m-fg-3)', fontSize: 13 }}>
            No findings match this filter
          </div>
        )}
        {filtered.map(finding => {
          const sev = SEVERITY_CFG[finding.severity] ?? SEVERITY_CFG.MEDIUM
          const fix = FIX_TYPE_CFG[finding.fix_type] ?? FIX_TYPE_CFG.manual
          const isOpen = expandedId === finding.id

          return (
            <div key={finding.id}>
              {/* Row */}
              <div
                onClick={() => setExpandedId(isOpen ? null : finding.id)}
                style={{
                  display: 'flex', alignItems: 'flex-start', gap: 14,
                  padding: '14px 18px', borderRadius: isOpen ? '12px 12px 0 0' : 12,
                  background: isOpen ? 'var(--ink-2)' : 'var(--ink-3)',
                  border: `1px solid ${isOpen ? 'var(--ink-line-2)' : 'var(--ink-line)'}`,
                  borderBottom: isOpen ? '1px solid transparent' : undefined,
                  cursor: 'pointer', transition: 'background 150ms',
                }}
              >
                {/* Severity dot + label */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0, paddingTop: 1 }}>
                  <span style={{ width: 7, height: 7, borderRadius: '50%', background: sev.color, display: 'inline-block', flexShrink: 0 }} />
                  <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: sev.color, letterSpacing: '0.06em', width: 48 }}>
                    {sev.label}
                  </span>
                </div>

                {/* Title + category */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ margin: 0, fontSize: 13, color: 'var(--m-fg)', lineHeight: 1.4 }}>{finding.title}</p>
                  <p style={{ margin: '3px 0 0', fontSize: 11, color: 'var(--m-fg-3)', fontFamily: 'var(--font-geist-mono)' }}>
                    {CHECK_LABELS[finding.check_id] ?? finding.check_id} &middot; {finding.pillar?.replace('_', ' & ')}
                  </p>
                </div>

                {/* Right side: products affected + fix type */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
                  {finding.affected_count > 0 && (
                    <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-fg-3)' }}>
                      {finding.affected_count} product{finding.affected_count !== 1 ? 's' : ''}
                    </span>
                  )}
                  <span style={{
                    fontFamily: 'var(--font-geist-mono)', fontSize: 10, padding: '2px 8px',
                    borderRadius: 100, background: fix.bg, color: fix.color, border: `1px solid ${fix.border}`,
                  }}>
                    {fix.label}
                  </span>
                  <svg
                    width="12" height="12" viewBox="0 0 16 16" fill="none"
                    style={{ color: 'var(--m-fg-3)', transition: 'transform 200ms', transform: isOpen ? 'rotate(180deg)' : 'rotate(0)' }}
                  >
                    <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              </div>

              {/* Expanded detail */}
              {isOpen && (
                <div style={{
                  background: 'var(--ink-2)', border: '1px solid var(--ink-line-2)',
                  borderTop: 'none', borderRadius: '0 0 12px 12px',
                  padding: '16px 18px 20px', display: 'flex', flexDirection: 'column', gap: 14,
                }}>
                  {/* Detail */}
                  <p style={{ margin: 0, fontSize: 13, color: 'var(--m-fg-2)', lineHeight: 1.6 }}>{finding.detail}</p>

                  {/* Impact */}
                  {finding.impact_statement && (
                    <div style={{
                      display: 'flex', alignItems: 'flex-start', gap: 8,
                      padding: '10px 14px', borderRadius: 8,
                      background: 'rgba(212,169,107,0.06)', border: '1px solid rgba(212,169,107,0.15)',
                    }}>
                      <span style={{ fontSize: 13, color: 'var(--m-warn)', flexShrink: 0, marginTop: 1 }}>!</span>
                      <p style={{ margin: 0, fontSize: 12, color: 'var(--m-warn)', lineHeight: 1.5, fontStyle: 'italic' }}>
                        {finding.impact_statement}
                      </p>
                    </div>
                  )}

                  {/* What to do */}
                  {finding.fix_instruction && (
                    <div>
                      <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8 }}>
                        What to do
                      </div>
                      <div style={{
                        background: 'rgba(0,0,0,0.2)', border: '1px solid var(--ink-line)',
                        borderRadius: 8, padding: '10px 14px', fontSize: 12,
                        fontFamily: 'var(--font-geist-mono)', color: 'var(--m-fg-2)',
                        whiteSpace: 'pre-wrap', lineHeight: 1.6,
                      }}>
                        {finding.fix_instruction}
                      </div>
                    </div>
                  )}

                  {/* Code to paste */}
                  {finding.fix_content && (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                        <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                          Code to paste
                        </div>
                        <button
                          onClick={e => { e.stopPropagation(); copyContent(finding.id, finding.fix_content!) }}
                          style={{
                            display: 'inline-flex', alignItems: 'center', gap: 5,
                            fontSize: 11, color: copiedId === finding.id ? 'var(--m-good)' : 'var(--m-violet)',
                            background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-geist)',
                          }}
                        >
                          {copiedId === finding.id ? 'Copied!' : 'Copy'}
                        </button>
                      </div>
                      <div style={{
                        background: 'rgba(0,0,0,0.25)', border: '1px solid var(--ink-line)',
                        borderRadius: 8, padding: '10px 14px', fontSize: 11,
                        fontFamily: 'var(--font-geist-mono)', color: 'var(--m-fg-3)',
                        maxHeight: 160, overflowY: 'auto', whiteSpace: 'pre-wrap', lineHeight: 1.6,
                      }}>
                        {finding.fix_content}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
