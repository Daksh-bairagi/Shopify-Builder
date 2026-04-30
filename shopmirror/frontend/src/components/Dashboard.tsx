import { useEffect, useState } from 'react'
import { API_BASE_URL, type AuditReport, type ChannelStatus, type CompetitorResult } from '../api/client'
import FindingsTable from './FindingsTable'
import CompetitorPanel from './CompetitorPanel'
import CompetitorDiscovery from './CompetitorDiscovery'
import MCPSimulation from './MCPSimulation'
import PerceptionDiff from './PerceptionDiff'
import FixApproval from './FixApproval'
import AgentActivity from './AgentActivity'
import BeforeAfterReport from './BeforeAfterReport'
import ReadinessCertificate from './ReadinessCertificate'
import HeatmapGrid from './HeatmapGrid'
import { CHECK_LABELS } from '../utils/labels'
import { normalizeScore, overallFromPillars, scoreBand } from '../utils/score'

interface Props {
  report: AuditReport
  jobId: string
  adminToken: string | null
  error: string | null
  onReset: () => void
  onRestartWithUrl?: (prefilledUrl: string) => void
  onExecute: (approvedFixIds: string[]) => Promise<void>
  onReportRefresh?: () => void | Promise<void>
}

type Tab = 'overview' | 'perception' | 'findings' | 'products' | 'fixes'

function channelColor(status: ChannelStatus['status']) {
  if (status === 'READY')   return { c: 'var(--m-good)', bg: 'rgba(143,184,154,0.12)', border: 'rgba(143,184,154,0.25)' }
  if (status === 'PARTIAL') return { c: 'var(--m-warn)', bg: 'rgba(212,169,107,0.12)', border: 'rgba(212,169,107,0.25)' }
  // BLOCKED and NOT_READY share the failure styling.
  return                           { c: 'var(--m-bad)',  bg: 'rgba(213,122,120,0.12)', border: 'rgba(213,122,120,0.25)' }
}

const CHANNEL_STATUS_LABELS: Record<string, string> = {
  READY: 'Ready',
  PARTIAL: 'Partial',
  NOT_READY: 'Not ready',
  BLOCKED: 'Blocked',
}

const PILLAR_LABELS: Record<string, string> = {
  Discoverability: 'Discoverability',
  Completeness:    'Completeness',
  Consistency:     'Consistency',
  Trust_Policies:  'Trust & Policies',
  Transaction:     'Transaction',
}

// Derives a plain-English verdict from findings when perception_diff is unavailable
function deriveVerdict(report: AuditReport): string {
  const findings = report.findings ?? []
  const critCount = findings.filter(f => f.severity === 'CRITICAL').length
  const highCount  = findings.filter(f => f.severity === 'HIGH').length
  const score      = normalizeScore(report.ai_readiness_score)

  const readyChannels = Object.values(report.channel_compliance).filter(c => c.status === 'READY').length
  const totalChannels = Object.values(report.channel_compliance).length

  if (score >= 80) {
    return `Well-structured store with strong AI discoverability. ${readyChannels} of ${totalChannels} channels ready.`
  }
  if (critCount > 0) {
    return `Store has ${critCount} critical data gap${critCount > 1 ? 's' : ''} that block AI agents from classifying or recommending your products.`
  }
  if (highCount > 0) {
    return `Store is partially visible to AI agents but ${highCount} structural gap${highCount > 1 ? 's' : ''} reduce ranking and recommendation coverage.`
  }
  return `Store is discoverable but missing structured signals that AI agents use to match buyer queries to your products.`
}

const CHANNEL_LABELS: Record<string, string> = {
  shopify_catalog:  'Shopify Catalog',
  google_shopping:  'Google Shopping',
  meta_catalog:     'Meta Catalog',
  perplexity_web:   'Perplexity',
  chatgpt_shopping: 'ChatGPT',
}

// ── Logo ────────────────────────────────────────────────────────────────
function Logo() {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
      <svg width={26} height={26} viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="14" stroke="var(--m-fg)" strokeOpacity="0.25" strokeWidth="1" />
        <path d="M9 11 Q16 8 23 11 M9 21 Q16 24 23 21" stroke="var(--m-fg)" strokeWidth="1.4" strokeLinecap="round" fill="none" />
        <line x1="16" y1="3" x2="16" y2="29" stroke="var(--m-violet)" strokeWidth="1" strokeDasharray="2 2" />
      </svg>
      <span style={{ fontFamily: 'var(--font-display)', fontSize: 18, letterSpacing: '-0.02em', color: 'var(--m-fg)' }}>
        Shop<em style={{ fontStyle: 'italic', color: 'var(--m-violet)' }}>Mirror</em>
      </span>
    </span>
  )
}

