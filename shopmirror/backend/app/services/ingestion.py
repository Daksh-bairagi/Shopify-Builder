"""
Merchant ingestion helpers.

This module translates Shopify storefront/Admin payloads into the normalized
`MerchantData` shape used by the rest of the system. Keeping those conversion
rules here lets the audit pipeline reason about one stable internal model.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Optional

import httpx

from app.models.merchant import (
    Collection,
    MerchantData,
    Policies,
    Product,
    ProductImage,
    ProductOption,
    ProductVariant,
)
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize_url(store_url: str) -> str:
    """Strip trailing slash, ensure https:// prefix."""
    url = store_url.strip().rstrip("/")
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    # Downgrade http → https for Shopify stores
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url


def _bare_domain(url: str) -> str:
    """Return host/domain only, with protocol removed after normalization."""
    return re.sub(r"^https?://", "", _normalize_url(url))


_MYSHOPIFY_RE = re.compile(r"([a-z0-9][a-z0-9\-]*\.myshopify\.com)", re.IGNORECASE)


def _extract_myshopify_domain(text: str) -> Optional[str]:
    match = _MYSHOPIFY_RE.search(text or "")
    return match.group(1).lower() if match else None


def _extract_json_ld(html: str) -> list[dict]:
    """Return all parsed JSON-LD blocks found in an HTML page."""
    blocks: list[dict] = []
    pattern = re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(html):
        raw = match.group(1).strip()
        try:
            parsed = json.loads(raw)
            # A single page may contain a list or a single object
            if isinstance(parsed, list):
                blocks.extend(parsed)
            elif isinstance(parsed, dict):
                blocks.append(parsed)
        except json.JSONDecodeError:
            logger.debug("Failed to parse JSON-LD block: %s", raw[:120])
    return blocks


def _gid_to_id(gid: str) -> str:
    """'gid://shopify/Product/12345' → '12345'"""
    return gid.rsplit("/", 1)[-1]


@async_retry
async def _run_admin_query(
    url: str,
    token: str,
    query: str,
    variables: Optional[dict] = None,
) -> dict:
    """POST a GraphQL query to the Shopify Admin API and return the response dict.

    Raises httpx.HTTPStatusError on 4xx/5xx, and RuntimeError if the response
    contains top-level 'errors'.
    """
    payload: dict = {"query": query}
    if variables:
        payload["variables"] = variables

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        body = response.json()
    if "errors" in body:
        raise RuntimeError(f"GraphQL errors from {url}: {body['errors']}")
    return body


# ---------------------------------------------------------------------------
# Product/collection parsing helpers for REST API
# ---------------------------------------------------------------------------

def _parse_variant(v: dict) -> ProductVariant:
    """Map a Shopify REST variant object into our internal dataclass."""
    return ProductVariant(
        id=str(v["id"]),
        title=v.get("title", ""),
        price=v.get("price", "0.00"),
        sku=v.get("sku") or "",
        inventory_management=v.get("inventory_management"),
        inventory_policy=v.get("inventory_policy", "deny"),
        inventory_quantity=v.get("inventory_quantity") or 0,
        option1=v.get("option1"),
        option2=v.get("option2"),
        option3=v.get("option3"),
    )


def _parse_image(img: dict) -> ProductImage:
    """Map a Shopify REST image object into our internal dataclass."""
    return ProductImage(
        id=str(img["id"]),
        src=img.get("src", ""),
        alt=img.get("alt"),
        position=img.get("position", 0),
    )


def _parse_option(opt: dict) -> ProductOption:
    """Map a Shopify REST option object into our internal dataclass."""
    return ProductOption(
        name=opt.get("name", ""),
        values=opt.get("values", []),
    )


