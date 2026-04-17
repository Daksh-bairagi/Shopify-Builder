import type { PerceptionDiff as PerceptionDiffType } from '../api/client'

interface Props {
  diff: PerceptionDiffType
}

export default function PerceptionDiff({ diff }: Props) {
  return (
    <div className="bg-gray-900 rounded-2xl p-6">
      <h2 className="text-xl font-semibold text-white">AI Perception Gap</h2>

      <div className="grid grid-cols-2 gap-6 mt-4">
        {/* Intended positioning */}
        <div className="bg-blue-900/30 border border-blue-800 rounded-xl p-4">
          <div className="text-xs font-semibold text-blue-400 uppercase tracking-wide mb-3">
            How You Want to Be Seen
          </div>
          <p className="text-gray-200 text-sm leading-relaxed">
            {diff.intended_positioning}
          </p>
        </div>

        {/* AI perception */}
        <div className="bg-red-900/30 border border-red-800 rounded-xl p-4">
          <div className="text-xs font-semibold text-red-400 uppercase tracking-wide mb-3">
            How AI Actually Sees You
          </div>
          <p className="text-gray-200 text-sm leading-relaxed">
            {diff.ai_perception}
          </p>
        </div>
      </div>

      {/* Gap reasons */}
      {diff.gap_reasons.length > 0 && (
        <div className="mt-4">
          <p className="text-gray-400 text-sm mb-2">Why the gap exists:</p>
          <ul className="space-y-1.5">
            {diff.gap_reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                <span className="text-orange-400 mt-0.5 shrink-0">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
