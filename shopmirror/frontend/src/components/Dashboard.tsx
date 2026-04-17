import type { AuditReport, ChannelStatus, QueryMatchResult } from '../api/client'
import FindingsTable from './FindingsTable'
import CompetitorPanel from './CompetitorPanel'
import MCPSimulation from './MCPSimulation'
import PerceptionDiff from './PerceptionDiff'

interface Props {
  report: AuditReport
  jobId: string
  onReset: () => void
}

function scoreColor(score: number): string {
  if (score >= 70) return 'text-green-400'
  if (score >= 40) return 'text-yellow-400'
  return 'text-red-400'
}

const CHANNEL_LABELS: Record<keyof AuditReport['channel_compliance'], string> = {
  shopify_catalog: 'Shopify Catalog',
  google_shopping: 'Google Shopping',
  meta_catalog: 'Meta Catalog',
  perplexity_web: 'Perplexity',
  chatgpt_shopping: 'ChatGPT',
}

function channelStatusClasses(status: ChannelStatus['status']): string {
  if (status === 'READY') return 'bg-green-500/20 text-green-400 border border-green-600'
  if (status === 'PARTIAL') return 'bg-yellow-500/20 text-yellow-400 border border-yellow-600'
  return 'bg-red-500/20 text-red-400 border border-red-600'
}

function QueryMatchBar({ result }: { result: QueryMatchResult }) {
  const pct =
    result.total_products > 0
      ? Math.round((result.match_count / result.total_products) * 100)
      : 0

  return (
    <div className="bg-gray-900 rounded-xl p-4 space-y-2">
      <div className="flex justify-between items-center gap-4">
        <span className="text-gray-200 text-sm font-medium truncate">{result.query}</span>
        <span className="text-gray-400 text-xs shrink-0">
          {result.match_count}/{result.total_products} matched
        </span>
      </div>
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-green-500 rounded-full transition-all"
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
                className="text-xs bg-gray-800 text-gray-400 rounded px-2 py-0.5"
              >
                {attr}: {count} missing
              </span>
            ))}
        </div>
      )}
    </div>
  )
}

export default function Dashboard({ report, jobId: _jobId, onReset }: Props) {
  const score = Math.round(report.ai_readiness_score)
  const channels = Object.entries(report.channel_compliance) as [
    keyof AuditReport['channel_compliance'],
    ChannelStatus,
  ][]

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="max-w-6xl mx-auto px-6 py-10">

        {/* Header */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-white">{report.store_name}</h1>
            <p className="text-gray-400 text-sm mt-1">{report.store_domain}</p>
            <span
              className={`inline-block mt-2 text-xs px-2.5 py-1 rounded-full font-medium ${
                report.ingestion_mode === 'admin_token'
                  ? 'bg-sky-500/20 text-sky-400 border border-sky-600'
                  : 'bg-gray-700 text-gray-300 border border-gray-600'
              }`}
            >
              {report.ingestion_mode === 'admin_token' ? 'Full audit' : 'Public data'}
            </span>
          </div>
          <button
            onClick={onReset}
            className="text-sky-400 hover:text-sky-300 transition-colors text-sm font-medium mt-1"
          >
            ← New Analysis
          </button>
        </div>

        {/* AI Readiness Score */}
        <div className="mt-10 bg-gray-900 rounded-2xl p-10 text-center">
          <div className={`text-8xl font-black leading-none ${scoreColor(score)}`}>
            {score}
          </div>
          <div className="text-gray-400 text-lg mt-3">AI Readiness Score</div>
          <div className="text-gray-500 text-sm mt-1">
            {report.total_products} products analyzed
          </div>
        </div>

        {/* Pillar Scores */}
        {Object.keys(report.pillars).length > 0 && (
          <div className="mt-8 grid grid-cols-5 gap-4">
            {Object.entries(report.pillars).map(([name, pillar]) => (
              <div key={name} className="bg-gray-800 rounded-xl p-4 text-center">
                <div className="text-xs text-gray-400 truncate mb-2" title={name}>
                  {name}
                </div>
                <div className={`text-2xl font-bold ${scoreColor(pillar.score)}`}>
                  {Math.round(pillar.score)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {pillar.checks_passed}/{pillar.checks_total}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Channel Compliance */}
        <div className="mt-10">
          <h2 className="text-xl font-semibold text-white mb-4">
            Multi-Channel AI Compliance
          </h2>
          <div className="grid grid-cols-5 gap-3">
            {channels.map(([key, ch]) => (
              <div key={key} className="bg-gray-900 rounded-xl p-4 text-center">
                <div className="text-xs text-gray-400 mb-3">{CHANNEL_LABELS[key]}</div>
                <span
                  className={`inline-block text-xs font-semibold px-2 py-1 rounded-full ${channelStatusClasses(ch.status)}`}
                >
                  {ch.status}
                </span>
                {ch.blocking_check_ids.length > 0 && (
                  <div
                    className="text-xs text-gray-600 mt-2 truncate"
                    title={ch.blocking_check_ids.join(', ')}
                  >
                    {ch.blocking_check_ids.length} blocker
                    {ch.blocking_check_ids.length !== 1 ? 's' : ''}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Query Match Simulator */}
        {report.query_match_results.length > 0 && (
          <div className="mt-10">
            <h2 className="text-xl font-semibold text-white mb-4">
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
        <div className="mt-10">
          <FindingsTable findings={report.findings} />
        </div>

        {/* Perception Diff */}
        {report.perception_diff && (
          <div className="mt-10">
            <PerceptionDiff diff={report.perception_diff} />
          </div>
        )}

        {/* MCP Simulation */}
        {report.mcp_simulation && report.mcp_simulation.length > 0 && (
          <div className="mt-10">
            <MCPSimulation results={report.mcp_simulation} />
          </div>
        )}

        {/* Competitor Panel */}
        {report.competitor_comparison.length > 0 && (
          <div className="mt-10">
            <CompetitorPanel results={report.competitor_comparison} />
          </div>
        )}

        {/* Worst Products */}
        <div className="mt-10">
          <h2 className="text-xl font-semibold text-white mb-4">
            Most Problematic Products
          </h2>
          <div className="space-y-3">
            {report.worst_5_products.map((product) => (
              <div key={product.product_id} className="bg-gray-900 rounded-xl p-4">
                <div className="flex justify-between items-start gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="text-white font-medium truncate">{product.title}</div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {product.failing_check_ids.map((id) => (
                        <span
                          key={id}
                          className="text-xs bg-gray-800 text-gray-400 font-mono rounded px-2 py-0.5"
                        >
                          {id}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="shrink-0 text-right">
                    <div className={`text-lg font-bold ${scoreColor(100 - product.gap_score)}`}>
                      {product.gap_score.toFixed(0)}
                    </div>
                    <div className="text-xs text-gray-500">gap score</div>
                  </div>
                </div>
                <div className="mt-3 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-red-500 rounded-full"
                    style={{ width: `${Math.min(product.gap_score, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
