"""
White-box tests for generate_fix_plan() in app/agent/nodes.py

Every mapping rule, deduplication guard, dependency-order contract, and
product-count cap is tested in isolation so a single line change in the
planner is caught immediately.
"""

from __future__ import annotations

import pytest

from app.agent.nodes import (
    DEPENDENCY_ORDER,
    generate_fix_plan,
)
from app.models.findings import Finding

from tests.fixtures.merchant_data import (
    make_merchant,
    make_product,
    make_variant,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SEVERITY_WEIGHT = {"CRITICAL": 10, "HIGH": 6, "MEDIUM": 2}


def _finding(
    check_id: str,
    pillar: str = "Completeness",
    severity: str = "HIGH",
    affected_products: list[str] | None = None,
    fix_instruction: str = "Fix this.",
    detail: str = "Detail.",
) -> Finding:
    affected = affected_products or []
    return Finding(
        id=f"f_{check_id}",
        pillar=pillar,
        check_id=check_id,
        check_name=f"Check {check_id}",
        severity=severity,
        weight=_SEVERITY_WEIGHT.get(severity, 6),
        title=f"Title for {check_id}",
        detail=detail,
        spec_citation="Spec",
        affected_products=affected,
        affected_count=len(affected),
        impact_statement="Impact.",
        fix_type="auto",
        fix_instruction=fix_instruction,
        fix_content=None,
    )


# ===========================================================================
# Basic mapping — check_id → fix_type
# ===========================================================================

class TestCheckToFixTypeMapping:

    def test_d1b_maps_to_map_taxonomy(self):
        product = make_product(id="p1", title="Running Shoe", variants=[make_variant(price="29.99")])
        merchant = make_merchant(products=[product], taxonomy_by_product={}, ingestion_mode="admin_token")
        findings = [_finding("D1b", "Discoverability", "CRITICAL", ["p1"])]
        plan = generate_fix_plan(findings, merchant_data=merchant)
        types = {item.type for item in plan}
        assert "map_taxonomy" in types

    def test_c2_maps_to_improve_title(self):
        findings = [_finding("C2", "Completeness", "CRITICAL", ["p1"])]
        plan = generate_fix_plan(findings)
        assert any(item.type == "improve_title" for item in plan)

    def test_c6_maps_to_generate_alt_text(self):
        findings = [_finding("C6", "Completeness", "MEDIUM", ["p1"])]
        plan = generate_fix_plan(findings)
        assert any(item.type == "generate_alt_text" for item in plan)

    def test_c5_maps_to_create_metafield_definitions(self):
        findings = [_finding("C5", "Completeness", "HIGH")]
        plan = generate_fix_plan(findings)
        assert any(item.type == "create_metafield_definitions" for item in plan)

    def test_t1_maps_to_suggest_policy_fix(self):
        findings = [_finding("T1", "Trust_Policies", "HIGH")]
        plan = generate_fix_plan(findings)
        assert any(item.type == "suggest_policy_fix" for item in plan)

    def test_t2_maps_to_suggest_policy_fix(self):
        findings = [_finding("T2", "Trust_Policies", "HIGH")]
        plan = generate_fix_plan(findings)
        assert any(item.type == "suggest_policy_fix" for item in plan)

    def test_d1a_has_no_auto_fix_excluded_from_plan(self):
        # D1a (robots.txt) is manual-only and NOT in CHECK_TO_FIX_TYPE
        findings = [_finding("D1a", "Discoverability")]
        plan = generate_fix_plan(findings)
        assert all(item.field != "D1a" for item in plan)

    def test_unknown_check_id_excluded_from_plan(self):
        findings = [_finding("FAKE_CHECK", "Completeness")]
        plan = generate_fix_plan(findings)
        assert plan == []

    def test_empty_findings_returns_empty_plan(self):
        assert generate_fix_plan([]) == []


# ===========================================================================
# Store-level deduplication
# ===========================================================================

class TestStoreLevelDeduplication:

    def test_t1_and_t2_produce_only_one_suggest_policy_fix(self):
        # Both T1 and T2 map to suggest_policy_fix which is STORE_LEVEL_TYPES
        # Only ONE fix item should be created
        findings = [
            _finding("T1", "Trust_Policies"),
            _finding("T2", "Trust_Policies"),
        ]
        plan = generate_fix_plan(findings)
        policy_fixes = [item for item in plan if item.type == "suggest_policy_fix"]
        assert len(policy_fixes) == 1, (
            f"Expected 1 suggest_policy_fix, got {len(policy_fixes)}"
        )

    def test_create_metafield_definitions_deduplicated(self):
        # Two findings mapping to create_metafield_definitions → only ONE item
        findings = [
            _finding("C5", "Completeness"),
            _finding("C5", "Completeness"),  # duplicate
        ]
        plan = generate_fix_plan(findings)
        defs = [item for item in plan if item.type == "create_metafield_definitions"]
        assert len(defs) == 1

    def test_store_level_items_have_empty_product_id(self):
        findings = [_finding("T1", "Trust_Policies")]
        plan = generate_fix_plan(findings)
        for item in plan:
            if item.type in {"suggest_policy_fix", "create_metafield_definitions",
                             "generate_schema_snippet"}:
                assert item.product_id == ""


# ===========================================================================
# Product-level deduplication
# ===========================================================================

class TestProductLevelDeduplication:

    def test_same_fix_type_and_product_not_duplicated(self):
        # Two findings both affect p1 and both map to improve_title
        findings = [
            _finding("C2", "Completeness", affected_products=["p1"]),
            _finding("C2", "Completeness", affected_products=["p1"]),  # same
        ]
        plan = generate_fix_plan(findings)
        title_fixes_for_p1 = [
            item for item in plan
            if item.type == "improve_title" and item.product_id == "p1"
        ]
        assert len(title_fixes_for_p1) == 1

    def test_same_fix_type_different_products_both_included(self):
        findings = [
            _finding("C2", "Completeness", affected_products=["p1", "p2"]),
        ]
        plan = generate_fix_plan(findings)
        title_product_ids = {
            item.product_id for item in plan if item.type == "improve_title"
        }
        assert "p1" in title_product_ids
        assert "p2" in title_product_ids

    def test_different_fix_types_for_same_product_both_included(self):
        # C2 → improve_title, C6 → generate_alt_text — both for p1
        findings = [
            _finding("C2", "Completeness", affected_products=["p1"]),
            _finding("C6", "Completeness", affected_products=["p1"]),
        ]
        plan = generate_fix_plan(findings)
        types_for_p1 = {item.type for item in plan if item.product_id == "p1"}
        assert "improve_title" in types_for_p1
        assert "generate_alt_text" in types_for_p1


# ===========================================================================
# Max 20 products cap per finding
# ===========================================================================

class TestProductCap:

    def test_more_than_20_products_capped_at_20(self):
        # 30 affected products — plan should cap at 20
        affected = [f"p{i}" for i in range(30)]
        findings = [_finding("C2", "Completeness", affected_products=affected)]
        plan = generate_fix_plan(findings)
        title_fixes = [item for item in plan if item.type == "improve_title"]
        assert len(title_fixes) == 20

    def test_exactly_20_products_not_capped(self):
        affected = [f"p{i}" for i in range(20)]
        findings = [_finding("C2", "Completeness", affected_products=affected)]
        plan = generate_fix_plan(findings)
        title_fixes = [item for item in plan if item.type == "improve_title"]
        assert len(title_fixes) == 20


# ===========================================================================
# Dependency ordering
# ===========================================================================

class TestDependencyOrdering:

    def test_map_taxonomy_before_improve_title(self):
        findings = [
            _finding("C2", "Completeness", affected_products=["p1"]),      # improve_title
            _finding("D1b", "Discoverability", "CRITICAL", ["p1"]),         # map_taxonomy (via D1b)
        ]
        product = make_product(id="p1", title="X", variants=[make_variant(price="1.99")])
        merchant = make_merchant(products=[product], taxonomy_by_product={}, ingestion_mode="admin_token")
        plan = generate_fix_plan(findings, merchant_data=merchant)

        types = [item.type for item in plan if item.product_id == "p1"]
        if "map_taxonomy" in types and "improve_title" in types:
            assert types.index("map_taxonomy") < types.index("improve_title")

    def test_create_metafield_definitions_before_fill_metafield(self):
        findings = [
            _finding("C5", "Completeness", affected_products=[]),   # create_metafield_definitions
            _finding("C6", "Completeness", affected_products=["p1"]),  # generate_alt_text (not fill)
        ]
        plan = generate_fix_plan(findings)
        types = [item.type for item in plan]
        if "create_metafield_definitions" in types and len(types) > 1:
            dep_idx = DEPENDENCY_ORDER.index("create_metafield_definitions") if "create_metafield_definitions" in DEPENDENCY_ORDER else 99
            for other in types:
                if other == "create_metafield_definitions":
                    continue
                other_dep_idx = DEPENDENCY_ORDER.index(other) if other in DEPENDENCY_ORDER else 99
                if other_dep_idx < dep_idx:
                    # Other comes before metafield_defs in order
                    assert types.index(other) <= types.index("create_metafield_definitions")

    def test_all_items_respect_dependency_order(self):
        # Build a plan with all common fix types and verify ordering is non-decreasing
        findings = [
            _finding("D1b", "Discoverability", "CRITICAL", ["p1"]),
            _finding("C5", "Completeness", "HIGH"),
            _finding("C2", "Completeness", "CRITICAL", ["p1"]),
            _finding("C6", "Completeness", "MEDIUM", ["p1"]),
            _finding("T1", "Trust_Policies", "HIGH"),
        ]
        product = make_product(id="p1", title="X", variants=[make_variant(price="9.99")])
        merchant = make_merchant(products=[product], taxonomy_by_product={}, ingestion_mode="admin_token")
        plan = generate_fix_plan(findings, merchant_data=merchant)

        dep_indices = [
            DEPENDENCY_ORDER.index(item.type) if item.type in DEPENDENCY_ORDER else 99
            for item in plan
        ]
        for i in range(len(dep_indices) - 1):
            assert dep_indices[i] <= dep_indices[i + 1], (
                f"Ordering violation: {plan[i].type} (idx {dep_indices[i]}) "
                f"before {plan[i+1].type} (idx {dep_indices[i+1]})"
            )


# ===========================================================================
# D1b special-case handling
# ===========================================================================

class TestD1bSpecialHandling:

    def test_d1b_product_missing_only_taxonomy_creates_map_taxonomy(self):
        product = make_product(
            id="p1",
            title="Running Shoe",
            variants=[make_variant(price="29.99")],
        )
        merchant = make_merchant(
            ingestion_mode="admin_token",
            products=[product],
            taxonomy_by_product={},  # missing taxonomy
        )
        findings = [_finding("D1b", "Discoverability", "CRITICAL", ["p1"])]
        plan = generate_fix_plan(findings, merchant_data=merchant)

        assert any(item.type == "map_taxonomy" and item.product_id == "p1" for item in plan)

    def test_d1b_product_missing_taxonomy_and_title_creates_both_items(self):
        product = make_product(
            id="p1",
            title="   ",           # empty title — triggers repair_catalog_eligibility
            variants=[make_variant(price="0.00")],  # zero price — also triggers repair
        )
        merchant = make_merchant(
            ingestion_mode="admin_token",
            products=[product],
            taxonomy_by_product={},
        )
        findings = [_finding("D1b", "Discoverability", "CRITICAL", ["p1"])]
        plan = generate_fix_plan(findings, merchant_data=merchant)

        # Should have BOTH map_taxonomy AND repair_catalog_eligibility
        types_for_p1 = {item.type for item in plan if item.product_id == "p1"}
        assert "map_taxonomy" in types_for_p1
        assert "repair_catalog_eligibility" in types_for_p1

    def test_d1b_product_missing_only_price_creates_repair_not_map_taxonomy(self):
        product = make_product(
            id="p1",
            title="Running Shoe",
            variants=[make_variant(price="0.00")],  # zero price only
        )
        merchant = make_merchant(
            ingestion_mode="admin_token",
            products=[product],
            taxonomy_by_product={"p1": "gid://shopify/TaxonomyCategory/1"},  # taxonomy exists
        )
        findings = [_finding("D1b", "Discoverability", "CRITICAL", ["p1"])]
        plan = generate_fix_plan(findings, merchant_data=merchant)

        types_for_p1 = {item.type for item in plan if item.product_id == "p1"}
        assert "map_taxonomy" not in types_for_p1
        assert "repair_catalog_eligibility" in types_for_p1

    def test_d1b_with_no_product_map_skips_gracefully(self):
        # D1b with affected products but no merchant_data with matching products
        findings = [_finding("D1b", "Discoverability", "CRITICAL", ["ghost_product"])]
        # No merchant_data → D1b falls through to generic mapping, must not crash
        plan = generate_fix_plan(findings)
        assert isinstance(plan, list)


# ===========================================================================
# Fix item metadata correctness
# ===========================================================================

class TestFixItemMetadata:

    def test_fix_id_is_unique_across_all_items(self):
        affected = [f"p{i}" for i in range(5)]
        findings = [_finding("C2", "Completeness", affected_products=affected)]
        plan = generate_fix_plan(findings)
        fix_ids = [item.fix_id for item in plan]
        assert len(fix_ids) == len(set(fix_ids)), "Duplicate fix_ids found in plan"

    def test_check_id_propagated_to_fix_item(self):
        findings = [_finding("C2", "Completeness", affected_products=["p1"])]
        plan = generate_fix_plan(findings)
        for item in plan:
            if item.product_id == "p1":
                assert item.check_id == "C2"

    def test_severity_propagated_from_finding(self):
        findings = [_finding("C2", "Completeness", "CRITICAL", ["p1"])]
        plan = generate_fix_plan(findings)
        for item in plan:
            if item.product_id == "p1":
                assert item.severity == "CRITICAL"

    def test_auto_fix_items_have_auto_fix_type(self):
        findings = [_finding("C2", "Completeness", affected_products=["p1"])]
        plan = generate_fix_plan(findings)
        auto_items = [i for i in plan if i.type == "improve_title"]
        assert all(item.fix_type == "auto" for item in auto_items)

    def test_copy_paste_items_have_copy_paste_fix_type(self):
        findings = [_finding("T1", "Trust_Policies")]
        plan = generate_fix_plan(findings)
        policy_items = [i for i in plan if i.type == "suggest_policy_fix"]
        assert all(item.fix_type == "copy_paste" for item in policy_items)