def _parse_product(p: dict) -> Product:
    """Map a Shopify REST product payload into the normalized product model."""
    return Product(
        id=str(p["id"]),
        title=p.get("title", ""),
        handle=p.get("handle", ""),
        product_type=p.get("product_type", ""),
        body_html=p.get("body_html") or "",
        vendor=p.get("vendor", ""),
        tags=[t.strip() for t in p.get("tags", "").split(",") if t.strip()]
        if isinstance(p.get("tags"), str)
        else list(p.get("tags", [])),
        variants=[_parse_variant(v) for v in p.get("variants", [])],
        images=[_parse_image(i) for i in p.get("images", [])],
        options=[_parse_option(o) for o in p.get("options", [])],
    )


def _parse_collection(c: dict) -> Collection:
    """Map a Shopify REST collection payload into the normalized collection model."""
    return Collection(
        id=str(c["id"]),
        title=c.get("title", ""),
        handle=c.get("handle", ""),
        body_html=c.get("body_html") or "",
    )


# ---------------------------------------------------------------------------
# Public REST API fetch helpers (all use async_retry via wrapper)
# ---------------------------------------------------------------------------

@async_retry
async def _get_json(client: httpx.AsyncClient, url: str) -> dict:
    response = await client.get(url)
    response.raise_for_status()
    return response.json()


# Returns (status, text) without raising — callers handle soft 404s directly
async def _get_text(client: httpx.AsyncClient, url: str) -> tuple[int, str]:
    """Return (status_code, text)."""
    response = await client.get(url)
    return response.status_code, response.text


async def _discover_admin_domain(base_url: str, client: httpx.AsyncClient) -> Optional[str]:
    """Best-effort discovery of the canonical myshopify domain from structured public metadata."""
    for url in (f"{base_url}/meta.json",):
        try:
            response = await client.get(url)
        except (httpx.HTTPStatusError, httpx.RequestError):
            continue
        candidates = [response.text]
        for candidate in candidates:
            discovered = _extract_myshopify_domain(candidate)
            if discovered:
                return discovered
    return None


async def resolve_admin_domain(store_url: str, admin_token: str) -> str:
    """Resolve the canonical domain to use for Shopify Admin API calls.

    Merchants often paste a branded storefront URL, while the Admin API expects
    the canonical `.myshopify.com` domain. We try to discover that canonical
    host first and fall back to the supplied host when discovery is not
    possible.
    """
    base_url = _normalize_url(store_url)
    input_domain = _bare_domain(store_url)
    if input_domain.endswith(".myshopify.com"):
        return input_domain

    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
        headers={"User-Agent": "ShopMirror/1.0 (+https://shopmirror.ai)"},
    ) as client:
        discovered = await _discover_admin_domain(base_url, client)

    candidates = [candidate for candidate in [discovered, input_domain] if candidate]
    seen: set[str] = set()
    shop_query = "query ShopIdentity { shop { myshopifyDomain } }"

    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        admin_url = f"https://{candidate}/admin/api/{_ADMIN_API_VERSION}/graphql.json"
        try:
            body = await _run_admin_query(admin_url, admin_token, shop_query)
        except Exception:
            continue
        shop = (body.get("data") or {}).get("shop") or {}
        return (shop.get("myshopifyDomain") or candidate).lower()

    return input_domain


@async_retry
async def _fetch_page(client: httpx.AsyncClient, url: str) -> tuple[dict, str]:
    """Fetch a single products.json page. Returns (json_body, link_header)."""
    response = await client.get(url)
    response.raise_for_status()
    return response.json(), response.headers.get("link", "")


async def _fetch_all_products(base_url: str, client: httpx.AsyncClient) -> list[Product]:
    """Paginate through /products.json using Link header cursor pagination.

    Each page fetch goes through the @async_retry-decorated _fetch_page helper
    so transient 429/503 errors on any page are retried automatically.
    """
    products: list[Product] = []
    url: Optional[str] = f"{base_url}/products.json?limit=250"

    while url:
        data, link_header = await _fetch_page(client, url)
        for p in data.get("products", []):
            products.append(_parse_product(p))

        # Follow Link: <...>; rel="next" header
        url = _parse_next_link(link_header)

    return products


