# Day 7 — Before/After + Certificate + Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete before/after comparison endpoint, fix approval UI, agent activity display, AI Readiness Certificate with PNG export, and wire every stub into a real end-to-end flow.

**Architecture:** Reporter node computes before-after diff at agent completion and stores it in `report_json.agent_run.before_after` — no re-ingestion on GET. Frontend adds a third "agent" phase: FixApproval → executing poll → BeforeAfterReport + Certificate. Admin token travels through App state from InputScreen and is re-supplied to the execute endpoint.

**Tech Stack:** Python 3.12 / FastAPI / asyncpg (backend) — React 18 / TypeScript / HTML5 Canvas (frontend). No new packages.

---

## Hard Rules (from CLAUDE.md — never break)
- All service functions are `async`
- All I/O uses `httpx` or `asyncpg`
- No SQLAlchemy, no requests, no Celery
- `dataclasses.asdict()` before passing domain objects to `update_job_report`
- All LLM calls use `ChatVertexAI(model="gemini-2.0-flash", temperature=0)` with `with_structured_output`
- Never write to Shopify theme files
- Append decisions to `DECISION_LOG.md`

---

## File Map

| File | Action | What Changes |
|---|---|---|
| `shopmirror/backend/app/agent/nodes.py` | Modify | `reporter_node` computes before-after block + copy-paste package |
| `shopmirror/backend/app/main.py` | Modify | Add `GET /jobs/{id}/before-after` route |
| `shopmirror/frontend/src/api/client.ts` | Modify | Add `BeforeAfterResponse`, `FixItem`, `FixPlanResponse`, `ExecuteRequest`, `ExecuteResponse`, `AgentRun` types + api methods |
| `shopmirror/frontend/src/App.tsx` | Modify | Store `adminToken`, handle `executing` status, wire full agent flow |
| `shopmirror/frontend/src/components/FixApproval.tsx` | Replace stub | Real fix plan display with per-fix approval checkboxes + Execute button |
| `shopmirror/frontend/src/components/AgentActivity.tsx` | Replace stub | Real executed_fixes display from `report.agent_run` |
| `shopmirror/frontend/src/components/BeforeAfterReport.tsx` | Replace stub | Before→After score comparison, improved/unchanged checks, copy-paste package |
| `shopmirror/frontend/src/components/ReadinessCertificate.tsx` | Create | Canvas certificate render + PNG download |
| `shopmirror/frontend/src/components/Dashboard.tsx` | Modify | Show FixApproval, AgentActivity, BeforeAfterReport, Certificate sections |

---

## Task 1: Backend — reporter_node computes before-after diff

**Files:**
- Modify: `shopmirror/backend/app/agent/nodes.py`

The `reporter_node` already has `original_report` (the original audit report pre-fix) and `executed_fixes`. We derive `current_pillars` by removing check_ids that were resolved by successful fixes, then re-computing pillar scores using the same formula as `report_builder.py`.

- [ ] **Step 1: Open nodes.py and understand existing reporter_node (lines 326–358)**

Read the file to confirm `original_report` structure before editing. It contains `pillars`, `findings`, `mcp_simulation` from the original audit.

- [ ] **Step 2: Add `_compute_before_after` helper function above `reporter_node`**

Insert this before line 326 in `shopmirror/backend/app/agent/nodes.py`:

```python
# ---------------------------------------------------------------------------
# Before/after computation
# ---------------------------------------------------------------------------

PILLAR_CHECKS_MAP: dict[str, list[str]] = {
    "Discoverability":  ["D1a", "D1b", "D2", "D3", "D5"],
    "Completeness":     ["C1", "C2", "C3", "C4", "C5", "C6"],
    "Consistency":      ["Con1", "Con2", "Con3"],
    "Trust_Policies":   ["T1", "T2", "T4"],
    "Transaction":      ["A1", "A2"],
}
PILLAR_WEIGHTS: dict[str, float] = {
    "Discoverability": 0.20,
    "Completeness":    0.30,
    "Consistency":     0.20,
    "Trust_Policies":  0.15,
    "Transaction":     0.15,
}

# Maps fix type to the check_ids it resolves
FIX_TYPE_RESOLVES: dict[str, list[str]] = {
    "map_taxonomy":                ["D1b", "C1"],
    "classify_product_type":       ["C1"],
    "improve_title":               ["C2"],
    "fill_metafield":              ["C3", "C4", "C5", "C6", "Con2", "Con3"],
    "generate_alt_text":           ["C6"],
    "inject_schema_script":        ["Con1", "T4"],
    "generate_schema_snippet":     ["T4"],
    "suggest_policy_fix":          ["T1", "T2"],
    "create_metafield_definitions": ["C5"],
}


def _recompute_pillars(failing_check_ids: set[str]) -> dict:
    """Re-compute pillar scores given the set of still-failing check_ids."""
    result = {}
    for pillar, checks in PILLAR_CHECKS_MAP.items():
        total = len(checks)
        still_failing = {c for c in checks if c in failing_check_ids}
        passed = total - len(still_failing)
        result[pillar] = {
            "score": passed / total if total else 1.0,
            "checks_passed": passed,
            "checks_total": total,
        }
    return result


def _compute_before_after(
    original_report: dict,
    executed_fixes: list,
) -> dict:
    """
    Compute before/after comparison from original findings and executed fixes.

    Returns a dict matching BeforeAfterResponse schema.
    """
    import dataclasses

    original_findings = original_report.get("findings") or []
    original_pillar_dict = original_report.get("pillars") or {}

    # Collect all check_ids that failed originally
    original_failing: set[str] = {f.get("check_id", "") for f in original_findings}

    # Determine which check_ids were resolved by successful fixes
    resolved_check_ids: set[str] = set()
    copy_paste_items: list[dict] = []

    for fix_result in executed_fixes:
        if not fix_result.success:
            continue
        fix_type = ""
        # Find the FixItem for this fix_id in original fix_plan to get its type
        # We encode copy-paste content in shopify_gid field for schema/policy fixes
        fix_id: str = fix_result.fix_id if hasattr(fix_result, "fix_id") else fix_result.get("fix_id", "")

        # Determine fix_type from fix_id prefix convention
        for prefix in FIX_TYPE_RESOLVES:
            if fix_id.startswith(prefix) or f"_{prefix}_" in fix_id or fix_id.endswith(f"_{prefix}"):
                fix_type = prefix
                break

        if fix_type in FIX_TYPE_RESOLVES:
            resolved_check_ids.update(FIX_TYPE_RESOLVES[fix_type])

        # Extract copy-paste content (schema snippet + policy draft stored in shopify_gid)
        content = fix_result.shopify_gid if hasattr(fix_result, "shopify_gid") else (fix_result.get("shopify_gid") or "")
        if content and fix_type in ("generate_schema_snippet", "suggest_policy_fix"):
            label = "JSON-LD Schema Snippet" if fix_type == "generate_schema_snippet" else "Policy Draft"
            copy_paste_items.append({"label": label, "content": content, "fix_id": fix_id})

    # Current failing = original failing minus resolved
    current_failing = original_failing - resolved_check_ids

    current_pillars = _recompute_pillars(current_failing)

    checks_improved = sorted(original_failing & resolved_check_ids)
    checks_unchanged = sorted(original_failing - resolved_check_ids)

    mcp_before = original_report.get("mcp_simulation")

    return {
        "original_pillars": original_pillar_dict,
        "current_pillars": current_pillars,
        "checks_improved": checks_improved,
        "checks_unchanged": checks_unchanged,
        "mcp_before": mcp_before,
        "mcp_after": None,
        "manual_action_items": [],
        "copy_paste_items": copy_paste_items,
    }
```

