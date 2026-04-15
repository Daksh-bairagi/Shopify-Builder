# ShopMirror — Product Requirements Document

**Observability Infrastructure for Agentic Commerce Readiness**

| Field | Detail |
|---|---|
| Product | ShopMirror |
| Document Type | Product Requirements Document (PRD) |
| Version | 1.0 |
| Hackathon | Kasparro Agentic Commerce Hackathon |
| Track | Track 5 — AI Representation Optimizer |
| Team Size | 2 members |
| Build Window | 8 days (Days 1–8 of 15-day total) |
| Stack | Python / FastAPI / React / PostgreSQL / LangGraph / LangChain / Google Cloud Vertex AI |

---

## 1. Executive Summary

> **The Problem in One Paragraph**
> Shopify has solved connectivity to AI shopping platforms. Every eligible store now appears in Shopify Catalog and is theoretically discoverable by ChatGPT, Copilot, and Gemini. But connectivity is not visibility. A store with incomplete product data, missing structured attributes, inconsistent schema markup, and vague policies remains invisible to AI agents even after Agentic Storefronts is enabled. Merchants have no way to see this gap, no way to measure it, and no way to close it. ShopMirror is built to solve exactly this.

ShopMirror is a merchant-facing diagnostic and optimization agent for Shopify stores. It audits a store against the documented requirements of real AI shopping systems, identifies every structural gap causing AI invisibility, shows merchants the gap between how they intend to be represented and how AI agents currently perceive them, benchmarks them against competitors who are winning AI recommendations in their category, and autonomously fixes what it can while providing precise instructions for everything else.

This is not an SEO tool. This is not a generic AI content generator. This is observability infrastructure for the agentic commerce era — the layer between a merchant's store and the AI agents that increasingly mediate their customers' purchase decisions.

### 1.1 The One-Line Pitch

> An agentic AI system that audits Shopify merchant product data against AI shopping platform requirements, identifies every structural gap causing AI invisibility, and fixes them autonomously — turning products that AI agents skip into products AI agents recommend.

### 1.2 Why This Exists Now

Three things happened in 2025-2026 that make this product urgent:

- Shopify activated Agentic Storefronts by default for all eligible US merchants on March 24, 2026. Every paid Shopify store's products are now theoretically in front of ChatGPT's 800 million weekly users. Most stores will never see a single AI-attributed order because their data quality does not meet the requirements for AI agent matching.
- AI-driven traffic to Shopify stores grew 693% during the 2025 holiday season. The channel is real, growing, and already affecting merchant revenue distribution.
- No tool exists that addresses this at the product data level for Shopify merchants. OmniSEO, Profound, Goodie, and similar tools track brand mentions for content marketers. Nobody fixes Shopify product data structures for AI agent consumption.

---

## 2. Problem Definition

### 2.1 Root Cause Analysis

The real problem is not that merchants have bad data. It is that merchants wrote their product data for human browsers, not for AI agents. These are fundamentally different audiences with fundamentally different requirements.

A human browser can read "Premium amazing soft elegant vibe" and understand it is a clothing item. An AI agent cannot classify this product, cannot match it to a category query, and will not recommend it. The merchant does not know this is happening.

| Failure Layer | What Goes Wrong | Real World Impact |
|---|---|---|
| Findability | AI crawlers blocked by robots.txt, price only in JS, no sitemap | Product pages never indexed by AI shopping systems |
| Classifiability | Title has no category noun, product_type field empty | AI cannot route product to any category query |
| Constraint Extraction | Material not in metafields, return window not explicit, variant options unnamed | AI cannot answer pre-purchase questions, drops product |
| Data Consistency | Schema price differs from actual price, availability contradicts inventory | AI shows wrong information, erodes shopper trust |
| Trust Signals | No schema ratings, policy too vague, no FAQ coverage | AI deprioritises merchant vs competitors with richer signals |
| Transaction Readiness | Inventory untracked, oversell policy enabled | AI-initiated transactions fail on delivery, worst outcome |

### 2.2 Stakeholder Pain

**The Merchant**
- Cannot see how AI agents perceive their store — no feedback loop exists
- Losing AI recommendation share to competitors with structurally cleaner data without knowing why
- Shopify Agentic Storefronts is enabled but generating zero orders — cause unknown
- No actionable tool exists to diagnose or fix this

