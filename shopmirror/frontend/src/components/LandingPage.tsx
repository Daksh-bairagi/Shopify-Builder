import { useState, useEffect } from 'react'

interface Props {
  onGetStarted: () => void
}

function ArrowRight({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

const PILLARS = [
  { n: '01', label: 'Discoverability', desc: 'Schema, GTINs, taxonomy — can agents find you?' },
  { n: '02', label: 'Completeness',    desc: 'Descriptions, materials, specs, sizes — all present?' },
  { n: '03', label: 'Consistency',     desc: 'Prices, inventory, copy matching across channels.' },
  { n: '04', label: 'Trust & Policies',desc: 'Returns, warranty, shipping — trust signals AI weights.' },
  { n: '05', label: 'Transaction',     desc: 'Cart, checkout, payment options visible to agents.' },
]

export default function LandingPage({ onGetStarted }: Props) {
  const [mouseX, setMouseX] = useState(0.5)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div
      style={{ background: 'var(--ink)', color: 'var(--m-fg)', fontFamily: 'var(--font-geist)', minHeight: '100vh', overflowX: 'hidden' }}
      onMouseMove={(e) => setMouseX(e.clientX / window.innerWidth)}
    >
      {/* ── Sticky nav ──────────────────────────────────────────────── */}
      <header style={{
        position: 'sticky', top: 0, zIndex: 50,
        backdropFilter: 'blur(12px)',
        background: scrolled ? 'rgba(14,13,18,0.85)' : 'rgba(14,13,18,0.5)',
        borderBottom: scrolled ? '1px solid var(--ink-line)' : '1px solid transparent',
        transition: 'background 300ms, border-color 300ms',
      }}>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 32px', height: 64, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Logo />
          <nav style={{ display: 'flex', gap: 28, alignItems: 'center' }}>
            <a href="#how" style={{ fontFamily: 'var(--font-geist)', fontSize: 13, color: 'var(--m-fg-2)', textDecoration: 'none' }}>How it works</a>
            <a href="#pillars" style={{ fontFamily: 'var(--font-geist)', fontSize: 13, color: 'var(--m-fg-2)', textDecoration: 'none' }}>What we check</a>
            <button
              onClick={onGetStarted}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 18px', borderRadius: 100, background: 'var(--m-fg)', color: 'var(--ink)', border: 'none', fontSize: 13, fontWeight: 500, cursor: 'pointer', transition: 'background 200ms' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--m-violet)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'var(--m-fg)')}
            >
              Audit my store <ArrowRight />
            </button>
          </nav>
        </div>
      </header>

      {/* ── Hero ────────────────────────────────────────────────────── */}
      <section style={{ position: 'relative', minHeight: '92vh' }}>
        {/* grid bg texture */}
        <div style={{
          position: 'absolute', inset: 0, opacity: 0.35, pointerEvents: 'none',
          backgroundImage: 'linear-gradient(to right,rgba(180,160,214,0.04) 1px,transparent 1px),linear-gradient(to bottom,rgba(180,160,214,0.04) 1px,transparent 1px)',
          backgroundSize: '80px 80px',
        }} />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: '92vh', position: 'relative' }}>

          {/* LEFT — You */}
          <div style={{ padding: '120px 64px 80px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <div className="eyebrow" style={{ marginBottom: 28 }}>You — the merchant</div>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(52px,7vw,120px)', lineHeight: 0.92, letterSpacing: '-0.025em', fontWeight: 400, margin: 0, color: 'var(--m-fg)' }}>
              You sell<br />
              <span style={{ color: 'var(--m-violet)' }}>great</span><br />
              <em style={{ fontStyle: 'italic' }}>products.</em>
            </h1>
            <p style={{ marginTop: 32, maxWidth: 460, fontSize: 17, lineHeight: 1.55, color: 'var(--m-fg-2)', fontFamily: 'var(--font-geist)' }}>
              Premium, curated, built with care. That's the brand you've spent years growing — the one your customers know by heart.
            </p>
          </div>

          {/* RIGHT — Mirror */}
          <div style={{
            padding: '120px 64px 80px',
            background: 'var(--paper)',
            color: 'var(--paper-ink)',
            display: 'flex', flexDirection: 'column', justifyContent: 'center',
            position: 'relative',
            transform: `skewX(${(mouseX - 0.5) * -0.3}deg)`,
            transformOrigin: 'left center',
            transition: 'transform 600ms ease',
          }}>
            <div className="eyebrow-paper" style={{ marginBottom: 28 }}>The mirror — what AI sees</div>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(52px,7vw,120px)', lineHeight: 0.92, letterSpacing: '-0.025em', fontWeight: 400, margin: 0, color: 'var(--paper-ink)', fontStyle: 'italic', opacity: 0.88 }}>
              Generic<br />
              store.<br />
              <span style={{ color: 'var(--m-violet-2)', fontStyle: 'normal' }}>Invisible.</span>
            </h1>
            <p style={{ marginTop: 32, maxWidth: 460, fontSize: 17, lineHeight: 1.55, color: 'rgba(26,24,18,0.72)', fontFamily: 'var(--font-geist)' }}>
              That's how AI shopping agents — Google, Meta, ChatGPT, Perplexity — read your store. Your story doesn't make it through their filter.
            </p>
          </div>

          {/* Seam */}
          <div className="seam-line" />
        </div>

        {/* CTA strip */}
        <div style={{ position: 'absolute', bottom: 56, left: '50%', transform: 'translateX(-50%)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18, zIndex: 10 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderRadius: 100,
            border: '1px solid var(--ink-line)', fontFamily: 'var(--font-geist-mono)', fontSize: 11, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--m-fg-2)',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--m-violet)', display: 'inline-block' }} />
            19 checks · 5 channels · ~30 second scan
          </div>
          <button
            onClick={onGetStarted}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 10, padding: '16px 28px', borderRadius: 100, background: 'var(--m-fg)', color: 'var(--ink)', border: 'none', fontSize: 15, fontWeight: 500, cursor: 'pointer', fontFamily: 'var(--font-geist)' }}
          >
            See what AI sees of your store <ArrowRight size={16} />
          </button>
          <span style={{ fontFamily: 'var(--font-geist)', fontSize: 12, color: 'var(--m-fg-3)' }}>
            Free public scan · admin token optional · no signup
          </span>
        </div>
      </section>

      {/* ── The Gap ─────────────────────────────────────────────────── */}
      <section style={{ padding: '140px 0', borderTop: '1px solid var(--ink-line)' }}>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 32px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 80, alignItems: 'start' }}>
            <div>
              <div className="eyebrow">The Gap</div>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(36px,4vw,64px)', lineHeight: 1.0, letterSpacing: '-0.02em', margin: '24px 0 0', fontWeight: 400, color: 'var(--m-fg)' }}>
                Your products<br />
                are <em style={{ fontStyle: 'italic', color: 'var(--m-violet)' }}>invisible</em><br />
                to AI agents.
              </h2>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
              <p style={{ fontSize: 19, lineHeight: 1.55, color: 'var(--m-fg)', margin: 0 }}>
                When a buyer asks ChatGPT, Perplexity or Google's AI for your product category — agents read your structured data, not your hero copy.
              </p>
              <p style={{ fontSize: 16, lineHeight: 1.55, color: 'var(--m-fg-2)', margin: 0 }}>
                Missing GTINs, thin metafields, descriptions that don't surface what you actually make. The agent shrugs and recommends someone else.{' '}
                <em style={{ fontFamily: 'var(--font-display)', fontStyle: 'italic' }}>ShopMirror</em> tells you exactly what's getting lost — and fixes it autonomously.
              </p>
              <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                <button onClick={onGetStarted} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '14px 22px', borderRadius: 100, background: 'var(--m-fg)', color: 'var(--ink)', border: 'none', fontSize: 14, fontWeight: 500, cursor: 'pointer' }}>
                  Run my audit <ArrowRight />
                </button>
                <a href="#how" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '14px 22px', borderRadius: 100, background: 'none', color: 'var(--m-fg)', border: '1px solid var(--ink-line)', fontSize: 14, fontWeight: 500, cursor: 'pointer', textDecoration: 'none' }}>
                  How it works
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── HOW ─────────────────────────────────────────────────────── */}
      <section id="how" style={{ padding: '140px 0', borderTop: '1px solid var(--ink-line)' }}>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 32px' }}>
          <div className="eyebrow" style={{ display: 'block', textAlign: 'center', marginBottom: 16 }}>The Process</div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(32px,4vw,60px)', lineHeight: 1.0, letterSpacing: '-0.02em', fontWeight: 400, margin: '0 0 80px', textAlign: 'center', color: 'var(--m-fg)' }}>
            Three steps. <em style={{ fontStyle: 'italic', color: 'var(--m-violet)' }}>Sixty seconds.</em>
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 0 }}>
            {[
              { n: '01', t: 'Paste your URL', d: 'Public scan needs nothing more. Add your Admin token to unlock fixes.' },
              { n: '02', t: 'Mirror runs 19 checks', d: 'Catalog completeness, taxonomy, metafields, AI query matching, multi-channel compliance — all in parallel.' },
              { n: '03', t: 'Approve the fixes', d: 'Auto-fix, copy-paste, or manual — every change is reviewed before it ships, and every change is reversible.' },
            ].map((s, i) => (
              <div key={s.n} style={{ padding: '0 32px', borderRight: i < 2 ? '1px solid var(--ink-line)' : 'none', display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 64, color: 'var(--m-violet)', lineHeight: 1, letterSpacing: '-0.03em' }}>{s.n}</div>
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 28, lineHeight: 1.05, fontWeight: 400, margin: 0, color: 'var(--m-fg)' }}>{s.t}</h3>
                <p style={{ fontSize: 15, lineHeight: 1.55, color: 'var(--m-fg-2)', margin: 0 }}>{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── What we check ───────────────────────────────────────────── */}
      <section id="pillars" style={{ padding: '140px 0', borderTop: '1px solid var(--ink-line)' }}>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 32px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80, alignItems: 'start', marginBottom: 64 }}>
            <div>
              <div className="eyebrow">The Audit</div>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(32px,4vw,60px)', lineHeight: 1.0, letterSpacing: '-0.02em', fontWeight: 400, margin: '24px 0 0', color: 'var(--m-fg)' }}>
                Five pillars.<br />
                <em style={{ fontStyle: 'italic', color: 'var(--m-violet)' }}>Nineteen</em> checks.
              </h2>
            </div>
            <p style={{ fontSize: 17, lineHeight: 1.55, color: 'var(--m-fg-2)', margin: 0, alignSelf: 'end' }}>
              The score isn't a vibe. Each pillar is a weighted set of binary checks against the actual specs Google, Meta, OpenAI and Anthropic publish for AI commerce ingestion.
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 16 }}>
            {PILLARS.map((p) => (
              <div key={p.n} style={{ background: 'var(--ink-2)', border: '1px solid var(--ink-line)', borderRadius: 18, padding: 24, display: 'flex', flexDirection: 'column', gap: 12, minHeight: 200 }}>
                <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)', letterSpacing: '0.1em' }}>{p.n}</span>
                <h3 style={{ fontFamily: 'var(--font-geist)', fontSize: 15, fontWeight: 600, margin: 0, color: 'var(--m-fg)', letterSpacing: '-0.01em' }}>{p.label}</h3>
                <p style={{ fontSize: 12, color: 'var(--m-fg-3)', lineHeight: 1.5, margin: 0, flex: 1 }}>{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Sample score card ───────────────────────────────────────── */}
      <section style={{ padding: '100px 0', borderTop: '1px solid var(--ink-line)' }}>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 32px' }}>
          <div className="eyebrow" style={{ display: 'block', textAlign: 'center', marginBottom: 16 }}>Example Report</div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px,3vw,48px)', lineHeight: 1.05, fontWeight: 400, margin: '0 0 48px', textAlign: 'center', color: 'var(--m-fg)' }}>
            Here's what your audit looks like.
          </h2>
          <div style={{ maxWidth: 720, margin: '0 auto', background: 'var(--ink-2)', border: '1px solid var(--ink-line)', borderRadius: 24, overflow: 'hidden' }}>
            {/* score row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', borderBottom: '1px solid var(--ink-line)' }}>
              <div style={{ padding: 32 }}>
                <div className="eyebrow" style={{ marginBottom: 16 }}>AI Readiness Score</div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 96, lineHeight: 0.9, letterSpacing: '-0.04em', color: 'var(--m-fg)', position: 'relative', display: 'inline-block' }}>
                  54
                  <span style={{ position: 'absolute', right: -22, top: 10, fontSize: 14, color: 'var(--m-fg-3)', opacity: 0.55 }}>/100</span>
                </div>
                <div style={{ marginTop: 8, fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-warn)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Needs work</div>
              </div>
              <div style={{ background: 'var(--paper)', color: 'var(--paper-ink)', padding: 32, borderLeft: '1px solid var(--m-violet-2)' }}>
                <div className="eyebrow-paper" style={{ marginBottom: 16 }}>AI verdict</div>
                <p style={{ fontFamily: 'var(--font-display)', fontSize: 18, lineHeight: 1.35, margin: 0, fontStyle: 'italic' }}>
                  "Generic outdoor clothing store. Mid-range. No clear sustainability story."
                </p>
                <div style={{ marginTop: 12, fontFamily: 'var(--font-geist-mono)', fontSize: 10, opacity: 0.55 }}>— Gemini, GPT-4, Perplexity</div>
              </div>
            </div>
            {/* pillar bars */}
            <div style={{ padding: '20px 32px', display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 12 }}>
              {[
                { l: 'Discoverability', s: 72 },
                { l: 'Completeness',    s: 38 },
                { l: 'Consistency',     s: 61 },
                { l: 'Trust',           s: 45 },
                { l: 'Transaction',     s: 55 },
              ].map(p => {
                const c = p.s >= 70 ? 'var(--m-info)' : p.s >= 45 ? 'var(--m-warn)' : 'var(--m-bad)'
                return (
                  <div key={p.l} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                      <span style={{ fontSize: 10, color: 'var(--m-fg-3)' }}>{p.l}</span>
                      <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: c }}>{p.s}</span>
                    </div>
                    <div style={{ height: 3, background: 'rgba(255,255,255,0.06)', borderRadius: 100, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${p.s}%`, background: c, borderRadius: 100 }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ── Final CTA ───────────────────────────────────────────────── */}
      <section style={{ padding: '120px 0', borderTop: '1px solid var(--ink-line)' }}>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 32px', textAlign: 'center' }}>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(56px,8vw,128px)', lineHeight: 0.92, letterSpacing: '-0.025em', fontWeight: 400, margin: '0 0 48px', color: 'var(--m-fg)' }}>
            Show me<br />
            <em style={{ fontStyle: 'italic', color: 'var(--m-violet)' }}>the mirror.</em>
          </h2>
          <div style={{ display: 'inline-flex', flexDirection: 'column', gap: 14, alignItems: 'center' }}>
            <button
              onClick={onGetStarted}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 10, padding: '18px 32px', borderRadius: 100, background: 'var(--m-fg)', color: 'var(--ink)', border: 'none', fontSize: 16, fontWeight: 500, cursor: 'pointer', fontFamily: 'var(--font-geist)' }}
            >
              Audit my store — free <ArrowRight size={16} />
            </button>
            <span style={{ fontFamily: 'var(--font-geist)', fontSize: 12, color: 'var(--m-fg-3)' }}>~30 second scan · public data only · no signup</span>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer style={{ padding: '40px 0', borderTop: '1px solid var(--ink-line)' }}>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Logo />
          <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-fg-3)' }}>
            Kasparro Agentic Commerce Hackathon · Track 5
          </span>
          <button onClick={onGetStarted} style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-violet)', background: 'none', border: 'none', cursor: 'pointer' }}>
            Start free audit →
          </button>
        </div>
      </footer>
    </div>
  )
}

function Logo({ inverted = false }: { inverted?: boolean }) {
  const stroke = inverted ? 'var(--paper-ink)' : 'var(--m-fg)'
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
      <svg width={32} height={32} viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="14" stroke={stroke} strokeOpacity="0.25" strokeWidth="1" />
        <path d="M9 11 Q16 8 23 11 M9 21 Q16 24 23 21" stroke={stroke} strokeWidth="1.4" strokeLinecap="round" fill="none" />
        <line x1="16" y1="3" x2="16" y2="29" stroke="var(--m-violet)" strokeWidth="1" strokeDasharray="2 2" />
      </svg>
      <span style={{ fontFamily: 'var(--font-display)', fontSize: 20, letterSpacing: '-0.02em', color: stroke }}>
        Shop<em style={{ fontStyle: 'italic', color: 'var(--m-violet)' }}>Mirror</em>
      </span>
    </span>
  )
}
