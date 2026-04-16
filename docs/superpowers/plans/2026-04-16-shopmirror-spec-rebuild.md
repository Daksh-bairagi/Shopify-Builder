# ShopMirror Spec Rebuild — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update all spec files and already-built Python files to reflect the strategic changes that make ShopMirror technically accurate, Shopify-native, and hackathon-winning.

**Architecture:** Nine discrete tasks — two spec rewrites, one CLAUDE.md update, five Python file edits, one DB migration update, one DECISION_LOG append. Each task is self-contained and commits independently.

**Tech Stack:** Markdown spec files, Python 3.12 dataclasses, SQL, FastAPI route stubs.

---

## What Changes and Why (Summary)

### REMOVE from spec
- **D4** (price in raw HTML) — Shopify Liquid renders server-side; will pass 98% of stores; not diagnostic
- **T3** (AggregateRating schema) — Universal failure on Shopify themes; not diagnostic

### MODIFY in spec
- **D1** → Split into D1a (robots.txt, MEDIUM, accurate framing) + D1b (Shopify Catalog eligibility, CRITICAL)
- **C1** → Replace "product_type non-empty" with "Shopify Standard Taxonomy mapped" (real routing layer)
- **T4** → Change fix from copy-paste to autonomous via Shopify Script Tags API
- **MCP framing** → "Shopify's native AI agent endpoint" not "ChatGPT uses this"
- **Competitor feature** → Remove DuckDuckGo; replace with Shopify Search-based approach
- **Perception diff** → Ground "what AI sees" in actual MCP output, not LLM inference

### ADD to spec
**Shopify-native:**
- Shopify Standard Taxonomy auto-mapper (C1 replacement, biggest impact)
- Shopify Metafield Definitions creator (typed definitions, not raw string values)
- Script Tags schema injection (autonomous T4 fix)
- Shopify Bulk Operations ingestion path (for stores >150 products)
- Shopify Markets translation coverage check (new check slot)
- `script_tag_id` column in fix_backups table (rollback Script Tags)

**Market-proven:**
- AI Readiness Score (0–100) — headline metric judges expect
- Product Data Completeness Heatmap — visual gap display
- AI Query Match Simulator — evidence-of-impact feature
- Multi-Channel Compliance Dashboard — Google Shopping, Meta Catalog, Perplexity, Shopify Catalog
- Before/After AI Readiness Certificate — shareable, retention + viral

---

## Files Touched

| File | Action | What Changes |
|---|---|---|
| `ShopMirror_PRD (1).md` | Modify | Feature 2 check tables, Feature 5 competitor, Feature 6 MCP, new Features 9–13, demo script |
| `ShopMirror_TechSpec (1).md` | Modify | DB schema, API spec, service specs, agent tools, LLM prompts, build plan, directory structure |
| `CLAUDE.md` | Modify | What Is Already Built, model import paths |
| `shopmirror/backend/app/models/merchant.py` | Modify | Add taxonomy_by_product, markets_by_product, metafield_definitions fields |
| `shopmirror/backend/app/models/findings.py` | Modify | Add ChannelCompliance, QueryMatchResult, ai_readiness_score, channel_compliance, query_match_results to AuditReport |
| `shopmirror/backend/app/models/fixes.py` | Modify | Add script_tag_id to FixResult, add new fix types to comments |
| `shopmirror/backend/app/db/migrations/001_initial.sql` | Modify | Add script_tag_id column to fix_backups, add 002_add_script_tag.sql |
| `shopmirror/backend/app/db/queries.py` | Modify | Add script_tag_id param to save_fix_backup |
| `shopmirror/backend/app/main.py` | Modify | Add new route stubs for multi-channel, query-match endpoints |
| `DECISION_LOG.md` | Modify | Append new decisions for all strategic changes |

---

## Task 1: Update PRD — Feature 2 (19-Check Audit)

**Files:** Modify `ShopMirror_PRD (1).md`

- [ ] **Step 1: Replace Pillar 1 (Discoverability) check table**

Find and replace the entire "#### Pillar 1 — Discoverability (4 checks)" section with:

```markdown
#### Pillar 1 — Discoverability (5 checks)

| Check | What Is Tested | Severity if Fail | Source |
|---|---|---|---|
| D1a | robots.txt: PerplexityBot, GPTBot not blocked | MEDIUM per blocked bot | Perplexity/OpenAI crawler docs — affects web-index AI only, not Shopify Catalog |
| D1b | Shopify Catalog eligibility: product has taxonomy mapped, title non-empty, price set | CRITICAL | Shopify Catalog API docs — required fields for AI catalog inclusion |
| D2 | sitemap.xml present and contains /products/ URLs | HIGH | Shopify SEO documentation |
| D3 | llms.txt present at store root | MEDIUM | llms.txt emerging standard |
| D5 | Shopify Markets: active markets have translated product titles | HIGH | Shopify Markets API — AI agents serve international queries |
```

- [ ] **Step 2: Replace Pillar 2 (Completeness) check table**

Replace "#### Pillar 2 — Completeness (6 checks)" with:

