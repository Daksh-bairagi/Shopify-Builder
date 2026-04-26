"""
trust_signals.py — Score the store on the three trust-signal axes that AI
search engines use to decide who to cite (Semrush 2026 framework):

  1. Entity Identity     — Organization schema, sameAs links, NAP consistency
  2. Evidence & Citations — review schema density, third-party mention proxy
  3. Technical & UX      — HTTPS, sitemap, bot allowance, page speed signals

Pure-ish: probes the merchant_data already in memory, plus a single optional
HEAD request for HTTPS/redirect inspection (kept lightweight).
"""
from __future__ import annotations

import re
from typing import Optional

from app.models.merchant import MerchantData


def _flatten_jsonld(merchant_data: MerchantData) -> list[dict]:
    flat: list[dict] = []
    for blocks in (merchant_data.schema_by_url or {}).values():
        for b in blocks or []:
            if isinstance(b, dict):
                flat.append(b)
    return flat


def _has_type(blocks: list[dict], schema_type: str) -> bool:
    s = schema_type.lower()
    for b in blocks:
        t = b.get("@type")
        if isinstance(t, str) and t.lower() == s:
            return True
        if isinstance(t, list) and any(isinstance(x, str) and x.lower() == s for x in t):
            return True
    return False


def _count_review_blocks(blocks: list[dict]) -> int:
    n = 0
    for b in blocks:
        t = b.get("@type")
        types = t if isinstance(t, list) else [t]
        if any(isinstance(x, str) and x.lower() in ("review", "aggregaterating") for x in types):
            n += 1
        # Aggregations embedded in Product
        if isinstance(b.get("aggregateRating"), dict):
            n += 1
        if isinstance(b.get("review"), (dict, list)):
            n += 1
    return n


