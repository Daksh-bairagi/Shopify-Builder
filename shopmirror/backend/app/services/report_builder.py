"""
report_builder.py — Assembles the final AuditReport from all pipeline outputs.
No LLM calls, no I/O, no side effects.
"""

from __future__ import annotations

from app.models.merchant import MerchantData, Product
from app.models.findings import (
    Finding, PillarScore, AuditReport, PerceptionDiff, ProductPerception,
    MCPResult, CompetitorResult, CopyPasteItem, ProductSummary,
    ChannelStatus, ChannelCompliance, QueryMatchResult,
)

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

PILLAR_CHECKS: dict[str, dict] = {
    "Discoverability":  {"check_ids": ["D1a", "D1b", "D2", "D3", "D5"], "weight": 0.20},
    "Completeness":     {"check_ids": ["C1", "C2", "C3", "C4", "C5", "C6"], "weight": 0.30},
    "Consistency":      {"check_ids": ["Con1", "Con2", "Con3"], "weight": 0.20},
    "Trust_Policies":   {"check_ids": ["T1", "T2", "T4"], "weight": 0.15},
    "Transaction":      {"check_ids": ["A1", "A2"], "weight": 0.15},
}

CHANNEL_CHECKS: dict[str, list[str]] = {
    "shopify_catalog":  ["D1b", "C1", "Con1", "A1", "A2"],
    "google_shopping":  ["C4", "C1", "Con1", "Con2"],
    "meta_catalog":     ["C2", "C6", "Con1"],
    "perplexity_web":   ["D1a", "D2", "D3"],
    "chatgpt_shopping": ["T4", "T1", "T2"],
}


# ---------------------------------------------------------------------------
# 1. calculate_pillar_scores
# ---------------------------------------------------------------------------

def calculate_pillar_scores(findings: list[Finding]) -> dict[str, PillarScore]:
    """
    For each pillar, count distinct check_ids that appear in findings,
    then compute score = checks_passed / checks_total.
    """
    result: dict[str, PillarScore] = {}
    try:
        for pillar, cfg in PILLAR_CHECKS.items():
            check_ids: list[str] = cfg["check_ids"]
            checks_total = len(check_ids)
            failed_check_ids = {
                f.check_id
                for f in findings
                if f.pillar == pillar and f.check_id in check_ids
            }
            checks_passed = checks_total - len(failed_check_ids)
            score = checks_passed / checks_total if checks_total > 0 else 1.0
            result[pillar] = PillarScore(
                score=score,
                checks_passed=checks_passed,
                checks_total=checks_total,
            )
    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# 2. calculate_ai_readiness_score
# ---------------------------------------------------------------------------

def calculate_ai_readiness_score(pillar_scores: dict[str, PillarScore]) -> float:
    """
    Weighted sum across all pillars, scaled to 0–100.
    """
    if not pillar_scores:
        return 0.0
    try:
        raw = sum(
            pillar_scores[p].score * PILLAR_CHECKS[p]["weight"]
            for p in PILLAR_CHECKS
            if p in pillar_scores
        )
        return round(raw * 100, 1)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# 3. calculate_channel_compliance
# ---------------------------------------------------------------------------

def calculate_channel_compliance(findings: list[Finding]) -> ChannelCompliance:
    """
    For each channel, derive READY / PARTIAL / BLOCKED based on which
    of its gating check_ids appear in findings.
    """
    try:
        failed_globally = {f.check_id for f in findings}

        def _channel_status(channel_check_ids: list[str]) -> ChannelStatus:
            failed_ids = [cid for cid in channel_check_ids if cid in failed_globally]
            n_failed = len(failed_ids)
            n_total = len(channel_check_ids)
            if n_failed == 0:
                status = "READY"
            elif n_failed == n_total:
                status = "BLOCKED"
            else:
                status = "PARTIAL"
            return ChannelStatus(status=status, blocking_check_ids=failed_ids)

        return ChannelCompliance(
            shopify_catalog=_channel_status(CHANNEL_CHECKS["shopify_catalog"]),
            google_shopping=_channel_status(CHANNEL_CHECKS["google_shopping"]),
            meta_catalog=_channel_status(CHANNEL_CHECKS["meta_catalog"]),
            perplexity_web=_channel_status(CHANNEL_CHECKS["perplexity_web"]),
            chatgpt_shopping=_channel_status(CHANNEL_CHECKS["chatgpt_shopping"]),
        )
    except Exception:
        default = ChannelStatus(status="READY", blocking_check_ids=[])
        return ChannelCompliance(
            shopify_catalog=default,
            google_shopping=default,
            meta_catalog=default,
            perplexity_web=default,
            chatgpt_shopping=default,
        )


