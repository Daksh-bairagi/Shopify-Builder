import { useState } from 'react'
import type { Finding } from '../api/client'

interface Props {
  findings: Finding[]
}

type SeverityFilter = 'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM'

const SEVERITY_COLORS: Record<Finding['severity'], string> = {
  CRITICAL: 'bg-red-600/20 text-red-400 border border-red-700',
  HIGH: 'bg-orange-500/20 text-orange-400 border border-orange-600',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border border-yellow-600',
}

const FIX_TYPE_COLORS: Record<Finding['fix_type'], string> = {
  auto: 'bg-sky-500/20 text-sky-400 border border-sky-600',
  copy_paste: 'bg-purple-500/20 text-purple-400 border border-purple-600',
  manual: 'bg-gray-600/20 text-gray-400 border border-gray-600',
  developer: 'bg-orange-500/20 text-orange-400 border border-orange-600',
}

const FIX_TYPE_LABELS: Record<Finding['fix_type'], string> = {
  auto: 'Auto',
  copy_paste: 'Copy/Paste',
  manual: 'Manual',
  developer: 'Developer',
}

export default function FindingsTable({ findings }: Props) {
  const [filter, setFilter] = useState<SeverityFilter>('ALL')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const filtered =
    filter === 'ALL' ? findings : findings.filter((f) => f.severity === filter)

  const FILTER_OPTIONS: SeverityFilter[] = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM']

  function toggleExpand(id: string) {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  async function copyContent(id: string, content: string) {
    await navigator.clipboard.writeText(content)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div>
      {/* Header + filters */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-white">
          Audit Findings ({filtered.length})
        </h2>
        <div className="flex gap-2">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt}
              onClick={() => setFilter(opt)}
              className={`text-xs font-medium px-3 py-1.5 rounded-lg transition-colors ${
                filter === opt
                  ? 'bg-sky-500 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-gray-900 rounded-2xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left text-xs text-gray-500 font-medium px-4 py-3 w-24">
                Severity
              </th>
              <th className="text-left text-xs text-gray-500 font-medium px-4 py-3 w-32">
                Check
              </th>
              <th className="text-left text-xs text-gray-500 font-medium px-4 py-3">
                Issue
              </th>
              <th className="text-left text-xs text-gray-500 font-medium px-4 py-3 w-28">
                Affected
              </th>
              <th className="text-left text-xs text-gray-500 font-medium px-4 py-3 w-28">
                Fix Type
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="text-center text-gray-500 text-sm py-10">
                  No findings match this filter.
                </td>
              </tr>
            )}
            {filtered.map((finding) => (
              <>
                <tr
                  key={finding.id}
                  onClick={() => toggleExpand(finding.id)}
                  className="hover:bg-gray-800/50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block text-xs font-semibold px-2 py-0.5 rounded-full ${SEVERITY_COLORS[finding.severity]}`}
                    >
                      {finding.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-gray-400 font-mono text-xs">
                      {finding.check_id}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-white text-sm">
                      {expandedId === finding.id
                        ? finding.title
                        : finding.title.length > 60
                        ? finding.title.slice(0, 60) + '…'
                        : finding.title}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-gray-400 text-sm">
                      {finding.affected_count} product
                      {finding.affected_count !== 1 ? 's' : ''}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${FIX_TYPE_COLORS[finding.fix_type]}`}
                    >
                      {FIX_TYPE_LABELS[finding.fix_type]}
                    </span>
                  </td>
                </tr>

                {/* Expanded row */}
                {expandedId === finding.id && (
                  <tr key={`${finding.id}-expanded`}>
                    <td colSpan={5} className="bg-gray-900 px-6 py-4 border-b border-gray-800">
                      <p className="text-gray-300 text-sm mb-3">{finding.detail}</p>
                      {finding.impact_statement && (
                        <p className="text-gray-400 text-sm italic mb-3">
                          {finding.impact_statement}
                        </p>
                      )}
                      <div className="bg-gray-800 rounded-lg p-3 text-sm font-mono text-gray-300 mt-2 whitespace-pre-wrap">
                        {finding.fix_instruction}
                      </div>
                      {finding.fix_content && (
                        <div className="mt-3">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              copyContent(finding.id, finding.fix_content!)
                            }}
                            className="text-xs text-sky-400 hover:text-sky-300 font-medium mb-2 transition-colors"
                          >
                            {copiedId === finding.id ? '✓ Copied!' : 'Copy content'}
                          </button>
                          <div className="bg-gray-800 rounded-lg p-3 text-xs font-mono text-gray-400 max-h-40 overflow-y-auto whitespace-pre-wrap">
                            {finding.fix_content}
                          </div>
                        </div>
                      )}
                      {finding.spec_citation && (
                        <p className="text-gray-600 text-xs mt-3">
                          Spec: {finding.spec_citation}
                        </p>
                      )}
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