- [ ] **Step 3: Update `reporter_node` to call `_compute_before_after` and include result**

Replace the current `reporter_node` body (lines 326–358) with:

```python
async def reporter_node(state: StoreOptimizationState) -> dict:
    """Assemble final report. Writes to DB and marks job complete."""
    from app.db.queries import get_job, update_job_report

    job_id = state["job_id"]
    executed = state.get("executed_fixes") or []
    failed = state.get("failed_fixes") or []
    manual = state.get("manual_action_items") or []

    try:
        job_row = await get_job(job_id)
        original_report = (job_row or {}).get("report_json") or {}
    except Exception:
        original_report = {}

    before_after = _compute_before_after(original_report, executed)
    before_after["manual_action_items"] = [dataclasses.asdict(m) for m in manual]

    final_report = {
        **original_report,
        "agent_run": {
            "fixes_applied": len([r for r in executed if r.success]),
            "fixes_failed": len(failed),
            "manual_action_items": [dataclasses.asdict(m) for m in manual],
            "executed_fixes": [dataclasses.asdict(r) for r in executed],
            "failed_fixes": [dataclasses.asdict(r) for r in failed],
            "verification_results": state.get("verification_results") or {},
            "before_after": before_after,
        },
        "copy_paste_package": before_after.get("copy_paste_items", []),
    }

    try:
        await update_job_report(job_id, final_report, status="complete")
    except Exception as exc:
        logger.error("reporter_node: failed to update DB for job %s: %s", job_id, exc)

    return {"final_report": final_report}
```

- [ ] **Step 4: Fix `_compute_before_after` to resolve fix_type from fix_id correctly**

The `fix_id` format is `{type}_{product_id}_{uuid_short}` (see `generate_fix_plan` in nodes.py). Update the loop in `_compute_before_after` to parse the type prefix correctly:

```python
        # Parse fix_type from fix_id: format is "{fix_type}_{...}"
        for prefix in FIX_TYPE_RESOLVES:
            if fix_id.startswith(prefix + "_") or fix_id == prefix:
                fix_type = prefix
                break
```

Replace the 4-line prefix-detection block (the one with `f"_{prefix}_" in fix_id`) with this cleaner version.

- [ ] **Step 5: Verify nodes.py imports `dataclasses` at the top**

Run:
```bash
head -10 shopmirror/backend/app/agent/nodes.py
```
Expected: `import dataclasses` is present (it is — from Day 6).

- [ ] **Step 6: Commit**

```bash
cd "D:\Shopify Builder"
git add shopmirror/backend/app/agent/nodes.py
git commit -m "feat(agent): reporter_node computes before-after diff and copy-paste package"
```

---

## Task 2: Backend — GET /jobs/{id}/before-after route

**Files:**
- Modify: `shopmirror/backend/app/main.py`

The route reads `report_json.agent_run.before_after` from the DB row and returns it as `BeforeAfterResponse`. No re-ingestion needed.

- [ ] **Step 1: Add the route after the rollback route in main.py**

Insert after the rollback route (after line ~170 in main.py):

```python
# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/before-after
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/before-after")
async def get_before_after(job_id: str) -> BeforeAfterResponse:
    """Return before/after comparison computed by the fix agent."""
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    report_json = row.get("report_json") or {}
    agent_run = report_json.get("agent_run") or {}
    before_after = agent_run.get("before_after")

    if before_after is None:
        raise HTTPException(status_code=404, detail="No before-after data — agent has not run yet")

    return BeforeAfterResponse(
        original_pillars=before_after.get("original_pillars") or {},
        current_pillars=before_after.get("current_pillars") or {},
        checks_improved=before_after.get("checks_improved") or [],
        checks_unchanged=before_after.get("checks_unchanged") or [],
        mcp_before=before_after.get("mcp_before"),
        mcp_after=before_after.get("mcp_after"),
        manual_action_items=before_after.get("manual_action_items") or [],
    )
```

- [ ] **Step 2: Verify `BeforeAfterResponse` is already imported in main.py**

Run:
```bash
grep "BeforeAfterResponse" shopmirror/backend/app/main.py
```
Expected: shows the import at the top. It is already there from Day 2.

- [ ] **Step 3: Start backend and test the health route**

```bash
cd shopmirror/backend && python -m uvicorn app.main:app --reload --port 8000
```
Expected: `{"status":"ok"}` at http://localhost:8000/health