**The Shopper**
- AI agents confidently recommend incorrect information about products
- Gets shown wrong prices, incorrect availability, or incomplete specs
- Clicks through from AI recommendation to find product description does not match what agent said

**Kasparro / Platform**
- AI recommendation quality depends entirely on merchant data quality
- Poor merchant data degrades the entire agentic commerce ecosystem
- No tooling exists to help merchants meet the structural requirements

---

## 3. Product Overview

### 3.1 What ShopMirror Does

ShopMirror runs as a two-phase system. Phase one is diagnosis: it reads the store, runs 19 deterministic checks across 5 pillars, finds every structural gap, calculates a weighted priority score per product, and identifies the worst performing products as evidence. Phase two is remediation: a LangGraph-powered optimization agent plans fixes in dependency order, executes autonomous writes to Shopify with merchant approval, verifies each fix worked, and provides precise copy-paste instructions for everything it cannot write automatically.

### 3.2 User Workflow

| Step | What Merchant Does | What ShopMirror Does |
|---|---|---|
| 1 | Enters Shopify store URL | Validates URL, detects Shopify store |
| 2 | Optionally pastes Admin API token | Ingests full catalog via Admin GraphQL (richer data) |
| 3 | Optionally enters merchant intent statement | Used to compare intended vs actual AI perception |
| 4 | Optionally enters 1-2 competitor store URLs | Runs same audit on competitors for benchmarking |
| 5 | Clicks Analyze | Runs full ingestion + 19-check audit + LLM batch + competitor check |
| 6 | Reviews store-level findings | Sees 5-pillar pass/fail, worst 5 products, perception diff, competitor gap |
| 7 | Reviews fix plan (if token provided) | Sees dependency-ordered plan, each fix with diff preview |
| 8 | Approves fixes | LangGraph agent executes approved fixes, verifies each one |
| 9 | Reviews before/after report | Sees which checks moved from FAIL to PASS, what still needs manual action |
| 10 | Gets copy-paste instructions | Schema snippets, policy drafts, FAQ templates ready to use |

### 3.3 Tiered Model

**Free Tier (no token required)**
Full 19-check structural audit on entire catalog. Store-level AI perception summary. Competitor structural comparison. Copy-paste instructions and fix guides for all findings. No LLM calls on individual products. Cost per analysis: under $0.05.

**Paid Tier (Admin token required)**
Everything in free tier PLUS: worst 5 product perception diff (before/after AI view). Storefront MCP experience simulation. LangGraph autonomous fix execution. Re-audit verification after fixes. Cost per analysis: under $0.50.

---

## 4. Feature Specifications

### Feature 1: Data Ingestion

Foundation layer. Runs always. Two modes depending on what merchant provides.

**Mode A — URL Only**
- products.json (paginated, all products, max 250 per page)
- collections.json
- policies.json (refund, shipping, privacy)
- robots.txt (plain HTTP fetch)
- sitemap.xml (presence + product URL check)
- llms.txt (presence check)
- Raw HTML of 5 product pages via httpx (no JavaScript execution) — extracts JSON-LD schema blocks, meta tags, checks if price appears in raw source

**Mode B — URL + Admin Token (adds via Admin GraphQL)**
- Full metafields per product across all namespaces
- SEO fields per product (metaTitle, metaDescription)
- Shopify standard product taxonomy category
- Inventory per variant (tracked/untracked/policy setting)
- Image alt text for all product images
- Search engine listing data

**Edge Cases**
- products.json returns 0: mark catalog_not_public, run HTML-only checks
- Store password protected (401): flag store_private, still run robots.txt and homepage schema
- Rate limit (429): exponential backoff, max 3 retries, then graceful partial result
- Which 5 pages to crawl: top 5 products by variant count (proxy for importance)

---

### Feature 2: 19-Check Structural Audit (5 Pillars)

> **Design Principle:** Zero LLM calls. Pure deterministic Python. Every check maps to a published specification from Shopify documentation, schema.org, or OpenAI/Google published AI commerce requirements. Every finding is binary pass/fail with a cited source.

