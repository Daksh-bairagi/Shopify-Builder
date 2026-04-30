import { useState } from 'react'
import type { BeforeAfterResponse, CopyPasteItem } from '../api/client'
import { overallFromPillars, pillarPercent } from '../utils/score'
import { CHECK_LABELS } from '../utils/labels'

interface Props {
  data: BeforeAfterResponse
  copyPasteItems: CopyPasteItem[]
  storeName: string
}

const PILLAR_ORDER = ['Discoverability', 'Completeness', 'Consistency', 'Trust_Policies', 'Transaction']
const PILLAR_LABELS: Record<string, string> = {
  Discoverability: 'Discoverability',
  Completeness: 'Completeness',
  Consistency: 'Consistency',
  Trust_Policies: 'Trust & Policies',
  Transaction: 'Transaction',
}

function scoreColorVar(score: number): string {
  if (score >= 70) return 'var(--m-good)'
  if (score >= 40) return 'var(--m-warn)'
  return 'var(--m-bad)'
}

function CopyPasteCard({ item }: { item: CopyPasteItem }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    await navigator.clipboard.writeText(item.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div style={{
      background: 'var(--ink-2)', border: '1px solid var(--ink-line)',
      borderRadius: 14, padding: 16, display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--m-fg)' }}>{item.label}</span>
        <button
          onClick={handleCopy}
          style={{
            fontSize: 11, fontFamily: 'var(--font-geist-mono)',
            color: copied ? 'var(--m-good)' : 'var(--m-violet)',
            background: 'transparent',
            border: `1px solid ${copied ? 'rgba(143,184,154,0.3)' : 'rgba(180,160,214,0.3)'}`,
            padding: '3px 10px', borderRadius: 6, cursor: 'pointer',
            transition: 'all 150ms',
          }}
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre style={{
        margin: 0, padding: '10px 12px', borderRadius: 8,
        background: 'rgba(0,0,0,0.2)', border: '1px solid var(--ink-line)',
        fontSize: 11, lineHeight: 1.5, fontFamily: 'var(--font-geist-mono)',
        color: 'var(--m-fg-3)', overflow: 'auto', maxHeight: 200, whiteSpace: 'pre-wrap',
      }}>
        {item.content}
      </pre>
    </div>
  )
}

export default function BeforeAfterReport({ data, copyPasteItems }: Props) {
  const beforeScore = overallFromPillars(data.original_pillars)
  const afterScore = overallFromPillars(data.current_pillars)
  const delta = afterScore - beforeScore

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32, fontFamily: 'var(--font-geist)' }}>
      {/* Score delta hero */}
      <div style={{
        background: 'var(--paper)', color: 'var(--paper-ink)',
        borderRadius: 20, padding: '28px 32px',
        display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', gap: 24,
      }}>
        <div style={{ textAlign: 'center' }}>
          <div className="eyebrow-paper" style={{ marginBottom: 8 }}>Before</div>
          <div style={{
            fontFamily: 'var(--font-display)', fontSize: 80, lineHeight: 0.9,
            color: beforeScore < 50 ? 'var(--m-bad-p)' : 'var(--m-warn-p)',
          }}>
            {beforeScore}
          </div>
          <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, opacity: 0.4, marginTop: 6 }}>/100</div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="rgba(26,24,18,0.35)" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>
          <span style={{
            fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 400,
            color: delta >= 0 ? '#2d7a4f' : 'var(--m-bad-p)',
          }}>
            {delta >= 0 ? '+' : ''}{delta}
          </span>
          <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, opacity: 0.45, letterSpacing: '0.08em' }}>pts</span>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div className="eyebrow-paper" style={{ marginBottom: 8 }}>After</div>
          <div style={{
            fontFamily: 'var(--font-display)', fontSize: 80, lineHeight: 0.9,
            color: afterScore >= 70 ? '#2d7a4f' : afterScore >= 50 ? 'var(--m-warn-p)' : 'var(--m-bad-p)',
          }}>
            {afterScore}
          </div>
          <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, opacity: 0.4, marginTop: 6 }}>/100</div>
        </div>
      </div>

      {/* Pillar comparison */}
      <div>
        <div className="eyebrow" style={{ marginBottom: 12 }}>Pillar breakdown</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {PILLAR_ORDER.map(pillar => {
            const before = data.original_pillars[pillar]
            const after = data.current_pillars[pillar]
            if (!before || !after) return null
            const bScore = pillarPercent(before)
            const aScore = pillarPercent(after)
            const improved = aScore > bScore
            return (
              <div key={pillar} style={{
                background: 'var(--ink-2)', border: '1px solid var(--ink-line)',
                borderRadius: 12, padding: '14px 18px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ fontSize: 13, color: 'var(--m-fg)', fontWeight: 500 }}>{PILLAR_LABELS[pillar]}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'var(--font-geist-mono)', fontSize: 12 }}>
                    <span style={{ color: scoreColorVar(bScore) }}>{bScore}</span>
                    <span style={{ color: 'var(--m-fg-4)' }}>→</span>
                    <span style={{ color: scoreColorVar(aScore), fontWeight: improved ? 600 : 400 }}>{aScore}</span>
                    {improved && <span style={{ fontSize: 10, color: 'var(--m-good)' }}>▲{aScore - bScore}</span>}
                  </div>
                </div>
                <div style={{ height: 3, background: 'rgba(255,255,255,0.05)', borderRadius: 100, overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${aScore}%`,
                      background: scoreColorVar(aScore),
                      borderRadius: 100,
                      transition: 'width 800ms cubic-bezier(.2,.8,.2,1)',
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Checks improved */}
      {data.checks_improved.length > 0 && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 12 }}>Fixed ({data.checks_improved.length})</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {data.checks_improved.map(id => (
              <span
                key={id}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  fontSize: 12, color: 'var(--m-good)',
                  background: 'rgba(143,184,154,0.1)',
                  border: '1px solid rgba(143,184,154,0.25)',
                  borderRadius: 8, padding: '5px 12px',
                }}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                {CHECK_LABELS[id] ?? id}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Checks unchanged */}
      {data.checks_unchanged.length > 0 && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 12 }}>Still needs attention ({data.checks_unchanged.length})</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {data.checks_unchanged.map(id => (
              <span
                key={id}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  fontSize: 12, color: 'var(--m-warn)',
                  background: 'rgba(212,169,107,0.08)',
                  border: '1px solid rgba(212,169,107,0.25)',
                  borderRadius: 8, padding: '5px 12px',
                }}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
                {CHECK_LABELS[id] ?? id}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Copy-paste package */}
      {copyPasteItems.length > 0 && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 12 }}>Copy-paste package ({copyPasteItems.length})</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {copyPasteItems.map((item, i) => <CopyPasteCard key={i} item={item} />)}
          </div>
        </div>
      )}
    </div>
  )
}
