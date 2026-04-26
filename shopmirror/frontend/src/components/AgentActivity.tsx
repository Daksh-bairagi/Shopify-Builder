import type { AgentRun, FixResult } from '../api/client'

interface Props {
  agentRun: AgentRun
}

const FIX_TYPE_LABELS: Record<string, string> = {
  improve_title:               'Improved product title',
  map_taxonomy:                'Mapped product to Shopify taxonomy',
  classify_product_type:       'Set product type category',
  fill_metafield:              'Filled in product attributes',
  generate_alt_text:           'Generated image alt text',
  create_metafield_definitions:'Created structured attribute definitions',
  inject_schema_script:        'Injected AI-readable schema markup',
  generate_schema_snippet:     'Generated schema markup snippet',
  suggest_policy_fix:          'Drafted policy improvements',
}

function fixLabel(fixId: string): string {
  for (const [prefix, label] of Object.entries(FIX_TYPE_LABELS)) {
    if (fixId.startsWith(prefix)) return label
  }
  // Fall back to a readable form of the first segment
  const firstSegment = fixId.split('_').slice(0, 2).join(' ')
  return firstSegment.charAt(0).toUpperCase() + firstSegment.slice(1)
}

function productFromFixId(fixId: string): string | null {
  // fix_ids look like "improve_title_prod-12345_abc" — extract nothing user-facing
  return null
}

function FixRow({ result }: { result: FixResult }) {
  const label = fixLabel(result.fix_id)
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 12, padding: '12px 16px',
      borderRadius: 12, border: `1px solid ${result.success ? 'rgba(143,184,154,0.2)' : 'rgba(213,122,120,0.2)'}`,
      background: result.success ? 'rgba(143,184,154,0.05)' : 'rgba(213,122,120,0.05)',
    }}>
      {/* Status icon */}
      <div style={{
        width: 22, height: 22, borderRadius: '50%', flexShrink: 0, marginTop: 1,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: result.success ? 'var(--m-good)' : 'var(--m-bad)',
      }}>
        {result.success ? (
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        ) : (
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ margin: 0, fontSize: 13, fontWeight: 500, color: result.success ? 'var(--m-fg)' : 'var(--m-bad)' }}>
          {label}
        </p>
        {result.error && (
          <p style={{ margin: '4px 0 0', fontSize: 11, color: 'var(--m-bad)', fontFamily: 'var(--font-geist)' }}>
            {result.error}
          </p>
        )}
      </div>

      {/* Status badge */}
      <span style={{
        flexShrink: 0, fontFamily: 'var(--font-geist-mono)', fontSize: 10,
        letterSpacing: '0.08em', textTransform: 'uppercase', paddingTop: 3,
        color: result.success ? 'var(--m-good)' : 'var(--m-bad)',
      }}>
        {result.success ? 'Applied' : 'Skipped'}
      </span>
    </div>
  )
}

export default function AgentActivity({ agentRun }: Props) {
  const all = [...agentRun.executed_fixes, ...agentRun.failed_fixes]
  const appliedCount = agentRun.fixes_applied
  const failedCount  = agentRun.fixes_failed
  const manualCount  = agentRun.manual_action_items.length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>

      {/* Summary counters */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12,
        padding: '20px 24px', background: 'var(--ink-2)',
        border: '1px solid var(--ink-line)', borderRadius: 16,
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 42, lineHeight: 1, color: 'var(--m-good)' }}>{appliedCount}</div>
          <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)', marginTop: 6, letterSpacing: '0.1em', textTransform: 'uppercase' }}>fixes applied</div>
        </div>
        <div style={{ textAlign: 'center', borderLeft: '1px solid var(--ink-line)', borderRight: '1px solid var(--ink-line)' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 42, lineHeight: 1, color: manualCount > 0 ? 'var(--m-warn)' : 'var(--m-fg-3)' }}>{manualCount}</div>
          <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)', marginTop: 6, letterSpacing: '0.1em', textTransform: 'uppercase' }}>need your action</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 42, lineHeight: 1, color: failedCount > 0 ? 'var(--m-bad)' : 'var(--m-fg-3)' }}>{failedCount}</div>
          <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)', marginTop: 6, letterSpacing: '0.1em', textTransform: 'uppercase' }}>could not apply</div>
        </div>
      </div>

      {/* Fix results list */}
      {all.length > 0 && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 16 }}>What was changed</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {all.map((r, i) => <FixRow key={i} result={r} />)}
          </div>
        </div>
      )}

      {/* Manual action items */}
      {agentRun.manual_action_items.length > 0 && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 16 }}>Still needs your attention</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {agentRun.manual_action_items.map((item, i) => (
              <div key={i} style={{
                background: 'var(--ink-2)', border: '1px solid rgba(212,169,107,0.2)',
                borderRadius: 14, padding: '16px 20px',
              }}>
                <p style={{ margin: '0 0 6px', fontSize: 14, fontWeight: 500, color: 'var(--m-warn)' }}>{item.title}</p>
                <p style={{ margin: 0, fontSize: 13, color: 'var(--m-fg-2)', lineHeight: 1.5 }}>{item.fix_instruction}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
