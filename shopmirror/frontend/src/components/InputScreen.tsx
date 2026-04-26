import { useState } from 'react'
import { AnalyzeRequest } from '../api/client'

interface Props {
  onSubmit: (req: AnalyzeRequest) => void
  error: string | null
}

function ArrowRight({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
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

export default function InputScreen({ onSubmit, error }: Props) {
  const [loading, setLoading] = useState(false)
  const [showToken, setShowToken] = useState(false)
  const [storeUrl, setStoreUrl] = useState('')
  const [adminToken, setAdminToken] = useState('')
  const [merchantIntent, setMerchantIntent] = useState('')
  const [competitorUrl1, setCompetitorUrl1] = useState('')
  const [competitorUrl2, setCompetitorUrl2] = useState('')

  function normalizeUrl(raw: string): string {
    let url = raw.trim()
    url = url.replace(/^https?:\/\//, '')
    url = url.replace(/\/$/, '')
    return url
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const normalized = normalizeUrl(storeUrl)
    if (!normalized) return
    setLoading(true)
    const req: AnalyzeRequest = { store_url: normalized }
    const token = adminToken.trim()
    if (token) req.admin_token = token
    const intent = merchantIntent.trim()
    if (intent) req.merchant_intent = intent
    const competitors: string[] = []
    if (competitorUrl1.trim()) competitors.push(competitorUrl1.trim())
    if (competitorUrl2.trim()) competitors.push(competitorUrl2.trim())
    if (competitors.length > 0) req.competitor_urls = competitors
    try {
      await onSubmit(req)
    } finally {
      setLoading(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    background: 'transparent',
    border: 'none',
    borderBottom: '1px solid var(--ink-line-2)',
    padding: '12px 0',
    fontSize: 20,
    fontFamily: 'var(--font-display)',
    color: 'var(--m-fg)',
    outline: 'none',
    width: '100%',
  }

  const areaStyle: React.CSSProperties = {
    background: 'transparent',
    border: '1px solid var(--ink-line)',
    borderRadius: 12,
    padding: 14,
    fontSize: 14,
    fontFamily: 'var(--font-geist)',
    color: 'var(--m-fg)',
    outline: 'none',
    resize: 'none',
    width: '100%',
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      position: 'relative',
      background: 'var(--ink)',
      fontFamily: 'var(--font-geist)',
    }}>
      {/* Seam */}
      <div className="seam-line" />

      {/* LEFT — form */}
      <div style={{ padding: '64px 72px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', color: 'var(--m-fg)' }}>
        <Logo />

        <div style={{ maxWidth: 460 }}>
          <div className="eyebrow">Step 01 — Identify</div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(36px,4vw,60px)', lineHeight: 1.0, letterSpacing: '-0.02em', fontWeight: 400, margin: '16px 0 40px', color: 'var(--m-fg)' }}>
            Where's your<br />
            <em style={{ fontStyle: 'italic', color: 'var(--m-violet)' }}>storefront?</em>
          </h1>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {/* Store URL */}
            <label style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <span className="eyebrow">Storefront URL <span style={{ color: 'var(--m-bad)' }}>*</span></span>
              <input
                type="text"
                value={storeUrl}
                onChange={e => setStoreUrl(e.target.value)}
                placeholder="yourstore.myshopify.com"
                required
                style={inputStyle}
                onFocus={e => (e.target.style.borderColor = 'var(--m-violet)')}
                onBlur={e => (e.target.style.borderColor = 'var(--ink-line-2)')}
              />
              <span style={{ fontSize: 11, color: 'var(--m-fg-3)', fontFamily: 'var(--font-geist)' }}>
                Public storefront — disable password protection if on a dev store.
              </span>
            </label>

            {/* Brand context */}
            <label style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <span className="eyebrow">
                Brand context <span style={{ color: 'var(--m-fg-4)', textTransform: 'none', letterSpacing: 0, fontFamily: 'var(--font-geist)' }}>· optional</span>
              </span>
              <textarea
                rows={2}
                value={merchantIntent}
                onChange={e => setMerchantIntent(e.target.value)}
                placeholder="e.g. Premium sustainable outdoor gear for serious hikers"
                style={areaStyle}
              />
              <span style={{ fontSize: 11, color: 'var(--m-fg-3)' }}>
                Tells the mirror what you <em style={{ fontFamily: 'var(--font-display)', fontStyle: 'italic' }}>intended</em> to be — so we can measure the gap.
              </span>
            </label>

            {/* Admin token */}
            <div style={{ border: '1px solid var(--ink-line)', borderRadius: 12, padding: 16 }}>
              {!showToken ? (
                <button
                  type="button"
                  onClick={() => setShowToken(true)}
                  style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 12, textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer' }}
                >
                  <span style={{ width: 28, height: 28, borderRadius: 8, border: '1px solid var(--m-violet-soft)', background: 'rgba(180,160,214,0.08)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: 'var(--m-violet)', fontSize: 16, fontWeight: 400 }}>+</span>
                  <span style={{ flex: 1 }}>
                    <span style={{ display: 'block', fontSize: 14, fontWeight: 500, color: 'var(--m-fg)' }}>Add Admin Token</span>
                    <span style={{ fontSize: 11, color: 'var(--m-fg-3)' }}>Unlocks autonomous fixes — taxonomy, metafields, descriptions.</span>
                  </span>
                </button>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span className="eyebrow" style={{ color: 'var(--m-violet)' }}>Admin Token</span>
                    <button type="button" onClick={() => { setShowToken(false); setAdminToken('') }} style={{ fontSize: 11, color: 'var(--m-fg-3)', background: 'none', border: 'none', cursor: 'pointer' }}>remove</button>
                  </div>
                  <input
                    type="password"
                    value={adminToken}
                    onChange={e => setAdminToken(e.target.value)}
                    placeholder="shpat_..."
                    autoFocus
                    style={{ background: 'var(--ink-3)', border: '1px solid var(--ink-line)', borderRadius: 8, padding: 10, fontFamily: 'var(--font-geist-mono)', color: 'var(--m-fg)', outline: 'none', width: '100%' }}
                  />
                </div>
              )}
            </div>

            {/* Competitor URLs */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <span className="eyebrow">
                Competitor URLs <span style={{ color: 'var(--m-fg-4)', textTransform: 'none', letterSpacing: 0, fontFamily: 'var(--font-geist)' }}>· optional, max 2</span>
              </span>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { val: competitorUrl1, set: setCompetitorUrl1 },
                  { val: competitorUrl2, set: setCompetitorUrl2 },
                ].map((c, i) => (
                  <input
                    key={i}
                    type="text"
                    value={c.val}
                    onChange={e => c.set(e.target.value)}
                    placeholder="competitor.myshopify.com"
                    style={{ ...areaStyle, padding: '10px 12px', fontFamily: 'var(--font-geist)', fontSize: 13 }}
                  />
                ))}
              </div>
            </div>

            {/* Error */}
            {error && (
              <div style={{ background: 'rgba(213,122,120,0.08)', border: '1px solid rgba(213,122,120,0.25)', borderRadius: 12, padding: '12px 16px', display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <svg style={{ width: 14, height: 14, color: 'var(--m-bad)', marginTop: 1, flexShrink: 0 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
                <p style={{ margin: 0, fontSize: 13, color: 'var(--m-bad)' }}>{error}</p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !storeUrl.trim()}
              style={{
                marginTop: 8,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                padding: '16px 24px', borderRadius: 100,
                background: loading || !storeUrl.trim() ? 'rgba(236,232,245,0.3)' : 'var(--m-fg)',
                color: 'var(--ink)', border: 'none', fontSize: 15, fontWeight: 500, cursor: loading || !storeUrl.trim() ? 'not-allowed' : 'pointer',
                transition: 'background 200ms', fontFamily: 'var(--font-geist)',
              }}
            >
              {loading ? (
                <>
                  <span style={{ display: 'inline-block', width: 14, height: 14, borderRadius: '50%', border: '2px solid rgba(14,13,18,0.3)', borderTopColor: 'var(--ink)', animation: 'spin 700ms linear infinite' }} />
                  Analyzing…
                </>
              ) : (
                <>Run audit <ArrowRight /></>
              )}
            </button>
          </form>
        </div>

        {/* Trust badges */}
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          {['Token never stored', 'Results in ~60 s', 'Every fix reversible'].map(t => (
            <span key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--m-fg-3)', fontFamily: 'var(--font-geist)' }}>
              <span style={{ width: 4, height: 4, background: 'var(--m-violet)', borderRadius: '50%', display: 'inline-block' }} />
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* RIGHT — paper preview */}
      <div style={{ background: 'var(--paper)', color: 'var(--paper-ink)', padding: '64px 72px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div className="eyebrow-paper">The reflection — what we'll run</div>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(24px,3vw,40px)', lineHeight: 1.1, letterSpacing: '-0.015em', fontWeight: 400, margin: '16px 0 56px', fontStyle: 'italic', color: 'var(--paper-ink)', maxWidth: 480 }}>
          We'll read your store the way an AI agent does — and show you the gap, line by line.
        </h2>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          {[
            { l: 'Crawling storefront',   c: 'Public catalog, sitemap, schema.org' },
            { l: 'Reading product feed',  c: 'Variants, options, pricing, inventory' },
            { l: 'Running 19 checks',     c: 'Across 5 pillars, 5 channels' },
            { l: 'Querying agents',        c: 'Gemini · GPT · Perplexity · MCP' },
            { l: 'Generating fix plan',   c: 'Auto · copy-paste · manual' },
          ].map((s, i, arr) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '14px 0', borderBottom: i < arr.length - 1 ? '1px solid var(--paper-line)' : 'none' }}>
              <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--paper-ink)', opacity: 0.5, width: 24 }}>0{i + 1}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 500 }}>{s.l}</div>
                <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, opacity: 0.55, marginTop: 2 }}>{s.c}</div>
              </div>
              <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, opacity: 0.35 }}>—</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
