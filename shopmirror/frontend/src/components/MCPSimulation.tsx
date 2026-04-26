import type { MCPResult } from '../api/client'

interface Props {
  results: MCPResult[]
  isSimulation?: boolean   // true when real MCP was unavailable, Gemini was used
}

type Classification = MCPResult['classification']

// Inline-style equivalents matching Dashboard design language
const RESULT_STYLES: Record<Classification, { border: string; bg: string; badgeBg: string; badgeColor: string }> = {
  ANSWERED: {
    border: 'rgba(143,184,154,0.2)',
    bg:     'rgba(143,184,154,0.04)',
    badgeBg:'rgba(143,184,154,0.12)',
    badgeColor: 'var(--m-good)',
  },
  UNANSWERED: {
    border: 'rgba(213,122,120,0.2)',
    bg:     'rgba(213,122,120,0.04)',
    badgeBg:'rgba(213,122,120,0.12)',
    badgeColor: 'var(--m-bad)',
  },
  WRONG: {
    border: 'rgba(212,169,107,0.25)',
    bg:     'rgba(212,169,107,0.04)',
    badgeBg:'rgba(212,169,107,0.12)',
    badgeColor: 'var(--m-warn)',
  },
}

const BADGE_LABEL: Record<Classification, string> = {
  ANSWERED:   '✓ Answered',
  UNANSWERED: '✗ No data',
  WRONG:      '⚠ Wrong',
}

export default function MCPSimulation({ results, isSimulation }: Props) {
  const answered   = results.filter(r => r.classification === 'ANSWERED').length
  const unanswered = results.filter(r => r.classification === 'UNANSWERED').length
  const wrong      = results.filter(r => r.classification === 'WRONG').length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Mode label */}
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 8,
        padding: '6px 12px', borderRadius: 100, alignSelf: 'flex-start',
        border: '1px solid var(--ink-line)', fontFamily: 'var(--font-geist-mono)',
        fontSize: 11, color: 'var(--m-fg-3)', letterSpacing: '0.04em',
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: isSimulation ? 'var(--m-warn)' : 'var(--m-good)', display: 'inline-block' }} />
        {isSimulation
          ? 'Simulated AI agent responses (based on your store\'s machine-readable data)'
          : 'Live Shopify MCP endpoint — real AI agent responses'}
      </div>

      {/* Summary counters */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        {[
          { n: answered,   l: 'Answered',    c: 'var(--m-good)', bg: 'rgba(143,184,154,0.08)', border: 'rgba(143,184,154,0.2)' },
          { n: unanswered, l: 'No data',     c: 'var(--m-bad)',  bg: 'rgba(213,122,120,0.08)', border: 'rgba(213,122,120,0.2)' },
          { n: wrong,      l: 'Wrong data',  c: 'var(--m-warn)', bg: 'rgba(212,169,107,0.08)', border: 'rgba(212,169,107,0.2)' },
        ].map(s => (
          <div key={s.l} style={{
            padding: '14px 16px', borderRadius: 14, textAlign: 'center',
            background: s.bg, border: `1px solid ${s.border}`,
          }}>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 36, lineHeight: 1, color: s.c }}>{s.n}</div>
            <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)', marginTop: 6, letterSpacing: '0.1em', textTransform: 'uppercase' }}>{s.l}</div>
          </div>
        ))}
      </div>

      {/* Result cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {results.map((result, i) => {
          const s = RESULT_STYLES[result.classification]
          return (
            <div key={i} style={{
              background: s.bg, border: `1px solid ${s.border}`,
              borderRadius: 14, padding: '16px 18px',
            }}>
              {/* Question row + badge */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 10 }}>
                <span style={{
                  flexShrink: 0, fontFamily: 'var(--font-geist-mono)', fontSize: 10,
                  padding: '3px 8px', borderRadius: 6, fontWeight: 600,
                  background: s.badgeBg, color: s.badgeColor,
                  letterSpacing: '0.06em', whiteSpace: 'nowrap', marginTop: 1,
                }}>
                  {BADGE_LABEL[result.classification]}
                </span>
                <p style={{ margin: 0, fontSize: 14, fontWeight: 500, color: 'var(--m-fg)', flex: 1, lineHeight: 1.4 }}>
                  {result.question}
                </p>
              </div>

              {/* AI response */}
              <p style={{
                margin: 0, fontSize: 13, color: 'var(--m-fg-2)', lineHeight: 1.55,
                fontStyle: result.classification === 'UNANSWERED' ? 'italic' : 'normal',
              }}>
                {result.response}
              </p>

              {/* Ground truth mismatch */}
              {result.ground_truth_mismatch && (
                <div style={{
                  marginTop: 10, padding: '8px 12px', borderRadius: 8,
                  background: 'rgba(212,169,107,0.08)', border: '1px solid rgba(212,169,107,0.2)',
                }}>
                  <span style={{ fontSize: 12, color: 'var(--m-warn)' }}>
                    ↳ {result.ground_truth_mismatch}
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>

    </div>
  )
}
