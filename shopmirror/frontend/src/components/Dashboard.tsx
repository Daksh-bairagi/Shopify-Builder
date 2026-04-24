import { useState } from 'react'
import type { AuditReport, ChannelStatus, QueryMatchResult } from '../api/client'
import FindingsTable from './FindingsTable'
import CompetitorPanel from './CompetitorPanel'
import MCPSimulation from './MCPSimulation'
import PerceptionDiff from './PerceptionDiff'
import FixApproval from './FixApproval'
import AgentActivity from './AgentActivity'
import BeforeAfterReport from './BeforeAfterReport'
import ReadinessCertificate from './ReadinessCertificate'
import HeatmapGrid from './HeatmapGrid'

interface Props {
  report: AuditReport
  jobId: string
  adminToken: string | null
  onReset: () => void
  onExecute: (approvedFixIds: string[]) => Promise<void>
}

type Tab = 'overview' | 'findings' | 'ai-perception' | 'products' | 'fixes'

function scoreLabel(score: number) {
  if (score >= 80) return { label: 'Excellent', color: 'text-emerald-400' }
  if (score >= 60) return { label: 'Good', color: 'text-blue-400' }
  if (score >= 40) return { label: 'Needs Work', color: 'text-amber-400' }
  return { label: 'Critical', color: 'text-red-400' }
}

function scoreRingColor(score: number) {
  if (score >= 80) return '#10B981'
  if (score >= 60) return '#3B82F6'
  if (score >= 40) return '#F59E0B'
  return '#EF4444'
}

function pillarColor(s: number) {
  if (s >= 0.7) return { text: 'text-blue-400', bar: 'bg-blue-500', glow: 'rgba(59,130,246,0.4)' }
  if (s >= 0.4) return { text: 'text-amber-400', bar: 'bg-amber-500', glow: 'rgba(245,158,11,0.4)' }
  return { text: 'text-red-400', bar: 'bg-red-500', glow: 'rgba(239,68,68,0.4)' }
}

const PILLAR_LABELS: Record<string, string> = {
  Discoverability: 'Discoverability',
  Completeness: 'Completeness',
  Consistency: 'Consistency',
  Trust_Policies: 'Trust & Policies',
  Transaction: 'Transaction',
}

const CHANNEL_LABELS: Record<keyof AuditReport['channel_compliance'], string> = {
  shopify_catalog: 'Shopify Catalog',
  google_shopping: 'Google Shopping',
  meta_catalog: 'Meta Catalog',
  perplexity_web: 'Perplexity',
  chatgpt_shopping: 'ChatGPT',
}

function channelCfg(s: ChannelStatus['status']) {
  if (s === 'READY') return { dot: 'bg-emerald-400', text: 'text-emerald-400', bg: 'bg-emerald-400/10 border-emerald-400/20', bar: 'bg-emerald-500' }
  if (s === 'PARTIAL') return { dot: 'bg-amber-400', text: 'text-amber-400', bg: 'bg-amber-400/10 border-amber-400/20', bar: 'bg-amber-500' }
  return { dot: 'bg-red-400', text: 'text-red-400', bg: 'bg-red-400/10 border-red-400/20', bar: 'bg-red-500' }
}

function ScoreRing({ score }: { score: number }) {
  const r = 54
  const circ = 2 * Math.PI * r
  const offset = circ - (score / 100) * circ
  const color = scoreRingColor(score)
  const { label, color: labelColor } = scoreLabel(score)
  return (
    <div className="relative flex items-center justify-center w-40 h-40">
      <svg className="absolute inset-0 -rotate-90" width="160" height="160">
        <circle cx="80" cy="80" r={r} fill="none" stroke="#1E2545" strokeWidth="10" />
        <circle
          cx="80" cy="80" r={r} fill="none"
          stroke={color} strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          style={{ filter: `drop-shadow(0 0 8px ${color})`, transition: 'stroke-dashoffset 1s ease-out' }}
        />
      </svg>
      <div className="relative text-center">
        <div className="font-code text-4xl font-black text-white leading-none">{score}</div>
        <div className={`font-code text-xs font-semibold mt-1 ${labelColor}`}>{label}</div>
      </div>
    </div>
  )
}

