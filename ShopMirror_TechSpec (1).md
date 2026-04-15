
# ShopMirror — Technical Specification

**Development Reference Document for GitHub Copilot**

| Field | Detail |
|---|---|
| Product | ShopMirror — AI Representation Optimizer |
| Stack | Python 3.11 / FastAPI / React 18 / PostgreSQL 15 / LangGraph / LangChain / AWS EC2+RDS |
| LLM | Gemini 2.0 Flash via Google Cloud Vertex AI (structured JSON output only) |
| Key Libraries | httpx, BeautifulSoup4, LangGraph, LangChain, pydantic, asyncpg, gql |
| Build Window | 8 days |
| Read alongside | ShopMirror_PRD.md (product context and feature rationale) |

---

## 1. Project Directory Structure

> **Instruction for Copilot:** Create this exact directory structure before writing any code. Every file mentioned in this spec lives at the path shown here. Do not deviate from this structure.

```
shopmirror/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, routes, startup
│   │   ├── models/
│   │   │   ├── merchant.py            # MerchantData, Product, Policy dataclasses
│   │   │   ├── findings.py            # Finding, Pillar, AuditReport dataclasses
│   │   │   ├── fixes.py               # FixItem, FixPlan, FixResult dataclasses
│   │   │   └── jobs.py                # AnalysisJob, JobStatus dataclasses
│   │   ├── services/
│   │   │   ├── ingestion.py           # All Shopify data fetching
│   │   │   ├── heuristics.py          # 19 deterministic checks
│   │   │   ├── llm_analysis.py        # LLM batch call, Pydantic schemas
│   │   │   ├── perception_diff.py     # Merchant intent vs AI perception
│   │   │   ├── competitor.py          # Web search + competitor audit
│   │   │   ├── mcp_simulation.py      # Storefront MCP calls
│   │   │   ├── report_builder.py      # Assembles final report JSON
│   │   │   └── shopify_writer.py      # Admin GraphQL write operations
│   │   ├── agent/
│   │   │   ├── graph.py               # LangGraph state machine definition
│   │   │   ├── nodes.py               # Planner, Executor, Verifier, Reporter nodes
│   │   │   ├── tools.py               # All executor tools as LangChain tools
│   │   │   └── state.py               # StoreOptimizationState TypedDict
│   │   ├── db/
│   │   │   ├── connection.py          # asyncpg pool setup
│   │   │   ├── migrations/
│   │   │   │   └── 001_initial.sql    # All table definitions
│   │   │   └── queries.py             # All DB read/write functions
│   │   └── utils/
│   │       ├── retry.py               # Exponential backoff decorator
│   │       └── validators.py          # URL validation, Shopify detection
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── InputScreen.tsx        # URL + token + intent + competitor input
│   │   │   ├── ProgressScreen.tsx     # Animated step-by-step progress
│   │   │   ├── Dashboard.tsx          # 5-pillar summary + worst 5 products
│   │   │   ├── PerceptionDiff.tsx     # Intent vs perception table
│   │   │   ├── CompetitorPanel.tsx    # Competitor structural comparison
│   │   │   ├── MCPSimulation.tsx      # Question/answer display
│   │   │   ├── FindingsTable.tsx      # 19 checks, sortable, filterable
│   │   │   ├── AgentActivity.tsx      # Live agent step feed
│   │   │   ├── FixApproval.tsx        # Plan review + approve/reject per fix
│   │   │   ├── DiffViewer.tsx         # Before/after per fix
│   │   │   └── BeforeAfterReport.tsx  # Final summary
│   │   ├── api/
│   │   │   └── client.ts              # All API calls, polling logic
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── .env.example
└── docker-compose.yml                 # PostgreSQL local dev
```

---

## 2. Tech Stack

