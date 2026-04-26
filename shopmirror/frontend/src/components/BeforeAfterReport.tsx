import type { BeforeAfterResponse, PillarScore, CopyPasteItem } from '../api/client'
import { useState } from 'react'

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

// Human-readable names for check IDs shown in "Checks Improved" / "Still Failing"
const CHECK_LABELS: Record<string, string> = {
  D1a: 'AI bot crawl access',
  D1b: 'Shopify Catalog eligibility',
  D2:  'Sitemap with product URLs',
  D3:  'llms.txt AI guidance file',
  D5:  'Translated product content',
  C1:  'Product taxonomy mapped',
  C2:  'Category noun in title',
  C3:  'Variant options named',
  C4:  'Product identifier (GTIN/SKU)',
  C5:  'Typed material metafields',
  C6:  'Image alt text coverage',
  Con1:'Schema price accuracy',
  Con2:'Schema availability accuracy',
  Con3:'SEO title consistency',
  T1:  'Return policy timeframe',
  T2:  'Shipping regions specified',
  T4:  'AI checkout schema (OfferShippingDetails)',
  A1:  'Inventory tracking enabled',
  A2:  'Oversell risk eliminated',
}

function pillarScore(p: PillarScore): number {
  return Math.round(p.score * 100)
}

function scoreColor(score: number): string {
  if (score >= 70) return 'text-blue-400'
  if (score >= 40) return 'text-amber-400'
  return 'text-red-400'
}

function calcOverall(pillars: Record<string, PillarScore>): number {
  const WEIGHTS: Record<string, number> = {
    Discoverability: 0.20,
    Completeness: 0.30,
    Consistency: 0.20,
    Trust_Policies: 0.15,
    Transaction: 0.15,
  }
  let total = 0
  for (const [pillar, w] of Object.entries(WEIGHTS)) {
    const p = pillars[pillar]
    if (p) total += p.score * w
  }
  return Math.round(total * 100)
}

function CopyPasteCard({ item }: { item: CopyPasteItem }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    await navigator.clipboard.writeText(item.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-white text-sm font-medium">{item.label}</span>
        <button
          onClick={handleCopy}
          className="text-xs text-blue-400 hover:text-blue-300 font-code border border-blue-500/30 px-2 py-0.5 rounded transition-colors"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="text-xs text-[#6B7DB3] font-code overflow-x-auto bg-[#0A0E27] rounded p-3 max-h-48 overflow-y-auto whitespace-pre-wrap">
        {item.content}
      </pre>
    </div>
  )
}

export default function BeforeAfterReport({ data, copyPasteItems }: Props) {
  const beforeScore = calcOverall(data.original_pillars)
  const afterScore = calcOverall(data.current_pillars)
  const delta = afterScore - beforeScore

  return (
    <div className="space-y-8">
      {/* Score delta hero */}
      <div style={{
        background: 'var(--paper)', color: 'var(--paper-ink)', borderRadius: 20, padding: '28px 32px',
        display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', gap: 24,
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'rgba(26,24,18,0.5)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Before</div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 80, lineHeight: 0.9, color: beforeScore < 50 ? 'var(--m-bad-p)' : 'var(--m-warn-p)' }}>{beforeScore}</div>
          <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, opacity: 0.4, marginTop: 6 }}>/100</div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="rgba(26,24,18,0.35)" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>
          <span style={{ fontFamily: 'var(--font-display)', fontSize: 22, color: delta >= 0 ? '#2d7a4f' : 'var(--m-bad-p)', fontWeight: 400 }}>
            {delta >= 0 ? '+' : ''}{delta}
          </span>
          <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, opacity: 0.4, letterSpacing: '0.08em' }}>pts</span>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'rgba(26,24,18,0.5)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>After</div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 80, lineHeight: 0.9, color: afterScore >= 70 ? '#2d7a4f' : afterScore >= 50 ? 'var(--m-warn-p)' : 'var(--m-bad-p)' }}>{afterScore}</div>
          <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, opacity: 0.4, marginTop: 6 }}>/100</div>
        </div>
      </div>

      {/* Pillar comparison */}
      <div>
        <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-3">Pillar Breakdown</p>
        <div className="space-y-3">
          {PILLAR_ORDER.map(pillar => {
            const before = data.original_pillars[pillar]
            const after = data.current_pillars[pillar]
            if (!before || !after) return null
            const bScore = pillarScore(before)
            const aScore = pillarScore(after)
            const improved = aScore > bScore
            return (
              <div key={pillar} className="card p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-white font-medium">{PILLAR_LABELS[pillar]}</span>
                  <div className="flex items-center gap-2 text-sm font-code">
                    <span className={scoreColor(bScore)}>{bScore}</span>
                    <span className="text-[#2D3A5E]">→</span>
                    <span className={`${scoreColor(aScore)} ${improved ? 'font-bold' : ''}`}>{aScore}</span>
                    {improved && <span className="text-xs text-blue-400">▲{aScore - bScore}</span>}
                  </div>
                </div>
                <div className="h-1.5 bg-[#0F1535] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${aScore >= 70 ? 'bg-blue-500' : aScore >= 40 ? 'bg-amber-500' : 'bg-red-500'}`}
                    style={{ width: `${aScore}%` }}
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
          <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-3">
            Fixed ({data.checks_improved.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {data.checks_improved.map(id => (
              <span key={id} className="flex items-center gap-1.5 text-sm text-green-400 bg-green-500/10 border border-green-500/20 rounded-lg px-3 py-1.5">
                <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
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
          <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-3">
            Still needs attention ({data.checks_unchanged.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {data.checks_unchanged.map(id => (
              <span key={id} className="flex items-center gap-1.5 text-sm text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-1.5">
                <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
          <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-3">
            Copy-Paste Package ({copyPasteItems.length})
          </p>
          <div className="space-y-3">
            {copyPasteItems.map((item, i) => <CopyPasteCard key={i} item={item} />)}
          </div>
        </div>
      )}
    </div>
  )
}