// ── ArrowRight ──────────────────────────────────────────────────────────
function ArrowRight({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

// ── Status dot ──────────────────────────────────────────────────────────
function StatusDot({ color, size = 7 }: { color: string; size?: number }) {
  return <span style={{ display: 'inline-block', width: size, height: size, borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}`, flexShrink: 0 }} />
}

// ── Pillar bar ──────────────────────────────────────────────────────────
function PillarBar({ label, score }: { label: string; score: number }) {
  const s100 = normalizeScore(score)
  const c = s100 >= 70 ? 'var(--m-info)' : s100 >= 45 ? 'var(--m-warn)' : 'var(--m-bad)'
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span style={{ fontSize: 12, color: 'var(--m-fg)' }}>{label}</span>
        <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: c, fontWeight: 500 }}>{s100}<span style={{ color: 'var(--m-fg-3)', fontWeight: 400 }}>/100</span></span>
      </div>
      <div style={{ height: 3, background: 'rgba(255,255,255,0.06)', borderRadius: 100, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${s100}%`, background: c, borderRadius: 100, transition: 'width 1200ms cubic-bezier(.2,.8,.2,1)' }} />
      </div>
    </div>
  )
}

// ── Severity tag ────────────────────────────────────────────────────────
function SeverityTag({ severity }: { severity: string }) {
  const map: Record<string, string> = { CRITICAL: 'var(--m-bad)', HIGH: 'var(--m-warn)', MEDIUM: 'var(--m-info)' }
  const c = map[severity] || map.MEDIUM
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: 'var(--font-geist-mono)', fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: c, fontWeight: 500 }}>
      <span style={{ width: 5, height: 5, background: c, borderRadius: 1 }} />
      {severity.charAt(0) + severity.slice(1).toLowerCase()}
    </span>
  )
}

// ────────────────────────────────────────────────────────────────────────
const TABS: { id: Tab; label: string }[] = [
  { id: 'overview',   label: 'Overview' },
  { id: 'perception', label: 'Perception' },
  { id: 'findings',   label: 'Findings' },
  { id: 'products',   label: 'Products' },
  { id: 'fixes',      label: 'Fix Plan' },
]

export default function Dashboard({ report, jobId, adminToken, error, onReset, onRestartWithUrl, onExecute, onReportRefresh }: Props) {
  const [tab, setTab] = useState<Tab>('overview')
  const [competitorResults, setCompetitorResults] = useState<CompetitorResult[]>(report.competitor_comparison ?? [])
  // If the report changes (e.g. after an agent run or rollback refresh), pick up the new server-side competitor data.
  useEffect(() => {
    setCompetitorResults(report.competitor_comparison ?? [])
  }, [report])
  // Use the same overall calc as BeforeAfterReport so hero/after never diverge.
  const pillars = report.pillars ?? {}
  const score = Object.keys(pillars).length
    ? overallFromPillars(pillars)
    : normalizeScore(report.ai_readiness_score)
  const band  = scoreBand(score)
  const channels = Object.entries(report.channel_compliance ?? {}) as [string, ChannelStatus][]
  const findings = report.findings ?? []
  const critCount  = findings.filter(f => f.severity === 'CRITICAL').length
  const highCount  = findings.filter(f => f.severity === 'HIGH').length

  return (
    <div style={{ minHeight: '100vh', background: 'var(--ink)', color: 'var(--m-fg)', fontFamily: 'var(--font-geist)' }}>

      {/* ── Header ────────────────────────────────────────────────── */}
      <header style={{
        position: 'sticky', top: 0, zIndex: 30,
        background: 'rgba(14,13,18,0.88)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid var(--ink-line)',
      }}>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
              <Logo />
              <span style={{ width: 1, height: 20, background: 'var(--ink-line)' }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--m-fg)' }}>{report.store_name}</div>
                <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)' }}>{report.store_domain}</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderRadius: 100, border: `1px solid ${band.c}`, fontFamily: 'var(--font-geist-mono)', fontSize: 11, letterSpacing: '0.04em', textTransform: 'uppercase', color: band.c }}>
                <StatusDot color={band.c} size={6} />
                {score} · {band.label}
              </div>
              <button
                onClick={onReset}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 100, border: '1px solid var(--ink-line)', background: 'none', color: 'var(--m-fg-2)', fontSize: 12, cursor: 'pointer', transition: 'border-color 200ms, color 200ms' }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--m-fg-3)' }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--ink-line)' }}
              >
                <span style={{ transform: 'scaleX(-1)', display: 'inline-block' }}><ArrowRight /></span> New audit
              </button>
            </div>
          </div>

          {/* Tab bar */}
          <nav style={{ display: 'flex', gap: 2, marginBottom: -1 }}>
            {TABS.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)} style={{
                padding: '12px 18px', fontSize: 13, fontWeight: 500, background: 'none', border: 'none',
                color: tab === t.id ? 'var(--m-fg)' : 'var(--m-fg-3)',
                borderBottom: tab === t.id ? '1.5px solid var(--m-violet)' : '1.5px solid transparent',
                cursor: 'pointer', transition: 'all 200ms ease',
                display: 'inline-flex', alignItems: 'center', gap: 6,
              }}>
                {t.label}
                {t.id === 'findings' && findings.length > 0 && (
                  <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, padding: '2px 6px', borderRadius: 100, background: tab === t.id ? 'rgba(180,160,214,0.15)' : 'var(--ink-3)', color: tab === t.id ? 'var(--m-violet)' : 'var(--m-fg-3)' }}>
                    {findings.length}
                  </span>
                )}
                {t.id === 'fixes' && adminToken && (
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--m-warn)', display: 'inline-block', animation: 'pulse 2s infinite' }} />
                )}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* ── Tab content ───────────────────────────────────────────── */}
      <main style={{ maxWidth: 1280, margin: '0 auto', padding: '48px 32px 80px' }}>

        {error && (
          <div style={{
            marginBottom: 24,
            padding: '14px 18px',
            borderRadius: 14,
            background: 'rgba(213,122,120,0.08)',
            border: '1px solid rgba(213,122,120,0.25)',
            color: 'var(--m-bad)',
            fontSize: 13,
            lineHeight: 1.5,
          }}>
            {error}
          </div>
        )}

        {tab === 'overview' && <OverviewTab report={report} band={band} channels={channels} critCount={critCount} highCount={highCount} jobId={jobId} adminToken={adminToken} />}
        {tab === 'perception' && <PerceptionTab report={report} onReset={onReset} jobId={jobId} competitorResults={competitorResults} onCompetitorResults={setCompetitorResults} />}
        {tab === 'findings' && <FindingsTab report={report} critCount={critCount} highCount={highCount} />}
        {tab === 'products' && <ProductsTab report={report} onRestart={() => onRestartWithUrl ? onRestartWithUrl(report.store_domain) : onReset()} />}
        {tab === 'fixes' && <FixesTab report={report} jobId={jobId} adminToken={adminToken} onReset={() => onRestartWithUrl ? onRestartWithUrl(report.store_domain) : onReset()} onExecute={onExecute} onReportRefresh={onReportRefresh} />}

      </main>

      <footer style={{ borderTop: '1px solid var(--ink-line)', padding: '20px 0', textAlign: 'center' }}>
        <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-fg-4)' }}>
          ShopMirror — AI Readiness for Shopify stores
        </span>
      </footer>
    </div>
  )
}