| Component | Technology | Version | Rationale |
|---|---|---|---|
| Backend API | FastAPI | 0.111+ | Async native, BackgroundTasks for job running, auto OpenAPI docs |
| Agent Framework | LangGraph | 0.2+ | State machine for optimization loop, graph interrupts for approval gate |
| LLM Orchestration | LangChain | 0.3+ | Tool definitions, LLM wrappers, explicitly in hackathon allowed stack |
| LLM Model | Gemini 2.0 Flash via Vertex AI (langchain-google-vertexai) | latest | Structured JSON output via response_schema, cheap, fast, available on Google Cloud |
| HTTP Client | httpx | 0.27+ | Async HTTP, used for all Shopify public endpoint fetching |
| HTML Parsing | BeautifulSoup4 | 4.12+ | JSON-LD extraction from raw HTML, no JS execution |
| GraphQL Client | gql + aiohttp | 3.5+ | Shopify Admin GraphQL API calls |
| Data Validation | Pydantic | 2.x | All LLM outputs, all API request/response shapes |
| Database | PostgreSQL 15 | 15+ | Job state, results storage, provided via AWS RDS |
| DB Driver | asyncpg | 0.29+ | Async PostgreSQL driver compatible with FastAPI |
| Frontend | React 18 + TypeScript | 18+ | Teammate's stack, component model fits UI requirements |
| UI Components | shadcn/ui + Tailwind CSS | latest | Pre-built components, fast styling, professional look |
| Infra | AWS EC2 + RDS | provided | Cognizant-provided, EC2 for backend, RDS for PostgreSQL |
| Container | Docker + docker-compose | latest | Local dev parity, production deployment |

### requirements.txt

```
fastapi==0.111.0
uvicorn[standard]==0.30.0
httpx==0.27.0
beautifulsoup4==4.12.3
lxml==5.2.2
gql==3.5.0
aiohttp==3.9.5
pydantic==2.7.0
asyncpg==0.29.0
google-cloud-aiplatform>=1.60.0
langchain==0.3.0
langchain-google-vertexai>=1.0.0
langgraph==0.2.0
python-dotenv==1.0.1
serpapi==0.1.5
```

---

## 3. Database Schema

### Table: analysis_jobs

```sql
CREATE TABLE analysis_jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  store_url       VARCHAR(512) NOT NULL,
  store_domain    VARCHAR(256),
  has_token       BOOLEAN DEFAULT FALSE,
  status          VARCHAR(32) DEFAULT 'queued',
  -- status values: queued | ingesting | auditing | simulating | complete | failed | awaiting_approval
  progress_step   VARCHAR(256),
  progress_pct    INTEGER DEFAULT 0,
  report_json     JSONB,
  fix_plan_json   JSONB,
  error_message   TEXT,
  created_at      TIMESTAMP DEFAULT NOW(),
  completed_at    TIMESTAMP
);
```

### Table: fix_backups

```sql
CREATE TABLE fix_backups (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id          UUID REFERENCES analysis_jobs(id),
  fix_id          VARCHAR(64) NOT NULL,
  product_id      VARCHAR(128),
  field_type      VARCHAR(64),
  -- field_type values: title | product_type | metafield | alt_text
  field_key       VARCHAR(128),
  original_value  TEXT,
  new_value       TEXT,
  shopify_gid     VARCHAR(256),
  applied_at      TIMESTAMP DEFAULT NOW(),
  rolled_back     BOOLEAN DEFAULT FALSE
);
```

### Report JSON Structure

The `report_json` column stores the complete analysis result:

```json
{
  "store_name": "string",
  "store_domain": "string",
  "ingestion_mode": "url_only | admin_token",
  "total_products": "number",
  "pillars": {
    "discoverability": { "score": "number", "checks_passed": "number", "checks_total": 4 },
    "completeness":    { "score": "number", "checks_passed": "number", "checks_total": 6 },
    "consistency":     { "score": "number", "checks_passed": "number", "checks_total": 3 },
    "trust_policies":  { "score": "number", "checks_passed": "number", "checks_total": 4 },
    "transaction":     { "score": "number", "checks_passed": "number", "checks_total": 2 }
  },
  "findings": "Finding[]",
  "worst_5_products": "ProductSummary[]",
  "perception_diff": "PerceptionDiff | null",
  "competitor_comparison": "CompetitorResult[]",
  "mcp_simulation": "MCPResult[] | null",
  "copy_paste_package": "CopyPasteItem[]"
}
```

### Finding Object Shape

```python
Finding {
  id: str                    # e.g. 'finding_D1_001'
  pillar: str                # 'Discoverability' | 'Completeness' | 'Consistency' | 'Trust_Policies' | 'Transaction'
  check_id: str              # 'D1' | 'C2' | 'Con1' | etc.
  check_name: str            # human-readable check name
  severity: str              # 'CRITICAL' | 'HIGH' | 'MEDIUM'
  weight: int                # 10 | 6 | 2
  title: str                 # short description
  detail: str                # why it matters for AI agents
  spec_citation: str         # source document being violated
  affected_products: list[str]
  affected_count: int
  impact_statement: str      # e.g. 'Affects 100% of category queries'
  fix_type: str              # 'auto' | 'copy_paste' | 'manual' | 'developer'
  fix_instruction: str       # exact steps to fix
  fix_content: str | None    # generated content if fix_type is copy_paste
}
```

