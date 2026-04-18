import { useEffect, useState } from 'react'
import { api, FixItem } from '../api/client'

interface Props {
  jobId: string
  onExecute: (approvedFixIds: string[]) => Promise<void>
}

const FIX_TYPE_LABELS: Record<string, string> = {
  improve_title: 'Improve Title',
  map_taxonomy: 'Map Taxonomy',
  classify_product_type: 'Set Product Type',
  fill_metafield: 'Fill Metafield',
  generate_alt_text: 'Generate Alt Text',
  create_metafield_definitions: 'Create Metafield Definitions',
  inject_schema_script: 'Inject Schema (Script Tag)',
  generate_schema_snippet: 'Generate Schema Snippet',
  suggest_policy_fix: 'Draft Policy',
}

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: 'text-red-400 border-red-500/30 bg-red-500/10',
  HIGH: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
  MEDIUM: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
}

export default function FixApproval({ jobId, onExecute }: Props) {
  const [fixes, setFixes] = useState<FixItem[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getFixPlan(jobId)
      .then(res => {
        setFixes(res.fixes)
        setSelected(new Set(res.fixes.map(f => f.fix_id)))
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [jobId])

  const toggle = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleExecute = async () => {
    if (selected.size === 0) return
    setExecuting(true)
    try {
      await onExecute([...selected])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Execution failed')
      setExecuting(false)
    }
  }

  if (loading) {
    return (
      <div className="card p-8 text-center">
        <div className="w-8 h-8 rounded-full border-2 border-[#1E2545] border-t-blue-500 animate-spin mx-auto" />
        <p className="text-[#6B7DB3] mt-4 text-sm">Loading fix plan...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-6 border-red-500/20">
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    )
  }

  const autofixable = fixes.filter(f => f.fix_type === 'auto')
  const copyPaste = fixes.filter(f => f.fix_type === 'copy_paste')

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-white font-semibold">{fixes.length} fixes planned</h3>
          <p className="text-[#6B7DB3] text-sm mt-0.5">{selected.size} selected for execution</p>
        </div>
        <button
          onClick={handleExecute}
          disabled={executing || selected.size === 0}
          className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium text-sm transition-colors flex items-center gap-2"
        >
          {executing ? (
            <>
              <div className="w-3.5 h-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              Executing...
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
              </svg>
              Run Agent
            </>
          )}
        </button>
      </div>

      {autofixable.length > 0 && (
        <div>
          <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-2">Auto-fixable ({autofixable.length})</p>
          <div className="space-y-2">
            {autofixable.map(fix => (
              <label key={fix.fix_id} className="flex items-start gap-3 card card-hover p-4 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selected.has(fix.fix_id)}
                  onChange={() => toggle(fix.fix_id)}
                  className="mt-0.5 accent-blue-500 shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white text-sm font-medium">{FIX_TYPE_LABELS[fix.type] ?? fix.type}</span>
                    <span className={`text-xs font-code px-1.5 py-0.5 rounded border ${SEVERITY_COLOR[fix.severity] ?? 'text-gray-400'}`}>
                      {fix.severity}
                    </span>
                    <span className="text-xs font-code text-[#4B5A8A] bg-[#0F1535] border border-[#1E2545] px-1.5 py-0.5 rounded">
                      {fix.check_id}
                    </span>
                  </div>
                  {fix.product_title && (
                    <p className="text-[#6B7DB3] text-xs mt-1 truncate">{fix.product_title}</p>
                  )}
                  <p className="text-[#4B5A8A] text-xs mt-0.5">{fix.reason}</p>
                  {fix.proposed_value && (
                    <p className="text-blue-400 text-xs mt-1 font-code truncate">→ {fix.proposed_value}</p>
                  )}
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {copyPaste.length > 0 && (
        <div>
          <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-2">Copy-Paste Required ({copyPaste.length})</p>
          <div className="space-y-2">
            {copyPaste.map(fix => (
              <div key={fix.fix_id} className="card p-4 border-amber-500/10">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-amber-400 text-sm font-medium">{FIX_TYPE_LABELS[fix.type] ?? fix.type}</span>
                  <span className="text-xs font-code text-[#4B5A8A]">{fix.check_id}</span>
                </div>
                <p className="text-[#4B5A8A] text-xs mt-1">{fix.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
