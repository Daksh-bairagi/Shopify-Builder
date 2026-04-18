import type { PerceptionDiff as PerceptionDiffType } from '../api/client'

interface Props {
  diff: PerceptionDiffType
}

export default function PerceptionDiff({ diff }: Props) {
  return (
    <div className="bg-[#141830] border border-[#1E2545] rounded-2xl p-6">

      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" strokeWidth="2">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
          <path d="M8 12h8M12 8v8"/>
        </svg>
        <span className="font-code text-lg font-semibold text-white">AI Perception Gap</span>
        <span className="text-xs text-slate-500 ml-auto">How AI actually sees your store vs your intent</span>
      </div>

      {/* Intent vs Perception grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">

        {/* Left — Intended Positioning */}
        <div className="bg-[#0F1535] border border-blue-500/20 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />
            <span className="font-code text-xs text-blue-400 uppercase tracking-wider">Your Intent</span>
          </div>
          <p className="text-sm text-slate-200 leading-relaxed">{diff.intended_positioning}</p>
        </div>

        {/* Right — AI Perception */}
        <div className="bg-[#0F1535] border border-red-500/20 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full bg-red-400 shrink-0" />
            <span className="font-code text-xs text-red-400 uppercase tracking-wider">AI Perception</span>
          </div>
          <p className="text-sm text-slate-200 leading-relaxed">{diff.ai_perception}</p>
        </div>
      </div>

      {/* Gap reasons */}
      <div>
        <p className="font-code text-xs text-slate-500 uppercase tracking-wider mb-3">Why the gap exists</p>
        <div className="space-y-2">
          {diff.gap_reasons.map((reason, i) => (
            <div key={i} className="flex items-start gap-3 bg-[#0F1535] rounded-lg px-4 py-2.5">
              <span className="shrink-0 mt-0.5">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" strokeWidth="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
              </span>
              <span className="text-sm text-slate-300">{reason}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}
