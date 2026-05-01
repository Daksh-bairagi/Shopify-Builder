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
import json
import logging
import os
import re
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
    "C3":  "rename_variant_options",
    "C4":  "supply_identifiers",
    "C5":  "create_metafield_definitions",
    "C6":  "generate_alt_text",
    "Con1": "generate_schema_snippet",
    "Con2": "repair_availability_schema",
    "Con3": "align_seo_metadata",
    "T1":  "suggest_policy_fix",     # No refund policy
    "T2":  "suggest_policy_fix",     # No shipping policy
    "T4":  "generate_schema_snippet",
}

# Store-level fix types get a single fix item regardless of affected product count
STORE_LEVEL_TYPES = {
    "generate_schema_snippet",
    "create_metafield_definitions",
    "suggest_policy_fix",
}


def _extract_shipping_country_codes(shipping_text: str) -> list[str]:
    text = (shipping_text or "").lower()
    codes: list[str] = []
    mapping = [
        ("united states", "US"),
        ("usa", "US"),
        ("canada", "CA"),
        ("united kingdom", "GB"),
        ("uk", "GB"),
        ("australia", "AU"),
        ("europe", "EU"),
        ("international", "INTL"),
        ("worldwide", "INTL"),
    ]
    for needle, code in mapping:
        if needle in text and code not in codes:
            codes.append(code)
    return codes or ["US"]


def _build_schema_snippet_content(merchant_data) -> str:
    refund_text = getattr(getattr(merchant_data, "policies", None), "refund", "") or ""
    shipping_text = getattr(getattr(merchant_data, "policies", None), "shipping", "") or ""
    return_days = 30
    match = re.search(
        r"(\d+)\s*(?:day|days|business\s+day|business\s+days)",
        refund_text,
        re.IGNORECASE,
    )
    if match:
        return_days = int(match.group(1))

    shipping_destinations = [
        {"@type": "DefinedRegion", "addressCountry": code}
        for code in _extract_shipping_country_codes(shipping_text)
    ]

    schema = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "{{ product.title }}",
        "image": "{{ product.featured_image | image_url: width: 1600 }}",
        "description": "{{ product.description | strip_html | truncate: 240 }}",
        "sku": "{{ product.selected_or_first_available_variant.sku }}",
        "brand": {
            "@type": "Brand",
            "name": "{{ product.vendor }}",
        },
        "offers": {
            "@type": "Offer",
            "url": "{{ canonical_url }}",
            "priceCurrency": "{{ cart.currency.iso_code }}",
            "price": "{{ product.selected_or_first_available_variant.price | money_without_currency }}",
            "availability": "{% if product.selected_or_first_available_variant.available %}https://schema.org/InStock{% else %}https://schema.org/OutOfStock{% endif %}",
            "shippingDetails": {
                "@type": "OfferShippingDetails",
                "shippingDestination": shipping_destinations,
            },
            "hasMerchantReturnPolicy": {
                "@type": "MerchantReturnPolicy",
                "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
                "merchantReturnDays": return_days,
                "returnMethod": "https://schema.org/ReturnByMail",
            },
        },
    }
    return json.dumps(schema, indent=2)


def _build_policy_fix_content(check_id: str) -> str:
    if check_id == "T1":
        return (
            "Returns & Refunds Policy\n\n"
            "We accept returns within 30 days of delivery. Items must be unused, in original packaging, "
            "and accompanied by proof of purchase. To start a return, contact support with your order number. "
            "Approved refunds are issued to the original payment method within 5-7 business days after the return is received."
        )
    return (
        "Shipping Policy\n\n"
        "We currently ship within the United States and Canada. Standard shipping typically arrives within "
        "5-7 business days, while expedited shipping arrives within 2-3 business days where available. "
        "Shipping rates and delivery timelines are shown at checkout based on destination."
    )


