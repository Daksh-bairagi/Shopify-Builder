"""
heuristics.py — 19 deterministic audit checks for ShopMirror.

All functions are pure (no side effects, no LLM calls).
All functions return list[Finding] — empty list means check passed.
"""
from __future__ import annotations

import re
from typing import Optional

from app.models.merchant import MerchantData
from app.models.findings import Finding

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SEVERITY_WEIGHT = {"CRITICAL": 10, "HIGH": 6, "MEDIUM": 2}
_SEVERITY_ORDER  = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}


def _w(severity: str) -> int:
    return _SEVERITY_WEIGHT.get(severity, 2)


def _make_finding(
    *,
    check_id: str,
    pillar: str,
    check_name: str,
    severity: str,
    title: str,
    detail: str,
    spec_citation: str,
    affected_products: list[str],
    impact_statement: str,
    fix_type: str,
    fix_instruction: str,
    fix_content: Optional[str] = None,
) -> Finding:
    pillar_abbrev = {
        "Discoverability": "disc",
        "Completeness": "comp",
        "Consistency": "con",
        "Trust_Policies": "trust",
        "Transaction": "trans",
    }.get(pillar, pillar.lower()[:4])

    finding_id = f"finding_{check_id}_{pillar_abbrev}"
    return Finding(
        id=finding_id,
        pillar=pillar,
        check_id=check_id,
        check_name=check_name,
        severity=severity,
        weight=_w(severity),
        title=title,
        detail=detail,
        spec_citation=spec_citation,
        affected_products=affected_products,
        affected_count=len(affected_products),
        impact_statement=impact_statement,
        fix_type=fix_type,
        fix_instruction=fix_instruction,
        fix_content=fix_content,
    )


# ---------------------------------------------------------------------------
# Pillar 1 — Discoverability
# ---------------------------------------------------------------------------

def check_robot_crawlers(data: MerchantData) -> list[Finding]:
    """D1a — Flag if PerplexityBot or GPTBot is fully blocked in robots.txt."""
    findings: list[Finding] = []
    try:
        robots = data.robots_txt or ""
        bots_to_check = {"PerplexityBot", "GPTBot"}

        # Parse robots.txt into user-agent blocks
        current_agents: list[str] = []
        disallows: dict[str, list[str]] = {}

        for raw_line in robots.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            lower = line.lower()
            if lower.startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip()
                current_agents = [agent]
                for a in current_agents:
                    disallows.setdefault(a, [])
            elif lower.startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                for a in current_agents:
                    disallows.setdefault(a, []).append(path)
            else:
                # Any other directive resets current block grouping logic only
                # (we keep current_agents active for multi-agent stanzas)
                pass

        for bot in bots_to_check:
            # Only flag explicit named-bot blocks, not wildcard
            named_blocked = False
            for agent, paths in disallows.items():
                if agent.lower() == bot.lower() and "/" in paths:
                    named_blocked = True
                    break
            if named_blocked:
                findings.append(_make_finding(
                    check_id="D1a",
                    pillar="Discoverability",
                    check_name="AI Crawler Access",
                    severity="MEDIUM",
                    title=f"{bot} fully blocked in robots.txt",
                    detail=(
                        f"{bot} is blocked from crawling your store via robots.txt "
                        f"(Disallow: /). This affects web-index AI platforms such as "
                        f"Perplexity and ChatGPT Browse — it does NOT affect Shopify "
                        f"Catalog ingestion, which uses the Admin API, not web crawling."
                    ),
                    spec_citation="Perplexity/OpenAI crawler documentation",
                    affected_products=[],
                    impact_statement=f"{bot} cannot index any product pages via web crawl.",
                    fix_type="manual",
                    fix_instruction=(
                        f"Remove or modify the 'Disallow: /' rule for {bot} in your "
                        f"robots.txt file. Consider using 'Allow: /products/' to "
                        f"permit product page indexing while still restricting other paths."
                    ),
                ))
    except Exception:
        pass
    return findings