def _parse_next_link(link_header: str) -> Optional[str]:
    """Extract the 'next' URL from a Shopify Link header."""
    if not link_header:
        return None
    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' in part:
            match = re.search(r"<([^>]+)>", part)
            if match:
                return match.group(1)
    return None


async def _fetch_collections(base_url: str, client: httpx.AsyncClient) -> list[Collection]:
    collections: list[Collection] = []
    try:
        data = await _get_json(client, f"{base_url}/collections.json?limit=250")
        for c in data.get("collections", []):
            collections.append(_parse_collection(c))
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.warning("Failed to fetch collections: %s", exc)
    return collections


async def _fetch_policies(base_url: str, client: httpx.AsyncClient) -> Policies:
    policies = Policies()
    title_map = {
        "Refund policy": "refund",
        "Shipping policy": "shipping",
        "Privacy policy": "privacy",
        "Terms of service": "terms_of_service",
    }
    try:
        data = await _get_json(client, f"{base_url}/policies.json")
        for policy in data.get("policies", []):
            field_name = title_map.get(policy.get("title", ""))
            if field_name:
                setattr(policies, field_name, policy.get("body", ""))
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.warning("Failed to fetch policies: %s", exc)
    return policies


async def _fetch_robots_txt(base_url: str, client: httpx.AsyncClient) -> str:
    try:
        status, text = await _get_text(client, f"{base_url}/robots.txt")
        if status == 200:
            return text
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.warning("Failed to fetch robots.txt: %s", exc)
    return ""


async def _fetch_sitemap(base_url: str, client: httpx.AsyncClient) -> tuple[bool, bool]:
    """Returns (sitemap_present, sitemap_has_products)."""
    try:
        status, text = await _get_text(client, f"{base_url}/sitemap.xml")
        if status == 200:
            return True, "/products/" in text
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.warning("Failed to fetch sitemap: %s", exc)
    return False, False


async def _fetch_llms_txt(base_url: str, client: httpx.AsyncClient) -> Optional[str]:
    try:
        status, text = await _get_text(client, f"{base_url}/llms.txt")
        if status == 200:
            return text
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.warning("Failed to fetch llms.txt: %s", exc)
    return None


_PRICE_RE = re.compile(r"[\$£€][\d,]+\.?\d*")


async def _crawl_product_pages(
    base_url: str,
    products: list[Product],
    client: httpx.AsyncClient,
) -> tuple[dict[str, list], dict[str, bool]]:
    """Crawl the top 5 product pages by variant count.

    Returns (schema_by_url, price_in_html).
    """
    schema_by_url: dict[str, list] = {}
    price_in_html: dict[str, bool] = {}

    # Sort by number of variants descending, take top 5
    top5 = sorted(products, key=lambda p: len(p.variants), reverse=True)[:5]

    for product in top5:
        page_url = f"{base_url}/products/{product.handle}"
        try:
            status, html = await _get_text(client, page_url)
            if status != 200:
                continue
            schema_by_url[page_url] = _extract_json_ld(html)
            price_in_html[page_url] = bool(_PRICE_RE.search(html))
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning("Failed to crawl product page %s: %s", page_url, exc)

    return schema_by_url, price_in_html


