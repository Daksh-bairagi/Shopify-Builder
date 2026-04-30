"""
White-box tests for app/services/heuristics.py

Each of the 19 deterministic check functions is exercised against:
  - the happy path (check passes, returns empty list)
  - the failure path (check fires, returns a Finding with correct metadata)
  - every relevant boundary condition and edge case

Finding metadata assertions (check_id, pillar, severity) are explicit so that
any accidental change to the spec is immediately caught.
"""

from __future__ import annotations

import pytest

from app.services.heuristics import (
    check_catalog_eligibility,
    check_gtin_identifier,
    check_image_alt_text,
    check_inventory_tracking,
    check_llms_txt,
    check_markets_translation,
    check_metafield_definitions,
    check_offer_schema,
    check_oversell_risk,
    check_robot_crawlers,
    check_schema_availability,
    check_schema_price_consistency,
    check_seo_consistency,
    check_shipping_regions,
    check_sitemap,
    check_taxonomy_mapped,
    check_title_category_noun,
    check_variant_option_names,
    check_refund_timeframe,
    run_all_checks,
)

from tests.fixtures.merchant_data import (
    make_merchant,
    make_product,
    make_variant,
    make_image,
    make_option,
    make_policies,
    clean_store_admin,
    broken_store_admin,
)


# ===========================================================================
# D1a — check_robot_crawlers
# ===========================================================================

class TestCheckRobotCrawlers:

    def test_empty_robots_txt_passes(self):
        data = make_merchant(robots_txt="")
        assert check_robot_crawlers(data) == []

    def test_no_robots_txt_passes(self):
        data = make_merchant(robots_txt=None)
        # heuristic uses `data.robots_txt or ""` so None is safe
        assert check_robot_crawlers(data) == []

    def test_allow_all_wildcard_passes(self):
        data = make_merchant(robots_txt="User-agent: *\nAllow: /\n")
        assert check_robot_crawlers(data) == []

    def test_wildcard_disallow_without_named_bot_passes(self):
        # Wildcard block must NOT be treated as named-bot block
        data = make_merchant(robots_txt="User-agent: *\nDisallow: /\n")
        assert check_robot_crawlers(data) == []

    def test_gptbot_full_block_fires(self):
        data = make_merchant(robots_txt="User-agent: GPTBot\nDisallow: /\n")
        findings = check_robot_crawlers(data)
        assert len(findings) == 1
        f = findings[0]
        assert f.check_id == "D1a"
        assert f.pillar == "Discoverability"
        assert f.severity == "MEDIUM"

    def test_perplexitybot_full_block_fires(self):
        data = make_merchant(robots_txt="User-agent: PerplexityBot\nDisallow: /\n")
        findings = check_robot_crawlers(data)
        assert len(findings) == 1
        assert findings[0].check_id == "D1a"

    def test_both_bots_blocked_two_findings(self):
        data = make_merchant(
            robots_txt="User-agent: GPTBot\nDisallow: /\n\nUser-agent: PerplexityBot\nDisallow: /\n"
        )
        findings = check_robot_crawlers(data)
        assert len(findings) == 2

    def test_partial_path_disallow_does_not_fire(self):
        # Only blocking /admin is not a full-site block
        data = make_merchant(robots_txt="User-agent: GPTBot\nDisallow: /admin\n")
        assert check_robot_crawlers(data) == []

    def test_case_insensitive_bot_name(self):
        # Lowercase agent name
        data = make_merchant(robots_txt="User-agent: gptbot\nDisallow: /\n")
        findings = check_robot_crawlers(data)
        assert len(findings) == 1

    def test_gptbot_allowed_explicitly_after_wildcard_block(self):
        # Wildcard blocks everything but GPTBot is allowed → should NOT flag GPTBot
        robots = (
            "User-agent: *\nDisallow: /\n\n"
            "User-agent: GPTBot\nAllow: /\n"
        )
        data = make_merchant(robots_txt=robots)
        findings = check_robot_crawlers(data)
        # GPTBot is allowed — only wildcard fires, which isn't named → 0 findings
        assert all(f.check_id == "D1a" for f in findings)
        gptbot_findings = [f for f in findings if "GPTBot" in f.title]
        assert len(gptbot_findings) == 0

    def test_finding_affected_products_is_empty(self):
        data = make_merchant(robots_txt="User-agent: GPTBot\nDisallow: /\n")
        findings = check_robot_crawlers(data)
        assert findings[0].affected_products == []
        assert findings[0].affected_count == 0

    def test_d1a_severity_is_medium_not_critical(self):
        # Spec rule: D1a must be MEDIUM — not CRITICAL (doesn't affect Admin API pipeline)
        data = make_merchant(robots_txt="User-agent: PerplexityBot\nDisallow: /\n")
        assert check_robot_crawlers(data)[0].severity == "MEDIUM"


# ===========================================================================
# D1b — check_catalog_eligibility
# ===========================================================================

