from __future__ import annotations

import re as _re

_RE_DAYS = _re.compile(r'(\d+)[\s-]?day', _re.IGNORECASE)

from app.models.merchant import MerchantData
from app.models.findings import Finding, MCPResult





# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_product_data_text(merchant_data: MerchantData) -> str:
    """Render up to 5 products as structured one-liner text for the prompt."""
    lines: list[str] = []
    for product in merchant_data.products[:5]:
        in_stock = any(
            v.inventory_quantity > 0 for v in product.variants
        ) if product.variants else False

        options_text = "; ".join(
            f"{opt.name}: {', '.join(opt.values)}" for opt in product.options
        ) if product.options else "none"

        tags_text = ", ".join(product.tags) if product.tags else "none"
        product_type_text = product.product_type or "not specified"
        variant_count = len(product.variants)

        lines.append(
            f'Product: "{product.title}" | Type: {product_type_text} | '
            f"Tags: {tags_text} | Variants: {variant_count} | "
            f"In stock: {in_stock} | Options: {options_text}"
        )
    return "\n".join(lines) if lines else "No products available."


def _trim_policy(text: str) -> str:
    """Trim policy text to first 200 chars; return 'Not provided' if empty."""
    if not text or not text.strip():
        return "Not provided"
    trimmed = text.strip()[:200]
    return trimmed + ("..." if len(text.strip()) > 200 else "")


def _default_unanswered_results(questions: list[str]) -> list[MCPResult]:
    """Return 5 UNANSWERED results for use on error."""
    return [
        MCPResult(
            question=q,
            response="Simulation unavailable",
            classification="UNANSWERED",
            ground_truth_mismatch=None,
            related_finding_ids=[],
        )
        for q in questions
    ]


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def _build_dynamic_questions(merchant_data: MerchantData) -> list[str]:
    """Generate 5 buyer questions tailored to this specific store's catalog."""
    products = merchant_data.products

    # Pick distinct products for variety across questions
    p0 = products[0].title if products else "your products"
    p1 = products[1].title if len(products) > 1 else p0
    p2 = products[2].title if len(products) > 2 else p1

    # Get actual product types from catalog
    product_types = list({p.product_type for p in products if p.product_type})[:3]
    type_str = ", ".join(product_types) if product_types else "products"

    # Check if store has a notable price spread (worth asking about)
    prices: list[float] = []
    for p in products[:10]:
        for v in p.variants:
            try:
                prices.append(float(v.price))
            except (ValueError, TypeError, AttributeError):
                pass
    wide_price_range = len(prices) >= 2 and (max(prices) - min(prices)) > 20

    # Check if policies are populated (affects question relevance)
    has_refund = bool(merchant_data.policies.refund and merchant_data.policies.refund.strip())
    has_shipping = bool(merchant_data.policies.shipping and merchant_data.policies.shipping.strip())

    q_category = (
        f"What types of {type_str} do you sell and what sets them apart?"
        if product_types
        else "What products do you sell and what categories are they in?"
    )
    q_stock = f"Is '{p0}' currently in stock and available to ship right now?"
    q_return = (
        "What is your return policy — how many days do I have and how do I start a return?"
        if has_refund
        else "Can I return a product if it doesn't fit or I change my mind?"
    )
    q_shipping = (
        "Which countries do you ship to and how long does delivery take?"
        if has_shipping
        else "Do you offer international shipping? Which regions do you deliver to?"
    )
    q_details = (
        f"What is the price range across your {type_str} collection and what's different at each price point?"
        if wide_price_range
        else f"What are the materials, sizes, or specifications available for '{p1}'?"
    )

    return [q_category, q_stock, q_return, q_shipping, q_details]