// ── OVERVIEW TAB ────────────────────────────────────────────────────────
function OverviewTab({ report, band, channels, critCount, highCount, jobId, adminToken }: {
  report: AuditReport
  band: ReturnType<typeof scoreBand>
  channels: [string, ChannelStatus][]
  critCount: number
  highCount: number
  jobId: string
  adminToken: string | null
}) {
  const pillars = report.pillars ?? {}
  const score = Object.keys(pillars).length
    ? overallFromPillars(pillars)
    : normalizeScore(report.ai_readiness_score)
  const findings = report.findings ?? []
  const readyCount = channels.filter(([, ch]) => ch.status === 'READY').length
  const handleAssetDownload = async (path: string, filename: string) => {
    // Use header auth + Blob download so the admin token never leaks into
    // browser history, referrer headers, or web logs the way a query string would.
    const url = `${API_BASE_URL}${path}`
    try {
      const headers: Record<string, string> = {}
      if (adminToken) headers['X-Admin-Token'] = adminToken
      const res = await fetch(url, { headers })
      if (!res.ok) throw new Error(`Asset download failed: ${res.status}`)
      const blob = await res.blob()
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      // Give the browser a moment to start the download before revoking.
      setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
    } catch {
      // Graceful degradation only: if fetch is blocked we still open a tab so the user gets the file.
      const tokenSuffix = adminToken
        ? `${path.includes('?') ? '&' : '?'}admin_token=${encodeURIComponent(adminToken)}`
        : ''
      window.open(`${url}${tokenSuffix}`, '_blank', 'noopener,noreferrer')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 56 }}>

      {/* Hero — split score card */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', borderRadius: 24, overflow: 'hidden', border: '1px solid var(--ink-line)', position: 'relative', minHeight: 320 }}>
        {/* Ink left — big score */}
        <div style={{ background: 'var(--ink-2)', padding: 40, position: 'relative', minWidth: 0, overflow: 'hidden' }}>
          <div className="eyebrow">AI Readiness Score</div>
          <div style={{ marginTop: 20, display: 'flex', alignItems: 'flex-start', gap: 24, flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', display: 'inline-block', flexShrink: 0 }} className="write-in">
              <span style={{ fontFamily: 'var(--font-display)', fontSize: 140, lineHeight: 0.85, letterSpacing: '-0.05em', color: 'var(--m-fg)' }}>{score}</span>
              <span style={{ position: 'absolute', right: -24, top: 12, fontFamily: 'var(--font-geist-mono)', fontSize: 18, color: 'var(--m-fg-3)', opacity: 0.5 }}>/100</span>
            </div>
            <div style={{ paddingTop: 8, flex: '1 1 160px', minWidth: 0 }}>
              <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: band.c, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8 }}>{band.label}</div>
              <div style={{ fontSize: 13, color: 'var(--m-fg-2)', lineHeight: 1.5 }}>
                The mirror reads your store. Analyzed <strong style={{ color: 'var(--m-fg)', fontWeight: 500 }}>{report.total_products}</strong> products across 5 pillars and 5 AI channels.
              </div>
            </div>
          </div>
          {/* Pillar bars */}
          <div style={{ marginTop: 32, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            {Object.entries(pillars).map(([name, pillar]) => (
              <PillarBar key={name} label={PILLAR_LABELS[name] ?? name} score={pillar.score} />
            ))}
          </div>
        </div>

        {/* Paper right — verdict */}
        <div style={{ background: 'var(--paper)', color: 'var(--paper-ink)', padding: 48, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', position: 'relative', borderLeft: '1px solid var(--m-violet-2)' }}>
          <div>
            <div className="eyebrow-paper">How AI sees your store</div>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 28, lineHeight: 1.2, letterSpacing: '-0.015em', margin: '16px 0 0', fontStyle: 'italic' }}>
              "{report.perception_diff?.ai_perception ?? deriveVerdict(report)}"
            </h2>
            <div style={{ marginTop: 16, fontFamily: 'var(--font-geist-mono)', fontSize: 10, opacity: 0.5, letterSpacing: '0.06em' }}>
              — synthesized from structural audit · {report.total_products} products analysed
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 20, paddingTop: 24, borderTop: '1px solid var(--paper-line)', marginTop: 24 }}>
            {[
              { v: findings.length,                   l: 'issues' },
              { v: critCount + highCount,             l: 'urgent issues' },
              { v: channels.filter(([,c]) => c.status === 'READY').length + '/' + channels.length, l: 'channels ready' },
            ].map(s => (
              <div key={s.l}>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 36, lineHeight: 1, color: 'var(--paper-ink)' }}>{s.v}</div>
                <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, opacity: 0.5, marginTop: 4, letterSpacing: '0.1em', textTransform: 'uppercase' }}>{s.l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Channel compliance */}
      <section>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 20 }}>
          <div>
            <div className="eyebrow">Multi-channel compliance</div>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 32, lineHeight: 1.05, fontWeight: 400, margin: '8px 0 0', color: 'var(--m-fg)' }}>Where can AI find you?</h3>
          </div>
          <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-fg-3)' }}>{readyCount}/{channels.length} ready</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 12 }}>
          {channels.map(([key, ch]) => {
            const cfg = channelColor(ch.status)
            return (
              <div key={key} style={{ border: `1px solid ${cfg.border}`, borderRadius: 14, padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8, background: cfg.bg }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: 'var(--m-fg)', fontWeight: 500 }}>{CHANNEL_LABELS[key] ?? key}</span>
                  <StatusDot color={cfg.c} size={6} />
                </div>
                <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, letterSpacing: '0.06em', color: cfg.c, fontWeight: 500 }}>{CHANNEL_STATUS_LABELS[ch.status] ?? ch.status}</span>
                <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)' }}>
                  {(ch.blocking_check_ids?.length ?? 0) === 0
                    ? 'all clear'
                    : `${ch.blocking_check_ids.length} issue${ch.blocking_check_ids.length > 1 ? 's' : ''} blocking`}
                </span>
              </div>
            )
          })}
        </div>
      </section>

      {/* Top findings preview */}
      {findings.length > 0 && (
        <section>
          <div className="eyebrow" style={{ marginBottom: 16 }}>Top Issues</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {findings.slice(0, 4).map(f => (
              <div key={f.id} style={{ background: 'var(--ink-2)', border: '1px solid var(--ink-line)', borderRadius: 14, padding: '16px 18px', display: 'flex', gap: 14, alignItems: 'flex-start' }}>
                <SeverityTag severity={f.severity} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, color: 'var(--m-fg)', marginBottom: 4, lineHeight: 1.4 }}>{f.title}</div>
                  <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)' }}>{f.pillar}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Channel readiness deep audit */}
      <ChannelReadinessAudit report={report} />

      {(report.feed_summaries || report.llms_txt_preview) && (
        <section>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 20, gap: 16, flexWrap: 'wrap' }}>
            <div>
              <div className="eyebrow">Generated Assets</div>
              <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 32, lineHeight: 1.05, fontWeight: 400, margin: '8px 0 0', color: 'var(--m-fg)' }}>Scope we can stand behind.</h3>
            </div>
            <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-fg-3)' }}>
              Core flow: audit, explain, verify, and auto-fix supported fields
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 16 }}>
            <div style={{ background: 'var(--ink-2)', border: '1px solid var(--ink-line)', borderRadius: 18, padding: 24 }}>
              <div className="eyebrow" style={{ marginBottom: 12 }}>Ready To Export</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 16 }}>
                {[
                  { label: 'llms.txt', path: `/jobs/${jobId}/llms-txt`, filename: `llms-${jobId.slice(0,8)}.txt` },
                  { label: 'Schema Package', path: `/jobs/${jobId}/schema-package`, filename: `schema-${jobId.slice(0,8)}.json` },
                  { label: 'Google Feed', path: `/jobs/${jobId}/feeds/google`, filename: `google-feed-${jobId.slice(0,8)}.xml` },
                  { label: 'Perplexity Feed', path: `/jobs/${jobId}/feeds/perplexity`, filename: `perplexity-feed-${jobId.slice(0,8)}.xml` },
                  { label: 'ChatGPT Feed', path: `/jobs/${jobId}/feeds/chatgpt`, filename: `chatgpt-feed-${jobId.slice(0,8)}.jsonl` },
                ].map(asset => (
                  <button
                    key={asset.label}
                    onClick={() => handleAssetDownload(asset.path, asset.filename)}
                    type="button"
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 14px',
                      borderRadius: 999, border: '1px solid var(--ink-line)', color: 'var(--m-fg)',
                      background: 'transparent', cursor: 'pointer', fontFamily: 'var(--font-geist)',
                      fontSize: 12,
                    }}
                  >
                    {asset.label} <ArrowRight size={11} />
                  </button>
                ))}
              </div>
              {report.feed_summaries && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10 }}>
                  {Object.entries(report.feed_summaries).map(([name, summary]) => (
                    <div key={name} style={{ borderRadius: 12, background: 'var(--ink-3)', border: '1px solid var(--ink-line)', padding: '12px 14px' }}>
                      <div style={{ fontSize: 12, color: 'var(--m-fg)', marginBottom: 4, textTransform: 'capitalize' }}>{name}</div>
                      <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)', lineHeight: 1.5 }}>
                        {JSON.stringify(summary)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div style={{ background: 'var(--ink-2)', border: '1px solid var(--ink-line)', borderRadius: 18, padding: 24 }}>
              <div className="eyebrow" style={{ marginBottom: 12 }}>Product Scope</div>
              <p style={{ margin: '0 0 12px', fontSize: 13, color: 'var(--m-fg-2)', lineHeight: 1.55 }}>
                Autonomous fixes are deliberately limited to catalog fields we can write, verify live, and roll back safely.
                Generated assets and lab workflows stay separate from that core promise.
              </p>
              {report.llms_txt_preview && (
                <pre style={{
                  margin: 0, whiteSpace: 'pre-wrap', fontSize: 11, lineHeight: 1.5,
                  color: 'var(--m-fg-3)', fontFamily: 'var(--font-geist-mono)',
                  background: 'var(--ink-3)', border: '1px solid var(--ink-line)',
                  borderRadius: 12, padding: 14, maxHeight: 220, overflow: 'auto',
                }}>
                  {report.llms_txt_preview}
                </pre>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}

// ── CHANNEL READINESS AUDIT (surfaces bot_access, identifier_audit, golden_record, trust_signals)
function ChannelReadinessAudit({ report }: { report: AuditReport }) {
  const bot = report.bot_access as Record<string, any> | undefined
  const ident = report.identifier_audit as Record<string, any> | undefined
  const golden = report.golden_record as Record<string, any> | undefined
  const trust = report.trust_signals as Record<string, any> | undefined

  if (!bot && !ident && !golden && !trust) return null

  const tile = (title: string, value: string | number, subtitle: string, color: string) => (
    <div style={{
      background: 'var(--ink-2)', border: '1px solid var(--ink-line)',
      borderRadius: 14, padding: '18px 20px',
    }}>
      <div className="eyebrow" style={{ marginBottom: 8 }}>{title}</div>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: 32, lineHeight: 1, color }}>{value}</div>
      <div style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)', marginTop: 8, letterSpacing: '0.06em' }}>
        {subtitle}
      </div>
    </div>
  )

  // Defensive accessors — different deployments may shape these differently.
  const botBlocked = Array.isArray(bot?.blocked_bots) ? bot.blocked_bots.length : (bot?.blocked_count ?? 0)
  const botAllowed = Array.isArray(bot?.allowed_bots) ? bot.allowed_bots.length : (bot?.allowed_count ?? 0)
  const identCoverage = ident?.coverage_pct ?? ident?.coverage ?? null
  const identMissing = ident?.missing_count ?? (Array.isArray(ident?.missing) ? ident.missing.length : null)
  const goldenScore = golden?.score ?? golden?.overall ?? null
  const trustScore = trust?.score ?? trust?.overall ?? null

  const fmtPct = (v: number | null) =>
    v == null ? '—' : `${Math.round(v <= 1 ? v * 100 : v)}%`
  const fmtScore = (v: number | null) =>
    v == null ? '—' : String(Math.round(v <= 1 ? v * 100 : v))

  // Color a 0–1 (or 0–100) metric, returning a neutral grey when null/undefined
  // so the dashboard doesn't pretend a missing measurement is a failure.
  const metricColor = (v: number | null | undefined): string => {
    if (v == null || Number.isNaN(v)) return 'var(--m-fg-3)'
    const pct = v <= 1 ? v * 100 : v
    if (pct >= 70) return 'var(--m-good)'
    if (pct >= 40) return 'var(--m-warn)'
    return 'var(--m-bad)'
  }

  return (
    <section>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <div className="eyebrow">Deeper audit</div>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 32, lineHeight: 1.05, fontWeight: 400, margin: '8px 0 0', color: 'var(--m-fg)' }}>
            What's under the hood.
          </h3>
        </div>
        <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-fg-3)' }}>
          Signals AI shopping platforms weight separately from the headline checks
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12 }}>
        {bot && tile(
          'Bot access',
          botBlocked === 0 ? 'OK' : `${botBlocked} blocked`,
          `${botAllowed} AI bots allowed in robots.txt`,
          botBlocked === 0 ? 'var(--m-good)' : 'var(--m-warn)',
        )}
        {ident && tile(
          'Identifiers',
          fmtPct(identCoverage),
          identMissing != null ? `${identMissing} products without GTIN/MPN` : 'GTIN / barcode / MPN coverage',
          metricColor(identCoverage),
        )}
        {golden && tile(
          'Golden record',
          fmtScore(goldenScore),
          'Catalog data integrity score',
          metricColor(goldenScore),
        )}
        {trust && tile(
          'Trust signals',
          fmtScore(trustScore),
          'Policy clarity, shipping, returns',
          metricColor(trustScore),
        )}
      </div>
    </section>
  )
}

