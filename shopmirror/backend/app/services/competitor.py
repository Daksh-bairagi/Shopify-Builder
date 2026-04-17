from __future__ import annotations

import asyncio
import os
import re
from urllib.parse import urlparse

import httpx

from app.models.merchant import MerchantData
from app.models.findings import Finding, CompetitorAudit, CompetitorResult
from app.utils.validators import detect_shopify
from app.utils.retry import async_retry


# Domains that are never competitor Shopify stores
_BLOCKLIST: set[str] = {
    "amazon.com",
    "etsy.com",
    "shopify.com",
    "reddit.com",
    "youtube.com",
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "pinterest.com",
}

# Bots whose blocking in robots.txt is a negative signal (D1a check)
_AI_BOTS = {"GPTBot", "PerplexityBot"}


def _extract_domain(url: str) -> str | None:
    """Return bare hostname from a URL string, or None if unparseable."""
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        host = parsed.hostname or ""
        return host.lower() if host else None
    except Exception:
        return None


def _is_blocklisted(domain: str) -> bool:
    for blocked in _BLOCKLIST:
        if domain == blocked or domain.endswith(f".{blocked}"):
            return True
    return False


async def find_competitors(
    store_domain: str,
    store_name: str,
    product_types: list[str],
    max_results: int = 5,
) -> list[str]:
    """Discover competitor Shopify stores via DuckDuckGo or SerpAPI.

    Returns a list of base URLs (with https://) for confirmed Shopify stores,
    capped at *max_results*. Returns [] on any failure.
    """
    try:
        primary = product_types[0] if product_types else store_name
        query = f'"{primary}" shopify store'

        serpapi_key = os.environ.get("SERPAPI_KEY")

        if serpapi_key:
            raw_urls = await _search_serpapi(query, serpapi_key)
        else:
            raw_urls = await _search_duckduckgo(query)

        merchant_domain = _extract_domain(store_domain) or store_domain.lower()

        seen_domains: dict[str, str] = {}  # domain -> first full url
        for url in raw_urls:
            domain = _extract_domain(url)
            if not domain:
                continue
            if domain == merchant_domain:
                continue
            if _is_blocklisted(domain):
                continue
            if domain not in seen_domains:
                seen_domains[domain] = url

        if not seen_domains:
            return []

        # Validate candidates in parallel
        domains = list(seen_domains.keys())
        results: list[bool] = await asyncio.gather(
            *[detect_shopify(d) for d in domains],
            return_exceptions=False,
        )

        confirmed: list[str] = []
        for domain, is_shopify in zip(domains, results):
            if is_shopify:
                confirmed.append(f"https://{domain}")
            if len(confirmed) >= max_results:
                break

        return confirmed

    except Exception:
        return []


async def _search_duckduckgo(query: str) -> list[str]:
    """Run a DuckDuckGo text search in a thread executor (DDGS is sync)."""
    loop = asyncio.get_running_loop()

    def _run() -> list[str]:
        from duckduckgo_search import DDGS  # imported here to stay optional

        results = list(DDGS().text(query, max_results=20))
        return [r["href"] for r in results if "href" in r]

    return await loop.run_in_executor(None, _run)


async def _search_serpapi(query: str, api_key: str) -> list[str]:
    """Run a Google search via SerpAPI and return result URLs."""
    params = {
        "q": query,
        "api_key": api_key,
        "num": 20,
        "engine": "google",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get("https://serpapi.com/search", params=params)
        resp.raise_for_status()
        data = resp.json()
    return [r["link"] for r in data.get("organic_results", []) if "link" in r]


# ---------------------------------------------------------------------------
# Competitor auditing
# ---------------------------------------------------------------------------

@async_retry
async def _fetch_products_json(base_url: str) -> list[dict]:
    """Fetch up to 10 products from a competitor's public products.json."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{base_url}/products.json", params={"limit": 10})
        resp.raise_for_status()
        return resp.json().get("products", [])


@async_retry
async def _fetch_robots_txt(base_url: str) -> str:
    """Fetch robots.txt text from competitor."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{base_url}/robots.txt")
        if resp.status_code == 200:
            return resp.text
        return ""


