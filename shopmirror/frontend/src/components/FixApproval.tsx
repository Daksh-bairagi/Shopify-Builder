import { useEffect, useState } from 'react'
import { api, FixItem } from '../api/client'

interface Props {
  jobId: string
  onExecute: (approvedFixIds: string[]) => Promise<void>
}

const FIX_TYPE_LABELS: Record<string, string> = {
  improve_title:               'Improve product title',
  map_taxonomy:                'Map to Shopify product taxonomy',
  classify_product_type:       'Set product category',
  fill_metafield:              'Fill in product attributes',
  generate_alt_text:           'Generate image descriptions',
  create_metafield_definitions:'Set up structured attribute fields',
  inject_schema_script:        'Add AI-readable schema markup',
  generate_schema_snippet:     'Create schema markup (copy-paste)',
  suggest_policy_fix:          'Draft policy improvements',
  repair_catalog_eligibility:  'Repair catalog eligibility manually',
  rename_variant_options:      'Rename variant options manually',
  supply_identifiers:          'Add product identifiers manually',
  repair_availability_schema:  'Repair availability schema manually',
  align_seo_metadata:          'Align SEO metadata manually',
}

const FIX_DESCRIPTIONS: Record<string, string> = {
  improve_title:               'Adds a clear product category noun so AI agents can classify what you sell.',
  map_taxonomy:                "Links your products to Shopify's standard taxonomy — required for Shopify Catalog and Google Shopping inclusion.",
  classify_product_type:       'Sets the product type field so AI agents can route your product to the right category queries.',
  fill_metafield:              'Extracts attributes like material, care instructions, and specs from your description and stores them in searchable fields.',
  generate_alt_text:           'Creates descriptive image alt text that AI image crawlers use to understand your products.',
  create_metafield_definitions:'Creates the typed field definitions that make your attributes machine-readable (not just plain text).',
  inject_schema_script:        'Injects structured data into your storefront so AI checkout agents can read shipping and return information.',
  generate_schema_snippet:     'Generates a JSON-LD block you can paste into your theme to make your store visible to AI shopping agents.',
  suggest_policy_fix:          'Drafts clearer policy language with explicit dates and regions that AI agents can extract and verify.',
  repair_catalog_eligibility:  'Some catalog blockers need a human fix, such as adding a real title or a priced variant before the product can qualify.',
  rename_variant_options:      'Variant labels like Option1 and Option2 need a human-readable rename in Shopify Admin.',
  supply_identifiers:          'GTINs, barcodes, and manufacturer identifiers must come from your catalog source of truth, not be invented automatically.',
  repair_availability_schema:  'Availability markup needs a storefront/schema implementation change rather than a blind content write.',
  align_seo_metadata:          'SEO titles and descriptions should be reviewed and updated manually so search-facing copy stays intentional.',
}

const PREVIEW_COUNT = 5