```markdown
#### Pillar 2 — Completeness (6 checks)

| Check | What Is Tested | Severity if Fail | Source |
|---|---|---|---|
| C1 | Product mapped to Shopify Standard Product Taxonomy (category GID set) | CRITICAL | Shopify Standard Product Taxonomy 2024 — catalog routing layer |
| C2 | Product title contains a category noun (LLM check) | CRITICAL | GEO research: AI cannot classify brand-name-only titles |
| C3 | Variant options named (not Option1/Option2/Title) | HIGH | Shopify: unnamed options break agentic variant resolution |
| C4 | GTIN present OR (vendor non-empty AND SKU non-empty) | HIGH | Google Merchant Center: product identifier required for Shopping feed |
| C5 | Typed metafield definitions exist for material, care_instructions | HIGH | Shopify Search & Discovery uses typed definitions for filtering |
| C6 | Image alt text on 70%+ of product images | MEDIUM | AI crawler: alt text is primary image signal |
```

- [ ] **Step 3: Replace Pillar 4 (Trust and Policies) check table**

Replace "#### Pillar 4 — Trust and Policies (4 checks)" with:

```markdown
#### Pillar 4 — Trust and Policies (3 checks)

| Check | What Is Tested | Severity if Fail | Source |
|---|---|---|---|
| T1 | Refund policy contains explicit number of days (regex: \d+ days) | HIGH | AI constraint matching: 'within a few weeks' is unextractable |
| T2 | Shipping policy names at least one region or country | HIGH | AI location-filtered queries require explicit region data |
| T4 | OfferShippingDetails + hasMerchantReturnPolicy in schema Offer | CRITICAL | Shopify/IFG: products invisible to AI checkout without these — auto-fixed via Script Tags |
```

Note: T3 (AggregateRating) removed — universally absent from Shopify themes, not diagnostic.

- [ ] **Step 4: Update severity weighting note**

After the check tables, update the product scoring note to reflect 19 checks total (5+6+3+3+2=19).

- [ ] **Step 5: Commit**
```bash
git add "ShopMirror_PRD (1).md"
git commit -m "spec(prd): rebuild 19-check audit — remove D4/T3, add D1b/D5, upgrade C1 to taxonomy, reframe D1a"
```

---

## Task 2: Update PRD — Features 3–8 and Add Features 9–13

**Files:** Modify `ShopMirror_PRD (1).md`

- [ ] **Step 1: Update Feature 5 (Competitor Comparison)**

Replace the competitor discovery section text:

Old: "Finds competitors via web search — not merchant-provided URLs. Searches globally, not just Shopify stores."

Replace the entire Feature 5 section body with:

```markdown
#### 5: Competitor Discovery and Structural Comparison

Finds competitors via Shopify-native signals rather than general web search.

1. Query generation: search for merchant's Shopify Standard Taxonomy category globally using DuckDuckGo (free tier) or SerpAPI (when key configured)
2. Filter: apply detect_shopify() — only compare against verified Shopify stores; non-Shopify results silently excluded
3. Structural extraction: run lightweight audit on top 3 Shopify competitor stores (D1a, D1b, C1, C4, T1, T4 checks only)
4. Gap comparison: side-by-side table showing structural advantages competitors have

**Key framing change:** D1a framing is accurate — robots.txt affects web-index AI (Perplexity, Bing AI) not Shopify Catalog. Competitor comparison is structural data only. No claims about actual AI visibility performance.
```

- [ ] **Step 2: Update Feature 6 (MCP Simulation) framing**

Replace the Framing line at end of Feature 6:

Old: `"This is what Shopify's native agentic storefront interface returns when an AI agent asks these questions about your store. ChatGPT, Copilot, and Gemini use this same interface."`

New: `"This is Shopify's official AI agent endpoint — the interface Shopify exposes for AI shopping systems to query store data. We run real queries against it and show you exactly what any AI agent receives."`

Add after the question table:

```markdown
**Graceful Fallback:** If the MCP endpoint returns non-200, `mcp_available` is set to False and ShopMirror falls back to a structured simulation: Gemini answers the same 10 questions using ONLY the product's machine-readable fields (title, product_type, metafields, schema markup). Framed as "Simulated AI agent query" — never as real ChatGPT output.
```

- [ ] **Step 3: Add Feature 9 — AI Readiness Score**

After Feature 8 (Before/After Report), add:

```markdown
---

### Feature 9: AI Readiness Score (0–100)

A single weighted composite score across all 5 pillars, displayed prominently throughout the UI. Calculated at the end of every audit and re-calculated after agent fixes. Merchants track this number over time.

**Formula:**
- For each check: if PASS → full weight, if FAIL → 0
- Pillar weight contributions: Discoverability 20%, Completeness 30%, Consistency 20%, Trust_Policies 15%, Transaction 15%
- Normalize: (weighted_passes / weighted_total) × 100, rounded to nearest integer

**Display:** Large badge at top of Dashboard. Color: 0–39 red, 40–69 amber, 70–89 green, 90–100 blue.

**Demo moment:** Score animates from starting value to improved value after agent execution. "AI Readiness Score: 31 → 68."
```

- [ ] **Step 4: Add Feature 10 — Product Data Completeness Heatmap**

```markdown
---

### Feature 10: Product Data Completeness Heatmap

Visual grid — products on Y-axis, required fields on X-axis. Each cell colored:
- Red: field missing / check fails
- Amber: field present but below threshold
- Green: field present and passing

Required fields shown: title, taxonomy, product_type, GTIN/SKU, material metafield, image alt, schema markup.

Sorted by gap score descending — worst products at top. Clicking a cell links to the specific finding for that product+field combination.

**Why this wins demo:** Communicates scale of the problem in two seconds. A 50-product store with red cells across 6 columns is more visceral than a list of findings.
```

