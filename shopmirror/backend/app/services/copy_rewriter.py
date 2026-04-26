"""
copy_rewriter.py — Per-product, per-channel conversational copy rewriter.

Different AI surfaces parse copy differently:
  - ChatGPT Shopping: front-load attributes, factual, "best for" framings
  - Perplexity:       answer-first, citation-friendly, fact-dense
  - Google AI Mode:   structured benefits + concrete attributes
  - Generic AI:       safe baseline that improves recall
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


CHANNEL_BRIEFS = {
    "chatgpt": (
        "ChatGPT Shopping. Front-load category noun and key attributes (material, "
        "size, primary use). Avoid marketing fluff. Use factual, parseable bullet phrasing."
    ),
    "perplexity": (
        "Perplexity. Lead with the most cite-worthy sentence. Each sentence should be "
        "verifiable and self-contained. Include specifications inline."
    ),
    "google": (
        "Google AI Mode. Use structured benefit-attribute pairs. Lead with the category "
        "phrase users search. Include compatibility, audience, and care notes."
    ),
    "generic": (
        "Generic AI assistant. Plain, clear, factual. 1 lead sentence with "
        "category + key benefit, then 4-6 bullet points of attributes."
    ),
}


class ChannelCopy(BaseModel):
    channel: str
    title: str = Field(description="Rewritten product title, ≤ 90 chars")
    description: str = Field(description="Rewritten product description")
    key_bullets: list[str] = Field(description="3-6 attribute bullets")
    suggested_keywords: list[str] = Field(description="3-8 search-intent phrases")


class RewriteBundle(BaseModel):
    product_id: str
    original_title: str
    variants: list[ChannelCopy]


_llm_instance = None


def _get_structured_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm = ChatGoogleGenerativeAI(
            model=os.environ.get("VERTEX_MODEL", "gemini-2.5-flash"),
            temperature=0.4,
            google_api_key=os.environ.get("GEMINI_API_KEY"),
        )
        _llm_instance = _llm.with_structured_output(RewriteBundle)
    return _llm_instance


_PROMPT = """You are an AI commerce copywriter. Rewrite the product copy for each
of these channels: chatgpt, perplexity, google, generic.

Channel briefs:
{briefs}

Product:
- ID: {pid}
- Title: {title}
- Vendor (Brand): {vendor}
- Type: {ptype}
- Tags: {tags}
- Variants: {variants}
- Options: {options}
- Description (raw HTML stripped):
{description}

Rules:
- Never invent specs that aren't in the input.
- Keep claims falsifiable.
- Use short, factual sentences.
- Output one ChannelCopy per channel listed.
"""


def _strip_html(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


async def rewrite_product(product: Product, channels: list[str] | None = None) -> dict:
    """Run rewriter for one product across channels."""
    channels = channels or list(CHANNEL_BRIEFS.keys())
    briefs = "\n".join(f"- {c}: {CHANNEL_BRIEFS[c]}" for c in channels if c in CHANNEL_BRIEFS)
    variants_text = ", ".join((v.title or "default") for v in product.variants[:8]) or "n/a"
    options_text = "; ".join(f"{o.name}={'/'.join(o.values[:6])}" for o in product.options) or "n/a"

    prompt = _PROMPT.format(
        briefs=briefs,
        pid=product.id,
        title=product.title,
        vendor=product.vendor or "n/a",
        ptype=product.product_type or "n/a",
        tags=", ".join(product.tags[:12]) or "n/a",
        variants=variants_text,
        options=options_text,
        description=_strip_html(product.body_html)[:3000],
    )

    try:
        result: RewriteBundle = await _get_structured_llm().ainvoke([HumanMessage(content=prompt)])
        return result.model_dump()
    except Exception as exc:
        logger.warning("copy_rewriter failed for %s: %s", product.id, exc)
        return {
            "product_id": product.id,
            "original_title": product.title,
            "variants": [],
            "error": str(exc),
        }


async def rewrite_top_products(products: list[Product], limit: int = 10, channels: list[str] | None = None) -> list[dict]:
    """Rewrite the first N products in parallel (bounded concurrency)."""
    sem = asyncio.Semaphore(4)

    async def _bound(p: Product):
        async with sem:
            return await rewrite_product(p, channels)

    return await asyncio.gather(*[_bound(p) for p in products[:limit]])
