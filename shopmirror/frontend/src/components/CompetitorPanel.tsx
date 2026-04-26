import type { CompetitorResult } from '../api/client'
import { CHECK_LABELS } from '../utils/labels'

interface Props {
  results: CompetitorResult[]
}

export default function CompetitorPanel({ results }: Props) {
  if (results.length === 0) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontFamily: 'var(--font-geist)' }}>
      {results.map((result, i) => {
        const gaps = result.gaps ?? []
        const hasGaps = gaps.length > 0

        return (
          <div key={i} style={{
            background: 'var(--ink-2)', border: '1px solid var(--ink-line)',
            borderRadius: 16, padding: '20px 24px',
          }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, marginBottom: hasGaps ? 16 : 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--m-info)', display: 'inline-block', flexShrink: 0 }} />
                <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--m-fg)' }}>
                  {result.competitor.store_domain}
                </span>
              </div>
              {hasGaps ? (
                <span style={{
                  fontFamily: 'var(--font-geist-mono)', fontSize: 10, padding: '3px 10px',
                  borderRadius: 100, background: 'rgba(213,122,120,0.08)',
                  color: 'var(--m-bad)', border: '1px solid rgba(213,122,120,0.2)',
                }}>
                  They are ahead on {gaps.length} thing{gaps.length !== 1 ? 's' : ''}
                </span>
              ) : (
                <span style={{
                  fontFamily: 'var(--font-geist-mono)', fontSize: 10, padding: '3px 10px',
                  borderRadius: 100, background: 'rgba(143,184,154,0.08)',
                  color: 'var(--m-good)', border: '1px solid rgba(143,184,154,0.2)',
                }}>
                  You are ahead
                </span>
              )}
            </div>

            {/* Gap list — readable names only */}
            {hasGaps && (
              <div>
                <p style={{ margin: '0 0 10px', fontSize: 11, color: 'var(--m-fg-3)', fontFamily: 'var(--font-geist-mono)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  Where they have an edge
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {gaps.map((gap: string) => (
                    <span key={gap} style={{
                      fontSize: 12, padding: '4px 10px', borderRadius: 8,
                      background: 'rgba(213,122,120,0.06)', color: 'var(--m-fg-2)',
                      border: '1px solid rgba(213,122,120,0.15)',
                    }}>
                      {CHECK_LABELS[gap] ?? gap}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