class TestCheckCatalogEligibility:

    def test_url_only_mode_skips_check(self):
        data = make_merchant(ingestion_mode="url_only")
        assert check_catalog_eligibility(data) == []

    def test_all_products_fully_eligible(self):
        p = make_product(
            id="p1",
            title="Running Shoe",
            variants=[make_variant(price="49.99")],
        )
        data = make_merchant(
            ingestion_mode="admin_token",
            products=[p],
            taxonomy_by_product={"p1": "gid://shopify/TaxonomyCategory/371"},
        )
        assert check_catalog_eligibility(data) == []

    def test_exactly_80_pct_eligible_no_finding(self):
        # 4 out of 5 eligible = 80% — boundary, should NOT fire
        eligible = [
            make_product(
                id=f"ok{i}",
                title="Running Shoe",
                variants=[make_variant(id=f"v{i}", price="29.99")],
            )
            for i in range(4)
        ]
        ineligible = make_product(
            id="bad",
            title="Bad Product",
            variants=[make_variant(id="vbad", price="29.99")],
        )
        taxonomy = {f"ok{i}": "gid://shopify/TaxonomyCategory/1" for i in range(4)}
        # bad has no taxonomy
        data = make_merchant(
            ingestion_mode="admin_token",
            products=eligible + [ineligible],
            taxonomy_by_product=taxonomy,
        )
        # 4/5 = 80% — not < 80%, so no finding
        assert check_catalog_eligibility(data) == []

    def test_below_80_pct_fires(self):
        # 3 out of 5 eligible = 60% — should fire
        eligible = [
            make_product(
                id=f"ok{i}",
                title="Running Shoe",
                variants=[make_variant(id=f"v{i}", price="29.99")],
            )
            for i in range(3)
        ]
        ineligible = [
            make_product(
                id=f"bad{i}",
                title="Bad Product",
                variants=[make_variant(id=f"vbad{i}", price="29.99")],
            )
            for i in range(2)
        ]
        taxonomy = {f"ok{i}": "gid://shopify/TaxonomyCategory/1" for i in range(3)}
        data = make_merchant(
            ingestion_mode="admin_token",
            products=eligible + ineligible,
            taxonomy_by_product=taxonomy,
        )
        findings = check_catalog_eligibility(data)
        assert len(findings) == 1
        assert findings[0].check_id == "D1b"
        assert findings[0].severity == "CRITICAL"

    def test_zero_price_makes_product_ineligible(self):
        p = make_product(
            id="p1",
            title="Running Shoe",
            variants=[make_variant(price="0.00")],
        )
        data = make_merchant(
            ingestion_mode="admin_token",
            products=[p],
            taxonomy_by_product={"p1": "gid://shopify/TaxonomyCategory/1"},
        )
        findings = check_catalog_eligibility(data)
        assert len(findings) == 1
        assert "p1" in findings[0].affected_products

    def test_missing_taxonomy_makes_product_ineligible(self):
        p = make_product(
            id="p1", title="Running Shoe",
            variants=[make_variant(price="29.99")]
        )
        data = make_merchant(
            ingestion_mode="admin_token",
            products=[p],
            taxonomy_by_product={},  # empty
        )
        findings = check_catalog_eligibility(data)
        assert len(findings) == 1

    def test_empty_title_makes_product_ineligible(self):
        p = make_product(
            id="p1", title="   ",  # whitespace-only title
            variants=[make_variant(price="29.99")]
        )
        data = make_merchant(
            ingestion_mode="admin_token",
            products=[p],
            taxonomy_by_product={"p1": "gid://shopify/TaxonomyCategory/1"},
        )
        findings = check_catalog_eligibility(data)
        assert len(findings) == 1

    def test_no_products_returns_no_findings(self):
        data = make_merchant(ingestion_mode="admin_token", products=[])
        assert check_catalog_eligibility(data) == []

    def test_affected_products_lists_ineligible_ids(self):
        eligible = make_product(
            id="good", title="Shoe", variants=[make_variant(price="9.99")]
        )
        bad1 = make_product(id="bad1", title="X", variants=[make_variant(id="bv1", price="0")])
        bad2 = make_product(id="bad2", title="Y", variants=[make_variant(id="bv2", price="0")])
        data = make_merchant(
            ingestion_mode="admin_token",
            products=[eligible, bad1, bad2],
            taxonomy_by_product={"good": "gid://shopify/TaxonomyCategory/1"},
        )
        findings = check_catalog_eligibility(data)
        assert len(findings) == 1
        assert "bad1" in findings[0].affected_products
        assert "bad2" in findings[0].affected_products
        assert "good" not in findings[0].affected_products


# ===========================================================================
# D2 — check_sitemap
# ===========================================================================

class TestCheckSitemap:

    def test_sitemap_present_with_products_passes(self):
        data = make_merchant(sitemap_present=True, sitemap_has_products=True)
        assert check_sitemap(data) == []

    def test_no_sitemap_fires_high(self):
        data = make_merchant(sitemap_present=False, sitemap_has_products=False)
        findings = check_sitemap(data)
        assert len(findings) == 1
        assert findings[0].check_id == "D2"
        assert findings[0].severity == "HIGH"

    def test_sitemap_present_but_no_products_fires(self):
        data = make_merchant(sitemap_present=True, sitemap_has_products=False)
        findings = check_sitemap(data)
        assert len(findings) == 1
        assert "no product" in findings[0].title.lower() or "contains no" in findings[0].title.lower()


# ===========================================================================
# D3 — check_llms_txt
# ===========================================================================

class TestCheckLlmsTxt:

    def test_llms_txt_present_passes(self):
        data = make_merchant(llms_txt="# My Store\n> We sell running gear.")
        assert check_llms_txt(data) == []

    def test_llms_txt_absent_fires_medium(self):
        data = make_merchant(llms_txt=None)
        findings = check_llms_txt(data)
        assert len(findings) == 1
        assert findings[0].check_id == "D3"
        assert findings[0].severity == "MEDIUM"

    def test_llms_txt_empty_string_is_considered_present(self):
        # llms_txt="" means file exists but is empty — check only fires on None
        data = make_merchant(llms_txt="")
        assert check_llms_txt(data) == []