---

## 4. API Specification

> **Contract Note:** This is the agreed API contract between backend and frontend. Frontend mocks these responses from Day 1 using hardcoded JSON in `api/client.ts`. Backend implements real logic. Integration happens Day 5.

### POST /analyze

Start a new analysis job. Returns immediately with job_id.

```
Request:
{
  "store_url": "string",           // required, e.g. 'example.myshopify.com'
  "admin_token": "string | null",  // optional, enables Mode B ingestion + fixes
  "merchant_intent": "string | null",
  "competitor_urls": "string[]"    // optional, max 2
}

Response 202:
{ "job_id": "string" }

Response 400:
{ "error": "Invalid Shopify URL | Store not accessible" }
```

### GET /jobs/{job_id}

Poll every 2 seconds until status is complete or failed.

```
Response (while processing):
{
  "status": "ingesting | auditing | simulating | awaiting_approval",
  "progress": { "step": "string", "pct": "number" },
  "report": null
}

Response (complete):
{
  "status": "complete",
  "progress": { "step": "Analysis complete", "pct": 100 },
  "report": "Report"
}

Response (failed):
{
  "status": "failed",
  "error": "string"
}
```

### GET /jobs/{job_id}/fix-plan

Returns planned fixes for merchant review. Only available when token was provided.

```
Response:
{
  "fixes": [
    {
      "fix_id": "string",
      "type": "classify_product_type | improve_title | fill_metafield | generate_alt_text",
      "product_id": "string",
      "product_title": "string",
      "field": "string",
      "current_value": "string | null",
      "proposed_value": "string",
      "reason": "string",
      "risk": "LOW",
      "reversible": true
    }
  ]
}
```

### POST /jobs/{job_id}/execute

Execute approved fixes. Triggers LangGraph agent run.

```
Request:
{ "approved_fix_ids": ["string"] }

Response 202:
{ "execution_job_id": "string" }
// Poll GET /jobs/{execution_job_id} for progress
```

### POST /jobs/{job_id}/rollback/{fix_id}

Rollback a single applied fix.

```
Response 200:
{ "status": "rolled_back", "field": "string", "restored_value": "string" }

Response 404:
{ "error": "Fix not found or already rolled back" }
```

### GET /jobs/{job_id}/before-after

Returns re-audit results after fix execution.

```
Response:
{
  "original_pillars": "PillarScores",
  "current_pillars": "PillarScores",
  "checks_improved": ["string"],
  "checks_unchanged": ["string"],
  "mcp_before": "MCPResult[] | null",
  "mcp_after": "MCPResult[] | null",
  "manual_action_items": "Finding[]"
}
```

---

## 5. Service Specifications

### 5.1 ingestion.py

Responsible for all data fetching. Called first in every analysis job. Returns a MerchantData object.

| Function | Inputs | Outputs | Notes |
|---|---|---|---|
| fetch_public_data(store_url) | Validated store URL | MerchantData (Mode A) | Fetches products.json, policies.json, robots.txt, sitemap.xml, llms.txt. Paginates products.json (250/page). |
| fetch_admin_data(store_url, token) | Store URL + Admin token | MerchantData (Mode B) | Admin GraphQL: metafields, SEO, taxonomy, inventory, image alt text. Merges with Mode A data. |
| crawl_product_pages(product_urls) | List of 5 product URLs | Dict[url, SchemaData] | httpx raw fetch, BeautifulSoup JSON-LD extraction. No JS execution. |
| detect_shopify(store_url) | Any URL | Boolean | Checks /products.json returns 200 with products key. Used for validation and competitor detection. |
| select_crawl_targets(products) | Product list | List[url] max 5 | Selects top 5 by variant count as crawl targets. |

**MerchantData Dataclass Fields**

| Field | Type | Source |
|---|---|---|
| store_domain | str | Parsed from input URL |
| store_name | str | Extracted from HTML title or meta |
| products | list[Product] | products.json paginated |
| collections | list[Collection] | collections.json |
| policies | Policies | policies.json |
| robots_txt | str | GET /robots.txt |
| sitemap_present | bool | GET /sitemap.xml status |
| sitemap_has_products | bool | Parsed sitemap content |
| llms_txt | str or None | GET /llms.txt |
| schema_by_url | dict[str, list] | Crawled JSON-LD blocks |
| price_in_html | dict[str, bool] | Raw HTML price check per URL |
| ingestion_mode | str | 'url_only' or 'admin_token' |
| metafields_by_product | dict[str, list] | Admin GraphQL (Mode B only) |
| seo_by_product | dict[str, dict] | Admin GraphQL (Mode B only) |
| inventory_by_variant | dict[str, dict] | Admin GraphQL (Mode B only) |