- [ ] **Step 5: Add Feature 11 — AI Query Match Simulator**

```markdown
---

### Feature 11: AI Query Match Simulator

Answers the question the current system cannot: "would my products actually appear if someone asked AI for them?"

**How it works:**
1. Merchant (or system) inputs a natural-language shopping query: "machine washable yoga mat under $50, eco-friendly"
2. Parser extracts structured attributes: {category: "yoga mat", washable: true, price_max: 50, sustainable: true}
3. For each product: check if machine-readable data satisfies each attribute (metafields, taxonomy, price, tags)
4. Output: "{N} of {total} products match this query. {M} fail because material metafield is empty."
5. After fixes: re-run same queries, show improvement

**3 default queries generated from merchant's actual taxonomy + price range.**
**Free tier: 1 query. Paid tier: 5 queries + custom query input.**

This is the evidence-of-impact feature: directly shows the causal link between structural fixes and query matching potential.
```

- [ ] **Step 6: Add Feature 12 — Multi-Channel Compliance Dashboard**

```markdown
---

### Feature 12: Multi-Channel Compliance Dashboard

AI shopping is five channels, not one. Single compliance view across all:

| Channel | Required Fields | Our Checks That Map |
|---|---|---|
| Shopify Catalog | taxonomy, title, price, inventory tracked | D1b, C1, Con1, A1, A2 |
| Google Shopping | GTIN or brand+MPN, category, price, availability | C4, C1, Con1, Con2 |
| Meta Catalog | product_type, price, image, description | C2, C6, Con1 |
| Perplexity Web | robots.txt open, sitemap, llms.txt | D1a, D2, D3 |
| ChatGPT Shopping | schema OfferShippingDetails, structured policies | T4, T1, T2 |

Each channel shows: READY / PARTIAL / BLOCKED with the specific blocking checks.

**Why this wins:** Every competitor does one channel. ShopMirror does all five in one scan — the "single pane of glass" no tool in the market provides at this price point.
```

- [ ] **Step 7: Add Feature 13 — Before/After AI Readiness Certificate**

```markdown
---

### Feature 13: Before/After AI Readiness Certificate

After agent execution and re-audit, generate a visual summary:
- Store name + domain
- Before score (badge) → After score (badge)
- Checks improved: N of 19
- Top 3 fixes applied (human-readable)
- Date of certification

**Exportable as:** Downloadable PNG (frontend canvas render) or shareable link.

**Business function:** Retention tool (merchants return to improve score) + viral distribution (merchants share in Shopify communities).
```

- [ ] **Step 8: Update Demo Script (Section 9)**

Replace the demo time table with:

```markdown
| Time | What You Say | What They See |
|---|---|---|
| 0:00-0:20 | "AI commerce grew 800% in 2025. Every Shopify store is theoretically in front of 800M ChatGPT users. Most will never get a single AI order — because their data doesn't pass the checks AI systems require." | Problem slide |
| 0:20-0:40 | "Enter store URL. No login required." | AI Readiness Score appears: 31/100 (red badge) |
| 0:40-1:00 | "Here's every product in the catalog. Every red cell is a field an AI agent cannot read." | Product Completeness Heatmap loads — most cells red |
| 1:00-1:15 | "Watch what happens when an AI agent actually queries this store." | MCP simulation: "I don't have material information for this product." UNANSWERED x 6 |
| 1:15-1:30 | "AI Query Match: zero of 23 products appear when someone asks for your top product category." | Query Match Simulator: 0/23 |
| 1:30-1:45 | "Five channels. Four blocked." | Multi-Channel Dashboard: Shopify Catalog BLOCKED, Google Shopping PARTIAL, Meta PARTIAL |
| 1:45-2:15 | "The agent plans fixes in dependency order. Taxonomy first — everything else depends on knowing what the product IS." | LangGraph agent: map_taxonomy → verify → inject_schema → verify → fill_metafields → verify |
| 2:15-2:30 | "AI Readiness Score: 31 → 68. AI Query Match: 19 of 23 products now match." | Score animates up. Heatmap turns green. |
| 2:30-3:00 | "Certificate generated. This is what $49/month buys a Shopify merchant." | Certificate shows +37 point improvement. |
```

- [ ] **Step 9: Commit**
```bash
git add "ShopMirror_PRD (1).md"
git commit -m "spec(prd): add features 9-13, update competitor/MCP/demo, ground narrative in Shopify APIs"
```

---

## Task 3: Update TechSpec — DB Schema + API Spec

**Files:** Modify `ShopMirror_TechSpec (1).md`

- [ ] **Step 1: Update fix_backups table in Section 3**

Add `script_tag_id` column to the fix_backups SQL block:

