"""
ai_visibility.py — FLAGSHIP: Live multi-LLM AI visibility probe.

Sends category-level shopping prompts to Gemini (with Google Search grounding),
detects whether the merchant is mentioned, ranks competitors, and computes
share-of-voice. This is the demo moment: real prompts, real models, real
citations.

Provider matrix (April 2026):
  - Gemini 2.5 Flash with `google_search` tool       — primary, available now via GEMINI_API_KEY
  - ChatGPT / Perplexity / Claude                    — stubbed adapters; real
                                                       calls require additional API keys

Falls back gracefully when keys are absent (the function returns a
structured-zero result and a `provider_status` map).
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Optional

from pydantic import BaseModel, Field

from app.models.merchant import MerchantData

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default prompt set
# ---------------------------------------------------------------------------

DEFAULT_PROMPT_TEMPLATES: list[str] = [
    "best {category} under $100",
    "top {category} for beginners 2026",
    "where to buy {category} online",
    "what is the best {category} brand",
    "compare {category} options for everyday use",
    "best gift {category} this year",
    "is {brand} a good brand for {category}",
    "{brand} vs alternatives for {category}",
]


def _derive_prompts(merchant_data: MerchantData, max_prompts: int = 8) -> list[str]:
    """Pick representative prompts for the merchant's catalog."""
    types_seen: dict[str, int] = {}
    for p in merchant_data.products:
        if p.product_type:
            types_seen[p.product_type.lower()] = types_seen.get(p.product_type.lower(), 0) + 1
    top_types = sorted(types_seen.items(), key=lambda x: -x[1])[:3]
    if not top_types:
        # Fall back to a generic noun pulled from store name.
        top_types = [(merchant_data.store_name.split()[0].lower() if merchant_data.store_name else "products", 1)]

    brand = (merchant_data.products[0].vendor if merchant_data.products else merchant_data.store_name) or "this store"

    prompts: list[str] = []
    for category, _ in top_types:
        for tpl in DEFAULT_PROMPT_TEMPLATES:
            prompts.append(tpl.format(category=category, brand=brand))
            if len(prompts) >= max_prompts:
                return prompts
    return prompts[:max_prompts]


# ---------------------------------------------------------------------------
# Mention detection
# ---------------------------------------------------------------------------

def _build_mention_aliases(merchant_data: MerchantData) -> list[str]:
    aliases = set()
    if merchant_data.store_name:
        aliases.add(merchant_data.store_name.lower())
    if merchant_data.store_domain:
        aliases.add(merchant_data.store_domain.lower())
        aliases.add(merchant_data.store_domain.split(".")[0].lower())
    # Vendor mentions
    for p in merchant_data.products[:50]:
        if p.vendor:
            aliases.add(p.vendor.lower())
    aliases = {a for a in aliases if len(a) >= 3}
    return list(aliases)


def _detect_mention(answer_text: str, citation_urls: list[str], aliases: list[str], domain: str) -> dict:
    text = (answer_text or "").lower()
    domain_l = (domain or "").lower()
    name_hits = [a for a in aliases if a and a in text]
    url_hits = [u for u in citation_urls if domain_l and domain_l in u.lower()]
    rank: Optional[int] = None
    if name_hits:
        # Approximate rank by first-appearance order in the answer.
        positions = sorted(text.find(a) for a in name_hits if text.find(a) >= 0)
        if positions:
            # Crude rank: count "1.", "2." markers before first hit.
            before = text[: positions[0]]
            rank = len(re.findall(r"\b\d+\.\s", before)) + 1
    return {
        "mentioned": bool(name_hits) or bool(url_hits),
        "name_hits": name_hits[:5],
        "citation_hits": url_hits[:5],
        "approx_rank": rank,
    }


# ---------------------------------------------------------------------------
# Provider adapters
# ---------------------------------------------------------------------------

class _ProviderResult(BaseModel):
    provider: str
    prompt: str
    answer: str = ""
    citations: list[str] = Field(default_factory=list)
    error: str | None = None