async def _fetch_policy_text(base_url: str, path: str) -> str:
    """Fetch a policy page and return its text, or '' on failure/non-200."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}{path}")
            if resp.status_code == 200:
                return resp.text
            return ""
    except Exception:
        return ""


def _check_d1a(robots_txt: str) -> bool:
    """D1a: True (passes) if no AI bots are blocked."""
    for bot in _AI_BOTS:
        # Look for User-agent: <bot> followed by Disallow: / (with optional whitespace/newline)
        pattern = rf"User-agent\s*:\s*{re.escape(bot)}.*?Disallow\s*:\s*/(?:\s|$)"
        if re.search(pattern, robots_txt, re.IGNORECASE | re.DOTALL):
            return False  # bot is blocked — fails check
    return True


_GENERIC_TYPES = {"", "uncategorized", "n/a", "none"}


def _check_c1(products: list[dict]) -> bool:
    """C1 (proxy): True if any product has a non-empty, non-generic product_type.
    Taxonomy GID is unavailable from public products.json."""
    for p in products:
        pt = (p.get("product_type") or "").strip()
        if pt.lower() not in _GENERIC_TYPES:
            return True
    return False


_UNNAMED_OPTIONS = {"title", "option1", "option2", "option3"}


def _check_c3(products: list[dict]) -> bool:
    """C3: True if at least one product has a non-generic option name (not Title/Option1/2/3)."""
    for p in products:
        for opt in p.get("options", []):
            if (opt.get("name") or "").strip().lower() not in _UNNAMED_OPTIONS:
                return True
    return False


def _check_c4(products: list[dict]) -> bool:
    """C4: True if any variant has a numeric SKU >= 8 digits (GTIN proxy)."""
    for p in products:
        for v in p.get("variants", []):
            sku = (v.get("sku") or "").strip()
            if re.fullmatch(r"\d{8,}", sku):
                return True
    return False


def _check_c6(products: list[dict]) -> bool:
    """C6: True if >=70% of images have non-empty alt text."""
    total = 0
    with_alt = 0
    for p in products:
        for img in p.get("images", []):
            total += 1
            alt = (img.get("alt") or "").strip()
            if alt:
                with_alt += 1
    if total == 0:
        return False  # no images — cannot pass
    return (with_alt / total) >= 0.70


async def audit_competitor(
    competitor_url: str,
    merchant_findings: list[Finding],
) -> CompetitorResult | None:
    """Fetch public data from a competitor store and run a lightweight check subset.

    Returns None if the store is unreachable or returns no products.
    """
    try:
        # Fetch products and robots in parallel
        products, robots_txt = await asyncio.gather(
            _fetch_products_json(competitor_url),
            _fetch_robots_txt(competitor_url),
            return_exceptions=True,
        )

        # Bail out if products fetch failed or returned nothing
        if isinstance(products, BaseException) or not products:
            return None
        if isinstance(robots_txt, BaseException):
            robots_txt = ""

        # Policy checks — fetch page text, then inspect content
        refund_text, shipping_text = await asyncio.gather(
            _fetch_policy_text(competitor_url, "/policies/refund-policy"),
            _fetch_policy_text(competitor_url, "/policies/shipping-policy"),
        )
        t1_pass = bool(re.search(r"\d+\s*days?", refund_text, re.IGNORECASE))
        _SHIPPING_KEYWORDS = [
            "united states", " us ", "uk", "canada", "australia",
            "europe", "worldwide", "international",
        ]
        t2_pass = any(kw in shipping_text.lower() for kw in _SHIPPING_KEYWORDS)

        check_results: dict[str, bool] = {
            "D1a": _check_d1a(robots_txt),
            "C1":  _check_c1(products),
            "C3":  _check_c3(products),
            "C4":  _check_c4(products),
            "C6":  _check_c6(products),
            "T1":  t1_pass,
            "T2":  t2_pass,
        }

        domain = _extract_domain(competitor_url) or competitor_url
        audit = CompetitorAudit(
            url=competitor_url,
            store_domain=domain,
            check_results=check_results,
        )

        # Gaps: checks the merchant fails but this competitor passes
        merchant_failing = {f.check_id for f in merchant_findings}
        gaps = [
            cid
            for cid, passed in check_results.items()
            if passed and cid in merchant_failing
        ]

        return CompetitorResult(competitor=audit, gaps=gaps)

    except Exception:
        return None


async def run_competitor_analysis(
    merchant_data: MerchantData,
    merchant_findings: list[Finding],
    competitor_urls: list[str] | None = None,
) -> list[CompetitorResult]:
    """Main entry point for competitor analysis.

    Discovers or validates competitor stores, audits up to 3 in parallel,
    and returns results sorted by number of gaps (most impactful first).
    """
    if competitor_urls:
        # Caller-supplied URLs — still validate they are Shopify stores
        validation_results: list[bool] = await asyncio.gather(
            *[
                detect_shopify(_extract_domain(u) or u)
                for u in competitor_urls
            ],
            return_exceptions=False,
        )
        candidates = [
            url
            for url, is_shopify in zip(competitor_urls, validation_results)
            if is_shopify
        ]
    else:
        product_types = list(
            {p.product_type for p in merchant_data.products if p.product_type}
        )
        candidates = await find_competitors(
            store_domain=merchant_data.store_domain,
            store_name=merchant_data.store_name,
            product_types=product_types,
        )

    # Audit up to 3 competitors in parallel
    audit_targets = candidates[:3]
    raw_results = await asyncio.gather(
        *[audit_competitor(url, merchant_findings) for url in audit_targets],
        return_exceptions=False,
    )

    results: list[CompetitorResult] = [r for r in raw_results if r is not None]

    # Sort by number of gaps descending — most impactful comparison first
    results.sort(key=lambda r: len(r.gaps), reverse=True)

    return results