# ===========================================================================
# D5 — check_markets_translation
# ===========================================================================

class TestCheckMarketsTranslation:

    def test_url_only_mode_skips(self):
        data = make_merchant(
            ingestion_mode="url_only",
            markets_by_product={"p1": {"fr": {"title_translated": False}}},
        )
        assert check_markets_translation(data) == []

    def test_no_markets_data_passes(self):
        data = make_merchant(ingestion_mode="admin_token", markets_by_product={})
        assert check_markets_translation(data) == []

    def test_all_translated_passes(self):
        data = make_merchant(
            ingestion_mode="admin_token",
            markets_by_product={
                "p1": {"fr": {"title_translated": True}, "de": {"title_translated": True}}
            },
        )
        assert check_markets_translation(data) == []

    def test_above_20_pct_untranslated_fires(self):
        # 3 out of 3 products untranslated = 100%
        markets = {
            f"p{i}": {f"fr_{i}": {"title_translated": False}} for i in range(3)
        }
        data = make_merchant(ingestion_mode="admin_token", markets_by_product=markets)
        findings = check_markets_translation(data)
        assert len(findings) == 1
        assert findings[0].check_id == "D5"
        assert findings[0].severity == "HIGH"

    def test_exactly_20_pct_no_finding(self):
        # threshold is > 0.20, so exactly 20% should NOT fire
        markets = {
            "p1": {"fr": {"title_translated": False}},   # untranslated
            "p2": {"fr": {"title_translated": True}},
            "p3": {"fr": {"title_translated": True}},
            "p4": {"fr": {"title_translated": True}},
            "p5": {"fr": {"title_translated": True}},
        }
        data = make_merchant(ingestion_mode="admin_token", markets_by_product=markets)
        # 1/5 = 20% — not > 20%, so no finding
        assert check_markets_translation(data) == []

    def test_affected_products_list_is_accurate(self):
        markets = {
            "p1": {"fr": {"title_translated": False}},
            "p2": {"fr": {"title_translated": True}},
        }
        data = make_merchant(ingestion_mode="admin_token", markets_by_product=markets)
        # Only 1 of 2 = 50% > 20%
        findings = check_markets_translation(data)
        assert len(findings) == 1
        assert "p1" in findings[0].affected_products
        assert "p2" not in findings[0].affected_products


# ===========================================================================
# C1 — check_taxonomy_mapped
# ===========================================================================

class TestCheckTaxonomyMapped:

    def test_url_only_mode_skips(self):
        data = make_merchant(ingestion_mode="url_only")
        assert check_taxonomy_mapped(data) == []

    def test_all_mapped_passes(self):
        p = make_product(id="p1")
        data = make_merchant(
            ingestion_mode="admin_token",
            products=[p],
            taxonomy_by_product={"p1": "gid://shopify/TaxonomyCategory/1"},
        )
        assert check_taxonomy_mapped(data) == []

    def test_missing_taxonomy_fires_critical(self):
        p = make_product(id="p1")
        data = make_merchant(
            ingestion_mode="admin_token",
            products=[p],
            taxonomy_by_product={},
        )
        findings = check_taxonomy_mapped(data)
        assert len(findings) == 1
        assert findings[0].check_id == "C1"
        assert findings[0].severity == "CRITICAL"
        assert "p1" in findings[0].affected_products

    def test_whitespace_gid_counts_as_missing(self):
        p = make_product(id="p1")
        data = make_merchant(
            ingestion_mode="admin_token",
            products=[p],
            taxonomy_by_product={"p1": "   "},
        )
        findings = check_taxonomy_mapped(data)
        assert len(findings) == 1

    def test_only_one_finding_even_if_multiple_products_missing(self):
        products = [make_product(id=f"p{i}") for i in range(5)]
        data = make_merchant(
            ingestion_mode="admin_token",
            products=products,
            taxonomy_by_product={},
        )
        findings = check_taxonomy_mapped(data)
        assert len(findings) == 1
        assert findings[0].affected_count == 5


# ===========================================================================
# C2 — check_title_category_noun
# ===========================================================================

class TestCheckTitleCategoryNoun:

    def test_no_llm_results_returns_no_findings(self):
        data = make_merchant()
        assert check_title_category_noun(data, []) == []

    def test_all_titles_have_noun_passes(self):
        data = make_merchant()
        llm_results = [
            {"product_id": "p1", "title_contains_category_noun": True}
        ]
        assert check_title_category_noun(data, llm_results) == []

    def test_title_missing_noun_fires_critical(self):
        data = make_merchant()
        llm_results = [
            {"product_id": "p1", "title_contains_category_noun": False},
        ]
        findings = check_title_category_noun(data, llm_results)
        assert len(findings) == 1
        assert findings[0].check_id == "C2"
        assert findings[0].severity == "CRITICAL"
        assert "p1" in findings[0].affected_products

    def test_mixed_results_only_reports_failing(self):
        data = make_merchant()
        llm_results = [
            {"product_id": "p1", "title_contains_category_noun": True},
            {"product_id": "p2", "title_contains_category_noun": False},
            {"product_id": "p3", "title_contains_category_noun": False},
        ]
        findings = check_title_category_noun(data, llm_results)
        assert len(findings) == 1
        assert "p1" not in findings[0].affected_products
        assert "p2" in findings[0].affected_products
        assert "p3" in findings[0].affected_products


# ===========================================================================
# C3 — check_variant_option_names
# ===========================================================================

