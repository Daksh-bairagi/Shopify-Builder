import type { CompetitorResult } from '../api/client'

interface Props {
  results: CompetitorResult[]
}

// Plain-language explanation for each gap a competitor might have over you
const GAP_PLAIN: Record<string, { headline: string; impact: string }> = {
  D1a: {
    headline: 'AI bots can crawl their site',
    impact: 'When someone asks ChatGPT or Perplexity to find a product like yours, their store gets seen — yours might not.',
  },
  D1b: {
    headline: "Listed in Shopify's AI catalog",
    impact: "Their products show up inside Shopify's own AI-powered discovery tool.",
  },
  D2: {
    headline: 'Sitemap guides AI search engines',
    impact: 'Search engines and AI tools find and index their products faster.',
  },
  D3: {
    headline: 'AI guidance file (llms.txt) present',
    impact: 'AI shopping agents know exactly how to navigate and use their store.',
  },
  C1: {
    headline: 'Products are properly categorized',
    impact: "When someone asks 'find me a [type of product]', their items match. Yours might be getting skipped.",
  },
  C3: {
    headline: 'Options labeled (size, color, material…)',
    impact: "AI assistants can filter by size or color and recommend their specific variants. Yours aren't as easy to narrow down.",
  },
  C4: {
    headline: 'Products have barcodes / identifiers',
    impact: 'Google Shopping and AI product finders can match their items precisely by barcode.',
  },
  C6: {
    headline: 'Product images have text descriptions',
    impact: "AI tools can 'read' and describe their product photos — yours are invisible to AI.",
  },
  T1: {
    headline: 'Return window clearly stated',
    impact: "AI assistants can answer 'what's your return policy?' for them — building trust at the moment a buyer is deciding.",
  },
  T2: {
    headline: 'Shipping regions listed',
    impact: "AI agents can tell buyers where they ship. Yours can't answer that yet.",
  },
}

function GapItem({ gapId }: { gapId: string }) {
  const info = GAP_PLAIN[gapId]
  if (!info) {
    return (
      <div style={{
        padding: '10px 14px', borderRadius: 10,
        background: 'rgba(213,122,120,0.05)', border: '1px solid rgba(213,122,120,0.15)',
      }}>
        <span style={{ fontSize: 13, color: 'var(--m-fg-2)' }}>{gapId}</span>
      </div>
    )
  }
  return (
    <div style={{
      padding: '12px 16px', borderRadius: 10,
      background: 'rgba(213,122,120,0.05)', border: '1px solid rgba(213,122,120,0.15)',
    }}>
      <p style={{ margin: '0 0 4px', fontSize: 13, fontWeight: 500, color: 'var(--m-fg)' }}>
        {info.headline}
      </p>
      <p style={{ margin: 0, fontSize: 12, color: 'var(--m-fg-3)', lineHeight: 1.5 }}>
        {info.impact}
      </p>
    </div>
  )
}

export default function CompetitorPanel({ results }: Props) {
  if (results.length === 0) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, fontFamily: 'var(--font-geist)' }}>

      {/* Summary line */}
      <p style={{ margin: 0, fontSize: 13, color: 'var(--m-fg-3)', lineHeight: 1.5 }}>
        Here's where competing stores look stronger than you on a public-data AI-readiness benchmark.
        Each point is something a shopper's AI assistant may use to find and recommend products.{' '}
        <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-fg-4)' }}>
          Based on 7 publicly verifiable checks and up to 5 products per competitor.
        </span>
      </p>

      {results.map((result, i) => {
        const gaps = result.gaps ?? []
        const hasGaps = gaps.length > 0

        return (
          <div key={i} style={{
            background: 'var(--ink-2)', border: '1px solid var(--ink-line)',
            borderRadius: 16, padding: '20px 24px',
          }}>
            {/* Header */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              gap: 16, marginBottom: hasGaps ? 20 : 0,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{
                  width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                  background: 'rgba(180,160,214,0.08)', border: '1px solid rgba(180,160,214,0.2)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: 'var(--m-violet)',
                }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 9l1-5h16l1 5" />
                    <path d="M5 9v11h14V9" />
                    <path d="M9 22v-7h6v7" />
                  </svg>
                </span>
                <div>
                  <p style={{ margin: 0, fontSize: 14, fontWeight: 500, color: 'var(--m-fg)' }}>
                    {result.competitor.store_domain}
                  </p>
                  <p style={{ margin: 0, fontSize: 11, color: 'var(--m-fg-3)', fontFamily: 'var(--font-geist-mono)' }}>
                    Shopify store
                  </p>
                </div>
              </div>

              {hasGaps && (
                <div style={{
                  padding: '6px 14px', borderRadius: 100, textAlign: 'center',
                  background: 'rgba(213,122,120,0.08)', border: '1px solid rgba(213,122,120,0.2)',
                }}>
                  <p style={{ margin: 0, fontSize: 12, fontWeight: 500, color: 'var(--m-bad)' }}>
                    {gaps.length} gap{gaps.length !== 1 ? 's' : ''} vs. you
                  </p>
                </div>
              )}
            </div>

            {/* Plain-language gap list */}
            {hasGaps && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <p style={{ margin: '0 0 4px', fontSize: 11, fontFamily: 'var(--font-geist-mono)', color: 'var(--m-fg-3)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  Where they have an edge over you
                </p>
                {gaps.map(gapId => (
                  <GapItem key={gapId} gapId={gapId} />
                ))}
              </div>
            )}

            {!hasGaps && (
              <p style={{ margin: 0, fontSize: 13, color: 'var(--m-fg-3)', lineHeight: 1.5 }}>
                No gaps detected on these 7 checks — they're not ahead of you on any of the measured signals.
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}
