"""
agent/nodes.py — LangGraph node functions for the fix agent.

Nodes:
  planner_node      — picks next approved fix from the plan
  approval_gate_node — pass-through (approvals already in initial state)
  executor_node     — dispatches the tool for current_fix_id
  verifier_node     — checks if the fix resolved the finding
  reporter_node     — assembles final report, writes to DB
"""

from __future__ import annotations

import dataclasses
import logging
import uuid
from typing import Literal

from app.agent.state import StoreOptimizationState
from app.agent.tools import dispatch_tool
from app.models.fixes import FixItem, FixResult
from app.models.findings import Finding

logger = logging.getLogger(__name__)

# Dependency order for fix type sorting (lower index = executed first)
DEPENDENCY_ORDER = [
    "map_taxonomy",
    "create_metafield_definitions",
    "classify_product_type",
    "improve_title",
    "fill_metafield",
    "generate_alt_text",
    "inject_schema_script",
    "generate_schema_snippet",
    "suggest_policy_fix",
]

SEVERITY_WEIGHT = {"CRITICAL": 10, "HIGH": 6, "MEDIUM": 2}


# ---------------------------------------------------------------------------
# Fix plan generation (called once by planner on first run)
# ---------------------------------------------------------------------------

CHECK_TO_FIX_TYPE: dict[str, str] = {
    # D1a = robots.txt/crawler check — no auto-fix, manual only; excluded from plan
    "D1b": "map_taxonomy",           # Missing Shopify Standard Taxonomy GID → map_taxonomy
    "C1":  "map_taxonomy",           # Taxonomy/product_type structural gap → map_taxonomy
    "C2":  "improve_title",          # Title missing category noun → improve_title
    "C3":  "fill_metafield",         # Missing structured attributes → fill_metafield
    "C4":  "fill_metafield",         # Missing GTIN/barcode → fill_metafield
    "C5":  "fill_metafield",         # Missing specifications → fill_metafield
    "C6":  "fill_metafield",         # Missing material → fill_metafield
    "Con1": "inject_schema_script",  # Missing/inconsistent schema markup → inject_schema_script
    "Con2": "fill_metafield",        # Metafield inconsistency → fill_metafield
    "Con3": "fill_metafield",        # SEO field inconsistency (Mode B) → fill_metafield
    "T1":  "suggest_policy_fix",     # No refund policy
    "T2":  "suggest_policy_fix",     # No shipping policy
    "T4":  "inject_schema_script",   # Missing JSON-LD schema markup
}

# Store-level fix types get a single fix item regardless of affected product count
STORE_LEVEL_TYPES = {"inject_schema_script", "create_metafield_definitions", "suggest_policy_fix"}


def generate_fix_plan(findings: list[Finding]) -> list[FixItem]:
    """Map audit findings to ordered FixItem list.

    Rules:
    - Product-level fix types: one FixItem per affected product per finding
    - Store-level fix types: one FixItem for the whole store, deduplicated
    - Sorted by DEPENDENCY_ORDER then severity_weight * affected_count desc
    """
    items: list[FixItem] = []
    seen_store_level: set[str] = set()

    for finding in findings:
        fix_type = CHECK_TO_FIX_TYPE.get(finding.check_id)
        if fix_type is None:
            continue

        if fix_type in STORE_LEVEL_TYPES:
            if fix_type in seen_store_level:
                continue
            seen_store_level.add(fix_type)
            items.append(FixItem(
                fix_id=str(uuid.uuid4()),
                type=fix_type,
                product_id="",
                product_title="(store-level)",
                field=finding.check_id,
                current_value=None,
                proposed_value=f"Fix for {finding.title}",
                reason=finding.detail,
                risk="LOW",
                reversible=fix_type != "suggest_policy_fix",
            ))
        else:
            for product_id in finding.affected_products[:20]:  # cap at 20 products per finding
                items.append(FixItem(
                    fix_id=str(uuid.uuid4()),
                    type=fix_type,
                    product_id=product_id,
                    product_title="",
                    field=finding.check_id,
                    current_value=None,
                    proposed_value=f"Fix for {finding.title}",
                    reason=finding.detail,
                    risk="LOW",
                    reversible=True,
                ))

    # Sort: primary by DEPENDENCY_ORDER index, secondary by severity weight desc
    severity_map = {f.check_id: SEVERITY_WEIGHT.get(f.severity, 3) * f.affected_count for f in findings}

    def sort_key(item: FixItem) -> tuple:
        dep_idx = DEPENDENCY_ORDER.index(item.type) if item.type in DEPENDENCY_ORDER else 99
        weight = severity_map.get(item.field, 0)
        return (dep_idx, -weight)

    items.sort(key=sort_key)
    return items