async def run_mcp_simulation(
    merchant_data: MerchantData,
    findings: list[Finding],
) -> list[MCPResult]:
    """
    Simulate an MCP-based shopping AI answering 5 standard questions about
    the merchant's store using only their structured product data.

    Returns a list of MCPResult dataclasses.
    """
    # Build questions dynamically from the actual store catalog
    questions = _build_dynamic_questions(merchant_data)

    # Rule-based answers derived directly from structured store data — no LLM call.
    try:
        products = merchant_data.products
        policies = merchant_data.policies

        # --- Q0: what product categories does the store sell? ---
        product_types = list({p.product_type for p in products if p.product_type})
        if product_types:
            type_str = ", ".join(product_types[:5])
            q0_response = f"This store sells {type_str}. Each product type has its own set of variants and options available."
            q0_class: str = "ANSWERED"
        else:
            q0_response = "I cannot determine the specific product categories from the available structured data."
            q0_class = "UNANSWERED"

        # --- Q1: is a specific product in stock? ---
        # inventory_management=None means Shopify doesn't track inventory for this product
        # — we should not report it as out-of-stock, because it may well be available.
        p0 = products[0] if products else None
        if p0:
            tracked_variants = [
                v for v in p0.variants
                if getattr(v, "inventory_management", None) is not None
            ]
            if not tracked_variants:
                # No tracking → availability unknown; don't guess
                q1_response = f"'{p0.title}' doesn't use inventory tracking, so real-time stock status isn't available from structured data."
                q1_class = "UNANSWERED"
            elif any(getattr(v, "inventory_quantity", 0) > 0 for v in tracked_variants):
                q1_response = f"Yes, '{p0.title}' is currently in stock and available to order."
                q1_class = "ANSWERED"
            else:
                q1_response = f"Based on inventory data, '{p0.title}' appears to be out of stock right now."
                q1_class = "ANSWERED"
        else:
            q1_response = "I cannot determine stock availability — no product data is available."
            q1_class = "UNANSWERED"

        # --- Q2: return policy ---
        refund = (getattr(policies, "refund", None) or "").strip()
        days_match = _RE_DAYS.search(refund) if refund else None
        if days_match:
            days = days_match.group(1)
            q2_response = f"Returns are accepted within {days} days of purchase. Contact the store to initiate a return."
            q2_class = "ANSWERED"
        elif refund:
            q2_response = refund[:300]
            q2_class = "ANSWERED"
        else:
            q2_response = "I cannot determine the return policy — no refund policy text is available in the store data."
            q2_class = "UNANSWERED"

        # --- Q3: shipping regions ---
        shipping = (getattr(policies, "shipping", None) or "").strip()
        _SHIPPING_KW = [
            "united states", "canada", "australia", "united kingdom", "uk",
            "europe", "worldwide", "international", "global",
        ]
        regions = [kw.title() for kw in _SHIPPING_KW if kw in shipping.lower()] if shipping else []
        if regions:
            q3_response = f"They ship to: {', '.join(regions)}."
            q3_class = "ANSWERED"
        elif shipping:
            q3_response = shipping[:300]
            q3_class = "ANSWERED"
        else:
            q3_response = "I cannot determine shipping destinations — no shipping policy is available in the store data."
            q3_class = "UNANSWERED"

        # --- Q4: price range or product specs ---
        prices: list[float] = []
        for p in products[:10]:
            for v in p.variants:
                try:
                    prices.append(float(v.price))
                except (ValueError, TypeError, AttributeError):
                    pass

        if len(prices) >= 2 and (max(prices) - min(prices)) > 20:
            lo, hi = min(prices), max(prices)
            q4_response = f"Prices range from ${lo:.0f} to ${hi:.0f}. Higher-priced items typically offer more variants or premium materials."
            q4_class = "ANSWERED"
        else:
            p1 = products[1] if len(products) > 1 else p0
            if p1 and p1.options:
                opt_str = "; ".join(
                    f"{o.name}: {', '.join(o.values[:4])}" for o in p1.options[:3]
                )
                q4_response = f"Available options for '{p1.title}': {opt_str}."
                q4_class = "ANSWERED"
            else:
                q4_response = "I cannot determine detailed specifications — option and metafield data is not available."
                q4_class = "UNANSWERED"

        responses   = [q0_response, q1_response, q2_response, q3_response, q4_response]
        classes     = [q0_class,    q1_class,    q2_class,    q3_class,    q4_class]

        # Map findings to questions for context links
        check_to_findings: dict[str, list[str]] = {}
        for f in findings:
            check_to_findings.setdefault(f.check_id, []).append(f.id)

        question_to_checks: dict[int, list[str]] = {
            0: ["C1"], 1: ["T1"], 2: ["T2"], 3: ["A1", "A2"], 4: ["C4", "C5"],
        }

        results: list[MCPResult] = []
        for idx in range(len(questions)):
            cls = classes[idx] if idx < len(classes) else "UNANSWERED"
            related_ids: list[str] = []
            if cls == "UNANSWERED":
                for cid in question_to_checks.get(idx, []):
                    related_ids.extend(check_to_findings.get(cid, []))
            results.append(MCPResult(
                question=questions[idx],
                response=responses[idx] if idx < len(responses) else "No data available.",
                classification=cls,
                ground_truth_mismatch=None,
                related_finding_ids=related_ids,
            ))

        return results

    except Exception:
        return _default_unanswered_results(questions)