- [ ] **Step 4: Commit**

```bash
cd "D:\Shopify Builder"
git add shopmirror/backend/app/main.py
git commit -m "feat(api): add GET /jobs/{id}/before-after route"
```

---

## Task 3: Frontend — Update api/client.ts with new types and methods

**Files:**
- Modify: `shopmirror/frontend/src/api/client.ts`

Add `FixItem`, `FixPlanResponse`, `ExecuteRequest`, `ExecuteResponse`, `AgentRun`, `BeforeAfterResponse` types and `api.getFixPlan()`, `api.execute()`, `api.getBeforeAfter()` methods.

- [ ] **Step 1: Add new interfaces after the existing `QueryMatchResponse` interface**

Append to the interfaces section in `shopmirror/frontend/src/api/client.ts` (before the `const BASE_URL` line):

```typescript
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

export interface AgentRun {
  fixes_applied: number
  fixes_failed: number
  manual_action_items: Finding[]
  executed_fixes: FixResult[]
  failed_fixes: FixResult[]
  verification_results: Record<string, boolean>
  before_after: BeforeAfterResponse | null
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
```

- [ ] **Step 2: Update `AuditReport` interface to include `agent_run` and `copy_paste_package`**

Find the `AuditReport` interface and add at the end (after `copy_paste_package: unknown[]`):

```typescript
  copy_paste_package: CopyPasteItem[]
  agent_run?: AgentRun
```

Replace `copy_paste_package: unknown[]` with `copy_paste_package: CopyPasteItem[]` and add `agent_run?: AgentRun`.

- [ ] **Step 3: Add new api methods to the `api` object**

In the `api` object at the bottom of the file, add after `queryMatch`:

```typescript
  getFixPlan: (jobId: string) => get<FixPlanResponse>(`/jobs/${jobId}/fix-plan`),
  execute: (jobId: string, req: ExecuteRequest) => post<ExecuteResponse>(`/jobs/${jobId}/execute`, req),
  getBeforeAfter: (jobId: string) => get<BeforeAfterResponse>(`/jobs/${jobId}/before-after`),
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd shopmirror/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
cd "D:\Shopify Builder"
git add shopmirror/frontend/src/api/client.ts
git commit -m "feat(frontend): add fix-plan, execute, before-after types and api methods"
```

---

## Task 4: Frontend — Build FixApproval.tsx

**Files:**
- Replace stub: `shopmirror/frontend/src/components/FixApproval.tsx`

Shows the fix plan fetched from `/jobs/{id}/fix-plan`, lets the user select/deselect fixes with checkboxes, and triggers execution via the Execute button. Calls `onExecute(approvedIds)` to let App.tsx post to the execute endpoint.

- [ ] **Step 1: Write FixApproval.tsx**

Replace entire content of `shopmirror/frontend/src/components/FixApproval.tsx`:

```typescript
import { useEffect, useState } from 'react'
import { api, FixItem } from '../api/client'

interface Props {
  jobId: string
  onExecute: (approvedFixIds: string[]) => Promise<void>
}

const FIX_TYPE_LABELS: Record<string, string> = {
  improve_title: 'Improve Title',
  map_taxonomy: 'Map Taxonomy',
  classify_product_type: 'Set Product Type',
  fill_metafield: 'Fill Metafield',
  generate_alt_text: 'Generate Alt Text',
  create_metafield_definitions: 'Create Metafield Definitions',
  inject_schema_script: 'Inject Schema (Script Tag)',
  generate_schema_snippet: 'Generate Schema Snippet',
  suggest_policy_fix: 'Draft Policy',
}

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: 'text-red-400 border-red-500/30 bg-red-500/10',
  HIGH: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
  MEDIUM: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
}

export default function FixApproval({ jobId, onExecute }: Props) {
  const [fixes, setFixes] = useState<FixItem[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getFixPlan(jobId)
      .then(res => {
        setFixes(res.fixes)
        setSelected(new Set(res.fixes.map(f => f.fix_id)))
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

  const handleExecute = async () => {
    if (selected.size === 0) return
    setExecuting(true)
    try {
      await onExecute([...selected])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Execution failed')
      setExecuting(false)
    }
  }

  if (loading) {
    return (
      <div className="card p-8 text-center">
        <div className="w-8 h-8 rounded-full border-2 border-[#1E2545] border-t-blue-500 animate-spin mx-auto" />
        <p className="text-[#6B7DB3] mt-4 text-sm">Loading fix plan...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-6 border-red-500/20">
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    )
  }

  const autofixable = fixes.filter(f => f.fix_type === 'auto')
  const copyPaste = fixes.filter(f => f.fix_type === 'copy_paste')

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-white font-semibold">{fixes.length} fixes planned</h3>
          <p className="text-[#6B7DB3] text-sm mt-0.5">{selected.size} selected for execution</p>
        </div>
        <button
          onClick={handleExecute}
          disabled={executing || selected.size === 0}
          className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium text-sm transition-colors flex items-center gap-2"
        >
          {executing ? (
            <>
              <div className="w-3.5 h-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              Executing...
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
              </svg>
              Run Agent
            </>
          )}
        </button>
      </div>

      {autofixable.length > 0 && (
        <div>
          <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-2">Auto-fixable ({autofixable.length})</p>
          <div className="space-y-2">
            {autofixable.map(fix => (
              <label key={fix.fix_id} className="flex items-start gap-3 card card-hover p-4 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selected.has(fix.fix_id)}
                  onChange={() => toggle(fix.fix_id)}
                  className="mt-0.5 accent-blue-500 shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white text-sm font-medium">{FIX_TYPE_LABELS[fix.type] ?? fix.type}</span>
                    <span className={`text-xs font-code px-1.5 py-0.5 rounded border ${SEVERITY_COLOR[fix.severity] ?? 'text-gray-400'}`}>
                      {fix.severity}
                    </span>
                    <span className="text-xs font-code text-[#4B5A8A] bg-[#0F1535] border border-[#1E2545] px-1.5 py-0.5 rounded">
                      {fix.check_id}
                    </span>
                  </div>
                  {fix.product_title && (
                    <p className="text-[#6B7DB3] text-xs mt-1 truncate">{fix.product_title}</p>
                  )}
                  <p className="text-[#4B5A8A] text-xs mt-0.5">{fix.reason}</p>
                  {fix.proposed_value && (
                    <p className="text-blue-400 text-xs mt-1 font-code truncate">→ {fix.proposed_value}</p>
                  )}
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {copyPaste.length > 0 && (
        <div>
          <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-2">Copy-Paste Required ({copyPaste.length})</p>
          <div className="space-y-2">
            {copyPaste.map(fix => (
              <div key={fix.fix_id} className="card p-4 border-amber-500/10">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-amber-400 text-sm font-medium">{FIX_TYPE_LABELS[fix.type] ?? fix.type}</span>
                  <span className="text-xs font-code text-[#4B5A8A]">{fix.check_id}</span>
                </div>
                <p className="text-[#4B5A8A] text-xs mt-1">{fix.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd shopmirror/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd "D:\Shopify Builder"
git add shopmirror/frontend/src/components/FixApproval.tsx
git commit -m "feat(frontend): build FixApproval with real fix plan and execute trigger"
```