def check_catalog_eligibility(data: MerchantData) -> list[Finding]:
    """D1b — ≥80% of products must have taxonomy GID, non-empty title, and price > 0."""
    findings: list[Finding] = []
    if data.ingestion_mode != "admin_token":
        return findings
    try:
        products = data.products
        if not products:
            return findings

        eligible_ids: list[str] = []
        ineligible_ids: list[str] = []

        for p in products:
            has_taxonomy = bool(data.taxonomy_by_product.get(p.id, "").strip())
            has_title = bool(p.title.strip())
            has_price = any(
                _safe_float(v.price) > 0 for v in p.variants
            ) if p.variants else False

            if has_taxonomy and has_title and has_price:
                eligible_ids.append(p.id)
            else:
                ineligible_ids.append(p.id)

        total = len(products)
        pct = len(eligible_ids) / total if total else 0

        if pct < 0.80:
            findings.append(_make_finding(
                check_id="D1b",
                pillar="Discoverability",
                check_name="Shopify Catalog Eligibility",
                severity="CRITICAL",
                title=f"Only {pct:.0%} of products eligible for Shopify Catalog",
                detail=(
                    "Shopify Catalog requires every product to have a taxonomy GID, "
                    "a non-empty title, and at least one variant with price > 0. "
                    f"{len(ineligible_ids)} of {total} products are missing one or more "
                    "of these fields and will be excluded from AI shopping platforms."
                ),
                spec_citation="Shopify Catalog API — required fields for AI catalog inclusion",
                affected_products=ineligible_ids,
                impact_statement=(
                    f"{len(ineligible_ids)} products ({1-pct:.0%}) excluded from "
                    "Shopify Catalog and invisible to ChatGPT/Copilot/Gemini shopping."
                ),
                fix_type="auto",
                fix_instruction=(
                    "Use the map_taxonomy tool to assign Shopify standard taxonomy GIDs "
                    "to unmapped products. Ensure all products have titles and at least "
                    "one variant with a price greater than zero."
                ),
            ))
    except Exception:
        pass
    return findings


def check_sitemap(data: MerchantData) -> list[Finding]:
    """D2 — Sitemap present and contains product URLs."""
    findings: list[Finding] = []
    try:
        if not data.sitemap_present:
            findings.append(_make_finding(
                check_id="D2",
                pillar="Discoverability",
                check_name="XML Sitemap",
                severity="HIGH",
                title="XML sitemap not found",
                detail=(
                    "No sitemap.xml was detected for this store. AI web crawlers rely on "
                    "sitemaps to discover and index product pages efficiently. Without a "
                    "sitemap, many product pages may never be crawled or indexed."
                ),
                spec_citation="Shopify SEO documentation",
                affected_products=[],
                impact_statement="All product pages at risk of not being discovered by AI crawlers.",
                fix_type="developer",
                fix_instruction=(
                    "Ensure your Shopify store has sitemap.xml enabled. In Shopify, "
                    "sitemaps are auto-generated at yourdomain.com/sitemap.xml. "
                    "If using a custom domain, verify DNS and Shopify settings are correct."
                ),
            ))
        elif not data.sitemap_has_products:
            findings.append(_make_finding(
                check_id="D2",
                pillar="Discoverability",
                check_name="XML Sitemap",
                severity="HIGH",
                title="Sitemap present but contains no product URLs",
                detail=(
                    "A sitemap.xml was found but it does not include product page URLs. "
                    "AI crawlers use the sitemap to discover product pages — without "
                    "product entries, individual product pages may not be indexed."
                ),
                spec_citation="Shopify SEO documentation",
                affected_products=[],
                impact_statement="Product pages missing from sitemap — crawler discovery severely limited.",
                fix_type="developer",
                fix_instruction=(
                    "Check your Shopify sitemap configuration. Shopify auto-includes "
                    "product pages in sitemap.xml. If using a custom sitemap plugin, "
                    "ensure product URLs are included in the generated sitemap."
                ),
            ))
    except Exception:
        pass
    return findings


def check_llms_txt(data: MerchantData) -> list[Finding]:
    """D3 — llms.txt file should be present."""
    findings: list[Finding] = []
    try:
        if data.llms_txt is None:
            findings.append(_make_finding(
                check_id="D3",
                pillar="Discoverability",
                check_name="llms.txt File",
                severity="MEDIUM",
                title="llms.txt file not found",
                detail=(
                    "llms.txt is an emerging standard that lets AI language models "
                    "understand your store's purpose, product categories, and policies "
                    "in a structured, LLM-readable format. Its absence means AI agents "
                    "must infer store context from unstructured content."
                ),
                spec_citation="llms.txt emerging standard (llmstxt.org)",
                affected_products=[],
                impact_statement="AI agents lack structured store context — classification accuracy reduced.",
                fix_type="manual",
                fix_instruction=(
                    "Create a /llms.txt file at your store root. Include: store name, "
                    "product categories, return policy summary, shipping regions, and "
                    "any AI-specific instructions. See llmstxt.org for the specification."
                ),
            ))
    except Exception:
        pass
    return findings