// ── PERCEPTION TAB ──────────────────────────────────────────────────────
function PerceptionTab({ report, onReset, jobId, competitorResults, onCompetitorResults }: { report: AuditReport; onReset: () => void; jobId: string; competitorResults: CompetitorResult[]; onCompetitorResults: (r: CompetitorResult[]) => void }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 56 }}>

      {/* Perception diff */}
      <section>
        <div className="eyebrow">Intent vs. Reality</div>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(32px,4vw,56px)', lineHeight: 1.0, letterSpacing: '-0.02em', fontWeight: 400, margin: '12px 0 32px', color: 'var(--m-fg)' }}>
          Intent <em style={{ fontStyle: 'italic', color: 'var(--m-violet)' }}>vs.</em> Mirror
        </h2>
        {report.perception_diff ? (
          <PerceptionDiff diff={report.perception_diff} />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', borderRadius: 18, overflow: 'hidden', border: '1px solid var(--ink-line)' }}>
            <div style={{ background: 'var(--ink-2)', padding: 32 }}>
              <div className="eyebrow" style={{ marginBottom: 16 }}>What you intend</div>
              <p style={{ fontFamily: 'var(--font-display)', fontSize: 20, lineHeight: 1.35, color: 'var(--m-fg)', margin: 0 }}>
                Your brand story, positioning, and unique value proposition.
              </p>
            </div>
            <div style={{ background: 'var(--paper)', color: 'var(--paper-ink)', padding: 32, borderLeft: '1px solid var(--m-violet-2)' }}>
              <div className="eyebrow-paper" style={{ marginBottom: 16 }}>What AI extracts</div>
              <p style={{ fontFamily: 'var(--font-display)', fontSize: 20, lineHeight: 1.35, margin: 0, fontStyle: 'italic' }}>
                Your store's AI-readable signals are incomplete. Category, taxonomy, and structured attributes need work.
              </p>
            </div>
          </div>
        )}
      </section>

      {/* Per-product perception drift */}
      {report.product_perceptions && report.product_perceptions.length > 0 && (
        <section>
          <div className="eyebrow" style={{ marginBottom: 12 }}>Per-product drift</div>
          <p style={{ margin: '0 0 16px', fontSize: 13, color: 'var(--m-fg-3)', lineHeight: 1.55 }}>
            How AI extraction reshapes each product's positioning. Cells flagged "cannot determine" are the data
            gaps that pull the overall perception away from your intent.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {report.product_perceptions.slice(0, 5).map((pp, i) => (
              <div key={i} style={{
                background: 'var(--ink-2)', border: '1px solid var(--ink-line)',
                borderRadius: 14, padding: '16px 20px',
              }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 10 }}>
                  <div>
                    <div className="eyebrow" style={{ marginBottom: 6, color: 'var(--m-good)' }}>Intended</div>
                    <p style={{ margin: 0, fontSize: 13, color: 'var(--m-fg-2)', lineHeight: 1.5 }}>{pp.intended || '—'}</p>
                  </div>
                  <div>
                    <div className="eyebrow" style={{ marginBottom: 6, color: 'var(--m-bad)' }}>AI extracted</div>
                    <p style={{ margin: 0, fontSize: 13, color: 'var(--m-fg-2)', lineHeight: 1.5, fontStyle: 'italic' }}>{pp.ai_extracted || '—'}</p>
                  </div>
                </div>
                {pp.cannot_determine && pp.cannot_determine.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
                    {pp.cannot_determine.slice(0, 6).map((field, j) => (
                      <span key={j} style={{
                        fontFamily: 'var(--font-geist-mono)', fontSize: 10,
                        padding: '2px 8px', borderRadius: 100,
                        background: 'rgba(213,122,120,0.08)', border: '1px solid rgba(213,122,120,0.2)',
                        color: 'var(--m-bad)',
                      }}>
                        cannot determine: {field}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {report.product_perceptions.length > 5 && (
              <p style={{ margin: 0, fontSize: 11, color: 'var(--m-fg-3)', textAlign: 'center' }}>
                Showing 5 of {report.product_perceptions.length} — full data available via API.
              </p>
            )}
          </div>
        </section>
      )}

      {/* MCP simulation */}
      {report.mcp_simulation && report.mcp_simulation.length > 0 && (
        <section>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 20 }}>
            <div>
              <div className="eyebrow">AI shopping agents tested</div>
              <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 32, lineHeight: 1.05, fontWeight: 400, margin: '8px 0 0', color: 'var(--m-fg)' }}>How AI answers buyer questions.</h3>
            </div>
            <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-fg-3)' }}>{report.mcp_simulation.length} probes</span>
          </div>
          <MCPSimulation results={report.mcp_simulation} isSimulation={report.ingestion_mode === 'url_only'} />
        </section>
      )}

      {/* Competitor comparison */}
      <section>
        <div className="eyebrow" style={{ marginBottom: 6 }}>Competitor Comparison</div>
        {competitorResults.length > 0 ? (
          <CompetitorPanel results={competitorResults} />
        ) : (
          <CompetitorDiscovery
            jobId={jobId}
            onResults={onCompetitorResults}
          />
        )}
      </section>
    </div>
  )
}