class TestCheckVariantOptionNames:

    def test_meaningful_option_names_pass(self):
        p = make_product(options=[make_option("Size"), make_option("Color")])
        data = make_merchant(products=[p])
        assert check_variant_option_names(data) == []

    def test_title_placeholder_fires(self):
        p = make_product(id="p1", options=[make_option("Title", ["One Size"])])
        data = make_merchant(products=[p])
        findings = check_variant_option_names(data)
        assert len(findings) == 1
        assert findings[0].check_id == "C3"
        assert findings[0].severity == "HIGH"

    def test_option1_fires(self):
        p = make_product(id="p1", options=[make_option("Option1")])
        data = make_merchant(products=[p])
        assert len(check_variant_option_names(data)) == 1

    def test_option2_fires(self):
        p = make_product(id="p1", options=[make_option("Option2")])
        data = make_merchant(products=[p])
        assert len(check_variant_option_names(data)) == 1

    def test_option3_fires(self):
        p = make_product(id="p1", options=[make_option("Option3")])
        data = make_merchant(products=[p])
        assert len(check_variant_option_names(data)) == 1

    def test_case_insensitive_detection(self):
        for name in ("OPTION1", "option1", "Option1", "TITLE"):
            p = make_product(id="p1", options=[make_option(name)])
            data = make_merchant(products=[p])
            assert len(check_variant_option_names(data)) == 1, f"Expected finding for option name {name!r}"

    def test_only_one_finding_even_if_multiple_products_fail(self):
        products = [
            make_product(id=f"p{i}", options=[make_option("Option1")]) for i in range(3)
        ]
        data = make_merchant(products=products)
        findings = check_variant_option_names(data)
        assert len(findings) == 1
        assert findings[0].affected_count == 3

    def test_one_good_option_on_product_with_bad_option_still_flags_product(self):
        p = make_product(
            id="p1",
            options=[make_option("Size"), make_option("Option1")],
        )
        data = make_merchant(products=[p])
        findings = check_variant_option_names(data)
        assert len(findings) == 1
        assert "p1" in findings[0].affected_products


# ===========================================================================
# C4 — check_gtin_identifier
# ===========================================================================

class TestCheckGtinIdentifier:

    def test_vendor_and_sku_present_passes(self):
        p = make_product(vendor="BrandX", variants=[make_variant(sku="SKU-123")])
        data = make_merchant(products=[p])
        assert check_gtin_identifier(data) == []

    def test_missing_vendor_fires(self):
        p = make_product(id="p1", vendor="", variants=[make_variant(sku="SKU-123")])
        data = make_merchant(products=[p])
        findings = check_gtin_identifier(data)
        assert len(findings) == 1
        assert findings[0].check_id == "C4"
        assert "p1" in findings[0].affected_products

    def test_whitespace_vendor_fires(self):
        p = make_product(id="p1", vendor="   ", variants=[make_variant(sku="SKU-123")])
        data = make_merchant(products=[p])
        assert len(check_gtin_identifier(data)) == 1

    def test_missing_sku_fires(self):
        p = make_product(id="p1", vendor="BrandX", variants=[make_variant(sku="")])
        data = make_merchant(products=[p])
        assert len(check_gtin_identifier(data)) == 1

    def test_whitespace_sku_fires(self):
        p = make_product(id="p1", vendor="BrandX", variants=[make_variant(sku="   ")])
        data = make_merchant(products=[p])
        assert len(check_gtin_identifier(data)) == 1

    def test_product_with_no_variants_fires(self):
        p = make_product(id="p1", vendor="BrandX", variants=[])
        data = make_merchant(products=[p])
        findings = check_gtin_identifier(data)
        assert len(findings) == 1

    def test_severity_is_high(self):
        p = make_product(id="p1", vendor="", variants=[make_variant(sku="")])
        data = make_merchant(products=[p])
        assert check_gtin_identifier(data)[0].severity == "HIGH"


# ===========================================================================
# C5 — check_metafield_definitions
# ===========================================================================

class TestCheckMetafieldDefinitions:

    def test_url_only_mode_skips(self):
        data = make_merchant(ingestion_mode="url_only", metafield_definitions=[])
        assert check_metafield_definitions(data) == []

    def test_both_definitions_present_passes(self):
        data = make_merchant(
            ingestion_mode="admin_token",
            metafield_definitions=[
                {"key": "material", "namespace": "custom"},
                {"key": "care_instructions", "namespace": "custom"},
            ],
        )
        assert check_metafield_definitions(data) == []

    def test_no_definitions_fires(self):
        data = make_merchant(ingestion_mode="admin_token", metafield_definitions=[])
        findings = check_metafield_definitions(data)
        assert len(findings) == 1
        assert findings[0].check_id == "C5"
        assert findings[0].severity == "HIGH"

    def test_only_material_missing_fires(self):
        data = make_merchant(
            ingestion_mode="admin_token",
            metafield_definitions=[{"key": "care_instructions"}],
        )
        findings = check_metafield_definitions(data)
        assert len(findings) == 1
        assert "material" in findings[0].title

    def test_only_care_instructions_missing_fires(self):
        data = make_merchant(
            ingestion_mode="admin_token",
            metafield_definitions=[{"key": "material"}],
        )
        findings = check_metafield_definitions(data)
        assert len(findings) == 1
        assert "care_instructions" in findings[0].title

    def test_case_insensitive_key_matching(self):
        # Keys stored as uppercase should still match
        data = make_merchant(
            ingestion_mode="admin_token",
            metafield_definitions=[
                {"key": "MATERIAL"},
                {"key": "CARE_INSTRUCTIONS"},
            ],
        )
        assert check_metafield_definitions(data) == []

    def test_extra_definitions_do_not_cause_problems(self):
        data = make_merchant(
            ingestion_mode="admin_token",
            metafield_definitions=[
                {"key": "material"},
                {"key": "care_instructions"},
                {"key": "weight"},
                {"key": "dimensions"},
            ],
        )
        assert check_metafield_definitions(data) == []


