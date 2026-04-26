"""
golden_record.py — Score every product on a 25-attribute "Golden Record" rubric.

Industry data (Google AI Mode 2026) shows products with 99.9% attribute
completion get 3-4× the AI visibility of sparse records. This service exposes
the gap.

Pure functions. No I/O.
"""
from __future__ import annotations

import re

from app.models.merchant import MerchantData, Product


# ---------------------------------------------------------------------------
# Rubric definition
# ---------------------------------------------------------------------------

# Each entry: (key, weight, predicate(product, metafields, seo) -> bool)
GOLDEN_FIELDS: list[tuple[str, float]] = [
    ("title_present",          1.0),
    ("title_long_enough",      1.0),   # > 25 chars
    ("title_has_category",     1.0),
    ("description_present",    1.0),
    ("description_long_enough",1.0),   # > 250 chars
    ("multiple_images",        1.0),   # >= 3
    ("alt_text_on_all_images", 1.0),
    ("has_variants_or_options",0.5),
    ("price_set",              1.0),
    ("inventory_tracked",      0.5),
    ("vendor_set",             1.0),
    ("product_type_set",       1.0),
    ("tags_present",           0.5),
    ("seo_title_set",          0.5),
    ("seo_description_set",    0.5),
    ("gtin_or_mpn",            1.0),
    ("brand_set",              1.0),
    ("material_metafield",     0.5),
    ("color_metafield",        0.5),
    ("size_metafield",         0.5),
    ("weight_or_dimensions",   0.5),
    ("care_instructions",      0.5),
    ("compatibility_metafield",0.5),
    ("certifications",         0.25),
    ("country_of_origin",      0.25),
]

TOTAL_WEIGHT = sum(w for _, w in GOLDEN_FIELDS)


# ---------------------------------------------------------------------------
# Rubric checks
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "")


def _metafield_present(metafields: list[dict], keys: list[str]) -> bool:
    keyset = {k.lower() for k in keys}
    for mf in metafields or []:
        if str(mf.get("key", "")).lower() in keyset and str(mf.get("value", "")).strip():
            return True
    return False


def _evaluate_product(
    product: Product,
    metafields: list[dict],
    seo: dict,
) -> dict[str, bool]:
    desc_text = _strip_html(product.body_html or "").strip()
    title = (product.title or "").strip()

    has_inventory = any(v.inventory_management == "shopify" for v in product.variants)
    any_price = any(v.price and v.price not in ("0", "0.00") for v in product.variants)

    return {
        "title_present":          bool(title),
        "title_long_enough":      len(title) >= 25,
        "title_has_category":     bool(product.product_type) and product.product_type.lower() in title.lower(),
        "description_present":    bool(desc_text),
        "description_long_enough":len(desc_text) >= 250,
        "multiple_images":        len(product.images) >= 3,
        "alt_text_on_all_images": bool(product.images) and all(bool(img.alt) for img in product.images),
        "has_variants_or_options":bool(product.options) or len(product.variants) > 1,
        "price_set":              any_price,
        "inventory_tracked":      has_inventory,
        "vendor_set":             bool(product.vendor),
        "product_type_set":       bool(product.product_type),
        "tags_present":           len(product.tags) >= 2,
        "seo_title_set":          bool((seo or {}).get("title")),
        "seo_description_set":    bool((seo or {}).get("description")),
        "gtin_or_mpn":            _metafield_present(metafields, ["gtin", "ean", "upc", "barcode", "mpn"]) or any(v.sku for v in product.variants),
        "brand_set":              bool(product.vendor) or _metafield_present(metafields, ["brand"]),
        "material_metafield":     _metafield_present(metafields, ["material", "fabric"]),
        "color_metafield":        _metafield_present(metafields, ["color", "colour"]) or any(o.name.lower() == "color" for o in product.options),
        "size_metafield":         _metafield_present(metafields, ["size"]) or any(o.name.lower() == "size" for o in product.options),
        "weight_or_dimensions":   _metafield_present(metafields, ["weight", "dimensions", "length", "width", "height"]),
        "care_instructions":      _metafield_present(metafields, ["care", "care_instructions", "wash"]),
        "compatibility_metafield":_metafield_present(metafields, ["compatibility", "compatible_with", "fits"]),
        "certifications":         _metafield_present(metafields, ["certification", "certifications", "iso", "ce_mark"]),
        "country_of_origin":      _metafield_present(metafields, ["country_of_origin", "made_in", "origin"]),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_product(product: Product, metafields: list[dict], seo: dict) -> dict:
    checks = _evaluate_product(product, metafields, seo)
    earned = 0.0
    missing: list[str] = []
    for key, weight in GOLDEN_FIELDS:
        if checks.get(key):
            earned += weight
        else:
            missing.append(key)
    pct = round(100 * earned / TOTAL_WEIGHT, 1)
    return {
        "product_id": product.id,
        "title": product.title,
        "score_pct": pct,
        "weight_earned": round(earned, 2),
        "weight_total": round(TOTAL_WEIGHT, 2),
        "missing_fields": missing,
    }


def score_store(merchant_data: MerchantData) -> dict:
    """Per-product scores + store-level distribution + AI visibility tier estimate."""
    by_product: list[dict] = []
    for p in merchant_data.products:
        mfs = (merchant_data.metafields_by_product or {}).get(p.id) or []
        seo = (merchant_data.seo_by_product or {}).get(p.id) or {}
        by_product.append(score_product(p, mfs, seo))

    if not by_product:
        return {
            "store_score_pct": 0.0,
            "tier": "UNKNOWN",
            "histogram": {"0-25": 0, "25-50": 0, "50-75": 0, "75-90": 0, "90-99": 0, "99+": 0},
            "products": [],
            "weakest_fields": [],
        }

    pct_values = [p["score_pct"] for p in by_product]
    avg = round(sum(pct_values) / len(pct_values), 1)

    # Histogram
    buckets = {"0-25": 0, "25-50": 0, "50-75": 0, "75-90": 0, "90-99": 0, "99+": 0}
    for v in pct_values:
        if v < 25:    buckets["0-25"] += 1
        elif v < 50:  buckets["25-50"] += 1
        elif v < 75:  buckets["50-75"] += 1
        elif v < 90:  buckets["75-90"] += 1
        elif v < 99:  buckets["90-99"] += 1
        else:         buckets["99+"] += 1

    # Tier (Google AI Mode 2026 thresholds)
    if avg >= 99:
        tier = "GOLDEN"          # 3-4× visibility
    elif avg >= 90:
        tier = "STRONG"
    elif avg >= 75:
        tier = "ADEQUATE"
    elif avg >= 50:
        tier = "WEAK"
    else:
        tier = "INVISIBLE"

    # Weakest fields across catalog
    field_misses: dict[str, int] = {}
    for p in by_product:
        for f in p["missing_fields"]:
            field_misses[f] = field_misses.get(f, 0) + 1
    weakest = sorted(field_misses.items(), key=lambda x: -x[1])[:10]
    weakest_out = [{"field": f, "missing_count": c, "missing_pct": round(100*c/len(by_product),1)} for f, c in weakest]

    by_product.sort(key=lambda x: x["score_pct"])
    return {
        "store_score_pct": avg,
        "tier": tier,
        "tier_thresholds": {"GOLDEN": 99, "STRONG": 90, "ADEQUATE": 75, "WEAK": 50},
        "histogram": buckets,
        "products": by_product,
        "weakest_fields": weakest_out,
    }
