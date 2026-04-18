import { useState } from 'react'
import type { Finding } from '../api/client'

interface Props {
  findings: Finding[]
}

type SeverityFilter = 'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM'

const SEVERITY_COLORS: Record<Finding['severity'], string> = {
  CRITICAL: 'bg-red-500/15 text-red-400 border border-red-500/40',
  HIGH: 'bg-orange-500/15 text-orange-400 border border-orange-500/40',
  MEDIUM: 'bg-amber-500/15 text-amber-400 border border-amber-500/40',
}

const SEVERITY_DOT: Record<Finding['severity'], string> = {
  CRITICAL: 'bg-red-500',
  HIGH: 'bg-orange-400',
  MEDIUM: 'bg-amber-400',
}

const FIX_TYPE_COLORS: Record<Finding['fix_type'], string> = {
  auto: 'bg-blue-500/15 text-blue-400 border border-blue-500/40',
  copy_paste: 'bg-purple-500/15 text-purple-400 border border-purple-500/40',
  manual: 'bg-[#1E2545] text-[#6B7DB3] border border-[#2D3A5E]',
  developer: 'bg-orange-500/15 text-orange-400 border border-orange-500/40',
}

const FIX_TYPE_LABELS: Record<Finding['fix_type'], string> = {
  auto: 'Auto',
  copy_paste: 'Copy/Paste',
  manual: 'Manual',
  developer: 'Developer',
}

const FILTER_OPTIONS: SeverityFilter[] = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM']

export default function FindingsTable({ findings }: Props) {
  const [filter, setFilter] = useState<SeverityFilter>('ALL')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const filtered =
    filter === 'ALL' ? findings : findings.filter((f) => f.severity === filter)

  function toggleExpand(id: string) {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  async function copyContent(id: string, content: string) {
    await navigator.clipboard.writeText(content)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const criticalCount = findings.filter((f) => f.severity === 'CRITICAL').length
  const highCount = findings.filter((f) => f.severity === 'HIGH').length
  const mediumCount = findings.filter((f) => f.severity === 'MEDIUM').length

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
        <div>
          <h2 className="text-xl font-semibold text-white font-sans">
            Audit Findings
          </h2>
          <div className="flex items-center gap-3 mt-1.5">
            {criticalCount > 0 && (
              <span className="flex items-center gap-1.5 text-xs text-red-400">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 inline-block" />
                {criticalCount} critical
              </span>
            )}
            {highCount > 0 && (
              <span className="flex items-center gap-1.5 text-xs text-orange-400">
                <span className="w-1.5 h-1.5 rounded-full bg-orange-400 inline-block" />
                {highCount} high
              </span>
            )}
            {mediumCount > 0 && (
              <span className="flex items-center gap-1.5 text-xs text-amber-400">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
                {mediumCount} medium
              </span>
            )}
          </div>
        </div>

        {/* Filter buttons */}
        <div className="flex gap-2">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt}
              onClick={() => setFilter(opt)}
              className={`text-xs font-medium px-3 py-1.5 rounded-lg transition-all duration-150 cursor-pointer ${
                filter === opt
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                  : 'bg-[#141830] border border-[#1E2545] text-[#6B7DB3] hover:text-white hover:border-[#2D3A5E]'
              }`}
            >
              {opt}
              {opt !== 'ALL' && (
                <span className="ml-1.5 opacity-60">
                  {findings.filter((f) => f.severity === opt).length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-[#141830] border border-[#1E2545] rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#1E2545]">
                <th className="text-left text-xs text-[#4B5A8A] font-medium px-4 py-3 w-24">
                  Severity
                </th>
                <th className="text-left text-xs text-[#4B5A8A] font-medium px-4 py-3 w-28">
                  Check
                </th>
                <th className="text-left text-xs text-[#4B5A8A] font-medium px-4 py-3">
                  Issue
                </th>
                <th className="text-left text-xs text-[#4B5A8A] font-medium px-4 py-3 w-24">
                  Affected
                </th>
                <th className="text-left text-xs text-[#4B5A8A] font-medium px-4 py-3 w-28">
                  Fix Type
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E2545]">
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center text-[#4B5A8A] text-sm py-12">
                    <svg className="w-8 h-8 mx-auto mb-3 text-[#2D3A5E]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    No findings match this filter
                  </td>
                </tr>
              )}
              {filtered.map((finding) => (
                <>
                  <tr
                    key={finding.id}
                    onClick={() => toggleExpand(finding.id)}
                    className="hover:bg-[#0F1535] cursor-pointer transition-colors duration-150"
                  >
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-0.5 rounded-full ${SEVERITY_COLORS[finding.severity]}`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${SEVERITY_DOT[finding.severity]}`} />
                        {finding.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-code text-[#6B7DB3] text-xs bg-[#0F1535] px-2 py-0.5 rounded">
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
                      <span className="text-[#6B7DB3] text-sm">
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
                      <td colSpan={5} className="bg-[#0A0E27] border-b border-[#1E2545]">
                        <div className="px-6 py-5 space-y-4">
                          <p className="text-[#A8B4D8] text-sm leading-relaxed">{finding.detail}</p>

                          {finding.impact_statement && (
                            <div className="flex items-start gap-2">
                              <svg className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                              </svg>
                              <p className="text-amber-400/80 text-sm italic">{finding.impact_statement}</p>
                            </div>
                          )}

                          <div>
                            <div className="text-xs text-[#4B5A8A] mb-2 font-code uppercase tracking-wider">
                              Fix Instruction
                            </div>
                            <div className="bg-[#141830] border border-[#1E2545] rounded-lg p-3 text-sm font-code text-[#A8B4D8] whitespace-pre-wrap leading-relaxed">
                              {finding.fix_instruction}
                            </div>
                          </div>

                          {finding.fix_content && (
                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <div className="text-xs text-[#4B5A8A] font-code uppercase tracking-wider">
                                  Fix Content
                                </div>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    copyContent(finding.id, finding.fix_content!)
                                  }}
                                  className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 font-medium transition-colors cursor-pointer"
                                >
                                  {copiedId === finding.id ? (
                                    <>
                                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                                      </svg>
                                      Copied!
                                    </>
                                  ) : (
                                    <>
                                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                                      </svg>
                                      Copy content
                                    </>
                                  )}
                                </button>
                              </div>
                              <div className="bg-[#141830] border border-[#1E2545] rounded-lg p-3 text-xs font-code text-[#6B7DB3] max-h-40 overflow-y-auto whitespace-pre-wrap">
                                {finding.fix_content}
                              </div>
                            </div>
                          )}

                          {finding.spec_citation && (
                            <p className="text-[#2D3A5E] text-xs font-code">
                              Spec: {finding.spec_citation}
                            </p>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