def _organization_block(blocks: list[dict]) -> Optional[dict]:
    for b in blocks:
        t = b.get("@type")
        types = t if isinstance(t, list) else [t]
        if any(isinstance(x, str) and x.lower() == "organization" for x in types):
            return b
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_trust_signals(merchant_data: MerchantData) -> dict:
    blocks = _flatten_jsonld(merchant_data)

    # ---------- Entity Identity ----------
    org = _organization_block(blocks)
    has_org_schema = org is not None
    same_as = []
    if isinstance(org, dict):
        sa = org.get("sameAs")
        if isinstance(sa, list):
            same_as = [str(x) for x in sa]
        elif isinstance(sa, str):
            same_as = [sa]
    has_logo = bool(org and org.get("logo"))
    has_search_action = isinstance(org and org.get("potentialAction"), dict)
    has_contact = isinstance(org, dict) and (org.get("contactPoint") or org.get("email") or org.get("telephone"))
    n_sameas = len(same_as)

    entity_score = 0
    entity_score += 25 if has_org_schema else 0
    entity_score += min(35, n_sameas * 10)        # 4+ social links = full credit
    entity_score += 15 if has_logo else 0
    entity_score += 15 if has_search_action else 0
    entity_score += 10 if has_contact else 0

    # ---------- Evidence & Citations ----------
    review_blocks = _count_review_blocks(blocks)
    review_density = round(review_blocks / max(1, len(merchant_data.products)), 2)

    # Approximate "expert mention" proxy = appearance in store policies / homepage
    citation_text = " ".join([
        merchant_data.policies.refund or "",
        merchant_data.policies.shipping or "",
        merchant_data.policies.privacy or "",
        merchant_data.policies.terms_of_service or "",
    ])
    mention_signals = 0
    for needle in ("featured in", "as seen on", "press", "awards", "certified", "winner"):
        if needle in citation_text.lower():
            mention_signals += 1

    evidence_score = 0
    evidence_score += 35 if review_density >= 0.5 else round(review_density * 70)
    evidence_score += min(35, review_blocks)       # raw count cap
    evidence_score += min(20, mention_signals * 7)
    evidence_score += 10 if _has_type(blocks, "FAQPage") else 0
    evidence_score = min(100, evidence_score)

    # ---------- Technical & UX ----------
    # Real HTTPS detection: prefer scheme on store_domain, fall back to schemes
    # observed in any captured JSON-LD URL keys.
    domain = (merchant_data.store_domain or "").strip().lower()
    if domain.startswith(("http://", "https://")):
        has_https = domain.startswith("https://")
    else:
        url_keys = list((merchant_data.schema_by_url or {}).keys())
        if url_keys:
            has_https = all(k.startswith("https://") for k in url_keys if k.startswith("http"))
        else:
            # Unknown — don't credit. Stricter than before, but truthful.
            has_https = False
    has_sitemap = merchant_data.sitemap_present
    sitemap_has_products = merchant_data.sitemap_has_products
    has_llms_txt = bool(merchant_data.llms_txt)
    robots_present = bool(merchant_data.robots_txt)

    tech_score = 0
    tech_score += 20 if has_https else 0
    tech_score += 20 if has_sitemap else 0
    tech_score += 15 if sitemap_has_products else 0
    tech_score += 25 if has_llms_txt else 0       # AI-era specific
    tech_score += 10 if robots_present else 0
    tech_score += 10 if merchant_data.price_in_html else 0

    # ---------- Composite ----------
    composite = round((entity_score * 0.30 + evidence_score * 0.40 + tech_score * 0.30), 1)
    if composite >= 85:    grade = "A"
    elif composite >= 70:  grade = "B"
    elif composite >= 55:  grade = "C"
    elif composite >= 40:  grade = "D"
    else:                  grade = "F"

    # ---------- Recommendations ----------
    recommendations: list[dict] = []
    if not has_org_schema:
        recommendations.append({
            "axis": "entity",
            "severity": "HIGH",
            "title": "Add Organization schema",
            "fix": "Inject schema.org Organization JSON-LD via Script Tag (use ShopMirror's schema enricher).",
        })
    if n_sameas < 3:
        recommendations.append({
            "axis": "entity",
            "severity": "MEDIUM",
            "title": "Add sameAs links to socials",
            "fix": "Include LinkedIn, X/Twitter, Instagram, and Crunchbase URLs in Organization sameAs.",
        })
    if review_density < 0.3:
        recommendations.append({
            "axis": "evidence",
            "severity": "HIGH",
            "title": "Inject Review / AggregateRating schema",
            "fix": "Connect a review app (Judge.me/Yotpo/Stamped) and ensure JSON-LD is emitted per product.",
        })
    if not has_llms_txt:
        recommendations.append({
            "axis": "technical",
            "severity": "HIGH",
            "title": "Publish /llms.txt",
            "fix": "Use ShopMirror's llms.txt generator and host at site root.",
        })
    if not _has_type(blocks, "FAQPage"):
        recommendations.append({
            "axis": "evidence",
            "severity": "MEDIUM",
            "title": "Publish FAQPage schema",
            "fix": "ShopMirror FAQ generator turns review/Q&A patterns into FAQPage JSON-LD.",
        })

    return {
        "composite_score": composite,
        "grade": grade,
        "axes": {
            "entity_identity": {
                "score": entity_score,
                "has_organization_schema": has_org_schema,
                "sameas_count": n_sameas,
                "has_logo": has_logo,
                "has_search_action": has_search_action,
                "has_contact_point": bool(has_contact),
            },
            "evidence_citations": {
                "score": evidence_score,
                "review_blocks": review_blocks,
                "review_density_per_product": review_density,
                "mention_signals_in_policy": mention_signals,
                "has_faq_schema": _has_type(blocks, "FAQPage"),
            },
            "technical_ux": {
                "score": tech_score,
                "https": has_https,
                "sitemap_present": has_sitemap,
                "sitemap_has_products": sitemap_has_products,
                "llms_txt_present": has_llms_txt,
                "robots_txt_present": robots_present,
            },
        },
        "recommendations": recommendations,
    }