# ---------------------------------------------------------------------------
# planner_node
# ---------------------------------------------------------------------------

def planner_node(state: StoreOptimizationState) -> dict:
    """Pick the next approved fix to execute.

    On first run (fix_plan is empty), generates the plan from audit_findings.
    Routes: executor if there's a pending approved fix, reporter otherwise.
    """
    fix_plan = state.get("fix_plan") or []
    approved_ids = set(state.get("approved_fix_ids") or [])
    executed_ids = {r.fix_id for r in (state.get("executed_fixes") or [])}
    failed_ids = {r.fix_id for r in (state.get("failed_fixes") or [])}

    # Generate plan on first run
    if not fix_plan:
        fix_plan = generate_fix_plan(state["audit_findings"])

    # Find next pending approved fix
    pending = [
        f for f in fix_plan
        if f.fix_id in approved_ids
        and f.fix_id not in executed_ids
        and f.fix_id not in failed_ids
    ]

    iteration = state.get("iteration", 0) + 1

    if not pending or iteration > 50:
        return {
            "fix_plan": fix_plan,
            "current_fix_id": None,
            "iteration": iteration,
        }

    next_fix = pending[0]
    return {
        "fix_plan": fix_plan,
        "current_fix_id": next_fix.fix_id,
        "iteration": iteration,
        "retry_count": 0,
    }


def route_after_planner(state: StoreOptimizationState) -> Literal["executor", "reporter"]:
    if state.get("current_fix_id") is None:
        return "reporter"
    return "executor"


# ---------------------------------------------------------------------------
# approval_gate_node
# ---------------------------------------------------------------------------

def approval_gate_node(state: StoreOptimizationState) -> dict:
    """Pass-through — approved_fix_ids are set in initial state by POST /execute.

    In a full multi-turn deployment this node would use LangGraph interrupt()
    to pause until the merchant approves via the frontend. For this build,
    approval is submitted upfront with the /execute request.
    """
    return {}


# ---------------------------------------------------------------------------
# executor_node
# ---------------------------------------------------------------------------

async def executor_node(state: StoreOptimizationState) -> dict:
    """Execute the tool for the current fix."""
    fix_id = state.get("current_fix_id")
    if not fix_id:
        return {}

    fix_plan = state.get("fix_plan") or []
    fix_item = next((f for f in fix_plan if f.fix_id == fix_id), None)
    if fix_item is None:
        result = FixResult(
            fix_id=fix_id,
            success=False,
            error="Fix item not found in plan",
            shopify_gid=None,
            script_tag_id=None,
            applied_at=None,
        )
        failed = list(state.get("failed_fixes") or [])
        failed.append(result)
        return {"failed_fixes": failed}

    result = await dispatch_tool(
        fix_item,
        state["store_data"],
        state["admin_token"],
        state["job_id"],
        merchant_intent=state.get("merchant_intent"),
    )

    if result.success:
        executed = list(state.get("executed_fixes") or [])
        executed.append(result)
        return {"executed_fixes": executed}
    else:
        failed = list(state.get("failed_fixes") or [])
        failed.append(result)
        return {"failed_fixes": failed}


def route_after_executor(state: StoreOptimizationState) -> Literal["verifier"]:
    return "verifier"


# ---------------------------------------------------------------------------
# verifier_node
# ---------------------------------------------------------------------------

