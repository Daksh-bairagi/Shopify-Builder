"""
seed_dev_store.py - Populate a Shopify dev store with intentionally broken products.

Creates 15 products that fail specific ShopMirror audit checks, allowing the
demo to show a low AI Readiness Score before the agent fixes things.

Usage:
    python shopmirror/scripts/seed_dev_store.py --store your-store.myshopify.com --token <admin_access_token>
    python shopmirror/scripts/seed_dev_store.py --store your-store.myshopify.com --client-id <client_id> --client-secret <client_secret>
    python shopmirror/scripts/seed_dev_store.py

Environment variables:
    SHOPIFY_STORE_DOMAIN
    SHOPIFY_ADMIN_ACCESS_TOKEN
    SHOPIFY_CLIENT_ID
    SHOPIFY_CLIENT_SECRET
    SHOPIFY_LOCATION_ID
    SHOPIFY_ONLINE_STORE_PUBLICATION_ID

The script auto-loads shopmirror/backend/.env if present.

Intentional breakage applied (per TechSpec Section 10):
  C1  - product_type field left empty on all products
  C2  - brand-name-only titles ("The Luna", "Vertex Pro", "Apex", ...)
  C3  - option names/values remain generic on several products
  C4  - no barcode / GTIN on any product
  C5  - no metafields set
  A2  - several variants continue selling when out of stock
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import aiohttp

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:
        return False

# ---------------------------------------------------------------------------
# Product definitions — intentionally broken per TechSpec Section 10
# ---------------------------------------------------------------------------

PRODUCTS = [
    # Sleep accessories (5 products)
    {
        "title": "The Luna",          # C2: no category noun
        "product_type": "",           # C1: empty
        "vendor": "SleepCo",
        "body_html": "<p>Premium comfort for a restful night. Soft and elegant. The Luna is designed for those who value quality sleep.</p>",
        "variants": [
            {"option1": "Standard", "price": "49.99", "inventory_quantity": 10, "inventory_policy": "deny"},
        ],
        "options": [{"name": "Size", "values": ["Standard"]}],
    },
    {
        "title": "Apex",              # C2: no category noun
        "product_type": "",           # C1: empty
        "vendor": "SleepCo",
        "body_html": "<p>Advanced support technology. The Apex is our flagship product engineered for superior performance.</p>",
        "variants": [
            {"option1": "S", "option2": "White", "price": "79.99", "inventory_quantity": 0, "inventory_policy": "continue"},  # A2: oversell
        ],
        "options": [{"name": "Option1", "values": ["S"]}, {"name": "Option2", "values": ["White"]}],  # C3: unnamed options
    },
    {
        "title": "Vertex Pro",        # C2: no category noun
        "product_type": "",           # C1: empty
        "vendor": "",                 # C4: no vendor (GTIN also empty)
        "body_html": "<p>The Vertex Pro combines innovation with comfort. Ideal for the modern lifestyle.</p>",
        "variants": [
            {"option1": "M", "option2": "Gray", "price": "89.99", "inventory_quantity": 5, "inventory_policy": "deny"},
            {"option1": "L", "option2": "Gray", "price": "89.99", "inventory_quantity": 3, "inventory_policy": "deny"},
        ],
        "options": [{"name": "Option1", "values": ["M", "L"]}, {"name": "Option2", "values": ["Gray"]}],  # C3: unnamed
    },
    {
        "title": "Nova Sleep",        # C2: 'Sleep' is there but not standard category noun
        "product_type": "",
        "vendor": "SleepCo",
        "body_html": "<p>Nova Sleep provides an unparalleled rest experience. Premium materials and expert craftsmanship.</p>",
        "variants": [
            {"option1": "One Size", "price": "59.99", "inventory_quantity": 8, "inventory_policy": "deny"},
        ],
        "options": [{"name": "Size", "values": ["One Size"]}],
    },
    {
        "title": "Solace",            # C2: no category noun
        "product_type": "",
        "vendor": "SleepCo",
        "body_html": "<p>Find your peace with Solace. Crafted for the discerning customer who values tranquility and comfort.</p>",
        "variants": [
            {"option1": "Standard", "price": "39.99", "inventory_quantity": 0, "inventory_policy": "continue"},  # A2: oversell
        ],
        "options": [{"name": "Option1", "values": ["Standard"]}],  # C3: unnamed
    },
    # Bags (5 products)
    {
        "title": "The Nomad",         # C2: no category noun
        "product_type": "",
        "vendor": "",                 # C4: no vendor
        "body_html": "<p>The Nomad is your perfect travel companion. Durable, stylish, and spacious.</p>",
        "variants": [
            {"option1": "Black", "price": "129.00", "inventory_quantity": 15, "inventory_policy": "deny"},
            {"option1": "Brown", "price": "129.00", "inventory_quantity": 7, "inventory_policy": "deny"},
        ],
        "options": [{"name": "Color", "values": ["Black", "Brown"]}],
    },
    {
        "title": "Pinnacle",          # C2: no category noun
        "product_type": "",
        "vendor": "BagCo",
        "body_html": "<p>The Pinnacle redefines what a bag can be. Premium craftsmanship meets modern design.</p>",
        "variants": [
            {"option1": "Navy", "option2": "Small", "price": "159.00", "inventory_quantity": 4, "inventory_policy": "deny"},
            {"option1": "Navy", "option2": "Large", "price": "189.00", "inventory_quantity": 2, "inventory_policy": "deny"},
        ],
        "options": [{"name": "Option1", "values": ["Navy"]}, {"name": "Option2", "values": ["Small", "Large"]}],  # C3: unnamed
    },
    {
        "title": "Drift",             # C2: no category noun
        "product_type": "",
        "vendor": "",                 # C4: no vendor
        "body_html": "<p>Go with the flow with Drift. Lightweight and functional for everyday adventures.</p>",
        "variants": [
            {"option1": "Tan", "price": "99.00", "inventory_quantity": 20, "inventory_policy": "deny"},
        ],
        "options": [{"name": "Color", "values": ["Tan"]}],
    },
    {
        "title": "Atlas Pro",         # C2: no category noun
        "product_type": "",
        "vendor": "BagCo",
        "body_html": "<p>Atlas Pro is built for explorers. Reinforced structure and multiple compartments for any journey.</p>",
        "variants": [
            {"option1": "M", "option2": "Olive", "price": "219.00", "inventory_quantity": 6, "inventory_policy": "deny"},
            {"option1": "L", "option2": "Olive", "price": "239.00", "inventory_quantity": 0, "inventory_policy": "continue"},  # A2: oversell
        ],
        "options": [{"name": "Option1", "values": ["M", "L"]}, {"name": "Option2", "values": ["Olive"]}],  # C3: unnamed
    },
    {
        "title": "Meridian",          # C2: no category noun
        "product_type": "",
        "vendor": "BagCo",
        "body_html": "<p>The Meridian crosses every boundary. Versatile design for work, travel, and everything in between.</p>",
        "variants": [
            {"option1": "Charcoal", "price": "175.00", "inventory_quantity": 9, "inventory_policy": "deny"},
        ],
        "options": [{"name": "Color", "values": ["Charcoal"]}],
    },
    # Home goods (5 products)
    {
        "title": "Aura",              # C2: no category noun
        "product_type": "",
        "vendor": "",                 # C4: no vendor
        "body_html": "<p>Transform your space with Aura. Elegant and minimal design that complements any interior.</p>",
        "variants": [
            {"option1": "White", "price": "34.99", "inventory_quantity": 25, "inventory_policy": "deny"},
            {"option1": "Sand", "price": "34.99", "inventory_quantity": 12, "inventory_policy": "deny"},
        ],
        "options": [{"name": "Color", "values": ["White", "Sand"]}],
    },
    {
        "title": "Zen Collection",    # C2: no category noun
        "product_type": "",
        "vendor": "HomeCo",
        "body_html": "<p>The Zen Collection brings calm to your environment. Thoughtfully designed for modern living.</p>",
        "variants": [
            {"option1": "Set of 2", "price": "64.99", "inventory_quantity": 18, "inventory_policy": "deny"},
        ],
        "options": [{"name": "Option1", "values": ["Set of 2"]}],  # C3: unnamed
    },
    {
        "title": "Ember",             # C2: no category noun
        "product_type": "",
        "vendor": "HomeCo",
        "body_html": "<p>Ember adds warmth to any room. Hand-finished with attention to every detail.</p>",
        "variants": [
            {"option1": "Terracotta", "option2": "Small", "price": "28.00", "inventory_quantity": 30, "inventory_policy": "deny"},
            {"option1": "Terracotta", "option2": "Large", "price": "44.00", "inventory_quantity": 14, "inventory_policy": "deny"},
        ],
        "options": [{"name": "Option1", "values": ["Terracotta"]}, {"name": "Option2", "values": ["Small", "Large"]}],  # C3: unnamed
    },
    {
        "title": "Lumen",             # C2: no category noun
        "product_type": "",
        "vendor": "",                 # C4: no vendor
        "body_html": "<p>Illuminate your world with Lumen. A perfect balance of form and function.</p>",
        "variants": [
            {"option1": "Brass", "price": "89.00", "inventory_quantity": 7, "inventory_policy": "deny"},
            {"option1": "Matte Black", "price": "89.00", "inventory_quantity": 3, "inventory_policy": "deny"},
        ],
        "options": [{"name": "Finish", "values": ["Brass", "Matte Black"]}],
    },
    {
        "title": "Hearth",            # C2: no category noun
        "product_type": "",
        "vendor": "HomeCo",
        "body_html": "<p>Hearth is where comfort begins. Designed to be the centerpiece of your living space.</p>",
        "variants": [
            {"option1": "Natural", "price": "119.00", "inventory_quantity": 5, "inventory_policy": "deny"},
        ],
        "options": [{"name": "Option1", "values": ["Natural"]}],  # C3: unnamed
    },
]


# ---------------------------------------------------------------------------
# GraphQL mutations
# ---------------------------------------------------------------------------

_ADMIN_API_VERSION = "2025-10"
_DEFAULT_ENV_FILE = Path(__file__).resolve().parents[1] / "backend" / ".env"

QUERY_PRIMARY_LOCATION = """
query PrimaryLocation {
  location {
    id
  }
}
"""

QUERY_PUBLICATIONS = """
query Publications {
  publications(first: 50) {
    nodes {
      id
      name
    }
  }
}
"""

MUTATION_PRODUCT_SET = """
mutation SeedProduct($input: ProductSetInput!, $synchronous: Boolean!) {
  productSet(input: $input, synchronous: $synchronous) {
    product {
      id
      title
      status
      variants(first: 25) {
        nodes {
          id
          title
          selectedOptions {
            name
            value
          }
          inventoryItem {
            id
            tracked
          }
        }
      }
    }
    userErrors {
      code
      field
      message
    }
  }
}
"""

MUTATION_PUBLISH_PRODUCT = """
mutation PublishProduct($id: ID!, $publicationId: ID!) {
  publishablePublish(id: $id, input: [{publicationId: $publicationId}]) {
    publishable {
      publishedOnPublication(publicationId: $publicationId)
    }
    userErrors {
      field
      message
    }
  }
}
"""

MUTATION_INVENTORY_SET = """
mutation InventorySet($input: InventorySetQuantitiesInput!) {
  inventorySetQuantities(input: $input) {
    userErrors {
      field
      message
    }
  }
}
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _load_env_files(extra_env_file: str | None) -> None:
    load_dotenv(_DEFAULT_ENV_FILE, override=False)
    load_dotenv(Path.cwd() / ".env", override=False)
    if extra_env_file:
        load_dotenv(extra_env_file, override=False)


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _normalize_store_domain(value: str | None) -> str:
    if not value:
        return ""
    domain = value.strip()
    domain = domain.removeprefix("https://").removeprefix("http://")
    domain = domain.split("/", 1)[0]
    return domain