```sql
CREATE TABLE fix_backups (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id          UUID REFERENCES analysis_jobs(id),
  fix_id          VARCHAR(64) NOT NULL UNIQUE,
  product_id      VARCHAR(128),
  field_type      VARCHAR(64),
  -- field_type values: title | product_type | metafield | alt_text | taxonomy | script_tag
  field_key       VARCHAR(128),
  original_value  TEXT,
  new_value       TEXT,
  shopify_gid     VARCHAR(256),
  script_tag_id   VARCHAR(256),     -- Shopify script tag ID for Script Tags fixes (rollback via scriptTagDelete)
  applied_at      TIMESTAMP DEFAULT NOW(),
  rolled_back     BOOLEAN DEFAULT FALSE
);
```

- [ ] **Step 2: Update Report JSON structure in Section 3**

Add new fields to the report_json shape:

```json
{
  "store_name": "string",
  "store_domain": "string",
  "ingestion_mode": "url_only | admin_token",
  "total_products": "number",
  "ai_readiness_score": "number",
  "pillars": { ... },
  "findings": "Finding[]",
  "worst_5_products": "ProductSummary[]",
  "channel_compliance": "ChannelCompliance",
  "perception_diff": "PerceptionDiff | null",
  "mcp_simulation": "MCPResult[] | null",
  "query_match_results": "QueryMatchResult[]",
  "competitor_comparison": "CompetitorResult[]",
  "copy_paste_package": "CopyPasteItem[]"
}
```

Add new object shapes:

```python
ChannelCompliance {
  shopify_catalog: ChannelStatus   # { status: 'READY'|'PARTIAL'|'BLOCKED', blocking_check_ids: list[str] }
  google_shopping: ChannelStatus
  meta_catalog: ChannelStatus
  perplexity_web: ChannelStatus
  chatgpt_shopping: ChannelStatus
}

QueryMatchResult {
  query: str                       # natural language query
  matched_product_ids: list[str]
  total_products: int
  match_count: int
  failing_attributes: dict[str, int]  # attribute -> count of products missing it
}
```

- [ ] **Step 3: Update API spec GET /jobs/{job_id} response**

Add `ai_readiness_score` and `channel_compliance` to the complete response shape.

- [ ] **Step 4: Add new endpoint GET /jobs/{job_id}/query-match**

```
### GET /jobs/{job_id}/query-match

Run AI query matching against job's ingested product data.

Request params:
  query: string (required) — natural language shopping query

Response 200:
{
  "query": "string",
  "matched_product_ids": ["string"],
  "total_products": "number",
  "match_count": "number",
  "failing_attributes": { "material": 18, "washable": 22 }
}
```

- [ ] **Step 5: Commit**
```bash
git add "ShopMirror_TechSpec (1).md"
git commit -m "spec(techspec): update DB schema, report JSON, API endpoints for new features"
```

---

## Task 4: Update TechSpec — Service Specs + Agent Tools + Prompts

**Files:** Modify `ShopMirror_TechSpec (1).md`

- [ ] **Step 1: Update ingestion.py spec (Section 5.1)**

Add to MerchantData fields table:

| Field | Type | Source |
|---|---|---|
| taxonomy_by_product | dict[str, str] | Admin GraphQL — product.category GID (Mode B) |
| markets_by_product | dict[str, dict] | Admin GraphQL — productTranslations per market (Mode B) |
| metafield_definitions | list[dict] | Admin GraphQL — store-level metafieldDefinitions (Mode B) |

Add to function table:

| Function | Inputs | Outputs | Notes |
|---|---|---|---|
| fetch_bulk_products(store_url, token) | Store URL + Admin token | MerchantData (large catalog) | Uses Shopify Bulk Operations API. Called when total_products > 150. Creates bulk query job, polls until complete, downloads JSONL result. |

- [ ] **Step 2: Update heuristics.py spec (Section 5.2) — complete check list**

Replace the full function table with:

```
| Function | Check ID | Returns |
|---|---|---|
| check_robot_crawlers(data) | D1a | Finding per blocked AI bot — severity MEDIUM, accurate framing |
| check_catalog_eligibility(data) | D1b | Finding if taxonomy unmapped or required catalog fields missing — CRITICAL |
| check_sitemap(data) | D2 | Finding if absent or missing products |
| check_llms_txt(data) | D3 | Finding if absent |
| check_markets_translation(data) | D5 | Finding per active market missing product translations (Mode B only) |
| check_taxonomy_mapped(data) | C1 | Finding per product with no Shopify Standard Taxonomy GID |
| check_title_category_noun(data, llm_results) | C2 | Finding with products lacking category noun |
| check_variant_option_names(data) | C3 | Finding with products having unnamed options |
| check_gtin_identifier(data) | C4 | Finding per product missing all identifiers |
| check_metafield_definitions(data) | C5 | Finding if typed MetafieldDefinition absent for material, care_instructions (Mode B) |
| check_image_alt_text(data) | C6 | Finding with coverage percentage |
| check_schema_price_consistency(data) | Con1 | Finding per page with price mismatch |
| check_schema_availability(data) | Con2 | Finding per page with availability mismatch |
| check_seo_consistency(data) | Con3 | Finding per product with inconsistent SEO title (Mode B) |
| check_refund_timeframe(data) | T1 | Finding if no days/number found in refund policy |
| check_shipping_regions(data) | T2 | Finding if no region names found in shipping policy |
| check_offer_schema(data) | T4 | Finding if OfferShippingDetails or MerchantReturnPolicy absent |
| check_inventory_tracking(data) | A1 | Finding per untracked variant |
| check_oversell_risk(data) | A2 | Finding per variant with continue+tracked combination |
| run_all_checks(data, llm_results) | all | list[Finding] sorted by severity then affected_count |
```