def check_markets_translation(data: MerchantData) -> list[Finding]:
    """D5 — >20% of products with untranslated market titles/descriptions → HIGH."""
    findings: list[Finding] = []
    if data.ingestion_mode != "admin_token":
        return findings
    try:
        markets_map = data.markets_by_product
        if not markets_map:
            return findings

        untranslated_ids: list[str] = []
        for product_id, markets in markets_map.items():
            has_untranslated = False
            for market_id, translation in markets.items():
                if not translation.get("title_translated", True):
                    has_untranslated = True
                    break
            if has_untranslated:
                untranslated_ids.append(product_id)

        total = len(markets_map)
        pct_untranslated = len(untranslated_ids) / total if total else 0

        if pct_untranslated > 0.20:
            findings.append(_make_finding(
                check_id="D5",
                pillar="Discoverability",
                check_name="Markets Translation",
                severity="HIGH",
                title=f"{pct_untranslated:.0%} of products have untranslated market content",
                detail=(
                    "AI shopping agents serving international markets match products using "
                    "localized titles and descriptions. Products without market translations "
                    "will not surface for queries in those markets' languages."
                ),
                spec_citation="Shopify Markets API",
                affected_products=untranslated_ids,
                impact_statement=(
                    f"{len(untranslated_ids)} products invisible to non-English AI shopping queries."
                ),
                fix_type="manual",
                fix_instruction=(
                    "Use Shopify Markets to add translated titles and descriptions for each "
                    "active market. Navigate to Settings > Markets, select each market, and "
                    "add translations for product titles and descriptions."
                ),
            ))
    except Exception:
        pass
    return findings


# ---------------------------------------------------------------------------
# Pillar 2 — Completeness
# ---------------------------------------------------------------------------

def check_taxonomy_mapped(data: MerchantData) -> list[Finding]:
    """C1 — All products must have a taxonomy GID (admin_token mode only)."""
    findings: list[Finding] = []
    if data.ingestion_mode != "admin_token":
        return findings
    try:
        missing_ids: list[str] = []
        for p in data.products:
            gid = data.taxonomy_by_product.get(p.id, "")
            if not gid or not gid.strip():
                missing_ids.append(p.id)

        if missing_ids:
            total = len(data.products)
            findings.append(_make_finding(
                check_id="C1",
                pillar="Completeness",
                check_name="Taxonomy Mapping",
                severity="CRITICAL",
                title=f"{len(missing_ids)} of {total} products have no taxonomy GID",
                detail=(
                    "Shopify Standard Product Taxonomy GIDs are required for AI agents to "
                    "classify and match products to category-based queries. Products without "
                    "a taxonomy GID cannot be routed to category searches by AI shopping systems."
                ),
                spec_citation="Shopify Standard Product Taxonomy 2024",
                affected_products=missing_ids,
                impact_statement=(
                    f"{len(missing_ids)} products unclassifiable by AI — invisible to "
                    "category and attribute queries."
                ),
                fix_type="auto",
                fix_instruction=(
                    "Use the map_taxonomy tool to automatically assign Shopify standard "
                    "taxonomy GIDs based on product titles, types, and descriptions."
                ),
            ))
    except Exception:
        pass
    return findings


def check_title_category_noun(
    data: MerchantData, llm_results: list[dict]
) -> list[Finding]:
    """C2 — Products whose title lacks a category noun (from LLM analysis)."""
    findings: list[Finding] = []
    try:
        if not llm_results:
            return findings

        failing_ids: list[str] = [
            r["product_id"]
            for r in llm_results
            if not r.get("title_contains_category_noun", True)
        ]

        if failing_ids:
            total = len(llm_results)
            findings.append(_make_finding(
                check_id="C2",
                pillar="Completeness",
                check_name="Title Category Noun",
                severity="CRITICAL",
                title=f"{len(failing_ids)} of {total} products have brand-name-only titles",
                detail=(
                    "AI agents cannot classify products when the title contains only a brand "
                    "name or marketing phrase with no category noun (e.g., 'Premium Vibe X' "
                    "instead of 'Premium Vibe X Running Shoe'). These products will not match "
                    "category queries and will be skipped by AI recommendation systems."
                ),
                spec_citation="GEO research: AI cannot classify brand-name-only titles",
                affected_products=failing_ids,
                impact_statement=(
                    f"{len(failing_ids)} products unclassifiable — will not appear in "
                    "AI category searches or recommendation results."
                ),
                fix_type="auto",
                fix_instruction=(
                    "Use the improve_title tool to automatically add category nouns to "
                    "product titles while preserving brand identity."
                ),
            ))
    except Exception:
        pass
    return findings


def check_variant_option_names(data: MerchantData) -> list[Finding]:
    """C3 — Products with unnamed variant options (Option1/Option2/Option3/Title)."""
    findings: list[Finding] = []
    try:
        _UNNAMED = {"option1", "option2", "option3", "title"}
        failing_ids: list[str] = []

        for p in data.products:
            for opt in p.options:
                if opt.name.strip().lower() in _UNNAMED:
                    failing_ids.append(p.id)
                    break

        if failing_ids:
            total = len(data.products)
            findings.append(_make_finding(
                check_id="C3",
                pillar="Completeness",
                check_name="Variant Option Names",
                severity="HIGH",
                title=f"{len(failing_ids)} products have unnamed variant options",
                detail=(
                    "Variant options named 'Option1', 'Option2', 'Option3', or 'Title' are "
                    "Shopify placeholders that provide no semantic meaning to AI agents. "
                    "AI agents cannot resolve agentic variant selection (e.g., 'size: Large', "
                    "'color: Blue') when option names are unnamed placeholders."
                ),
                spec_citation="Shopify: unnamed options break agentic variant resolution",
                affected_products=failing_ids,
                impact_statement=(
                    f"{len(failing_ids)} products with unresolvable variants — "
                    "AI agents cannot complete size/color/style selections."
                ),
                fix_type="manual",
                fix_instruction=(
                    "In Shopify Admin, go to each affected product and rename its variant "
                    "options from 'Option1'/'Option2' to descriptive names like 'Size', "
                    "'Color', 'Material', etc."
                ),
            ))
    except Exception:
        pass
    return findings