#### Pillar 1 — Discoverability (4 checks)

| Check | What Is Tested | Severity if Fail | Source |
|---|---|---|---|
| D1 | robots.txt: OAI-SearchBot, GPTBot, PerplexityBot, GoogleOther not blocked | CRITICAL per blocked bot | OpenAI GPTBot documentation |
| D2 | sitemap.xml present and contains /products/ URLs | HIGH | Shopify SEO documentation |
| D3 | llms.txt present at store root | MEDIUM | llms.txt emerging standard |
| D4 | Product price appears in raw HTML (not JS-injected) | HIGH | AI crawler JS limitation research |

#### Pillar 2 — Completeness (6 checks)

| Check | What Is Tested | Severity if Fail | Source |
|---|---|---|---|
| C1 | product_type field non-empty on all products | CRITICAL | Shopify Catalog: required for category routing |
| C2 | Product title contains a category noun (LLM check) | CRITICAL | GEO research: AI cannot classify brand-name-only titles |
| C3 | Variant options named (not Option1/Option2/Title) | HIGH | Shopify: unnamed options break agentic variant resolution |
| C4 | GTIN present OR (vendor non-empty AND SKU non-empty) | HIGH | OpenAI ACP spec: product identifier required |
| C5 | Key metafields populated: custom.material, custom.care_instructions | HIGH | ChatGPT: pulls specs from metafields, not description prose |
| C6 | Image alt text on 70%+ of product images | MEDIUM | AI crawler: alt text is primary image signal |

#### Pillar 3 — Consistency (3 checks)

| Check | What Is Tested | Severity if Fail | Source |
|---|---|---|---|
| Con1 | Schema.org price matches products.json price (within $0.01) | CRITICAL | AI shows shoppers wrong price — trust destruction |
| Con2 | Schema availability matches actual inventory state | CRITICAL | Failed agentic transactions from stale availability |
| Con3 | SEO title/description consistent with product title (Mode B only) | MEDIUM | Cross-surface consistency for AI aggregation |

#### Pillar 4 — Trust and Policies (4 checks)

| Check | What Is Tested | Severity if Fail | Source |
|---|---|---|---|
| T1 | Refund policy contains explicit number of days (regex: \d+ days) | HIGH | AI constraint matching: 'within a few weeks' is unextractable |
| T2 | Shipping policy names at least one region or country | HIGH | AI location-filtered queries require explicit region data |
| T3 | Schema.org AggregateRating present on product pages | MEDIUM | AI ranking: review signals affect recommendation priority |
| T4 | OfferShippingDetails + hasMerchantReturnPolicy in schema Offer | CRITICAL | IFG/Shopify: products invisible to AI checkout without these |

#### Pillar 5 — Agentic Transaction Readiness (2 checks)

| Check | What Is Tested | Severity if Fail | Source |
|---|---|---|---|
| A1 | inventory_management not null on variants (inventory tracked) | HIGH | Untracked inventory means agent cannot verify availability |
| A2 | inventory_policy is not 'continue' when inventory_management is 'shopify' | CRITICAL | Oversell risk: agent confirms stock, transaction fails on delivery |

#### Severity Weighting for Product Scoring

| Severity | Weight | Meaning |
|---|---|---|
| CRITICAL | 10 | Blocks AI inclusion entirely or causes active misinformation |
| HIGH | 6 | Reduces AI ranking or prevents answering common queries |
| MEDIUM | 2 | Reduces conversion after inclusion, lower priority |

Product gap score = sum of (weight × failed_checks) for that product. Top 5 products by gap score = worst performers shown in paid tier.

---

### Feature 3: LLM Batch Analysis

Supports Check C2 (title category noun detection) and provides attribute presence flags. Single batched call per 15 products using Gemini 2.0 Flash via Google Cloud Vertex AI with Pydantic structured output. Zero free-text responses.

**Output Schema Per Product**

| Field | Type | Purpose |
|---|---|---|
| product_id | string | Links result to product |
| title_contains_category_noun | boolean | Check C2 pass/fail |
| title_category_noun | string or null | What noun was found or should be added |
| description_has_material | boolean | Cross-validated against material keyword regex |
| description_has_use_case | boolean | Feeds into perception diff |
| description_has_specs | boolean | Feeds into perception diff |
| missing_vocabulary | list[string] max 3 | e.g. ['material', 'occasion', 'size range'] |

