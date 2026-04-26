"""
bot_audit.py — Audit robots.txt for AI crawler access.

Background: most merchants accidentally block GPTBot/ClaudeBot/PerplexityBot
through Cloudflare Bot Management or default robots.txt rules. This is the
single biggest silent killer of AI visibility.

Pure parser; no I/O.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# Bots that read your store to answer / cite during inference.
# Source: official docs from OpenAI, Anthropic, Perplexity, Google, Microsoft, Apple.
AI_BOTS: list[dict] = [
    # OpenAI
    {"name": "GPTBot",          "operator": "OpenAI",     "purpose": "training + search index"},
    {"name": "OAI-SearchBot",   "operator": "OpenAI",     "purpose": "ChatGPT Search index"},
    {"name": "ChatGPT-User",    "operator": "OpenAI",     "purpose": "live ChatGPT browsing"},
    # Anthropic
    {"name": "ClaudeBot",       "operator": "Anthropic",  "purpose": "training"},
    {"name": "Claude-User",     "operator": "Anthropic",  "purpose": "live Claude browsing"},
    {"name": "Claude-SearchBot","operator": "Anthropic",  "purpose": "Claude search"},
    # Perplexity
    {"name": "PerplexityBot",   "operator": "Perplexity", "purpose": "search index"},
    {"name": "Perplexity-User", "operator": "Perplexity", "purpose": "live retrieval"},
    # Google
    {"name": "Google-Extended", "operator": "Google",     "purpose": "Gemini training"},
    {"name": "GoogleOther",     "operator": "Google",     "purpose": "AI Mode + research"},
    # Microsoft
    {"name": "Bingbot",         "operator": "Microsoft",  "purpose": "Copilot index"},
    # Apple
    {"name": "Applebot",          "operator": "Apple",    "purpose": "Siri / Apple Intelligence"},
    {"name": "Applebot-Extended", "operator": "Apple",    "purpose": "Apple Intelligence training"},
    # Amazon
    {"name": "Amazonbot",       "operator": "Amazon",     "purpose": "Alexa / Rufus"},
    # Mistral
    {"name": "MistralAI-User",  "operator": "Mistral",    "purpose": "Le Chat browsing"},
    # DuckDuckGo
    {"name": "DuckAssistBot",   "operator": "DuckDuckGo", "purpose": "DuckAssist answers"},
    # Meta
    {"name": "FacebookBot",     "operator": "Meta",       "purpose": "Meta AI training"},
    {"name": "Meta-ExternalAgent", "operator": "Meta",    "purpose": "Meta AI live browsing"},
    # ByteDance
    {"name": "Bytespider",      "operator": "ByteDance",  "purpose": "Doubao training"},
]


@dataclass
class BotRule:
    user_agent: str
    is_allowed: bool         # site-wide allow when no Disallow:/* present
    blocked_paths: list[str] # explicit Disallow rules
    explicit_match: bool     # True if this UA appears literally in robots.txt


def _parse_robots(robots_txt: str) -> dict[str, BotRule]:
    """
    Parse robots.txt into a UA -> BotRule map. Wildcard '*' lives under key '*'.
    A bot's effective rule is its own block, falling back to '*' if absent.
    """
    rules: dict[str, BotRule] = {}
    current_uas: list[str] = []
    in_group = False

    if not robots_txt:
        return rules

    for raw in robots_txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            in_group = False
            continue

        if ":" not in line:
            continue
        directive, _, value = line.partition(":")
        directive = directive.strip().lower()
        value = value.strip()

        if directive == "user-agent":
            if not in_group:
                current_uas = []
                in_group = True
            current_uas.append(value)
            for ua in current_uas:
                rules.setdefault(ua, BotRule(user_agent=ua, is_allowed=True, blocked_paths=[], explicit_match=True))
        elif directive in ("disallow", "allow"):
            in_group = False
            for ua in current_uas:
                rule = rules.setdefault(ua, BotRule(user_agent=ua, is_allowed=True, blocked_paths=[], explicit_match=True))
                if directive == "disallow" and value:
                    rule.blocked_paths.append(value)
                    if value == "/":
                        rule.is_allowed = False
        elif directive == "crawl-delay":
            in_group = False
        else:
            in_group = False

    return rules


def _resolve_rule(ua: str, parsed: dict[str, BotRule]) -> BotRule:
    """Bot's specific rule, else fallback to '*'."""
    for key, rule in parsed.items():
        if key.lower() == ua.lower():
            return rule
    star = parsed.get("*")
    if star:
        return BotRule(user_agent=ua, is_allowed=star.is_allowed, blocked_paths=list(star.blocked_paths), explicit_match=False)
    return BotRule(user_agent=ua, is_allowed=True, blocked_paths=[], explicit_match=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def audit_bot_access(robots_txt: Optional[str]) -> dict:
    """
    Returns a structured report:
        {
            "robots_txt_present": bool,
            "bots": [
                {
                    "name": "GPTBot",
                    "operator": "OpenAI",
                    "purpose": "...",
                    "allowed": bool,
                    "explicit_match": bool,
                    "blocked_paths": [...],
                    "blocks_products": bool,
                    "blocks_homepage": bool,
                }
            ],
            "summary": {
                "total_bots_checked": int,
                "fully_allowed": int,
                "partially_blocked": int,
                "fully_blocked": int,
                "critical_blocks": [bot_name, ...]
            }
        }
    """
    parsed = _parse_robots(robots_txt or "")
    bots_out: list[dict] = []

    fully_allowed = 0
    partially_blocked = 0
    fully_blocked = 0
    critical_blocks: list[str] = []

    for spec in AI_BOTS:
        name = spec["name"]
        rule = _resolve_rule(name, parsed)
        blocks_products = any(
            re.match(re.escape(bp).replace(r"\*", ".*"), "/products/")
            or bp == "/" or bp.startswith("/products")
            for bp in rule.blocked_paths
        )
        blocks_homepage = any(bp == "/" for bp in rule.blocked_paths)

        if not rule.is_allowed or blocks_homepage:
            fully_blocked += 1
            critical_blocks.append(name)
            status = "BLOCKED"
        elif blocks_products or rule.blocked_paths:
            partially_blocked += 1
            status = "PARTIAL"
        else:
            fully_allowed += 1
            status = "ALLOWED"

        bots_out.append({
            "name": name,
            "operator": spec["operator"],
            "purpose": spec["purpose"],
            "status": status,
            "allowed": rule.is_allowed,
            "explicit_match": rule.explicit_match,
            "blocked_paths": rule.blocked_paths,
            "blocks_products": blocks_products,
            "blocks_homepage": blocks_homepage,
        })

    return {
        "robots_txt_present": bool(robots_txt),
        "bots": bots_out,
        "summary": {
            "total_bots_checked": len(AI_BOTS),
            "fully_allowed": fully_allowed,
            "partially_blocked": partially_blocked,
            "fully_blocked": fully_blocked,
            "critical_blocks": critical_blocks,
        },
    }


def suggested_robots_txt_additions(audit: dict) -> str:
    """
    Generate a robots.txt patch the merchant can paste in to allow all AI bots.
    Idempotent — safe to append.
    """
    lines = ["# --- ShopMirror: AI bot allowances ---"]
    for spec in AI_BOTS:
        lines.append(f"User-agent: {spec['name']}")
        lines.append("Allow: /")
        lines.append("")
    return "\n".join(lines).strip() + "\n"
