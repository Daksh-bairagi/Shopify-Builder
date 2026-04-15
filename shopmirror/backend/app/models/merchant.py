from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProductVariant:
    id: str
    title: str
    price: str
    sku: str
    inventory_management: Optional[str]   # 'shopify' | None
    inventory_policy: str                 # 'deny' | 'continue'
    inventory_quantity: int
    option1: Optional[str]
    option2: Optional[str]
    option3: Optional[str]


@dataclass
class ProductImage:
    id: str
    src: str
    alt: Optional[str]
    position: int


@dataclass
class ProductOption:
    name: str
    values: list[str]


@dataclass
class Product:
    id: str
    title: str
    handle: str
    product_type: str
    body_html: str
    vendor: str
    tags: list[str]
    variants: list[ProductVariant]
    images: list[ProductImage]
    options: list[ProductOption]


@dataclass
class Collection:
    id: str
    title: str
    handle: str
    body_html: str


@dataclass
class Policies:
    refund: str = ""
    shipping: str = ""
    privacy: str = ""
    terms_of_service: str = ""


@dataclass
class MerchantData:
    store_domain: str
    store_name: str
    products: list[Product]
    collections: list[Collection]
    policies: Policies
    robots_txt: str
    sitemap_present: bool
    sitemap_has_products: bool
    llms_txt: Optional[str]
    schema_by_url: dict[str, list]        # url -> list of JSON-LD blocks
    price_in_html: dict[str, bool]        # url -> price found in raw HTML
    ingestion_mode: str                   # 'url_only' | 'admin_token'
    metafields_by_product: dict[str, list]  # product_id -> metafield list (Mode B)
    seo_by_product: dict[str, dict]         # product_id -> SEO dict (Mode B)
    inventory_by_variant: dict[str, dict]   # variant_id -> inventory dict (Mode B)