**Cross-Validation Rule:** If description_has_material = true but no material keyword found by regex (cotton, polyester, leather, wood, steel, wool, linen, plastic, ceramic, gold, silver, nylon, silk), override to false and flag as uncertain. Prevents LLM hallucination from propagating into audit findings.

---

### Feature 4 + 5: Perception Diff and Competitor Comparison

#### 4A: Store-Level Perception Summary (Free Tier)

One LLM call. Merchant provides intent statement in a single text field before analysis. If skipped, intent is inferred from store name, collections, and tags (flagged as inferred).

- Input A: merchant_intent (what they typed, or inferred)
- Input B: store-level audit findings aggregated
- Output: two strings — "How you want to be seen" and "How AI currently sees you"
- Output: gap_summary explaining top 3 reasons for the gap

#### 4B: Worst 5 Product Perception Diff (Paid Tier)

Two LLM calls per product (10 total for 5 products). Products selected by highest gap score from Feature 2.

- Call 1: what merchant intends this product to communicate (uses merchant_intent + product data)
- Call 2: what AI can actually extract (uses ONLY machine-readable fields: title, product_type, metafields, schema markup, first 100 words of description)
- Output: side-by-side diff table showing merchant intent vs AI perception with root finding links

#### 5: Competitor Discovery and Structural Comparison

Finds competitors via web search — not merchant-provided URLs. Searches globally, not just Shopify stores.

1. Query generation: search for merchant's top product_type + category globally
2. Competitor detection: identify top 3-5 results that have structured product data
3. Structural extraction: run lightweight audit on competitor stores (D1-D4, C1, C4, T1, T4 checks only)
4. Gap comparison: side-by-side table showing what competitors have that merchant lacks

Framing: "These stores appear when someone searches for your products. Here is what structural advantages they have."

Important: comparison is structural data only. No claims about their actual AI visibility performance.

---

### Feature 6: Storefront MCP Experience Simulation

Every Shopify store has a built-in MCP endpoint at `{store}.myshopify.com/api/mcp`. No authentication required. This is the actual interface AI agents use to query the store. ShopMirror connects to this endpoint and asks real shopping questions, capturing exactly what an AI agent experiences.

**Question Generation** — 10 questions from real merchant data (3 free, 10 paid):

| Question Template | What It Tests | Maps To Check |
|---|---|---|
| What {category} do you sell? | Product classification | C1, C2 |
| What material is the {top_product} made from? | Attribute extractability | C5 |
| Do you have anything under ${price_bracket}? | Price data availability | Con1 |
| What is your return policy? | Policy clarity | T1 |
| How long does shipping take? | Shipping information | T2 |
| Does the {top_product} come in different sizes? | Variant data completeness | C3 |
| Do you ship internationally? | Region coverage | T2 |
| Is the {top_product} currently in stock? | Inventory accuracy | A1, A2 |
| Can I return a sale item? | Policy specificity | T1 |
| What makes your products different? | Brand differentiation | C5 |

**Response Classification:**
- ANSWERED: response contains relevant, accurate, verifiable information
- UNANSWERED: response says it does not have the information (correct but missing)
- WRONG: response contains a verifiable factual error vs ground truth data
- Each classification maps to specific audit findings explaining why

Framing: "This is what Shopify's native agentic storefront interface returns when an AI agent asks these questions about your store. ChatGPT, Copilot, and Gemini use this same interface."

---

### Feature 7: LangGraph Optimization Agent

> **Design Philosophy:** Single planner node + tool-based execution + verification loop. Not multi-agent. The intelligence is in dependency-aware ordering and self-verification, not in having many agents with fancy names.

#### LangGraph Graph Structure

| Node | Role | Decision Made |
|---|---|---|
| Planner | Reads current audit state, decides next fix | Which fix has highest impact given dependencies |
| Approval Gate | Pauses graph, shows merchant the diff | Graph interrupt — continues only on merchant approval |
| Executor | Runs the chosen tool | One tool per iteration, never bulk |
| Verifier | Re-runs the specific check just addressed | Pass: back to Planner. Fail: retry once then flag |
| Reporter | Produces final before/after summary | Runs when all auto-fixable issues resolved or flagged |

