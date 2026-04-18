import type { AgentRun, FixResult } from '../api/client'

interface Props {
  agentRun: AgentRun
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

function fixLabel(fixId: string): string {
  for (const [prefix, label] of Object.entries(FIX_TYPE_LABELS)) {
    if (fixId.startsWith(prefix)) return label
  }
  return fixId
}

function FixRow({ result }: { result: FixResult }) {
  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${result.success ? 'border-blue-500/20 bg-blue-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
      <div className={`shrink-0 w-5 h-5 rounded-full flex items-center justify-center mt-0.5 ${result.success ? 'bg-blue-600' : 'bg-red-600'}`}>
        {result.success ? (
          <svg className="w-3 h-3 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        ) : (
          <svg className="w-3 h-3 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className={`text-sm font-medium ${result.success ? 'text-white' : 'text-red-300'}`}>
          {fixLabel(result.fix_id)}
        </p>
        {result.error && (
          <p className="text-xs text-red-400 mt-0.5 truncate">{result.error}</p>
        )}
        <p className="text-xs text-[#4B5A8A] font-code mt-0.5 truncate">{result.fix_id}</p>
      </div>
      <span className={`shrink-0 text-xs font-code ${result.success ? 'text-blue-400' : 'text-red-400'}`}>
        {result.success ? 'DONE' : 'FAIL'}
      </span>
    </div>
  )
}

export default function AgentActivity({ agentRun }: Props) {
  const all = [...agentRun.executed_fixes, ...agentRun.failed_fixes]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-400">{agentRun.fixes_applied}</div>
          <div className="text-xs text-[#4B5A8A]">fixes applied</div>
        </div>
        <div className="h-8 w-px bg-[#1E2545]" />
        <div className="text-center">
          <div className="text-2xl font-bold text-red-400">{agentRun.fixes_failed}</div>
          <div className="text-xs text-[#4B5A8A]">failed</div>
        </div>
        <div className="h-8 w-px bg-[#1E2545]" />
        <div className="text-center">
          <div className="text-2xl font-bold text-amber-400">{agentRun.manual_action_items.length}</div>
          <div className="text-xs text-[#4B5A8A]">manual actions</div>
        </div>
      </div>

      {all.length > 0 && (
        <div className="space-y-2">
          {all.map((r, i) => <FixRow key={i} result={r} />)}
        </div>
      )}

      {agentRun.manual_action_items.length > 0 && (
        <div>
          <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-2">Needs Manual Action</p>
          <div className="space-y-2">
            {agentRun.manual_action_items.map((item, i) => (
              <div key={i} className="card p-4 border-amber-500/20">
                <p className="text-amber-400 text-sm font-medium">{item.title}</p>
                <p className="text-[#6B7DB3] text-xs mt-1">{item.fix_instruction}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