def _format_error_blob(blob: Any) -> str:
    if isinstance(blob, list):
        parts: list[str] = []
        for item in blob:
            if isinstance(item, dict):
                message = item.get("message") or json.dumps(item, ensure_ascii=True)
                field = item.get("field")
                if field:
                    message = f"{message} (field: {field})"
                parts.append(message)
            else:
                parts.append(str(item))
        return "; ".join(parts)
    if isinstance(blob, dict):
        return blob.get("message") or json.dumps(blob, ensure_ascii=True)
    return str(blob)


def _scope_set(scope_text: str | None) -> set[str]:
    if not scope_text:
        return set()
    return {part.strip() for part in scope_text.split(",") if part.strip()}


def _variant_key_from_definition(product_def: dict[str, Any], variant_def: dict[str, Any]) -> tuple[str, ...]:
    return tuple(variant_def.get(f"option{i}", "") for i in range(1, len(product_def["options"]) + 1))


def _variant_key_from_node(product_def: dict[str, Any], node: dict[str, Any]) -> tuple[str, ...]:
    selected = {opt["name"]: opt["value"] for opt in node.get("selectedOptions", [])}
    return tuple(selected.get(option["name"], "") for option in product_def["options"])


def _looks_like_online_store(publication_name: str | None) -> bool:
    if not publication_name:
        return False
    return "online store" in publication_name.strip().lower()