function QueryMatchBar({ result }: { result: QueryMatchResult }) {
  const pct = result.total_products > 0 ? Math.round((result.match_count / result.total_products) * 100) : 0
  const color = pct >= 70 ? 'from-blue-600 to-blue-400' : pct >= 40 ? 'from-amber-600 to-amber-400' : 'from-red-600 to-red-400'
  return (
    <div className="bg-[#0F1535] border border-[#1E2545] rounded-xl p-4 space-y-2.5 hover:border-[#2D3A5E] transition-colors">
      <div className="flex justify-between items-center gap-4">
        <span className="text-[#A8B4D8] text-sm truncate">{result.query}</span>
        <span className="font-code text-xs text-[#4B5A8A] shrink-0">{result.match_count}/{result.total_products}</span>
      </div>
      <div className="h-1.5 bg-[#1E2545] rounded-full overflow-hidden">
        <div className={`h-full bg-gradient-to-r ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

const TABS: { id: Tab; label: string; icon: JSX.Element }[] = [
  {
    id: 'overview', label: 'Overview',
    icon: <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" /></svg>,
  },
  {
    id: 'findings', label: 'Findings',
    icon: <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>,
  },
  {
    id: 'ai-perception', label: 'AI Perception',
    icon: <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" /></svg>,
  },
  {
    id: 'products', label: 'Products',
    icon: <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" /></svg>,
  },
  {
    id: 'fixes', label: 'Fix Plan',
    icon: <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" /></svg>,
  },
]

export default function Dashboard({ report, jobId, adminToken, onReset, onExecute }: Props) {
  const [tab, setTab] = useState<Tab>('overview')
  const score = Math.round(report.ai_readiness_score)
  const channels = Object.entries(report.channel_compliance) as [keyof AuditReport['channel_compliance'], ChannelStatus][]
  const readyCount = channels.filter(([, ch]) => ch.status === 'READY').length
  const criticalCount = report.findings.filter(f => f.severity === 'CRITICAL').length
  const highCount = report.findings.filter(f => f.severity === 'HIGH').length

  return (
    <div className="min-h-screen bg-[#070B1C] text-white flex flex-col">

      {/* ── Top header bar ──────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 bg-[#070B1C]/90 backdrop-blur-md border-b border-[#1E2545]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between h-16 gap-6">

            {/* Logo + store */}
            <div className="flex items-center gap-4 min-w-0">
              <div className="flex items-center gap-2 shrink-0">
                <div className="w-7 h-7 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center">
                  <svg className="w-4 h-4 text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 3.75H6A2.25 2.25 0 003.75 6v1.5M16.5 3.75H18A2.25 2.25 0 0120.25 6v1.5m0 9V18A2.25 2.25 0 0118 20.25h-1.5m-9 0H6A2.25 2.25 0 013.75 18v-1.5M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <span className="font-code text-sm font-bold text-white">Shop<span className="text-blue-400">Mirror</span></span>
              </div>
              <div className="w-px h-5 bg-[#1E2545]" />
              <div className="min-w-0">
                <p className="font-code text-sm font-semibold text-white truncate">{report.store_name}</p>
                <p className="font-code text-xs text-[#4B5A8A] truncate">{report.store_domain}</p>
              </div>
            </div>

            {/* Score pill */}
            <div className="hidden sm:flex items-center gap-3 shrink-0">
              <div className="flex items-center gap-2 bg-[#0F1535] border border-[#1E2545] rounded-xl px-4 py-2">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: scoreRingColor(score), boxShadow: `0 0 8px ${scoreRingColor(score)}` }} />
                <span className="font-code text-sm font-bold text-white">{score}</span>
                <span className="text-xs text-[#4B5A8A]">/ 100</span>
              </div>
              <div className={`text-xs px-2.5 py-1 rounded-full border font-medium ${
                report.ingestion_mode === 'admin_token'
                  ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                  : 'bg-[#0F1535] text-[#6B7DB3] border-[#1E2545]'
              }`}>
                {report.ingestion_mode === 'admin_token' ? 'Full audit' : 'Public data'}
              </div>
            </div>

            <button
              onClick={onReset}
              className="shrink-0 flex items-center gap-2 text-xs text-[#6B7DB3] hover:text-white transition-colors cursor-pointer bg-[#0F1535] border border-[#1E2545] hover:border-[#2D3A5E] px-3 py-2 rounded-lg"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
              </svg>
              New Audit
            </button>
          </div>

          {/* Tab bar */}
          <nav className="flex items-center gap-1 -mb-px overflow-x-auto">
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all duration-200 whitespace-nowrap cursor-pointer ${
                  tab === t.id
                    ? 'border-blue-500 text-white'
                    : 'border-transparent text-[#4B5A8A] hover:text-[#A8B4D8] hover:border-[#2D3A5E]'
                }`}
              >
                <span className={tab === t.id ? 'text-blue-400' : ''}>{t.icon}</span>
                {t.label}
                {t.id === 'findings' && report.findings.length > 0 && (
                  <span className={`text-xs px-1.5 py-0.5 rounded-full font-code ${
                    tab === t.id ? 'bg-blue-500/20 text-blue-400' : 'bg-[#1E2545] text-[#4B5A8A]'
                  }`}>{report.findings.length}</span>
                )}
                {t.id === 'fixes' && adminToken && (
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                )}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* ── Tab content ─────────────────────────────────────────────── */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">

        {/* OVERVIEW TAB */}
        {tab === 'overview' && (
          <div className="space-y-8 animate-fade-in">

            {/* Hero row: Score + Stats */}
            <div className="grid grid-cols-12 gap-5">

              {/* Score card */}
              <div className="col-span-12 md:col-span-4 bg-[#0D1130] border border-[#1E2545] rounded-2xl p-8 flex flex-col items-center justify-center gap-4">
                <ScoreRing score={score} />
                <div className="text-center space-y-1">
                  <p className="text-[#6B7DB3] text-sm">AI Readiness Score</p>
                  <p className="text-[#4B5A8A] text-xs font-code">{report.total_products} products analyzed</p>
                </div>
                {/* Mini score bar */}
                <div className="w-full bg-[#1E2545] rounded-full h-1.5 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-1000"
                    style={{ width: `${score}%`, backgroundColor: scoreRingColor(score), boxShadow: `0 0 10px ${scoreRingColor(score)}` }}
                  />
                </div>
              </div>

              {/* Stats grid */}
              <div className="col-span-12 md:col-span-8 grid grid-cols-2 gap-4">
                <div className="bg-[#0D1130] border border-[#1E2545] rounded-2xl p-6 space-y-3">
                  <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest">Issues Found</p>
                  <p className="font-code text-4xl font-black text-white">{report.findings.length}</p>
                  <div className="space-y-2 pt-1">
                    {criticalCount > 0 && (
                      <div className="flex items-center justify-between text-xs">
                        <span className="flex items-center gap-1.5 text-red-400"><span className="w-1.5 h-1.5 rounded-full bg-red-400" />Critical</span>
                        <span className="font-code text-red-400 font-semibold">{criticalCount}</span>
                      </div>
                    )}
                    {highCount > 0 && (
                      <div className="flex items-center justify-between text-xs">
                        <span className="flex items-center gap-1.5 text-orange-400"><span className="w-1.5 h-1.5 rounded-full bg-orange-400" />High</span>
                        <span className="font-code text-orange-400 font-semibold">{highCount}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="bg-[#0D1130] border border-[#1E2545] rounded-2xl p-6 space-y-3">
                  <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest">Channels Ready</p>
                  <p className="font-code text-4xl font-black text-white">{readyCount}<span className="text-[#2D3A5E] text-2xl">/{channels.length}</span></p>
                  <div className="flex gap-1.5 pt-1">
                    {channels.map(([key, ch]) => {
                      const cfg = channelCfg(ch.status)
                      return <div key={key} className={`flex-1 h-1.5 rounded-full ${cfg.bar}`} title={`${CHANNEL_LABELS[key]}: ${ch.status}`} />
                    })}
                  </div>
                  <p className="text-xs text-[#4B5A8A]">AI shopping platforms</p>
                </div>

                <div className="col-span-2 bg-[#0D1130] border border-[#1E2545] rounded-2xl p-5">
                  <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-4">Pillar Scores</p>
                  <div className="grid grid-cols-5 gap-3">
                    {Object.entries(report.pillars).map(([name, pillar]) => {
                      const s = Math.round(pillar.score * 100)
                      const cfg = pillarColor(pillar.score)
                      return (
                        <div key={name} className="text-center space-y-2">
                          <div className={`font-code text-2xl font-bold ${cfg.text}`}>{s}</div>
                          <div className="h-1 bg-[#1E2545] rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${cfg.bar}`} style={{ width: `${s}%` }} />
                          </div>
                          <p className="text-xs text-[#4B5A8A] leading-tight">{PILLAR_LABELS[name] ?? name}</p>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            </div>

            {/* Channel compliance */}
            <div>
              <h2 className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-4">Multi-Channel AI Compliance</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                {channels.map(([key, ch]) => {
                  const cfg = channelCfg(ch.status)
                  return (
                    <div key={key} className="bg-[#0D1130] border border-[#1E2545] rounded-xl p-4 hover:border-[#2D3A5E] transition-colors">
                      <div className="flex items-center justify-between mb-3">
                        <p className="text-xs text-[#6B7DB3] font-medium truncate">{CHANNEL_LABELS[key]}</p>
                        <span className={`w-2 h-2 rounded-full ${cfg.dot} shrink-0`} style={{ boxShadow: `0 0 6px currentColor` }} />
                      </div>
                      <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full border ${cfg.bg} ${cfg.text}`}>
                        {ch.status}
                      </span>
                      {ch.blocking_check_ids.length > 0 && (
                        <p className="text-xs text-[#2D3A5E] mt-2 font-code">{ch.blocking_check_ids.length} blocker{ch.blocking_check_ids.length !== 1 ? 's' : ''}</p>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Query match */}
            {report.query_match_results.length > 0 && (
              <div>
                <h2 className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-4">AI Query Match Simulator</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {report.query_match_results.map((r, i) => <QueryMatchBar key={i} result={r} />)}
                </div>
              </div>
            )}
          </div>
        )}

        {/* FINDINGS TAB */}
        {tab === 'findings' && (
          <div className="animate-fade-in">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">Audit Findings</h2>
                <p className="text-sm text-[#4B5A8A] mt-1">{report.findings.length} issues detected across your store</p>
              </div>
              <div className="flex items-center gap-2">
                {criticalCount > 0 && <span className="text-xs px-2.5 py-1 rounded-full bg-red-400/10 border border-red-400/20 text-red-400 font-medium">{criticalCount} Critical</span>}
                {highCount > 0 && <span className="text-xs px-2.5 py-1 rounded-full bg-orange-400/10 border border-orange-400/20 text-orange-400 font-medium">{highCount} High</span>}
              </div>
            </div>
            <FindingsTable findings={report.findings} />
          </div>
        )}

        {/* AI PERCEPTION TAB */}
        {tab === 'ai-perception' && (
          <div className="space-y-8 animate-fade-in">
            <div>
              <h2 className="text-lg font-semibold text-white">AI Perception Analysis</h2>
              <p className="text-sm text-[#4B5A8A] mt-1">How AI shopping agents perceive your store vs. your intent</p>
            </div>
            {report.perception_diff && <PerceptionDiff diff={report.perception_diff} />}
            {report.mcp_simulation && report.mcp_simulation.length > 0 && (
              <div>
                <h3 className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-4">MCP Agent Simulation</h3>
                <MCPSimulation results={report.mcp_simulation} />
              </div>
            )}
            {report.competitor_comparison.length > 0 && (
              <div>
                <h3 className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-4">Competitor Comparison</h3>
                <CompetitorPanel results={report.competitor_comparison} />
              </div>
            )}
          </div>
        )}

        {/* PRODUCTS TAB */}
        {tab === 'products' && (
          <div className="space-y-8 animate-fade-in">
            <div>
              <h2 className="text-lg font-semibold text-white">Product Analysis</h2>
              <p className="text-sm text-[#4B5A8A] mt-1">Completeness heatmap and most problematic products</p>
            </div>
            {(report.all_products ?? report.worst_5_products).length > 0 && (
              <div className="bg-[#0D1130] border border-[#1E2545] rounded-2xl p-6">
                <h3 className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-5">Completeness Heatmap</h3>
                <HeatmapGrid products={report.all_products ?? report.worst_5_products} findings={report.findings} />
              </div>
            )}
            {report.worst_5_products.length > 0 && (
              <div>
                <h3 className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-4">Most Problematic Products</h3>
                <div className="space-y-3">
                  {report.worst_5_products.map((product, idx) => (
                    <div key={product.product_id} className="bg-[#0D1130] border border-[#1E2545] hover:border-[#2D3A5E] rounded-xl p-4 transition-colors">
                      <div className="flex justify-between items-start gap-4">
                        <div className="flex items-start gap-3 min-w-0 flex-1">
                          <span className="font-code text-xs text-[#2D3A5E] mt-0.5 shrink-0 w-5">#{idx + 1}</span>
                          <div className="min-w-0">
                            <p className="text-white font-medium truncate">{product.title}</p>
                            <div className="mt-2 flex flex-wrap gap-1">
                              {product.failing_check_ids.map((id) => (
                                <span key={id} className="text-xs bg-[#1E2545] text-[#6B7DB3] font-code rounded px-2 py-0.5">{id}</span>
                              ))}
                            </div>
                          </div>
                        </div>
                        <div className="shrink-0 text-right">
                          <p className="font-code text-lg font-bold text-red-400">{product.gap_score.toFixed(0)}</p>
                          <p className="text-xs text-[#4B5A8A]">gap score</p>
                        </div>
                      </div>
                      <div className="mt-3 h-1 bg-[#1E2545] rounded-full overflow-hidden">
                        <div className="h-full bg-red-500/60 rounded-full" style={{ width: `${Math.min(product.gap_score, 100)}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* FIXES TAB */}
        {tab === 'fixes' && (
          <div className="space-y-8 animate-fade-in">
            <div>
              <h2 className="text-lg font-semibold text-white">Fix Plan</h2>
              <p className="text-sm text-[#4B5A8A] mt-1">
                {adminToken ? 'Review and approve autonomous fixes for your store' : 'Add an Admin Token to unlock autonomous fix execution'}
              </p>
            </div>

            {!adminToken && (
              <div className="bg-[#0D1130] border border-amber-500/20 rounded-2xl p-8 text-center space-y-4">
                <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto">
                  <svg className="w-6 h-6 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
                  </svg>
                </div>
                <p className="text-white font-semibold">Admin Token Required</p>
                <p className="text-[#6B7DB3] text-sm max-w-sm mx-auto">Run a new audit with your Shopify Admin API token to unlock autonomous fix execution, taxonomy mapping, and metafield injection.</p>
                <button onClick={onReset} className="inline-flex items-center gap-2 bg-amber-500 hover:bg-amber-400 text-black font-semibold text-sm px-5 py-2.5 rounded-xl transition-colors cursor-pointer">
                  Run Full Audit
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                  </svg>
                </button>
              </div>
            )}

            {adminToken && !report.agent_run && <FixApproval jobId={jobId} onExecute={onExecute} />}
            {report.agent_run && <AgentActivity agentRun={report.agent_run} />}
            {report.agent_run?.before_after && (
              <>
                <BeforeAfterReport data={report.agent_run.before_after} copyPasteItems={report.copy_paste_package} storeName={report.store_name} />
                <ReadinessCertificate storeName={report.store_name} storeDomain={report.store_domain} data={report.agent_run.before_after} agentRun={report.agent_run} />
              </>
            )}
          </div>
        )}

      </main>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="border-t border-[#1E2545] py-4 text-center">
        <p className="text-xs text-[#1E2545] font-code">ShopMirror — Kasparro Agentic Commerce Hackathon · Track 5</p>
      </footer>
    </div>
  )
}
