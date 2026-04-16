from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage

from app.models.merchant import Product


# ---------------------------------------------------------------------------
# Pydantic output schemas for structured LLM output
# ---------------------------------------------------------------------------

class ProductTitleAnalysis(BaseModel):
    product_id: str
    title_contains_category_noun: bool
    category_noun_found: Optional[str] = None  # the noun found, or None


class BatchTitleAnalysisResult(BaseModel):
    results: list[ProductTitleAnalysis]


# ---------------------------------------------------------------------------
# Lazy LLM instantiation (avoids import-time Vertex AI credential check)
# ---------------------------------------------------------------------------

_structured_llm_instance = None


def _get_structured_llm():
    global _structured_llm_instance
    if _structured_llm_instance is None:
        _llm = ChatVertexAI(model="gemini-2.0-flash", temperature=0)
        _structured_llm_instance = _llm.with_structured_output(BatchTitleAnalysisResult)
    return _structured_llm_instance


_BATCH_SIZE = 100

_PROMPT_TEMPLATE = """You are analyzing Shopify product titles for AI commerce readiness.

For each product below, determine if the title contains a CATEGORY NOUN — a word that tells an AI agent what TYPE of thing the product is (examples: "shoe", "jacket", "mug", "desk", "lamp", "serum", "supplement", "bracelet", "poster").

A brand-name-only title like "Premium Vibe X" or "CloudBliss Pro" has NO category noun.
A good title like "Premium Vibe X Running Shoe" or "CloudBliss Pro Memory Foam Pillow" HAS a category noun.

Products:
{product_list_text}

Return a result for EVERY product ID listed. Do not skip any.
Your output must be a JSON object matching the schema provided."""


def _safe_defaults(products: list[Product]) -> list[dict]:
    """Return safe defaults (all True) so C2 won't fire on error."""
    return [
        {"product_id": p.id, "title_contains_category_noun": True}
        for p in products
    ]


def _format_product_list(products: list[Product]) -> str:
    lines = [f'- ID: {p.id} | Title: "{p.title}"' for p in products]
    return "\n".join(lines)


async def _analyze_batch(batch: list[Product]) -> list[dict]:
    """Run a single LLM call for a batch of up to 100 products."""
    product_list_text = _format_product_list(batch)
    prompt = _PROMPT_TEMPLATE.format(product_list_text=product_list_text)
    message = HumanMessage(content=prompt)

    try:
        result: BatchTitleAnalysisResult = await _get_structured_llm().ainvoke([message])
        return [
            {
                "product_id": item.product_id,
                "title_contains_category_noun": item.title_contains_category_noun,
            }
            for item in result.results
        ]
    except Exception as exc:
        print(f"llm_analysis error: {exc}")
        return _safe_defaults(batch)


async def analyze_products(products: list[Product]) -> list[dict]:
    """
    Determine which products have brand-name-only titles (no category noun).

    Processes products in batches of 100. Returns a list of dicts with keys:
        - product_id: str
        - title_contains_category_noun: bool

    On any failure, returns safe defaults (all True) so the C2 check won't fire.
    """
    if not products:
        return []

    all_results: list[dict] = []

    for start in range(0, len(products), _BATCH_SIZE):
        batch = products[start : start + _BATCH_SIZE]
        batch_results = await _analyze_batch(batch)

        # Fix 1: Remove hallucinated product IDs not in this batch
        valid_ids = {p.id for p in batch}
        batch_results = [r for r in batch_results if r["product_id"] in valid_ids]

        # Guard: if the LLM skipped entries, fill gaps with safe defaults
        returned_ids = {r["product_id"] for r in batch_results}
        for product in batch:
            if product.id not in returned_ids:
                batch_results.append(
                    {"product_id": product.id, "title_contains_category_noun": True}
                )

        all_results.extend(batch_results)

    return all_results