async def _decode_response(response: aiohttp.ClientResponse) -> tuple[Any, str]:
    text = await response.text()
    try:
        return json.loads(text), text
    except json.JSONDecodeError:
        return None, text


async def _admin_graphql(
    session: aiohttp.ClientSession,
    store_domain: str,
    token: str,
    query: str,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"https://{store_domain}/admin/api/{_ADMIN_API_VERSION}/graphql.json"
    payload: dict[str, Any] = {"query": query}
    if variables is not None:
        payload["variables"] = variables

    async with session.post(
        url,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": token,
        },
    ) as response:
        body, text = await _decode_response(response)

    if response.status >= 400:
        detail = _format_error_blob(body) if body is not None else text
        raise RuntimeError(f"Shopify Admin API HTTP {response.status}: {detail}")

    if not isinstance(body, dict):
        raise RuntimeError(f"Shopify Admin API returned non-JSON content: {text}")

    if body.get("errors"):
        raise RuntimeError(_format_error_blob(body["errors"]))

    return body


async def _exchange_admin_access_token(
    session: aiohttp.ClientSession,
    store_domain: str,
    client_id: str,
    client_secret: str,
) -> tuple[str, str | None, int | None]:
    url = f"https://{store_domain}/admin/oauth/access_token"
    async with session.post(
        url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ) as response:
        body, text = await _decode_response(response)

    if response.status >= 400:
        detail = _format_error_blob(body) if body is not None else text
        raise RuntimeError(f"Client-credentials token exchange failed (HTTP {response.status}): {detail}")

    if not isinstance(body, dict) or not body.get("access_token"):
        raise RuntimeError(f"Client-credentials token exchange did not return an access_token: {text}")

    return body["access_token"], body.get("scope"), body.get("expires_in")


