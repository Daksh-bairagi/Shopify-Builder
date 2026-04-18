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
      <div className="card p-6 text-center space-y-2">
        <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest">AI Readiness Score</p>
        <div className="flex items-center justify-center gap-6">
          <div>
            <div className="text-4xl font-bold text-red-400">{beforeScore}</div>
            <div className="text-xs text-[#4B5A8A] mt-1">Before</div>
          </div>
          <div className="flex flex-col items-center gap-1">
            <svg className="w-6 h-6 text-[#4B5A8A]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
            <span className={`text-sm font-bold ${delta >= 0 ? 'text-blue-400' : 'text-red-400'}`}>
              {delta >= 0 ? '+' : ''}{delta} pts
            </span>
          </div>
          <div>
            <div className="text-4xl font-bold text-blue-400">{afterScore}</div>
            <div className="text-xs text-[#4B5A8A] mt-1">After</div>
          </div>
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
            Checks Improved ({data.checks_improved.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {data.checks_improved.map(id => (
              <span key={id} className="flex items-center gap-1.5 text-sm text-blue-400 bg-blue-500/10 border border-blue-500/30 rounded px-3 py-1.5 font-code">
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                {id}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Checks unchanged */}
      {data.checks_unchanged.length > 0 && (
        <div>
          <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-3">
            Still Failing ({data.checks_unchanged.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {data.checks_unchanged.map(id => (
              <span key={id} className="flex items-center gap-1.5 text-sm text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded px-3 py-1.5 font-code">
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
                {id}
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
