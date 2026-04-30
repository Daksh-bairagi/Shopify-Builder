"""
query_matcher.py — AI Query Match Simulator

Answers: "would my products actually appear if someone asked AI for them?"
Deterministic attribute matching from machine-readable product fields.
Zero LLM calls — query parsed with regex; matching is deterministic.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from app.models.merchant import MerchantData, Product
from app.models.findings import QueryMatchResult


# ---------------------------------------------------------------------------
# LLM output schema — one call per query to extract structured attributes
# ---------------------------------------------------------------------------

class ParsedQuery(BaseModel):
    """Structured attributes extracted from a natural language shopping query."""
    category: Optional[str] = Field(None, description="Product category noun, e.g. 'yoga mat'")
    price_max: Optional[float] = Field(None, description="Maximum price in USD if mentioned")
    price_min: Optional[float] = Field(None, description="Minimum price in USD if mentioned")
    attributes: list[str] = Field(
        default_factory=list,
        description="Up to 5 key product attributes mentioned, e.g. ['washable', 'eco-friendly', 'cotton']"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_query_attributes(query_text: str) -> ParsedQuery:
    """
    Extract structured shopping attributes from a natural language query
    using pure regex — no LLM call required.

    Handles patterns like:
        "yoga mat under $50"
        "best cotton shirt with fast shipping"
        "premium quality sneakers"
    """
    import re

    text = query_text.strip()

    # --- Price extraction ---
    price_max: float | None = None
    price_min: float | None = None
    max_match = re.search(r'(?:under|below|max|up to)\s+\$?([\d]+(?:\.\d+)?)', text, re.IGNORECASE)
    if max_match:
        price_max = float(max_match.group(1))
    min_match = re.search(r'(?:over|above|at least|from)\s+\$?([\d]+(?:\.\d+)?)', text, re.IGNORECASE)
    if min_match:
        price_min = float(min_match.group(1))

    # --- Strip price phrases and punctuation for token extraction ---
    cleaned = re.sub(r'(?:under|below|over|above|up to|at least|from|max)\s+\$?[\d]+(?:\.\d+)?', ' ', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\$[\d]+(?:\.\d+)?', ' ', cleaned)
    cleaned = re.sub(r'[^a-zA-Z0-9\s-]', ' ', cleaned)

    STOP_WORDS = {
        'a', 'an', 'the', 'with', 'and', 'or', 'for', 'in', 'of',
        'is', 'are', 'do', 'me', 'my', 'its', 'this', 'that',
        'best', 'good', 'great', 'nice', 'idea', 'gift', 'reviews',
        'review', 'quality', 'affordable', 'cheap', 'fast', 'quick',
        'shipping', 'delivery', 'price', 'buy', 'shop',
    }

    tokens = [t.lower().strip() for t in cleaned.split() if t.strip()]
    meaningful = [t for t in tokens if t not in STOP_WORDS and len(t) > 2]

    category = meaningful[0] if meaningful else None
    attributes = meaningful[1:6] if len(meaningful) > 1 else []

    return ParsedQuery(
        category=category,
        price_max=price_max,
        price_min=price_min,
        attributes=attributes,
    )


def match_products(
    products: list[Product],
    attributes: ParsedQuery,
    metafields_by_product: dict[str, list],
    taxonomy_by_product: dict[str, str],
) -> tuple[list[str], dict[str, int]]:
    """
    Deterministic matching — no LLM calls.

    For each product, check if machine-readable data satisfies each
    attribute extracted from the query.

    Returns:
        matched_product_ids: products that satisfy ALL extractable attributes
        failing_attributes: {attribute_name: count of products missing it}
    """
    MATERIAL_KEYWORDS = {
        "cotton", "polyester", "leather", "wood", "steel", "wool",
        "linen", "plastic", "ceramic", "gold", "silver", "nylon", "silk",
    }

    matched_ids: list[str] = []
    failing: dict[str, int] = {}

    for product in products:
        product_passes = True

        # --- Category match ---
        if attributes.category:
            cat_lower = attributes.category.lower()
            title_lower = product.title.lower()
            type_lower = product.product_type.lower()
            taxonomy_gid = taxonomy_by_product.get(product.id, "")
            category_matches = (
                cat_lower in title_lower
                or cat_lower in type_lower
                or cat_lower in taxonomy_gid.lower()
            )
            if not category_matches:
                product_passes = False
                failing["category"] = failing.get("category", 0) + 1

        # --- Price range match ---
        if attributes.price_max is not None or attributes.price_min is not None:
            prices = [float(v.price) for v in product.variants if v.price]
            min_price = min(prices) if prices else None
            if min_price is not None:
                if attributes.price_max is not None and min_price > attributes.price_max:
                    product_passes = False
                    failing["price_max"] = failing.get("price_max", 0) + 1
                if attributes.price_min is not None and min_price < attributes.price_min:
                    product_passes = False
                    failing["price_min"] = failing.get("price_min", 0) + 1

        # --- Attribute matching ---
        product_metafields = metafields_by_product.get(product.id, [])
        metafield_values = " ".join(
            str(mf.get("value", "")) for mf in product_metafields
        ).lower()
        description_lower = product.body_html.lower()
        all_text = f"{product.title} {description_lower} {metafield_values}".lower()

        for attr in attributes.attributes:
            attr_lower = attr.lower()
            attr_found = attr_lower in all_text

            # Special case: material attributes cross-validated against known keywords
            if attr_lower in MATERIAL_KEYWORDS and attr_lower not in metafield_values:
                attr_found = False  # must be in metafields, not just description prose

            if not attr_found:
                product_passes = False
                failing[attr] = failing.get(attr, 0) + 1

        if product_passes:
            matched_ids.append(product.id)

    return matched_ids, failing


def build_query_match_result(
    query: str,
    products: list[Product],
    matched_product_ids: list[str],
    failing_attributes: dict[str, int],
) -> QueryMatchResult:
    """Assemble a QueryMatchResult dataclass from match_products output."""
    return QueryMatchResult(
        query=query,
        matched_product_ids=matched_product_ids,
        total_products=len(products),
        match_count=len(matched_product_ids),
        failing_attributes=failing_attributes,
    )


async def run_default_queries(merchant_data: MerchantData, paid_tier: bool = False) -> list[QueryMatchResult]:
    """
    Generate default queries from merchant taxonomy + price range and run matching.

    Free tier: 1 query.
    Paid tier: 5 queries.

    Returns list of QueryMatchResult — one per query.
    """
    if not merchant_data.products:
        return []

    # Build default queries from merchant's actual data
    # Use top product types / taxonomy categories as the base
    product_types = list({
        p.product_type for p in merchant_data.products if p.product_type
    })[:3]
    prices = [
        float(v.price)
        for p in merchant_data.products
        for v in p.variants
        if v.price
    ]
    price_bracket = int(max(prices) * 0.6) if prices else 50

    base_queries = []
    if product_types:
        cat = product_types[0]
        base_queries.append(f"{cat} under ${price_bracket}")
        if paid_tier and len(product_types) > 1:
            base_queries.append(f"best {product_types[1]} with good reviews")
            base_queries.append(f"affordable {cat} with fast shipping")
            base_queries.append(f"premium quality {cat}")
            if len(product_types) > 2:
                base_queries.append(f"{product_types[2]} gift idea")
    else:
        base_queries.append(f"product under ${price_bracket}")

    limit = 5 if paid_tier else 1
    queries_to_run = base_queries[:limit]

    results = []
    for query_text in queries_to_run:
        try:
            parsed = parse_query_attributes(query_text)
            matched_ids, failing = match_products(
                products=merchant_data.products,
                attributes=parsed,
                metafields_by_product=merchant_data.metafields_by_product,
                taxonomy_by_product=merchant_data.taxonomy_by_product,
            )
            results.append(build_query_match_result(
                query=query_text,
                products=merchant_data.products,
                matched_product_ids=matched_ids,
                failing_attributes=failing,
            ))
        except Exception:
            # Never let query matching break the main pipeline
            continue

    return results
