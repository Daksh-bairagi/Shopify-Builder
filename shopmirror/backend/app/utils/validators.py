import re

import httpx


_DOMAIN_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}$")


async def validate_shopify_url(url: str) -> str:
    """Strip protocol and trailing slashes, return bare domain.

    Raises ValueError if the result does not look like a valid domain.
    """
    cleaned = url.strip()

    for prefix in ("https://", "http://"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break

    # Drop any path, query string, or fragment after the domain
    cleaned = cleaned.split("/")[0].rstrip(".")

    if not _DOMAIN_RE.match(cleaned):
        raise ValueError(f"Not a valid domain: {url!r}")

    return cleaned


async def detect_shopify(domain: str) -> bool:
    """Return True if domain serves a Shopify products.json endpoint.

    Never raises — returns False on any network or parsing error.
    Used for input validation and competitor detection.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"https://{domain}/products.json")
        if response.status_code == 200:
            return "products" in response.json()
        return False
    except Exception:
        return False