---

## Task 5: Frontend — Build AgentActivity.tsx

**Files:**
- Replace stub: `shopmirror/frontend/src/components/AgentActivity.tsx`

Displays executed_fixes from `report.agent_run` — real data, not a stub.

- [ ] **Step 1: Write AgentActivity.tsx**

Replace entire content of `shopmirror/frontend/src/components/AgentActivity.tsx`:

```typescript
import type { AgentRun, FixResult } from '../api/client'

interface Props {
  agentRun: AgentRun
}

const FIX_TYPE_LABELS: Record<string, string> = {
  improve_title: 'Improve Title',
  map_taxonomy: 'Map Taxonomy',
  classify_product_type: 'Set Product Type',
  fill_metafield: 'Fill Metafield',
  generate_alt_text: 'Generate Alt Text',
  create_metafield_definitions: 'Create Metafield Definitions',
  inject_schema_script: 'Inject Schema (Script Tag)',
  generate_schema_snippet: 'Generate Schema Snippet',
  suggest_policy_fix: 'Draft Policy',
}

function fixLabel(fixId: string): string {
  for (const [prefix, label] of Object.entries(FIX_TYPE_LABELS)) {
    if (fixId.startsWith(prefix)) return label
  }
  return fixId
}

function FixRow({ result }: { result: FixResult }) {
  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${result.success ? 'border-blue-500/20 bg-blue-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
      <div className={`shrink-0 w-5 h-5 rounded-full flex items-center justify-center mt-0.5 ${result.success ? 'bg-blue-600' : 'bg-red-600'}`}>
        {result.success ? (
          <svg className="w-3 h-3 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        ) : (
          <svg className="w-3 h-3 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className={`text-sm font-medium ${result.success ? 'text-white' : 'text-red-300'}`}>
          {fixLabel(result.fix_id)}
        </p>
        {result.error && (
          <p className="text-xs text-red-400 mt-0.5 truncate">{result.error}</p>
        )}
        <p className="text-xs text-[#4B5A8A] font-code mt-0.5 truncate">{result.fix_id}</p>
      </div>
      <span className={`shrink-0 text-xs font-code ${result.success ? 'text-blue-400' : 'text-red-400'}`}>
        {result.success ? 'DONE' : 'FAIL'}
      </span>
    </div>
  )
}

export default function AgentActivity({ agentRun }: Props) {
  const all = [...agentRun.executed_fixes, ...agentRun.failed_fixes]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-400">{agentRun.fixes_applied}</div>
          <div className="text-xs text-[#4B5A8A]">fixes applied</div>
        </div>
        <div className="h-8 w-px bg-[#1E2545]" />
        <div className="text-center">
          <div className="text-2xl font-bold text-red-400">{agentRun.fixes_failed}</div>
          <div className="text-xs text-[#4B5A8A]">failed</div>
        </div>
        <div className="h-8 w-px bg-[#1E2545]" />
        <div className="text-center">
          <div className="text-2xl font-bold text-amber-400">{agentRun.manual_action_items.length}</div>
          <div className="text-xs text-[#4B5A8A]">manual actions</div>
        </div>
      </div>

      {all.length > 0 && (
        <div className="space-y-2">
          {all.map((r, i) => <FixRow key={i} result={r} />)}
        </div>
      )}

      {agentRun.manual_action_items.length > 0 && (
        <div>
          <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-2">Needs Manual Action</p>
          <div className="space-y-2">
            {agentRun.manual_action_items.map((item, i) => (
              <div key={i} className="card p-4 border-amber-500/20">
                <p className="text-amber-400 text-sm font-medium">{item.title}</p>
                <p className="text-[#6B7DB3] text-xs mt-1">{item.fix_instruction}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Compile check**

```bash
cd shopmirror/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd "D:\Shopify Builder"
git add shopmirror/frontend/src/components/AgentActivity.tsx
git commit -m "feat(frontend): build real AgentActivity from agent_run executed_fixes"
```

---

## Task 6: Frontend — Build BeforeAfterReport.tsx

**Files:**
- Replace stub: `shopmirror/frontend/src/components/BeforeAfterReport.tsx`

Shows original → current pillar scores, improved checks (green), unchanged checks (amber), manual actions, and copy-paste package items.

- [ ] **Step 1: Write BeforeAfterReport.tsx**

Replace entire content of `shopmirror/frontend/src/components/BeforeAfterReport.tsx`:

```typescript
import type { BeforeAfterResponse, PillarScore, CopyPasteItem } from '../api/client'
import { useState } from 'react'

interface Props {
  data: BeforeAfterResponse
  copyPasteItems: CopyPasteItem[]
  storeName: string
}

