// Request/response shapes matching app/schemas.py
export interface AnalyzeRequest {
  store_url: string
  admin_token?: string
  merchant_intent?: string
  competitor_urls?: string[]
}

export interface AnalyzeResponse {
  job_id: string
}

export interface JobProgress {
  step: string
  pct: number
}

export interface JobStatusResponse {
  status: 'pending' | 'ingesting' | 'auditing' | 'simulating' | 'complete' | 'awaiting_approval' | 'error'
  progress: JobProgress
  report: AuditReport | null
  error: string | null
}

// Domain types matching app/models/findings.py
export interface PillarScore {
  score: number
  checks_passed: number
  checks_total: number
}

export interface Finding {
  id: string
  pillar: string
  check_id: string
  check_name: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM'
  weight: number
  title: string
  detail: string
  spec_citation: string
  affected_products: string[]
  affected_count: number
  impact_statement: string
  fix_type: 'auto' | 'copy_paste' | 'manual' | 'developer'
  fix_instruction: string
  fix_content: string | null
}

export interface ProductSummary {
  product_id: string
  title: string
  gap_score: number
  failing_check_ids: string[]
}

export interface ChannelStatus {
  status: 'READY' | 'PARTIAL' | 'BLOCKED'
  blocking_check_ids: string[]
}

export interface ChannelCompliance {
  shopify_catalog: ChannelStatus
  google_shopping: ChannelStatus
  meta_catalog: ChannelStatus
  perplexity_web: ChannelStatus
  chatgpt_shopping: ChannelStatus
}

export interface PerceptionDiff {
  intended_positioning: string
  ai_perception: string
  gap_reasons: string[]
}

export interface ProductPerception {
  product_id: string
  intended: string
  ai_extracted: string
  cannot_determine: string[]
  root_finding_ids: string[]
}

export interface MCPResult {
  question: string
  response: string
  classification: 'ANSWERED' | 'UNANSWERED' | 'WRONG'
  ground_truth_mismatch: string | null
  related_finding_ids: string[]
}

export interface QueryMatchResult {
  query: string
  matched_product_ids: string[]
  total_products: number
  match_count: number
  failing_attributes: Record<string, number>
}

export interface CompetitorAudit {
  url: string
  store_domain: string
  check_results: Record<string, boolean>
}

export interface CompetitorResult {
  competitor: CompetitorAudit
  gaps: string[]
}

export interface FixItem {
  fix_id: string
  product_id: string | null
  product_title: string | null
  type: string
  field: string
  current_value: string | null
  proposed_value: string | null
  reason: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM'
  fix_type: 'auto' | 'copy_paste' | 'manual' | 'developer'
  check_id: string
}

export interface FixPlanResponse {
  fixes: FixItem[]
}

export interface ExecuteRequest {
  approved_fix_ids: string[]
  admin_token: string
  merchant_intent?: string
}

export interface ExecuteResponse {
  execution_job_id: string
}

export interface FixResult {
  fix_id: string
  success: boolean
  error: string | null
  shopify_gid: string | null
  script_tag_id: string | null
  applied_at: string | null
}

export interface CopyPasteItem {
  label: string
  content: string
  fix_id: string
}

export interface BeforeAfterResponse {
  original_pillars: Record<string, PillarScore>
  current_pillars: Record<string, PillarScore>
  checks_improved: string[]
  checks_unchanged: string[]
  mcp_before: MCPResult[] | null
  mcp_after: MCPResult[] | null
  manual_action_items: Finding[]
}

export interface AgentRun {
  fixes_applied: number
  fixes_failed: number
  manual_action_items: Finding[]
  executed_fixes: FixResult[]
  failed_fixes: FixResult[]
  verification_results: Record<string, boolean>
  before_after: BeforeAfterResponse | null
}

export interface AuditReport {
  store_name: string
  store_domain: string
  ingestion_mode: 'url_only' | 'admin_token'
  total_products: number
  ai_readiness_score: number
  pillars: Record<string, PillarScore>
  findings: Finding[]
  worst_5_products: ProductSummary[]
  all_products?: ProductSummary[]
  channel_compliance: ChannelCompliance
  perception_diff: PerceptionDiff | null
  product_perceptions: ProductPerception[]
  mcp_simulation: MCPResult[] | null
  query_match_results: QueryMatchResult[]
  competitor_comparison: CompetitorResult[]
  copy_paste_package: CopyPasteItem[]
  agent_run?: AgentRun
}

export interface QueryMatchResponse {
  query: string
  matched_product_ids: string[]
  total_products: number
  match_count: number
  failing_attributes: Record<string, number>
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Request failed')
  }
  return res.json()
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Request failed')
  }
  return res.json()
}

export const api = {
  analyze: (req: AnalyzeRequest) => post<AnalyzeResponse>('/analyze', req),
  getJob: (jobId: string) => get<JobStatusResponse>(`/jobs/${jobId}`),
  queryMatch: (jobId: string, query: string) =>
    get<QueryMatchResponse>(`/jobs/${jobId}/query-match?query=${encodeURIComponent(query)}`),
  getFixPlan: (jobId: string) => get<FixPlanResponse>(`/jobs/${jobId}/fix-plan`),
  execute: (jobId: string, req: ExecuteRequest) => post<ExecuteResponse>(`/jobs/${jobId}/execute`, req),
  getBeforeAfter: (jobId: string) => get<BeforeAfterResponse>(`/jobs/${jobId}/before-after`),
}