// ── FINDINGS TAB ────────────────────────────────────────────────────────
function FindingsTab({ report, critCount, highCount }: { report: AuditReport; critCount: number; highCount: number }) {
  const findings = report.findings ?? []
  return (
    <div>
      <div className="eyebrow">All issues found</div>
      <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(32px,4vw,52px)', lineHeight: 1.0, letterSpacing: '-0.02em', fontWeight: 400, margin: '12px 0 8px', color: 'var(--m-fg)' }}>
        {findings.length} <em style={{ fontStyle: 'italic', color: 'var(--m-violet)' }}>thing{findings.length !== 1 ? 's' : ''} to fix.</em>
      </h2>
      <div style={{ display: 'flex', gap: 10, marginBottom: 32 }}>
        {critCount > 0 && <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, padding: '4px 10px', borderRadius: 100, background: 'rgba(213,122,120,0.1)', border: '1px solid rgba(213,122,120,0.25)', color: 'var(--m-bad)' }}>{critCount} Critical</span>}
        {highCount > 0 && <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, padding: '4px 10px', borderRadius: 100, background: 'rgba(212,169,107,0.1)', border: '1px solid rgba(212,169,107,0.25)', color: 'var(--m-warn)' }}>{highCount} High</span>}
      </div>
      <FindingsTable findings={findings} />
    </div>
  )
}