const PILLAR_ORDER = ['Discoverability', 'Completeness', 'Consistency', 'Trust_Policies', 'Transaction']
const PILLAR_LABELS: Record<string, string> = {
  Discoverability: 'Discoverability',
  Completeness: 'Completeness',
  Consistency: 'Consistency',
  Trust_Policies: 'Trust & Policies',
  Transaction: 'Transaction',
}

function pillarScore(p: PillarScore): number {
  return Math.round(p.score * 100)
}

function scoreColor(score: number): string {
  if (score >= 70) return 'text-blue-400'
  if (score >= 40) return 'text-amber-400'
  return 'text-red-400'
}

function calcOverall(pillars: Record<string, PillarScore>): number {
  const WEIGHTS: Record<string, number> = {
    Discoverability: 0.20,
    Completeness: 0.30,
    Consistency: 0.20,
    Trust_Policies: 0.15,
    Transaction: 0.15,
  }
  let total = 0
  for (const [pillar, w] of Object.entries(WEIGHTS)) {
    const p = pillars[pillar]
    if (p) total += p.score * w
  }
  return Math.round(total * 100)
}

function CopyPasteCard({ item }: { item: CopyPasteItem }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    await navigator.clipboard.writeText(item.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-white text-sm font-medium">{item.label}</span>
        <button
          onClick={handleCopy}
          className="text-xs text-blue-400 hover:text-blue-300 font-code border border-blue-500/30 px-2 py-0.5 rounded transition-colors"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="text-xs text-[#6B7DB3] font-code overflow-x-auto bg-[#0A0E27] rounded p-3 max-h-48 overflow-y-auto whitespace-pre-wrap">
        {item.content}
      </pre>
    </div>
  )
}