def check_gtin_identifier(data: MerchantData) -> list[Finding]:
    """C4 — Products need vendor non-empty AND at least one variant with non-empty SKU."""
    findings: list[Finding] = []
    try:
        failing_ids: list[str] = []

        for p in data.products:
            has_vendor = bool(p.vendor.strip())
            has_sku = any(
                bool(v.sku.strip()) for v in p.variants
            ) if p.variants else False

            if not (has_vendor and has_sku):
                failing_ids.append(p.id)

        if failing_ids:
            total = len(data.products)
            findings.append(_make_finding(
                check_id="C4",
                pillar="Completeness",
                check_name="Product Identifier (GTIN/SKU)",
                severity="HIGH",
                title=f"{len(failing_ids)} of {total} products missing vendor + SKU identifier",
                detail=(
                    "AI shopping platforms and Google Merchant Center require a unique "
                    "product identifier (GTIN preferred, or vendor + SKU combination). "
                    "Products without a vendor name and at least one variant SKU cannot "
                    "be uniquely identified across AI commerce platforms."
                ),
                spec_citation="Google Merchant Center feed spec: product identifier required",
                affected_products=failing_ids,
                impact_statement=(
                    f"{len(failing_ids)} products cannot be uniquely identified — "
                    "excluded from Google Shopping and AI commerce feeds."
                ),
                fix_type="manual",
                fix_instruction=(
                    "For each affected product: (1) set the Vendor field to your brand name, "
                    "(2) add a unique SKU to at least one variant. Ideally add GTINs "
                    "(barcode/UPC/EAN) for the strongest identifier signal."
                ),
            ))
    except Exception:
        pass
    return findings


def check_metafield_definitions(data: MerchantData) -> list[Finding]:
    """C5 — Store-level typed metafield definitions for 'material' and 'care_instructions'."""
    findings: list[Finding] = []
    if data.ingestion_mode != "admin_token":
        return findings
    try:
        defined_keys = {
            d.get("key", "").lower()
            for d in data.metafield_definitions
        }

        required_keys = {"material", "care_instructions"}
        missing_keys = required_keys - defined_keys

        if missing_keys:
            findings.append(_make_finding(
                check_id="C5",
                pillar="Completeness",
                check_name="Metafield Definitions",
                severity="HIGH",
                title=f"Missing typed metafield definitions: {', '.join(sorted(missing_keys))}",
                detail=(
                    "Shopify Search & Discovery requires typed metafield definitions for "
                    "product attributes like 'material' and 'care_instructions' to enable "
                    "AI-powered filtering. Without typed definitions, these attributes cannot "
                    "be indexed or queried by AI agents."
                ),
                spec_citation="Shopify Search & Discovery: typed definitions required for filtering",
                affected_products=[],
                impact_statement=(
                    f"Missing definitions for: {', '.join(sorted(missing_keys))}. "
                    "AI agents cannot filter or match on these attributes."
                ),
                fix_type="auto",
                fix_instruction=(
                    "Use the create_metafield_definitions tool to automatically create "
                    "typed metafield definitions for 'material' and 'care_instructions' "
                    "in your Shopify store."
                ),
            ))
    except Exception:
        pass
    return findings


def check_image_alt_text(data: MerchantData) -> list[Finding]:
    """C6 — Image alt text coverage must be ≥70%."""
    findings: list[Finding] = []
    try:
        total = 0
        covered = 0

        for p in data.products:
            for img in p.images:
                total += 1
                if img.alt and img.alt.strip():
                    covered += 1

        if total == 0:
            return findings

        pct = covered / total

        if pct < 0.70:
            findings.append(_make_finding(
                check_id="C6",
                pillar="Completeness",
                check_name="Image Alt Text",
                severity="MEDIUM",
                title=f"Image alt text coverage is only {pct:.0%} ({covered}/{total} images)",
                detail=(
                    "AI crawlers use alt text as the primary signal for understanding "
                    "product images. Low alt text coverage means AI agents cannot process "
                    "your product imagery, losing a critical source of product attribute data."
                ),
                spec_citation="AI crawler: alt text is primary image signal",
                affected_products=[],
                impact_statement=f"Alt text coverage: {pct:.0%} ({covered}/{total} images)",
                fix_type="auto",
                fix_instruction=(
                    "Use the generate_alt_text tool to automatically generate descriptive "
                    "alt text for all product images based on product title, type, and "
                    "image content."
                ),
            ))
    except Exception:
        pass
    return findings