// ── PRODUCTS TAB ────────────────────────────────────────────────────────
function ProductsTab({ report, onRestart }: { report: AuditReport; onRestart: () => void }) {
  const products = report.all_products ?? report.worst_5_products ?? []
  const findings = report.findings ?? []
  const worst = report.worst_5_products ?? []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 48 }}>
      <div>
        <div className="eyebrow">Product Analysis</div>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(32px,4vw,52px)', lineHeight: 1.0, letterSpacing: '-0.02em', fontWeight: 400, margin: '12px 0 0', color: 'var(--m-fg)' }}>
          Completeness <em style={{ fontStyle: 'italic', color: 'var(--m-violet)' }}>heatmap.</em>
        </h2>
        <p style={{ fontSize: 14, color: 'var(--m-fg-2)', marginTop: 8, lineHeight: 1.5 }}>
          Every product graded against the catalog completeness checks. Red cells are gaps AI agents hit.
        </p>
      </div>

      {report.scan_limited && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
          padding: '14px 20px', borderRadius: 14, flexWrap: 'wrap',
          background: 'rgba(212,169,107,0.06)', border: '1px solid rgba(212,169,107,0.2)',
        }}>
          <div>
            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--m-warn)' }}>
              Free scan — showing {report.total_products} of {report.full_product_count} products
            </span>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--m-fg-3)' }}>
              Add an Admin Token to scan your full catalog and unlock autonomous fixes.
            </p>
          </div>
          <button
            onClick={onRestart}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 100, border: '1px solid rgba(212,169,107,0.4)',
              background: 'transparent', color: 'var(--m-warn)', fontSize: 12,
              cursor: 'pointer', fontFamily: 'var(--font-geist)', whiteSpace: 'nowrap',
            }}
          >
            Run full scan <ArrowRight size={11} />
          </button>
        </div>
      )}

      {products.length > 0 && (
        <div style={{ background: 'var(--ink-2)', border: '1px solid var(--ink-line)', borderRadius: 20, padding: 28 }}>
          <div className="eyebrow" style={{ marginBottom: 20 }}>Completeness Heatmap</div>
          <HeatmapGrid products={products} findings={findings} />
        </div>
      )}

      {worst.length > 0 && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 20 }}>Most Problematic Products</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {worst.map((product, idx) => (
              <div key={product.product_id} style={{ background: 'var(--ink-2)', border: '1px solid var(--ink-line)', borderRadius: 14, padding: '16px 20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, minWidth: 0, flex: 1 }}>
                    <span style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11, color: 'var(--m-fg-4)', marginTop: 2, flexShrink: 0, width: 20 }}>#{idx + 1}</span>
                    <div style={{ minWidth: 0 }}>
                      <p style={{ margin: '0 0 6px', fontSize: 14, color: 'var(--m-fg)', fontWeight: 500 }}>{product.title}</p>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {(product.failing_check_ids ?? []).slice(0, 6).map(id => (
                          <span key={id} style={{ fontSize: 11, background: 'var(--ink-3)', color: 'var(--m-fg-3)', borderRadius: 6, padding: '2px 8px', border: '1px solid var(--ink-line)' }}>{CHECK_LABELS[id] ?? id}</span>
                        ))}
                        {(product.failing_check_ids?.length ?? 0) > 6 && (
                          <span style={{ fontSize: 11, color: 'var(--m-fg-4)', padding: '2px 4px' }}>+{(product.failing_check_ids?.length ?? 0) - 6} more</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div style={{ flexShrink: 0, textAlign: 'right' }}>
                    <p style={{ fontFamily: 'var(--font-display)', fontSize: 28, lineHeight: 1, color: 'var(--m-bad)', margin: 0 }}>{product.gap_score.toFixed(0)}</p>
                    <p style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 10, color: 'var(--m-fg-3)', marginTop: 2 }}>issues</p>
                  </div>
                </div>
                <div style={{ marginTop: 10, height: 2, background: 'rgba(255,255,255,0.05)', borderRadius: 100, overflow: 'hidden' }}>
                  <div style={{ height: '100%', background: 'rgba(213,122,120,0.5)', borderRadius: 100, width: `${Math.min(product.gap_score, 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── FIXES TAB ───────────────────────────────────────────────────────────
function FixesTab({ report, jobId, adminToken, onReset, onExecute, onReportRefresh }: {
  report: AuditReport
  jobId: string
  adminToken: string | null
  onReset: () => void
  onExecute: (ids: string[]) => Promise<void>
  onReportRefresh?: () => void | Promise<void>
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 48 }}>
      <div>
        <div className="eyebrow">The plan</div>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(32px,4vw,56px)', lineHeight: 1.0, letterSpacing: '-0.02em', fontWeight: 400, margin: '12px 0 12px', color: 'var(--m-fg)' }}>
          Mend the<br />
          <em style={{ fontStyle: 'italic', color: 'var(--m-violet)' }}>reflection.</em>
        </h2>
        <p style={{ fontSize: 15, lineHeight: 1.55, color: 'var(--m-fg-2)', margin: 0, maxWidth: 560 }}>
          {adminToken
            ? 'Approve fixes one by one or in bulk. Every autonomous change is logged, verified, and rollback-ready.'
            : 'Add an Admin Token to unlock autonomous fix execution.'}
        </p>
      </div>

      {!adminToken && (
        <div style={{ background: 'var(--ink-2)', border: '1px solid rgba(212,169,107,0.25)', borderRadius: 20, padding: 40, textAlign: 'center' }}>
          <div style={{ width: 48, height: 48, borderRadius: 14, background: 'rgba(212,169,107,0.1)', border: '1px solid rgba(212,169,107,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', color: 'var(--m-warn)' }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="8" cy="14" r="4" />
              <path d="M11 11l9-9M16 6l3 3" />
            </svg>
          </div>
          <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--m-fg)', margin: '0 0 8px' }}>Admin Token Required</p>
          <p style={{ fontSize: 14, color: 'var(--m-fg-2)', margin: '0 0 20px', maxWidth: 400, marginLeft: 'auto', marginRight: 'auto', lineHeight: 1.55 }}>
            Run a new audit with your Shopify Admin API token to unlock autonomous fix execution, taxonomy mapping, and metafield injection.
          </p>
          <button
            onClick={onReset}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '12px 22px', borderRadius: 100, background: 'var(--m-warn)', color: 'var(--ink)', border: 'none', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}
          >
            Run Full Audit <ArrowRight size={14} />
          </button>
        </div>
      )}

      {adminToken && !report.agent_run && (
        <FixApproval jobId={jobId} onExecute={onExecute} />
      )}

      {report.agent_run && (
        <AgentActivity
          agentRun={report.agent_run}
          jobId={jobId}
          adminToken={adminToken}
          onAfterRollback={onReportRefresh}
        />
      )}

      {report.agent_run?.before_after && (
        <>
          <BeforeAfterReport
            data={report.agent_run.before_after}
            copyPasteItems={report.copy_paste_package ?? []}
            storeName={report.store_name}
          />
          <ReadinessCertificate
            storeName={report.store_name}
            storeDomain={report.store_domain}
            data={report.agent_run.before_after}
            agentRun={report.agent_run}
          />
        </>
      )}
    </div>
  )
}
