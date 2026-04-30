"""
White-box tests for the pure routing / state-transition logic in
app/agent/nodes.py — no Shopify API or DB calls required.

Covered:
  - planner_node  (fix selection, iteration guard, first-run plan generation)
  - route_after_planner  (executor vs reporter routing)
  - route_after_verifier  (retry vs planner routing)
  - _compute_before_after  (real delta between original and post-fix findings)
  - _build_schema_snippet_content  (policy-driven JSON-LD generation)
  - _extract_shipping_country_codes  (address-text parsing)
"""

from __future__ import annotations

import json
import pytest

from app.agent.nodes import (
    _build_schema_snippet_content,
    _extract_shipping_country_codes,
    _compute_before_after,
    generate_fix_plan,
    planner_node,
    route_after_planner,
    route_after_verifier,
)
from app.models.findings import Finding
from app.models.fixes import FixItem, FixResult

from tests.fixtures.merchant_data import make_merchant, make_product, make_variant, make_policies


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finding(check_id, pillar="Completeness", severity="HIGH", affected=None):
    w = {"CRITICAL": 10, "HIGH": 6, "MEDIUM": 2}.get(severity, 6)
    af = affected or []
    return Finding(
        id=f"f_{check_id}", pillar=pillar, check_id=check_id,
        check_name=f"Check {check_id}", severity=severity, weight=w,
        title=f"Title {check_id}", detail="Detail", spec_citation="",
        affected_products=af, affected_count=len(af),
        impact_statement="", fix_type="auto", fix_instruction="Fix.",
        fix_content=None,
    )


def _fix_item(fix_id="fix-1", type_="improve_title", product_id="p1",
              fix_type="auto", check_id="C2") -> FixItem:
    return FixItem(
        fix_id=fix_id, type=type_, product_id=product_id, product_title="Test Product",
        field=check_id, current_value=None, proposed_value="Better Title",
        reason="Reason", risk="LOW", reversible=True,
        severity="HIGH", fix_type=fix_type, check_id=check_id,
    )


def _fix_result(fix_id="fix-1", success=True, rolled_back=False) -> FixResult:
    from datetime import datetime
    return FixResult(
        fix_id=fix_id, success=success, error=None if success else "Error",
        shopify_gid="gid://shopify/Product/1" if success else None,
        script_tag_id=None, applied_at=datetime.utcnow(),
    )


def _base_state(**overrides):
    state = {
        "job_id": "job-1",
        "store_data": make_merchant(),
        "admin_token": "shpat_test",
        "merchant_intent": None,
        "audit_findings": [],
        "fix_plan": [],
        "approved_fix_ids": [],
        "executed_fixes": [],
        "failed_fixes": [],
        "current_fix_id": None,
        "retry_count": 0,
        "iteration": 0,
        "verification_results": {},
        "manual_action_items": [],
        "final_report": None,
    }
    state.update(overrides)
    return state


# ===========================================================================
# planner_node
# ===========================================================================

class TestPlannerNode:

    def test_first_run_generates_fix_plan_from_findings(self):
        findings = [_finding("C2", affected=["p1"])]
        state = _base_state(audit_findings=findings, approved_fix_ids=[])
        result = planner_node(state)
        # Plan should be generated even if no approved_ids
        assert result["fix_plan"] is not None
        assert len(result["fix_plan"]) > 0

    def test_no_approved_fixes_routes_to_reporter(self):
        state = _base_state(
            audit_findings=[_finding("C2", affected=["p1"])],
            approved_fix_ids=[],
        )
        result = planner_node(state)
        assert result["current_fix_id"] is None
        assert route_after_planner({**state, **result}) == "reporter"

    def test_approved_fix_sets_current_fix_id(self):
        fix = _fix_item("fix-1")
        state = _base_state(
            fix_plan=[fix],
            approved_fix_ids=["fix-1"],
        )
        result = planner_node(state)
        assert result["current_fix_id"] == "fix-1"

    def test_already_executed_fix_is_skipped(self):
        fix1 = _fix_item("fix-1")
        fix2 = _fix_item("fix-2", product_id="p2")
        state = _base_state(
            fix_plan=[fix1, fix2],
            approved_fix_ids=["fix-1", "fix-2"],
            executed_fixes=[_fix_result("fix-1")],
        )
        result = planner_node(state)
        assert result["current_fix_id"] == "fix-2"

    def test_already_failed_fix_is_skipped(self):
        fix1 = _fix_item("fix-1")
        fix2 = _fix_item("fix-2", product_id="p2")
        state = _base_state(
            fix_plan=[fix1, fix2],
            approved_fix_ids=["fix-1", "fix-2"],
            failed_fixes=[_fix_result("fix-1", success=False)],
        )
        result = planner_node(state)
        assert result["current_fix_id"] == "fix-2"

    def test_iteration_counter_increments(self):
        state = _base_state(iteration=5, fix_plan=[], approved_fix_ids=[])
        result = planner_node(state)
        assert result["iteration"] == 6

    def test_iteration_guard_stops_at_50(self):
        fix = _fix_item("fix-1")
        state = _base_state(
            fix_plan=[fix],
            approved_fix_ids=["fix-1"],
            iteration=50,
        )
        result = planner_node(state)
        assert result["current_fix_id"] is None
        assert route_after_planner({**state, **result}) == "reporter"

    def test_no_approved_id_for_existing_fix_routes_to_reporter(self):
        fix = _fix_item("fix-1")
        state = _base_state(
            fix_plan=[fix],
            approved_fix_ids=[],  # fix exists but not approved
        )
        result = planner_node(state)
        assert result["current_fix_id"] is None


