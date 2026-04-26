import { JobStatusResponse } from '../api/client'

interface Props {
  status: JobStatusResponse
}

const STEPS = [
  { l: 'Connecting to storefront',   d: 'Pulling sitemap, robots.txt, theme metadata' },
  { l: 'Ingesting product catalog',  d: 'Products, variants, pricing, inventory' },
  { l: 'Running 19 structural checks', d: 'GTIN, taxonomy, metafields, schema.org' },
  { l: 'Probing AI shopping agents', d: 'Gemini · Perplexity · Shopify MCP' },
  { l: 'Computing perception gap',   d: 'Intended positioning vs. AI-extracted view' },
  { l: 'Drafting fix plan',          d: 'Sorting by impact · auto vs. copy-paste vs. manual' },
]

function statusToStep(s: JobStatusResponse['status']): number {
  switch (s) {
    case 'pending':
    case 'ingesting':   return 0
    case 'auditing':    return 2
    case 'simulating':  return 3
    case 'awaiting_approval':
    case 'complete':    return 5
    default:            return 0
  }
}

function Logo() {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
      <svg width={28} height={28} viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="14" stroke="var(--m-fg)" strokeOpacity="0.25" strokeWidth="1" />
        <path d="M9 11 Q16 8 23 11 M9 21 Q16 24 23 21" stroke="var(--m-fg)" strokeWidth="1.4" strokeLinecap="round" fill="none" />
        <line x1="16" y1="3" x2="16" y2="29" stroke="var(--m-violet)" strokeWidth="1" strokeDasharray="2 2" />
      </svg>
      <span style={{ fontFamily: 'var(--font-display)', fontSize: 19, letterSpacing: '-0.02em', color: 'var(--m-fg)' }}>
        Shop<em style={{ fontStyle: 'italic', color: 'var(--m-violet)' }}>Mirror</em>
      </span>
    </span>
  )
}

export default function ProgressScreen({ status }: Props) {
  const activeStep = statusToStep(status.status)
  const pct = status.progress.pct

  return (
    <div style={{
      minHeight: '100vh',
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      position: 'relative',
      background: 'var(--ink)',
      fontFamily: 'var(--font-geist)',
    }}>
      {/* Animated seam */}
      <div className="seam-line">
        <div className="scanline-anim" />
      </div>

      {/* LEFT — step list */}
      <div style={{ padding: '64px 72px', display: 'flex', flexDirection: 'column', gap: 48, color: 'var(--m-fg)' }}>
        <Logo />

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div className="eyebrow">Auditing</div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(36px,4vw,60px)', lineHeight: 1.0, letterSpacing: '-0.02em', fontWeight: 400, margin: '16px 0 56px', color: 'var(--m-fg)' }}>
            Holding the<br />
            <em style={{ fontStyle: 'italic', color: 'var(--m-violet)' }}>mirror</em> up to<br />
            your store…
          </h1>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {STEPS.map((s, i) => {
              const active = i === activeStep
              const done   = i < activeStep
              return (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 16,
                  padding: '14px 0',
                  borderBottom: i < STEPS.length - 1 ? '1px solid var(--ink-line)' : 'none',
                  opacity: done ? 0.4 : active ? 1 : 0.28,
                  transition: 'opacity 300ms ease',
                }}>
                  <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: active ? 'var(--m-violet)' : 'var(--m-fg-3)', width: 24, flexShrink: 0 }}>0{i + 1}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, fontWeight: active ? 500 : 400, color: active ? 'var(--m-fg)' : 'var(--m-fg-2)' }}>{s.l}</div>
                    <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)', marginTop: 2 }}>{s.d}</div>
                  </div>
                  {done && <span style={{ color: 'var(--m-good)', fontSize: 12 }}>✓</span>}
                  {active && (
                    <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', border: '1.5px solid var(--m-violet)', borderTopColor: 'transparent', animation: 'spin 700ms linear infinite', flexShrink: 0 }} />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Progress bar */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
            <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-fg-3)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Progress</span>
            <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 12, color: 'var(--m-violet)' }}>{Math.floor(pct)}%</span>
          </div>
          <div style={{ height: 2, background: 'var(--ink-line)', borderRadius: 100, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${pct}%`, background: 'var(--m-violet)', transition: 'width 400ms linear', borderRadius: 100 }} />
          </div>
          <p style={{ marginTop: 8, fontSize: 12, color: 'var(--m-fg-3)', textAlign: 'center' }}>
            {status.progress.step || 'Starting analysis…'}
          </p>
        </div>
      </div>

      {/* RIGHT — paper scan */}
      <div style={{ background: 'var(--paper)', color: 'var(--paper-ink)', padding: '64px 72px', display: 'flex', flexDirection: 'column', gap: 32, position: 'relative', overflow: 'hidden' }}>
        <div className="eyebrow-paper">Reflection — live</div>

        {/* Product grid being revealed */}
        <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, alignContent: 'start' }}>
          {Array.from({ length: 24 }).map((_, i) => {
            const revealed = (i / 24) * 100 < pct + 8
            return (
              <div key={i} style={{
                aspectRatio: '1',
                borderRadius: 8,
                border: '1px solid var(--paper-line)',
                background: revealed ? 'rgba(0,0,0,0.04)' : 'var(--paper-2)',
                position: 'relative', overflow: 'hidden',
                transition: 'background 400ms ease',
              }}>
                <div style={{
                  position: 'absolute', inset: 8,
                  display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
                  opacity: revealed ? 1 : 0.2,
                  transition: 'opacity 400ms ease',
                }}>
                  <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 9, opacity: 0.5 }}>P-{String(i + 1).padStart(3, '0')}</span>
                  <div style={{
                    height: 3, borderRadius: 100,
                    background: revealed
                      ? i % 5 === 0 ? 'var(--m-bad-p)' : i % 3 === 0 ? 'var(--m-warn-p)' : 'var(--m-good-p)'
                      : 'var(--paper-line)',
                  }} />
                </div>
              </div>
            )
          })}
        </div>

        {/* Ticker */}
        <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 12, color: 'var(--paper-ink)', opacity: 0.7, padding: '12px 0', borderTop: '1px solid var(--paper-line)' }}>
          <span style={{ color: 'var(--m-violet-2)' }}>›</span>{' '}
          {STEPS[Math.min(activeStep, STEPS.length - 1)]?.l}…
        </div>

        {/* Scan line on paper */}
        <div style={{
          position: 'absolute', left: 0, right: 0, height: 2,
          background: 'linear-gradient(to right, transparent, var(--m-violet-2), transparent)',
          opacity: 0.4,
          animation: 'scanMove 3.6s ease-in-out infinite',
        }} />
      </div>
    </div>
  )
}