# ===========================================================================
# C6 — check_image_alt_text
# ===========================================================================

class TestCheckImageAltText:

    def test_full_coverage_passes(self):
        p = make_product(
            images=[
                make_image(id="i1", alt="A nice shoe"),
                make_image(id="i2", alt="Side profile of shoe"),
            ]
        )
        data = make_merchant(products=[p])
        assert check_image_alt_text(data) == []

    def test_zero_images_across_all_products_no_finding(self):
        p = make_product(images=[])
        data = make_merchant(products=[p])
        assert check_image_alt_text(data) == []

    def test_exactly_70_pct_coverage_passes(self):
        # 7 out of 10 images have alt = exactly 70%, which should NOT fire (threshold is < 0.70)
        images = [
            make_image(id=f"i{i}", alt="alt text") for i in range(7)
        ] + [
            make_image(id=f"j{i}", alt=None) for i in range(3)
        ]
        p = make_product(images=images)
        data = make_merchant(products=[p])
        assert check_image_alt_text(data) == []

    def test_below_70_pct_fires_medium(self):
        # 6 out of 10 = 60% < 70%
        images = [
            make_image(id=f"i{i}", alt="alt") for i in range(6)
        ] + [
            make_image(id=f"j{i}", alt=None) for i in range(4)
        ]
        p = make_product(id="p1", images=images)
        data = make_merchant(products=[p])
        findings = check_image_alt_text(data)
        assert len(findings) == 1
        assert findings[0].check_id == "C6"
        assert findings[0].severity == "MEDIUM"

    def test_empty_string_alt_counts_as_missing(self):
        images = [
            make_image(id="i1", alt=""),    # empty → missing
            make_image(id="i2", alt=None),  # None → missing
            make_image(id="i3", alt="Shoe"),
        ]
        # 1 out of 3 covered = 33% → fires
        p = make_product(id="p1", images=images)
        data = make_merchant(products=[p])
        findings = check_image_alt_text(data)
        assert len(findings) == 1

    def test_whitespace_only_alt_counts_as_missing(self):
        images = [
            make_image(id="i1", alt="   "),   # whitespace only → missing
        ]
        p = make_product(id="p1", images=images)
        data = make_merchant(products=[p])
        findings = check_image_alt_text(data)
        assert len(findings) == 1

    def test_all_images_missing_alt_fires(self):
        p = make_product(
            id="p1",
            images=[make_image(id=f"i{i}", alt=None) for i in range(5)],
        )
        data = make_merchant(products=[p])
        assert len(check_image_alt_text(data)) == 1


# ===========================================================================
# Con1 — check_schema_price_consistency
# ===========================================================================

class TestCheckSchemaPriceConsistency:

    def _schema_with_price(self, price_str: str) -> dict:
        return {
            "@type": "Product",
            "offers": {"@type": "Offer", "price": price_str},
        }

    def test_no_schema_passes(self):
        data = make_merchant(schema_by_url={})
        assert check_schema_price_consistency(data) == []

    def test_exact_price_match_passes(self):
        p = make_product(id="p1", handle="shoe", variants=[make_variant(price="29.99")])
        data = make_merchant(
            products=[p],
            schema_by_url={
                "https://store.myshopify.com/products/shoe": [
                    self._schema_with_price("29.99")
                ]
            },
        )
        assert check_schema_price_consistency(data) == []

    def test_price_within_tolerance_passes(self):
        # diff = 0.009 < 0.01 → should pass
        p = make_product(id="p1", handle="shoe", variants=[make_variant(price="29.99")])
        data = make_merchant(
            products=[p],
            schema_by_url={
                "https://store.myshopify.com/products/shoe": [
                    self._schema_with_price("29.999")
                ]
            },
        )
        assert check_schema_price_consistency(data) == []

    def test_price_exactly_at_tolerance_passes(self):
        # diff = 0.005 — well below the > 0.01 threshold, must NOT fire
        p = make_product(id="p1", handle="shoe", variants=[make_variant(price="30.00")])
        data = make_merchant(
            products=[p],
            schema_by_url={
                "https://store.myshopify.com/products/shoe": [
                    self._schema_with_price("30.005")
                ]
            },
        )
        assert check_schema_price_consistency(data) == []

    def test_price_exceeds_tolerance_fires_critical(self):
        # diff = 0.011 > 0.01 → fires
        p = make_product(id="p1", handle="shoe", variants=[make_variant(price="30.00")])
        data = make_merchant(
            products=[p],
            schema_by_url={
                "https://store.myshopify.com/products/shoe": [
                    self._schema_with_price("29.98")
                ]
            },
        )
        findings = check_schema_price_consistency(data)
        assert len(findings) == 1
        assert findings[0].check_id == "Con1"
        assert findings[0].severity == "CRITICAL"

    def test_schema_url_with_no_matching_product_handle_is_ignored(self):
        p = make_product(id="p1", handle="shoe", variants=[make_variant(price="29.99")])
        data = make_merchant(
            products=[p],
            schema_by_url={
                "https://store.myshopify.com/products/completely-different": [
                    self._schema_with_price("1.00")
                ]
            },
        )
        assert check_schema_price_consistency(data) == []

    def test_schema_price_at_top_level_is_extracted(self):
        p = make_product(id="p1", handle="shoe", variants=[make_variant(price="50.00")])
        data = make_merchant(
            products=[p],
            schema_by_url={
                "https://store.myshopify.com/products/shoe": [
                    {"@type": "Product", "price": "49.00"}  # direct price field
                ]
            },
        )
        findings = check_schema_price_consistency(data)
        assert len(findings) == 1