# ===========================================================================
# route_after_planner
# ===========================================================================

class TestRouteAfterPlanner:

    def test_current_fix_id_routes_to_executor(self):
        state = _base_state(current_fix_id="fix-1")
        assert route_after_planner(state) == "executor"

    def test_no_current_fix_id_routes_to_reporter(self):
        state = _base_state(current_fix_id=None)
        assert route_after_planner(state) == "reporter"


# ===========================================================================
# route_after_verifier
# ===========================================================================

class TestRouteAfterVerifier:

    def test_successful_fix_routes_to_planner(self):
        state = _base_state(
            current_fix_id="fix-1",
            retry_count=0,
            executed_fixes=[_fix_result("fix-1", success=True)],
        )
        assert route_after_verifier(state) == "planner"

    def test_failed_fix_with_retry_remaining_routes_to_executor(self):
        state = _base_state(
            current_fix_id="fix-1",
            retry_count=1,  # > 0 = in retry mode
            executed_fixes=[],
            failed_fixes=[_fix_result("fix-1", success=False)],
        )
        assert route_after_verifier(state) == "executor"

    def test_failed_fix_retry_count_zero_routes_to_planner(self):
        # No retries remaining (retry_count was reset after exceeding max)
        state = _base_state(
            current_fix_id="fix-1",
            retry_count=0,
            executed_fixes=[],
            failed_fixes=[_fix_result("fix-1", success=False)],
        )
        assert route_after_verifier(state) == "planner"

    def test_no_current_fix_id_routes_to_planner(self):
        state = _base_state(current_fix_id=None, retry_count=0)
        assert route_after_verifier(state) == "planner"


# ===========================================================================
# _compute_before_after
# ===========================================================================

class TestComputeBeforeAfter:

    def test_resolved_checks_appear_in_checks_improved(self):
        original_report = {
            "findings": [
                {"check_id": "C2", "pillar": "Completeness"},
                {"check_id": "C6", "pillar": "Completeness"},
            ],
            "pillars": {},
        }
        # Post-fix only C6 remains (C2 resolved)
        post_fix = [_finding("C6", "Completeness")]
        result = _compute_before_after(original_report, post_fix)
        assert "C2" in result["checks_improved"]
        assert "C6" not in result["checks_improved"]

    def test_unresolved_checks_appear_in_checks_unchanged(self):
        original_report = {
            "findings": [
                {"check_id": "C2"},
                {"check_id": "C6"},
            ],
            "pillars": {},
        }
        # Both remain
        post_fix = [_finding("C2"), _finding("C6")]
        result = _compute_before_after(original_report, post_fix)
        assert "C2" in result["checks_unchanged"]
        assert "C6" in result["checks_unchanged"]
        assert result["checks_improved"] == []

    def test_all_checks_resolved_all_improved(self):
        original_report = {
            "findings": [{"check_id": "C2"}, {"check_id": "C6"}],
            "pillars": {},
        }
        post_fix = []  # nothing remains
        result = _compute_before_after(original_report, post_fix)
        assert sorted(result["checks_improved"]) == ["C2", "C6"]
        assert result["checks_unchanged"] == []

    def test_current_pillars_computed_from_post_fix_findings(self):
        original_report = {"findings": [{"check_id": "C1"}], "pillars": {}}
        post_fix = []  # all resolved
        result = _compute_before_after(original_report, post_fix)
        # With no findings, Completeness score should be 1.0 (all checks pass)
        current_comp = result["current_pillars"].get("Completeness", {})
        if current_comp:
            assert current_comp["score"] == 1.0

    def test_original_pillars_preserved_verbatim(self):
        original_pillars = {"Completeness": {"score": 0.5, "checks_passed": 3, "checks_total": 6}}
        original_report = {"findings": [], "pillars": original_pillars}
        result = _compute_before_after(original_report, [])
        assert result["original_pillars"] == original_pillars

    def test_mcp_before_propagated_from_original_report(self):
        mcp_data = [{"question": "q1", "response": "r1", "classification": "ANSWERED"}]
        original_report = {"findings": [], "pillars": {}, "mcp_simulation": mcp_data}
        result = _compute_before_after(original_report, [])
        assert result["mcp_before"] == mcp_data