async def _call_gemini(prompt: str) -> _ProviderResult:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _ProviderResult(provider="gemini", prompt=prompt, error="GEMINI_API_KEY missing")
    try:
        # New google-genai SDK — installed in this venv.
        from google import genai
        from google.genai import types as genai_types

        client = genai.Client(api_key=api_key)
        model_name = os.environ.get("VERTEX_MODEL", "gemini-2.5-flash")
        config = genai_types.GenerateContentConfig(
            tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
        )

        resp = await asyncio.to_thread(
            client.models.generate_content,
            model=model_name,
            contents=prompt,
            config=config,
        )

        answer = ""
        try:
            answer = resp.text or ""
        except Exception:
            answer = str(resp)

        citations: list[str] = []
        try:
            for cand in (resp.candidates or []):
                meta = getattr(cand, "grounding_metadata", None)
                if meta is None:
                    continue
                for chunk in (getattr(meta, "grounding_chunks", []) or []):
                    web = getattr(chunk, "web", None)
                    if web is not None and getattr(web, "uri", None):
                        citations.append(web.uri)
        except Exception:
            pass
        return _ProviderResult(provider="gemini", prompt=prompt, answer=answer, citations=citations[:20])
    except Exception as exc:
        logger.warning("gemini call failed: %s", exc)
        return _ProviderResult(provider="gemini", prompt=prompt, error=str(exc))


async def _call_openai(prompt: str) -> _ProviderResult:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _ProviderResult(provider="openai", prompt=prompt, error="OPENAI_API_KEY missing")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60) as cli:
            r = await cli.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                    "input": prompt,
                    "tools": [{"type": "web_search_preview"}],
                },
            )
            r.raise_for_status()
            data = r.json()
            answer = ""
            citations: list[str] = []
            for o in data.get("output", []):
                if o.get("type") == "message":
                    for c in o.get("content", []):
                        if c.get("type") == "output_text":
                            answer += c.get("text", "")
                            for ann in (c.get("annotations") or []):
                                if ann.get("type") == "url_citation" and ann.get("url"):
                                    citations.append(ann["url"])
            return _ProviderResult(provider="openai", prompt=prompt, answer=answer, citations=citations[:20])
    except Exception as exc:
        logger.warning("openai call failed: %s", exc)
        return _ProviderResult(provider="openai", prompt=prompt, error=str(exc))


async def _call_perplexity(prompt: str) -> _ProviderResult:
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        return _ProviderResult(provider="perplexity", prompt=prompt, error="PERPLEXITY_API_KEY missing")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60) as cli:
            r = await cli.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": os.environ.get("PERPLEXITY_MODEL", "sonar-pro"),
                    "messages": [{"role": "user", "content": prompt}],
                    "return_citations": True,
                },
            )
            r.raise_for_status()
            data = r.json()
            answer = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            citations = data.get("citations", []) or []
            return _ProviderResult(provider="perplexity", prompt=prompt, answer=answer, citations=citations[:20])
    except Exception as exc:
        logger.warning("perplexity call failed: %s", exc)
        return _ProviderResult(provider="perplexity", prompt=prompt, error=str(exc))


async def _call_claude(prompt: str) -> _ProviderResult:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _ProviderResult(provider="claude", prompt=prompt, error="ANTHROPIC_API_KEY missing")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60) as cli:
            r = await cli.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
                    "max_tokens": 1024,
                    "tools": [{"type": "web_search_20250305", "name": "web_search"}],
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            r.raise_for_status()
            data = r.json()
            answer = ""
            citations: list[str] = []
            for block in (data.get("content") or []):
                if block.get("type") == "text":
                    answer += block.get("text", "")
                    for cit in (block.get("citations") or []):
                        url = cit.get("url")
                        if url:
                            citations.append(url)
            return _ProviderResult(provider="claude", prompt=prompt, answer=answer, citations=citations[:20])
    except Exception as exc:
        logger.warning("claude call failed: %s", exc)
        return _ProviderResult(provider="claude", prompt=prompt, error=str(exc))