---

### 5.2 heuristics.py

All 19 deterministic checks. Zero LLM calls. Takes MerchantData, returns list of Finding objects.

| Function | Check ID | Returns |
|---|---|---|
| check_robot_crawlers(data) | D1 | Finding per blocked AI bot |
| check_sitemap(data) | D2 | Finding if absent or missing products |
| check_llms_txt(data) | D3 | Finding if absent |
| check_js_rendered_price(data) | D4 | Finding per product page where price not in HTML |
| check_product_type(data) | C1 | Finding with all affected product IDs |
| check_variant_option_names(data) | C3 | Finding with products having unnamed options |
| check_gtin_identifier(data) | C4 | Finding per product missing all identifiers |
| check_metafields(data) | C5 | Finding per product with empty key metafields (Mode B only) |
| check_image_alt_text(data) | C6 | Finding with coverage percentage |
| check_schema_price_consistency(data) | Con1 | Finding per page with price mismatch |
| check_schema_availability(data) | Con2 | Finding per page with availability mismatch |
| check_seo_consistency(data) | Con3 | Finding per product with inconsistent SEO title |
| check_refund_timeframe(data) | T1 | Finding if no days/number found in refund policy |
| check_shipping_regions(data) | T2 | Finding if no region names found in shipping policy |
| check_aggregate_rating(data) | T3 | Finding if AggregateRating absent from schema |
| check_offer_schema(data) | T4 | Finding if OfferShippingDetails or MerchantReturnPolicy absent |
| check_inventory_tracking(data) | A1 | Finding per untracked variant |
| check_oversell_risk(data) | A2 | Finding per variant with continue+tracked combination |
| run_all_checks(data) | all | list[Finding] sorted by severity then affected_count |

---

### 5.3 llm_analysis.py

Single batched LangChain call. Processes products in groups of 15. Uses Gemini 2.0 Flash via `langchain-google-vertexai` with Pydantic structured output via `response_schema`. Feeds Check C2 results back into heuristics output.

```python
class ProductAnalysis(BaseModel):
    product_id: str
    title_contains_category_noun: bool
    title_category_noun: Optional[str]  # what noun found or should be added
    description_has_material: bool
    description_has_use_case: bool
    description_has_specs: bool
    missing_vocabulary: list[str]  # max 3 items

# Cross-validation applied after LLM call:
# If description_has_material=True but no material keyword in text -> set False
# Material keywords: cotton, polyester, leather, wood, steel, wool,
#                    linen, plastic, ceramic, gold, silver, nylon, silk
```

---

### 5.4 perception_diff.py

| Function | When Called | LLM Calls | Output |
|---|---|---|---|
| get_store_perception(data, intent) | Every analysis | 1 | Store-level: intended_positioning, ai_perception, gap_reasons |
| get_product_perception(product, intent, findings) | Worst 5 products (paid) | 2 per product | ProductPerception: intended, ai_extracted, cannot_determine, root_finding_ids |

---

### 5.5 competitor.py

| Function | What It Does |
|---|---|
| find_competitors(merchant_data) | Searches for merchant's product category globally. Returns top 3 competitor URLs. |
| audit_competitor(url) | Runs subset of checks: D1-D4, C1, C4, T1, T4 only. Returns CompetitorAudit object. |
| build_comparison(merchant_findings, competitor_audits) | Produces side-by-side gap table showing what competitors have that merchant lacks. |

---

### 5.6 mcp_simulation.py

| Function | What It Does |
|---|---|
| check_mcp_available(store_domain) | GET {domain}/api/mcp, returns bool. If False, simulation is skipped gracefully. |
| generate_questions(merchant_data) | Builds 10 questions using real product names, categories, price brackets. |
| run_simulation(store_domain, questions, mode) | Posts each question to MCP endpoint. Free tier: 3 questions. Paid tier: 10 questions. |
| classify_response(question, response, ground_truth) | Returns ANSWERED, UNANSWERED, or WRONG. Maps WRONG to specific ground truth mismatch. |
| map_to_findings(mcp_results, findings) | Links each failure to the specific audit finding explaining why it failed. |