# ---------------------------------------------------------------------------
# Pillar 3 — Consistency
# ---------------------------------------------------------------------------

def check_schema_price_consistency(data: MerchantData) -> list[Finding]:
    """Con1 — JSON-LD schema price must match actual product price (within $0.01)."""
    findings: list[Finding] = []
    try:
        if not data.schema_by_url:
            return findings

        # Build handle -> product map for URL matching
        handle_to_product = {p.handle: p for p in data.products}

        mismatched_ids: list[str] = []

        for url, schema_blocks in data.schema_by_url.items():
            # Try to match URL to a product by handle
            product = _match_product_by_url(url, handle_to_product)
            if not product:
                continue

            actual_price = _get_product_min_price(product)
            if actual_price is None:
                continue

            for block in schema_blocks:
                schema_price = _extract_schema_price(block)
                if schema_price is None:
                    continue
                if abs(schema_price - actual_price) > 0.01:
                    if product.id not in mismatched_ids:
                        mismatched_ids.append(product.id)

        if mismatched_ids:
            findings.append(_make_finding(
                check_id="Con1",
                pillar="Consistency",
                check_name="Schema Price Consistency",
                severity="CRITICAL",
                title=f"{len(mismatched_ids)} products have mismatched schema price vs actual price",
                detail=(
                    "JSON-LD structured data on these product pages shows a different price "
                    "than the actual product price. AI agents read schema markup to extract "
                    "prices — showing shoppers a wrong price destroys trust and can violate "
                    "consumer protection regulations."
                ),
                spec_citation="AI shows shoppers wrong price — trust destruction",
                affected_products=mismatched_ids,
                impact_statement=(
                    f"{len(mismatched_ids)} products showing incorrect price to AI agents "
                    "and shoppers — critical trust and compliance risk."
                ),
                fix_type="auto",
                fix_instruction=(
                    "Use the inject_schema_script tool to replace stale schema markup with "
                    "dynamically generated JSON-LD that always reflects the current product price."
                ),
            ))
    except Exception:
        pass
    return findings


def check_schema_availability(data: MerchantData) -> list[Finding]:
    """Con2 — JSON-LD availability must match actual inventory state."""
    findings: list[Finding] = []
    try:
        if not data.schema_by_url:
            return findings

        handle_to_product = {p.handle: p for p in data.products}
        mismatched_ids: list[str] = []

        _IN_STOCK_SCHEMA = {
            "https://schema.org/instock",
            "instock",
            "http://schema.org/instock",
        }
        _OUT_OF_STOCK_SCHEMA = {
            "https://schema.org/outofstock",
            "outofstock",
            "http://schema.org/outofstock",
        }

        for url, schema_blocks in data.schema_by_url.items():
            product = _match_product_by_url(url, handle_to_product)
            if not product:
                continue

            actual_in_stock = _is_product_in_stock(product)

            for block in schema_blocks:
                schema_avail = _extract_schema_availability(block)
                if schema_avail is None:
                    continue

                schema_avail_lower = schema_avail.lower().rstrip("/")
                schema_in_stock = schema_avail_lower in _IN_STOCK_SCHEMA

                if actual_in_stock != schema_in_stock:
                    if product.id not in mismatched_ids:
                        mismatched_ids.append(product.id)

        if mismatched_ids:
            findings.append(_make_finding(
                check_id="Con2",
                pillar="Consistency",
                check_name="Schema Availability Consistency",
                severity="CRITICAL",
                title=f"{len(mismatched_ids)} products have mismatched availability in schema vs inventory",
                detail=(
                    "JSON-LD availability status on these product pages does not match "
                    "actual inventory. AI agents rely on schema availability to determine "
                    "if they can proceed with a transaction. Stale availability data causes "
                    "failed agentic transactions and poor shopper experiences."
                ),
                spec_citation="Failed agentic transactions from stale availability",
                affected_products=mismatched_ids,
                impact_statement=(
                    f"{len(mismatched_ids)} products showing incorrect availability — "
                    "agentic transactions will fail on fulfillment."
                ),
                fix_type="auto",
                fix_instruction=(
                    "Use the inject_schema_script tool to replace static availability "
                    "schema with dynamically generated JSON-LD that reflects real-time inventory."
                ),
            ))
    except Exception:
        pass
    return findings


