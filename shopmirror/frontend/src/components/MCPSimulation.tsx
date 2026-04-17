import type { MCPResult } from '../api/client'

interface Props {
  results: MCPResult[]
}

type Classification = MCPResult['classification']

const BADGE_CLASSES: Record<Classification, string> = {
  ANSWERED: 'bg-green-500/20 text-green-400 border border-green-600',
  UNANSWERED: 'bg-red-500/20 text-red-400 border border-red-600',
  WRONG: 'bg-orange-500/20 text-orange-400 border border-orange-600',
}

const BADGE_LABELS: Record<Classification, string> = {
  ANSWERED: '✓ Answered',
  UNANSWERED: '✗ Cannot Answer',
  WRONG: '⚠ Wrong',
}

export default function MCPSimulation({ results }: Props) {
  return (
    <div className="bg-gray-900 rounded-2xl p-6">
      <h2 className="text-xl font-semibold text-white">MCP Shopping AI Simulation</h2>
      <p className="text-gray-400 text-sm mt-1">
        How an AI shopping assistant responds to customer questions about your store
      </p>

      <div className="mt-4 space-y-4">
        {results.map((result, i) => (
          <div key={i} className="bg-gray-800 rounded-xl p-4">
            {/* Header: badge + question */}
            <div className="flex items-start gap-3">
              <span
                className={`inline-block text-xs font-semibold px-2 py-0.5 rounded-full shrink-0 mt-0.5 ${BADGE_CLASSES[result.classification]}`}
              >
                {BADGE_LABELS[result.classification]}
              </span>
              <p className="text-white font-medium text-sm">{result.question}</p>
            </div>

            {/* Response */}
            <p className="mt-2 text-gray-400 text-sm italic leading-relaxed pl-0">
              {result.response}
            </p>

            {/* Ground truth mismatch */}
            {result.ground_truth_mismatch && (
              <div className="mt-2 bg-orange-500/10 border border-orange-700 rounded-lg px-3 py-2">
                <p className="text-orange-300 text-xs">
                  <span className="font-semibold">Mismatch:</span>{' '}
                  {result.ground_truth_mismatch}
                </p>
              </div>
            )}

            {/* Related findings */}
            {result.related_finding_ids.length > 0 && (
              <p className="mt-2 text-xs text-gray-500">
                Caused by: {result.related_finding_ids.join(', ')}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