async def _fetch_primary_location_id(
    session: aiohttp.ClientSession,
    store_domain: str,
    token: str,
) -> str | None:
    body = await _admin_graphql(session, store_domain, token, QUERY_PRIMARY_LOCATION)
    return ((body.get("data") or {}).get("location") or {}).get("id")


async def _fetch_online_store_publication_id(
    session: aiohttp.ClientSession,
    store_domain: str,
    token: str,
) -> str | None:
    body = await _admin_graphql(session, store_domain, token, QUERY_PUBLICATIONS)
    publications = ((body.get("data") or {}).get("publications") or {}).get("nodes") or []
    for publication in publications:
        if _looks_like_online_store(publication.get("name")):
            return publication["id"]
    return None


def _build_product_set_input(product_def: dict[str, Any]) -> dict[str, Any]:
    product_input: dict[str, Any] = {
        "title": product_def["title"],
        "descriptionHtml": product_def["body_html"],
        "status": "ACTIVE",
        "productOptions": [
            {
                "name": option["name"],
                "position": index,
                "values": [{"name": value} for value in option["values"]],
            }
            for index, option in enumerate(product_def["options"], start=1)
        ],
        "variants": [],
    }

    if product_def["product_type"]:
        product_input["productType"] = product_def["product_type"]
    if product_def["vendor"]:
        product_input["vendor"] = product_def["vendor"]

    for position, variant in enumerate(product_def["variants"], start=1):
        option_values = []
        for option_index, option in enumerate(product_def["options"], start=1):
            option_key = f"option{option_index}"
            option_value = variant.get(option_key)
            if option_value is None:
                raise RuntimeError(
                    f"Variant definition for {product_def['title']} is missing {option_key} for option {option['name']}"
                )
            option_values.append({"optionName": option["name"], "name": option_value})

        product_input["variants"].append(
            {
                "position": position,
                "price": float(variant["price"]),
                "inventoryPolicy": variant["inventory_policy"].upper(),
                "inventoryItem": {"tracked": True},
                "optionValues": option_values,
            }
        )

    return product_input


