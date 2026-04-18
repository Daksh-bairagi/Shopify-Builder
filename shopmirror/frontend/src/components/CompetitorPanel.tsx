import type { CompetitorResult } from '../api/client'

interface Props {
  results: CompetitorResult[]
}

export default function CompetitorPanel({ results }: Props) {
  const totalGaps = results.reduce((acc, r) => acc + r.gaps.length, 0)

  return (
    <div className="bg-[#141830] border border-[#1E2545] rounded-2xl p-6">

      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" strokeWidth="2">
          <line x1="18" y1="20" x2="18" y2="10"/>
          <line x1="12" y1="20" x2="12" y2="4"/>
          <line x1="6" y1="20" x2="6" y2="14"/>
          <line x1="2" y1="20" x2="22" y2="20"/>
        </svg>
        <span className="font-code text-lg font-semibold text-white">Competitor Analysis</span>
        {totalGaps > 0 && (
          <span className="ml-auto bg-red-500/15 text-red-400 border border-red-500/30 text-xs font-code px-2.5 py-1 rounded-full">
            {totalGaps} gaps found
          </span>
        )}
      </div>

      {/* Competitor cards */}
      <div className="space-y-4">
        {results.map((result, i) => (
          <div
            key={i}
            className="bg-[#0F1535] border border-[#1E2545] rounded-xl p-5 hover:border-blue-500/20 transition-all duration-200 cursor-pointer"
          >
            {/* Card header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />
                <span className="font-code text-sm font-semibold text-white">
                  {result.competitor.store_domain}
                </span>
              </div>
              {result.gaps.length > 0 ? (
                <span className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-code px-2.5 py-1 rounded-full">
                  {result.gaps.length} checks they pass, you fail
                </span>
              ) : (
                <span className="bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-code px-2.5 py-1 rounded-full">
                  No gaps found
                </span>
              )}
            </div>

            {/* Gap badges */}
            {result.gaps.length > 0 && (
              <div className="mb-4">
                <p className="font-code text-xs text-slate-500 uppercase tracking-wider mb-2">
                  Your gaps vs this competitor
                </p>
                <div className="flex flex-wrap gap-2">
                  {result.gaps.map(gap => (
                    <span
                      key={gap}
                      className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-code px-2.5 py-1.5 rounded-lg"
                    >
                      &#x2717; {gap}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Check results */}
            <div>
              <p className="font-code text-xs text-slate-500 uppercase tracking-wider mb-2">
                Their check results
              </p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(result.competitor.check_results).map(([checkId, passed]) =>
                  passed ? (
                    <span
                      key={checkId}
                      className="bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-code px-2 py-1 rounded"
                    >
                      &#x2713; {checkId}
                    </span>
                  ) : (
                    <span
                      key={checkId}
                      className="bg-[#1E2545] text-slate-500 text-xs font-code px-2 py-1 rounded"
                    >
                      &#x2717; {checkId}
                    </span>
                  )
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

    </div>
  )
}