---

### 5.7 shopify_writer.py

All write operations to Shopify Admin GraphQL. Called only by agent/tools.py. Never called directly.

| Function | Shopify Mutation | Backup Created |
|---|---|---|
| write_product_type(gid, product_type, job_id) | productUpdate | Yes — original product_type |
| write_title(gid, title, job_id) | productUpdate | Yes — original title |
| write_metafield(product_gid, namespace, key, value, type, job_id) | metafieldsSet | Yes — null (new field, delete to rollback) |
| write_alt_text(image_gid, alt_text, job_id) | productImageUpdate | Yes — original alt text |
| rollback_fix(fix_id) | Appropriate mutation | N/A — restores backup |

---

## 6. LangGraph Agent Specification

### 6.1 State Definition (agent/state.py)

```python
class StoreOptimizationState(TypedDict):
    job_id: str
    store_data: MerchantData
    admin_token: str
    audit_findings: list[Finding]
    fix_plan: list[FixItem]           # all planned fixes
    approved_fix_ids: list[str]       # merchant-approved subset
    executed_fixes: list[FixResult]
    failed_fixes: list[FixResult]
    current_fix_id: str | None        # fix being processed right now
    retry_count: int                  # resets per fix, max 2
    iteration: int                    # total iterations, max 50
    verification_results: dict        # check_id -> bool after re-run
    manual_action_items: list[Finding]
    final_report: dict | None
```

### 6.2 Graph Nodes (agent/nodes.py)

| Node Function | Input State Fields | Output State Changes | Routing Logic |
|---|---|---|---|
| planner_node | audit_findings, executed_fixes, failed_fixes, iteration | current_fix_id, fix_plan (if first run) | If no approved fixes left: route to reporter. If iteration > 50: route to reporter. Else: route to executor. |
| approval_gate_node | fix_plan | Pauses graph (interrupt) | Graph interrupt. Resumes when POST /execute called with approved_fix_ids. |
| executor_node | current_fix_id, fix_plan, store_data, admin_token | executed_fixes or failed_fixes updated | Always routes to verifier after execution attempt. |
| verifier_node | current_fix_id, executed_fixes, store_data | verification_results, retry_count | If check passes: retry_count=0, route to planner. If fail and retry_count < 2: increment retry, route to executor. If retry_count >= 2: add to manual_action_items, route to planner. |
| reporter_node | all state fields | final_report | Terminal node. Assembles before/after comparison. Updates DB. No routing. |

### 6.3 Dependency Order (Planner Logic)

```python
DEPENDENCY_ORDER = [
    'classify_product_type',   # 1st: everything needs product classification
    'improve_title',           # 2nd: needs product_type context
    'fill_metafield',          # 3rd: extract from description
    'generate_alt_text',       # 4th: needs title + type context
    'generate_schema_snippet', # 5th: based on corrected data (copy-paste only)
    'suggest_policy_fix',      # 6th: least urgent, human must apply
]

# Within same level: sort by (severity_weight x affected_count) descending
# CRITICAL (weight 10) x 14 products = 140 > HIGH (weight 6) x 18 products = 108
```

### 6.4 Executor Tools (agent/tools.py)

| Tool | Confidence Gate | What Happens on Low Confidence |
|---|---|---|
| classify_product_type | Only writes if confidence='high' | Adds to manual_action_items with suggested value |
| improve_title | Always generates, shows diff | Merchant approves per-product in approval gate |
| fill_metafield | Cross-validates with keyword regex | Only writes verified fields, flags uncertain ones |
| generate_alt_text | Always generates | Shown as suggestion, written only on explicit approval |
| generate_schema_snippet | N/A — no write | Adds to copy_paste_package in final report |
| suggest_policy_fix | N/A — no write | Adds structured draft to copy_paste_package |

---

## 7. LLM Prompt Specifications

> **Rule for All Prompts:** Every LLM call uses structured output via Pydantic schema. System prompt always ends with: "Return ONLY valid JSON matching the provided schema. Do not include any text outside the JSON object." All prompts use temperature=0.

### 7.1 LLM Batch Analysis Prompt

```
SYSTEM:
You are a product data analyst for AI commerce optimization.
Analyze each product and determine if its title clearly identifies
the product category (what the product IS, not what it is like)
and whether the description contains structured, machine-readable attributes.
A category noun is a word like 'jacket', 'lamp', 'backpack', 'serum'.
Brand names alone are NOT category nouns.
Return ONLY valid JSON matching the ProductAnalysisBatch schema.

USER:
Analyze these {n} products: {product_list_json}
```