async def _create_product(
    session: aiohttp.ClientSession,
    store_domain: str,
    token: str,
    product_def: dict[str, Any],
) -> dict[str, Any]:
    body = await _admin_graphql(
        session,
        store_domain,
        token,
        MUTATION_PRODUCT_SET,
        {"input": _build_product_set_input(product_def), "synchronous": True},
    )
    payload = (body.get("data") or {}).get("productSet") or {}
    errors = payload.get("userErrors") or []
    if errors:
        raise RuntimeError(_format_error_blob(errors))
    product = payload.get("product")
    if not product:
        raise RuntimeError("Shopify did not return the created product payload.")
    return product


async def _set_inventory_quantity(
    session: aiohttp.ClientSession,
    store_domain: str,
    token: str,
    inventory_item_id: str,
    location_id: str,
    quantity: int,
    reference_key: str,
) -> None:
    body = await _admin_graphql(
        session,
        store_domain,
        token,
        MUTATION_INVENTORY_SET,
        {
            "input": {
                "name": "available",
                "reason": "correction",
                "ignoreCompareQuantity": True,
                "referenceDocumentUri": f"shopmirror://seed/{reference_key}",
                "quantities": [
                    {
                        "inventoryItemId": inventory_item_id,
                        "locationId": location_id,
                        "quantity": quantity,
                    }
                ],
            }
        },
    )
    errors = ((body.get("data") or {}).get("inventorySetQuantities") or {}).get("userErrors") or []
    if errors:
        raise RuntimeError(_format_error_blob(errors))


async def _apply_inventory_quantities(
    session: aiohttp.ClientSession,
    store_domain: str,
    token: str,
    product_def: dict[str, Any],
    product_node: dict[str, Any],
    location_id: str,
) -> None:
    variants = ((product_node.get("variants") or {}).get("nodes")) or []
    variant_by_key = {
        _variant_key_from_node(product_def, node): node
        for node in variants
    }

    for variant_def in product_def["variants"]:
        variant_key = _variant_key_from_definition(product_def, variant_def)
        product_variant = variant_by_key.get(variant_key)
        if not product_variant:
            raise RuntimeError(f"Could not match created variant for {product_def['title']} and options {variant_key}")

        inventory_item_id = ((product_variant.get("inventoryItem") or {}).get("id"))
        if not inventory_item_id:
            raise RuntimeError(f"Created variant for {product_def['title']} has no inventory item ID")

        await _set_inventory_quantity(
            session,
            store_domain,
            token,
            inventory_item_id,
            location_id,
            int(variant_def["inventory_quantity"]),
            reference_key=product_def["title"].lower().replace(" ", "-"),
        )


async def _publish_product(
    session: aiohttp.ClientSession,
    store_domain: str,
    token: str,
    product_id: str,
    publication_id: str,
) -> None:
    body = await _admin_graphql(
        session,
        store_domain,
        token,
        MUTATION_PUBLISH_PRODUCT,
        {"id": product_id, "publicationId": publication_id},
    )
    errors = ((body.get("data") or {}).get("publishablePublish") or {}).get("userErrors") or []
    if errors:
        raise RuntimeError(_format_error_blob(errors))