def _derive_store_name(products: list[Product], homepage_html: str, domain: str) -> str:
    """Derive store name from vendor, <title> tag, or domain fallback."""
    # Try first product's vendor
    if products and products[0].vendor:
        return products[0].vendor

    # Try <title> tag from homepage
    match = re.search(r"<title[^>]*>([^<]+)</title>", homepage_html, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        if title:
            return title

    # Fallback to domain
    return domain


async def _fetch_homepage_html(base_url: str, client: httpx.AsyncClient) -> str:
    try:
        status, html = await _get_text(client, base_url)
        if status == 200:
            return html
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.warning("Failed to fetch homepage: %s", exc)
    return ""


# ---------------------------------------------------------------------------
# Mode A: Public data only
# ---------------------------------------------------------------------------

async def fetch_public_data(store_url: str) -> MerchantData:
    """Fetch all publicly available merchant data without admin credentials.

    Uses Shopify's public JSON APIs (products.json, collections.json, policies.json)
    plus public pages (robots.txt, sitemap.xml, llms.txt, product HTML).
    """
    base_url = _normalize_url(store_url)
    domain = re.sub(r"^https?://", "", base_url)

    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "ShopMirror/1.0 (+https://shopmirror.ai)"},
    ) as client:
        # Fetch products first — needed for store name + crawl targeting
        try:
            products = await _fetch_all_products(base_url, client)
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error("Failed to fetch products from %s: %s", base_url, exc)
            raise

        # Parallel fetch of everything else
        (
            collections,
            policies,
            robots_txt,
            sitemap_result,
            llms_txt,
            homepage_html,
        ) = await asyncio.gather(
            _fetch_collections(base_url, client),
            _fetch_policies(base_url, client),
            _fetch_robots_txt(base_url, client),
            _fetch_sitemap(base_url, client),
            _fetch_llms_txt(base_url, client),
            _fetch_homepage_html(base_url, client),
        )

        sitemap_present, sitemap_has_products = sitemap_result

        schema_by_url, price_in_html = await _crawl_product_pages(base_url, products, client)

    store_name = _derive_store_name(products, homepage_html, domain)

    return MerchantData(
        store_domain=domain,
        store_name=store_name,
        products=products,
        collections=collections,
        policies=policies,
        robots_txt=robots_txt,
        sitemap_present=sitemap_present,
        sitemap_has_products=sitemap_has_products,
        llms_txt=llms_txt,
        schema_by_url=schema_by_url,
        price_in_html=price_in_html,
        ingestion_mode="url_only",
        metafields_by_product={},
        seo_by_product={},
        inventory_by_variant={},
        admin_domain=domain,
        taxonomy_by_product={},
        markets_by_product={},
        metafield_definitions=[],
    )


# ---------------------------------------------------------------------------
# Mode B: Admin GraphQL enrichment
# ---------------------------------------------------------------------------

_ADMIN_API_VERSION = "2024-01"

