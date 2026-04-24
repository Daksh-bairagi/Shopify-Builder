from __future__ import annotations

from collections import Counter

import os
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from app.models.merchant import MerchantData, Product
from app.models.findings import Finding, PerceptionDiff, ProductPerception

# --- Module-level LLM cache (lazy-initialized) ---
_llm: ChatGoogleGenerativeAI | None = None


def _get_llm() -> ChatGoogleGenerativeAI:
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(model=os.environ.get("VERTEX_MODEL", "gemini-2.5-flash"), temperature=0, google_api_key=os.environ.get("GEMINI_API_KEY"))
    return _llm


# --- Pydantic output schemas ---

class StorePerceptionOutput(BaseModel):
    intended_positioning: str
    ai_perception: str
    gap_reasons: list[str]  # min 2, max 5 items


class SingleProductPerceptionOutput(BaseModel):
    intended: str
    ai_extracted: str
    cannot_determine: list[str]  # 1–5 items


class ProductPerceptionItem(BaseModel):
    product_id: str
    intended: str
    ai_extracted: str
    cannot_determine: list[str]


class BatchProductPerceptionOutput(BaseModel):
    products: list[ProductPerceptionItem]


# --- Public async functions ---

async def compute_store_perception_diff(
    data: MerchantData,
    findings: list[Finding],
    merchant_intent: str | None = None,
) -> PerceptionDiff:
    """
    Compare the store's intended brand positioning vs what an AI agent can
    actually determine from its structured data.
    """
    try:
        # Build prompt variables
        sample_titles = ", ".join(p.title for p in data.products[:10])

        raw_types = [p.product_type for p in data.products if p.product_type]
        unique_types = list(dict.fromkeys(raw_types))[:5]
        product_types = ", ".join(unique_types) if unique_types else "not specified"

        all_tags: list[str] = []
        for p in data.products:
            all_tags.extend(p.tags)
        unique_tags = list(dict.fromkeys(all_tags))[:15]
        tags_sample = ", ".join(unique_tags) if unique_tags else "none"

        findings_summary = "\n".join(
            f"- [{f.severity}] {f.check_id}: {f.title}"
            for f in findings[:8]
        )

        intent_line = f"Merchant's stated intent: {merchant_intent}\n" if merchant_intent is not None else ""

        prompt = (
            "You are analyzing a Shopify store's data quality from the perspective of an AI shopping agent.\n\n"
            f"Store: {data.store_name}\n"
            f"{intent_line}"
            f"Domain: {data.store_domain}\n"
            f"Total products: {len(data.products)}\n"
            f"Sample product titles: {sample_titles}\n"
            f"Product types: {product_types}\n"
            f"Tags sample: {tags_sample}\n\n"
            "Active audit findings (issues the store has):\n"
            f"{findings_summary}\n\n"
            "Based on this data, identify:\n"
            "1. How the merchant INTENDS to be positioned (infer from titles, vendor name, product types)\n"
            "2. How an AI agent would ACTUALLY perceive this store based on available structured data\n"
            "3. The specific reasons for any gap between intended and actual perception\n\n"
            "Be specific and actionable. \"AI perception\" should describe exactly what data signals are present or missing."
        )

        llm = _get_llm()
        structured_llm = llm.with_structured_output(StorePerceptionOutput)
        result: StorePerceptionOutput = await structured_llm.ainvoke(
            [HumanMessage(content=prompt)]
        )

        return PerceptionDiff(
            intended_positioning=result.intended_positioning,
            ai_perception=result.ai_perception,
            gap_reasons=result.gap_reasons,
        )

    except Exception:
        return PerceptionDiff(
            intended_positioning="Could not determine intended positioning",
            ai_perception="Insufficient data to assess AI perception",
            gap_reasons=["Analysis unavailable"],
        )


async def compute_product_perceptions(
    products: list[Product],
    findings: list[Finding],
    merchant_intent: str | None = None,
    max_products: int = 10,
) -> list[ProductPerception]:
    """
    For each of the worst products (up to max_products), determine what an AI
    agent can and cannot extract from structured data. Uses a single batch LLM call.
    """
    try:
        # --- Select worst products by finding frequency ---
        product_issue_count: Counter[str] = Counter()
        for f in findings:
            for pid in f.affected_products:
                product_issue_count[pid] += 1

        if product_issue_count:
            # Sort products by issue count descending, preserving original list order for ties
            sorted_ids = [pid for pid, _ in product_issue_count.most_common()]
            id_to_product = {p.id: p for p in products}
            selected: list[Product] = []
            for pid in sorted_ids:
                if pid in id_to_product and len(selected) < max_products:
                    selected.append(id_to_product[pid])
            # If we still have room, add products not in any finding
            if len(selected) < max_products:
                seen = {p.id for p in selected}
                for p in products:
                    if p.id not in seen and len(selected) < max_products:
                        selected.append(p)
        else:
            selected = products[:max_products]

        if not selected:
            return []

        # --- Build product text block for prompt ---
        product_blocks: list[str] = []
        for p in selected:
            option_names = ", ".join(o.name for o in p.options) if p.options else "none"
            block = (
                f"ID: {p.id}\n"
                f"Title: {p.title}\n"
                f"Type: {p.product_type or 'not specified'}\n"
                f"Tags: {', '.join(p.tags) if p.tags else 'none'}\n"
                f"Options: {option_names}\n"
                f"Has description: {'yes' if p.body_html else 'no'}\n"
                f"Variants: {len(p.variants)} variants"
            )
            product_blocks.append(block)

        products_text = "\n\n".join(product_blocks)

        intent_context = (
            f"Merchant's stated intent for their store: {merchant_intent}\n\n"
            if merchant_intent is not None
            else ""
        )

        prompt = (
            f"{intent_context}"
            "For each Shopify product below, analyze from an AI shopping agent's perspective:\n"
            "1. What the merchant INTENDS this product to convey (from title, description, tags)\n"
            "2. What an AI agent can ACTUALLY extract from the structured data fields\n"
            "3. Key attributes that AI CANNOT determine from available data\n\n"
            f"Products:\n{products_text}\n\n"
            "For each product, \"cannot_determine\" should list specific attributes an AI would want but cannot find "
            "(examples: \"material\", \"size range\", \"country of origin\", \"target age group\", \"compatibility\")."
        )

        llm = _get_llm()
        structured_llm = llm.with_structured_output(BatchProductPerceptionOutput)
        result: BatchProductPerceptionOutput = await structured_llm.ainvoke(
            [HumanMessage(content=prompt)]
        )

        # --- Build finding-to-product mapping ---
        # product_id -> list of finding IDs that include it
        product_finding_ids: dict[str, list[str]] = {p.id: [] for p in selected}
        for f in findings:
            for pid in f.affected_products:
                if pid in product_finding_ids:
                    product_finding_ids[pid].append(f.id)

        # --- Map Pydantic results back to ProductPerception dataclasses ---
        # Index results by product_id for safe lookup
        result_map = {item.product_id: item for item in result.products}

        perceptions: list[ProductPerception] = []
        for p in selected:
            item = result_map.get(p.id)
            if item is None:
                print(f"perception_diff: skipping product {p.id}, not in LLM results")
                continue

            perceptions.append(
                ProductPerception(
                    product_id=p.id,
                    intended=item.intended,
                    ai_extracted=item.ai_extracted,
                    cannot_determine=item.cannot_determine,
                    root_finding_ids=product_finding_ids.get(p.id, []),
                )
            )

        return perceptions

    except Exception:
        return []
