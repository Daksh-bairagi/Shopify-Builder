"""
schema_enricher.py — Per-product JSON-LD package for AI surfaces.

Scope of THIS module (kept narrow on purpose so it's easy to reason about):
  - Organization                      (one, store-level)
  - Product   (+ Offer / AggregateOffer, ImageObject sub-blocks)
  - BreadcrumbList                    (one per product)
  - AggregateRating                   (embedded in Product when source data
                                       exposes it via merchant_data.schema_by_url)
  - VideoObject                       (embedded in Product when a video URL is
                                       discoverable on existing JSON-LD)

Out of scope (handled elsewhere — by design):
  - FAQPage                           → see services/faq_generator.py
  - MerchantReturnPolicy + ShippingDetails
                                      → see agent/tools.py inject_schema_script
                                        (operates on store policies, not products)

Pure functions. No I/O.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from app.models.merchant import MerchantData, Product


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _domain_url(store_domain: str) -> str:
    if store_domain.startswith("http"):
        return store_domain.rstrip("/")
    return f"https://{store_domain.rstrip('/')}"


def _strip_html(html: Optional[str]) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _availability(inventory_qty: int, policy: str) -> str:
    if inventory_qty > 0:
        return "https://schema.org/InStock"
    if policy == "continue":
        return "https://schema.org/BackOrder"
    return "https://schema.org/OutOfStock"


def _safe_price(p: str) -> str:
    """Strip $, ₹, commas; keep digits + dot."""
    if not p:
        return "0.00"
    return re.sub(r"[^\d.]", "", str(p)) or "0.00"


def _detect_currency(merchant_data: MerchantData) -> str:
    """Best-effort currency from any embedded JSON-LD; default USD."""
    for url, blocks in (merchant_data.schema_by_url or {}).items():
        for b in blocks or []:
            offers = b.get("offers") if isinstance(b, dict) else None
            if isinstance(offers, dict):
                cur = offers.get("priceCurrency") or offers.get("priceCurrencyCode")
                if cur:
                    return str(cur)
    return "USD"


def _find_existing_product_block(
    product: Product,
    merchant_data: MerchantData,
) -> Optional[dict]:
    """Locate a Product JSON-LD block already on the merchant page so we can
    inherit its review/rating/video info instead of fabricating it."""
    handle_path = f"/products/{product.handle}"
    for url, blocks in (merchant_data.schema_by_url or {}).items():
        if handle_path not in url:
            continue
        for b in blocks or []:
            if not isinstance(b, dict):
                continue
            t = b.get("@type")
            types = t if isinstance(t, list) else [t]
            if any(isinstance(x, str) and x.lower() == "product" for x in types):
                return b
    return None


def _aggregate_rating(existing: Optional[dict]) -> Optional[dict]:
    if not existing:
        return None
    ar = existing.get("aggregateRating")
    if isinstance(ar, dict) and ar.get("ratingValue") is not None:
        out = {
            "@type": "AggregateRating",
            "ratingValue": ar.get("ratingValue"),
        }
        for k in ("reviewCount", "ratingCount", "bestRating", "worstRating"):
            if k in ar:
                out[k] = ar[k]
        return out
    return None


def _video_objects(existing: Optional[dict]) -> list[dict]:
    if not existing:
        return []
    raw = existing.get("video") or existing.get("subjectOf")
    candidates = raw if isinstance(raw, list) else [raw] if isinstance(raw, dict) else []
    out: list[dict] = []
    for v in candidates:
        if not isinstance(v, dict):
            continue
        t = v.get("@type")
        types = t if isinstance(t, list) else [t]
        if not any(isinstance(x, str) and x.lower() == "videoobject" for x in types):
            continue
        block = {
            "@type": "VideoObject",
            "name": v.get("name") or "",
            "description": v.get("description") or "",
            "thumbnailUrl": v.get("thumbnailUrl"),
            "uploadDate": v.get("uploadDate"),
            "contentUrl": v.get("contentUrl") or v.get("url"),
            "embedUrl": v.get("embedUrl"),
        }
        out.append({k: val for k, val in block.items() if val})
    return out


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def build_organization_jsonld(merchant_data: MerchantData) -> dict:
    """Org schema. AI ranking signal — establishes entity identity."""
    base = _domain_url(merchant_data.store_domain)
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": merchant_data.store_name or merchant_data.store_domain,
        "url": base,
        "logo": f"{base}/favicon.ico",
        "potentialAction": {
            "@type": "SearchAction",
            "target": f"{base}/search?q={{search_term_string}}",
            "query-input": "required name=search_term_string",
        },
    }


def build_breadcrumb_jsonld(product: Product, merchant_data: MerchantData) -> dict:
    base = _domain_url(merchant_data.store_domain)
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": base,
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": product.product_type or "Products",
                "item": f"{base}/collections/all",
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": product.title,
                "item": f"{base}/products/{product.handle}",
            },
        ],
    }


def build_product_jsonld(product: Product, merchant_data: MerchantData) -> dict:
    """Product + Offer + ImageObjects. Skips fields that are missing rather than emitting empties."""
    base = _domain_url(merchant_data.store_domain)
    url = f"{base}/products/{product.handle}"
    currency = _detect_currency(merchant_data)

    images_jsonld = [
        {
            "@type": "ImageObject",
            "url": img.src,
            "caption": img.alt or product.title,
            "representativeOfPage": img.position == 1,
        }
        for img in product.images[:8]
    ]

    # Offer: aggregate when multi-variant, single when one variant.
    if len(product.variants) <= 1:
        v = product.variants[0] if product.variants else None
        offer = {
            "@type": "Offer",
            "url": url,
            "priceCurrency": currency,
            "price": _safe_price(v.price if v else "0"),
            "availability": _availability(
                v.inventory_quantity if v else 0,
                v.inventory_policy if v else "deny",
            ),
            "itemCondition": "https://schema.org/NewCondition",
        }
    else:
        prices = sorted([float(_safe_price(v.price)) for v in product.variants])
        any_in_stock = any(v.inventory_quantity > 0 for v in product.variants)
        offer = {
            "@type": "AggregateOffer",
            "url": url,
            "priceCurrency": currency,
            "lowPrice": f"{prices[0]:.2f}",
            "highPrice": f"{prices[-1]:.2f}",
            "offerCount": len(product.variants),
            "availability": (
                "https://schema.org/InStock" if any_in_stock
                else "https://schema.org/OutOfStock"
            ),
        }

    block: dict = {
        "@context": "https://schema.org",
        "@type": "Product",
        "@id": f"{url}#product",
        "name": product.title,
        "url": url,
        "description": _strip_html(product.body_html)[:5000],
        "sku": product.variants[0].sku if product.variants and product.variants[0].sku else None,
        "brand": {
            "@type": "Brand",
            "name": product.vendor,
        } if product.vendor else None,
        "category": product.product_type or None,
        "image": [img.src for img in product.images[:8]] or None,
        "offers": offer,
    }

    # Rich variants — Property/Value hints for AI agents.
    if product.options:
        block["additionalProperty"] = [
            {"@type": "PropertyValue", "name": opt.name, "value": ", ".join(opt.values[:6])}
            for opt in product.options
        ]

    # Image objects (separate block — gives AI multi-modal handles).
    subject_of: list[dict] = list(images_jsonld)

    # Inherit AggregateRating + VideoObject from any existing on-page JSON-LD
    # so we don't fabricate review counts.
    existing = _find_existing_product_block(product, merchant_data)
    rating = _aggregate_rating(existing)
    if rating is not None:
        block["aggregateRating"] = rating

    videos = _video_objects(existing)
    if videos:
        subject_of.extend(videos)

    if subject_of:
        block["subjectOf"] = subject_of

    return {k: v for k, v in block.items() if v is not None}


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def generate_schema_package(merchant_data: MerchantData) -> dict:
    """
    Returns a structured package:
        {
            "organization": {...},
            "products": {
                "<product_id>": {
                    "url": "...",
                    "blocks": [Product, BreadcrumbList],
                    "script_tag_payload": "<script type=...>...</script>",
                }
            },
            "all_blocks": [...]   # flat list, for downloadable .json
        }
    """
    org = build_organization_jsonld(merchant_data)
    products: dict[str, dict] = {}
    flat: list[dict] = [org]

    products_with_rating = 0
    products_with_video = 0

    for p in merchant_data.products:
        product_block = build_product_jsonld(p, merchant_data)
        breadcrumb_block = build_breadcrumb_jsonld(p, merchant_data)
        blocks = [product_block, breadcrumb_block]
        flat.extend(blocks)

        if "aggregateRating" in product_block:
            products_with_rating += 1
        if any(
            isinstance(s, dict) and s.get("@type") == "VideoObject"
            for s in (product_block.get("subjectOf") or [])
        ):
            products_with_video += 1

        payload = (
            '<script type="application/ld+json">'
            + json.dumps({"@graph": blocks}, separators=(",", ":"))
            + "</script>"
        )
        products[p.id] = {
            "url": f"{_domain_url(merchant_data.store_domain)}/products/{p.handle}",
            "blocks": blocks,
            "script_tag_payload": payload,
        }

    return {
        "organization": org,
        "products": products,
        "all_blocks": flat,
        "summary": {
            "total_products": len(merchant_data.products),
            "blocks_per_product": 2,        # Product + BreadcrumbList; rating/video embed inside Product
            "total_blocks": len(flat),
            "products_with_aggregate_rating": products_with_rating,
            "products_with_video_object": products_with_video,
            "scope": (
                "Organization + Product (+ AggregateRating/VideoObject when source data exists) "
                "+ BreadcrumbList. FAQPage handled by faq_generator.py; "
                "MerchantReturnPolicy by agent/tools.py.inject_schema_script."
            ),
        },
    }
