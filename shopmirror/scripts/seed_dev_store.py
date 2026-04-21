"""
seed_dev_store.py — Populate a Shopify dev store with intentionally broken products.

Creates 15 products that fail specific ShopMirror audit checks, allowing the
demo to show a low AI Readiness Score before the agent fixes things.

Usage:
    cd shopmirror/scripts
    pip install gql aiohttp python-dotenv
    python seed_dev_store.py --store your-store.myshopify.com --token shpat_xxx

Intentional breakage applied (per TechSpec Section 10):
  C1  — product_type field left empty on all products
  C2  — brand-name-only titles ('The Luna', 'Vertex', 'Apex Pro', ...)
  C3  — variant option names left as 'Size', 'Color' but values generic
  C4  — no barcode / GTIN on any product
  C5  — no metafields set
  A2  — 3 products set to continue selling when out of stock
"""

from __future__ import annotations

import argparse
import asyncio
import sys

try:
    from gql import gql, Client
    from gql.transport.aiohttp import AIOHTTPTransport
except ImportError:
    print("ERROR: gql not installed. Run: pip install gql aiohttp")
    sys.exit(1)

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

PRODUCT_CREATE = gql("""
mutation productCreate($input: ProductInput!) {
  productCreate(input: $input) {
    product {
      id
      title
    }
    userErrors {
      field
      message
    }
  }
}
""")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def create_products(store_domain: str, token: str) -> None:
    url = f"https://{store_domain}/admin/api/2024-01/graphql.json"
    transport = AIOHTTPTransport(
        url=url,
        headers={"X-Shopify-Access-Token": token},
    )

    async with Client(transport=transport, fetch_schema_from_transport=False) as session:
        created = 0
        failed = 0

        for product_def in PRODUCTS:
            variants_input = []
            for v in product_def["variants"]:
                vi: dict = {
                    "price": v["price"],
                    "inventoryManagement": "SHOPIFY",
                    "inventoryPolicy": v["inventory_policy"].upper(),
                    "inventoryQuantities": [{"availableQuantity": v["inventory_quantity"], "locationId": None}],
                }
                if "option1" in v:
                    vi["option1"] = v["option1"]
                if "option2" in v:
                    vi["option2"] = v["option2"]
                variants_input.append(vi)

            # Remove locationId None entries — will rely on default location
            for vi in variants_input:
                vi.pop("inventoryQuantities", None)

            product_input: dict = {
                "title": product_def["title"],
                "productType": product_def["product_type"],
                "vendor": product_def["vendor"],
                "bodyHtml": product_def["body_html"],
                "options": [o["name"] for o in product_def["options"]],
                "variants": variants_input,
                "published": True,
            }

            try:
                result = await session.execute(PRODUCT_CREATE, variable_values={"input": product_input})
                errors = result["productCreate"]["userErrors"]
                if errors:
                    print(f"  WARN {product_def['title']}: {errors[0]['message']}")
                    failed += 1
                else:
                    pid = result["productCreate"]["product"]["id"]
                    print(f"  OK   {product_def['title']} ({pid})")
                    created += 1
            except Exception as exc:
                print(f"  ERR  {product_def['title']}: {exc}")
                failed += 1

        print(f"\nDone — {created} created, {failed} failed")
        print("\nNext steps for full breakage:")
        print("  1. Add 'User-agent: PerplexityBot\\nDisallow: /' to robots.txt.liquid in theme editor")
        print("  2. Set return policy to: 'We accept returns within a few weeks'")
        print("  3. Inject wrong price in theme JSON-LD snippet (manually)")
        print("\nShopMirror should now find: C1, C2, C3, C4, C5, A2, D1a (if you did step 1)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Shopify dev store with intentionally broken products")
    parser.add_argument("--store", required=True, help="Store domain, e.g. my-store.myshopify.com")
    parser.add_argument("--token", required=True, help="Admin API access token (shpat_xxx)")
    args = parser.parse_args()

    print(f"Seeding {args.store} with {len(PRODUCTS)} intentionally broken products...\n")
    asyncio.run(create_products(args.store, args.token))


if __name__ == "__main__":
    main()