def build_copy_paste_items(fix_plan: list[FixItem]) -> list[dict]:
    """Extract human-copyable outputs so the UI can present them as a package."""
    items: list[dict] = []
    for fix in fix_plan:
        if fix.fix_type != "copy_paste" or not fix.proposed_value:
            continue
        label = "Policy Draft" if fix.type == "suggest_policy_fix" else "JSON-LD Schema Snippet"
        items.append({
            "label": label,
            "content": fix.proposed_value,
            "fix_id": fix.fix_id,
        })
    return items


def _safe_price(value) -> float:
    """Best-effort numeric parsing for price-like fields from Shopify payloads."""
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _catalog_eligibility_missing_fields(product, merchant_data) -> list[str]:
    """List the minimum fields still missing for a product to look catalog-ready."""
    missing: list[str] = []
    taxonomy_gid = (merchant_data.taxonomy_by_product.get(product.id, "") if merchant_data else "") or ""
    if not taxonomy_gid.strip():
        missing.append("taxonomy")
    if not (product.title or "").strip():
        missing.append("title")
    has_priced_variant = any(_safe_price(getattr(variant, "price", None)) > 0 for variant in product.variants) if product.variants else False
    if not has_priced_variant:
        missing.append("priced variant")
    return missing


def generate_fix_plan(findings: list[Finding], merchant_data=None) -> list[FixItem]:
    """Map audit findings to ordered FixItem list.

    Rules:
    - Product-level fix types: one FixItem per affected product per finding
    - Store-level fix types: one FixItem for the whole store, deduplicated
    - Sorted by DEPENDENCY_ORDER then severity_weight * affected_count desc
    """
    # Build product id → title lookup for human-readable fix descriptions
    product_titles: dict[str, str] = {}
    if merchant_data and hasattr(merchant_data, "products"):
        for p in merchant_data.products:
            product_titles[p.id] = p.title

    items: list[FixItem] = []
    seen_store_level: set[str] = set()
    seen_product_fix_types: set[tuple[str, str]] = set()
    product_map = {
        p.id: p for p in getattr(merchant_data, "products", [])
    } if merchant_data and hasattr(merchant_data, "products") else {}

    for finding in findings:
        if finding.check_id == "D1b" and product_map:
            for product_id in finding.affected_products[:20]:
                product = product_map.get(product_id)
                if product is None:
                    continue

                missing_fields = _catalog_eligibility_missing_fields(product, merchant_data)

                if "taxonomy" in missing_fields and ("map_taxonomy", product_id) not in seen_product_fix_types:
                    seen_product_fix_types.add(("map_taxonomy", product_id))
                    items.append(FixItem(
                        fix_id=str(uuid.uuid4()),
                        type="map_taxonomy",
                        product_id=product_id,
                        product_title=product_titles.get(product_id, ""),
                        field=finding.check_id,
                        current_value=None,
                        proposed_value="Assign a Shopify Standard Product Taxonomy category.",
                        reason=f"{finding.detail} Missing requirement: taxonomy mapping.",
                        risk="LOW",
                        reversible=True,
                        severity=finding.severity,
                        fix_type="auto",
                        check_id=finding.check_id,
                    ))

                remaining_manual_fields = [field for field in missing_fields if field != "taxonomy"]
                if remaining_manual_fields and ("repair_catalog_eligibility", product_id) not in seen_product_fix_types:
                    seen_product_fix_types.add(("repair_catalog_eligibility", product_id))
                    items.append(FixItem(
                        fix_id=str(uuid.uuid4()),
                        type="repair_catalog_eligibility",
                        product_id=product_id,
                        product_title=product_titles.get(product_id, ""),
                        field=finding.check_id,
                        current_value=None,
                        proposed_value=(
                            "Update this product so it meets catalog eligibility by adding "
                            + ", ".join(remaining_manual_fields)
                            + "."
                        ),
                        reason=(
                            "This product still fails Shopify Catalog eligibility after taxonomy "
                            "mapping because it is missing: "
                            + ", ".join(remaining_manual_fields)
                            + "."
                        ),
                        risk="LOW",
                        reversible=False,
                        severity=finding.severity,
                        fix_type="manual",
                        check_id=finding.check_id,
                    ))
            continue

        fix_type = CHECK_TO_FIX_TYPE.get(finding.check_id)
        if fix_type is None:
            continue

        # Map fix_type to its execution category
        if fix_type in ("generate_schema_snippet", "suggest_policy_fix"):
            item_fix_type = "copy_paste"
        elif fix_type in ("inject_schema_script", "create_metafield_definitions",
                          "map_taxonomy", "classify_product_type", "improve_title",
                          "fill_metafield", "generate_alt_text"):
            item_fix_type = "auto"
        else:
            item_fix_type = "manual"

        if fix_type in STORE_LEVEL_TYPES:
            if fix_type in seen_store_level:
                continue
            seen_store_level.add(fix_type)
            proposed_value = f"Fix for {finding.title}"
            if fix_type == "generate_schema_snippet" and merchant_data is not None:
                proposed_value = _build_schema_snippet_content(merchant_data)
            elif fix_type == "suggest_policy_fix":
                proposed_value = _build_policy_fix_content(finding.check_id)
            items.append(FixItem(
                fix_id=str(uuid.uuid4()),
                type=fix_type,
                product_id="",
                product_title="",
                field=finding.check_id,
                current_value=None,
                proposed_value=proposed_value,
                reason=finding.detail,
                risk="LOW",
                reversible=fix_type != "suggest_policy_fix",
                severity=finding.severity,
                fix_type=item_fix_type,
                check_id=finding.check_id,
            ))
        else:
            for product_id in finding.affected_products[:20]:  # cap at 20 products per finding
                if (fix_type, product_id) in seen_product_fix_types:
                    continue
                seen_product_fix_types.add((fix_type, product_id))
                items.append(FixItem(
                    fix_id=str(uuid.uuid4()),
                    type=fix_type,
                    product_id=product_id,
                    product_title=product_titles.get(product_id, ""),
                    field=finding.check_id,
                    current_value=None,
                    proposed_value=finding.fix_instruction,
                    reason=finding.detail,
                    risk="LOW",
                    reversible=True,
                    severity=finding.severity,
                    fix_type=item_fix_type,
                    check_id=finding.check_id,
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
        fix_plan = generate_fix_plan(state["audit_findings"], merchant_data=state.get("store_data"))

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
    fix_plan = state.get("fix_plan") or []
    fix_item = next((f for f in fix_plan if f.fix_id == fix_id), None)
    last_success = any(r.fix_id == fix_id and r.success for r in executed)
    verified_success = last_success

    verification_results = dict(state.get("verification_results") or {})

    if last_success and fix_item is not None:
        # Copy-paste fixes generate content without writing to Shopify — nothing to verify
        if fix_item.fix_type == "copy_paste":
            verified_success = True
        else:
            from app.services.shopify_writer import verify_fix_applied
            try:
                verified_success = await verify_fix_applied(
                    getattr(state["store_data"], "admin_domain", None) or state["store_data"].store_domain,
                    state["admin_token"],
                    fix_id,
                    fix_item.type,
                )
            except Exception as exc:
                logger.warning("verifier_node: live verification failed for %s: %s", fix_id, exc)
                verified_success = False

    if fix_id:
        verification_results[fix_id] = verified_success

    if verified_success:
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
            impact_statement="Agent could not verify this fix against live Shopify data after retrying.",
            fix_type="manual",
            fix_instruction=fix_item.proposed_value,
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
    "inject_schema_script":        [],
    "generate_schema_snippet":     [],
    "suggest_policy_fix":          ["T1", "T2"],
    "create_metafield_definitions": ["C5"],
}


def _recompute_pillars(failing_check_ids: set[str]) -> dict:
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


def _compute_before_after(original_report: dict, post_fix_findings: list[Finding]) -> dict:
    """
    Compute before/after comparison from original findings and executed fixes.
    Returns a dict matching BeforeAfterResponse schema.
    """
    original_findings = original_report.get("findings") or []
    original_pillar_dict = original_report.get("pillars") or {}
    original_failing: set[str] = {f.get("check_id", "") for f in original_findings}
    post_failing: set[str] = {finding.check_id for finding in post_fix_findings}

    from app.services.report_builder import calculate_pillar_scores
    current_pillars = {
        pillar: dataclasses.asdict(score)
        for pillar, score in calculate_pillar_scores(post_fix_findings).items()
    }

    checks_improved = sorted(original_failing - post_failing)
    checks_unchanged = sorted(original_failing & post_failing)

    mcp_before = original_report.get("mcp_simulation")

    return {
        "original_pillars": original_pillar_dict,
        "current_pillars": current_pillars,
        "checks_improved": checks_improved,
        "checks_unchanged": checks_unchanged,
        "mcp_before": mcp_before,
        "mcp_after": None,
    }


def _estimate_post_fix_findings(
    original_report: dict,
    fix_plan: list[FixItem],
    verification_results: dict[str, bool],
) -> list[Finding]:
    """Cheap post-fix estimate used to avoid a full store re-audit on every execute.

    We start from the original report findings and remove the findings that were
    resolved by verified successful fixes. For product-level fixes we only remove
    the affected product from the finding; for store-level fixes we drop the
    whole finding.
    """
    findings = [Finding(**finding) for finding in (original_report.get("findings") or [])]
    fix_by_id = {fix.fix_id: fix for fix in fix_plan}

    for fix_id, verified in (verification_results or {}).items():
        if not verified:
            continue
        fix = fix_by_id.get(fix_id)
        if fix is None:
            continue

        updated_findings: list[Finding] = []
        for finding in findings:
            if finding.check_id != fix.check_id:
                updated_findings.append(finding)
                continue

            if fix.product_id:
                if fix.product_id not in finding.affected_products:
                    updated_findings.append(finding)
                    continue

                remaining_products = [pid for pid in finding.affected_products if pid != fix.product_id]
                if not remaining_products:
                    continue

                updated_findings.append(
                    dataclasses.replace(
                        finding,
                        affected_products=remaining_products,
                        affected_count=max(0, finding.affected_count - 1),
                    )
                )
            else:
                # Store-level fix verified successfully: remove the finding.
                continue

        findings = updated_findings

    return findings


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
    fix_plan = state.get("fix_plan") or []

    def _display_label_for_fix_id(fix_id: str) -> str:
        fix = next((item for item in fix_plan if item.fix_id == fix_id), None)
        if fix is None:
            return fix_id
        if fix.product_title:
            return f"{fix.type.replace('_', ' ').title()} for {fix.product_title}"
        if fix.reason:
            return fix.reason
        return fix.type.replace("_", " ").title()

    def _serialize_fix_result(result) -> dict:
        payload = dataclasses.asdict(result)
        payload["display_label"] = _display_label_for_fix_id(result.fix_id)
        return payload

    try:
        job_row = await get_job(job_id)
        original_report = (job_row or {}).get("report_json") or {}
    except Exception:
        original_report = {}

    before_after = {
        "original_pillars": original_report.get("pillars") or {},
        "current_pillars": original_report.get("pillars") or {},
        "checks_improved": [],
        "checks_unchanged": sorted({f.get("check_id", "") for f in original_report.get("findings") or []}),
        "mcp_before": original_report.get("mcp_simulation"),
        "mcp_after": None,
    }
    refreshed_report_fields: dict = {}
    full_reaudit = os.getenv("SHOPMIRROR_FULL_REAUDIT_AFTER_FIX", "").strip().lower() in {"1", "true", "yes"}
    if full_reaudit:
        try:
            from app.services.ingestion import fetch_admin_data
            from app.services.heuristics import run_all_checks
            from app.services.llm_analysis import analyze_products
            from app.services.report_builder import (
                calculate_ai_readiness_score,
                calculate_channel_compliance,
                calculate_pillar_scores,
                get_worst_products,
            )
            from app.services.bot_audit import audit_bot_access
            from app.services.identifier_audit import audit_identifiers
            from app.services.golden_record import score_store
            from app.services.trust_signals import score_trust_signals
            from app.services.feed_generator import (
                build_chatgpt_feed,
                build_google_feed,
                build_perplexity_feed,
            )
            from app.services.llms_txt import generate_llms_txt

            store_url = (job_row or {}).get("store_url") or f"https://{state['store_data'].store_domain}"
            refreshed = await fetch_admin_data(store_url, state["admin_token"])
            llm_results = await analyze_products(refreshed.products)
            post_fix_findings = run_all_checks(refreshed, llm_results=llm_results)
            before_after = _compute_before_after(original_report, post_fix_findings)
            pillar_scores = calculate_pillar_scores(post_fix_findings)
            all_products = get_worst_products(refreshed.products, post_fix_findings, n=len(refreshed.products))
            refreshed_report_fields = {
                "store_name": refreshed.store_name,
                "store_domain": refreshed.store_domain,
                "ingestion_mode": refreshed.ingestion_mode,
                "total_products": len(refreshed.products),
                "findings": [dataclasses.asdict(finding) for finding in post_fix_findings],
                "pillars": {
                    pillar: dataclasses.asdict(score)
                    for pillar, score in pillar_scores.items()
                },
                "ai_readiness_score": calculate_ai_readiness_score(pillar_scores),
                "channel_compliance": dataclasses.asdict(calculate_channel_compliance(post_fix_findings)),
                "worst_5_products": [dataclasses.asdict(product) for product in all_products[:5]],
                "all_products": [dataclasses.asdict(product) for product in all_products],
                "bot_access": audit_bot_access(refreshed.robots_txt),
                "identifier_audit": audit_identifiers(refreshed),
                "golden_record": score_store(refreshed),
                "trust_signals": score_trust_signals(refreshed),
                "feed_summaries": {
                    "chatgpt": build_chatgpt_feed(refreshed)["summary"],
                    "perplexity": build_perplexity_feed(refreshed)["summary"],
                    "google": build_google_feed(refreshed)["summary"],
                },
                "llms_txt_preview": generate_llms_txt(refreshed)[:1500],
            }
        except Exception as exc:
            logger.warning("reporter_node: post-fix re-audit failed for job %s: %s", job_id, exc)
    else:
        from app.services.report_builder import (
            calculate_ai_readiness_score,
            calculate_channel_compliance,
            calculate_pillar_scores,
        )

        post_fix_findings = _estimate_post_fix_findings(
            original_report,
            fix_plan,
            state.get("verification_results") or {},
        )
        before_after = _compute_before_after(original_report, post_fix_findings)
        pillar_scores = calculate_pillar_scores(post_fix_findings)
        refreshed_report_fields = {
            "findings": [dataclasses.asdict(finding) for finding in post_fix_findings],
            "pillars": {
                pillar: dataclasses.asdict(score)
                for pillar, score in pillar_scores.items()
            },
            "ai_readiness_score": calculate_ai_readiness_score(pillar_scores),
            "channel_compliance": dataclasses.asdict(calculate_channel_compliance(post_fix_findings)),
        }

    before_after["manual_action_items"] = [dataclasses.asdict(m) for m in manual]

    existing_copy_paste = original_report.get("copy_paste_package") or []

    final_report = {
        **original_report,
        **refreshed_report_fields,
        "agent_run": {
            "fixes_applied": len([r for r in executed if r.success]),
            "fixes_failed": len(failed),
            "manual_action_items": [dataclasses.asdict(m) for m in manual],
            "executed_fixes": [_serialize_fix_result(r) for r in executed],
            "failed_fixes": [_serialize_fix_result(r) for r in failed],
            "verification_results": state.get("verification_results") or {},
            "before_after": before_after,
        },
        "copy_paste_package": existing_copy_paste,
    }

    try:
        await update_job_report(job_id, final_report, status="complete")
    except Exception as exc:
        logger.error("reporter_node: failed to update DB for job %s: %s", job_id, exc)
        # Escalate so the outer background task can mark the job failed.
        raise

    return {"final_report": final_report}
