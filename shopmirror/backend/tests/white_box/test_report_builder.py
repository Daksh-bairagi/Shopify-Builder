"""
White-box tests for app/services/report_builder.py

Tests cover:
  - calculate_pillar_scores  (per-pillar pass/fail counting)
  - calculate_ai_readiness_score  (weighted composite, 0–100)
  - calculate_channel_compliance  (READY / PARTIAL / BLOCKED logic)
  - get_worst_products  (gap-score accumulation and ranking)
  - assemble_report  (empty-store fast path and normal path)
"""

from __future__ import annotations

import asyncio
import pytest

from app.models.findings import Finding, PillarScore, ChannelStatus
from app.services.report_builder import (
    PILLAR_CHECKS,
    CHANNEL_CHECKS,
    calculate_pillar_scores,
    calculate_ai_readiness_score,
    calculate_channel_compliance,
    get_worst_products,
    assemble_report,
)

from tests.fixtures.merchant_data import make_merchant, make_product, make_variant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_finding(check_id: str, pillar: str, severity: str = "HIGH", affected_products=None) -> Finding:
    weight = {"CRITICAL": 10, "HIGH": 6, "MEDIUM": 2}.get(severity, 6)
    affected = affected_products or []
    return Finding(
        id=f"finding_{check_id}",
        pillar=pillar,
        check_id=check_id,
        check_name=f"Check {check_id}",
        severity=severity,
        weight=weight,
        title=f"Issue with {check_id}",
        detail="Detail text.",
        spec_citation="Spec",
        affected_products=affected,
        affected_count=len(affected),
        impact_statement="Impact.",
        fix_type="auto",
        fix_instruction="Fix it.",
        fix_content=None,
    )


# ===========================================================================
# calculate_pillar_scores
# ===========================================================================

class TestCalculatePillarScores:

    def test_no_findings_all_pillars_score_1(self):
        scores = calculate_pillar_scores([])
        for pillar in PILLAR_CHECKS:
            assert pillar in scores
            assert scores[pillar].score == 1.0
            assert scores[pillar].checks_passed == scores[pillar].checks_total

    def test_one_failed_check_reduces_score(self):
        # Completeness has 6 checks. Failing C1 → 5/6 passed
        f = _make_finding("C1", "Completeness", "CRITICAL")
        scores = calculate_pillar_scores([f])
        comp = scores["Completeness"]
        assert comp.checks_passed == comp.checks_total - 1
        assert abs(comp.score - (5 / 6)) < 0.001

    def test_all_checks_in_pillar_fail_score_zero(self):
        # Fail all 3 Consistency checks
        consistency_checks = PILLAR_CHECKS["Consistency"]["check_ids"]
        findings = [_make_finding(cid, "Consistency") for cid in consistency_checks]
        scores = calculate_pillar_scores(findings)
        assert scores["Consistency"].score == 0.0
        assert scores["Consistency"].checks_passed == 0

    def test_same_check_id_twice_counts_as_one_failed_check(self):
        # Two findings with the same check_id should count as ONE failed check
        f1 = _make_finding("C1", "Completeness")
        f2 = _make_finding("C1", "Completeness")
        scores = calculate_pillar_scores([f1, f2])
        comp = scores["Completeness"]
        # 6 total checks, only 1 distinct check_id failed
        assert comp.checks_passed == comp.checks_total - 1

    def test_finding_in_wrong_pillar_does_not_affect_other_pillar(self):
        # C1 is in Completeness; failing it should not touch Discoverability
        f = _make_finding("C1", "Completeness", "CRITICAL")
        scores = calculate_pillar_scores([f])
        disc = scores["Discoverability"]
        assert disc.score == 1.0

    def test_each_pillar_has_correct_total_checks(self):
        scores = calculate_pillar_scores([])
        expected = {
            "Discoverability": 5,
            "Completeness": 6,
            "Consistency": 3,
            "Trust_Policies": 3,
            "Transaction": 2,
        }
        for pillar, expected_total in expected.items():
            assert scores[pillar].checks_total == expected_total, (
                f"{pillar}: expected {expected_total} total checks, got {scores[pillar].checks_total}"
            )

    def test_all_pillars_present_in_output_even_with_findings(self):
        f = _make_finding("D1a", "Discoverability")
        scores = calculate_pillar_scores([f])
        assert set(scores.keys()) == set(PILLAR_CHECKS.keys())


# ===========================================================================
# calculate_ai_readiness_score
# ===========================================================================

