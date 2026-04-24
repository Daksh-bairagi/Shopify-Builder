from __future__ import annotations

from typing import Optional

import os
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from app.models.merchant import MerchantData
from app.models.findings import Finding, MCPResult


# ---------------------------------------------------------------------------
# Pydantic output schemas (for structured LLM output only)
# ---------------------------------------------------------------------------

class SimulatedAnswer(BaseModel):
    question: str
    response: str               # AI's answer or "I cannot determine..."
    classification: str         # 'ANSWERED' | 'UNANSWERED' | 'WRONG'
    ground_truth_mismatch: Optional[str] = None


class MCPSimulationOutput(BaseModel):
    answers: list[SimulatedAnswer]


# ---------------------------------------------------------------------------
# Lazy LLM initializer
# ---------------------------------------------------------------------------

_llm: ChatGoogleGenerativeAI | None = None


def _get_llm() -> ChatGoogleGenerativeAI:
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(model=os.environ.get("VERTEX_MODEL", "gemini-2.5-flash"), temperature=0, google_api_key=os.environ.get("GEMINI_API_KEY"))
    return _llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_product_data_text(merchant_data: MerchantData) -> str:
    """Render up to 5 products as structured one-liner text for the prompt."""
    lines: list[str] = []
    for product in merchant_data.products[:5]:
        in_stock = any(
            v.inventory_quantity > 0 for v in product.variants
        ) if product.variants else False

        options_text = "; ".join(
            f"{opt.name}: {', '.join(opt.values)}" for opt in product.options
        ) if product.options else "none"

        tags_text = ", ".join(product.tags) if product.tags else "none"
        product_type_text = product.product_type or "not specified"
        variant_count = len(product.variants)

        lines.append(
            f'Product: "{product.title}" | Type: {product_type_text} | '
            f"Tags: {tags_text} | Variants: {variant_count} | "
            f"In stock: {in_stock} | Options: {options_text}"
        )
    return "\n".join(lines) if lines else "No products available."


def _trim_policy(text: str) -> str:
    """Trim policy text to first 200 chars; return 'Not provided' if empty."""
    if not text or not text.strip():
        return "Not provided"
    trimmed = text.strip()[:200]
    return trimmed + ("..." if len(text.strip()) > 200 else "")


def _default_unanswered_results(questions: list[str]) -> list[MCPResult]:
    """Return 5 UNANSWERED results for use on error."""
    return [
        MCPResult(
            question=q,
            response="Simulation unavailable",
            classification="UNANSWERED",
            ground_truth_mismatch=None,
            related_finding_ids=[],
        )
        for q in questions
    ]


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

async def run_mcp_simulation(
    merchant_data: MerchantData,
    findings: list[Finding],
) -> list[MCPResult]:
    """
    Simulate an MCP-based shopping AI answering 5 standard questions about
    the merchant's store using only their structured product data.

    Returns a list of MCPResult dataclasses.
    """
    # Resolve product title for question substitution
    first_product_title = (
        merchant_data.products[0].title
        if merchant_data.products
        else "your products"
    )

    questions = [
        "What products do you sell and what categories are they in?",
        "Can I return this product if it doesn't fit? What's the return window?",
        "Do you ship internationally? Which countries?",
        f"Is {first_product_title} currently in stock?",
        f"What materials or specifications does {first_product_title} come in?",
    ]

    try:
        # Build prompt context
        product_data_text = _build_product_data_text(merchant_data)
        refund_text = _trim_policy(merchant_data.policies.refund)
        shipping_text = _trim_policy(merchant_data.policies.shipping)

        prompt = (
            "You are simulating an AI shopping assistant that ONLY has access to the structured "
            "product data below from a Shopify store. You cannot browse the web or access any "
            "information not present in the data provided.\n\n"
            f"Store: {merchant_data.store_name}\n"
            f"Domain: {merchant_data.store_domain}\n\n"
            "PRODUCT DATA (structured fields only):\n"
            f"{product_data_text}\n\n"
            "POLICY DATA:\n"
            f"Refund policy: {refund_text}\n"
            f"Shipping policy: {shipping_text}\n\n"
            "For each question below, respond as this AI assistant would:\n"
            "- If you can fully answer from the data: classify as ANSWERED\n"
            "- If you cannot determine the answer from the data: classify as UNANSWERED, "
            'respond with "I cannot determine [X] from available product data"\n'
            "- If the data contains conflicting or clearly wrong information: classify as WRONG\n\n"
            "Questions:\n"
            f"1. {questions[0]}\n"
            f"2. {questions[1]}\n"
            f"3. {questions[2]}\n"
            f"4. {questions[3]}\n"
            f"5. {questions[4]}\n\n"
            "Your output must be a JSON object matching the schema provided. "
            "Include one answer per question in order."
        )

        llm = _get_llm()
        structured_llm = llm.with_structured_output(MCPSimulationOutput)
        output: MCPSimulationOutput = await structured_llm.ainvoke(
            [HumanMessage(content=prompt)]
        )

        if len(output.answers) != len(questions):
            return _default_unanswered_results(questions)

        # Build check_id -> [finding.id, ...] index
        check_to_findings: dict[str, list[str]] = {}
        for f in findings:
            check_to_findings.setdefault(f.check_id, []).append(f.id)

        # Which audit checks are relevant to each question (by index)
        question_to_checks: dict[int, list[str]] = {
            0: ["C1"],
            1: ["T1"],
            2: ["T2"],
            3: ["A1", "A2"],
            4: ["C4", "C5"],
        }

        results: list[MCPResult] = []
        for idx, answer in enumerate(output.answers):
            # Collect related finding IDs for UNANSWERED / WRONG questions
            related_ids: list[str] = []
            if answer.classification in ("UNANSWERED", "WRONG"):
                for check_id in question_to_checks.get(idx, []):
                    related_ids.extend(check_to_findings.get(check_id, []))

            results.append(
                MCPResult(
                    question=questions[idx],
                    response=answer.response,
                    classification=answer.classification,
                    ground_truth_mismatch=answer.ground_truth_mismatch,
                    related_finding_ids=related_ids,
                )
            )

        return results

    except Exception:
        return _default_unanswered_results(questions)