# ===========================================================================
# _build_schema_snippet_content
# ===========================================================================

class TestBuildSchemaSnippetContent:

    def test_schema_is_valid_json_ld(self):
        merchant = make_merchant(policies=make_policies(
            refund="Returns within 30 days.",
            shipping="Ships to United States.",
        ))
        content = _build_schema_snippet_content(merchant)
        schema = json.loads(content)
        assert schema["@context"] == "https://schema.org/"
        assert schema["@type"] == "Product"

    def test_return_days_extracted_from_policy(self):
        merchant = make_merchant(policies=make_policies(
            refund="We accept returns within 14 days of delivery.",
            shipping="Ships to US.",
        ))
        content = _build_schema_snippet_content(merchant)
        schema = json.loads(content)
        return_days = (
            schema["offers"]["hasMerchantReturnPolicy"]["merchantReturnDays"]
        )
        assert return_days == 14

    def test_default_return_days_when_no_number_in_policy(self):
        merchant = make_merchant(policies=make_policies(
            refund="We accept all returns.",
            shipping="US shipping.",
        ))
        content = _build_schema_snippet_content(merchant)
        schema = json.loads(content)
        return_days = (
            schema["offers"]["hasMerchantReturnPolicy"]["merchantReturnDays"]
        )
        assert return_days == 30  # default

    def test_schema_contains_liquid_template_placeholders(self):
        merchant = make_merchant()
        content = _build_schema_snippet_content(merchant)
        assert "product.title" in content
        assert "product.selected_or_first_available_variant.price" in content

    def test_shipping_destinations_extracted(self):
        merchant = make_merchant(policies=make_policies(
            shipping="We ship to the United States and Canada.",
        ))
        content = _build_schema_snippet_content(merchant)
        schema = json.loads(content)
        destinations = schema["offers"]["shippingDetails"]["shippingDestination"]
        codes = [d["addressCountry"] for d in destinations]
        assert "US" in codes
        assert "CA" in codes


# ===========================================================================
# _extract_shipping_country_codes
# ===========================================================================

class TestExtractShippingCountryCodes:

    def test_united_states_maps_to_us(self):
        assert "US" in _extract_shipping_country_codes("Ships to United States only.")

    def test_usa_maps_to_us(self):
        assert "US" in _extract_shipping_country_codes("We ship within USA.")

    def test_canada_maps_to_ca(self):
        assert "CA" in _extract_shipping_country_codes("Ships to Canada.")

    def test_uk_maps_to_gb(self):
        assert "GB" in _extract_shipping_country_codes("Shipping available to UK.")

    def test_united_kingdom_maps_to_gb(self):
        assert "GB" in _extract_shipping_country_codes("We ship to United Kingdom.")

    def test_australia_maps_to_au(self):
        assert "AU" in _extract_shipping_country_codes("Australian orders welcome.")

    def test_international_maps_to_intl(self):
        assert "INTL" in _extract_shipping_country_codes("International shipping.")

    def test_worldwide_maps_to_intl(self):
        assert "INTL" in _extract_shipping_country_codes("Worldwide delivery.")

    def test_no_region_defaults_to_us(self):
        codes = _extract_shipping_country_codes("Ships to many places.")
        assert codes == ["US"]

    def test_empty_string_defaults_to_us(self):
        assert _extract_shipping_country_codes("") == ["US"]

    def test_no_duplicates_when_mentioned_twice(self):
        codes = _extract_shipping_country_codes("USA, US, United States shipping.")
        assert codes.count("US") == 1