def check_seo_consistency(data: MerchantData) -> list[Finding]:
    """Con3 — SEO metaTitle should contain words from the product title (admin_token only)."""
    findings: list[Finding] = []
    if data.ingestion_mode != "admin_token":
        return findings
    try:
        failing_ids: list[str] = []

        for product in data.products:
            seo = data.seo_by_product.get(product.id)
            if not seo:
                continue
            meta_title = seo.get("metaTitle", "") or ""
            if not meta_title.strip():
                continue

            # Extract meaningful words (>= 3 chars) from product title
            product_words = {
                w.lower() for w in re.split(r"\s+", product.title)
                if len(w) >= 3
            }
            meta_words = {
                w.lower() for w in re.split(r"\s+", meta_title)
            }

            if product_words and not product_words.intersection(meta_words):
                failing_ids.append(product.id)

        if failing_ids:
            findings.append(_make_finding(
                check_id="Con3",
                pillar="Consistency",
                check_name="SEO Title Consistency",
                severity="MEDIUM",
                title=f"{len(failing_ids)} products have SEO titles inconsistent with product titles",
                detail=(
                    "The SEO meta title for these products shares no meaningful words with "
                    "the product title. AI aggregators that combine data from multiple sources "
                    "will see conflicting product names, reducing confidence in product data "
                    "and potentially causing misclassification."
                ),
                spec_citation="Cross-surface consistency for AI aggregation",
                affected_products=failing_ids,
                impact_statement=(
                    f"{len(failing_ids)} products with inconsistent naming across surfaces — "
                    "AI aggregation confidence reduced."
                ),
                fix_type="manual",
                fix_instruction=(
                    "Update the SEO meta title for each affected product to include the "
                    "product name. Navigate to each product in Shopify Admin, scroll to "
                    "the 'Search engine listing' section, and update the meta title."
                ),
            ))
    except Exception:
        pass
    return findings


# ---------------------------------------------------------------------------
# Pillar 4 — Trust and Policies
# ---------------------------------------------------------------------------

def check_refund_timeframe(data: MerchantData) -> list[Finding]:
    """T1 — Refund policy must contain an explicit day/timeframe."""
    findings: list[Finding] = []
    try:
        refund_text = data.policies.refund or ""
        pattern = r"\d+\s*(?:day|days|business\s+day|business\s+days)"
        if not re.search(pattern, refund_text, re.IGNORECASE):
            findings.append(_make_finding(
                check_id="T1",
                pillar="Trust_Policies",
                check_name="Refund Timeframe",
                severity="HIGH",
                title="Refund policy has no explicit return timeframe",
                detail=(
                    "AI agents answer pre-purchase questions about return windows by extracting "
                    "explicit timeframes from policy text (e.g., '30 days', '14 business days'). "
                    "Vague language like 'within a reasonable period' cannot be extracted and "
                    "will cause AI agents to report the return policy as unknown."
                ),
                spec_citation="AI constraint matching: vague timeframes are unextractable",
                affected_products=[],
                impact_statement="AI agents cannot answer 'What is your return policy?' accurately.",
                fix_type="copy_paste",
                fix_instruction=(
                    "Add an explicit return window to your refund policy. Include a specific "
                    "number of days (e.g., '30 days from delivery date'). Use the suggest_policy_fix "
                    "tool to generate a compliant policy draft."
                ),
            ))
    except Exception:
        pass
    return findings


def check_shipping_regions(data: MerchantData) -> list[Finding]:
    """T2 — Shipping policy must mention at least one explicit geographic region."""
    findings: list[Finding] = []
    try:
        shipping_text = data.policies.shipping or ""
        region_keywords = [
            "US", "USA", "United States",
            "UK", "United Kingdom",
            "Canada", "Australia",
            "Europe", "EU",
            "worldwide", "international", "domestic",
        ]
        found = any(
            re.search(r"\b" + re.escape(kw) + r"\b", shipping_text, re.IGNORECASE)
            for kw in region_keywords
        )
        if not found:
            findings.append(_make_finding(
                check_id="T2",
                pillar="Trust_Policies",
                check_name="Shipping Regions",
                severity="HIGH",
                title="Shipping policy contains no explicit geographic regions",
                detail=(
                    "AI agents handling location-filtered queries (e.g., 'ships to Canada') "
                    "extract shipping regions from policy text. Without explicit country or "
                    "region names, AI agents cannot confirm shipping eligibility and will "
                    "exclude your products from location-filtered recommendations."
                ),
                spec_citation="AI location-filtered queries require explicit region data",
                affected_products=[],
                impact_statement=(
                    "AI agents cannot confirm shipping availability to any region — "
                    "excluded from location-filtered shopping queries."
                ),
                fix_type="copy_paste",
                fix_instruction=(
                    "Add explicit shipping regions to your shipping policy. List the countries "
                    "or regions you ship to by name. Use the suggest_policy_fix tool to generate "
                    "a compliant shipping policy draft with your actual shipping regions."
                ),
            ))
    except Exception:
        pass
    return findings