async def create_products(
    store_domain: str,
    token: str,
    location_id: str | None = None,
    publication_id: str | None = None,
    known_scopes: set[str] | None = None,
) -> None:
    timeout = aiohttp.ClientTimeout(total=60)
    warnings: list[str] = []
    known_scopes = known_scopes or set()

    inventory_allowed = not known_scopes or "write_inventory" in known_scopes
    publication_lookup_allowed = not known_scopes or "read_publications" in known_scopes
    publication_write_allowed = not known_scopes or "write_publications" in known_scopes
    location_lookup_allowed = not known_scopes or bool({"read_inventory", "read_locations"} & known_scopes)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        resolved_location_id = location_id
        if not resolved_location_id and inventory_allowed and location_lookup_allowed:
            try:
                resolved_location_id = await _fetch_primary_location_id(session, store_domain, token)
            except Exception as exc:
                warnings.append(
                    "Inventory quantities were skipped because the primary location could not be resolved. "
                    f"Reason: {exc}"
                )
        elif not resolved_location_id and not inventory_allowed:
            warnings.append(
                "Inventory quantities were skipped because this token does not appear to include write_inventory."
            )
        elif resolved_location_id and not inventory_allowed:
            warnings.append(
                "A location ID was provided, but inventory quantities will still be skipped because this token does not appear to include write_inventory."
            )

        resolved_publication_id = publication_id
        if not resolved_publication_id and publication_lookup_allowed:
            try:
                resolved_publication_id = await _fetch_online_store_publication_id(session, store_domain, token)
            except Exception as exc:
                warnings.append(
                    "Online Store publication auto-discovery failed, so products may need manual publishing. "
                    f"Reason: {exc}"
                )
        elif not resolved_publication_id and known_scopes and "read_publications" not in known_scopes:
            warnings.append(
                "Online Store publication auto-discovery was skipped because this token does not appear to include read_publications."
            )
        elif resolved_publication_id and not publication_write_allowed:
            warnings.append(
                "An Online Store publication ID was provided, but products will not be published because this token does not appear to include write_publications."
            )
        elif not resolved_publication_id and known_scopes and "write_publications" not in known_scopes:
            warnings.append(
                "Products will be created but not auto-published because this token does not appear to include write_publications."
            )

        created = 0
        failed = 0
        published = 0
        inventory_enabled = bool(resolved_location_id and inventory_allowed)
        publish_enabled = bool(resolved_publication_id and publication_write_allowed)

        for product_def in PRODUCTS:
            try:
                product = await _create_product(session, store_domain, token, product_def)
                product_id = product["id"]

                if inventory_enabled and resolved_location_id:
                    try:
                        await _apply_inventory_quantities(
                            session,
                            store_domain,
                            token,
                            product_def,
                            product,
                            resolved_location_id,
                        )
                    except Exception as exc:
                        inventory_enabled = False
                        warnings.append(
                            "Inventory quantities stopped after the first inventory write failure. "
                            f"Reason: {exc}"
                        )

                publish_note = ""
                if publish_enabled and resolved_publication_id:
                    try:
                        await _publish_product(session, store_domain, token, product_id, resolved_publication_id)
                        published += 1
                        publish_note = " + published"
                    except Exception as exc:
                        publish_enabled = False
                        warnings.append(
                            "Online Store publishing stopped after the first publish failure. "
                            f"Reason: {exc}"
                        )
                        publish_note = " + not published"
                elif resolved_publication_id:
                    publish_note = " + not published"

                print(f"  OK   {product_def['title']} ({product_id}){publish_note}")
                created += 1
            except Exception as exc:
                print(f"  ERR  {product_def['title']}: {exc}")
                failed += 1

    print(f"\nDone - {created} created, {failed} failed, {published} published")

    if warnings:
        print("\nWarnings:")
        seen: set[str] = set()
        for warning in warnings:
            if warning in seen:
                continue
            seen.add(warning)
            print(f"  - {warning}")

    print("\nNext steps for full breakage:")
    print("  1. Add 'User-agent: PerplexityBot\\nDisallow: /' to robots.txt.liquid in theme editor")
    print("  2. Set return policy to: 'We accept returns within a few weeks'")
    print("  3. Inject wrong price in theme JSON-LD snippet (manually)")
    print("\nShopMirror should now find: C1, C2, C3, C4, C5, A2, D1a (if you did step 1)")


