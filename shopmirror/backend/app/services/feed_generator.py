"""
feed_generator.py — Build channel-specific product feeds.

Channels:
  - ChatGPT Shopping (.jsonl per ACP product feed spec, 2026-04-17)
  - Perplexity Merchant Program (XML, GTIN-required)
  - Google Merchant Center / AI Mode (XML, RSS 2.0 with g: namespace)

Pure builders — caller decides how to serve / compress.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
from typing import Optional
from xml.sax.saxutils import escape as xml_escape

from app.models.merchant import MerchantData, Product, ProductVariant
from app.services.identifier_audit import extract_identifiers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _domain_url(store_domain: str) -> str:
    if store_domain.startswith("http"):
        return store_domain.rstrip("/")
    return f"https://{store_domain.rstrip('/')}"


def _strip_html(text: str, limit: int = 5000) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _safe_price(p: str) -> str:
    if not p:
        return "0.00"
    return re.sub(r"[^\d.]", "", str(p)) or "0.00"


def _availability(v: ProductVariant) -> str:
    if v.inventory_quantity > 0:
        return "in_stock"
    if v.inventory_policy == "continue":
        return "backorder"
    return "out_of_stock"


def _detect_currency(merchant_data: MerchantData) -> str:
    for blocks in (merchant_data.schema_by_url or {}).values():
        for b in blocks or []:
            offers = b.get("offers") if isinstance(b, dict) else None
            if isinstance(offers, dict):
                cur = offers.get("priceCurrency") or offers.get("priceCurrencyCode")
                if cur:
                    return str(cur)
    return "USD"


def _gtin_or_mpn(product: Product, metafields: list[dict] | None) -> tuple[str, str]:
    """Wrapper kept for call-site readability. Delegates to the shared,
    checksum-validating extractor in identifier_audit so feeds and the audit
    endpoint always agree on the same identifiers."""
    ids = extract_identifiers(product, metafields)
    return ids["gtin"], ids["mpn"]


# ---------------------------------------------------------------------------
# ChatGPT Shopping feed (ACP 2026-04-17)
# ---------------------------------------------------------------------------

def build_chatgpt_feed(
    merchant_data: MerchantData,
    target_country: str = "US",
    feed_id: Optional[str] = None,
    account_id: Optional[str] = None,
) -> dict:
    """
    Returns {"jsonl": str, "summary": dict}.
    JSONL: one product variant per line. Out-of-stock variants get
    enable_search=False; in-stock get enable_search=True.
    """
    base = _domain_url(merchant_data.store_domain)
    currency = _detect_currency(merchant_data)
    feed_id = feed_id or f"feed_{merchant_data.store_domain.replace('.', '_')}"
    account_id = account_id or merchant_data.store_domain
    timestamp = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    lines: list[str] = []
    enabled = 0
    disabled = 0

    for p in merchant_data.products:
        mfs = (merchant_data.metafields_by_product or {}).get(p.id) or []
        gtin, mpn = _gtin_or_mpn(p, mfs)
        product_url = f"{base}/products/{p.handle}"
        primary_image = p.images[0].src if p.images else None

        for v in (p.variants or [None]):
            if v is None:
                continue
            in_stock = v.inventory_quantity > 0
            enable_search = in_stock or v.inventory_policy == "continue"
            if enable_search:
                enabled += 1
            else:
                disabled += 1

            line = {
                # Header / routing
                "feed_id": feed_id,
                "account_id": account_id,
                "target_country": target_country,
                "timestamp": timestamp,
                # Product identity
                "id": p.id,
                "variant_id": v.id,
                "title": p.title,
                "variant_title": v.title or p.title,
                "description": _strip_html(p.body_html, 5000),
                "link": f"{product_url}?variant={v.id}",
                "image_link": primary_image,
                "additional_image_links": [img.src for img in p.images[1:6]],
                # Identifiers
                "brand": p.vendor or None,
                "gtin": gtin or None,
                "mpn": mpn or None,
                # Inventory + price
                "price": f"{_safe_price(v.price)} {currency}",
                "availability": _availability(v),
                "condition": "new",
                # Visibility flags (ACP)
                "enable_search": enable_search,
                "enable_checkout": False,   # default off; merchant opts in
                # Taxonomy hints
                "product_type": p.product_type or None,
                "google_product_category": None,  # caller can map taxonomy_by_product
                # Variant axes
                "color": v.option1 if (p.options and p.options[0].name.lower() == "color") else None,
                "size": v.option2 if (len(p.options) > 1 and p.options[1].name.lower() == "size") else None,
            }
            line = {k: val for k, val in line.items() if val not in (None, "", [])}
            lines.append(json.dumps(line, separators=(",", ":"), ensure_ascii=False))

    return {
        "jsonl": "\n".join(lines) + ("\n" if lines else ""),
        "summary": {
            "total_lines": len(lines),
            "enable_search_true": enabled,
            "enable_search_false": disabled,
            "feed_id": feed_id,
            "target_country": target_country,
            "currency": currency,
        },
    }


# ---------------------------------------------------------------------------
# Perplexity Merchant feed (XML)
# ---------------------------------------------------------------------------

def build_perplexity_feed(merchant_data: MerchantData) -> dict:
    base = _domain_url(merchant_data.store_domain)
    currency = _detect_currency(merchant_data)
    items: list[str] = []
    skipped_no_gtin = 0

    for p in merchant_data.products:
        mfs = (merchant_data.metafields_by_product or {}).get(p.id) or []
        gtin, mpn = _gtin_or_mpn(p, mfs)
        if not (gtin or (mpn and p.vendor)):
            # Perplexity rejects records without a stable identifier path.
            skipped_no_gtin += 1
            continue
        product_url = f"{base}/products/{p.handle}"
        primary_image = p.images[0].src if p.images else ""
        v = p.variants[0] if p.variants else None
        price_str = f"{_safe_price(v.price if v else '0')}" + f" {currency}"

        items.append(
            "<item>"
            f"<id>{xml_escape(p.id)}</id>"
            f"<title>{xml_escape(p.title)}</title>"
            f"<description>{xml_escape(_strip_html(p.body_html, 5000))}</description>"
            f"<link>{xml_escape(product_url)}</link>"
            f"<image_link>{xml_escape(primary_image)}</image_link>"
            f"<price>{xml_escape(price_str)}</price>"
            f"<availability>{xml_escape(_availability(v) if v else 'out_of_stock')}</availability>"
            f"<brand>{xml_escape(p.vendor or '')}</brand>"
            f"<gtin>{xml_escape(gtin)}</gtin>"
            f"<mpn>{xml_escape(mpn)}</mpn>"
            f"<condition>new</condition>"
            f"<product_type>{xml_escape(p.product_type or '')}</product_type>"
            "</item>"
        )

    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "<channel>\n"
        f"<title>{xml_escape(merchant_data.store_name)}</title>\n"
        f"<link>{xml_escape(base)}</link>\n"
        f"<description>Perplexity Merchant Program feed</description>\n"
        + "\n".join(items) + "\n"
        "</channel>\n</rss>\n"
    )

    return {
        "xml": body,
        "summary": {
            "total_items": len(items),
            "skipped_without_identifier": skipped_no_gtin,
            "currency": currency,
        },
    }


# ---------------------------------------------------------------------------
# Google Merchant Center / AI Mode feed (RSS 2.0 + g: namespace)
# ---------------------------------------------------------------------------

def build_google_feed(merchant_data: MerchantData) -> dict:
    base = _domain_url(merchant_data.store_domain)
    currency = _detect_currency(merchant_data)
    items: list[str] = []
    invalid: int = 0

    for p in merchant_data.products:
        mfs = (merchant_data.metafields_by_product or {}).get(p.id) or []
        gtin, mpn = _gtin_or_mpn(p, mfs)
        if not p.vendor and not gtin and not mpn:
            invalid += 1
        primary_image = p.images[0].src if p.images else ""
        v = p.variants[0] if p.variants else None

        items.append(
            "<item>\n"
            f"  <g:id>{xml_escape(p.id)}</g:id>\n"
            f"  <g:title>{xml_escape(p.title)}</g:title>\n"
            f"  <g:description>{xml_escape(_strip_html(p.body_html, 5000))}</g:description>\n"
            f"  <g:link>{xml_escape(base)}/products/{xml_escape(p.handle)}</g:link>\n"
            f"  <g:image_link>{xml_escape(primary_image)}</g:image_link>\n"
            + "".join(f"  <g:additional_image_link>{xml_escape(img.src)}</g:additional_image_link>\n" for img in p.images[1:10])
            + f"  <g:availability>{xml_escape(_availability(v) if v else 'out_of_stock')}</g:availability>\n"
            f"  <g:price>{xml_escape(f'{_safe_price(v.price if v else 0)} {currency}')}</g:price>\n"
            f"  <g:brand>{xml_escape(p.vendor or '')}</g:brand>\n"
            f"  <g:gtin>{xml_escape(gtin)}</g:gtin>\n"
            f"  <g:mpn>{xml_escape(mpn)}</g:mpn>\n"
            f"  <g:identifier_exists>{('yes' if (gtin or mpn or p.vendor) else 'no')}</g:identifier_exists>\n"
            f"  <g:condition>new</g:condition>\n"
            f"  <g:product_type>{xml_escape(p.product_type or '')}</g:product_type>\n"
            "</item>"
        )

    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\n'
        "<channel>\n"
        f"<title>{xml_escape(merchant_data.store_name)}</title>\n"
        f"<link>{xml_escape(base)}</link>\n"
        "<description>Google Merchant Center / AI Mode feed</description>\n"
        + "\n".join(items) + "\n"
        "</channel>\n</rss>\n"
    )

    return {
        "xml": body,
        "summary": {
            "total_items": len(items),
            "items_missing_identifier": invalid,
            "currency": currency,
        },
    }