### 7.2 Store-Level Perception Prompt

```
SYSTEM:
You are simulating how an AI shopping agent perceives a Shopify store.
You will receive: (1) what the merchant intends to communicate,
(2) the store's actual machine-readable data quality summary.
Output the gap between intent and AI perception in plain language.
Return ONLY valid JSON matching the StorePerception schema.

USER:
Merchant intent: {merchant_intent}
Store audit summary: {audit_summary}
Worst performing pillar: {worst_pillar}
Most critical findings: {top_3_findings}
```

### 7.3 Product AI View Prompt (Call 2 of perception diff)

```
SYSTEM:
You are an AI shopping agent with access ONLY to the product data provided.
Do NOT use any external knowledge. Do NOT infer information not present.
If information is not in the data, state that you cannot determine it.
Return ONLY valid JSON matching the ProductAIView schema.

USER:
Product title: {title}
product_type field: {product_type}
Metafields available: {metafields}
Schema markup fields found: {schema_fields}
First 100 words of description: {description_start}
Describe this product as you would to a shopper asking about it.
```

### 7.4 Title Improvement Prompt

```
SYSTEM:
You improve Shopify product titles for AI shopping agent discoverability.
Rules you MUST follow:
1. The improved title must contain the product category noun (what it IS)
2. Preserve any brand name if present in the original title
3. Maximum 70 characters total
4. Do not add any claims not present in the product data
5. Do not change the meaning, only add clarity
Return ONLY valid JSON matching the TitleImprovement schema.

USER:
Original title: {current_title}
product_type: {product_type}
Key attributes found in description: {extracted_attributes}
Merchant brand voice: {merchant_intent}
```

### 7.5 Metafield Extraction Prompt

```
SYSTEM:
You extract structured product attributes from description text.
ONLY extract facts that are explicitly stated in the text.
Do NOT infer or guess any values. If a fact is not present, return null.
Return ONLY valid JSON matching the MetafieldExtraction schema.

USER:
Product: {product_title}
Description text: {full_description}
Extract: material, care_instructions, specifications, weight if present.
```

### 7.6 Product Type Classification Prompt

```
SYSTEM:
You classify Shopify products into their product type category.
Use the most specific, accurate category name possible.
Examples: 'Sleep Mask', 'Hiking Backpack', 'Desk Lamp', 'Face Serum'
Confidence: high = unambiguous from title alone.
            medium = requires description context.
            low = genuinely unclear even with description.
Return ONLY valid JSON matching the ProductTypeClassification schema.

USER:
Title: {title}
First 50 words of description: {description_start}
```

---

## 8. Environment Variables

### Backend (.env)

```
# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_MODEL=gemini-2.0-flash

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/shopmirror

# Search API (for competitor discovery)
SERPAPI_KEY=...    # OR use DDGS (DuckDuckGo, free, no key needed)

# App
ENVIRONMENT=development
LOG_LEVEL=INFO
MAX_PRODUCTS_PER_ANALYSIS=500
MAX_CRAWL_PAGES=5
FREE_TIER_MCP_QUESTIONS=3
PAID_TIER_MCP_QUESTIONS=10
FREE_TIER_PERCEPTION_PRODUCTS=0
PAID_TIER_PERCEPTION_PRODUCTS=5
```

### Frontend (.env)

```
VITE_API_BASE_URL=http://localhost:8000
VITE_POLLING_INTERVAL_MS=2000
```

---

## 9. 8-Day Build Plan

> **Split Principle:** Backend owner handles everything in `backend/` and `agent/`. Frontend owner handles everything in `frontend/`. The API contract in Section 4 is the only dependency. Frontend mocks all API responses from Day 1 using hardcoded JSON so both can work independently until integration day.

### Day 1 — Foundation

| Owner | Tasks | End of Day Milestone |
|---|---|---|
| Backend | Set up FastAPI project structure per Section 1. Set up PostgreSQL with docker-compose. Run 001_initial.sql. Implement ingestion.py: fetch_public_data() with pagination, robots.txt, sitemap, llms.txt, raw HTML crawl with BeautifulSoup JSON-LD extraction. Test on 3 real public Shopify stores. | ingestion.py complete and tested. Can ingest any public Shopify store in under 30 seconds. |
| Frontend | Set up React + TypeScript + Tailwind + shadcn/ui. Create api/client.ts with mock responses matching Section 4 shapes. Build InputScreen.tsx with all 4 input fields. Build ProgressScreen.tsx with animated steps. | Frontend renders mock data. Both screens work against mock API. |

