"""
faq_generator.py — Generate FAQPage JSON-LD from product data.

Why: Google AI Overviews + Perplexity disproportionately cite FAQPage schema.
Auto-generating 5-8 buyer-intent Q&A pairs per product is a cheap visibility lift.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.models.merchant import Product

logger = logging.getLogger(__name__)


class FAQPair(BaseModel):
    question: str
    answer: str = Field(description="2-4 sentence factual answer.")


class FAQOutput(BaseModel):
    product_id: str
    pairs: list[FAQPair]


_llm_instance = None


def _get_structured_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm = ChatGoogleGenerativeAI(
            model=os.environ.get("VERTEX_MODEL", "gemini-2.5-flash"),
            temperature=0.2,
            google_api_key=os.environ.get("GEMINI_API_KEY"),
        )
        _llm_instance = _llm.with_structured_output(FAQOutput)
    return _llm_instance


_PROMPT = """Generate 6 buyer-intent FAQ pairs for the product below.

Constraints:
- Each Q must reflect a real shopper question (sizing, materials, compatibility, returns, care, target use, audience).
- Each A must be 2-4 sentences, factual, and grounded in the product fields supplied.
- Do NOT invent specifications that aren't in the input. If a fact is unknown, give a safe generic answer ("Refer to the product page for full specifications.").
- Output valid JSON matching the FAQOutput schema.

Product:
- ID: {pid}
- Title: {title}
- Brand: {vendor}
- Type: {ptype}
- Variants: {variants}
- Options: {options}
- Tags: {tags}
- Description:
{description}
"""


def _strip_html(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def _faq_schema(pairs: list[FAQPair]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": p.question,
                "acceptedAnswer": {"@type": "Answer", "text": p.answer},
            }
            for p in pairs
        ],
    }


async def generate_faq_for_product(product: Product) -> dict:
    """Returns {"product_id":..., "pairs":[...], "jsonld":{...}, "script_tag_payload":"..."}"""
    variants_text = ", ".join((v.title or "default") for v in product.variants[:8]) or "n/a"
    options_text = "; ".join(f"{o.name}={'/'.join(o.values[:6])}" for o in product.options) or "n/a"
    prompt = _PROMPT.format(
        pid=product.id,
        title=product.title,
        vendor=product.vendor or "n/a",
        ptype=product.product_type or "n/a",
        variants=variants_text,
        options=options_text,
        tags=", ".join(product.tags[:12]) or "n/a",
        description=_strip_html(product.body_html)[:3000],
    )
    try:
        result: FAQOutput = await _get_structured_llm().ainvoke([HumanMessage(content=prompt)])
        jsonld = _faq_schema(result.pairs)
        import json as _json
        payload = (
            '<script type="application/ld+json">'
            + _json.dumps(jsonld, separators=(",", ":"))
            + "</script>"
        )
        return {
            "product_id": result.product_id or product.id,
            "pairs": [p.model_dump() for p in result.pairs],
            "jsonld": jsonld,
            "script_tag_payload": payload,
        }
    except Exception as exc:
        logger.warning("faq_generator failed for %s: %s", product.id, exc)
        return {
            "product_id": product.id,
            "pairs": [],
            "jsonld": {},
            "script_tag_payload": "",
            "error": str(exc),
        }


async def generate_faq_for_top_products(products: list[Product], limit: int = 10) -> list[dict]:
    sem = asyncio.Semaphore(4)

    async def _bound(p: Product):
        async with sem:
            return await generate_faq_for_product(p)

    return await asyncio.gather(*[_bound(p) for p in products[:limit]])
