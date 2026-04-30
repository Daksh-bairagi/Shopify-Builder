import type { PerceptionDiff as PerceptionDiffType } from '../api/client'

interface Props {
  diff: PerceptionDiffType
}

export default function PerceptionDiff({ diff }: Props) {
  return (
    <div style={{
      background: 'var(--ink-2)', border: '1px solid var(--ink-line)',
      borderRadius: 18, padding: 28, fontFamily: 'var(--font-geist)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
        <span style={{
          width: 28, height: 28, borderRadius: 8, border: '1px solid var(--m-violet-soft, rgba(180,160,214,0.25))',
          background: 'rgba(180,160,214,0.08)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--m-violet)',
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v10M7 12h10" />
          </svg>
        </span>
        <span style={{ fontFamily: 'var(--font-display)', fontSize: 18, color: 'var(--m-fg)' }}>AI Perception Gap</span>
        <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-fg-3)' }}>
          How AI actually sees your store vs. your intent
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 24 }}>
        <div style={{
          background: 'var(--ink-3)', border: '1px solid rgba(143,184,154,0.2)',
          borderRadius: 14, padding: '18px 20px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--m-good)' }} />
            <span className="eyebrow" style={{ color: 'var(--m-good)' }}>Your intent</span>
          </div>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--m-fg-2)', lineHeight: 1.55 }}>
            {diff.intended_positioning}
          </p>
        </div>

        <div style={{
          background: 'var(--ink-3)', border: '1px solid rgba(213,122,120,0.2)',
          borderRadius: 14, padding: '18px 20px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--m-bad)' }} />
            <span className="eyebrow" style={{ color: 'var(--m-bad)' }}>AI perception</span>
          </div>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--m-fg-2)', lineHeight: 1.55, fontStyle: 'italic' }}>
            {diff.ai_perception}
          </p>
        </div>
      </div>

      {diff.gap_reasons.length > 0 && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 12 }}>Why the gap exists</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {diff.gap_reasons.map((reason, i) => (
              <div
                key={i}
                style={{
                  display: 'flex', alignItems: 'flex-start', gap: 10,
                  padding: '10px 14px', borderRadius: 10,
                  background: 'rgba(212,169,107,0.06)',
                  border: '1px solid rgba(212,169,107,0.18)',
                }}
              >
                <svg
                  width="14" height="14" viewBox="0 0 24 24" fill="none"
                  stroke="var(--m-warn)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"
                  style={{ flexShrink: 0, marginTop: 2 }}
                >
                  <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
                <span style={{ fontSize: 13, color: 'var(--m-fg-2)', lineHeight: 1.5 }}>{reason}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