#### Fix Dependency Order

The planner follows this order. It does not deviate unless a dependency is already satisfied:

1. product_type classification (everything depends on knowing what the product IS)
2. Title improvement (needs product_type context for good category noun)
3. Metafield population (extract from description, AI can now answer spec questions)
4. Image alt text generation (uses title + product_type context)
5. Schema JSON-LD snippet generation (based on now-corrected product data, copy-paste only)
6. Policy improvement suggestions (draft text, merchant must review and apply)

#### Executor Tools

| Tool | What It Does | Write Type | Reversible |
|---|---|---|---|
| classify_product_type | LLM classifies from title+description. Pydantic: {type, confidence}. Only writes if confidence=high | Admin GraphQL productUpdate | Yes — backup saved |
| improve_title | LLM adds category noun, preserves brand name, max 70 chars. Shows diff first | Admin GraphQL productUpdate | Yes — original in metafield |
| fill_metafield | Extracts material/care/specs from description. Cross-validates with regex | Admin GraphQL metafieldsSet | Yes — delete to revert |
| generate_alt_text | LLM generates descriptive alt text. Returns suggestions for approval | Admin GraphQL (on approval) | Yes |
| generate_schema_snippet | Produces complete JSON-LD block with OfferShippingDetails + MerchantReturnPolicy. Copy-paste only | None (copy-paste output) | N/A |
| suggest_policy_fix | Analyzes current policy, generates structured replacement. Draft only | None (copy-paste output) | N/A |

#### Rollback Mechanism
- Before every write: original value saved to `shopmirror.backup.[field]` metafield
- Rollback endpoint: `POST /fixes/{job_id}/rollback/{fix_id}`
- Restores original value via same Admin GraphQL endpoint
- Policy/schema suggestions have no rollback needed (no auto-write)

#### Verification Loop

After each tool execution, the Verifier re-runs only the specific check(s) that fix addressed.
- If check now passes → Planner moves to next priority
- If check still fails → retry once with adjusted approach
- If retry fails → flag for manual action, Planner moves on
- Maximum 2 retries per fix. No infinite loops.

---

### Feature 8: Before/After Report

Runs after all agent iterations complete. Re-runs full 19-check audit against updated store data.

- Per-pillar: checks passing before vs after
- Per-product: gap score before vs after for worst 5
- MCP simulation re-run: which UNANSWERED questions are now ANSWERED
- Manual action list: precise instructions for every unfixed finding
- Copy-paste package: all generated schema snippets, policy drafts, FAQ templates in one section

---

## 5. Explicit Scope Exclusions

These were considered and deliberately excluded. Do not revisit them during the build.

| Feature | Why Excluded |
|---|---|
| Real API probe calling (ChatGPT/Perplexity APIs) | Non-deterministic output, cannot do before/after, $1-6 per analysis at scale, TOS grey area |
| Semantic embedding / cosine similarity scoring | Thresholds are invented, hard to explain, judges will ask calibration source |
| Ghost Shopper personas | Gimmicky without hard methodology, MCP simulation achieves same goal more honestly |
| Two-model Judge & Jury (Gemini + GPT) | $0.01 savings not worth two provider integrations and extra failure modes |
| Multi-agent LangGraph (4+ agents) | Fake complexity, shared state bugs, harder to explain, planner+tools achieves same result |
| Direct theme mutation for schema | Liquid template variability makes this fragile, copy-paste snippet is safer |
| Auto-writing policy text | Legal content, never auto-generate, always draft-and-review |
| Historical tracking | Needs persistent user accounts, post-launch feature |
| Shopify App Store / OAuth flow | Partner approval takes weeks, custom app token is the correct hackathon approach |
| Playwright headless browser | Shopify SSR means raw HTML has everything needed, Playwright adds 3s latency per page |
| Image vision analysis on all products | $4-12 per analysis for medium store, alt text keyword check achieves same finding |

---

## 6. Success Metrics

### For the Hackathon Demo

