import type { MCPResult } from '../api/client'

interface Props {
  results: MCPResult[]
}

type Classification = MCPResult['classification']

const BORDER_CLASS: Record<Classification, string> = {
  ANSWERED: 'border-green-500/20',
  UNANSWERED: 'border-red-500/20',
  WRONG: 'border-orange-500/20',
}

const BADGE_CLASS: Record<Classification, string> = {
  ANSWERED: 'bg-green-500/15 text-green-400 border border-green-500/30',
  UNANSWERED: 'bg-red-500/15 text-red-400 border border-red-500/30',
  WRONG: 'bg-orange-500/15 text-orange-400 border border-orange-500/30',
}

const BADGE_LABEL: Record<Classification, string> = {
  ANSWERED: '✓ ANSWERED',
  UNANSWERED: '✗ NO ANSWER',
  WRONG: '⚠ WRONG',
}

export default function MCPSimulation({ results }: Props) {
  const answered = results.filter(r => r.classification === 'ANSWERED').length
  const unanswered = results.filter(r => r.classification === 'UNANSWERED').length
  const wrong = results.filter(r => r.classification === 'WRONG').length

  return (
    <div className="bg-[#141830] border border-[#1E2545] rounded-2xl p-6">

      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" strokeWidth="2">
            <polyline points="4 17 10 11 4 5"/>
            <line x1="12" y1="19" x2="20" y2="19"/>
          </svg>
          <span className="font-code text-lg font-semibold text-white">MCP Shopping AI Simulation</span>
        </div>
        <p className="text-xs text-slate-500">
          Simulating how an AI assistant responds using only your store's structured data
        </p>
      </div>

      {/* Summary row */}
      <div className="flex gap-3 mb-5">
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-3 py-2 text-center">
          <div className="font-code text-xl font-bold text-green-400">{answered}</div>
          <div className="text-xs text-slate-400">Answered</div>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 text-center">
          <div className="font-code text-xl font-bold text-red-400">{unanswered}</div>
          <div className="text-xs text-slate-400">Cannot Answer</div>
        </div>
        <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg px-3 py-2 text-center">
          <div className="font-code text-xl font-bold text-orange-400">{wrong}</div>
          <div className="text-xs text-slate-400">Wrong</div>
        </div>
      </div>

      {/* Result cards */}
      <div className="space-y-3">
        {results.map((result, i) => (
          <div
            key={i}
            className={`bg-[#0F1535] border rounded-xl p-4 ${BORDER_CLASS[result.classification]}`}
          >
            {/* Question + badge */}
            <div className="flex items-start gap-3 mb-2">
              <span className={`shrink-0 font-code text-xs px-2.5 py-1 rounded-md font-semibold ${BADGE_CLASS[result.classification]}`}>
                {BADGE_LABEL[result.classification]}
              </span>
              <p className="text-sm font-medium text-white flex-1">{result.question}</p>
            </div>

            {/* AI response */}
            <p className="text-sm text-slate-400 italic leading-relaxed">{result.response}</p>

            {/* Ground truth mismatch */}
            {result.ground_truth_mismatch && (
              <div className="mt-2 bg-orange-500/10 rounded-lg px-3 py-2">
                <span className="text-xs text-orange-300">{result.ground_truth_mismatch}</span>
              </div>
            )}

            {/* Related finding IDs */}
            {result.related_finding_ids.length > 0 && (
              <div className="mt-2 flex items-center gap-2 flex-wrap">
                <span className="text-xs text-slate-500 font-code">Linked findings:</span>
                {result.related_finding_ids.map(id => (
                  <span
                    key={id}
                    className="font-code text-xs bg-[#141830] border border-[#1E2545] text-slate-400 px-2 py-0.5 rounded"
                  >
                    {id}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

    </div>
  )
}