def check_offer_schema(data: MerchantData) -> list[Finding]:
    """T4 — OfferShippingDetails and MerchantReturnPolicy must be present in schema."""
    findings: list[Finding] = []
    try:
        missing_shipping = True
        missing_return = True

        if data.schema_by_url:
            for url, schema_blocks in data.schema_by_url.items():
                for block in schema_blocks:
                    block_str = str(block).lower()
                    if "offershippingdetails" in block_str or "shippingdetails" in block_str:
                        missing_shipping = False
                    if "merchantreturnpolicy" in block_str or "hasmerchantreturnpolicy" in block_str:
                        missing_return = False

        missing_parts: list[str] = []
        if missing_shipping:
            missing_parts.append("OfferShippingDetails")
        if missing_return:
            missing_parts.append("MerchantReturnPolicy")

        if missing_parts:
            findings.append(_make_finding(
                check_id="T4",
                pillar="Trust_Policies",
                check_name="Offer Schema (Shipping + Return)",
                severity="CRITICAL",
                title=f"Missing schema markup: {', '.join(missing_parts)}",
                detail=(
                    "OfferShippingDetails and MerchantReturnPolicy schema markup are required "
                    "for AI checkout flows to understand shipping costs and return eligibility "
                    "before initiating a transaction. Without these, products are invisible to "
                    "AI-initiated checkout and will not appear in comparison queries involving "
                    "shipping or returns."
                ),
                spec_citation="Shopify/IFG: products invisible to AI checkout without OfferShippingDetails",
                affected_products=[],
                impact_statement=(
                    f"Missing: {', '.join(missing_parts)}. AI checkout transactions blocked — "
                    "products excluded from agentic purchase flows."
                ),
                fix_type="auto",
                fix_instruction=(
                    "Use the inject_schema_script tool to add OfferShippingDetails and "
                    "MerchantReturnPolicy JSON-LD markup to all product pages."
                ),
            ))
    except Exception:
        pass
    return findings


# ---------------------------------------------------------------------------
# Pillar 5 — Transaction
# ---------------------------------------------------------------------------

def check_inventory_tracking(data: MerchantData) -> list[Finding]:
    """A1 — Products with any untracked variant (inventory_management is None)."""
    findings: list[Finding] = []
    try:
        failing_ids: list[str] = []

        for p in data.products:
            for v in p.variants:
                if v.inventory_management is None:
                    failing_ids.append(p.id)
                    break

        if failing_ids:
            total = len(data.products)
            findings.append(_make_finding(
                check_id="A1",
                pillar="Transaction",
                check_name="Inventory Tracking",
                severity="HIGH",
                title=f"{len(failing_ids)} of {total} products have untracked inventory",
                detail=(
                    "Variants with inventory_management set to None are not tracked by Shopify. "
                    "AI agents verify product availability before initiating transactions — "
                    "untracked inventory means the agent cannot confirm availability and may "
                    "either refuse to transact or cause oversell situations."
                ),
                spec_citation="Untracked inventory: agent cannot verify availability",
                affected_products=failing_ids,
                impact_statement=(
                    f"{len(failing_ids)} products with unverifiable inventory — "
                    "AI agents cannot confirm availability before purchase."
                ),
                fix_type="manual",
                fix_instruction=(
                    "For each affected product, go to Shopify Admin > Products > Variants "
                    "and enable 'Track quantity' for each variant. This ensures Shopify "
                    "tracks inventory so AI agents can verify availability."
                ),
            ))
    except Exception:
        pass
    return findings


def check_oversell_risk(data: MerchantData) -> list[Finding]:
    """A2 — Variants with inventory tracked but oversell (continue) policy enabled."""
    findings: list[Finding] = []
    try:
        failing_ids: list[str] = []

        for p in data.products:
            for v in p.variants:
                if (
                    v.inventory_management == "shopify"
                    and v.inventory_policy == "continue"
                ):
                    failing_ids.append(p.id)
                    break

        if failing_ids:
            total = len(data.products)
            findings.append(_make_finding(
                check_id="A2",
                pillar="Transaction",
                check_name="Oversell Risk",
                severity="CRITICAL",
                title=f"{len(failing_ids)} of {total} products at risk of overselling via AI agents",
                detail=(
                    "Variants with inventory_management='shopify' and inventory_policy='continue' "
                    "will accept orders even when inventory reaches zero. AI agents confirm stock "
                    "before initiating transactions, but the continue policy allows purchase "
                    "after the agent's check — leading to confirmed orders that cannot be fulfilled."
                ),
                spec_citation="Oversell risk: agent confirms stock, transaction fails on delivery",
                affected_products=failing_ids,
                impact_statement=(
                    f"{len(failing_ids)} products can be oversold via AI transactions — "
                    "highest severity: confirmed orders that fail on delivery."
                ),
                fix_type="manual",
                fix_instruction=(
                    "For each affected product, go to Shopify Admin > Products > Variants "
                    "and change the 'Continue selling when out of stock' setting to disabled. "
                    "Set inventory policy to 'deny' to prevent oversell via AI transactions."
                ),
            ))
    except Exception:
        pass
    return findings