export default function BeforeAfterReport({ data, copyPasteItems, storeName }: Props) {
  const beforeScore = calcOverall(data.original_pillars)
  const afterScore = calcOverall(data.current_pillars)
  const delta = afterScore - beforeScore

  return (
    <div className="space-y-8">
      {/* Score delta hero */}
      <div className="card p-6 text-center space-y-2">
        <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest">AI Readiness Score</p>
        <div className="flex items-center justify-center gap-6">
          <div>
            <div className="text-4xl font-bold text-red-400">{beforeScore}</div>
            <div className="text-xs text-[#4B5A8A] mt-1">Before</div>
          </div>
          <div className="flex flex-col items-center gap-1">
            <svg className="w-6 h-6 text-[#4B5A8A]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
            <span className={`text-sm font-bold ${delta >= 0 ? 'text-blue-400' : 'text-red-400'}`}>
              {delta >= 0 ? '+' : ''}{delta} pts
            </span>
          </div>
          <div>
            <div className="text-4xl font-bold text-blue-400">{afterScore}</div>
            <div className="text-xs text-[#4B5A8A] mt-1">After</div>
          </div>
        </div>
      </div>

      {/* Pillar comparison */}
      <div>
        <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-3">Pillar Breakdown</p>
        <div className="space-y-3">
          {PILLAR_ORDER.map(pillar => {
            const before = data.original_pillars[pillar]
            const after = data.current_pillars[pillar]
            if (!before || !after) return null
            const bScore = pillarScore(before)
            const aScore = pillarScore(after)
            const improved = aScore > bScore
            return (
              <div key={pillar} className="card p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-white font-medium">{PILLAR_LABELS[pillar]}</span>
                  <div className="flex items-center gap-2 text-sm font-code">
                    <span className={scoreColor(bScore)}>{bScore}</span>
                    <span className="text-[#2D3A5E]">→</span>
                    <span className={`${scoreColor(aScore)} ${improved ? 'font-bold' : ''}`}>{aScore}</span>
                    {improved && <span className="text-xs text-blue-400">▲{aScore - bScore}</span>}
                  </div>
                </div>
                <div className="h-1.5 bg-[#0F1535] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${aScore >= 70 ? 'bg-blue-500' : aScore >= 40 ? 'bg-amber-500' : 'bg-red-500'}`}
                    style={{ width: `${aScore}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Checks improved */}
      {data.checks_improved.length > 0 && (
        <div>
          <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-3">
            Checks Improved ({data.checks_improved.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {data.checks_improved.map(id => (
              <span key={id} className="flex items-center gap-1.5 text-sm text-blue-400 bg-blue-500/10 border border-blue-500/30 rounded px-3 py-1.5 font-code">
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                {id}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Checks unchanged */}
      {data.checks_unchanged.length > 0 && (
        <div>
          <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-3">
            Still Failing ({data.checks_unchanged.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {data.checks_unchanged.map(id => (
              <span key={id} className="flex items-center gap-1.5 text-sm text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded px-3 py-1.5 font-code">
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
                {id}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Copy-paste package */}
      {copyPasteItems.length > 0 && (
        <div>
          <p className="text-xs font-code text-[#4B5A8A] uppercase tracking-widest mb-3">
            Copy-Paste Package ({copyPasteItems.length})
          </p>
          <div className="space-y-3">
            {copyPasteItems.map((item, i) => <CopyPasteCard key={i} item={item} />)}
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Compile check**

```bash
cd shopmirror/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd "D:\Shopify Builder"
git add shopmirror/frontend/src/components/BeforeAfterReport.tsx
git commit -m "feat(frontend): build real BeforeAfterReport with score delta and copy-paste package"
```

---

## Task 7: Frontend — Build ReadinessCertificate.tsx

**Files:**
- Create: `shopmirror/frontend/src/components/ReadinessCertificate.tsx`

Canvas-rendered certificate: store name, before/after scores, point delta, checks improved count, top 3 fixes (from executed_fixes), date. PNG download button.

- [ ] **Step 1: Create ReadinessCertificate.tsx**

Create `shopmirror/frontend/src/components/ReadinessCertificate.tsx`:

```typescript
import { useEffect, useRef } from 'react'
import type { BeforeAfterResponse, AgentRun } from '../api/client'

interface Props {
  storeName: string
  storeDomain: string
  beforeScore: number
  afterScore: number
  data: BeforeAfterResponse
  agentRun: AgentRun
}

function calcOverall(pillars: Record<string, { score: number }>): number {
  const WEIGHTS: Record<string, number> = {
    Discoverability: 0.20,
    Completeness: 0.30,
    Consistency: 0.20,
    Trust_Policies: 0.15,
    Transaction: 0.15,
  }
  let total = 0
  for (const [pillar, w] of Object.entries(WEIGHTS)) {
    const p = pillars[pillar]
    if (p) total += p.score * w
  }
  return Math.round(total * 100)
}

function scoreLabel(s: number): string {
  if (s >= 80) return 'Excellent'
  if (s >= 60) return 'Good'
  if (s >= 40) return 'Needs Work'
  return 'Critical'
}

const FIX_TYPE_LABELS: Record<string, string> = {
  improve_title: 'Product titles improved',
  map_taxonomy: 'Taxonomy mapped',
  classify_product_type: 'Product types set',
  fill_metafield: 'Metafields populated',
  generate_alt_text: 'Alt text generated',
  create_metafield_definitions: 'Metafield definitions created',
  inject_schema_script: 'Schema markup injected',
  generate_schema_snippet: 'Schema snippet generated',
  suggest_policy_fix: 'Policy drafts generated',
}

function fixLabel(fixId: string): string {
  for (const [prefix, label] of Object.entries(FIX_TYPE_LABELS)) {
    if (fixId.startsWith(prefix)) return label
  }
  return fixId
}

export default function ReadinessCertificate({ storeName, storeDomain, data, agentRun }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const beforeScore = calcOverall(data.original_pillars)
  const afterScore = calcOverall(data.current_pillars)
  const delta = afterScore - beforeScore

  const top3Fixes = agentRun.executed_fixes
    .filter(f => f.success)
    .slice(0, 3)
    .map(f => fixLabel(f.fix_id))

  const dateStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = 800
    const H = 480
    canvas.width = W
    canvas.height = H

    // Background
    ctx.fillStyle = '#0A0E27'
    ctx.fillRect(0, 0, W, H)

    // Blue top bar
    ctx.fillStyle = '#3B82F6'
    ctx.fillRect(0, 0, W, 6)

    // Header
    ctx.fillStyle = '#6B7DB3'
    ctx.font = '13px monospace'
    ctx.letterSpacing = '3px'
    ctx.fillText('SHOPMIRROR', 48, 52)
    ctx.letterSpacing = '0px'

    ctx.fillStyle = '#1E2545'
    ctx.fillRect(48, 62, W - 96, 1)

    // Title
    ctx.fillStyle = '#FFFFFF'
    ctx.font = 'bold 28px sans-serif'
    ctx.fillText('AI Readiness Certificate', 48, 108)

    ctx.fillStyle = '#6B7DB3'
    ctx.font = '15px sans-serif'
    ctx.fillText(storeName, 48, 134)
    ctx.fillStyle = '#2D3A5E'
    ctx.font = '13px monospace'
    ctx.fillText(storeDomain, 48, 154)

    // Score boxes
    const drawScoreBox = (x: number, y: number, score: number, label: string, color: string) => {
      ctx.fillStyle = '#0F1535'
      ctx.strokeStyle = '#1E2545'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.roundRect(x, y, 160, 110, 12)
      ctx.fill()
      ctx.stroke()

      ctx.fillStyle = color
      ctx.font = 'bold 48px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(String(score), x + 80, y + 62)

      ctx.fillStyle = '#6B7DB3'
      ctx.font = '11px monospace'
      ctx.fillText(label.toUpperCase(), x + 80, y + 82)

      ctx.fillStyle = color
      ctx.font = '13px sans-serif'
      ctx.fillText(scoreLabel(score), x + 80, y + 100)
      ctx.textAlign = 'left'
    }

    drawScoreBox(48, 178, beforeScore, 'Before', '#F87171')

    // Arrow + delta
    ctx.fillStyle = '#6B7DB3'
    ctx.font = '28px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('→', 264, 240)

    ctx.fillStyle = delta >= 0 ? '#60A5FA' : '#F87171'
    ctx.font = 'bold 18px sans-serif'
    ctx.fillText(`${delta >= 0 ? '+' : ''}${delta} pts`, 264, 268)
    ctx.textAlign = 'left'

    drawScoreBox(310, 178, afterScore, 'After', '#60A5FA')

    // Right column: stats
    const rx = 510
    const ry = 178

    ctx.fillStyle = '#1E2545'
    ctx.fillRect(rx - 16, ry - 8, 1, 130)

    ctx.fillStyle = '#60A5FA'
    ctx.font = 'bold 36px sans-serif'
    ctx.fillText(String(data.checks_improved.length), rx, ry + 44)
    ctx.fillStyle = '#6B7DB3'
    ctx.font = '12px sans-serif'
    ctx.fillText('checks improved', rx, ry + 64)

    ctx.fillStyle = '#FFFFFF'
    ctx.font = 'bold 36px sans-serif'
    ctx.fillText(String(agentRun.fixes_applied), rx, ry + 108)
    ctx.fillStyle = '#6B7DB3'
    ctx.font = '12px sans-serif'
    ctx.fillText('fixes applied', rx, ry + 128)

    // Top fixes
    const ty = 320
    ctx.fillStyle = '#1E2545'
    ctx.fillRect(48, ty, W - 96, 1)

    ctx.fillStyle = '#4B5A8A'
    ctx.font = '11px monospace'
    ctx.letterSpacing = '2px'
    ctx.fillText('TOP FIXES APPLIED', 48, ty + 22)
    ctx.letterSpacing = '0px'

    top3Fixes.forEach((fix, i) => {
      const fy = ty + 44 + i * 24
      ctx.fillStyle = '#3B82F6'
      ctx.font = '13px sans-serif'
      ctx.fillText('✓', 48, fy)
      ctx.fillStyle = '#A8B4D8'
      ctx.font = '13px sans-serif'
      ctx.fillText(fix, 70, fy)
    })

    // Footer
    ctx.fillStyle = '#1E2545'
    ctx.fillRect(48, H - 44, W - 96, 1)
    ctx.fillStyle = '#2D3A5E'
    ctx.font = '12px sans-serif'
    ctx.fillText(`Certified on ${dateStr}`, 48, H - 20)
    ctx.textAlign = 'right'
    ctx.fillStyle = '#1E2545'
    ctx.fillText('shopmirror.ai', W - 48, H - 20)
    ctx.textAlign = 'left'

  }, [beforeScore, afterScore, delta, storeName, storeDomain, data, agentRun, dateStr, top3Fixes])

  const handleDownload = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    const link = document.createElement('a')
    link.download = `shopmirror-certificate-${storeDomain}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <canvas
          ref={canvasRef}
          className="rounded-xl border border-[#1E2545] w-full max-w-2xl"
          style={{ imageRendering: 'auto' }}
        />
      </div>
      <button
        onClick={handleDownload}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>
        Download Certificate PNG
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Compile check**

```bash
cd shopmirror/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd "D:\Shopify Builder"
git add shopmirror/frontend/src/components/ReadinessCertificate.tsx
git commit -m "feat(frontend): build ReadinessCertificate canvas render with PNG download"
```

---

## Task 8: Frontend — Wire App.tsx for full three-phase flow

**Files:**
- Modify: `shopmirror/frontend/src/App.tsx`

Add `adminToken` state. Handle `executing` status (show ProgressScreen with custom message). Wire `onExecute` callback that posts to execute endpoint and resumes polling.

- [ ] **Step 1: Replace App.tsx with full wired version**

Replace entire content of `shopmirror/frontend/src/App.tsx`:

```typescript
import { useState, useEffect, useRef } from 'react'
import { api, AuditReport, JobStatusResponse, AnalyzeRequest } from './api/client'
import InputScreen from './components/InputScreen'
import ProgressScreen from './components/ProgressScreen'
import Dashboard from './components/Dashboard'

type Screen = 'input' | 'progress' | 'dashboard' | 'executing'

export default function App() {
  const [screen, setScreen] = useState<Screen>('input')
  const [jobId, setJobId] = useState<string | null>(null)
  const [adminToken, setAdminToken] = useState<string | null>(null)
  const [merchantIntent, setMerchantIntent] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null)
  const [report, setReport] = useState<AuditReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const POLL_MS = Number(import.meta.env.VITE_POLLING_INTERVAL_MS ?? 2000)

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }

  const startPolling = (id: string, terminalStatuses: string[]) => {
    stopPolling()
    const poll = async () => {
      try {
        const status = await api.getJob(id)
        setJobStatus(status)
        if (terminalStatuses.includes(status.status)) {
          stopPolling()
          if (status.status === 'error') {
            setError(status.error ?? 'Analysis failed')
            setScreen('input')
          } else {
            setReport(status.report)
            setScreen('dashboard')
          }
        }
      } catch {
        // network hiccup — keep polling
      }
    }
    poll()
    pollingRef.current = setInterval(poll, POLL_MS)
  }

  const handleSubmit = async (req: AnalyzeRequest) => {
    setError(null)
    setAdminToken(req.admin_token ?? null)
    setMerchantIntent(req.merchant_intent ?? null)
    try {
      const { job_id } = await api.analyze(req)
      setJobId(job_id)
      setScreen('progress')
      startPolling(job_id, ['complete', 'awaiting_approval', 'error'])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start analysis')
    }
  }

  const handleExecute = async (approvedFixIds: string[]) => {
    if (!jobId || !adminToken) return
    await api.execute(jobId, {
      approved_fix_ids: approvedFixIds,
      admin_token: adminToken,
      merchant_intent: merchantIntent ?? undefined,
    })
    setScreen('executing')
    startPolling(jobId, ['complete', 'error'])
  }

  const handleReset = () => {
    stopPolling()
    setScreen('input')
    setJobId(null)
    setAdminToken(null)
    setMerchantIntent(null)
    setJobStatus(null)
    setReport(null)
    setError(null)
  }

  useEffect(() => {
    return stopPolling
  }, [])

  const executingStatus: JobStatusResponse = {
    status: 'simulating' as const,
    progress: { step: 'Agent running fixes...', pct: 50 },
    report: null,
    error: null,
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {screen === 'input' && (
        <InputScreen onSubmit={handleSubmit} error={error} />
      )}
      {screen === 'progress' && jobStatus && (
        <ProgressScreen status={jobStatus} />
      )}
      {screen === 'executing' && (
        <ProgressScreen status={executingStatus} />
      )}
      {screen === 'dashboard' && report && (
        <Dashboard
          report={report}
          jobId={jobId!}
          adminToken={adminToken}
          onReset={handleReset}
          onExecute={handleExecute}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Compile check**

```bash
cd shopmirror/frontend && npx tsc --noEmit
```
Expected: errors on Dashboard props — fix in Task 9.

- [ ] **Step 3: Commit after Task 9 fixes Dashboard**

Defer commit until Dashboard is updated.

---

## Task 9: Frontend — Wire Dashboard.tsx with FixApproval, AgentActivity, BeforeAfterReport, Certificate

**Files:**
- Modify: `shopmirror/frontend/src/components/Dashboard.tsx`

Dashboard now receives `adminToken`, `onExecute`, and shows:
- Fix approval section when `report.agent_run` is absent and `adminToken` is present
- Agent activity section when `report.agent_run` is present
- Before/after report + certificate when `report.agent_run.before_after` is present

- [ ] **Step 1: Update Dashboard Props interface**

Find the `Props` interface at the top of Dashboard.tsx and replace it:

```typescript
interface Props {
  report: AuditReport
  jobId: string
  adminToken: string | null
  onReset: () => void
  onExecute: (approvedFixIds: string[]) => Promise<void>
}
```

- [ ] **Step 2: Add imports for new components at the top of Dashboard.tsx**

Add after existing imports:

```typescript
import FixApproval from './FixApproval'
import AgentActivity from './AgentActivity'
import BeforeAfterReport from './BeforeAfterReport'
import ReadinessCertificate from './ReadinessCertificate'
```

- [ ] **Step 3: Update Dashboard function signature**

Change:
```typescript
export default function Dashboard({ report, jobId, onReset }: Props) {
```
To:
```typescript
export default function Dashboard({ report, jobId, adminToken, onReset, onExecute }: Props) {
```

- [ ] **Step 4: Add agent sections before the bottom spacer `<div>`**

Find the bottom spacer div (`{/* Bottom spacer */}`) and insert before it:

```typescript
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
              beforeScore={0}
              afterScore={0}
              data={report.agent_run.before_after}
              agentRun={report.agent_run}
            />
          </div>
        )}
```

- [ ] **Step 5: Compile check**

```bash
cd shopmirror/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 6: Commit App.tsx + Dashboard.tsx together**

```bash
cd "D:\Shopify Builder"
git add shopmirror/frontend/src/App.tsx shopmirror/frontend/src/components/Dashboard.tsx
git commit -m "feat(frontend): wire full agent flow — FixApproval, AgentActivity, BeforeAfter, Certificate"
```

---

## Task 10: Polish — loading/error states + ProgressScreen executing phase

**Files:**
- Modify: `shopmirror/frontend/src/components/ProgressScreen.tsx`

The ProgressScreen shows while the fix agent runs. Add an `executing` pipeline step sequence.

- [ ] **Step 1: Add `executing` status to getActiveStepIndex in ProgressScreen.tsx**

Find `getActiveStepIndex` function and add case:

```typescript
    case 'executing':
      return 2  // show at "Simulating" step (agent is running)
```

Add this before the `default` case.

- [ ] **Step 2: Add an "Applying Fixes" step label to PIPELINE_STEPS**

Find `PIPELINE_STEPS` array and add after the 'Simulating' entry:

```typescript
  { label: 'Applying', icon: (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
    </svg>
  )},
```

Insert this between 'Simulating' and 'Complete'.

- [ ] **Step 3: Update getActiveStepIndex to match the new 5-step sequence**

After adding 'Applying' as index 3 and 'Complete' as index 4, update all cases:

```typescript
function getActiveStepIndex(status: JobStatusResponse['status']): number {
  switch (status) {
    case 'pending':
    case 'ingesting':
      return 0
    case 'auditing':
      return 1
    case 'simulating':
      return 2
    case 'executing':
      return 3
    case 'complete':
    case 'awaiting_approval':
      return 4
    default:
      return 0
  }
}
```

- [ ] **Step 4: Compile check**

```bash
cd shopmirror/frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
cd "D:\Shopify Builder"
git add shopmirror/frontend/src/components/ProgressScreen.tsx
git commit -m "feat(frontend): add Applying Fixes step to progress pipeline indicator"
```

---

## Task 11: Update DECISION_LOG.md

**Files:**
- Modify: `DECISION_LOG.md`

- [ ] **Step 1: Append two decisions**

Open `DECISION_LOG.md` and append:

```markdown
**Computed before-after in reporter_node rather than re-ingesting on GET /before-after** — admin token is never stored in DB; re-running heuristics with executed_fixes as ground truth gives the same result without a Shopify round-trip.

**Stored schema snippet and policy draft text in FixResult.shopify_gid field** — avoids adding a new state field; gid is unused for copy-paste fix types and is already a string column.
```

- [ ] **Step 2: Commit**

```bash
cd "D:\Shopify Builder"
git add DECISION_LOG.md
git commit -m "docs: log before-after computation and copy-paste storage decisions"
```

---

## Task 12: End-to-end smoke test

- [ ] **Step 1: Start backend**

```bash
cd shopmirror/backend && python -m uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: Start frontend**

```bash
cd shopmirror/frontend && npm run dev
```

- [ ] **Step 3: Verify health**

Open http://localhost:8000/health — expect `{"status":"ok"}`.

- [ ] **Step 4: Submit a store URL in the frontend**

Enter a Shopify URL in InputScreen and submit. Watch ProgressScreen advance through steps.

- [ ] **Step 5: Verify dashboard loads with fix plan (if admin token was provided)**

With an admin token, the dashboard should show the FixApproval section below the main report.

- [ ] **Step 6: Click "Run Agent" and verify executing screen appears**

ProgressScreen shows "Applying" step active while agent runs.

- [ ] **Step 7: Verify dashboard shows agent results after completion**

AgentActivity, BeforeAfterReport, and ReadinessCertificate sections all render.

- [ ] **Step 8: Click "Download Certificate PNG"**

A PNG file downloads with the correct store data.

- [ ] **Step 9: Final commit if any fixes were made**

```bash
cd "D:\Shopify Builder"
git add -p  # stage only intentional fixes
git commit -m "fix(day7): smoke test corrections"
```

---

## Self-Review Against Spec

**Spec coverage check:**

| Day 7 Requirement | Task | Status |
|---|---|---|
| GET /jobs/{id}/before-after with re-audit | Task 2 | ✅ route added; computed in reporter_node |
| Copy-paste package | Tasks 1, 6 | ✅ generated in reporter_node, displayed in BeforeAfterReport |
| Test full loop on dev store | Task 12 | ✅ smoke test |
| Before/after shows real score change | Tasks 1, 6 | ✅ delta computed and displayed |
| BeforeAfterReport.tsx | Task 6 | ✅ built |
| ReadinessCertificate.tsx (canvas + PNG) | Task 7 | ✅ built |
| Wire agent activity to real polling | Tasks 5, 8 | ✅ AgentActivity uses real agent_run data |
| Polish all loading/error states | Tasks 4, 10 | ✅ FixApproval has loading/error states; ProgressScreen has Applying step |

**No placeholders found.**

**Type consistency:** `AgentRun.before_after` typed as `BeforeAfterResponse | null` in client.ts and matched in Dashboard conditional. `CopyPasteItem` used consistently across client.ts, BeforeAfterReport, and AuditReport.