### Day 2 — Core Audit

| Owner | Tasks | End of Day Milestone |
|---|---|---|
| Backend | Implement all 19 checks in heuristics.py. Each check is a separate function. Write unit tests for each. Implement POST /analyze and GET /jobs/{id} endpoints with BackgroundTasks. Wire ingestion + heuristics into job pipeline. | Full audit pipeline running. POST /analyze returns job_id. Polling shows real audit results. |
| Frontend | Build Dashboard.tsx with 5-pillar score display. Build FindingsTable.tsx with severity sorting and filtering. Wire to mock API. | Dashboard renders all findings from mock data. |

### Day 3 — LLM Layer + Perception Diff

| Owner | Tasks | End of Day Milestone |
|---|---|---|
| Backend | Implement llm_analysis.py with batch processing and Pydantic output. Feed C2 results back into heuristics. Implement perception_diff.py store-level call. Wire into job pipeline. Implement product gap scoring to identify worst 5. | LLM analysis running. Store perception diff in report. Worst 5 products identified. |
| Frontend | Build PerceptionDiff.tsx with intent vs perception side-by-side table. Build worst 5 product cards. | Perception diff renders from mock data. |

### Day 4 — Competitor + MCP

| Owner | Tasks | End of Day Milestone |
|---|---|---|
| Backend | Implement competitor.py: web search for competitors, detect_shopify(), lightweight structural audit on top 3 results. Implement mcp_simulation.py: availability check, question generation, MCP calls, response classification. Both gracefully degrade if unavailable. | Competitor comparison and MCP simulation in pipeline. Both skip gracefully on failure. |
| Frontend | Build CompetitorPanel.tsx. Build MCPSimulation.tsx with ANSWERED/UNANSWERED/WRONG display and finding links. | Both panels render from mock data. |

### Day 5 — Integration Day

| Owner | Tasks | End of Day Milestone |
|---|---|---|
| Both | Replace all mock responses in api/client.ts with real API calls. Fix all shape mismatches. Run full pipeline end-to-end: InputScreen → ProgressScreen → Dashboard → all panels. Test on dev store. | Complete analysis pipeline working end-to-end in browser. |

### Day 6 — LangGraph Fix Agent

| Owner | Tasks | End of Day Milestone |
|---|---|---|
| Backend | Implement agent/state.py, agent/nodes.py, agent/tools.py, agent/graph.py. Implement shopify_writer.py with all write operations and backup creation. Implement rollback endpoint. Wire fix plan generation into job pipeline. | LangGraph agent runs and executes fixes on dev store. Rollback works. |
| Frontend | Build AgentActivity.tsx with live step feed. Build FixApproval.tsx with diff viewer and approve/reject per fix. Build DiffViewer.tsx. | Fix approval flow works against mock agent steps. |

### Day 7 — Before/After + Polish

| Owner | Tasks | End of Day Milestone |
|---|---|---|
| Backend | Implement GET /jobs/{id}/before-after with re-audit after fixes. Implement copy-paste package assembly in report_builder.py. Test full loop: analyze → fix → re-audit on dev store. Verify before/after shows real improvement. | Full loop working: analyze → agent fixes → re-audit shows improvement. |
| Frontend | Build BeforeAfterReport.tsx. Wire agent activity to real polling. Polish all loading states and error states. | Complete UI flow works end-to-end. |

### Day 8 — Demo Prep + Buffer

| Owner | Tasks | End of Day Milestone |
|---|---|---|
| Both | Set up intentionally broken dev store. Run full demo flow. Fix anything that breaks. Deploy to AWS EC2 + RDS. Rehearse 3-minute demo script from PRD Section 9. | Deployed. Demo rehearsed. Submission ready. |

---

## 10. Dev Store Setup

> **Critical for Demo:** The demo store must be intentionally broken in specific ways so the tool finds real issues and the agent fixes real things. Set this up on Day 1.

### Steps to Create Dev Store

1. Create free Shopify Partner account at partners.shopify.com
2. Create development store from Partner Dashboard (no credit card required)
3. Add 15-20 products across 2-3 categories (e.g. sleep accessories, bags, home goods)
4. Create custom app in dev store admin for Admin API token — required scopes: read_products, write_products, read_content, write_content

### Intentional Breakage to Apply