- [ ] **Step 3: Add new service spec — query_matcher.py (Section 5.8)**

```markdown
### 5.8 query_matcher.py

Implements the AI Query Match Simulator. Deterministic attribute extraction from product machine-readable fields. No LLM calls.

| Function | What It Does |
|---|---|
| parse_query_attributes(query_text) | One LLM call (Gemini) → extracts structured attributes: {category, price_max, price_min, attributes: list[str]} |
| match_products(products, attributes, metafields_by_product) | For each product: check if taxonomy covers category, if price in range, if material metafield satisfies material attribute. Returns list of matched product_ids and per-attribute failure counts. |
| build_query_match_result(query, products, attributes, matches) | Returns QueryMatchResult dataclass |
| run_default_queries(merchant_data) | Generates 1 (free) or 5 (paid) queries from merchant taxonomy + price range. Runs match_products for each. |
```

- [ ] **Step 4: Update shopify_writer.py spec (Section 5.7)**

Add to function table:

| Function | Shopify Mutation | Backup Created |
|---|---|---|
| write_taxonomy(gid, taxonomy_gid, job_id) | productUpdate (category field) | Yes — original taxonomy GID or null |
| inject_schema_script(store_domain, token, schema_json, job_id) | scriptTagCreate | Yes — script_tag_id stored for rollback |
| delete_schema_script(script_tag_id) | scriptTagDelete | N/A — rollback action |
| create_metafield_definition(token, namespace, key, type) | metafieldDefinitionCreate | No — idempotent, safe to re-run |

- [ ] **Step 5: Update agent/tools.py spec (Section 6.4)**

Add to executor tools table:

| Tool | Confidence Gate | What Happens on Low Confidence |
|---|---|---|
| map_taxonomy | Only writes if Gemini returns taxonomy_gid from valid Shopify taxonomy list | Adds to manual_action_items with suggested category |
| inject_schema_script | Always executes when T4 fails | Generates complete JSON-LD block, injects via scriptTagCreate, stores script_tag_id in fix_backups |
| create_metafield_definitions | Always executes | Idempotent — creates typed definitions for material, care_instructions if not exist |

- [ ] **Step 6: Add taxonomy classification LLM prompt (Section 7)**

```markdown
### 7.7 Taxonomy Classification Prompt

```
SYSTEM:
You classify Shopify products to the official Shopify Standard Product Taxonomy.
Return the most specific matching category from the taxonomy.
Use the full path format: "Apparel & Accessories > Clothing > Tops & T-Shirts"
Confidence: high = clear match from title alone. medium = needs description context. low = unclear.
Return ONLY valid JSON matching the TaxonomyClassification schema.

USER:
Product title: {title}
product_type hint: {product_type}
First 30 words of description: {description_start}
Match to the Shopify Standard Product Taxonomy.
```
```

- [ ] **Step 7: Update Directory Structure (Section 1)**

Add `query_matcher.py` to the services list in the directory tree:
```
│   │   ├── services/
│   │   │   ├── ingestion.py
│   │   │   ├── heuristics.py
│   │   │   ├── llm_analysis.py
│   │   │   ├── perception_diff.py
│   │   │   ├── competitor.py
│   │   │   ├── mcp_simulation.py
│   │   │   ├── query_matcher.py       # NEW: AI Query Match Simulator
│   │   │   ├── report_builder.py
│   │   │   └── shopify_writer.py
```

Add new frontend components to directory tree:
```
│   │   ├── components/
│   │   │   ├── InputScreen.tsx
│   │   │   ├── ProgressScreen.tsx
│   │   │   ├── Dashboard.tsx           # Now shows AI Readiness Score badge
│   │   │   ├── ReadinessScore.tsx      # NEW: 0-100 score badge with animation
│   │   │   ├── HeatmapGrid.tsx         # NEW: product × field completeness grid
│   │   │   ├── MultiChannelDashboard.tsx  # NEW: 5-channel compliance view
│   │   │   ├── QueryMatchSimulator.tsx  # NEW: query input + match results
│   │   │   ├── ReadinessCertificate.tsx # NEW: before/after certificate
│   │   │   ├── PerceptionDiff.tsx
│   │   │   ├── CompetitorPanel.tsx
│   │   │   ├── MCPSimulation.tsx
│   │   │   ├── FindingsTable.tsx
│   │   │   ├── AgentActivity.tsx
│   │   │   ├── FixApproval.tsx
│   │   │   ├── DiffViewer.tsx
│   │   │   └── BeforeAfterReport.tsx
```

- [ ] **Step 8: Update 8-Day Build Plan (Section 9)**

Update Day 2 backend tasks to include schemas.py and new check implementations.
Update Day 3 to include query_matcher.py.
Update Day 6 to include Script Tags injection tool and taxonomy tool.
Update Day 7 to include Certificate component and MultiChannelDashboard.

Replace the day plan table with:

