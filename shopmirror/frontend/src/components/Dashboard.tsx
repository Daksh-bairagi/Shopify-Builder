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

function scoreLabel(score: number): string {
  if (score >= 80) return 'Excellent'
  if (score >= 60) return 'Good'
  if (score >= 40) return 'Needs Work'
  return 'Critical'
}

function scorePillarColor(score: number): string {
  if (score >= 0.7) return 'text-blue-400'
  if (score >= 0.4) return 'text-amber-400'
  return 'text-red-400'
}

function scorePillarBar(score: number): string {
  if (score >= 0.7) return 'bg-blue-500'
  if (score >= 0.4) return 'bg-amber-500'
  return 'bg-red-500'
}

const CHANNEL_LABELS: Record<keyof AuditReport['channel_compliance'], string> = {
  shopify_catalog: 'Shopify Catalog',
  google_shopping: 'Google Shopping',
  meta_catalog: 'Meta Catalog',
  perplexity_web: 'Perplexity',
  chatgpt_shopping: 'ChatGPT',
}

const CHANNEL_ICONS: Record<keyof AuditReport['channel_compliance'], JSX.Element> = {
  shopify_catalog: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 00-16.536-1.84M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z" />
    </svg>
  ),
  google_shopping: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
    </svg>
  ),
  meta_catalog: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
    </svg>
  ),
  perplexity_web: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
    </svg>
  ),
  chatgpt_shopping: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 9.75a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.184-4.183a1.14 1.14 0 01.778-.332 48.294 48.294 0 005.83-.498c1.585-.233 2.708-1.626 2.708-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
    </svg>
  ),
}

function channelStatusConfig(status: ChannelStatus['status']) {
  if (status === 'READY') return {
    border: 'border-l-blue-500',
    badge: 'bg-blue-500/15 text-blue-400 border border-blue-500/30',
    dot: 'bg-blue-500',
  }
  if (status === 'PARTIAL') return {
    border: 'border-l-amber-500',
    badge: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
    dot: 'bg-amber-500',
  }
  return {
    border: 'border-l-red-500',
    badge: 'bg-red-500/15 text-red-400 border border-red-500/30',
    dot: 'bg-red-500',
  }
}

