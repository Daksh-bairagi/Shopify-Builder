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

// Status values that the backend actually emits. 'error' was historical and is not used —
// backend writes 'failed' on any error path via update_job_error.
export type JobStatus =
  | 'pending'
  | 'queued'
  | 'ingesting'
  | 'auditing'
  | 'simulating'
  | 'complete'
  | 'awaiting_approval'
  | 'executing'
  | 'failed'

export interface JobStatusResponse {
  status: JobStatus
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
  status: 'READY' | 'PARTIAL' | 'BLOCKED' | 'NOT_READY'
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

export interface CompetitorAudit {
  url: string
  store_domain: string
  check_results: Record<string, boolean>
}

export interface CompetitorResult {
  competitor: CompetitorAudit
  gaps: string[]
}

export interface CompetitorDiscoveryResponse {
  results: CompetitorResult[]
  status: string
  message: string
  mode: 'auto' | 'manual'
  scope_label: string
  candidates_considered: number
  audited_competitors: number
  notes: string[]
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
  display_label?: string
  rolled_back?: boolean
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
  competitor_comparison: CompetitorResult[]
  copy_paste_package: CopyPasteItem[]
  agent_run?: AgentRun
  bot_access?: Record<string, unknown>
  identifier_audit?: Record<string, unknown>
  golden_record?: Record<string, unknown>
  trust_signals?: Record<string, unknown>
  ai_visibility?: Record<string, unknown>
  feed_summaries?: Record<string, unknown>
  llms_txt_preview?: string
  scan_limited?: boolean
  full_product_count?: number
}

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
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
  const res = await fetch(`${API_BASE_URL}${path}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Request failed')
  }
  return res.json()
}

export const api = {
  analyze: (req: AnalyzeRequest) => post<AnalyzeResponse>('/analyze', req),
  getJob: (jobId: string) => get<JobStatusResponse>(`/jobs/${jobId}`),
  getFixPlan: (jobId: string) => get<FixPlanResponse>(`/jobs/${jobId}/fix-plan`),
  execute: (jobId: string, req: ExecuteRequest) => post<ExecuteResponse>(`/jobs/${jobId}/execute`, req),
  getBeforeAfter: (jobId: string) => get<BeforeAfterResponse>(`/jobs/${jobId}/before-after`),
  findCompetitors: (jobId: string, urls: string[] = []) =>
    post<CompetitorDiscoveryResponse>(`/jobs/${jobId}/competitors`, { competitor_urls: urls }),
  rollback: (jobId: string, fixId: string, adminToken: string) =>
    post<{ status: string; field: string; restored_value: string }>(
      `/jobs/${jobId}/rollback/${fixId}`,
      { admin_token: adminToken },
    ),
}
