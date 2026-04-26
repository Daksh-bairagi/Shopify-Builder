"""
agent/tools.py — Executor tool functions for the fix agent.

Each tool is a plain async function that takes the state and the FixItem
to execute. Returns an updated FixResult. LLM calls use Gemini API key +
with_structured_output, same pattern as other services.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.fixes import FixItem, FixResult
from app.models.merchant import MerchantData
from app.services import shopify_writer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy LLM factory
# ---------------------------------------------------------------------------

_llm_cache: dict = {}


def _get_llm(schema_class):
    key = schema_class.__name__
    if key not in _llm_cache:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model=os.environ.get("VERTEX_MODEL", "gemini-2.5-flash"),
            temperature=0,
            google_api_key=os.environ.get("GEMINI_API_KEY"),
        )
        _llm_cache[key] = llm.with_structured_output(schema_class)
    return _llm_cache[key]


# ---------------------------------------------------------------------------
# Pydantic schemas for LLM responses (Section 7 prompts)
# ---------------------------------------------------------------------------

class TitleImprovement(BaseModel):
    improved_title: str = Field(description="Improved product title, max 70 chars, contains category noun")
    category_noun: str = Field(description="The category noun added or present")
    reasoning: str = Field(description="Why this title better serves AI discoverability")


class TaxonomyClassification(BaseModel):
    taxonomy_path: str = Field(description="Full Shopify Standard Taxonomy path, e.g. 'Apparel & Accessories > Clothing > Tops'")
    taxonomy_gid: str = Field(description="Shopify Standard Taxonomy GID, format: gid://shopify/TaxonomyCategory/...")
    confidence: str = Field(description="high | medium | low")
    reasoning: str


class ProductTypeClassification(BaseModel):
    product_type: str = Field(description="Specific product type, e.g. 'Hiking Backpack', 'Sleep Mask'")
    confidence: str = Field(description="high | medium | low")
    reasoning: str


class MetafieldExtraction(BaseModel):
    material: Optional[str] = Field(default=None, description="Material if explicitly stated in text")
    care_instructions: Optional[str] = Field(default=None, description="Care instructions if present")
    specifications: Optional[str] = Field(default=None, description="Key specifications if present")
    weight: Optional[str] = Field(default=None, description="Weight with unit if present")


class AltTextGeneration(BaseModel):
    alt_text: str = Field(description="Descriptive alt text for the product image, max 125 chars")


# ---------------------------------------------------------------------------
# Helper: find FixItem by fix_id
# ---------------------------------------------------------------------------

def _find_fix(fix_plan: list[FixItem], fix_id: str) -> Optional[FixItem]:
    return next((f for f in fix_plan if f.fix_id == fix_id), None)


def _find_product(store_data: MerchantData, product_id: str):
    return next((p for p in store_data.products if p.id == product_id), None)


def _ok(fix_id: str, gid: str) -> FixResult:
    return FixResult(
        fix_id=fix_id,
        success=True,
        error=None,
        shopify_gid=gid,
        script_tag_id=None,
        applied_at=datetime.utcnow(),
    )


def _fail(fix_id: str, error: str) -> FixResult:
    return FixResult(
        fix_id=fix_id,
        success=False,
        error=error,
        shopify_gid=None,
        script_tag_id=None,
        applied_at=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# Tool: improve_title
# ---------------------------------------------------------------------------

async def improve_title(
    fix_item: FixItem,
    store_data: MerchantData,
    admin_token: str,
    job_id: str,
    merchant_intent: str | None = None,
) -> FixResult:
    product = _find_product(store_data, fix_item.product_id)
    if product is None:
        return _fail(fix_item.fix_id, f"Product {fix_item.product_id} not found in store data")

    try:
        description_words = re.sub(r"<[^>]+>", "", product.body_html).split()[:30]
        description_start = " ".join(description_words)
        brand_voice = merchant_intent or "Not provided"

        llm = _get_llm(TitleImprovement)
        result: TitleImprovement = await llm.ainvoke(
            f"Original title: {product.title}\n"
            f"product_type: {product.product_type}\n"
            f"Key attributes found in description: {description_start}\n"
            f"Merchant brand voice: {brand_voice}\n"
            "Rules: contain the category noun, preserve brand, max 70 chars, do not add claims not in data.\n"
            "Return improved title."
        )

        product_gid = f"gid://shopify/Product/{product.id}"
        gid = await shopify_writer.write_title(
            store_data.store_domain,
            admin_token,
            product_gid,
            result.improved_title,
            product.title,
            job_id,
            fix_item.fix_id,
        )
        return _ok(fix_item.fix_id, gid)
    except Exception as exc:
        logger.error("improve_title failed for %s: %s", fix_item.product_id, exc)
        return _fail(fix_item.fix_id, str(exc))


# ---------------------------------------------------------------------------
# Tool: map_taxonomy
# ---------------------------------------------------------------------------

async def map_taxonomy(
    fix_item: FixItem,
    store_data: MerchantData,
    admin_token: str,
    job_id: str,
) -> FixResult:
    product = _find_product(store_data, fix_item.product_id)
    if product is None:
        return _fail(fix_item.fix_id, f"Product {fix_item.product_id} not found")

    try:
        description_words = re.sub(r"<[^>]+>", "", product.body_html).split()[:30]

        llm = _get_llm(TaxonomyClassification)
        result: TaxonomyClassification = await llm.ainvoke(
            f"Product title: {product.title}\n"
            f"product_type hint: {product.product_type}\n"
            f"First 30 words of description: {' '.join(description_words)}\n"
            "Match to the Shopify Standard Product Taxonomy. "
            "The taxonomy_gid MUST be in format: gid://shopify/TaxonomyCategory/<id>. "
            "Only write if confidence is high or medium."
        )

        if result.confidence == "low":
            return _fail(fix_item.fix_id, f"Low confidence taxonomy: {result.taxonomy_path}")

        # Validate GID format
        if not result.taxonomy_gid.startswith("gid://shopify/TaxonomyCategory/"):
            return _fail(fix_item.fix_id, f"Invalid taxonomy GID format: {result.taxonomy_gid}")

        product_gid = f"gid://shopify/Product/{product.id}"
        original_gid = store_data.taxonomy_by_product.get(product.id)

        gid = await shopify_writer.write_taxonomy(
            store_data.store_domain,
            admin_token,
            product_gid,
            result.taxonomy_gid,
            original_gid,
            job_id,
            fix_item.fix_id,
        )
        return _ok(fix_item.fix_id, gid)
    except Exception as exc:
        logger.error("map_taxonomy failed for %s: %s", fix_item.product_id, exc)
        return _fail(fix_item.fix_id, str(exc))


# ---------------------------------------------------------------------------
# Tool: classify_product_type
# ---------------------------------------------------------------------------

async def classify_product_type(
    fix_item: FixItem,
    store_data: MerchantData,
    admin_token: str,
    job_id: str,
) -> FixResult:
    product = _find_product(store_data, fix_item.product_id)
    if product is None:
        return _fail(fix_item.fix_id, f"Product {fix_item.product_id} not found")

    try:
        description_words = re.sub(r"<[^>]+>", "", product.body_html).split()[:50]

        llm = _get_llm(ProductTypeClassification)
        result: ProductTypeClassification = await llm.ainvoke(
            f"Title: {product.title}\n"
            f"First 50 words of description: {' '.join(description_words)}\n"
            "Classify to a specific product type (e.g. 'Hiking Backpack', 'Sleep Mask'). "
            "Only write if confidence is high."
        )

        if result.confidence != "high":
            return _fail(fix_item.fix_id, f"Low confidence product type: {result.product_type}")

        product_gid = f"gid://shopify/Product/{product.id}"
        gid = await shopify_writer.write_product_type(
            store_data.store_domain,
            admin_token,
            product_gid,
            result.product_type,
            product.product_type,
            job_id,
            fix_item.fix_id,
        )
        return _ok(fix_item.fix_id, gid)
    except Exception as exc:
        logger.error("classify_product_type failed for %s: %s", fix_item.product_id, exc)
        return _fail(fix_item.fix_id, str(exc))


# ---------------------------------------------------------------------------
# Tool: fill_metafield
# ---------------------------------------------------------------------------

async def fill_metafield(
    fix_item: FixItem,
    store_data: MerchantData,
    admin_token: str,
    job_id: str,
) -> FixResult:
    product = _find_product(store_data, fix_item.product_id)
    if product is None:
        return _fail(fix_item.fix_id, f"Product {fix_item.product_id} not found")

    try:
        llm = _get_llm(MetafieldExtraction)
        result: MetafieldExtraction = await llm.ainvoke(
            f"Product: {product.title}\n"
            f"Description text: {product.body_html[:2000]}\n"
            "Extract: material, care_instructions, specifications, weight if present. "
            "ONLY extract facts explicitly stated. Return null for anything not present."
        )

        product_gid = f"gid://shopify/Product/{product.id}"
        written = False

        # Write whichever fields were extracted
        field_map = {
            "material": (result.material, "single_line_text_field"),
            "care_instructions": (result.care_instructions, "multi_line_text_field"),
            "specifications": (result.specifications, "multi_line_text_field"),
            "weight": (result.weight, "single_line_text_field"),
        }

        for key, (value, type_) in field_map.items():
            if value:
                await shopify_writer.write_metafield(
                    store_data.store_domain,
                    admin_token,
                    product_gid,
                    namespace="custom",
                    key=key,
                    value=value,
                    type_=type_,
                    job_id=job_id,
                    fix_id=f"{fix_item.fix_id}_{key}",
                )
                written = True

        if not written:
            return _fail(fix_item.fix_id, "No extractable attributes found in description")

        return _ok(fix_item.fix_id, product_gid)
    except Exception as exc:
        logger.error("fill_metafield failed for %s: %s", fix_item.product_id, exc)
        return _fail(fix_item.fix_id, str(exc))


# ---------------------------------------------------------------------------
# Tool: generate_alt_text
# ---------------------------------------------------------------------------

async def generate_alt_text(
    fix_item: FixItem,
    store_data: MerchantData,
    admin_token: str,
    job_id: str,
) -> FixResult:
    product = _find_product(store_data, fix_item.product_id)
    if product is None:
        return _fail(fix_item.fix_id, f"Product {fix_item.product_id} not found")

    # Find first image without alt text
    target_image = next(
        (img for img in product.images if not img.alt or not img.alt.strip()),
        product.images[0] if product.images else None,
    )

    if target_image is None:
        return _fail(fix_item.fix_id, "No images found on product")

    try:
        llm = _get_llm(AltTextGeneration)
        result: AltTextGeneration = await llm.ainvoke(
            f"Product title: {product.title}\n"
            f"product_type: {product.product_type}\n"
            f"Image position: {target_image.position}\n"
            "Generate descriptive alt text for this product image. Max 125 characters. "
            "Describe what the image likely shows based on product type and title."
        )

        image_gid = f"gid://shopify/MediaImage/{target_image.id}"
        gid = await shopify_writer.write_alt_text(
            store_data.store_domain,
            admin_token,
            image_gid,
            result.alt_text,
            target_image.alt,
            job_id,
            fix_item.fix_id,
            product_id=product.id,
        )
        return _ok(fix_item.fix_id, gid)
    except Exception as exc:
        logger.error("generate_alt_text failed for %s: %s", fix_item.product_id, exc)
        return _fail(fix_item.fix_id, str(exc))


# ---------------------------------------------------------------------------
# Tool: create_metafield_definitions — idempotent store-level operation
# ---------------------------------------------------------------------------

async def create_metafield_definitions(
    fix_item: FixItem,
    store_data: MerchantData,
    admin_token: str,
    job_id: str,
) -> FixResult:
    definitions = [
        ("custom", "material", "Material", "single_line_text_field"),
        ("custom", "care_instructions", "Care Instructions", "multi_line_text_field"),
    ]

    try:
        for namespace, key, name, type_ in definitions:
            await shopify_writer.create_metafield_definition(
                store_data.store_domain,
                admin_token,
                namespace,
                key,
                name,
                type_,
            )
        return _ok(fix_item.fix_id, f"gid://shopify/Store/{store_data.store_domain}")
    except Exception as exc:
        logger.error("create_metafield_definitions failed: %s", exc)
        return _fail(fix_item.fix_id, str(exc))


# ---------------------------------------------------------------------------
# Tool: inject_schema_script
# ---------------------------------------------------------------------------

async def inject_schema_script(
    fix_item: FixItem,
    store_data: MerchantData,
    admin_token: str,
    job_id: str,
) -> FixResult:
    """Generate store-level JSON-LD for manual installation.

    Shopify ScriptTagInput.src requires a hosted HTTPS JavaScript URL; it rejects
    inline data: URLs. Until the app has a hosted script asset or theme-file
    writer, return the schema as a copy-paste fix instead of attempting a write.
    """
    try:
        refund_days = 30  # default
        if store_data.policies.refund:
            match = re.search(r"(\d+)[- ]?day", store_data.policies.refund, re.IGNORECASE)
            if match:
                refund_days = int(match.group(1))

        schema = {
            "@context": "https://schema.org/",
            "@type": "Organization",
            "name": store_data.store_name,
            "url": f"https://{store_data.store_domain}",
            "hasMerchantReturnPolicy": {
                "@type": "MerchantReturnPolicy",
                "applicableCountry": "US",
                "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
                "merchantReturnDays": refund_days,
                "returnMethod": "https://schema.org/ReturnByMail",
                "returnFees": "https://schema.org/FreeReturn",
            },
        }

        import json
        return FixResult(
            fix_id=fix_item.fix_id,
            success=True,
            error=None,
            shopify_gid=json.dumps(schema, indent=2),
            script_tag_id=None,
            applied_at=datetime.utcnow(),
        )
    except Exception as exc:
        logger.error("inject_schema_script failed: %s", exc)
        return _fail(fix_item.fix_id, str(exc))


# ---------------------------------------------------------------------------
# Tool: generate_schema_snippet — no write, adds to copy_paste_package
# ---------------------------------------------------------------------------

async def generate_schema_snippet(
    fix_item: FixItem,
    store_data: MerchantData,
    admin_token: str,
    job_id: str,
) -> FixResult:
    """Generate a JSON-LD schema snippet for copy-paste use. No writes."""
    try:
        import json
        schema = {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": "{{product.title}}",
            "image": "{{product.featured_image | img_url: 'master'}}",
            "description": "{{product.description | strip_html | truncate: 200}}",
            "sku": "{{product.selected_variant.sku}}",
            "brand": {
                "@type": "Brand",
                "name": "{{product.vendor}}",
            },
            "offers": {
                "@type": "Offer",
                "url": "{{canonical_url}}",
                "priceCurrency": "{{cart.currency.iso_code}}",
                "price": "{{product.selected_variant.price | money_without_currency}}",
                "availability": "https://schema.org/InStock",
            },
        }
        # Return success — the calling node will add to copy_paste_package
        return FixResult(
            fix_id=fix_item.fix_id,
            success=True,
            error=None,
            shopify_gid=json.dumps(schema, indent=2),  # store schema in gid field for retrieval
            script_tag_id=None,
            applied_at=datetime.utcnow(),
        )
    except Exception as exc:
        return _fail(fix_item.fix_id, str(exc))


# ---------------------------------------------------------------------------
# Tool: suggest_policy_fix — no write, adds draft to copy_paste_package
# ---------------------------------------------------------------------------

async def suggest_policy_fix(
    fix_item: FixItem,
    store_data: MerchantData,
    admin_token: str,
    job_id: str,
) -> FixResult:
    """Generate a policy draft for copy-paste. No writes to Shopify."""
    try:
        policy_type = "refund" if "T1" in fix_item.fix_id or "refund" in fix_item.field.lower() else "shipping"

        drafts = {
            "refund": (
                "Returns & Refunds Policy\n\n"
                "We accept returns within 30 days of purchase. Items must be unused and in original packaging. "
                "To initiate a return, email support@yourstore.com with your order number. "
                "Refunds are processed within 5-7 business days of receiving the returned item."
            ),
            "shipping": (
                "Shipping Policy\n\n"
                "We ship to all 50 US states and select international destinations. "
                "Standard shipping (5-7 business days): Free on orders over $50, otherwise $4.99. "
                "Express shipping (2-3 business days): $12.99. "
                "International shipping (10-21 business days): Rates calculated at checkout."
            ),
        }

        draft = drafts.get(policy_type, drafts["refund"])

        return FixResult(
            fix_id=fix_item.fix_id,
            success=True,
            error=None,
            shopify_gid=draft,  # store draft in gid field
            script_tag_id=None,
            applied_at=datetime.utcnow(),
        )
    except Exception as exc:
        return _fail(fix_item.fix_id, str(exc))


# ---------------------------------------------------------------------------
# Dispatcher — called by executor_node
# ---------------------------------------------------------------------------

TOOL_DISPATCH = {
    "improve_title": improve_title,
    "map_taxonomy": map_taxonomy,
    "classify_product_type": classify_product_type,
    "fill_metafield": fill_metafield,
    "generate_alt_text": generate_alt_text,
    "create_metafield_definitions": create_metafield_definitions,
    "inject_schema_script": inject_schema_script,
    "generate_schema_snippet": generate_schema_snippet,
    "suggest_policy_fix": suggest_policy_fix,
}


async def dispatch_tool(
    fix_item: FixItem,
    store_data: MerchantData,
    admin_token: str,
    job_id: str,
    merchant_intent: str | None = None,
) -> FixResult:
    """Route to the correct tool based on fix_item.type."""
    tool_fn = TOOL_DISPATCH.get(fix_item.type)
    if tool_fn is None:
        return _fail(fix_item.fix_id, f"Unknown fix type: {fix_item.type!r}")
    if fix_item.type == "improve_title":
        return await tool_fn(fix_item, store_data, admin_token, job_id, merchant_intent)
    return await tool_fn(fix_item, store_data, admin_token, job_id)
