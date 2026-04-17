import type { CompetitorResult } from '../api/client'

interface Props {
  results: CompetitorResult[]
}

export default function CompetitorPanel({ results }: Props) {
  return (
    <div className="bg-gray-900 rounded-2xl p-6">
      <h2 className="text-xl font-semibold text-white">Competitor Analysis</h2>

      {results.map((result, i) => (
        <div key={i} className="bg-gray-800 rounded-xl p-4 mt-4">
          {/* Header */}
          <div className="flex items-center justify-between gap-3">
            <span className="text-white font-medium text-sm">
              {result.competitor.store_domain}
            </span>
            {result.gaps.length > 0 && (
              <span className="text-xs font-semibold bg-red-500/20 text-red-400 border border-red-700 px-2 py-0.5 rounded-full shrink-0">
                {result.gaps.length} gap{result.gaps.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Gap list */}
          {result.gaps.length > 0 && (
            <div className="mt-3">
              <p className="text-gray-400 text-xs mb-2">
                This competitor passes {result.gaps.length} check
                {result.gaps.length !== 1 ? 's' : ''} you fail:
              </p>
              <ul className="space-y-1">
                {result.gaps.map((gap) => (
                  <li key={gap} className="flex items-center gap-2 text-sm">
                    <span className="text-red-500 font-bold shrink-0">✗</span>
                    <span className="text-gray-300 font-mono text-xs">{gap}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Check results grid */}
          {Object.keys(result.competitor.check_results).length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {Object.entries(result.competitor.check_results).map(([checkId, passed]) => (
                <span
                  key={checkId}
                  className={`text-xs font-mono px-2 py-0.5 rounded ${
                    passed
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-gray-700 text-gray-500'
                  }`}
                >
                  {passed ? '✓' : '✗'} {checkId}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