| What to Break | How to Break It | Which Check It Fails |
|---|---|---|
| Product titles | Use brand names only: 'The Luna', 'Vertex', 'Apex Pro' | C2: no category noun |
| product_type field | Leave empty on all products | C1: product_type missing |
| Metafields | Leave custom.material empty on all products | C5: metafields empty |
| Variant option names | Leave as Option1, Option2 on 5 products | C3: unnamed options |
| Return policy | Write "We accept returns within a few weeks" | T1: no timeframe |
| Schema price | Manually inject wrong price in theme JSON-LD snippet | Con1: price mismatch |
| robots.txt | Add "User-agent: PerplexityBot / Disallow: /" to theme robots.txt.liquid | D1: crawler blocked |
| GTIN | Leave barcode field empty, leave vendor empty on 5 products | C4: no identifier |
| Inventory | Set 3 products to continue selling when out of stock | A2: oversell risk |
| Schema offer fields | Use basic theme without OfferShippingDetails or MerchantReturnPolicy | T4: offer schema missing |

### What Should Flip After Agent Runs

- C1, C2, C3: product_type + title + variant names (agent writes these)
- C5: metafields (agent extracts from descriptions and writes)
- Con1: schema price (schema snippet regenerated with correct price)
- D1: robots.txt (manual fix instruction provided, not auto-applied)
- T4: offer schema (copy-paste snippet provided, not auto-applied)

---

## 11. Error Handling Rules

| Scenario | Behaviour | User Sees |
|---|---|---|
| products.json returns 401 | Set catalog_not_public=True. Continue with HTML-only checks. | "Store catalog is private. Running checks on publicly available data only." |
| HTTP 429 from Shopify | Exponential backoff: 1s, 2s, 4s. Max 3 retries. Then mark partial. | Warning in findings: "Some products may not be included due to rate limiting." |
| MCP endpoint returns non-200 | Set mcp_available=False. Skip simulation entirely. | "Storefront MCP unavailable for this store. Simulation skipped." |
| Competitor URL not a Shopify store | detect_shopify() returns False. Skip that URL. | Competitor silently excluded. Others proceed. |
| LLM call returns malformed JSON | Retry once. If still malformed: skip that batch, mark products as unanalysed. | "LLM analysis unavailable" shown for those products in findings table. |
| Admin API write fails | Log to failed_fixes. Add to manual_action_items. Agent continues to next fix. | Finding shown in "Needs Manual Action" section with exact steps. |
| LangGraph iteration > 50 | Force route to reporter node. | Report generated with all completed fixes shown. Warning logged. |

---

## 12. Instructions for GitHub Copilot

### What to Build

- Backend is Python 3.11 + FastAPI. All service functions are async. All I/O uses httpx or asyncpg (never requests, never psycopg2).
- Every LLM call uses `langchain-google-vertexai` with `ChatVertexAI(model="gemini-2.0-flash", temperature=0)`. Use `with_structured_output(PydanticModel)` for all LLM calls. Never parse free text from LLM responses.
- All Shopify public data fetching uses httpx with a 30-second timeout and the retry decorator from utils/retry.py.
- Admin GraphQL calls use the gql library with aiohttp transport and the Admin token in Authorization header.
- LangGraph graph is defined in agent/graph.py. State is StoreOptimizationState TypedDict from agent/state.py.
- Database writes use asyncpg directly (no ORM). All queries are in db/queries.py.

### What NOT to Build

- Do NOT use requests library (use httpx). Do NOT use SQLAlchemy (use asyncpg). Do NOT use Celery (use FastAPI BackgroundTasks).
- Do NOT implement Shopify OAuth. The Admin token is provided directly by the merchant as a plain string.
- Do NOT write to Shopify theme files. Schema fixes are copy-paste outputs only.
- Do NOT auto-write policy text. Policy fixes are draft suggestions only.
- Do NOT use Playwright or Selenium. All HTML fetching is raw httpx + BeautifulSoup.
- Do NOT add vector databases. There are no embeddings in this project.
- Do NOT implement user authentication. This is a stateless URL-in, report-out tool for the hackathon.

### Code Quality Rules

- Every service function has a docstring stating: what it does, what it takes, what it returns.
- Every LLM prompt is defined as a constant string at the top of the file it is used in.
- Every Pydantic model has field descriptions for every field.
- All findings have spec_citation filled with the real source document name.
- Heuristics functions are pure functions: same input always produces same output. No side effects.
- The agent/tools.py tools are decorated with @tool from langchain. Each tool has a clear description string.