| Metric | Target | How Measured |
|---|---|---|
| Checks passing after agent run | At least 8/19 improvement on demo store | Re-audit after fix execution |
| MCP questions answered after fixes | At least 3 previously UNANSWERED now ANSWERED | MCP re-run comparison |
| Time to complete full analysis | Under 3 minutes for 20-product dev store | Stopwatch during demo |
| Fix execution time | Under 60 seconds for 10 products | Stopwatch during demo |
| Zero demo-breaking errors | No crashes, graceful degradation on any failure | Live demo |

### For Real-World Validity

| Metric | Target | Rationale |
|---|---|---|
| Cost per free analysis | Under $0.05 | Sustainable at any subscription price |
| Cost per paid analysis | Under $0.50 | Profitable at $29+/month |
| False positive rate on checks | Under 10% | Deterministic checks have defined pass/fail |
| LLM cross-validation catch rate | Prevents hallucination propagation | Material regex cross-check on LLM extraction |

---

## 7. Competitive Positioning

| Capability | OmniSEO | Profound | Goodie | ShopMirror |
|---|---|---|---|---|
| Tracks AI visibility | Yes | Yes | Yes | Yes |
| Gives optimization playbooks | Yes (content strategy) | Yes | Yes | Yes (product data specific) |
| Shopify product-level analysis | No | No | No | Yes |
| Uses real AI shopping infrastructure (MCP) | No | No | No | Yes |
| Shows perception vs intent gap | No | No | No | Yes |
| Competitor comparison | Yes (brand mentions) | Yes | No | Yes (structural data) |
| Autonomous fixes via Admin API | No | No | No | Yes |
| Before/after verification | No | No | No | Yes |
| Target customer | Enterprise content teams | Enterprise brands | Consumer brands | Shopify merchants |
| Pricing | $hundreds/month | Enterprise | Enterprise | $49/month target |

> **The Unique Position:** Every competitor measures brand mentions and provides content strategy advice to marketing teams. ShopMirror is the only tool that operates at the product data level, uses Shopify's own infrastructure for simulation, executes fixes autonomously, and verifies they worked.

---

## 8. Business Model

### Pricing Tiers

| Tier | Price | What Is Included |
|---|---|---|
| Free | $0 | Full 19-check audit, store-level perception summary, competitor comparison, copy-paste instructions |
| Pro | $49/month | Everything free + worst 5 product diffs, MCP simulation, autonomous fix execution, re-audit verification |
| Agency | $149/month | Pro features across unlimited stores, bulk analysis, white-label report export |

### Market Size
- 4+ million active Shopify merchants globally
- 0.1% adoption at $49/month = $2.4M ARR
- 1% adoption at $49/month = $24M ARR
- AI-driven traffic to retail sites grew 805% year-over-year in 2025

---

## 9. Demo Script (3 Minutes)

**Setup:** Dev store with intentionally broken data — brand-name-only titles, empty product_type fields, no metafields, vague policies, schema price mismatches, PerplexityBot blocked in robots.txt.

| Time | What You Say | What They See |
|---|---|---|
| 0:00-0:20 | "Merchants are invisible to AI shopping agents and they don't know why. AI-driven traffic grew 800% in 2025. Most of it is going to competitors. We show you why and fix it." | Problem slide |
| 0:20-0:40 | "Enter store URL. No login required. Analyzing now." | Progress bar: ingesting → auditing → simulating |
| 0:40-1:10 | "This store passes 4 of 19 checks. Here is what an AI agent sees when it tries to shop here." | MCP simulation: "I don't have material information for this product." |
| 1:10-1:40 | "Here is how this store wants to be seen vs how AI currently sees it. And here is the competitor winning recommendations in their category." | Perception diff table + competitor gap table |
| 1:40-2:10 | "The agent planned 8 fixes in dependency order. We approved them. Watch it execute." | LangGraph agent running live: classify → verify → improve_title → verify → fill_metafields → verify |
| 2:10-2:30 | "Re-audit: 14 of 19 checks now passing. MCP simulation: 6 of 10 questions now answered." | Before/after comparison + copy-paste package |
| 2:30-3:00 | "This is what Kasparro's vision of agentic commerce readiness looks like as a merchant tool." | Architecture slide + business model |