class TestCalculateAiReadinessScore:

    def test_all_passing_returns_100(self):
        scores = calculate_pillar_scores([])
        score = calculate_ai_readiness_score(scores)
        assert score == 100.0

    def test_all_failing_returns_low_score(self):
        # Fail every single check across all pillars
        all_findings = []
        for pillar, cfg in PILLAR_CHECKS.items():
            for cid in cfg["check_ids"]:
                all_findings.append(_make_finding(cid, pillar, "CRITICAL"))
        scores = calculate_pillar_scores(all_findings)
        score = calculate_ai_readiness_score(scores)
        assert score == 0.0

    def test_score_is_0_to_100(self):
        # Fail half the checks across all pillars
        all_findings = []
        for pillar, cfg in PILLAR_CHECKS.items():
            for cid in cfg["check_ids"][:1]:  # fail first check in each pillar
                all_findings.append(_make_finding(cid, pillar))
        scores = calculate_pillar_scores(all_findings)
        score = calculate_ai_readiness_score(scores)
        assert 0.0 <= score <= 100.0

    def test_higher_weight_pillar_impacts_score_more(self):
        # Completeness has weight 0.30, Transaction has 0.15
        # Failing ALL Completeness checks should drop score more than failing ALL Transaction checks
        comp_findings = [
            _make_finding(cid, "Completeness") for cid in PILLAR_CHECKS["Completeness"]["check_ids"]
        ]
        trans_findings = [
            _make_finding(cid, "Transaction") for cid in PILLAR_CHECKS["Transaction"]["check_ids"]
        ]
        score_comp_fail = calculate_ai_readiness_score(calculate_pillar_scores(comp_findings))
        score_trans_fail = calculate_ai_readiness_score(calculate_pillar_scores(trans_findings))
        assert score_comp_fail < score_trans_fail

    def test_empty_pillar_scores_returns_0(self):
        assert calculate_ai_readiness_score({}) == 0.0


# ===========================================================================
# calculate_channel_compliance
# ===========================================================================

class TestCalculateChannelCompliance:

    def test_no_findings_all_channels_ready(self):
        compliance = calculate_channel_compliance([])
        for channel in ("shopify_catalog", "google_shopping", "meta_catalog",
                        "perplexity_web", "chatgpt_shopping"):
            status = getattr(compliance, channel)
            assert status.status == "READY"
            assert status.blocking_check_ids == []

    def test_all_checks_fail_channels_blocked(self):
        # Fail every check relevant to a channel → BLOCKED
        all_check_ids = set()
        for checks in CHANNEL_CHECKS.values():
            all_check_ids.update(checks)

        pillar_for_check = {}
        for pillar, cfg in PILLAR_CHECKS.items():
            for cid in cfg["check_ids"]:
                pillar_for_check[cid] = pillar

        findings = [
            _make_finding(cid, pillar_for_check.get(cid, "Completeness"))
            for cid in all_check_ids
        ]
        compliance = calculate_channel_compliance(findings)
        for channel in ("shopify_catalog", "google_shopping", "meta_catalog",
                        "perplexity_web", "chatgpt_shopping"):
            status = getattr(compliance, channel)
            assert status.status == "BLOCKED", f"{channel} should be BLOCKED"

    def test_partial_failure_gives_partial_status(self):
        # Shopify Catalog needs D1b, C1, Con1, A1, A2
        # Fail only D1b → 1/5 failed → PARTIAL
        f = _make_finding("D1b", "Discoverability", "CRITICAL")
        compliance = calculate_channel_compliance([f])
        assert compliance.shopify_catalog.status == "PARTIAL"
        assert "D1b" in compliance.shopify_catalog.blocking_check_ids

    def test_perplexity_web_gated_on_d1a_d2_d3(self):
        # Fail all 3 perplexity checks → BLOCKED
        findings = [
            _make_finding("D1a", "Discoverability"),
            _make_finding("D2", "Discoverability"),
            _make_finding("D3", "Discoverability"),
        ]
        compliance = calculate_channel_compliance(findings)
        assert compliance.perplexity_web.status == "BLOCKED"

    def test_chatgpt_shopping_gated_on_t4_t1_t2(self):
        findings = [
            _make_finding("T4", "Trust_Policies"),
            _make_finding("T1", "Trust_Policies"),
            _make_finding("T2", "Trust_Policies"),
        ]
        compliance = calculate_channel_compliance(findings)
        assert compliance.chatgpt_shopping.status == "BLOCKED"

    def test_blocking_check_ids_match_failed_checks(self):
        # Fail D1b and C1 which are both in shopify_catalog
        findings = [
            _make_finding("D1b", "Discoverability", "CRITICAL"),
            _make_finding("C1", "Completeness", "CRITICAL"),
        ]
        compliance = calculate_channel_compliance(findings)
        shop_blocking = compliance.shopify_catalog.blocking_check_ids
        assert "D1b" in shop_blocking
        assert "C1" in shop_blocking

    def test_failed_check_only_impacts_relevant_channels(self):
        # D3 is only in perplexity_web, not in shopify_catalog
        f = _make_finding("D3", "Discoverability")
        compliance = calculate_channel_compliance([f])
        assert compliance.perplexity_web.status == "PARTIAL"
        assert compliance.shopify_catalog.status == "READY"