function QueryMatchBar({ result }: { result: QueryMatchResult }) {
  const pct =
    result.total_products > 0
      ? Math.round((result.match_count / result.total_products) * 100)
      : 0

  const barColor = pct >= 70 ? 'from-blue-600 to-blue-400' : pct >= 40 ? 'from-amber-600 to-amber-400' : 'from-red-600 to-red-400'

  return (
    <div className="bg-[#141830] border border-[#1E2545] rounded-xl p-4 space-y-2 card-hover cursor-default">
      <div className="flex justify-between items-center gap-4">
        <span className="text-[#A8B4D8] text-sm font-medium truncate">{result.query}</span>
        <span className="font-code text-xs text-[#6B7DB3] shrink-0 bg-[#0F1535] px-2 py-0.5 rounded">
          {result.match_count}/{result.total_products}
        </span>
      </div>
      <div className="h-1.5 bg-[#0F1535] rounded-full overflow-hidden">
        <div
          className={`h-full bg-gradient-to-r ${barColor} rounded-full transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {Object.keys(result.failing_attributes).length > 0 && (
        <div className="flex flex-wrap gap-1 pt-1">
          {Object.entries(result.failing_attributes)
            .slice(0, 5)
            .map(([attr, count]) => (
              <span
                key={attr}
                className="text-xs bg-[#0F1535] text-[#4B5A8A] rounded px-2 py-0.5 font-code"
              >
                {attr}: {count} missing
              </span>
            ))}
        </div>
      )}
    </div>
  )
}

const PILLAR_NAMES: Record<string, string> = {
  'Discoverability': 'Discover',
  'Completeness': 'Complete',
  'Consistency': 'Consistent',
  'Trust_Policies': 'Trust',
  'Transaction': 'Transact',
}

export default function Dashboard({ report, jobId, adminToken, onReset, onExecute }: Props) {
  const score = Math.round(report.ai_readiness_score)
  const channels = Object.entries(report.channel_compliance) as [
    keyof AuditReport['channel_compliance'],
    ChannelStatus,
  ][]

  const readyCount = channels.filter(([, ch]) => ch.status === 'READY').length

  return (
    <div className="min-h-screen bg-[#0A0E27] text-white">
      <div className="max-w-6xl mx-auto px-6 py-10">

        {/* Header */}
        <div className="flex justify-between items-start animate-fade-in">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-code text-2xl font-bold text-white">{report.store_name}</h1>
              <span
                className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium ${
                  report.ingestion_mode === 'admin_token'
                    ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                    : 'bg-[#141830] text-[#6B7DB3] border border-[#1E2545]'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${report.ingestion_mode === 'admin_token' ? 'bg-blue-400' : 'bg-[#4B5A8A]'}`} />
                {report.ingestion_mode === 'admin_token' ? 'Full audit' : 'Public data'}
              </span>
            </div>
            <p className="text-[#4B5A8A] text-sm mt-1 font-code">{report.store_domain}</p>
          </div>
          <button
            onClick={onReset}
            className="flex items-center gap-2 text-sm text-[#6B7DB3] hover:text-white transition-colors cursor-pointer bg-[#141830] border border-[#1E2545] px-4 py-2 rounded-xl hover:border-[#2D3A5E]"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            New Analysis
          </button>
        </div>

        {/* Bento Grid — Score + Summary */}
        <div className="mt-8 grid grid-cols-12 gap-4 animate-slide-up">

          {/* AI Readiness Score — large card */}
          <div className="col-span-12 md:col-span-5 card p-8 flex flex-col items-center justify-center text-center">
            <div className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-4">
              AI Readiness Score
            </div>
            <div
              className="font-code font-black leading-none glow-score"
              style={{ fontSize: '7rem', lineHeight: 1 }}
            >
              {score}
            </div>
            <div className="text-[#6B7DB3] text-base mt-3 font-sans">{scoreLabel(score)}</div>
            <div className="text-[#4B5A8A] text-sm mt-1">{report.total_products} products analyzed</div>

            {/* Score arc visual */}
            <div className="mt-5 w-full bg-[#0F1535] rounded-full h-1.5 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-1000"
                style={{
                  width: `${score}%`,
                  background: 'linear-gradient(90deg, #F59E0B, #FBBF24)',
                  boxShadow: '0 0 12px rgba(245,158,11,0.6)',
                }}
              />
            </div>
          </div>

          {/* Summary stats */}
          <div className="col-span-12 md:col-span-7 grid grid-cols-2 gap-4">
            <div className="card p-5">
              <div className="text-xs font-code text-[#4B5A8A] uppercase tracking-wider mb-2">Findings</div>
              <div className="font-code text-3xl font-bold text-white">{report.findings.length}</div>
              <div className="text-[#6B7DB3] text-sm mt-1">issues detected</div>
              <div className="mt-3 space-y-1.5">
                {['CRITICAL', 'HIGH', 'MEDIUM'].map((sev) => {
                  const count = report.findings.filter((f) => f.severity === sev).length
                  return count > 0 ? (
                    <div key={sev} className="flex items-center justify-between text-xs">
                      <span className={`${sev === 'CRITICAL' ? 'text-red-400' : sev === 'HIGH' ? 'text-orange-400' : 'text-amber-400'}`}>
                        {sev}
                      </span>
                      <span className="font-code text-[#6B7DB3]">{count}</span>
                    </div>
                  ) : null
                })}
              </div>
            </div>

            <div className="card p-5">
              <div className="text-xs font-code text-[#4B5A8A] uppercase tracking-wider mb-2">Channels</div>
              <div className="font-code text-3xl font-bold text-white">{readyCount}/{channels.length}</div>
              <div className="text-[#6B7DB3] text-sm mt-1">ready for AI</div>
              <div className="mt-3 w-full bg-[#0F1535] rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full rounded-full bg-blue-500 transition-all"
                  style={{ width: `${(readyCount / channels.length) * 100}%` }}
                />
              </div>
            </div>

            <div className="card p-5 col-span-2">
              <div className="text-xs font-code text-[#4B5A8A] uppercase tracking-wider mb-3">Ingestion Mode</div>
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${report.ingestion_mode === 'admin_token' ? 'bg-blue-500/20' : 'bg-[#0F1535]'}`}>
                  <svg className={`w-4 h-4 ${report.ingestion_mode === 'admin_token' ? 'text-blue-400' : 'text-[#4B5A8A]'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
                  </svg>
                </div>
                <div>
                  <div className="text-white text-sm font-medium">
                    {report.ingestion_mode === 'admin_token' ? 'Admin API' : 'Public Storefront'}
                  </div>
                  <div className="text-[#4B5A8A] text-xs mt-0.5">
                    {report.ingestion_mode === 'admin_token'
                      ? 'Full access: metafields, taxonomy, inventory'
                      : 'Limited: public product data only'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Pillar Scores */}
        {Object.keys(report.pillars).length > 0 && (
          <div className="mt-6 animate-slide-up">
            <h2 className="text-sm font-code text-[#4B5A8A] uppercase tracking-widest mb-4">
              Pillar Scores
            </h2>
            <div className="grid grid-cols-5 gap-3">
              {Object.entries(report.pillars).map(([name, pillar]) => (
                <div key={name} className="card card-hover p-4 text-center cursor-default">
                  <div className="text-xs text-[#4B5A8A] font-code mb-2 truncate" title={name}>
                    {PILLAR_NAMES[name] ?? name}
                  </div>
                  <div className={`font-code text-2xl font-bold ${scorePillarColor(pillar.score)}`}>
                    {Math.round(pillar.score * 100)}
                  </div>
                  <div className="text-xs text-[#2D3A5E] mt-1 font-code">
                    {pillar.checks_passed}/{pillar.checks_total}
                  </div>
                  <div className="mt-3 w-full bg-[#0F1535] rounded-full h-1 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${scorePillarBar(pillar.score)} transition-all`}
                      style={{ width: `${pillar.score * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Product Completeness Heatmap */}
        {(report.all_products ?? report.worst_5_products).length > 0 && (
          <div className="mt-8">
            <h2 className="text-sm font-code text-[#4B5A8A] uppercase tracking-widest mb-4">
              Product Completeness Heatmap
            </h2>
            <div className="card p-5">
              <HeatmapGrid
                products={report.all_products ?? report.worst_5_products}
                findings={report.findings}
              />
            </div>
          </div>
        )}

        {/* Channel Compliance */}
        <div className="mt-8">
          <h2 className="text-sm font-code text-[#4B5A8A] uppercase tracking-widest mb-4">
            Multi-Channel AI Compliance
          </h2>
          <div className="grid grid-cols-5 gap-3">
            {channels.map(([key, ch]) => {
              const cfg = channelStatusConfig(ch.status)
              return (
                <div
                  key={key}
                  className={`bg-[#141830] border border-[#1E2545] rounded-xl p-4 border-l-4 ${cfg.border} card-hover cursor-default`}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-[#6B7DB3]">{CHANNEL_ICONS[key]}</span>
                    <span className="text-xs text-[#6B7DB3] font-medium">{CHANNEL_LABELS[key]}</span>
                  </div>
                  <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-0.5 rounded-full ${cfg.badge}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                    {ch.status}
                  </span>
                  {ch.blocking_check_ids.length > 0 && (
                    <div className="text-xs text-[#2D3A5E] mt-2 font-code">
                      {ch.blocking_check_ids.length} blocker{ch.blocking_check_ids.length !== 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Query Match Simulator */}
        {report.query_match_results.length > 0 && (
          <div className="mt-8">
            <h2 className="text-sm font-code text-[#4B5A8A] uppercase tracking-widest mb-4">
              AI Query Match Simulator
            </h2>
            <div className="space-y-3">
              {report.query_match_results.map((result, i) => (
                <QueryMatchBar key={i} result={result} />
              ))}
            </div>
          </div>
        )}

        {/* Findings Table */}
        <div className="mt-8">
          <FindingsTable findings={report.findings} />
        </div>

        {/* Perception Diff */}
        {report.perception_diff && (
          <div className="mt-8">
            <PerceptionDiff diff={report.perception_diff} />
          </div>
        )}

        {/* MCP Simulation */}
        {report.mcp_simulation && report.mcp_simulation.length > 0 && (
          <div className="mt-8">
            <MCPSimulation results={report.mcp_simulation} />
          </div>
        )}

        {/* Competitor Panel */}
        {report.competitor_comparison.length > 0 && (
          <div className="mt-8">
            <CompetitorPanel results={report.competitor_comparison} />
          </div>
        )}

        {/* Worst Products */}
        {report.worst_5_products.length > 0 && (
          <div className="mt-8">
            <h2 className="text-sm font-code text-[#4B5A8A] uppercase tracking-widest mb-4">
              Most Problematic Products
            </h2>
            <div className="space-y-3">
              {report.worst_5_products.map((product, idx) => (
                <div key={product.product_id} className="card card-hover p-4 cursor-default">
                  <div className="flex justify-between items-start gap-4">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <span className="font-code text-xs text-[#2D3A5E] mt-0.5 shrink-0">#{idx + 1}</span>
                      <div className="min-w-0">
                        <div className="text-white font-medium truncate">{product.title}</div>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {product.failing_check_ids.map((id) => (
                            <span
                              key={id}
                              className="text-xs bg-[#0F1535] text-[#6B7DB3] font-code rounded px-2 py-0.5 border border-[#1E2545]"
                            >
                              {id}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="font-code text-lg font-bold text-red-400">
                        {product.gap_score.toFixed(0)}
                      </div>
                      <div className="text-xs text-[#4B5A8A]">gap score</div>
                    </div>
                  </div>
                  <div className="mt-3 h-1 bg-[#0F1535] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-red-500/70 rounded-full"
                      style={{ width: `${Math.min(product.gap_score, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Fix Approval — shown when report is ready and admin token present but agent not yet run */}
        {adminToken && !report.agent_run && (
          <div className="mt-8">
            <h2 className="text-sm font-code text-[#4B5A8A] uppercase tracking-widest mb-4">
              Fix Plan — Agent Ready
            </h2>
            <FixApproval jobId={jobId} onExecute={onExecute} />
          </div>
        )}

        {/* Agent Activity — shown after agent has run */}
        {report.agent_run && (
          <div className="mt-8">
            <h2 className="text-sm font-code text-[#4B5A8A] uppercase tracking-widest mb-4">
              Agent Activity
            </h2>
            <AgentActivity agentRun={report.agent_run} />
          </div>
        )}

        {/* Before/After Report — shown when agent has run */}
        {report.agent_run?.before_after && (
          <div className="mt-8">
            <h2 className="text-sm font-code text-[#4B5A8A] uppercase tracking-widest mb-4">
              Before / After Comparison
            </h2>
            <BeforeAfterReport
              data={report.agent_run.before_after}
              copyPasteItems={report.copy_paste_package}
              storeName={report.store_name}
            />
          </div>
        )}

        {/* AI Readiness Certificate — shown when before/after is available */}
        {report.agent_run?.before_after && (
          <div className="mt-8">
            <h2 className="text-sm font-code text-[#4B5A8A] uppercase tracking-widest mb-4">
              AI Readiness Certificate
            </h2>
            <ReadinessCertificate
              storeName={report.store_name}
              storeDomain={report.store_domain}
              data={report.agent_run.before_after}
              agentRun={report.agent_run}
            />
          </div>
        )}

        {/* Bottom spacer */}
        <div className="mt-16 pb-4 text-center text-xs text-[#1E2545] font-code">
          ShopMirror — Kasparro Agentic Commerce Hackathon
        </div>

      </div>
    </div>
  )
}