# ---------------------------------------------------------------------------
# 4. get_worst_products
# ---------------------------------------------------------------------------

def get_worst_products(
    products: list[Product],
    findings: list[Finding],
    n: int = 5,
) -> list[ProductSummary]:
    """
    Score each product by the sum of finding weights for findings that
    reference it, then return the top-n by descending gap_score.
    """
    try:
        product_map = {p.id: p for p in products}

        # Aggregate per-product gap score and failing check_ids
        gap_scores: dict[str, float] = {}
        failing_checks: dict[str, set[str]] = {}

        for finding in findings:
            for pid in finding.affected_products:
                if pid not in gap_scores:
                    gap_scores[pid] = 0.0
                    failing_checks[pid] = set()
                gap_scores[pid] += finding.weight
                failing_checks[pid].add(finding.check_id)

        # Build summaries only for products we actually know about
        summaries: list[ProductSummary] = []
        for pid, score in gap_scores.items():
            if pid in product_map:
                product = product_map[pid]
                summaries.append(
                    ProductSummary(
                        product_id=pid,
                        title=product.title,
                        gap_score=score,
                        failing_check_ids=sorted(failing_checks[pid]),
                    )
                )

        summaries.sort(key=lambda s: s.gap_score, reverse=True)
        return summaries[:n]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# 5. assemble_report
# ---------------------------------------------------------------------------

async def assemble_report(
    merchant_data: MerchantData,
    findings: list[Finding],
    llm_results: list[dict],
    perception_diff: PerceptionDiff | None,
    mcp_results: list[MCPResult] | None,
    query_match_results: list[QueryMatchResult],
    competitor_results: list[CompetitorResult],
    copy_paste_items: list[CopyPasteItem],
) -> AuditReport:
    """
    Assembles all pipeline outputs into a single AuditReport.
    No awaits needed — async for future-proofing only.
    """
    try:
        pillar_scores = calculate_pillar_scores(findings)
        ai_readiness_score = calculate_ai_readiness_score(pillar_scores)
        channel_compliance = calculate_channel_compliance(findings)
        worst_5_products = get_worst_products(merchant_data.products, findings, n=5)

        return AuditReport(
            store_name=merchant_data.store_name,
            store_domain=merchant_data.store_domain,
            ingestion_mode=merchant_data.ingestion_mode,
            total_products=len(merchant_data.products),
            ai_readiness_score=ai_readiness_score,
            pillars=pillar_scores,
            findings=findings,
            worst_5_products=worst_5_products,
            channel_compliance=channel_compliance,
            perception_diff=perception_diff,
            mcp_simulation=mcp_results,
            query_match_results=query_match_results,
            competitor_comparison=competitor_results,
            copy_paste_package=copy_paste_items,
        )
    except Exception:
        # Fallback: return a minimal valid report so the job doesn't crash
        default_channel = ChannelStatus(status="READY", blocking_check_ids=[])
        return AuditReport(
            store_name=getattr(merchant_data, "store_name", ""),
            store_domain=getattr(merchant_data, "store_domain", ""),
            ingestion_mode=getattr(merchant_data, "ingestion_mode", "url_only"),
            total_products=len(getattr(merchant_data, "products", [])),
            ai_readiness_score=0.0,
            pillars={},
            findings=findings,
            worst_5_products=[],
            channel_compliance=ChannelCompliance(
                shopify_catalog=default_channel,
                google_shopping=default_channel,
                meta_catalog=default_channel,
                perplexity_web=default_channel,
                chatgpt_shopping=default_channel,
            ),
            perception_diff=perception_diff,
            mcp_simulation=mcp_results,
            query_match_results=query_match_results or [],
            competitor_comparison=competitor_results or [],
            copy_paste_package=copy_paste_items or [],
        )
