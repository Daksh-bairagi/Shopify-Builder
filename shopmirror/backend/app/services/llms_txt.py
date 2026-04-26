"""
llms_txt.py — Generate /llms.txt and /llms-full.txt content for AI crawlers.

Spec: https://llmstxt.org/  (proposed Answer.AI standard)
Audience: GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot during inference.

Pure functions. No I/O, no LLM calls.
"""
from __future__ import annotations

from app.models.merchant import MerchantData


def _domain_url(store_domain: str) -> str:
    if store_domain.startswith("http"):
        return store_domain.rstrip("/")
    return f"https://{store_domain.rstrip('/')}"


def _strip_html(html: str, limit: int = 240) -> str:
    """Remove tags, collapse whitespace, truncate."""
    import re
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def generate_llms_txt(merchant_data: MerchantData) -> str:
    """
    Build a Markdown llms.txt that maps the most important resources of the store.

    Output structure:
        # <Store Name>
        > one-line summary
        ## Product Catalog
        - [feed](url)
        - [sitemap](url)
        ## Collections
        - [name](url) — body
        ## Policies
        - [refund](url)
        ## Top Products
        - [title](url) — short body
    """
    base = _domain_url(merchant_data.store_domain)
    lines: list[str] = []

    lines.append(f"# {merchant_data.store_name or merchant_data.store_domain}")
    n_products = len(merchant_data.products)
    n_collections = len(merchant_data.collections)
    lines.append(
        f"> Shopify storefront with {n_products} products across "
        f"{n_collections} collections. AI agents can read structured product "
        f"data via the linked feed and sitemap below."
    )
    lines.append("")

    # ---------------- Product Catalog ----------------
    lines.append("## Product Catalog")
    lines.append(f"- [Product feed (JSON)]({base}/products.json)")
    lines.append(f"- [XML sitemap]({base}/sitemap.xml)")
    lines.append(f"- [Sitemap (products only)]({base}/sitemap_products_1.xml)")
    if merchant_data.collections:
        lines.append(f"- [All collections]({base}/collections)")
    lines.append("")

    # ---------------- Collections ----------------
    if merchant_data.collections:
        lines.append("## Collections")
        for coll in merchant_data.collections[:25]:
            blurb = _strip_html(coll.body_html or "", 140) or coll.title
            lines.append(f"- [{coll.title}]({base}/collections/{coll.handle}) — {blurb}")
        lines.append("")

    # ---------------- Policies ----------------
    has_any_policy = any(
        getattr(merchant_data.policies, k)
        for k in ("refund", "shipping", "privacy", "terms_of_service")
    )
    if has_any_policy:
        lines.append("## Policies")
        for slug, attr in [
            ("refund-policy", "refund"),
            ("shipping-policy", "shipping"),
            ("privacy-policy", "privacy"),
            ("terms-of-service", "terms_of_service"),
        ]:
            if getattr(merchant_data.policies, attr):
                lines.append(f"- [{attr.replace('_', ' ').title()}]({base}/policies/{slug})")
        lines.append("")

    # ---------------- Top Products ----------------
    if merchant_data.products:
        lines.append("## Top Products")
        for p in merchant_data.products[:50]:
            blurb = _strip_html(p.body_html or "", 160) or p.title
            lines.append(f"- [{p.title}]({base}/products/{p.handle}) — {blurb}")
        lines.append("")

    # ---------------- Optional FAQ pointer ----------------
    lines.append("## Optional")
    lines.append(f"- [Search]({base}/search)")
    lines.append(f"- [Contact]({base}/pages/contact)")
    lines.append("")

    return "\n".join(lines).strip() + "\n"


def generate_llms_full_txt(merchant_data: MerchantData) -> str:
    """
    Build /llms-full.txt — verbose Markdown of the catalog optimized for LLM ingestion.
    Each product gets a heading + structured attributes block + description.
    """
    base = _domain_url(merchant_data.store_domain)
    lines: list[str] = []
    lines.append(f"# {merchant_data.store_name or merchant_data.store_domain} — Full Catalog")
    lines.append("")
    lines.append(
        "This document is intended for AI assistants. Each product is presented "
        "as a self-contained section with title, URL, identifiers, attributes, "
        "and a plain-text description."
    )
    lines.append("")

    for p in merchant_data.products:
        lines.append(f"## {p.title}")
        lines.append("")
        url = f"{base}/products/{p.handle}"
        lines.append(f"- URL: {url}")
        if p.vendor:
            lines.append(f"- Brand: {p.vendor}")
        if p.product_type:
            lines.append(f"- Category: {p.product_type}")
        if p.tags:
            lines.append(f"- Tags: {', '.join(p.tags[:20])}")
        if p.variants:
            v = p.variants[0]
            lines.append(f"- Price: {v.price}")
            if v.sku:
                lines.append(f"- SKU: {v.sku}")
            in_stock_count = sum(1 for vv in p.variants if vv.inventory_quantity > 0)
            lines.append(
                f"- Variants: {len(p.variants)} ({in_stock_count} currently in stock)"
            )
        if p.options:
            opts = ", ".join(f"{o.name}: {'/'.join(o.values[:6])}" for o in p.options)
            lines.append(f"- Options: {opts}")
        lines.append("")
        desc = _strip_html(p.body_html or "", 1200)
        if desc:
            lines.append(desc)
            lines.append("")

    return "\n".join(lines).strip() + "\n"