# ===========================================================================
# Con2 — check_schema_availability
# ===========================================================================

class TestCheckSchemaAvailability:

    def _make_schema(self, availability: str) -> dict:
        return {
            "@type": "Product",
            "offers": {"@type": "Offer", "availability": availability},
        }

    def test_no_schema_passes(self):
        data = make_merchant(schema_by_url={})
        assert check_schema_availability(data) == []

    def test_schema_in_stock_matches_inventory_passes(self):
        p = make_product(
            id="p1", handle="shoe",
            variants=[make_variant(inventory_quantity=10, inventory_management="shopify")],
        )
        data = make_merchant(
            products=[p],
            schema_by_url={
                "https://store.myshopify.com/products/shoe": [
                    self._make_schema("https://schema.org/InStock")
                ]
            },
        )
        assert check_schema_availability(data) == []

    def test_schema_out_of_stock_matches_inventory_passes(self):
        p = make_product(
            id="p1", handle="shoe",
            variants=[
                make_variant(
                    inventory_quantity=0,
                    inventory_management="shopify",
                    inventory_policy="deny",
                )
            ],
        )
        data = make_merchant(
            products=[p],
            schema_by_url={
                "https://store.myshopify.com/products/shoe": [
                    self._make_schema("https://schema.org/OutOfStock")
                ]
            },
        )
        assert check_schema_availability(data) == []

    def test_schema_in_stock_but_actually_out_fires_critical(self):
        p = make_product(
            id="p1", handle="shoe",
            variants=[
                make_variant(
                    inventory_quantity=0,
                    inventory_management="shopify",
                    inventory_policy="deny",  # deny = won't oversell
                )
            ],
        )
        data = make_merchant(
            products=[p],
            schema_by_url={
                "https://store.myshopify.com/products/shoe": [
                    self._make_schema("https://schema.org/InStock")
                ]
            },
        )
        findings = check_schema_availability(data)
        assert len(findings) == 1
        assert findings[0].check_id == "Con2"
        assert findings[0].severity == "CRITICAL"

    def test_untracked_inventory_considered_in_stock(self):
        # inventory_management=None → assume available → matches InStock schema
        p = make_product(
            id="p1", handle="shoe",
            variants=[make_variant(inventory_management=None, inventory_quantity=0)],
        )
        data = make_merchant(
            products=[p],
            schema_by_url={
                "https://store.myshopify.com/products/shoe": [
                    self._make_schema("https://schema.org/InStock")
                ]
            },
        )
        assert check_schema_availability(data) == []

    def test_schema_out_but_actually_in_stock_fires(self):
        p = make_product(
            id="p1", handle="shoe",
            variants=[make_variant(inventory_quantity=5, inventory_management="shopify")],
        )
        data = make_merchant(
            products=[p],
            schema_by_url={
                "https://store.myshopify.com/products/shoe": [
                    self._make_schema("https://schema.org/OutOfStock")
                ]
            },
        )
        findings = check_schema_availability(data)
        assert len(findings) == 1


# ===========================================================================
# Con3 — check_seo_consistency
# ===========================================================================

class TestCheckSeoConsistency:

    def test_url_only_mode_skips(self):
        data = make_merchant(ingestion_mode="url_only")
        assert check_seo_consistency(data) == []

    def test_seo_title_shares_words_passes(self):
        p = make_product(id="p1", title="Classic Running Shoe")
        data = make_merchant(
            ingestion_mode="admin_token",
            products=[p],
            seo_by_product={"p1": {"metaTitle": "Classic Running Shoe — BrandX"}},
        )
        assert check_seo_consistency(data) == []

    def test_no_seo_data_passes(self):
        p = make_product(id="p1", title="Running Shoe")
        data = make_merchant(
            ingestion_mode="admin_token",
            products=[p],
            seo_by_product={},
        )
        assert check_seo_consistency(data) == []

    def test_empty_meta_title_skipped(self):
        p = make_product(id="p1", title="Running Shoe")
        data = make_merchant(
            ingestion_mode="admin_token",
            products=[p],
            seo_by_product={"p1": {"metaTitle": ""}},
        )
        assert check_seo_consistency(data) == []

    def test_no_shared_meaningful_words_fires_medium(self):
        p = make_product(id="p1", title="Running Shoe")
        data = make_merchant(
            ingestion_mode="admin_token",
            products=[p],
            seo_by_product={"p1": {"metaTitle": "Amazing Deal ZXQW 2026"}},
        )
        findings = check_seo_consistency(data)
        assert len(findings) == 1
        assert findings[0].check_id == "Con3"
        assert findings[0].severity == "MEDIUM"

    def test_only_short_words_in_title_skipped(self):
        # Product title has only 1-2 char words → product_words is empty → no finding
        p = make_product(id="p1", title="A B C")
        data = make_merchant(
            ingestion_mode="admin_token",
            products=[p],
            seo_by_product={"p1": {"metaTitle": "Completely Different Text"}},
        )
        assert check_seo_consistency(data) == []


# ===========================================================================
# T1 — check_refund_timeframe
# ===========================================================================