```markdown
### Day 2 — Core Audit

| Owner | Tasks | End of Day Milestone |
|---|---|---|
| Backend | Implement schemas.py (all Pydantic request/response shapes). Implement all 19 checks in heuristics.py — each check is a separate function. Implement POST /analyze and GET /jobs/{id} endpoints with BackgroundTasks. Wire ingestion + heuristics into job pipeline. Implement AI Readiness Score calculation in report_builder.py. | Full audit pipeline running. Score appears in response. |
| Frontend | Build Dashboard.tsx with ReadinessScore badge (animated, color-coded). Build FindingsTable.tsx. Wire to mock API. | Dashboard shows score + findings from mock data. |

### Day 3 — LLM Layer + Perception Diff + Query Match

| Owner | Tasks | End of Day Milestone |
|---|---|---|
| Backend | Implement llm_analysis.py. Implement perception_diff.py. Implement query_matcher.py with parse_query_attributes + match_products. Implement multi-channel compliance scoring in report_builder.py. | Score, perception diff, query match, channel compliance all in report. |
| Frontend | Build HeatmapGrid.tsx. Build MultiChannelDashboard.tsx. Build QueryMatchSimulator.tsx. | All three components render from mock data. |

### Day 4 — Competitor + MCP

| Owner | Tasks | End of Day Milestone |
|---|---|---|
| Backend | Implement competitor.py (Shopify-verified stores only). Implement mcp_simulation.py with graceful fallback to Gemini simulation. | Competitor comparison and MCP simulation in pipeline. |
| Frontend | Build CompetitorPanel.tsx. Build MCPSimulation.tsx. | Both panels render from mock data. |

### Day 6 — LangGraph Fix Agent (Updated)

| Owner | Tasks | End of Day Milestone |
|---|---|---|
| Backend | Implement agent/state.py, nodes.py, tools.py, graph.py. Wire AsyncPostgresSaver on same day as graph (not deferred). Implement shopify_writer.py — include write_taxonomy(), inject_schema_script(), create_metafield_definitions(). Implement rollback endpoint with script_tag_id support. | Agent runs, Script Tags injection works, taxonomy mapping works, rollback works. |
| Frontend | Build AgentActivity.tsx, FixApproval.tsx, DiffViewer.tsx. | Fix approval flow works against mock agent steps. |

### Day 7 — Before/After + Certificate + Polish

| Owner | Tasks | End of Day Milestone |
|---|---|---|
| Backend | Implement GET /jobs/{id}/before-after with re-audit. Implement copy-paste package. Test full loop on dev store. | Full loop: analyze → fix → re-audit showing real improvement. |
| Frontend | Build BeforeAfterReport.tsx. Build ReadinessCertificate.tsx (canvas render + PNG export). Wire agent activity to real polling. Polish all states. | Complete UI flow with certificate export. |
```

- [ ] **Step 9: Update requirements.txt in Section 2**

Note addition of `duckduckgo-search` (already in requirements.txt per CLAUDE.md) and ensure `gql[aiohttp]` is present.

- [ ] **Step 10: Commit**
```bash
git add "ShopMirror_TechSpec (1).md"
git commit -m "spec(techspec): update service specs, agent tools, prompts, build plan for new features"
```

---

## Task 5: Update CLAUDE.md

**Files:** Modify `CLAUDE.md`

- [ ] **Step 1: Update Model Import Paths section**

Add new model types to the import path documentation:

```python
# Add to findings imports:
from app.models.findings import (Finding, PillarScore, AuditReport, PerceptionDiff,
    ProductPerception, MCPResult, CompetitorAudit, CompetitorResult, CopyPasteItem,
    ProductSummary, ChannelCompliance, ChannelStatus, QueryMatchResult)
```

- [ ] **Step 2: Update What Is Already Built section**

Add note about new files needed:
```
- `backend/app/services/query_matcher.py` — EMPTY FILE — AI Query Match Simulator
- `backend/app/db/migrations/002_add_script_tag.sql` — NEEDS CREATION — adds script_tag_id to fix_backups
```

Update the models section to reflect new fields in merchant.py and findings.py.

- [ ] **Step 3: Add new hard rules**

Add to Hard Rules:
```
- All Script Tags injection uses scriptTagCreate Admin GraphQL mutation — never inject via theme files
- All taxonomy writes use the Shopify Standard Product Taxonomy GID format — never write raw strings to the category field
- AsyncPostgresSaver MUST be wired on the same day as LangGraph graph — never deferred separately
```

- [ ] **Step 4: Update Known Deferred Items**