function ArrowRight({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function ChevronDown({ open }: { open: boolean }) {
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" style={{ transition: 'transform 200ms', transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}>
      <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function FixApproval({ jobId, onExecute }: Props) {
  const [fixes, setFixes] = useState<FixItem[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [expandedFixes, setExpandedFixes] = useState<Set<string>>(new Set())
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showAllAuto, setShowAllAuto] = useState(false)
  const [cpOpen, setCpOpen] = useState(false)
  const [manualOpen, setManualOpen] = useState(false)

  useEffect(() => {
    api.getFixPlan(jobId)
      .then(res => {
        setFixes(res.fixes)
        setSelected(new Set(res.fixes.filter(f => f.fix_type === 'auto').map(f => f.fix_id)))
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

  const toggleExpand = (id: string) => {
    setExpandedFixes(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    })
  }

  const handleExecute = async () => {
    const ids = [...selected]
    if (ids.length === 0) return
    setShowConfirm(true)
  }

  const confirmAndExecute = async () => {
    setShowConfirm(false)
    setExecuting(true)
    try {
      await onExecute([...selected])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong — please try again')
      setExecuting(false)
    }
  }

  if (loading) {
    return (
      <div style={{ background: 'var(--ink-2)', border: '1px solid var(--ink-line)', borderRadius: 16, padding: 40, textAlign: 'center' }}>
        <span style={{ display: 'inline-block', width: 20, height: 20, borderRadius: '50%', border: '2px solid var(--ink-line)', borderTopColor: 'var(--m-violet)', animation: 'spin 700ms linear infinite' }} />
        <p style={{ marginTop: 12, fontSize: 13, color: 'var(--m-fg-3)', fontFamily: 'var(--font-geist)' }}>Loading fix plan...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ background: 'rgba(213,122,120,0.05)', border: '1px solid rgba(213,122,120,0.2)', borderRadius: 16, padding: '16px 20px' }}>
        <p style={{ margin: 0, fontSize: 13, color: 'var(--m-bad)', fontFamily: 'var(--font-geist)' }}>{error}</p>
      </div>
    )
  }

  const autofixable = fixes.filter(f => f.fix_type === 'auto')
  const copyPaste   = fixes.filter(f => f.fix_type === 'copy_paste')
  const manualItems = fixes.filter(f => f.fix_type === 'manual' || f.fix_type === 'developer')

  const visibleAuto = showAllAuto ? autofixable : autofixable.slice(0, PREVIEW_COUNT)
  const hiddenAutoCount = autofixable.length - PREVIEW_COUNT

  const SectionHeader = ({
    label, badge, badgeStyle, open, onToggle, count,
  }: {
    label: string
    badge?: string
    badgeStyle?: React.CSSProperties
    open: boolean
    onToggle: () => void
    count: number
  }) => (
    <button
      onClick={onToggle}
      style={{
        display: 'flex', alignItems: 'center', gap: 10, width: '100%',
        background: 'none', border: 'none', cursor: 'pointer', padding: 0, marginBottom: open ? 14 : 0,
      }}
    >
      <div className="eyebrow">{label}</div>
      {badge && (
        <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, padding: '2px 8px', borderRadius: 100, ...badgeStyle }}>
          {badge}
        </span>
      )}
      <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)', marginLeft: 'auto', marginRight: 4 }}>
        {count} item{count !== 1 ? 's' : ''}
      </span>
      <span style={{ color: 'var(--m-fg-3)' }}>
        <ChevronDown open={open} />
      </span>
    </button>
  )

  const FixCard = ({ fix }: { fix: FixItem }) => (
    <label
      style={{
        display: 'flex', alignItems: 'flex-start', gap: 14,
        padding: '16px 18px', borderRadius: 14, cursor: 'pointer',
        background: selected.has(fix.fix_id) ? 'var(--ink-2)' : 'var(--ink-3)',
        border: selected.has(fix.fix_id) ? '1px solid rgba(180,160,214,0.25)' : '1px solid var(--ink-line)',
        transition: 'all 150ms ease',
      }}
    >
      <div
        onClick={() => toggle(fix.fix_id)}
        style={{
          width: 18, height: 18, borderRadius: 5, flexShrink: 0, marginTop: 1,
          border: selected.has(fix.fix_id) ? '1px solid var(--m-violet)' : '1px solid var(--ink-line-2)',
          background: selected.has(fix.fix_id) ? 'var(--m-violet)' : 'transparent',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'all 150ms ease',
        }}
      >
        {selected.has(fix.fix_id) && (
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        )}
      </div>
      <div style={{ flex: 1, minWidth: 0 }} onClick={() => toggle(fix.fix_id)}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--m-fg)' }}>
            {FIX_TYPE_LABELS[fix.type] ?? fix.type}
          </span>
          {fix.severity === 'CRITICAL' && (
            <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, padding: '2px 7px', borderRadius: 100, background: 'rgba(213,122,120,0.1)', color: 'var(--m-bad)', border: '1px solid rgba(213,122,120,0.25)' }}>
              Blocks AI inclusion
            </span>
          )}
          {fix.severity === 'HIGH' && (
            <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, padding: '2px 7px', borderRadius: 100, background: 'rgba(212,169,107,0.1)', color: 'var(--m-warn)', border: '1px solid rgba(212,169,107,0.25)' }}>
              Reduces ranking
            </span>
          )}
        </div>
        {fix.product_title && (
          <p style={{ margin: '0 0 3px', fontSize: 12, color: 'var(--m-fg-2)', fontStyle: 'italic' }}>"{fix.product_title}"</p>
        )}
        <p style={{ margin: 0, fontSize: 12, color: 'var(--m-fg-3)', lineHeight: 1.4 }}>
          {FIX_DESCRIPTIONS[fix.type] ?? fix.reason}
        </p>
        {(fix.proposed_value || fix.current_value) && fix.type !== 'map_taxonomy' && (
          <button
            onClick={e => { e.stopPropagation(); toggleExpand(fix.fix_id) }}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              marginTop: 6, padding: '3px 8px', borderRadius: 6,
              fontSize: 11, fontFamily: 'var(--font-geist-mono)',
              color: 'var(--m-fg-3)', background: 'transparent',
              border: '1px solid var(--ink-line)', cursor: 'pointer',
            }}
          >
            {expandedFixes.has(fix.fix_id) ? 'Hide' : 'What changes'}
          </button>
        )}
        {expandedFixes.has(fix.fix_id) && (
          <div style={{
            marginTop: 8, padding: '10px 12px', borderRadius: 8,
            background: 'rgba(0,0,0,0.15)', border: '1px solid var(--ink-line)',
            display: 'flex', flexDirection: 'column', gap: 6,
          }}>
            {fix.current_value && (
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <span style={{ fontSize: 10, fontFamily: 'var(--font-geist-mono)', color: 'var(--m-bad)', flexShrink: 0, marginTop: 1 }}>BEFORE</span>
                <span style={{ fontSize: 12, color: 'var(--m-fg-3)', fontFamily: 'var(--font-geist-mono)', wordBreak: 'break-all' }}>{fix.current_value}</span>
              </div>
            )}
            {fix.proposed_value && fix.type !== 'map_taxonomy' && (
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <span style={{ fontSize: 10, fontFamily: 'var(--font-geist-mono)', color: 'var(--m-good)', flexShrink: 0, marginTop: 1 }}>AFTER</span>
                <span style={{ fontSize: 12, color: 'var(--m-violet)', fontFamily: 'var(--font-geist-mono)', wordBreak: 'break-all' }}>{fix.proposed_value}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </label>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>

      {/* Confirmation modal */}
      {showConfirm && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 100,
          background: 'rgba(14,13,18,0.75)', backdropFilter: 'blur(6px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            background: 'var(--ink-2)', border: '1px solid var(--ink-line)',
            borderRadius: 20, padding: '32px 36px', maxWidth: 440, width: '90%',
            display: 'flex', flexDirection: 'column', gap: 20,
          }}>
            <div>
              <p style={{ margin: '0 0 6px', fontFamily: 'var(--font-display)', fontSize: 22, lineHeight: 1.2, color: 'var(--m-fg)', fontWeight: 400 }}>
                Apply {selected.size} fix{selected.size !== 1 ? 'es' : ''} to your store?
              </p>
              <p style={{ margin: 0, fontSize: 13, color: 'var(--m-fg-3)', lineHeight: 1.5 }}>
                These changes will be made to your live Shopify store. Every fix is logged and you can reverse any individual change after it is applied.
              </p>
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowConfirm(false)}
                style={{
                  padding: '10px 20px', borderRadius: 100, fontSize: 13, fontFamily: 'var(--font-geist)',
                  cursor: 'pointer', background: 'transparent',
                  border: '1px solid var(--ink-line)', color: 'var(--m-fg-2)',
                }}
              >
                Go back
              </button>
              <button
                onClick={confirmAndExecute}
                style={{
                  padding: '10px 20px', borderRadius: 100, fontSize: 13, fontWeight: 600,
                  fontFamily: 'var(--font-geist)', cursor: 'pointer',
                  background: 'var(--m-violet)', color: 'white', border: 'none',
                }}
              >
                Yes, apply fixes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header + CTA */}
      <div style={{
        background: 'var(--paper)', color: 'var(--paper-ink)',
        borderRadius: 20, padding: 32,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24,
        flexWrap: 'wrap',
      }}>
        <div>
          <div className="eyebrow-paper">Ready to apply</div>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 28, lineHeight: 1.1, margin: '8px 0 4px', fontWeight: 400, color: 'var(--paper-ink)' }}>
            {selected.size} auto-fix{selected.size !== 1 ? 'es' : ''} selected
          </h3>
          <p style={{ margin: 0, fontSize: 13, color: 'rgba(26,24,18,0.6)', fontFamily: 'var(--font-geist)' }}>
            Review the true auto-fixes below, then apply them in one click. Generated schema and policy content stays manual so the system never pretends it changed your storefront when it only drafted guidance.
          </p>
        </div>
        <button
          onClick={handleExecute}
          disabled={executing || selected.size === 0}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 10,
            padding: '14px 24px', borderRadius: 100, fontSize: 14, fontWeight: 600,
            fontFamily: 'var(--font-geist)', cursor: executing || selected.size === 0 ? 'not-allowed' : 'pointer',
            background: executing || selected.size === 0 ? 'rgba(26,24,18,0.2)' : 'var(--paper-ink)',
            color: 'var(--paper)', border: 'none', transition: 'background 200ms',
          }}
        >
          {executing ? (
            <>
              <span style={{ display: 'inline-block', width: 14, height: 14, borderRadius: '50%', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'var(--paper)', animation: 'spin 700ms linear infinite' }} />
              Applying fixes...
            </>
          ) : (
            <>Apply {selected.size} fix{selected.size !== 1 ? 'es' : ''} to my store <ArrowRight size={14} /></>
          )}
        </button>
      </div>

      {/* Auto-fixable section */}
      {autofixable.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <div className="eyebrow">Auto-fixable</div>
            <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, padding: '2px 8px', borderRadius: 100, background: 'rgba(143,184,154,0.12)', color: 'var(--m-good)', border: '1px solid rgba(143,184,154,0.25)' }}>
              {autofixable.filter(f => selected.has(f.fix_id)).length}/{autofixable.length} selected
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {visibleAuto.map(fix => <FixCard key={fix.fix_id} fix={fix} />)}
          </div>
          {hiddenAutoCount > 0 && (
            <button
              onClick={() => setShowAllAuto(v => !v)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                marginTop: 10, padding: '9px 16px', borderRadius: 10, width: '100%',
                justifyContent: 'center', cursor: 'pointer',
                background: 'var(--ink-3)', border: '1px solid var(--ink-line)',
                fontSize: 12, fontFamily: 'var(--font-geist)', color: 'var(--m-fg-2)',
                transition: 'background 150ms',
              }}
            >
              <ChevronDown open={showAllAuto} />
              {showAllAuto
                ? 'Show less'
                : `Show ${hiddenAutoCount} more fix${hiddenAutoCount !== 1 ? 'es' : ''}`}
            </button>
          )}
        </div>
      )}

      {/* Copy-paste section */}
      {copyPaste.length > 0 && (
        <div style={{
          borderRadius: 14,
          background: 'var(--ink-3)',
          border: cpOpen ? '1px solid rgba(212,169,107,0.2)' : '1px solid var(--ink-line)',
          overflow: 'hidden', transition: 'border-color 200ms',
        }}>
          <div style={{ padding: '14px 18px' }}>
            <SectionHeader
              label="Copy-paste required"
              badge="generated for you"
              badgeStyle={{ background: 'rgba(212,169,107,0.1)', color: 'var(--m-warn)', border: '1px solid rgba(212,169,107,0.25)' }}
              open={cpOpen}
              onToggle={() => setCpOpen(v => !v)}
              count={copyPaste.length}
            />
          </div>
          {cpOpen && (
            <div style={{ padding: '0 18px 18px', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <p style={{ margin: '0 0 12px', fontSize: 13, color: 'var(--m-fg-3)', fontFamily: 'var(--font-geist)', lineHeight: 1.5 }}>
                These improvements are generated for you, but they are not executed automatically. Preview the exact content below and copy it when you are ready to apply it yourself.
              </p>
              {copyPaste.map(fix => {
                return (
                  <div key={fix.fix_id} style={{
                    padding: '14px 18px', borderRadius: 14,
                    background: 'rgba(0,0,0,0.15)',
                    border: '1px solid rgba(212,169,107,0.12)',
                    transition: 'all 150ms ease',
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--m-warn)', marginBottom: 3 }}>
                      {FIX_TYPE_LABELS[fix.type] ?? fix.type}
                    </div>
                    <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--m-fg-3)', lineHeight: 1.4 }}>
                      {FIX_DESCRIPTIONS[fix.type] ?? fix.reason}
                    </p>
                    <pre style={{
                      margin: '0 0 10px',
                      padding: '12px 14px',
                      borderRadius: 10,
                      background: 'var(--ink-2)',
                      border: '1px solid var(--ink-line)',
                      color: 'var(--m-fg-2)',
                      fontSize: 11,
                      lineHeight: 1.5,
                      fontFamily: 'var(--font-geist-mono)',
                      whiteSpace: 'pre-wrap',
                      overflowX: 'auto',
                      maxHeight: 240,
                    }}>
                      {fix.proposed_value}
                    </pre>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <button
                        onClick={() => copyToClipboard(fix.proposed_value || fix.reason, fix.fix_id)}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: 5,
                          padding: '6px 12px', borderRadius: 8, fontSize: 12, fontFamily: 'var(--font-geist)',
                          fontWeight: 500, cursor: 'pointer',
                          background: copiedId === fix.fix_id ? 'rgba(143,184,154,0.15)' : 'transparent',
                          color: copiedId === fix.fix_id ? 'var(--m-good)' : 'var(--m-fg-2)',
                          border: copiedId === fix.fix_id ? '1px solid rgba(143,184,154,0.3)' : '1px solid var(--ink-line)',
                          transition: 'all 150ms ease',
                        }}
                      >
                        {copiedId === fix.fix_id ? 'Copied!' : 'Copy generated content'}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Manual / developer section */}
      {manualItems.length > 0 && (
        <div style={{
          borderRadius: 14,
          background: 'var(--ink-3)',
          border: '1px solid var(--ink-line)',
          overflow: 'hidden',
        }}>
          <div style={{ padding: '14px 18px' }}>
            <SectionHeader
              label="Needs manual setup"
              open={manualOpen}
              onToggle={() => setManualOpen(v => !v)}
              count={manualItems.length}
            />
          </div>
          {manualOpen && (
            <div style={{ padding: '0 18px 18px', display: 'flex', flexDirection: 'column', gap: 8 }}>
              {manualItems.map(fix => (
                <div key={fix.fix_id} style={{
                  padding: '14px 18px', borderRadius: 14,
                  background: 'rgba(0,0,0,0.15)', border: '1px solid var(--ink-line)',
                }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--m-fg-2)', marginBottom: 3 }}>
                    {FIX_TYPE_LABELS[fix.type] ?? fix.type}
                  </div>
                  <p style={{ margin: 0, fontSize: 12, color: 'var(--m-fg-3)', lineHeight: 1.4 }}>
                    {fix.reason}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