class TestCheckRefundTimeframe:

    def test_explicit_days_mention_passes(self):
        data = make_merchant(policies=make_policies(refund="Returns accepted within 30 days."))
        assert check_refund_timeframe(data) == []

    def test_business_days_mention_passes(self):
        data = make_merchant(policies=make_policies(refund="14 business days return window."))
        assert check_refund_timeframe(data) == []

    def test_no_refund_policy_fires(self):
        data = make_merchant(policies=make_policies(refund=""))
        findings = check_refund_timeframe(data)
        assert len(findings) == 1
        assert findings[0].check_id == "T1"
        assert findings[0].severity == "HIGH"

    def test_vague_policy_fires(self):
        data = make_merchant(policies=make_policies(refund="We handle refunds case by case."))
        assert len(check_refund_timeframe(data)) == 1

    def test_percent_number_does_not_satisfy(self):
        # "30%" is not "30 days"
        data = make_merchant(policies=make_policies(refund="Get 30% back on all returns."))
        findings = check_refund_timeframe(data)
        assert len(findings) == 1

    def test_numeric_day_patterns_satisfy(self):
        for policy in [
            "7 days",
            "7 day",
            "7 business days",
            "7 business day",
            "Returns within 60 days of purchase",
        ]:
            data = make_merchant(policies=make_policies(refund=policy))
            assert check_refund_timeframe(data) == [], f"Should pass for: {policy!r}"


# ===========================================================================
# T2 — check_shipping_regions
# ===========================================================================

class TestCheckShippingRegions:

    def test_us_mentioned_passes(self):
        data = make_merchant(policies=make_policies(shipping="Ships to United States only."))
        assert check_shipping_regions(data) == []

    def test_usa_abbreviation_passes(self):
        data = make_merchant(policies=make_policies(shipping="Shipping within USA."))
        assert check_shipping_regions(data) == []

    def test_worldwide_passes(self):
        data = make_merchant(policies=make_policies(shipping="We ship worldwide."))
        assert check_shipping_regions(data) == []

    def test_international_passes(self):
        data = make_merchant(policies=make_policies(shipping="International shipping available."))
        assert check_shipping_regions(data) == []

    def test_canada_passes(self):
        data = make_merchant(policies=make_policies(shipping="Ships to Canada and USA."))
        assert check_shipping_regions(data) == []

    def test_no_region_fires_high(self):
        data = make_merchant(policies=make_policies(shipping="We ship to many places."))
        findings = check_shipping_regions(data)
        assert len(findings) == 1
        assert findings[0].check_id == "T2"
        assert findings[0].severity == "HIGH"

    def test_empty_shipping_policy_fires(self):
        data = make_merchant(policies=make_policies(shipping=""))
        assert len(check_shipping_regions(data)) == 1

    def test_word_boundary_prevents_false_match(self):
        # "domesticated" should NOT match "domestic"
        data = make_merchant(policies=make_policies(shipping="We use domesticated shipping practices."))
        findings = check_shipping_regions(data)
        # "domestic" wouldn't match due to word boundary... but actually
        # "domestic" IS in the keyword list - let's check what the heuristic uses
        # The regex uses \b so "domestic" with word boundary must be a whole word
        # "domesticated" — \bdomestic\b does NOT match because after 'c' comes 'a' (word char)
        assert len(findings) == 1


# ===========================================================================
# T4 — check_offer_schema
# ===========================================================================

class TestCheckOfferSchema:

    def test_no_schema_fires_with_both_parts_missing(self):
        data = make_merchant(schema_by_url={})
        findings = check_offer_schema(data)
        assert len(findings) == 1
        assert findings[0].check_id == "T4"
        assert findings[0].severity == "CRITICAL"
        assert "OfferShippingDetails" in findings[0].title
        assert "MerchantReturnPolicy" in findings[0].title

    def test_both_parts_present_passes(self):
        schema = {
            "@type": "Product",
            "offers": {
                "@type": "Offer",
                "shippingDetails": {"@type": "OfferShippingDetails"},
                "hasMerchantReturnPolicy": {"@type": "MerchantReturnPolicy"},
            },
        }
        data = make_merchant(
            schema_by_url={"https://store.myshopify.com/products/shoe": [schema]}
        )
        assert check_offer_schema(data) == []

    def test_only_shipping_present_fires_for_return(self):
        schema = {
            "@type": "Product",
            "offers": {
                "@type": "Offer",
                "shippingDetails": {"@type": "OfferShippingDetails"},
            },
        }
        data = make_merchant(
            schema_by_url={"https://store.myshopify.com/products/shoe": [schema]}
        )
        findings = check_offer_schema(data)
        assert len(findings) == 1
        assert "MerchantReturnPolicy" in findings[0].title

    def test_only_return_present_fires_for_shipping(self):
        schema = {
            "@type": "Product",
            "offers": {
                "@type": "Offer",
                "hasMerchantReturnPolicy": {"@type": "MerchantReturnPolicy"},
            },
        }
        data = make_merchant(
            schema_by_url={"https://store.myshopify.com/products/shoe": [schema]}
        )
        findings = check_offer_schema(data)
        assert len(findings) == 1
        assert "OfferShippingDetails" in findings[0].title

    def test_schema_detection_is_case_insensitive(self):
        # Block string contains lowercase variants
        schema = {"type": "product", "offershippingdetails": True, "merchantreturnpolicy": True}
        data = make_merchant(
            schema_by_url={"https://store.myshopify.com/products/shoe": [schema]}
        )
        assert check_offer_schema(data) == []


# ===========================================================================
# A1 — check_inventory_tracking
# ===========================================================================

