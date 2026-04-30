import { useState } from 'react'
import type { CompetitorResult } from '../api/client'
import { api } from '../api/client'

interface Props {
  jobId: string
  onResults: (results: CompetitorResult[]) => void
}

function Dot({ color = 'var(--m-violet)' }: { color?: string }) {
  return (
    <span
      style={{ width: 6, height: 6, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }}
    />
  )
}

export default function CompetitorDiscovery({ jobId, onResults }: Props) {
  const [url1, setUrl1] = useState('')
  const [url2, setUrl2] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'auto' | 'manual'>('auto')

  function setModeSafely(next: 'auto' | 'manual') {
    if (next === 'auto') {
      // Switching to auto must clear stale manual URLs so they aren't silently submitted.
      setUrl1('')
      setUrl2('')
    }
    setMode(next)
    setError(null)
  }

  async function handleRun() {
    setLoading(true)
    setError(null)
    try {
      // Only forward URLs when in manual mode — auto mode delegates discovery to the backend.
      const urls = mode === 'manual'
        ? [url1.trim(), url2.trim()].filter(Boolean)
        : []
      const response = await api.findCompetitors(jobId, urls)
      const { results } = response
      if (results.length === 0) {
        setError(response.message || 'No competitors could be benchmarked. Try entering URLs manually.')
      } else {
        onResults(results)
      }
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : 'Competitor benchmarking hit a network or storefront-read issue. Try again or enter competitor URLs manually.',
      )
    } finally {
      setLoading(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '10px 14px', fontSize: 13, boxSizing: 'border-box',
    background: 'var(--ink-3)', border: '1px solid var(--ink-line)',
    borderRadius: 10, color: 'var(--m-fg)', fontFamily: 'var(--font-geist)',
    outline: 'none',
  }

  return (
    <div style={{ fontFamily: 'var(--font-geist)' }}>
      <div style={{
        background: 'var(--ink-2)', border: '1px solid var(--ink-line)',
        borderRadius: 20, padding: '32px 36px', marginBottom: 20, textAlign: 'center',
      }}>
        <div className="eyebrow" style={{ marginBottom: 10 }}>Benchmark</div>
        <h3 style={{ margin: '0 0 10px', fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 400, color: 'var(--m-fg)' }}>
          See how you compare to other stores
        </h3>
        <p style={{ margin: '0 0 24px', fontSize: 14, color: 'var(--m-fg-3)', lineHeight: 1.6, maxWidth: 480, marginLeft: 'auto', marginRight: 'auto' }}>
          We benchmark public storefront data from competitor stores against the same AI-readiness checks
          we ran on yours, then surface where they look stronger.
        </p>

        <div style={{ display: 'inline-flex', borderRadius: 10, border: '1px solid var(--ink-line)', overflow: 'hidden', marginBottom: 24 }}>
          {(['auto', 'manual'] as const).map(m => (
            <button
              key={m}
              onClick={() => setModeSafely(m)}
              style={{
                padding: '8px 20px', fontSize: 13, cursor: 'pointer',
                fontFamily: 'var(--font-geist)', border: 'none',
                background: mode === m ? 'var(--m-violet)' : 'transparent',
                color: mode === m ? 'white' : 'var(--m-fg-3)',
                transition: 'all 150ms',
              }}
            >
              {m === 'auto' ? 'Find for me' : 'I know my competitors'}
            </button>
          ))}
        </div>

        {mode === 'auto' ? (
          <p style={{ margin: '0 0 20px', fontSize: 13, color: 'var(--m-fg-3)', lineHeight: 1.5 }}>
            We'll automatically search for Shopify stores selling similar products and compare publicly visible signals.
            No admin access needed.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 400, margin: '0 auto 20px' }}>
            <p style={{ margin: '0 0 4px', fontSize: 13, color: 'var(--m-fg-3)', textAlign: 'left' }}>
              Paste 1–2 competitor store URLs (e.g.{' '}
              <code style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 12 }}>rival.myshopify.com</code>)
            </p>
            <input
              type="text"
              value={url1}
              onChange={e => setUrl1(e.target.value)}
              placeholder="Competitor 1 URL"
              style={inputStyle}
            />
            <input
              type="text"
              value={url2}
              onChange={e => setUrl2(e.target.value)}
              placeholder="Competitor 2 URL (optional)"
              style={inputStyle}
            />
          </div>
        )}

        {error && (
          <p style={{ margin: '0 0 16px', fontSize: 13, color: 'var(--m-bad)', lineHeight: 1.5 }}>
            {error}
          </p>
        )}

        <button
          onClick={handleRun}
          disabled={loading || (mode === 'manual' && !url1.trim() && !url2.trim())}
          style={{
            padding: '12px 28px', fontSize: 14, fontWeight: 500,
            cursor: loading || (mode === 'manual' && !url1.trim() && !url2.trim()) ? 'not-allowed' : 'pointer',
            fontFamily: 'var(--font-geist)', border: 'none', borderRadius: 12,
            background: loading || (mode === 'manual' && !url1.trim() && !url2.trim()) ? 'var(--ink-3)' : 'var(--m-violet)',
            color: loading || (mode === 'manual' && !url1.trim() && !url2.trim()) ? 'var(--m-fg-3)' : 'white',
            transition: 'all 150ms',
          }}
        >
          {loading
            ? 'Looking at competitor stores…'
            : mode === 'auto'
              ? 'Find competitors & compare'
              : 'Compare these stores'}
        </button>

        {loading && (
          <p style={{ marginTop: 14, fontSize: 12, color: 'var(--m-fg-3)', lineHeight: 1.5 }}>
            Fetching public storefront data and running a focused public-data benchmark — usually 10–30 seconds.
          </p>
        )}
      </div>

      <div style={{
        background: 'var(--ink-2)', border: '1px solid var(--ink-line)',
        borderRadius: 16, padding: '20px 24px',
      }}>
        <div className="eyebrow" style={{ marginBottom: 12 }}>What we compare</div>
        <p style={{ margin: '0 0 16px', fontSize: 12, color: 'var(--m-fg-3)', lineHeight: 1.5 }}>
          Public storefront benchmark across D1a, C1, C3, C4, C6, T1, and T2 on up to 5 products per competitor.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            'Can AI bots access and read their store?',
            'Are products properly categorized for AI shopping assistants?',
            'Do they clearly state their return policy?',
            'Do they list which countries they ship to?',
            'Do products have barcodes/identifiers AI product finders use?',
            'Do product images have alt text AI tools can read?',
          ].map(text => (
            <div key={text} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Dot />
              <span style={{ fontSize: 13, color: 'var(--m-fg-2)', lineHeight: 1.4 }}>{text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