_PROVIDERS = {
    "gemini": _call_gemini,
    "openai": _call_openai,
    "perplexity": _call_perplexity,
    "claude": _call_claude,
}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def probe_ai_visibility(
    merchant_data: MerchantData,
    prompts: Optional[list[str]] = None,
    providers: Optional[list[str]] = None,
    include_competitors_from_results: bool = True,
) -> dict:
    """
    Run prompts × providers and compute share-of-voice for the merchant.

    Returns:
        {
            "prompts":    [...],
            "providers":  {"gemini": "ok"|"missing_key"|"error", ...},
            "results":    [
                {"prompt": ..., "provider": ..., "answer_excerpt": ...,
                 "citations": [...], "merchant_mentioned": bool,
                 "approx_rank": int|None,
                 "competitor_mentions": [...]}
            ],
            "share_of_voice":   {provider: float 0-100},
            "citation_rate":    {provider: float 0-100},
            "competitor_leaderboard": [{"name": "...", "appearances": int}, ...],
            "summary": {...}
        }
    """
    prompts = prompts or _derive_prompts(merchant_data)
    providers = providers or ["gemini"]   # cheap default; caller can opt in
    aliases = _build_mention_aliases(merchant_data)
    domain = merchant_data.store_domain or ""

    coros = []
    for prompt in prompts:
        for prov in providers:
            fn = _PROVIDERS.get(prov)
            if not fn:
                continue
            coros.append(fn(prompt))

    raw_results: list[_ProviderResult] = await asyncio.gather(*coros, return_exceptions=False)

    provider_status: dict[str, str] = {}
    for prov in providers:
        if prov not in _PROVIDERS:
            provider_status[prov] = "unknown_provider"
            continue
        # Latest result for that provider tells us status.
        last_for_prov = next((r for r in reversed(raw_results) if r.provider == prov), None)
        if last_for_prov is None:
            provider_status[prov] = "no_calls"
        elif last_for_prov.error:
            provider_status[prov] = f"error: {last_for_prov.error}"
        else:
            provider_status[prov] = "ok"

    rich: list[dict] = []
    sov_counts: dict[str, int] = {p: 0 for p in providers}
    sov_totals: dict[str, int] = {p: 0 for p in providers}
    cite_counts: dict[str, int] = {p: 0 for p in providers}
    competitor_counter: dict[str, int] = {}

    # Crude competitor extraction: capitalized 2-3 word brands that appear
    # in answers but aren't us.
    own_aliases = {a.lower() for a in aliases}
    candidate_re = re.compile(r"\b([A-Z][A-Za-z0-9]{2,}(?:\s[A-Z][A-Za-z0-9]{2,}){0,2})\b")

    for r in raw_results:
        sov_totals[r.provider] = sov_totals.get(r.provider, 0) + 1
        if r.error:
            rich.append({
                "prompt": r.prompt,
                "provider": r.provider,
                "error": r.error,
                "merchant_mentioned": False,
                "approx_rank": None,
                "answer_excerpt": "",
                "citations": [],
                "competitor_mentions": [],
            })
            continue
        det = _detect_mention(r.answer, r.citations, aliases, domain)
        if det["mentioned"]:
            sov_counts[r.provider] = sov_counts.get(r.provider, 0) + 1
        if det["citation_hits"]:
            cite_counts[r.provider] = cite_counts.get(r.provider, 0) + 1

        comps: list[str] = []
        if include_competitors_from_results:
            for m in candidate_re.finditer(r.answer or ""):
                token = m.group(1)
                if token.lower() in own_aliases:
                    continue
                if token.lower() in {"the", "best", "compare", "find", "shop"}:
                    continue
                comps.append(token)
                competitor_counter[token] = competitor_counter.get(token, 0) + 1

        rich.append({
            "prompt": r.prompt,
            "provider": r.provider,
            "answer_excerpt": (r.answer or "")[:600],
            "citations": r.citations,
            "merchant_mentioned": det["mentioned"],
            "name_hits": det["name_hits"],
            "citation_hits": det["citation_hits"],
            "approx_rank": det["approx_rank"],
            "competitor_mentions": list(dict.fromkeys(comps))[:10],
        })

    sov: dict[str, float] = {}
    cite_rate: dict[str, float] = {}
    for p in providers:
        total = max(1, sov_totals.get(p, 0))
        sov[p] = round(100 * sov_counts.get(p, 0) / total, 1)
        cite_rate[p] = round(100 * cite_counts.get(p, 0) / total, 1)

    leaderboard = sorted(competitor_counter.items(), key=lambda x: -x[1])[:10]
    leaderboard_out = [{"name": n, "appearances": c} for n, c in leaderboard]

    composite_sov = round(sum(sov.values()) / max(1, len(sov)), 1)
    return {
        "prompts": prompts,
        "providers": provider_status,
        "results": rich,
        "share_of_voice": sov,
        "citation_rate": cite_rate,
        "competitor_leaderboard": leaderboard_out,
        "summary": {
            "total_calls": sum(sov_totals.values()),
            "merchant_mentions": sum(sov_counts.values()),
            "composite_share_of_voice": composite_sov,
            "providers_attempted": providers,
        },
    }