Remove the LangGraph checkpointing deferral note (it's now same-day as graph build).

- [ ] **Step 5: Commit**
```bash
git add CLAUDE.md
git commit -m "spec(claude): update model imports, hard rules, deferred items for rebuild"
```

---

## Task 6: Update merchant.py — Add New Fields

**Files:** Modify `shopmirror/backend/app/models/merchant.py`

- [ ] **Step 1: Add taxonomy_by_product, markets_by_product, metafield_definitions to MerchantData**

Current MerchantData ends at `inventory_by_variant`. Add three new fields:

```python
@dataclass
class MerchantData:
    store_domain: str
    store_name: str
    products: list[Product]
    collections: list[Collection]
    policies: Policies
    robots_txt: str
    sitemap_present: bool
    sitemap_has_products: bool
    llms_txt: Optional[str]
    schema_by_url: dict[str, list]
    price_in_html: dict[str, bool]
    ingestion_mode: str
    metafields_by_product: dict[str, list]
    seo_by_product: dict[str, dict]
    inventory_by_variant: dict[str, dict]
    taxonomy_by_product: dict[str, str]          # product_id -> Shopify taxonomy GID (Mode B)
    markets_by_product: dict[str, dict]          # product_id -> {market_id: {title_translated: bool, desc_translated: bool}}
    metafield_definitions: list[dict]            # store-level typed MetafieldDefinition objects (Mode B)
```

- [ ] **Step 2: Add default values so existing code doesn't break**

All three new fields need `field(default_factory=...)` since existing callers don't pass them yet:

```python
    taxonomy_by_product: dict[str, str] = field(default_factory=dict)
    markets_by_product: dict[str, dict] = field(default_factory=dict)
    metafield_definitions: list[dict] = field(default_factory=list)
```

Add `from dataclasses import dataclass, field` if `field` not already imported (it is — check line 3).

- [ ] **Step 3: Commit**
```bash
git add shopmirror/backend/app/models/merchant.py
git commit -m "feat(models): add taxonomy_by_product, markets_by_product, metafield_definitions to MerchantData"
```

---

## Task 7: Update findings.py — Add New Types + AuditReport Fields

**Files:** Modify `shopmirror/backend/app/models/findings.py`

- [ ] **Step 1: Add ChannelStatus and ChannelCompliance dataclasses**

Add after `CopyPasteItem`:

```python
@dataclass
class ChannelStatus:
    status: str                        # 'READY' | 'PARTIAL' | 'BLOCKED'
    blocking_check_ids: list[str]      # which check_ids cause the status


@dataclass
class ChannelCompliance:
    shopify_catalog: ChannelStatus
    google_shopping: ChannelStatus
    meta_catalog: ChannelStatus
    perplexity_web: ChannelStatus
    chatgpt_shopping: ChannelStatus


@dataclass
class QueryMatchResult:
    query: str                          # natural language query text
    matched_product_ids: list[str]
    total_products: int
    match_count: int
    failing_attributes: dict[str, int]  # attribute -> count of products missing it
```

- [ ] **Step 2: Update AuditReport to include new fields**

Add `ai_readiness_score`, `channel_compliance`, and `query_match_results` to AuditReport:

```python
@dataclass
class AuditReport:
    store_name: str
    store_domain: str
    ingestion_mode: str
    total_products: int
    ai_readiness_score: float                    # 0–100 composite score
    pillars: dict[str, PillarScore]
    findings: list[Finding]
    worst_5_products: list[ProductSummary]
    channel_compliance: ChannelCompliance
    perception_diff: Optional[PerceptionDiff]
    mcp_simulation: Optional[list[MCPResult]]
    query_match_results: list[QueryMatchResult]
    competitor_comparison: list[CompetitorResult]
    copy_paste_package: list[CopyPasteItem]
```

- [ ] **Step 3: Commit**
```bash
git add shopmirror/backend/app/models/findings.py
git commit -m "feat(models): add ChannelCompliance, QueryMatchResult, ai_readiness_score to findings"
```

---

## Task 8: Update fixes.py + DB Migration + queries.py

**Files:** Modify `shopmirror/backend/app/models/fixes.py`, create `shopmirror/backend/app/db/migrations/002_add_script_tag.sql`, modify `shopmirror/backend/app/db/queries.py`

- [ ] **Step 1: Update FixItem type comment and add new fix types**

In `fixes.py`, update the `type` field comment:

```python
@dataclass
class FixItem:
    fix_id: str
    type: str   # 'classify_product_type' | 'improve_title' | 'fill_metafield' |
                # 'generate_alt_text' | 'map_taxonomy' | 'inject_schema_script' |
                # 'create_metafield_definitions' | 'generate_schema_snippet' | 'suggest_policy_fix'
    product_id: str
    product_title: str
    field: str
    current_value: Optional[str]
    proposed_value: str
    reason: str
    risk: str
    reversible: bool
```

- [ ] **Step 2: Add script_tag_id to FixResult**

```python
@dataclass
class FixResult:
    fix_id: str
    success: bool
    error: Optional[str]
    shopify_gid: Optional[str]
    script_tag_id: Optional[str]     # Stored when fix_type is 'inject_schema_script' — used for rollback
    applied_at: Optional[datetime]
```

- [ ] **Step 3: Create migration 002**

Create `shopmirror/backend/app/db/migrations/002_add_script_tag.sql`:

```sql
-- Migration 002: add script_tag_id to fix_backups for Script Tags rollback support
ALTER TABLE fix_backups
  ADD COLUMN IF NOT EXISTS script_tag_id VARCHAR(256);

-- Update field_type comment — now includes 'taxonomy' and 'script_tag'
COMMENT ON COLUMN fix_backups.field_type IS
  'title | product_type | metafield | alt_text | taxonomy | script_tag';
```

- [ ] **Step 4: Update save_fix_backup in queries.py**

Add `script_tag_id` parameter:

```python
async def save_fix_backup(
    job_id: str,
    fix_id: str,
    product_id: str | None,
    field_type: str,
    field_key: str | None,
    original_value: str | None,
    new_value: str | None,
    shopify_gid: str | None,
    script_tag_id: str | None = None,
) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO fix_backups
            (job_id, fix_id, product_id, field_type, field_key,
             original_value, new_value, shopify_gid, script_tag_id)
        VALUES
            ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        job_id, fix_id, product_id, field_type, field_key,
        original_value, new_value, shopify_gid, script_tag_id,
    )
```

- [ ] **Step 5: Commit**
```bash
git add shopmirror/backend/app/models/fixes.py
git add shopmirror/backend/app/db/migrations/002_add_script_tag.sql
git add shopmirror/backend/app/db/queries.py
git commit -m "feat(db): add script_tag_id to fix_backups, new fix types for taxonomy and schema injection"
```

---

## Task 9: Update main.py Route Stubs + DECISION_LOG

**Files:** Modify `shopmirror/backend/app/main.py`, `DECISION_LOG.md`

- [ ] **Step 1: Update main.py route stub comments**

Replace the route comment block with:

```python
# Route implementations (to be added per day plan):
#   POST /analyze                      — Day 2, schemas: AnalyzeRequest, AnalyzeResponse
#   GET  /jobs/{id}                    — Day 2, schemas: JobStatusResponse
#   GET  /jobs/{id}/query-match        — Day 3, schemas: QueryMatchRequest, QueryMatchResponse
#   GET  /jobs/{id}/fix-plan           — Day 6, schemas: FixPlanResponse
#   POST /jobs/{id}/execute            — Day 6, schemas: ExecuteRequest, ExecuteResponse
#   POST /jobs/{id}/rollback/{fix_id}  — Day 6, schemas: RollbackResponse
#   GET  /jobs/{id}/before-after       — Day 7, schemas: BeforeAfterResponse
# All request/response shapes live in app/schemas.py
```

- [ ] **Step 2: Append new decisions to DECISION_LOG.md**

Add under a new `## Strategic Rebuild (Day 2+)` heading:

```markdown
## Strategic Rebuild — Post-Analysis Corrections

- **Replaced D1 "AI invisibility" framing with two accurate checks (D1a + D1b)** — D1a correctly flags robots.txt as MEDIUM (web-index AI only, not Shopify Catalog). D1b is the real CRITICAL check: Shopify Catalog eligibility via taxonomy + required fields. Original framing was factually wrong for Shopify's architecture.

- **Replaced C1 (product_type string check) with Shopify Standard Taxonomy mapping** — Shopify's 2024 taxonomy is the actual routing layer for Shopify Catalog, Google Shopping, and Meta Catalog. A non-empty product_type string has no structural meaning; a taxonomy GID does. All taxonomy writes use Shopify's productUpdate mutation with the category field.

- **Removed D4 (price in raw HTML) and T3 (AggregateRating)** — Both universally pass (D4) or fail (T3) on Shopify stores, making them non-diagnostic. Check slots reallocated to D1b and D5 (Markets translation).

- **T4 fix upgraded from copy-paste to Script Tags injection** — Shopify's scriptTagCreate Admin API injects JSON-LD schema into every storefront page without theme modification. Fully reversible via scriptTagDelete. script_tag_id stored in fix_backups for rollback. This turns the most CRITICAL finding into the most autonomous fix.

- **AsyncPostgresSaver wired same day as LangGraph graph (Day 6)** — Previous deferral was a documented risk; approval gate interrupts require persistent graph state. Building both together eliminates the multi-worker race condition.

- **Added AI Readiness Score (0–100) as headline metric** — Weighted composite across 5 pillars. Every credible SaaS tool has a headline score. Judges and merchants need one number to anchor the value proposition.

- **Added Multi-Channel Compliance Dashboard** — Shopify Catalog, Google Shopping, Meta Catalog, Perplexity Web, ChatGPT Shopping each map to specific checks. No competitor tool provides this at this price point.

- **Added AI Query Match Simulator as evidence-of-impact feature** — Closes the causal chain: structural fixes → more products match real AI shopping queries. Deterministic attribute matching from machine-readable fields. No LLM calls in the matching loop.
```

- [ ] **Step 3: Create empty query_matcher.py service file**

```bash
touch shopmirror/backend/app/services/query_matcher.py
```

- [ ] **Step 4: Commit everything**
```bash
git add shopmirror/backend/app/main.py
git add shopmirror/backend/app/services/query_matcher.py
git add DECISION_LOG.md
git commit -m "spec: update route stubs, add query_matcher service file, log all strategic decisions"
```

---

## Self-Review

**Spec coverage check:**
- D4 removed ✓ | T3 removed ✓ | D1 split into D1a + D1b ✓
- C1 → Taxonomy ✓ | T4 → Script Tags autonomous ✓
- MCP framing updated ✓ | Competitor updated ✓
- AI Readiness Score ✓ | Heatmap ✓ | Query Match ✓ | Multi-Channel ✓ | Certificate ✓
- DB script_tag_id ✓ | AsyncPostgresSaver same-day ✓
- Bulk Operations spec ✓ | Metafield Definitions ✓ | Markets check ✓

**Placeholder scan:** No TBDs. All code blocks complete.

**Type consistency:**
- `ChannelCompliance` defined in Task 7, referenced in Task 3 report JSON ✓
- `QueryMatchResult` defined in Task 7, referenced in Task 4 query_matcher spec ✓
- `script_tag_id` added to `FixResult` (Task 8), `fix_backups` table (Task 8), `save_fix_backup` (Task 8) ✓
- `taxonomy_by_product` added to `MerchantData` (Task 6), referenced in heuristics check_catalog_eligibility ✓
