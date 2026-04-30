"""
Reusable factory helpers for constructing MerchantData, Product, and related
objects. Every parameter has a sane default so callers only override what
matters for a particular test.
"""

from __future__ import annotations

from app.models.merchant import (
    Collection,
    MerchantData,
    Policies,
    Product,
    ProductImage,
    ProductOption,
    ProductVariant,
)


# ---------------------------------------------------------------------------
# Low-level builders
# ---------------------------------------------------------------------------

def make_variant(
    id: str = "v1",
    title: str = "Default Title",
    price: str = "29.99",
    sku: str = "SKU-001",
    inventory_management: str | None = "shopify",
    inventory_policy: str = "deny",
    inventory_quantity: int = 10,
    option1: str | None = "Default",
    option2: str | None = None,
    option3: str | None = None,
) -> ProductVariant:
    return ProductVariant(
        id=id,
        title=title,
        price=price,
        sku=sku,
        inventory_management=inventory_management,
        inventory_policy=inventory_policy,
        inventory_quantity=inventory_quantity,
        option1=option1,
        option2=option2,
        option3=option3,
    )


def make_image(
    id: str = "img1",
    src: str = "https://cdn.shopify.com/img1.jpg",
    alt: str | None = "A product image",
    position: int = 1,
) -> ProductImage:
    return ProductImage(id=id, src=src, alt=alt, position=position)


def make_option(name: str = "Size", values: list[str] | None = None) -> ProductOption:
    return ProductOption(name=name, values=values or ["S", "M", "L"])


def make_product(
    id: str = "p1",
    title: str = "Classic Running Shoe",
    handle: str = "classic-running-shoe",
    product_type: str = "Footwear",
    body_html: str = "<p>Premium running shoe built for all-day comfort and performance.</p>",
    vendor: str = "TestBrand",
    tags: list[str] | None = None,
    variants: list[ProductVariant] | None = None,
    images: list[ProductImage] | None = None,
    options: list[ProductOption] | None = None,
) -> Product:
    return Product(
        id=id,
        title=title,
        handle=handle,
        product_type=product_type,
        body_html=body_html,
        vendor=vendor,
        tags=tags if tags is not None else ["running", "shoes"],
        variants=variants if variants is not None else [make_variant()],
        images=images if images is not None else [make_image()],
        options=options if options is not None else [make_option("Size"), make_option("Color", ["Black", "White"])],
    )


def make_policies(
    refund: str = "Returns accepted within 30 days of purchase.",
    shipping: str = "We ship to the United States and Canada.",
    privacy: str = "We respect your privacy.",
    terms_of_service: str = "Standard terms apply.",
) -> Policies:
    return Policies(
        refund=refund,
        shipping=shipping,
        privacy=privacy,
        terms_of_service=terms_of_service,
    )


def make_merchant(
    store_domain: str = "test-store.myshopify.com",
    store_name: str = "Test Store",
    products: list[Product] | None = None,
    collections: list[Collection] | None = None,
    policies: Policies | None = None,
    robots_txt: str = "",
    sitemap_present: bool = True,
    sitemap_has_products: bool = True,
    llms_txt: str | None = "# Test Store\n> An e-commerce store for running gear.",
    schema_by_url: dict | None = None,
    price_in_html: dict | None = None,
    ingestion_mode: str = "url_only",
    metafields_by_product: dict | None = None,
    seo_by_product: dict | None = None,
    inventory_by_variant: dict | None = None,
    admin_domain: str | None = None,
    taxonomy_by_product: dict | None = None,
    markets_by_product: dict | None = None,
    metafield_definitions: list[dict] | None = None,
) -> MerchantData:
    if products is None:
        products = [make_product()]
    return MerchantData(
        store_domain=store_domain,
        store_name=store_name,
        products=products,
        collections=collections or [],
        policies=policies or make_policies(),
        robots_txt=robots_txt,
        sitemap_present=sitemap_present,
        sitemap_has_products=sitemap_has_products,
        llms_txt=llms_txt,
        schema_by_url=schema_by_url or {},
        price_in_html=price_in_html or {},
        ingestion_mode=ingestion_mode,
        metafields_by_product=metafields_by_product or {},
        seo_by_product=seo_by_product or {},
        inventory_by_variant=inventory_by_variant or {},
        admin_domain=admin_domain,
        taxonomy_by_product=taxonomy_by_product or {},
        markets_by_product=markets_by_product or {},
        metafield_definitions=metafield_definitions or [],
    )