class TestCheckInventoryTracking:

    def test_all_tracked_passes(self):
        p = make_product(variants=[make_variant(inventory_management="shopify")])
        data = make_merchant(products=[p])
        assert check_inventory_tracking(data) == []

    def test_untracked_variant_fires_high(self):
        p = make_product(
            id="p1",
            variants=[make_variant(inventory_management=None)],
        )
        data = make_merchant(products=[p])
        findings = check_inventory_tracking(data)
        assert len(findings) == 1
        assert findings[0].check_id == "A1"
        assert findings[0].severity == "HIGH"
        assert "p1" in findings[0].affected_products

    def test_product_with_mixed_variants_only_one_untracked_fires(self):
        p = make_product(
            id="p1",
            variants=[
                make_variant(id="v1", inventory_management="shopify"),
                make_variant(id="v2", inventory_management=None),  # untracked
            ],
        )
        data = make_merchant(products=[p])
        assert len(check_inventory_tracking(data)) == 1

    def test_single_finding_for_multiple_bad_products(self):
        products = [
            make_product(id=f"p{i}", variants=[make_variant(id=f"v{i}", inventory_management=None)])
            for i in range(4)
        ]
        data = make_merchant(products=products)
        findings = check_inventory_tracking(data)
        assert len(findings) == 1
        assert findings[0].affected_count == 4


# ===========================================================================
# A2 — check_oversell_risk
# ===========================================================================

class TestCheckOversellRisk:

    def test_deny_policy_tracked_passes(self):
        p = make_product(
            variants=[
                make_variant(inventory_management="shopify", inventory_policy="deny")
            ]
        )
        data = make_merchant(products=[p])
        assert check_oversell_risk(data) == []

    def test_tracked_with_continue_fires_critical(self):
        p = make_product(
            id="p1",
            variants=[
                make_variant(
                    inventory_management="shopify",
                    inventory_policy="continue",
                )
            ],
        )
        data = make_merchant(products=[p])
        findings = check_oversell_risk(data)
        assert len(findings) == 1
        assert findings[0].check_id == "A2"
        assert findings[0].severity == "CRITICAL"

    def test_untracked_with_continue_does_not_fire(self):
        # Only fires when management=shopify AND policy=continue
        # management=None means Shopify isn't tracking it, so oversell risk rule doesn't apply
        p = make_product(
            id="p1",
            variants=[
                make_variant(inventory_management=None, inventory_policy="continue")
            ],
        )
        data = make_merchant(products=[p])
        assert check_oversell_risk(data) == []

    def test_severity_is_critical(self):
        p = make_product(
            id="p1",
            variants=[make_variant(inventory_management="shopify", inventory_policy="continue")],
        )
        data = make_merchant(products=[p])
        assert check_oversell_risk(data)[0].severity == "CRITICAL"


# ===========================================================================
# run_all_checks — integration
# ===========================================================================

class TestRunAllChecks:

    def test_clean_store_returns_no_findings(self):
        findings = run_all_checks(clean_store_admin())
        assert findings == [], f"Expected clean store to pass all checks, got: {[f.check_id for f in findings]}"

    def test_broken_store_returns_many_findings(self):
        findings = run_all_checks(broken_store_admin())
        assert len(findings) >= 8, "Expected broken store to produce many findings"

    def test_findings_sorted_critical_first(self):
        findings = run_all_checks(broken_store_admin())
        severities = [f.severity for f in findings]
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
        for i in range(len(severities) - 1):
            assert order[severities[i]] <= order[severities[i + 1]], (
                f"Severity ordering violated: {severities[i]} before {severities[i+1]}"
            )

    def test_each_finding_has_required_fields(self):
        findings = run_all_checks(broken_store_admin())
        for f in findings:
            assert f.id, "Finding must have id"
            assert f.check_id, "Finding must have check_id"
            assert f.pillar, "Finding must have pillar"
            assert f.severity in ("CRITICAL", "HIGH", "MEDIUM")
            assert f.title
            assert f.detail
            assert f.fix_instruction
            assert isinstance(f.affected_products, list)
            assert f.affected_count == len(f.affected_products)

    def test_d1a_severity_never_critical(self):
        # Spec rule: D1a (robots.txt) must always be MEDIUM
        data = make_merchant(
            robots_txt="User-agent: GPTBot\nDisallow: /\n"
        )
        findings = run_all_checks(data)
        d1a = [f for f in findings if f.check_id == "D1a"]
        for f in d1a:
            assert f.severity == "MEDIUM", "D1a must be MEDIUM, never CRITICAL"

    def test_url_only_mode_skips_admin_checks(self):
        data = make_merchant(
            ingestion_mode="url_only",
            products=[make_product()],
        )
        findings = run_all_checks(data)
        admin_only_checks = {"D1b", "C1", "C5", "Con3", "D5"}
        fired_check_ids = {f.check_id for f in findings}
        for check_id in admin_only_checks:
            assert check_id not in fired_check_ids, f"{check_id} must not fire in url_only mode"

    def test_same_check_id_not_duplicated_in_output(self):
        # D1a is exempt: it intentionally creates one Finding PER blocked bot
        PER_BOT_CHECKS = {"D1a"}
        findings = run_all_checks(broken_store_admin())
        check_id_counts: dict[str, int] = {}
        for f in findings:
            check_id_counts[f.check_id] = check_id_counts.get(f.check_id, 0) + 1
        for check_id, count in check_id_counts.items():
            if check_id in PER_BOT_CHECKS:
                continue
            assert count == 1, f"Check {check_id} produced {count} findings (expected 1)"