async def verifier_node(state: StoreOptimizationState) -> dict:
    """Verify the last executed fix resolved its finding.

    Simplified verifier: checks if the fix succeeded (from executor result).
    Re-fetching live data from Shopify to re-run the check would add latency;
    for the hackathon we trust the executor result as ground truth.
    If retry_count < 2 and fix failed, route back to executor.
    """
    fix_id = state.get("current_fix_id")
    retry_count = state.get("retry_count", 0)

    executed = state.get("executed_fixes") or []
    last_success = any(r.fix_id == fix_id and r.success for r in executed)

    verification_results = dict(state.get("verification_results") or {})
    if fix_id:
        verification_results[fix_id] = last_success

    if last_success:
        return {
            "verification_results": verification_results,
            "retry_count": 0,
            "current_fix_id": None,
        }

    # Fix failed — retry up to 2 times
    if retry_count < 2:
        # Remove from failed to allow retry
        failed = [r for r in (state.get("failed_fixes") or []) if r.fix_id != fix_id]
        return {
            "verification_results": verification_results,
            "retry_count": retry_count + 1,
            "failed_fixes": failed,
        }

    # Exceeded retries — mark as manual action item
    fix_plan = state.get("fix_plan") or []
    fix_item = next((f for f in fix_plan if f.fix_id == fix_id), None)
    manual = list(state.get("manual_action_items") or [])
    if fix_item:
        manual_finding = Finding(
            id=f"manual_{fix_id}",
            pillar="",
            check_id=fix_item.field,
            check_name=fix_item.type,
            severity="HIGH",
            weight=6,
            title=f"Manual action needed: {fix_item.type} for {fix_item.product_title or fix_item.product_id}",
            detail=fix_item.reason,
            spec_citation="",
            affected_products=[fix_item.product_id] if fix_item.product_id else [],
            affected_count=1,
            impact_statement="Agent retried twice and could not auto-fix this issue.",
            fix_type="manual",
            fix_instruction=f"Manually apply: {fix_item.proposed_value}",
            fix_content=None,
        )
        manual.append(manual_finding)

    return {
        "verification_results": verification_results,
        "retry_count": 0,
        "current_fix_id": None,
        "manual_action_items": manual,
    }


def route_after_verifier(
    state: StoreOptimizationState,
) -> Literal["executor", "planner"]:
    fix_id = state.get("current_fix_id")
    retry_count = state.get("retry_count", 0)
    executed = state.get("executed_fixes") or []
    last_success = any(r.fix_id == fix_id and r.success for r in executed)

    if not last_success and retry_count > 0:
        return "executor"
    return "planner"


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
    original_findings = original_report.get("findings") or []
    original_pillar_dict = original_report.get("pillars") or {}

    original_failing: set[str] = {f.get("check_id", "") for f in original_findings}

    resolved_check_ids: set[str] = set()
    copy_paste_items: list[dict] = []

    for fix_result in executed_fixes:
        success = fix_result.success if hasattr(fix_result, "success") else fix_result.get("success", False)
        if not success:
            continue

        fix_id: str = fix_result.fix_id if hasattr(fix_result, "fix_id") else fix_result.get("fix_id", "")

        fix_type = ""
        for prefix in FIX_TYPE_RESOLVES:
            if fix_id.startswith(prefix + "_") or fix_id == prefix:
                fix_type = prefix
                break

        if fix_type in FIX_TYPE_RESOLVES:
            resolved_check_ids.update(FIX_TYPE_RESOLVES[fix_type])

        content = fix_result.shopify_gid if hasattr(fix_result, "shopify_gid") else (fix_result.get("shopify_gid") or "")
        if content and fix_type in ("generate_schema_snippet", "suggest_policy_fix"):
            label = "JSON-LD Schema Snippet" if fix_type == "generate_schema_snippet" else "Policy Draft"
            copy_paste_items.append({"label": label, "content": content, "fix_id": fix_id})

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


# ---------------------------------------------------------------------------
# reporter_node
# ---------------------------------------------------------------------------

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
