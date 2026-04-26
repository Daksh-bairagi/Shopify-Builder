"""
identifier_audit.py — Audit GTIN / MPN / Brand on every product.

Why it matters: Perplexity demotes products without GTIN; Google Merchant
Center hides products that lack identifiers when they should have them;
ChatGPT Shopping uses identifiers for de-duplication across merchants.

Pure functions. No I/O.
"""
from __future__ import annotations

import re

from app.models.merchant import MerchantData


GTIN_LENGTHS = {8, 12, 13, 14}


def _is_valid_gtin(value: str) -> bool:
    """GTIN-8/12/13/14 — pure-digit + checksum."""
    if not value or not value.isdigit():
        return False
    if len(value) not in GTIN_LENGTHS:
        return False
    digits = [int(c) for c in value]
    check = digits.pop()
    digits.reverse()
    weighted = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(digits))
    return (10 - weighted % 10) % 10 == check


def _coerce_str(v) -> str:
    return "" if v is None else str(v).strip()


def extract_identifiers(product, metafields: list[dict] | None) -> dict:
    """
    Single source of truth for product identifier extraction. Used by both the
    audit endpoint and the channel feed builders.

    Returns {"gtin": "<val or ''>", "mpn": "...", "brand": "..."} drawing from
    variants and metafields. GTINs are checksum-validated. SKU is checked as a
    fallback when no GTIN/MPN metafield is present.
    """
    gtin = ""
    mpn = ""
    brand = _coerce_str(product.vendor)

    # First variant's barcode is the canonical GTIN slot in Shopify Admin API.
    if product.variants:
        v = product.variants[0]
        sku_str = _coerce_str(v.sku)
        # SKU often holds GTIN or MPN — auto-detect.
        if _is_valid_gtin(sku_str):
            gtin = sku_str
        elif sku_str:
            mpn = sku_str

    # Metafields override / supplement.
    for mf in metafields or []:
        key = _coerce_str(mf.get("key")).lower()
        val = _coerce_str(mf.get("value"))
        if not val:
            continue
        if key in ("gtin", "ean", "upc", "barcode"):
            if _is_valid_gtin(val):
                gtin = val
        elif key in ("mpn", "manufacturer_part_number", "part_number"):
            mpn = val
        elif key == "brand" and not brand:
            brand = val

    return {"gtin": gtin, "mpn": mpn, "brand": brand}


# Backwards-compatible private alias.
_extract_identifiers = extract_identifiers


def audit_identifiers(merchant_data: MerchantData) -> dict:
    """
    Returns:
        {
            "summary": { ... totals ... },
            "products": [
                {"product_id": ..., "title": ..., "gtin": ..., "mpn": ...,
                 "brand": ..., "missing": [...], "score": 0-3}
            ],
            "fix_suggestions": [...]
        }
    """
    out_products: list[dict] = []
    have_gtin = 0
    have_mpn = 0
    have_brand = 0
    fully_identified = 0   # has at least GTIN OR (MPN + Brand)

    fix_suggestions: list[dict] = []

    for p in merchant_data.products:
        mfs = (merchant_data.metafields_by_product or {}).get(p.id) or []
        ids = _extract_identifiers(p, mfs)
        missing = [k for k in ("gtin", "mpn", "brand") if not ids[k]]
        score = 3 - len(missing)

        if ids["gtin"]:
            have_gtin += 1
        if ids["mpn"]:
            have_mpn += 1
        if ids["brand"]:
            have_brand += 1
        if ids["gtin"] or (ids["mpn"] and ids["brand"]):
            fully_identified += 1
        else:
            # Suggest the cheapest path to compliance.
            if not ids["brand"] and not ids["mpn"] and not ids["gtin"]:
                hint = "Add Brand (Vendor) + MPN at minimum. GTIN strongly preferred if barcode exists."
            elif not ids["gtin"] and not ids["mpn"]:
                hint = "Add MPN via metafield (mpn.metafield.value) for AI de-duplication."
            elif not ids["gtin"] and not ids["brand"]:
                hint = "Set product.vendor as Brand."
            elif not ids["gtin"]:
                hint = "Add GTIN to variant.barcode field if a manufacturer barcode exists."
            else:
                hint = "Identifiers complete."
            fix_suggestions.append({
                "product_id": p.id,
                "title": p.title,
                "missing": missing,
                "hint": hint,
            })

        out_products.append({
            "product_id": p.id,
            "title": p.title,
            "gtin": ids["gtin"],
            "mpn": ids["mpn"],
            "brand": ids["brand"],
            "missing": missing,
            "score": score,
        })

    total = len(merchant_data.products) or 1
    return {
        "summary": {
            "total_products": len(merchant_data.products),
            "have_gtin": have_gtin,
            "have_mpn": have_mpn,
            "have_brand": have_brand,
            "fully_identified": fully_identified,
            "gtin_pct":  round(100 * have_gtin / total, 1),
            "mpn_pct":   round(100 * have_mpn / total, 1),
            "brand_pct": round(100 * have_brand / total, 1),
            "compliant_pct": round(100 * fully_identified / total, 1),
        },
        "products": out_products,
        "fix_suggestions": fix_suggestions[:50],
    }