# ---------------------------------------------------------------------------
# Preset: a clean admin-mode store that passes all 19 checks
# ---------------------------------------------------------------------------

def clean_store_admin() -> MerchantData:
    """Returns a MerchantData in admin_token mode that passes every check."""
    product = make_product(
        id="p1",
        title="Classic Running Shoe",
        handle="classic-running-shoe",
        vendor="TestBrand",
        options=[make_option("Size"), make_option("Color", ["Black", "White"])],
        variants=[
            make_variant(
                id="v1",
                sku="SKU-001",
                price="59.99",
                inventory_management="shopify",
                inventory_policy="deny",
                inventory_quantity=50,
            )
        ],
        images=[make_image(alt="Classic Running Shoe in black — side profile view")],
    )
    schema = {
        "@type": "Product",
        "name": "Classic Running Shoe",
        "offers": {
            "@type": "Offer",
            "price": "59.99",
            "availability": "https://schema.org/InStock",
            "shippingDetails": {"@type": "OfferShippingDetails"},
            "hasMerchantReturnPolicy": {"@type": "MerchantReturnPolicy"},
        },
    }
    return make_merchant(
        ingestion_mode="admin_token",
        products=[product],
        robots_txt=(
            "User-agent: *\nAllow: /\n"
        ),
        sitemap_present=True,
        sitemap_has_products=True,
        llms_txt="# Test Store\n> Running gear for athletes.",
        policies=make_policies(
            refund="Returns accepted within 30 days of delivery.",
            shipping="We ship to United States, Canada, and United Kingdom.",
        ),
        schema_by_url={
            "https://test-store.myshopify.com/products/classic-running-shoe": [schema]
        },
        taxonomy_by_product={"p1": "gid://shopify/TaxonomyCategory/371"},
        metafield_definitions=[
            {"key": "material", "namespace": "custom"},
            {"key": "care_instructions", "namespace": "custom"},
        ],
        seo_by_product={"p1": {"metaTitle": "Classic Running Shoe — TestBrand"}},
        markets_by_product={},
    )


# ---------------------------------------------------------------------------
# Preset: a broken admin-mode store designed to trigger every possible check
# ---------------------------------------------------------------------------

def broken_store_admin() -> MerchantData:
    """
    Returns a MerchantData in admin_token mode engineered to fail every check.
    Each product is missing something specific so multiple heuristics fire.
    """
    # Product with untracked inventory + continue oversell + missing vendor/SKU
    # + no alt text + placeholder option name
    bad_product = make_product(
        id="bad1",
        title="Vibe X",                         # no category noun
        handle="vibe-x",
        vendor="",                               # missing vendor (C4)
        options=[make_option("Option1", ["yes"]), make_option("Color")],  # placeholder (C3)
        variants=[
            make_variant(
                id="bv1",
                sku="",                          # missing SKU (C4)
                price="0.00",                    # zero price (D1b)
                inventory_management="shopify",
                inventory_policy="continue",     # oversell (A2)
                inventory_quantity=0,
            )
        ],
        images=[
            make_image(id="bi1", alt=None),      # no alt text (C6)
            make_image(id="bi2", alt=""),         # empty alt text (C6)
        ],
    )
    schema_stale = {
        "@type": "Product",
        "offers": {
            "@type": "Offer",
            "price": "999.99",                   # way off from actual price (Con1)
            "availability": "https://schema.org/InStock",  # but product is out of stock (Con2)
        },
    }
    return make_merchant(
        ingestion_mode="admin_token",
        products=[bad_product],
        robots_txt=(
            "User-agent: GPTBot\nDisallow: /\n\n"
            "User-agent: PerplexityBot\nDisallow: /\n"
        ),
        sitemap_present=False,                   # no sitemap (D2)
        sitemap_has_products=False,
        llms_txt=None,                           # no llms.txt (D3)
        policies=make_policies(
            refund="We handle refunds case by case.",  # no timeframe (T1)
            shipping="We ship to many places.",         # no explicit region (T2)
        ),
        schema_by_url={
            "https://test-store.myshopify.com/products/vibe-x": [schema_stale]
        },
        taxonomy_by_product={},                  # no taxonomy (C1, D1b)
        metafield_definitions=[],                # no definitions (C5)
        seo_by_product={"bad1": {"metaTitle": "Amazing Deal ZXQW 2026"}},  # no shared words (Con3)
        markets_by_product={
            "bad1": {
                "market_fr": {"title_translated": False},   # untranslated (D5) — > 20%
                "market_de": {"title_translated": False},
            }
        },
    )