_QUERY_PRODUCTS_PAGE = """
query ProductsPage($cursor: String) {
  products(first: 50, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        title
        seo { title description }
        productCategory { productTaxonomyNode { id fullName } }
        metafields(first: 20) {
          edges {
            node {
              namespace key value type
            }
          }
        }
        variants(first: 10) {
          edges {
            node {
              id
              inventoryItem {
                id
                tracked
                inventoryLevels(first: 5) {
                  edges {
                    node {
                      quantities(names: ["available"]) { name quantity }
                      location { name }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

_QUERY_TRANSLATABLE_PRODUCTS_PAGE = """
query TranslatablePage($cursor: String) {
  translatableResources(first: 50, resourceType: PRODUCT, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        resourceId
        translatableContent {
          key value digest locale
        }
        translations(locale: "fr") {
          key value outdated
        }
      }
    }
  }
}
"""

_QUERY_METAFIELD_DEFINITIONS = """
{
  metafieldDefinitions(first: 50, ownerType: PRODUCT) {
    edges {
      node {
        id namespace key name type { name category }
        validations { name type value }
      }
    }
  }
}
"""


async def _fetch_admin_products(
    admin_url: str,
    token: str,
) -> tuple[dict[str, list], dict[str, dict], dict[str, str], dict[str, dict]]:
    """Paginate Query A until complete.

    Returns:
        metafields_by_product: product_id -> list of metafield dicts
        seo_by_product:        product_id -> {title, description}
        taxonomy_by_product:   product_id -> taxonomy GID
        inventory_by_variant:  variant_id -> inventory dict
    """
    metafields_by_product: dict[str, list] = {}
    seo_by_product: dict[str, dict] = {}
    taxonomy_by_product: dict[str, str] = {}
    inventory_by_variant: dict[str, dict] = {}

    cursor: Optional[str] = None
    has_next = True

    while has_next:
        variables: dict = {}
        if cursor:
            variables["cursor"] = cursor

        body = await _run_admin_query(admin_url, token, _QUERY_PRODUCTS_PAGE, variables)
        products_conn = body.get("data", {}).get("products", {})
        page_info = products_conn.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")

        for edge in products_conn.get("edges", []):
            node = edge["node"]
            product_gid: str = node["id"]
            pid = _gid_to_id(product_gid)

            # SEO
            seo_by_product[pid] = node.get("seo") or {}

            # Taxonomy
            cat = node.get("productCategory") or {}
            tax_node = (cat.get("productTaxonomyNode") or {})
            if tax_node.get("id"):
                taxonomy_by_product[pid] = tax_node["id"]

            # Metafields
            mf_edges = (node.get("metafields") or {}).get("edges", [])
            metafields_by_product[pid] = [
                {
                    "namespace": mf["node"]["namespace"],
                    "key": mf["node"]["key"],
                    "value": mf["node"]["value"],
                    "type": mf["node"]["type"],
                }
                for mf in mf_edges
            ]

            # Inventory per variant
            variant_edges = (node.get("variants") or {}).get("edges", [])
            for ve in variant_edges:
                vnode = ve["node"]
                vid = _gid_to_id(vnode["id"])
                inv_item = vnode.get("inventoryItem") or {}
                levels = (inv_item.get("inventoryLevels") or {}).get("edges", [])
                level_list = []
                for le in levels:
                    lnode = le["node"]
                    quantities = lnode.get("quantities", [])
                    level_list.append(
                        {
                            "location": (lnode.get("location") or {}).get("name"),
                            "quantities": {
                                q["name"]: q["quantity"] for q in quantities
                            },
                        }
                    )
                inventory_by_variant[vid] = {
                    "tracked": inv_item.get("tracked", False),
                    "inventory_item_id": _gid_to_id(inv_item["id"]) if inv_item.get("id") else None,
                    "levels": level_list,
                }

    return metafields_by_product, seo_by_product, taxonomy_by_product, inventory_by_variant


async def _fetch_admin_translations(
    admin_url: str,
    token: str,
) -> dict[str, dict]:
    """Paginate Query B until complete.

    Returns markets_by_product: product_id -> {"fr": {"title_translated": bool, "desc_translated": bool}}
    """
    markets_by_product: dict[str, dict] = {}

    cursor: Optional[str] = None
    has_next = True

    while has_next:
        variables: dict = {}
        if cursor:
            variables["cursor"] = cursor

        body = await _run_admin_query(
            admin_url, token, _QUERY_TRANSLATABLE_PRODUCTS_PAGE, variables
        )
        resources_conn = body.get("data", {}).get("translatableResources", {})
        page_info = resources_conn.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")

        for edge in resources_conn.get("edges", []):
            node = edge["node"]
            resource_gid: str = node.get("resourceId", "")
            pid = _gid_to_id(resource_gid)

            translations: list[dict] = node.get("translations") or []
            translated_keys = {t["key"] for t in translations if not t.get("outdated")}

            markets_by_product[pid] = {
                "fr": {
                    "title_translated": "title" in translated_keys,
                    "desc_translated": "body_html" in translated_keys
                    or "description" in translated_keys,
                }
            }

    return markets_by_product


async def _fetch_metafield_definitions(
    admin_url: str,
    token: str,
) -> list[dict]:
    """Fetch Query C — store-level MetafieldDefinitions for PRODUCT owner type."""
    body = await _run_admin_query(admin_url, token, _QUERY_METAFIELD_DEFINITIONS)
    defs_conn = body.get("data", {}).get("metafieldDefinitions", {})
    result: list[dict] = []
    for edge in defs_conn.get("edges", []):
        node = edge["node"]
        result.append(
            {
                "id": node.get("id"),
                "namespace": node.get("namespace"),
                "key": node.get("key"),
                "name": node.get("name"),
                "type": node.get("type"),
                "validations": node.get("validations", []),
            }
        )
    return result


async def fetch_admin_data(store_url: str, admin_token: str) -> MerchantData:
    """Fetch full merchant data using both public REST APIs and Admin GraphQL.

    Calls fetch_public_data first, then enriches with Admin API data for
    metafields, SEO, taxonomy, inventory, translations, and metafield definitions.
    """
    admin_domain = await resolve_admin_domain(store_url, admin_token)
    admin_url = f"https://{admin_domain}/admin/api/{_ADMIN_API_VERSION}/graphql.json"

    # Start with public data
    data = await fetch_public_data(store_url)

    # Run all three admin queries in parallel
    (
        (metafields_by_product, seo_by_product, taxonomy_by_product, inventory_by_variant),
        markets_by_product,
        metafield_definitions,
    ) = await asyncio.gather(
        _fetch_admin_products(admin_url, admin_token),
        _fetch_admin_translations(admin_url, admin_token),
        _fetch_metafield_definitions(admin_url, admin_token),
    )

    data.metafields_by_product = metafields_by_product
    data.seo_by_product = seo_by_product
    data.taxonomy_by_product = taxonomy_by_product
    data.inventory_by_variant = inventory_by_variant
    data.admin_domain = admin_domain
    data.markets_by_product = markets_by_product
    data.metafield_definitions = metafield_definitions
    data.ingestion_mode = "admin_token"

    return data


# ---------------------------------------------------------------------------
# Bulk Operations API (>150 products)
# ---------------------------------------------------------------------------

_BULK_INNER_QUERY = """{
      products {
        edges {
          node {
            id title handle productType bodyHtml vendor tags
            variants {
              edges {
                node {
                  id title price sku inventoryManagement inventoryPolicy inventoryQuantity
                  selectedOptions { name value }
                }
              }
            }
            images {
              edges {
                node { id src altText position }
              }
            }
            options { name values }
          }
        }
      }
    }"""

# The inner query is injected at runtime to avoid triple-quote nesting
_BULK_RUN_MUTATION_TEMPLATE = """
mutation BulkProducts($query: String!) {
  bulkOperationRunQuery(query: $query) {
    bulkOperation {
      id status
    }
    userErrors { field message }
  }
}
"""

_BULK_POLL_QUERY = """
{
  currentBulkOperation {
    id status errorCode url objectCount
  }
}
"""


async def _start_bulk_operation(admin_url: str, token: str) -> str:
    """Start a bulk operation and return the operation GID."""
    body = await _run_admin_query(
        admin_url,
        token,
        _BULK_RUN_MUTATION_TEMPLATE,
        variables={"query": _BULK_INNER_QUERY},
    )
    run_result = body.get("data", {}).get("bulkOperationRunQuery", {})
    user_errors = run_result.get("userErrors", [])
    if user_errors:
        raise RuntimeError(f"Bulk operation start errors: {user_errors}")
    op = run_result.get("bulkOperation") or {}
    op_id = op.get("id")
    if not op_id:
        raise RuntimeError("No bulk operation ID returned")
    return op_id


async def _poll_bulk_operation(
    admin_url: str, token: str, poll_interval: float = 3.0, timeout: float = 300.0
) -> str:
    """Poll until the bulk operation completes. Returns the download URL."""
    elapsed = 0.0
    while elapsed < timeout:
        body = await _run_admin_query(admin_url, token, _BULK_POLL_QUERY)
        op = (body.get("data") or {}).get("currentBulkOperation") or {}
        status = op.get("status", "")

        if status == "COMPLETED":
            url = op.get("url")
            if not url:
                raise RuntimeError("Bulk operation completed but no download URL provided")
            return url
        if status in ("FAILED", "CANCELED"):
            raise RuntimeError(
                f"Bulk operation {status}: errorCode={op.get('errorCode')}"
            )
        logger.debug("Bulk operation status=%s objectCount=%s", status, op.get("objectCount"))
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(f"Bulk operation did not complete within {timeout}s")


def _parse_bulk_jsonl(jsonl_text: str) -> list[Product]:
    """Parse Shopify Bulk Operations JSONL into a list of Product objects.

    Bulk JSONL format: each line is one object. Child objects carry a __parentId
    field pointing to the GID of their parent. The structure is flat:
      - Product line: no __parentId (or parent is the implicit query root)
      - Variant/image/option lines: __parentId = product GID
    """
    # First pass: bucket lines by type
    product_rows: dict[str, dict] = {}  # gid -> raw dict
    variant_rows: dict[str, list] = {}  # product_gid -> list of variant dicts
    image_rows: dict[str, list] = {}    # product_gid -> list of image dicts
    option_rows: dict[str, list] = {}   # product_gid -> list of option dicts

    for line in jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("Skipping invalid JSONL line: %s", line[:80])
            continue

        gid: str = obj.get("id", "")
        parent_gid: str = obj.get("__parentId", "")

        if "gid://shopify/Product/" in gid and not parent_gid:
            # Top-level product
            product_rows[gid] = obj
        elif "inventoryManagement" in obj or "inventoryPolicy" in obj:
            # Variant
            variant_rows.setdefault(parent_gid, []).append(obj)
        elif "altText" in obj or ("src" in obj and "position" in obj):
            # Image
            image_rows.setdefault(parent_gid, []).append(obj)
        elif "values" in obj and isinstance(obj.get("values"), list):
            # Option
            option_rows.setdefault(parent_gid, []).append(obj)

    products: list[Product] = []
    for gid, p in product_rows.items():
        pid = _gid_to_id(gid)

        # Parse tags — bulk JSONL returns tags as a list of strings
        raw_tags = p.get("tags", [])
        if isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        else:
            tags = list(raw_tags)

        variants: list[ProductVariant] = []
        for v in variant_rows.get(gid, []):
            opts = v.get("selectedOptions", [])
            option1 = opts[0]["value"] if len(opts) > 0 else None
            option2 = opts[1]["value"] if len(opts) > 1 else None
            option3 = opts[2]["value"] if len(opts) > 2 else None
            variants.append(
                ProductVariant(
                    id=_gid_to_id(v.get("id", "")),
                    title=v.get("title", ""),
                    price=v.get("price", "0.00"),
                    sku=v.get("sku") or "",
                    inventory_management=v.get("inventoryManagement"),
                    inventory_policy=v.get("inventoryPolicy", "deny"),
                    inventory_quantity=v.get("inventoryQuantity") or 0,
                    option1=option1,
                    option2=option2,
                    option3=option3,
                )
            )

        images: list[ProductImage] = []
        for img in image_rows.get(gid, []):
            images.append(
                ProductImage(
                    id=_gid_to_id(img.get("id", "")),
                    src=img.get("src", ""),
                    alt=img.get("altText"),
                    position=img.get("position", 0),
                )
            )

        options: list[ProductOption] = []
        for opt in option_rows.get(gid, []):
            options.append(
                ProductOption(
                    name=opt.get("name", ""),
                    values=opt.get("values", []),
                )
            )

        products.append(
            Product(
                id=pid,
                title=p.get("title", ""),
                handle=p.get("handle", ""),
                product_type=p.get("productType", ""),
                body_html=p.get("bodyHtml") or "",
                vendor=p.get("vendor", ""),
                tags=tags,
                variants=variants,
                images=images,
                options=options,
            )
        )

    return products


async def fetch_bulk_products(store_url: str, admin_token: str) -> list[Product]:
    """Fetch all products for stores with >150 products using Bulk Operations API.

    Step 1: Start bulk operation mutation
    Step 2: Poll currentBulkOperation every 3s (5 min timeout)
    Step 3: Download and parse the JSONL result file
    """
    admin_domain = await resolve_admin_domain(store_url, admin_token)
    admin_url = f"https://{admin_domain}/admin/api/{_ADMIN_API_VERSION}/graphql.json"

    await _start_bulk_operation(admin_url, admin_token)
    download_url = await _poll_bulk_operation(admin_url, admin_token)

    # Download JSONL — presigned URL, no auth header required
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.get(download_url)
        response.raise_for_status()
        jsonl_text = response.text

    return _parse_bulk_jsonl(jsonl_text)