async def _run() -> None:
    parser = argparse.ArgumentParser(description="Seed a Shopify dev store with intentionally broken products")
    parser.add_argument("--store", help="Store domain, e.g. my-store.myshopify.com")
    parser.add_argument(
        "--token",
        help="Admin API access token. This can be a legacy shpat_* token or a short-lived access token minted from client credentials.",
    )
    parser.add_argument("--client-id", help="Shopify app client ID for the client-credentials flow")
    parser.add_argument("--client-secret", help="Shopify app client secret (typically starts with shpss_)")
    parser.add_argument("--location-id", help="Optional Shopify location GID to use for inventory quantities")
    parser.add_argument(
        "--publication-id",
        help="Optional Online Store publication GID to use for publishing created products",
    )
    parser.add_argument(
        "--env-file",
        help="Optional dotenv file to load in addition to shopmirror/backend/.env and the current working directory .env",
    )
    args = parser.parse_args()

    _load_env_files(args.env_file)

    store_domain = _normalize_store_domain(args.store or _env_first("SHOPIFY_STORE_DOMAIN", "SHOPIFY_STORE"))
    token = args.token or _env_first("SHOPIFY_ADMIN_ACCESS_TOKEN", "SHOPIFY_ADMIN_TOKEN", "SHOPIFY_ACCESS_TOKEN")
    client_id = args.client_id or _env_first("SHOPIFY_CLIENT_ID")
    client_secret = args.client_secret or _env_first("SHOPIFY_CLIENT_SECRET")
    location_id = args.location_id or _env_first("SHOPIFY_LOCATION_ID")
    publication_id = args.publication_id or _env_first("SHOPIFY_ONLINE_STORE_PUBLICATION_ID")

    if token and token.startswith("shpss_") and not client_secret:
        client_secret = token
        token = None

    if not store_domain:
        print("ERROR: Missing Shopify store domain. Pass --store or set SHOPIFY_STORE_DOMAIN.")
        sys.exit(1)

    if client_secret and client_secret.startswith("shpss_") and not client_id and not token:
        print("ERROR: A Shopify client secret was found, but the matching client ID is missing.")
        print("Add SHOPIFY_CLIENT_ID or pass --client-id so the script can mint an Admin API token.")
        sys.exit(1)

    if not token and not (client_id and client_secret):
        print("ERROR: Missing Shopify credentials.")
        print("Pass either --token <admin_access_token> or --client-id + --client-secret.")
        print("You can also set SHOPIFY_ADMIN_ACCESS_TOKEN or SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET in shopmirror/backend/.env.")
        sys.exit(1)

    known_scopes: set[str] = set()
    if token:
        print(f"Seeding {store_domain} with {len(PRODUCTS)} intentionally broken products...\n")
        await create_products(
            store_domain,
            token,
            location_id=location_id,
            publication_id=publication_id,
            known_scopes=known_scopes,
        )
        return

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        access_token, scope_text, expires_in = await _exchange_admin_access_token(
            session,
            store_domain,
            client_id=client_id or "",
            client_secret=client_secret or "",
        )

    known_scopes = _scope_set(scope_text)
    if "write_products" not in known_scopes:
        print("ERROR: The minted access token does not include write_products, so product creation will fail.")
        print(f"Scopes returned by Shopify: {scope_text or '(none)'}")
        sys.exit(1)

    if expires_in:
        print(
            f"Minted a Shopify Admin API token via client credentials for {store_domain} "
            f"(expires in about {int(expires_in) // 3600}h)."
        )
    else:
        print(f"Minted a Shopify Admin API token via client credentials for {store_domain}.")
    if scope_text:
        print(f"Scopes: {scope_text}")
    print(f"\nSeeding {store_domain} with {len(PRODUCTS)} intentionally broken products...\n")

    await create_products(
        store_domain,
        access_token,
        location_id=location_id,
        publication_id=publication_id,
        known_scopes=known_scopes,
    )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