# ---------------------------------------------------------------------------
# run_all_checks
# ---------------------------------------------------------------------------

def run_all_checks(
    data: MerchantData,
    llm_results: list[dict] | None = None,
) -> list[Finding]:
    """
    Run all 19 deterministic checks and return findings sorted by:
    1. Severity (CRITICAL first, then HIGH, then MEDIUM)
    2. affected_count descending within same severity
    """
    if llm_results is None:
        llm_results = []

    all_findings: list[Finding] = []

    # Pillar 1 — Discoverability
    all_findings.extend(check_robot_crawlers(data))
    all_findings.extend(check_catalog_eligibility(data))
    all_findings.extend(check_sitemap(data))
    all_findings.extend(check_llms_txt(data))
    all_findings.extend(check_markets_translation(data))

    # Pillar 2 — Completeness
    all_findings.extend(check_taxonomy_mapped(data))
    all_findings.extend(check_title_category_noun(data, llm_results))
    all_findings.extend(check_variant_option_names(data))
    all_findings.extend(check_gtin_identifier(data))
    all_findings.extend(check_metafield_definitions(data))
    all_findings.extend(check_image_alt_text(data))

    # Pillar 3 — Consistency
    all_findings.extend(check_schema_price_consistency(data))
    all_findings.extend(check_schema_availability(data))
    all_findings.extend(check_seo_consistency(data))

    # Pillar 4 — Trust and Policies
    all_findings.extend(check_refund_timeframe(data))
    all_findings.extend(check_shipping_regions(data))
    all_findings.extend(check_offer_schema(data))

    # Pillar 5 — Transaction
    all_findings.extend(check_inventory_tracking(data))
    all_findings.extend(check_oversell_risk(data))

    # Sort: CRITICAL < HIGH < MEDIUM, then affected_count descending
    all_findings.sort(
        key=lambda f: (_SEVERITY_ORDER.get(f.severity, 99), -f.affected_count)
    )

    return all_findings


# ---------------------------------------------------------------------------
# Internal helpers (not part of the public API)
# ---------------------------------------------------------------------------

def _safe_float(value: str | float | int | None) -> float:
    """Convert a price string/number to float, returning 0.0 on failure."""
    try:
        return float(value) if value is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def _match_product_by_url(url: str, handle_to_product: dict) -> object | None:
    """
    Try to match a URL to a product by looking for its handle in the URL path.
    Returns the Product object or None.
    """
    try:
        # Shopify product URLs are typically /products/{handle}
        match = re.search(r"/products/([^/?#]+)", url)
        if match:
            handle = match.group(1).rstrip("/")
            return handle_to_product.get(handle)
    except Exception:
        pass
    return None


def _get_product_min_price(product) -> float | None:
    """Return the minimum variant price as a float, or None if no variants."""
    try:
        prices = [_safe_float(v.price) for v in product.variants if v.price]
        return min(prices) if prices else None
    except Exception:
        return None


def _extract_schema_price(block: dict) -> float | None:
    """Extract price from a JSON-LD block (Product or Offer level)."""
    try:
        # Direct price field
        if "price" in block:
            return _safe_float(block["price"])
        # offers.price
        offers = block.get("offers", {})
        if isinstance(offers, dict) and "price" in offers:
            return _safe_float(offers["price"])
        if isinstance(offers, list):
            for offer in offers:
                if isinstance(offer, dict) and "price" in offer:
                    return _safe_float(offer["price"])
        # @type Offer at top level
        if block.get("@type") in ("Offer", "AggregateOffer"):
            if "price" in block:
                return _safe_float(block["price"])
    except Exception:
        pass
    return None


def _extract_schema_availability(block: dict) -> str | None:
    """Extract availability from a JSON-LD block."""
    try:
        # offers.availability
        offers = block.get("offers", {})
        if isinstance(offers, dict):
            avail = offers.get("availability")
            if avail:
                return str(avail)
        if isinstance(offers, list):
            for offer in offers:
                if isinstance(offer, dict):
                    avail = offer.get("availability")
                    if avail:
                        return str(avail)
        # Direct availability on block
        if "availability" in block:
            return str(block["availability"])
    except Exception:
        pass
    return None


def _is_product_in_stock(product) -> bool:
    """
    Determine if a product is in stock based on its variants.
    A product is in stock if any variant has quantity > 0 or policy='continue'.
    """
    try:
        for v in product.variants:
            if v.inventory_management is None:
                # Untracked — assume available
                return True
            if v.inventory_quantity > 0:
                return True
            if v.inventory_policy == "continue":
                return True
        return False
    except Exception:
        return True  # default to in-stock if we can't determine