# ===========================================================================
# get_worst_products
# ===========================================================================

class TestGetWorstProducts:

    def test_no_findings_returns_empty(self):
        products = [make_product(id="p1"), make_product(id="p2")]
        result = get_worst_products(products, [])
        assert result == []

    def test_products_ranked_by_gap_score(self):
        products = [make_product(id=f"p{i}") for i in range(3)]
        findings = [
            _make_finding("C1", "Completeness", "CRITICAL", ["p0", "p1", "p2"]),  # weight 10
            _make_finding("C2", "Completeness", "CRITICAL", ["p0"]),               # weight 10 extra for p0
            _make_finding("C3", "Completeness", "HIGH",     ["p1"]),               # weight 6 extra for p1
        ]
        result = get_worst_products(products, findings)
        # p0 has score 20 (10+10), p1 has 16 (10+6), p2 has 10
        assert result[0].product_id == "p0"
        assert result[1].product_id == "p1"
        assert result[2].product_id == "p2"

    def test_gap_score_accumulates_across_findings(self):
        products = [make_product(id="p1")]
        findings = [
            _make_finding("C1", "Completeness", "CRITICAL", ["p1"]),  # weight 10
            _make_finding("C2", "Completeness", "CRITICAL", ["p1"]),  # weight 10
            _make_finding("C3", "Completeness", "HIGH",     ["p1"]),  # weight 6
        ]
        result = get_worst_products(products, findings)
        assert len(result) == 1
        assert result[0].gap_score == 26.0

    def test_n_cap_is_respected(self):
        products = [make_product(id=f"p{i}") for i in range(10)]
        findings = [_make_finding("C1", "Completeness", affected_products=[f"p{i}" for i in range(10)])]
        result = get_worst_products(products, findings, n=3)
        assert len(result) == 3

    def test_product_not_in_any_finding_excluded(self):
        products = [make_product(id="p1"), make_product(id="p2")]
        findings = [_make_finding("C1", "Completeness", affected_products=["p1"])]
        result = get_worst_products(products, findings)
        pids = [r.product_id for r in result]
        assert "p1" in pids
        assert "p2" not in pids

    def test_failing_check_ids_aggregated_correctly(self):
        products = [make_product(id="p1")]
        findings = [
            _make_finding("C1", "Completeness", affected_products=["p1"]),
            _make_finding("C2", "Completeness", affected_products=["p1"]),
        ]
        result = get_worst_products(products, findings)
        assert set(result[0].failing_check_ids) == {"C1", "C2"}

    def test_product_id_not_in_products_list_excluded(self):
        # Finding references a product_id not in the products list
        products = [make_product(id="p1")]
        findings = [_make_finding("C1", "Completeness", affected_products=["ghost_product"])]
        result = get_worst_products(products, findings)
        assert result == []


# ===========================================================================
# assemble_report
# ===========================================================================

class TestAssembleReport:

    def test_empty_store_returns_zero_score(self):
        data = make_merchant(products=[])
        report = asyncio.get_event_loop().run_until_complete(
            assemble_report(data, [], None, None, [], [])
        )
        assert report.total_products == 0
        assert report.ai_readiness_score == 0.0

    def test_empty_store_all_channels_blocked(self):
        data = make_merchant(products=[])
        report = asyncio.get_event_loop().run_until_complete(
            assemble_report(data, [], None, None, [], [])
        )
        for channel in ("shopify_catalog", "google_shopping", "meta_catalog",
                        "perplexity_web", "chatgpt_shopping"):
            assert getattr(report.channel_compliance, channel).status == "BLOCKED"

    def test_report_fields_populated_from_merchant_data(self):
        data = make_merchant(store_name="My Store", store_domain="my-store.myshopify.com")
        report = asyncio.get_event_loop().run_until_complete(
            assemble_report(data, [], None, None, [], [])
        )
        assert report.store_name == "My Store"
        assert report.store_domain == "my-store.myshopify.com"

    def test_worst_5_products_is_subset_of_all_products(self):
        products = [make_product(id=f"p{i}") for i in range(10)]
        findings = [_make_finding("C1", "Completeness", affected_products=[f"p{i}" for i in range(10)])]
        data = make_merchant(products=products)
        report = asyncio.get_event_loop().run_until_complete(
            assemble_report(data, findings, None, None, [], [])
        )
        worst_ids = {p.product_id for p in report.worst_5_products}
        all_ids = {p.product_id for p in report.all_products}
        assert worst_ids.issubset(all_ids)
        assert len(report.worst_5_products) <= 5
