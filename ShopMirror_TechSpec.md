# ShopMirror — Technical Specification

**Engineering Reference Document**

| Field | Detail |
|---|---|
| Product | ShopMirror — AI Representation Optimizer for Shopify |
| Version | 2.0 (April 2026 — post-implementation revision) |
| Stack | Python 3.12 / FastAPI / React 18 / TypeScript / PostgreSQL 15 / LangGraph / LangChain / Google Cloud Vertex AI / AWS EC2 + RDS |
| LLM | Gemini 2.0 Flash via Google Cloud Vertex AI (`with_structured_output` only — no free-text parsing) |
| Key Libraries | httpx, BeautifulSoup4, lxml, asyncpg, gql + aiohttp, pydantic 2, langchain, langchain-google-vertexai, langgraph, duckduckgo-search, serpapi |
| Read alongside | `ShopMirror_PRD.md` (product context and feature rationale) |

> **How to read this document.** Section 1 is the canonical directory layout — every file mentioned anywhere in this spec lives at the path shown there. Section 2 is the runtime stack and dependency manifest. Section 3 is the database schema and the JSON shapes that flow over the wire. Section 4 is the API surface — every endpoint, every header, every error path. Sections 5–6 are the service and agent specs. Section 7 documents the LLM prompts. Sections 8–11 cover environment, error handling, security, and the operational checklist. The companion PRD covers the same surfaces from a product perspective.

---

## 1. Architectural Overview

> **Judge-facing summary.** This document is intentionally written to show how the shipped system actually behaves, especially when something goes wrong.
>
> - **System architecture:** Browser -> FastAPI backend -> PostgreSQL, with Shopify, Gemini, and search providers called as external HTTP services.
> - **Real data flow:** ingest store data -> run deterministic checks -> run a bounded LLM pass only where language interpretation helps -> assemble report -> optionally execute approved fixes -> verify against live Shopify state -> re-audit.
> - **Where AI stops and deterministic code starts:** LLMs are used only for ambiguous language tasks such as attribute extraction, perception analysis, taxonomy suggestion, and draft generation. Deterministic code handles scoring, rule checks, query matching, eligibility logic, fix routing, Shopify writes, verification, rollback, and all user-facing state transitions.
> - **Why we drew that line:** if the task affects correctness, money, reversibility, or trust, the model is not allowed to decide it alone. The model may suggest; code must validate, constrain, or verify.
> - **Failure handling philosophy:** if Shopify is unavailable, the system falls back to the best public-data audit it can still perform. If the LLM returns malformed output, we retry once and then mark that block unavailable instead of guessing. If a write fails, the fix is surfaced as failed or manual rather than counted as complete.
> - **What this should signal to judges:** we optimized for a system we could defend under questioning, not for a diagram that only looks complete on paper.

### 1.1 Current System Architecture (C4-style Container Diagram)

The shipped system is a 3-tier architecture: a static React SPA, a stateless FastAPI backend, and a PostgreSQL persistence layer. All cross-cutting concerns (LLM, search, Shopify) are external services accessed over HTTP.

```mermaid
flowchart TB
    subgraph Client [Client Browser]
      direction TB
      SPA[React 18 + TypeScript SPA<br/>Vite-built static bundle]
      Canvas[ReadinessCertificate<br/>Canvas2D + DPR scaling]
      SPA --- Canvas
    end

    subgraph EC2 [AWS EC2 — backend host]
      direction TB
      FA[FastAPI app · uvicorn<br/>main.py · lifespan-managed]
      BG[BackgroundTasks<br/>async pipeline runners]
      LG[LangGraph agent<br/>+ AsyncPostgresSaver]
      SVC[18 service modules<br/>ingestion · heuristics ·<br/>llm_analysis · perception_diff ·<br/>mcp_simulation · query_matcher ·<br/>competitor · feed_generator ·<br/>llms_txt · schema_enricher ·<br/>bot_audit · identifier_audit ·<br/>golden_record · trust_signals ·<br/>ai_visibility · copy_rewriter ·<br/>faq_generator · report_builder]
      Writer[shopify_writer<br/>Admin GraphQL writes]
      FA --- BG
      BG --- LG
      BG --- SVC
      LG --- Writer
      SVC --- Writer
    end

    subgraph RDS [AWS RDS — PostgreSQL 15]
      direction TB
      Jobs[(analysis_jobs<br/>JSONB report_json,<br/>fix_plan_json)]
      Backups[(fix_backups<br/>script_tag_id, original_value)]
      LGState[(LangGraph<br/>checkpoint tables)]
    end

    subgraph External [External Services]
      direction TB
      Vertex[Google Cloud<br/>Vertex AI · Gemini 2.0 Flash]
      Shopify[Shopify Storefront<br/>+ Admin GraphQL<br/>+ MCP endpoint]
      Search[DuckDuckGo / SerpAPI]
    end

    Client <-->|HTTPS · JSON ·<br/>X-Admin-Token header| FA
    FA <--> Jobs
    FA <--> Backups
    LG <--> LGState
    SVC <-->|httpx · gql| Shopify
    Writer -->|Admin GraphQL mutations| Shopify
    SVC <-->|with_structured_output| Vertex
    SVC <-->|category queries| Search

    style Client fill:#1a1822,color:#ECE8F5
    style EC2 fill:#0E0D12,color:#ECE8F5
    style RDS fill:#A87B3C,color:#1a1822
    style External fill:#7E7B8C,color:#ECE8F5
```

### 1.2 Future System Architecture (Roadmap)

The architecture below is **not shipped** — it is the roadmap for moving from a single-tenant hackathon system to a multi-tenant production SaaS. Each addition is incremental and does not require rewriting the existing services.

```mermaid
flowchart TB
    subgraph Edge [Edge / CDN]
      CDN[CloudFront / Cloudflare<br/>SPA assets · cached feeds]
      WAF[WAF + rate limiter<br/>per-IP, per-token]
    end

    subgraph App [Application Tier · ECS or EKS]
      direction TB
      ALB[ALB · health checks ·<br/>X-Admin-Token forwarding]
      API1[FastAPI replica 1]
      API2[FastAPI replica 2]
      APIN[FastAPI replica N]
      Worker[Dedicated worker pool<br/>BackgroundTasks → Arq/RQ]
    end

    subgraph Data [Data Tier]
      direction TB
      PG[(PostgreSQL 15<br/>multi-AZ + read replica)]
      Redis[(Redis<br/>job-status cache,<br/>idempotency keys,<br/>rate-limit counters)]
      S3[(S3<br/>generated assets archive,<br/>certificates,<br/>bulk-op JSONL dumps)]
      Vault[AWS Secrets Manager<br/>Vertex SA, SerpAPI key]
    end

    subgraph Obs [Observability]
      direction TB
      OTEL[OpenTelemetry collector]
      Prom[Prometheus / Grafana]
      Sentry[Sentry — frontend +<br/>backend exception tracking]
      Logs[CloudWatch Logs<br/>structured JSON]
    end

    subgraph Auth [AuthN / AuthZ Layer · NEW]
      direction TB
      OAuth[Shopify Partner OAuth<br/>shop installation flow]
      JWT[JWT session tokens]
      Tenant[Multi-tenant isolation<br/>job_id scoped to shop_domain]
    end

    subgraph AIGW [AI Gateway · NEW]
      direction TB
      Router[LLM router<br/>Gemini · Claude · GPT-4]
      Cache[Prompt-response cache<br/>Redis-backed]
      Budget[Per-tenant budget cap]
    end

    Edge --> App
    App --> Data
    App --> Obs
    App --> Auth
    App --> AIGW

    AIGW --> Vertex[(Vertex AI)]
    AIGW --> Anthropic[(Anthropic API)]
    AIGW --> OpenAI[(OpenAI API)]

    Worker --> Shopify2[(Shopify Admin<br/>Bulk Operations)]
    Worker --> Webhooks[Shopify webhooks<br/>incremental re-audit]

    style Auth fill:#FFD896,color:#1a1822
    style AIGW fill:#FFD896,color:#1a1822
    style App fill:#0E0D12,color:#ECE8F5
    style Edge fill:#1a1822,color:#ECE8F5
    style Data fill:#A87B3C,color:#1a1822
    style Obs fill:#7E7B8C,color:#ECE8F5
```

**What changes from current → future**

| Capability | Current | Future |
|---|---|---|
| Auth | None — token in request body | Shopify Partner OAuth + JWT sessions; token managed by app installation |
| Multi-tenancy | None — single-tenant URL-in/report-out | `shop_domain` scopes every row; row-level isolation |
| LLM provider | Gemini 2.0 Flash only | LLM router with provider failover (Gemini → Claude → GPT-4); per-tenant budget cap |
| Background jobs | FastAPI BackgroundTasks (in-process) | Arq / RQ workers with retries, dead-letter queue |
| Observability | stdout logging only | OTEL traces + Prometheus + Sentry + CloudWatch Logs |
| Asset storage | Generated on every download | S3 cache with `Cache-Control: max-age` |
| Rate limiting | None | WAF + per-token Redis token bucket |
| Re-audits | Manual (re-run /analyze) | Webhook-driven incremental re-audit on product update |
| Secrets | `.env` file | AWS Secrets Manager |

### 1.3 Module Topology (Service Dependency Graph)

```mermaid
flowchart LR
    main[main.py<br/>FastAPI routes]
    schemas[schemas.py]
    queries[db/queries.py]
    main --> schemas
    main --> queries

    main --> ingest[ingestion.py]
    main --> heur[heuristics.py]
    main --> llm[llm_analysis.py]
    main --> perc[perception_diff.py]
    main --> mcp[mcp_simulation.py]
    main --> comp[competitor.py]
    main --> qm[query_matcher.py]
    main --> rb[report_builder.py]

    main --> bot[bot_audit.py]
    main --> idn[identifier_audit.py]
    main --> gold[golden_record.py]
    main --> trust[trust_signals.py]
    main --> feed[feed_generator.py]
    main --> llms[llms_txt.py]
    main --> sch[schema_enricher.py]
    main --> aiv[ai_visibility.py]
    main --> rew[copy_rewriter.py]
    main --> faq[faq_generator.py]

    main --> graph[agent/graph.py]
    graph --> nodes[agent/nodes.py]
    nodes --> tools[agent/tools.py]
    tools --> writer[shopify_writer.py]
    writer --> queries
    nodes --> heur

    rb --> heur
    rb --> bot
    rb --> idn
    rb --> gold
    rb --> trust
    rb --> feed
    rb --> llms

    perc --> ingest
    mcp --> ingest
    comp --> ingest
    qm --> ingest

    style main fill:#B4A0D6,color:#1a1822
    style graph fill:#FFD896,color:#1a1822
    style writer fill:#D57A78,color:#1a1822
```

---

## 2. Project Directory Structure

> **Hard rule.** This is the canonical layout. Every file mentioned in this spec lives at the path shown here. Do not deviate.

```
shopmirror/
├── backend/
│   ├── app/
│   │   ├── main.py                       # FastAPI app, routes, lifespan, _resolve_admin_token helper
│   │   ├── schemas.py                    # All API request/response Pydantic schemas (over-the-wire shapes)
│   │   ├── models/
│   │   │   ├── merchant.py               # MerchantData, Product, ProductVariant, ProductImage, ProductOption, Collection, Policies
│   │   │   ├── findings.py               # Finding, PillarScore, AuditReport, PerceptionDiff, ProductPerception, MCPResult,
│   │   │   │                             # CompetitorAudit, CompetitorResult, CopyPasteItem, ProductSummary,
│   │   │   │                             # ChannelStatus, ChannelCompliance, QueryMatchResult
│   │   │   ├── fixes.py                  # FixItem (with rolled_back flag), FixPlan, FixResult
│   │   │   └── jobs.py                   # AnalysisJob, JobStatus, JobProgress
│   │   ├── services/
│   │   │   ├── ingestion.py              # fetch_public_data, fetch_admin_data, fetch_bulk_products, detect_shopify
│   │   │   ├── heuristics.py             # 19 deterministic checks + run_all_checks
│   │   │   ├── llm_analysis.py           # Batched Gemini call → ProductAnalysisBatch, regex cross-validation
│   │   │   ├── perception_diff.py        # compute_combined_perception (store + per-product)
│   │   │   ├── competitor.py             # Discovery (DDG/SerpAPI), detect_shopify filter, lightweight 7-check audit
│   │   │   ├── mcp_simulation.py         # check_mcp_available, generate_questions, run_simulation, classify_response
│   │   │   ├── query_matcher.py          # parse_query_attributes, match_products, run_default_queries
│   │   │   ├── report_builder.py         # assemble_report, channel compliance, AI readiness score
│   │   │   ├── shopify_writer.py         # Admin GraphQL writes + Script Tags + rollback + backups
│   │   │   ├── bot_audit.py              # robots.txt audit + suggested_robots_txt_additions
│   │   │   ├── identifier_audit.py       # GTIN/MPN/barcode coverage audit
│   │   │   ├── golden_record.py          # Catalog data integrity score
│   │   │   ├── trust_signals.py          # Policy clarity / shipping / returns score
│   │   │   ├── feed_generator.py         # build_chatgpt_feed, build_perplexity_feed, build_google_feed
│   │   │   ├── llms_txt.py               # generate_llms_txt, generate_llms_full_txt
│   │   │   ├── schema_enricher.py        # generate_schema_package
│   │   │   ├── ai_visibility.py          # probe_ai_visibility (multi-LLM live probe)
│   │   │   ├── copy_rewriter.py          # rewrite_top_products (per-channel)
│   │   │   └── faq_generator.py          # generate_faq_for_top_products (FAQPage JSON-LD)
│   │   ├── agent/
│   │   │   ├── graph.py                  # LangGraph state machine + AsyncPostgresSaver wiring
│   │   │   ├── nodes.py                  # planner, approval_gate, executor, verifier, reporter, route_after_*
│   │   │   ├── tools.py                  # @tool-decorated executor tools
│   │   │   └── state.py                  # StoreOptimizationState TypedDict
│   │   ├── db/
│   │   │   ├── connection.py             # asyncpg pool: get_pool, close_pool
│   │   │   ├── migrations/
│   │   │   │   ├── 001_initial.sql       # analysis_jobs + fix_backups
│   │   │   │   └── 002_add_script_tag.sql # script_tag_id column on fix_backups
│   │   │   └── queries.py                # All DB read/write functions
│   │   └── utils/
│   │       ├── retry.py                  # async_retry decorator (3 retries, 1/2/4s, 429+503 only)
│   │       └── validators.py             # validate_shopify_url, detect_shopify
│   ├── requirements.txt
│   ├── .env / .env.example
│   └── start_backend.ps1
├── frontend/
│   ├── src/
│   │   ├── App.tsx                       # Top-level state machine, polling, screen routing
│   │   ├── main.tsx
│   │   ├── api/
│   │   │   └── client.ts                 # All API calls, types, JobStatus enum
│   │   ├── utils/
│   │   │   ├── labels.ts                 # CHECK_LABELS map
│   │   │   └── score.ts                  # normalizeScore, pillarPercent, overallFromPillars, scoreBand
│   │   └── components/
│   │       ├── LandingPage.tsx
│   │       ├── InputScreen.tsx           # URL + token + intent + competitor input; accepts prefillUrl
│   │       ├── ProgressScreen.tsx        # Dual-mode (audit vs execute) step list + reveal grid
│   │       ├── Dashboard.tsx             # Tabbed dashboard: Overview / Perception / Findings / Products / Fix Plan
│   │       ├── HeatmapGrid.tsx           # Products × checks grid
│   │       ├── PerceptionDiff.tsx        # Intent vs AI perception card
│   │       ├── MCPSimulation.tsx         # ANSWERED / UNANSWERED / WRONG cards
│   │       ├── CompetitorDiscovery.tsx   # Auto/manual mode toggle, run benchmark
│   │       ├── CompetitorPanel.tsx       # Competitor result panels
│   │       ├── FindingsTable.tsx         # Filterable findings list with expand-to-detail
│   │       ├── FixApproval.tsx           # Auto/copy-paste/manual sections; preselects auto fixes
│   │       ├── AgentActivity.tsx         # Per-fix status + rollback button + counters
│   │       ├── DiffViewer.tsx            # Before/after per-fix diff
│   │       ├── BeforeAfterReport.tsx     # Score delta hero + pillar comparison + checks improved
│   │       └── ReadinessCertificate.tsx  # Canvas-rendered PNG with DPR scaling
│   ├── package.json
│   └── .env.example
└── docker-compose.yml                    # Postgres 15 + named volume
```

---

## 3. Tech Stack

| Component | Technology | Version | Rationale |
|---|---|---|---|
| Backend API | FastAPI | 0.111+ | Async-native, BackgroundTasks for job running, auto-OpenAPI docs |
| Agent Framework | LangGraph | 0.2+ | State machine for optimization loop; AsyncPostgresSaver for persistence |
| LLM Orchestration | LangChain | 0.3+ | Tool definitions, structured-output wrappers |
| LLM Model | Gemini 2.0 Flash via `langchain-google-vertexai` | latest | Structured JSON via `with_structured_output(...)`, cheap, fast, available on Google Cloud |
| HTTP Client | httpx | 0.27+ | Async HTTP for all Shopify public-endpoint fetching |
| HTML Parsing | BeautifulSoup4 + lxml | 4.12+ / 5.2+ | JSON-LD extraction from raw HTML, no JS execution |
| GraphQL Client | gql + aiohttp | 3.5+ | Shopify Admin GraphQL API calls |
| Data Validation | Pydantic | 2.x | All LLM outputs and all API request/response shapes |
| Database | PostgreSQL | 15 | Job state + report storage; provided via AWS RDS in production |
| DB Driver | asyncpg | 0.29+ | Async PostgreSQL driver compatible with FastAPI |
| Search | duckduckgo-search OR serpapi | latest / 0.1+ | Competitor discovery; DDG is the no-key default, SerpAPI used when `SERPAPI_KEY` set |
| Frontend | React + TypeScript | 18 | Component model fits UI; strict TS config |
| Build Tool | Vite | 5+ | Fast dev server, native ESM |
| Container | Docker + docker-compose | latest | Local dev parity; production deployment to EC2 |
| Infra | AWS EC2 + RDS | n/a | EC2 for backend, RDS for PostgreSQL |

### `requirements.txt` (key entries)

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
duckduckgo-search>=6.0.0
serpapi==0.1.5
```

### Hard stack rules (do not violate)

- **Never** use `requests` — use `httpx`.
- **Never** use SQLAlchemy — use `asyncpg`.
- **Never** use Celery — use FastAPI `BackgroundTasks`.
- **Never** implement Shopify OAuth — Admin token is supplied as a plain string at request time.
- **Never** mutate Shopify theme files — schema fixes use Script Tags API or generate copy-paste blocks.
- **Never** auto-write policy text — policy fixes are drafts only.
- **Every** LLM call uses `ChatVertexAI(model="gemini-2.0-flash", temperature=0)` and `with_structured_output(PydanticModel)`.
- **Every** service function is `async`.
- **All** I/O uses `httpx` or `asyncpg`.
- **All** Script Tag injections use the `scriptTagCreate` mutation.
- **All** taxonomy writes use the Shopify Standard Taxonomy GID format (e.g. `gid://shopify/TaxonomyCategory/aa-1-1`).
- **AsyncPostgresSaver** must be wired on the same day as the LangGraph graph — never deferred.
- **D1a** severity is MEDIUM, never CRITICAL — robots.txt does not affect the Shopify Catalog pipeline.

---

## 4. Database Schema and Data Flow

### 4.1 Entity-Relationship Diagram

```mermaid
erDiagram
    ANALYSIS_JOBS ||--o{ FIX_BACKUPS : "produces"
    ANALYSIS_JOBS {
        UUID id PK
        VARCHAR store_url
        VARCHAR store_domain
        BOOLEAN has_token "token never stored"
        VARCHAR status "queued..failed"
        VARCHAR progress_step
        INTEGER progress_pct
        JSONB report_json "full audit + agent_run"
        JSONB fix_plan_json "list of FixItem"
        TEXT error_message
        TIMESTAMP created_at
        TIMESTAMP completed_at
    }
    FIX_BACKUPS {
        UUID id PK
        UUID job_id FK
        VARCHAR fix_id UK "stable across rollback"
        VARCHAR product_id
        VARCHAR field_type "title.product_type.metafield.alt_text.taxonomy.script_tag"
        VARCHAR field_key
        TEXT original_value
        TEXT new_value
        VARCHAR shopify_gid
        VARCHAR script_tag_id "for scriptTagDelete rollback"
        TIMESTAMP applied_at
        BOOLEAN rolled_back
    }
    LANGGRAPH_CHECKPOINTS {
        TEXT thread_id PK
        BYTEA checkpoint
        JSONB metadata
    }
```

### 4.2 Data Lifecycle

```mermaid
stateDiagram-v2
    [*] --> queued: POST /analyze
    queued --> ingesting: background task starts
    ingesting --> auditing: MerchantData ready
    auditing --> simulating: heuristics + LLM done
    simulating --> complete: free tier — no fixes
    simulating --> awaiting_approval: paid tier — fix plan ready
    awaiting_approval --> executing: POST /execute
    executing --> complete: agent done
    executing --> failed: agent crashed (preserve report in memory)
    auditing --> failed: pipeline crash
    ingesting --> failed: ingestion crash
    simulating --> failed: simulating crash
    complete --> [*]
    failed --> [*]

    note right of awaiting_approval
        Fix plan persisted as JSONB.
        Frontend polls until terminal status.
    end note

    note right of failed
        error_message recorded.
        Frontend preserves prior report
        if one exists in memory.
    end note
```

### 4.3 Database Schema

### Table: `analysis_jobs`

```sql
CREATE TABLE analysis_jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  store_url       VARCHAR(512) NOT NULL,
  store_domain    VARCHAR(256),
  has_token       BOOLEAN DEFAULT FALSE,        -- token itself is never stored
  status          VARCHAR(32) DEFAULT 'queued',
  -- status values: queued | pending | ingesting | auditing | simulating
  --                | awaiting_approval | executing | complete | failed
  progress_step   VARCHAR(256),
  progress_pct    INTEGER DEFAULT 0,
  report_json     JSONB,
  fix_plan_json   JSONB,
  error_message   TEXT,
  created_at      TIMESTAMP DEFAULT NOW(),
  completed_at    TIMESTAMP
);
```

### Table: `fix_backups`

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
  script_tag_id   VARCHAR(256),                  -- for inject_schema_script rollback via scriptTagDelete
  applied_at      TIMESTAMP DEFAULT NOW(),
  rolled_back     BOOLEAN DEFAULT FALSE
);
```

### Migration order

1. `001_initial.sql` — both tables.
2. `002_add_script_tag.sql` — adds `script_tag_id` column to `fix_backups`. Run after 001 in any fresh environment.

### `report_json` shape (over-the-wire)

```jsonc
{
  "store_name": "string",
  "store_domain": "string",
  "ingestion_mode": "url_only | admin_token",
  "total_products": 0,
  "ai_readiness_score": 0,                 // 0..100
  "pillars": {
    "Discoverability": { "score": 0.0, "checks_passed": 0, "checks_total": 5 },
    "Completeness":    { "score": 0.0, "checks_passed": 0, "checks_total": 6 },
    "Consistency":     { "score": 0.0, "checks_passed": 0, "checks_total": 3 },
    "Trust_Policies":  { "score": 0.0, "checks_passed": 0, "checks_total": 3 },
    "Transaction":     { "score": 0.0, "checks_passed": 0, "checks_total": 2 }
  },
  "findings": "Finding[]",
  "worst_5_products": "ProductSummary[]",
  "all_products": "ProductSummary[]?",         // present when full-catalog scan was run
  "channel_compliance": "ChannelCompliance",
  "perception_diff": "PerceptionDiff | null",
  "product_perceptions": "ProductPerception[]",
  "mcp_simulation": "MCPResult[] | null",
  "competitor_comparison": "CompetitorResult[]",
  "copy_paste_package": "CopyPasteItem[]",
  "agent_run": "AgentRun?",                    // populated after fix execution
  "bot_access": { "...": "..." },
  "identifier_audit": { "...": "..." },
  "golden_record": { "...": "..." },
  "trust_signals": { "...": "..." },
  "ai_visibility": { "...": "..." },           // populated by /ai-visibility on demand
  "feed_summaries": { "chatgpt": {...}, "perplexity": {...}, "google": {...} },
  "llms_txt_preview": "string",                // first 1500 chars
  "scan_limited": true,                        // free-tier flag
  "full_product_count": 0
}
```

### Object shapes (Python dataclasses + TS interfaces)

```python
ChannelStatus {
  status: 'READY' | 'PARTIAL' | 'BLOCKED' | 'NOT_READY'
  blocking_check_ids: list[str]
}

ChannelCompliance {
  shopify_catalog: ChannelStatus     # D1b, C1, Con1, A1, A2
  google_shopping: ChannelStatus     # C4, C1, Con1, Con2
  meta_catalog:    ChannelStatus     # C2, C6, Con1
  perplexity_web:  ChannelStatus     # D1a, D2, D3
  chatgpt_shopping:ChannelStatus     # T4, T1, T2
}

Finding {
  id: str
  pillar: str                # 'Discoverability' | 'Completeness' | 'Consistency' | 'Trust_Policies' | 'Transaction'
  check_id: str              # 'D1a' | 'D1b' | 'C2' | 'Con1' | etc.
  check_name: str
  severity: str              # 'CRITICAL' | 'HIGH' | 'MEDIUM'
  weight: int                # 10 | 6 | 2
  title: str
  detail: str
  spec_citation: str
  affected_products: list[str]
  affected_count: int
  impact_statement: str
  fix_type: str              # 'auto' | 'copy_paste' | 'manual' | 'developer'
  fix_instruction: str
  fix_content: str | None
}

FixItem {
  fix_id: str
  product_id: str | None
  product_title: str | None
  type: str                  # see DEPENDENCY_ORDER
  field: str
  current_value: str | None
  proposed_value: str | None
  reason: str
  severity: str              # 'CRITICAL' | 'HIGH' | 'MEDIUM'
  fix_type: str              # 'auto' | 'copy_paste' | 'manual' | 'developer'
  check_id: str
}

FixResult {
  fix_id: str
  success: bool
  error: str | None
  shopify_gid: str | None
  script_tag_id: str | None
  applied_at: str | None
  rolled_back: bool          # patched into stored agent_run on rollback
}

AgentRun {
  fixes_applied: int
  fixes_failed: int
  manual_action_items: Finding[]
  executed_fixes: FixResult[]
  failed_fixes: FixResult[]
  verification_results: dict[str, bool]
  before_after: BeforeAfterResponse | null
  rolled_back_fix_ids: list[str]   # patched in by /rollback
}

QueryMatchResult {
  query: str
  matched_product_ids: list[str]
  total_products: int
  match_count: int
  failing_attributes: dict[str, int]
}
```

---

## 5. API Specification

### 5.0 Sequence Diagram — Audit Path

```mermaid
sequenceDiagram
    autonumber
    participant U as Merchant
    participant FE as Dashboard SPA
    participant BE as FastAPI
    participant DB as PostgreSQL
    participant SH as Shopify
    participant GE as Vertex AI

    U->>FE: enters store_url + token
    FE->>BE: POST /analyze
    BE->>BE: validate_shopify_url
    BE->>DB: INSERT analysis_jobs (status=queued, has_token)
    BE-->>FE: 202 {job_id}
    BE->>BE: BackgroundTasks.add_task(run_analysis_pipeline)

    par Pipeline (async)
      BE->>DB: UPDATE status=ingesting
      BE->>SH: GET /products.json + Admin GraphQL
      SH-->>BE: catalog data
      BE->>DB: UPDATE status=auditing
      BE->>GE: batched ProductAnalysis prompt
      GE-->>BE: structured JSON
      BE->>DB: UPDATE status=simulating
      BE->>GE: perception diff + MCP simulation
      GE-->>BE: structured JSON
      BE->>SH: 7-check competitor audit (top 3)
      SH-->>BE: public storefront data
      BE->>DB: UPDATE report_json + status=complete or awaiting_approval
    end

    loop every 2s
      FE->>BE: GET /jobs/{job_id}
      BE->>DB: SELECT report_json, status, progress
      BE-->>FE: status + progress (+ report when terminal)
    end

    FE->>U: Dashboard render
```

### 5.1 Sequence Diagram — Execute + Rollback Path

```mermaid
sequenceDiagram
    autonumber
    participant U as Merchant
    participant FE as Dashboard SPA
    participant BE as FastAPI
    participant DB as PostgreSQL
    participant LG as LangGraph Agent
    participant SH as Shopify Admin

    U->>FE: clicks "Apply N fixes"
    FE->>BE: POST /jobs/{id}/execute (approved_fix_ids, token)
    BE->>BE: validate status=awaiting_approval, has_token=true
    BE-->>FE: 202 {execution_job_id}
    BE->>LG: spawn run_fix_agent_task

    rect rgb(40, 30, 60)
      note right of LG: LangGraph loop with AsyncPostgresSaver
      LG->>SH: re-fetch live product data
      LG->>DB: UPDATE status=executing, progress
      loop per approved fix
        LG->>LG: planner picks next fix (dependency order)
        LG->>SH: Admin GraphQL mutation
        SH-->>LG: shopify_gid / script_tag_id
        LG->>DB: INSERT fix_backups (original_value, new_value)
        LG->>SH: re-run check (verifier)
        alt check passes
          LG->>LG: planner advances
        else fail and retry < 2
          LG->>SH: retry mutation
        else fail final
          LG->>LG: add to manual_action_items
        end
      end
      LG->>DB: UPDATE report_json.agent_run, status=complete
    end

    FE->>BE: GET /jobs/{id} (polling)
    BE-->>FE: status=complete, agent_run

    U->>FE: clicks Undo on a fix
    FE->>BE: POST /jobs/{id}/rollback/{fix_id}
    BE->>DB: SELECT fix_backup WHERE fix_id AND job_id
    BE->>SH: reverse mutation (productUpdate / scriptTagDelete / metafieldsDelete)
    SH-->>BE: 200 OK
    BE->>DB: UPDATE fix_backups.rolled_back = true
    BE->>DB: PATCH report_json.agent_run.executed_fixes[].rolled_back, rolled_back_fix_ids
    BE-->>FE: 200 {status: rolled_back, field, restored_value}
    FE->>BE: GET /jobs/{id} (refresh from onAfterRollback)
    BE-->>FE: updated agent_run
    FE->>U: certificate, before/after, counters all update
```

### 5.2 Endpoint Reference

> **Contract.** This is the agreed API contract between backend and frontend. Frontend types live in `frontend/src/api/client.ts` and mirror these shapes 1:1.

### 5.3 Status enum

```
queued | pending | ingesting | auditing | simulating
| awaiting_approval | executing | complete | failed
```

The legacy `error` value is no longer emitted — `update_job_error()` writes `failed` exclusively. The frontend's polling loop tolerates the legacy value but does not depend on it.

### 5.4 Endpoints

#### `POST /analyze` — start an audit

**Request**
```json
{
  "store_url": "string",
  "admin_token": "string | null",
  "merchant_intent": "string | null",
  "competitor_urls": ["string"]
}
```
**Responses**
- `202` → `{ "job_id": "string" }`
- `400` → `{ "detail": "Invalid Shopify store URL" }`

The token, when supplied, is held in the request body for the duration of the background task and never written to disk. Only `has_token = true` is persisted.

#### `GET /jobs/{job_id}` — poll status

**Response**
```json
{
  "status": "ingesting | ... | failed",
  "progress": { "step": "string", "pct": 0 },
  "report": "AuditReport | null",
  "error": "string | null"
}
```

`report` is non-null only when status is `complete`, `awaiting_approval`, or `failed` (a failure mid-pipeline still surfaces partial data when available).

#### `GET /jobs/{job_id}/fix-plan` — list planned fixes

Requires `has_token = true` on the job, otherwise returns `403`. Response is `{ "fixes": FixItem[] }`.

#### `POST /jobs/{job_id}/execute` — run the agent

**Request**
```json
{
  "approved_fix_ids": ["string"],
  "admin_token": "string",
  "merchant_intent": "string | null"
}
```
**Responses**
- `202` → `{ "execution_job_id": "string" }`
- `400` → if status is not `awaiting_approval`
- `403` → if `has_token = false`
- `404` → if job not found

Triggers the LangGraph fix agent in the background. Poll `GET /jobs/{job_id}` to track progress (status flips to `executing`, then `complete` or `failed`).

#### `POST /jobs/{job_id}/rollback/{fix_id}` — reverse a single fix

**Request**
```json
{ "admin_token": "string" }
```
**Response (200)**
```json
{ "status": "rolled_back", "field": "string", "restored_value": "string" }
```

After a successful rollback, the route patches the stored report:
- `agent_run.executed_fixes[].rolled_back = true` for the matching `fix_id`.
- `agent_run.rolled_back_fix_ids[]` (sorted, de-duplicated).

This makes the rollback durable across page reloads. Errors include `404` (backup or job not found) and `500` (Shopify mutation failed). All errors leave the database state consistent — partial rollbacks are not allowed.

#### `GET /jobs/{job_id}/before-after` — re-audit comparison

Returns the BeforeAfterResponse computed by the reporter node:
```json
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

Returns `404` if the agent has not yet run.

#### `POST /jobs/{job_id}/competitors` — re-run competitor audit

**Request** `{ "competitor_urls": ["string"] }` (empty array → auto-discovery)
**Response**
```json
{
  "results": "CompetitorResult[]",
  "status": "ok | empty | error",
  "message": "string",
  "mode": "auto | manual",
  "scope_label": "string",
  "candidates_considered": 0,
  "audited_competitors": 0,
  "notes": ["string"]
}
```

Patches `competitor_comparison` back into the stored report so the next `/jobs/{id}` poll returns the new data.

#### Asset endpoints (token-authenticated)

All five asset endpoints accept the admin token via either an `X-Admin-Token` header (preferred) or a `?admin_token=` query parameter (legacy fallback). The dashboard always uses the header.

| Endpoint | Content-Type | Headers Returned |
|---|---|---|
| `GET /jobs/{id}/llms-txt` | `text/plain; charset=utf-8` | `Content-Disposition` |
| `GET /jobs/{id}/llms-full-txt` | `text/plain; charset=utf-8` | `Content-Disposition` |
| `GET /jobs/{id}/schema-package` | `application/json` | — |
| `GET /jobs/{id}/feeds/google` | `application/xml` | `X-Feed-Total-Items`, `X-Ingestion-Mode`, `Content-Disposition` |
| `GET /jobs/{id}/feeds/perplexity` | `application/xml` | `X-Feed-Total-Items`, `X-Skipped-No-Identifier`, `X-Ingestion-Mode`, `Content-Disposition` |
| `GET /jobs/{id}/feeds/chatgpt` | `application/x-ndjson` | `X-Feed-Total-Lines`, `X-Feed-Currency`, `X-Ingestion-Mode`, `Content-Disposition` |

CORS `expose_headers` is configured to expose `Content-Disposition` and all `X-*` feed headers so the dashboard's JS-driven download path can read them.

#### Deeper-audit endpoints

| Endpoint | What It Returns |
|---|---|
| `GET /jobs/{id}/bot-access` | `bot_access` section from the stored report |
| `GET /jobs/{id}/identifiers` | `identifier_audit` section |
| `GET /jobs/{id}/golden-record` | `golden_record` section |
| `GET /jobs/{id}/trust-signals` | `trust_signals` section |
| `GET /jobs/{id}/robots-suggestion` | Suggested `robots.txt` patch as `text/plain` |

#### Lab endpoints (live LLM, on-demand)

| Endpoint | Body | Purpose |
|---|---|---|
| `POST /jobs/{id}/ai-visibility` | `{ prompts?, providers?, admin_token? }` | Live multi-LLM probe. Result patched into `ai_visibility` |
| `POST /jobs/{id}/copy-rewrite` | `{ limit?, channels?, product_ids?, admin_token? }` | Per-channel copy rewriting, draft only |
| `POST /jobs/{id}/faq-schema` | `{ limit?, product_ids?, admin_token? }` | FAQPage JSON-LD generation |

#### `GET /health`

Returns `{ "status": "ok" }`. Used by AWS load balancer health checks.

### 5.5 Error envelope

Every error response uses FastAPI's default `{ "detail": "..." }` shape. Frontend `client.ts` parses this uniformly:
```ts
async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(...)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Request failed')
  }
  return res.json()
}
```

---

## 6. Service Specifications

### 6.1 `ingestion.py`

Foundation layer. Returns a `MerchantData` dataclass.

| Function | Inputs | Outputs | Notes |
|---|---|---|---|
| `fetch_public_data(store_url)` | Validated store URL | MerchantData (Mode A) | Fetches products.json, policies.json, robots.txt, sitemap.xml, llms.txt; paginates products.json (250/page) |
| `fetch_admin_data(store_url, token)` | URL + Admin token | MerchantData (Mode B) | Admin GraphQL: metafields, SEO, taxonomy, inventory, image alt text, market translations; merges with Mode A |
| `fetch_bulk_products(store_url, token)` | URL + Admin token | MerchantData | Used automatically when `total_products > 150`; submits `bulkOperationRunQuery`, polls until complete, downloads JSONL |
| `crawl_product_pages(product_urls)` | Up to 5 product URLs | `dict[url, SchemaData]` | httpx raw fetch + BeautifulSoup JSON-LD extraction; no JS execution |
| `select_crawl_targets(products)` | Product list | `list[url]` (max 5) | Top 5 by variant count |
| `detect_shopify(store_url)` | Any URL | `bool` | `/products.json` returns 200 with `products` key |

**`MerchantData` fields**

| Field | Type | Source |
|---|---|---|
| store_domain | str | Parsed from input URL |
| store_name | str | HTML title or meta |
| products | list[Product] | products.json paginated |
| collections | list[Collection] | collections.json |
| policies | Policies | policies.json |
| robots_txt | str | GET /robots.txt |
| sitemap_present | bool | GET /sitemap.xml status |
| sitemap_has_products | bool | Parsed sitemap content |
| llms_txt | str \| None | GET /llms.txt |
| schema_by_url | dict[str, list] | Crawled JSON-LD blocks |
| price_in_html | dict[str, bool] | Raw HTML price check per URL |
| ingestion_mode | str | `url_only` or `admin_token` |
| metafields_by_product | dict[str, list] | Admin GraphQL (Mode B) |
| seo_by_product | dict[str, dict] | Admin GraphQL (Mode B) |
| inventory_by_variant | dict[str, dict] | Admin GraphQL (Mode B) |
| taxonomy_by_product | dict[str, str] | `product.category` GID (Mode B) |
| markets_by_product | dict[str, dict] | productTranslations per active market (Mode B) |
| metafield_definitions | list[dict] | Store-level MetafieldDefinition objects (Mode B) |
| admin_domain | str \| None | Admin domain (typically `*.myshopify.com`) |

### 6.2 `heuristics.py`

19 deterministic checks. Zero LLM calls. Takes `MerchantData` + `llm_results`, returns `list[Finding]`.

| Function | Check | Returns |
|---|---|---|
| `check_robot_crawlers(data)` | D1a | Finding per blocked AI bot — severity MEDIUM |
| `check_catalog_eligibility(data)` | D1b | CRITICAL if taxonomy unmapped OR title empty OR price unset (Mode B only) |
| `check_sitemap(data)` | D2 | Finding if absent or missing products |
| `check_llms_txt(data)` | D3 | Finding if absent |
| `check_markets_translation(data)` | D5 | Finding per active market missing translations (Mode B only) |
| `check_taxonomy_mapped(data)` | C1 | Finding per product with no Standard Taxonomy GID (Mode B only) |
| `check_title_category_noun(data, llm_results)` | C2 | Fed from llm_analysis output |
| `check_variant_option_names(data)` | C3 | Products with unnamed options |
| `check_gtin_identifier(data)` | C4 | Products missing all identifiers |
| `check_metafield_definitions(data)` | C5 | Typed MetafieldDefinition absent for material/care_instructions (Mode B only) |
| `check_image_alt_text(data)` | C6 | Coverage percentage |
| `check_schema_price_consistency(data)` | Con1 | Per-page price mismatch |
| `check_schema_availability(data)` | Con2 | Per-page availability mismatch |
| `check_seo_consistency(data)` | Con3 | Inconsistent SEO title (Mode B only) |
| `check_refund_timeframe(data)` | T1 | No days/number in refund policy |
| `check_shipping_regions(data)` | T2 | No regions in shipping policy |
| `check_offer_schema(data)` | T4 | Missing OfferShippingDetails / MerchantReturnPolicy — `fix_type='auto'` (Script Tags) |
| `check_inventory_tracking(data)` | A1 | Untracked variants |
| `check_oversell_risk(data)` | A2 | continue + tracked combination |
| `run_all_checks(data, llm_results)` | all | `list[Finding]` sorted by severity then affected_count |

### 6.3 `llm_analysis.py`

Single batched LangChain call per 15 products. Pydantic structured output via `with_structured_output(...)`.

```python
class ProductAnalysis(BaseModel):
    product_id: str
    title_contains_category_noun: bool
    title_category_noun: Optional[str]
    description_has_material: bool
    description_has_use_case: bool
    description_has_specs: bool
    missing_vocabulary: list[str]   # max 3

# Cross-validation applied after LLM call:
# If description_has_material=True but no material keyword in description text → False.
# Material keywords: cotton, polyester, leather, wood, steel, wool, linen,
#                    plastic, ceramic, gold, silver, nylon, silk
```

### 6.4 `perception_diff.py`

| Function | When Called | LLM Calls | Output |
|---|---|---|---|
| `compute_combined_perception(data, findings, merchant_intent)` | Every analysis | 1 + 2 per worst-5 product | `(PerceptionDiff, list[ProductPerception])` |

Per-product Call 2 prompt is constrained to ONLY use machine-readable fields and emit `cannot_determine[]` for missing dimensions.

### 6.5 `competitor.py`

| Function | Behavior |
|---|---|
| `find_competitors(merchant_data)` | Searches via DuckDuckGo or SerpAPI; returns up to 5 candidate URLs |
| `audit_competitor(url)` | Runs the public-data subset (D1a, D1b, C1, C3, C4, C6, T1, T2) |
| `run_competitor_analysis(merchant_data, findings, competitor_urls)` | End-to-end: discover → detect_shopify filter → audit top 3 verified → build gap table |
| `run_competitor_analysis_with_meta(...)` | Same, but returns metadata (status, message, mode, scope_label, candidates_considered, notes) for the dashboard's discovery panel |

### 6.6 `mcp_simulation.py`

| Function | Behavior |
|---|---|
| `check_mcp_available(store_domain)` | GET `{domain}/api/mcp` |
| `generate_questions(merchant_data)` | Builds 10 questions using real product names, categories, price brackets |
| `run_mcp_simulation(merchant_data, findings)` | Posts to live MCP if available; otherwise Gemini-driven simulation using ONLY machine-readable data |
| `classify_response(question, response, ground_truth)` | Returns `ANSWERED` / `UNANSWERED` / `WRONG` |
| `map_to_findings(mcp_results, findings)` | Links each failure to specific audit findings |

### 6.7 `query_matcher.py`

Single LLM call to parse the query; zero LLM calls in the matching loop.

| Function | Behavior |
|---|---|
| `parse_query_attributes(query_text)` | One Gemini call → `ParsedQuery {category, price_max, price_min, attributes: list[str]}` |
| `match_products(products, attributes, metafields_by_product, taxonomy_by_product)` | Deterministic. Returns `(matched_product_ids, failing_attributes_dict)`. Material keywords must be in metafield values, not just description prose |
| `run_default_queries(merchant_data, paid_tier)` | Generates 1 (free) or 5 (paid) queries from taxonomy + price bracket; never raises (per-query exception capture) |

### 6.8 `shopify_writer.py`

All write operations to Shopify Admin GraphQL. Called only by `agent/tools.py`. Never directly from routes.

| Function | Mutation | Backup |
|---|---|---|
| `write_product_type(gid, product_type, job_id)` | productUpdate | Yes |
| `write_title(gid, title, job_id)` | productUpdate | Yes |
| `write_metafield(gid, namespace, key, value, type, job_id)` | metafieldsSet | Yes (null original; rollback deletes) |
| `write_alt_text(image_gid, alt_text, job_id)` | productImageUpdate | Yes |
| `write_taxonomy(gid, taxonomy_gid, job_id)` | productUpdate (`category` field) | Yes |
| `inject_schema_script(domain, token, schema_json, job_id)` | scriptTagCreate | Yes (`script_tag_id` stored) |
| `delete_schema_script(script_tag_id, token)` | scriptTagDelete | n/a (rollback) |
| `create_metafield_definition(token, namespace, key, type)` | metafieldDefinitionCreate | n/a (idempotent) |
| `rollback_fix(fix_id, store_domain, token, expected_job_id)` | per-field-type | Restores backup; raises `KeyError` if not found |

`rollback_fix` validates that the backup belongs to the calling job (`expected_job_id`) before restoring. The route layer additionally patches `agent_run.executed_fixes[].rolled_back` and `agent_run.rolled_back_fix_ids[]` into the stored report.

### 6.9 Auxiliary services

| Module | Responsibility |
|---|---|
| `bot_audit.py` | Parse robots.txt, classify allowed vs blocked AI bots, generate `suggested_robots_txt_additions(audit)` |
| `identifier_audit.py` | GTIN / barcode / MPN coverage; per-product missing list |
| `golden_record.py` | Composite catalog data integrity score |
| `trust_signals.py` | Composite policy/shipping/returns clarity score |
| `feed_generator.py` | `build_chatgpt_feed` (JSONL), `build_perplexity_feed` (XML), `build_google_feed` (XML) |
| `llms_txt.py` | `generate_llms_txt`, `generate_llms_full_txt` — emit valid llms.txt content for the merchant |
| `schema_enricher.py` | `generate_schema_package` — per-product JSON-LD blocks ready to host or paste |
| `ai_visibility.py` | `probe_ai_visibility` — multi-LLM live probe (Gemini default, configurable providers) |
| `copy_rewriter.py` | `rewrite_top_products` — per-channel copy rewrites; draft only |
| `faq_generator.py` | `generate_faq_for_top_products` — FAQPage JSON-LD blocks |

### 6.10 `report_builder.py`

`assemble_report(...)` is the single function that produces the final `AuditReport` from all upstream service outputs. Responsibilities:

1. Compute `pillars` map with `(score, checks_passed, checks_total)` per pillar.
2. Compute `ai_readiness_score` (0–100) using the weighted pillar formula. The same weighting is mirrored on the frontend in `utils/score.ts`.
3. Compute `channel_compliance` by mapping each channel's blocking check IDs against the failed findings.
4. Order `findings` by severity then affected_count.
5. Pick `worst_5_products` by gap score; emit `all_products` when paid tier (`scan_limited=false`).
6. Bundle `copy_paste_package` from copy-paste-type fixes.
7. Attach `bot_access`, `identifier_audit`, `golden_record`, `trust_signals`, `feed_summaries`, `llms_txt_preview`.
8. Carry `scan_limited` and `full_product_count` for the free-tier upgrade banner.

---

## 7. LangGraph Agent Specification

### 7.0 Agent State Machine

```mermaid
stateDiagram-v2
    [*] --> planner: initial state
    planner --> approval_gate: always
    approval_gate --> executor: approved fixes remain
    approval_gate --> reporter: no approved fixes left
    executor --> verifier: always
    verifier --> planner: check passed
    verifier --> executor: check failed and retry < 2
    verifier --> planner: check failed and retry exhausted, add to manual_action_items
    planner --> reporter: iteration > 50 (hard cap)
    reporter --> [*]: terminal, patches agent_run

    note right of approval_gate
        Pass-through node.
        Approval is collected via POST /execute
        before the graph starts running.
    end note

    note right of verifier
        retry_count is per-fix and resets when
        planner advances to the next fix.
    end note
```

### 7.1 State (`agent/state.py`)

```python
class StoreOptimizationState(TypedDict):
    job_id: str
    store_data: MerchantData
    admin_token: str
    merchant_intent: str | None
    audit_findings: list[Finding]
    fix_plan: list[FixItem]
    approved_fix_ids: list[str]
    executed_fixes: list[FixResult]
    failed_fixes: list[FixResult]
    current_fix_id: str | None
    retry_count: int                 # per-fix, max 2
    iteration: int                   # total, max 50
    verification_results: dict[str, bool]
    manual_action_items: list[Finding]
    final_report: dict | None
```

### 7.2 Graph (`agent/graph.py`)

```
planner → approval_gate → executor → verifier → planner (loop)
                                              ↘ reporter (terminal)
```

- `planner → approval_gate` always.
- `approval_gate → executor | reporter` via `route_after_planner` (executor if approved fixes remain, else reporter).
- `executor → verifier` always.
- `verifier → executor | planner` via `route_after_verifier` (executor on retry, planner otherwise).
- `reporter → END`.

`AsyncPostgresSaver` is constructed from `DATABASE_URL` on first compile and persists state across the approval interrupt.

### 7.3 Nodes (`agent/nodes.py`)

| Node | Reads | Writes | Routing |
|---|---|---|---|
| `planner_node` | findings, executed/failed, iteration | current_fix_id, fix_plan (first run) | If no approved fixes left → reporter. If iteration > 50 → reporter. Else → executor |
| `approval_gate_node` | fix_plan | (pass-through) | `route_after_planner` |
| `executor_node` | current_fix_id, fix_plan, store_data, admin_token | executed_fixes / failed_fixes | Always → verifier |
| `verifier_node` | current_fix_id, executed_fixes, store_data | verification_results, retry_count | Pass → planner; fail (retry < 2) → executor; else manual + planner |
| `reporter_node` | all state | final_report | Terminal. Patches `agent_run` (with `before_after`) into `analysis_jobs.report_json` |

### 7.4 Dependency order (planner)

```python
DEPENDENCY_ORDER = [
    'map_taxonomy',
    'create_metafield_definitions',
    'classify_product_type',
    'improve_title',
    'fill_metafield',
    'generate_alt_text',
    'inject_schema_script',
    'generate_schema_snippet',
    'suggest_policy_fix',
]
# Within same level: sort by (severity_weight × affected_count) descending.
```

### 7.5 Tools (`agent/tools.py`)

| Tool | Confidence Gate | Behavior on Low Confidence |
|---|---|---|
| `map_taxonomy` | Gemini-returned GID must match Shopify's published taxonomy | Adds to `manual_action_items` with suggested category path |
| `create_metafield_definitions` | Idempotent | n/a |
| `classify_product_type` | Writes only on `confidence='high'` | manual_action_items with suggestion |
| `improve_title` | Always generates; diff shown for approval | n/a |
| `fill_metafield` | Cross-validates with regex | Only writes verified fields; flags uncertain |
| `generate_alt_text` | Always generates | Written only on approval |
| `inject_schema_script` | Always when T4 fails + token present | `script_tag_id` stored for rollback |
| `generate_schema_snippet` | n/a (no write) | Adds to `copy_paste_package` |
| `suggest_policy_fix` | n/a (no write) | Adds structured draft to `copy_paste_package` |

---

## 8. LLM Prompt Specifications

> **Rule.** Every LLM call uses structured output via Pydantic. System prompt always ends with: "Return ONLY valid JSON matching the provided schema. Do not include any text outside the JSON object." All prompts use `temperature=0`.

### 8.1 Batch product analysis

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

### 8.2 Store-level perception

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

### 8.3 Product AI view (Call 2 of perception diff)

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

### 8.4 Title improvement

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

### 8.5 Metafield extraction

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

### 8.6 Taxonomy classification

```
SYSTEM:
You classify Shopify products to the official Shopify Standard Product Taxonomy.
Return the most specific matching category using the full path format.
Examples: "Apparel & Accessories > Clothing > Tops & T-Shirts"
          "Home & Garden > Furniture > Bedroom Furniture > Beds & Bed Frames"
Confidence: high = clear match from title alone.
            medium = requires description context.
            low = genuinely unclear even with full context.
Return ONLY valid JSON matching the TaxonomyClassification schema.

USER:
Product title: {title}
product_type hint: {product_type}
First 30 words of description: {description_start}
Match to the Shopify Standard Product Taxonomy.
```

### 8.7 Product-type classification

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

## 9. Frontend Architecture

### 9.0 Frontend State Diagram

```mermaid
stateDiagram-v2
    [*] --> landing
    landing --> input: "Audit my store"
    input --> progress: handleSubmit (POST /analyze)
    input --> input: error (stays put)
    progress --> dashboard: status complete or awaiting_approval
    progress --> input: status failed and no prior report
    progress --> dashboard: status failed and prior report exists
    dashboard --> executing: handleExecute (POST /execute)
    dashboard --> input: handleRestart prefilled url (free-tier upgrade)
    dashboard --> landing: handleReset (New audit)
    executing --> dashboard: status complete
    executing --> dashboard: status failed (preserve prior report)
    dashboard --> dashboard: rollback then onReportRefresh
    dashboard --> [*]: tab close

    note right of dashboard
        Polling closure captures prior report
        so failed re-execute keeps user
        on the dashboard with the audit
        report intact.
    end note
```

### 9.1 Top-level state machine (`App.tsx`)

```ts
type Screen = 'landing' | 'input' | 'progress' | 'dashboard' | 'executing'

state: {
  screen, jobId, adminToken, merchantIntent,
  jobStatus, report, error, prefillUrl
}
```

**Polling.** A single ref-tracked `setInterval` is used. `startPolling(id, terminalStatuses)` clears any prior interval and re-arms with a fresh closure. Network errors during polling are swallowed — the next tick retries.

**Failure preservation.** When polling sees `status === 'failed'`:
1. If `status.report` is present → keep the user on the dashboard with the new report and an inline error.
2. Else if a prior `report` is in memory → keep the user on the dashboard with the prior report and an inline error.
3. Else → fall back to `screen='input'` with the error.

This guarantees a failed re-execution never erases the audit the user just sat through 60 + seconds for.

**Defensive resets.** `handleSubmit` clears `report` and `jobStatus` before starting a new analysis. `handleReset` clears everything including `prefillUrl`. `handleRestart(prefilledUrl)` is the dashboard → input transition that pre-fills the store URL (used by the free-tier "Run full scan" upgrade button).

**Report refresh.** `handleReportRefresh()` is wired down through `Dashboard → FixesTab → AgentActivity → FixRow` so a successful rollback re-fetches the job and updates the dashboard, certificate, and before/after report in one render.

### 9.2 Score utility (`utils/score.ts`)

Single source of truth for score math. Used by hero, pillar bars, certificate, and BeforeAfterReport.

```ts
PILLAR_WEIGHTS = { Discoverability: 0.20, Completeness: 0.30,
                   Consistency: 0.20, Trust_Policies: 0.15, Transaction: 0.15 }

normalizeScore(raw)   // 0..1 fraction or 0..100 percent → 0..100 integer; clamps to [0, 100]
pillarPercent(p)      // PillarScore → 0..100
overallFromPillars(p) // weighted composite, re-normalized against weight actually applied
scoreBand(score)      // { label, c, cp } — Excellent / Solid / Needs work / Critical
```

### 9.3 Progress screen (dual-mode)

`ProgressScreen` has two distinct step lists:
- `AUDIT_STEPS` (6 steps: Connecting → Ingesting → Running checks → Probing AI agents → Computing perception gap → Drafting fix plan).
- `EXECUTE_STEPS` (4 steps: Re-fetching live store data → Applying autonomous fixes → Verifying writes → Building before/after report).

`auditStep(status, pct)` and `executeStep(status, pct)` map backend status + percent onto step indices. The headline copy ("Holding the mirror up to your store…" vs "Mending the reflection on your store…") flips based on `status === 'executing'`.

### 9.4 Dashboard tabs

`Dashboard.tsx` renders five tabs:

1. **Overview** — hero score card (split ink/paper), multi-channel compliance grid, deeper-audit tile row, top-issues preview, generated-assets row.
2. **Perception** — PerceptionDiff card, per-product drift cards, MCPSimulation, CompetitorPanel (or CompetitorDiscovery when no results yet).
3. **Findings** — FindingsTable with severity filter pills.
4. **Products** — free-tier banner, HeatmapGrid, worst-5 products list.
5. **Fix Plan** — admin-token-required state OR FixApproval (pre-execution) OR AgentActivity + BeforeAfterReport + ReadinessCertificate (post-execution).

### 9.5 Asset download (`handleAssetDownload`)

```ts
async function handleAssetDownload(path, filename) {
  const url = `${API_BASE_URL}${path}`
  try {
    const headers = adminToken ? { 'X-Admin-Token': adminToken } : {}
    const res = await fetch(url, { headers })
    if (!res.ok) throw new Error(`Asset download failed: ${res.status}`)
    const blob = await res.blob()
    const objectUrl = URL.createObjectURL(blob)
    triggerDownload(objectUrl, filename)
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
  } catch {
    // Graceful fallback only: open new tab with query-string token
    const fallback = `${url}${adminToken ? `?admin_token=${encodeURIComponent(adminToken)}` : ''}`
    window.open(fallback, '_blank', 'noopener,noreferrer')
  }
}
```

Header path is the production code path. Query-string fallback exists only for environments where the JS download path is intercepted.

### 9.6 ReadinessCertificate canvas

- DPR-scaled (`window.devicePixelRatio`) for sharp output on retina displays.
- Uses only standard Canvas2D primitives — no `ctx.letterSpacing` (which is silently dropped on Firefox / Safari).
- Filters out fixes flagged `rolled_back` from the top-3 list.
- Safe wrapping around `canvas.toDataURL()` to handle (theoretical) tainted-canvas errors.

---

## 10. Environment Variables

### Backend `.env`

```
# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_MODEL=gemini-2.0-flash

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/shopmirror

# Search API (competitor discovery)
SERPAPI_KEY=...                  # optional; DDG used when unset

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

### Frontend `.env`

```
VITE_API_BASE_URL=http://localhost:8000
VITE_POLLING_INTERVAL_MS=2000
```

---

## 11. Error Handling Rules

| Scenario | Behavior | User-Facing Message |
|---|---|---|
| `products.json` returns 401 | Set `catalog_not_public=True`; continue with HTML-only checks | "Store catalog is private. Running checks on publicly available data only." |
| HTTP 429 from Shopify | `async_retry`: 1s/2s/4s, max 3 retries; then partial result | Warning finding: "Some products may not be included due to rate limiting." |
| MCP endpoint non-200 | `mcp_available=False`; fall back to Gemini simulation; UI flips to amber "Simulated AI agent responses" label | Implicit (label change) |
| Competitor URL not Shopify | `detect_shopify()` False → silently excluded | Competitor list shorter than candidates_considered |
| LLM malformed JSON | Pydantic validation fails → retry once; if still bad, mark batch unanalysed | "LLM analysis unavailable" shown for those products |
| Admin write fails | `failed_fixes`; `manual_action_items` updated; agent continues | Finding shown in "Needs your action" section |
| LangGraph iteration > 50 | Force route to `reporter_node` | Report generated; warning logged |
| Rollback fails on Shopify side | Per-fix `rollbackError` shown inline | "Rollback failed" with reason |
| Asset download fetch blocked | Fallback to query-string GET in new tab | Implicit (download still works) |
| Re-ingestion fails inside agent | Stub `MerchantData` so reporter still runs | Reporter emits degraded final report |
| Failed analysis with prior report in memory | Polling preserves the prior report; user stays on dashboard | Inline error banner above the dashboard content |
| Pillars / findings / channel_compliance missing in report | Frontend defends with `?? {}` / `?? []` everywhere | Dashboard renders empty sections gracefully |

---

## 12. Security and Production Maturity

### 12.0 Trust Boundaries Diagram

```mermaid
flowchart LR
    subgraph BrowserTrust [Browser Trust Zone]
      User([User])
      SPA[React SPA]
      User --> SPA
    end

    subgraph TLSBoundary [HTTPS · TLS 1.3]
      direction LR
      ALB1[Load Balancer]
    end

    subgraph BackendTrust [Backend Trust Zone · VPC]
      FAPI[FastAPI]
      LGAgent[LangGraph]
      Writer2[shopify_writer]
      DB1[(PostgreSQL · private subnet)]
      FAPI --> LGAgent
      LGAgent --> Writer2
      FAPI --> DB1
      LGAgent --> DB1
    end

    subgraph ExternalTrust [External Trust Zone]
      Vertex2[Vertex AI]
      Shopify3[Shopify]
      DDG[Search]
    end

    SPA -- "HTTPS · X-Admin-Token header · CORS" --> ALB1
    ALB1 --> FAPI

    FAPI -- "service account · OAuth Bearer" --> Vertex2
    Writer2 -- "X-Shopify-Access-Token header" --> Shopify3
    FAPI -- "anonymous public catalog reads" --> Shopify3
    FAPI -- "anonymous queries" --> DDG

    note1[Admin token never persisted.<br/>Held in request body or<br/>X-Admin-Token header only.]:::note
    note2[Backups store Shopify GIDs<br/>and original/new values.<br/>No tokens. No PII.]:::note

    SPA -.- note1
    DB1 -.- note2

    classDef note fill:#FFD896,stroke:#A87B3C,color:#1a1822,font-style:italic
    style BrowserTrust fill:#1a1822,color:#ECE8F5
    style BackendTrust fill:#0E0D12,color:#ECE8F5
    style ExternalTrust fill:#7E7B8C,color:#ECE8F5
```

### 12.1 Token handling

- Admin token is supplied in the request body for `/analyze` and `/execute` (HTTPS in production).
- For asset endpoints, the token is supplied via `X-Admin-Token` header (preferred) or `?admin_token=` query (legacy fallback only).
- The `_resolve_admin_token(query, header)` helper prefers the header.
- The token is **never persisted**. `analysis_jobs.has_token` is a boolean only.
- `fix_backups` stores only Shopify GIDs and field values — no tokens.
- The frontend's `handleAssetDownload` uses the header path by default; the query-string path is only used when fetch is blocked.

### 12.2 Rollback durability

- Every successful rollback patches `agent_run.executed_fixes[].rolled_back = true` and `agent_run.rolled_back_fix_ids[]` into the stored report via `patch_report_section`.
- The frontend hydrates `FixRow.rolledBack` from `result.rolled_back` on first render so the badge persists across page reloads.
- After a successful rollback, the dashboard refetches the job (`handleReportRefresh`) so the certificate and before/after report update too.
- Backups are job-scoped — `rollback_fix(..., expected_job_id=job_id)` validates ownership before restoring.

### 12.3 Frontend defensive patterns

- All optional report sections are guarded against `undefined` (`?? {}` / `?? []`).
- `OverviewTab` and root Dashboard alias `report.pillars`, `report.findings`, `report.channel_compliance`, `report.copy_paste_package`, and `worst_5_products` to local nullish-fallback variables before consumption.
- The polling closure captures the prior `report` so the failed-execute path still has the analysis report available.
- `handleSubmit` defensively clears `report` and `jobStatus` to prevent stale data leaking into a new run.
- The competitor results state is reset via `useEffect([report])` whenever the report changes (e.g. after agent run or rollback refresh).

### 12.4 Score consistency invariants

- One utility (`overallFromPillars`) drives the hero, certificate, and before/after deltas.
- `normalizeScore` accepts both 0–1 and 0–100 inputs and clamps the result to `[0, 100]`.
- Missing pillars don't drag the score to zero — the utility re-normalizes against the weight actually applied.

### 12.5 CORS

```python
CORSMiddleware(
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Disposition",
        "X-Feed-Total-Items", "X-Feed-Total-Lines", "X-Feed-Currency",
        "X-Skipped-No-Identifier", "X-Ingestion-Mode",
    ],
)
```

`expose_headers` is required so the JS download path can read `Content-Disposition` and the `X-*` feed headers from same-origin or proxy-fronted requests.

### 12.6 Rate / cost ceilings

| Surface | Ceiling | Mechanism |
|---|---|---|
| Free-tier ingestion | 10 products | Catalog-pruning before audit |
| LLM batches | 15 products / call | Hard-coded batch size |
| Worst-5 perception calls | 10 LLM calls per audit | Bounded by worst-5 selection |
| Agent iterations | 50 | Hard cap in planner |
| Fix retries | 2 | Hard cap in verifier |
| Admin re-ingestion timeouts | 30 s | httpx default |
| Agent run wall clock | tracked via `progress_pct` | Never re-fetched from DB after start |

---

## 13. Deployment Topology

### 13.1 Current Deployment (Hackathon / Pilot)

```mermaid
flowchart TB
    Dev[Developer Machine] -->|docker compose up| Local[Local PG 15<br/>+ FastAPI dev server<br/>+ Vite dev server]

    subgraph EC2_Box [AWS EC2 t3.medium]
      direction TB
      Nginx[nginx · 443<br/>TLS termination]
      U[uvicorn · 8000]
      Static[Static SPA bundle<br/>served by nginx]
      Nginx --> U
      Nginx --> Static
    end

    subgraph RDS_Box [AWS RDS db.t3.micro]
      PG[(PostgreSQL 15<br/>+ pgcrypto)]
    end

    Browser([User browser]) -->|443| Nginx
    U -->|asyncpg pool| PG
    U -->|httpx| ShopifyExt[(Shopify)]
    U -->|google-cloud-aiplatform| VertexExt[(Vertex AI)]

    GCP[GCP Service Account] -.->|JSON key in env| U

    style EC2_Box fill:#0E0D12,color:#ECE8F5
    style RDS_Box fill:#A87B3C,color:#1a1822
```

### 13.2 Future Deployment (Multi-Tenant SaaS)

```mermaid
flowchart TB
    Browser2([User]) --> CDN[CloudFront CDN<br/>SPA · cached feeds]
    CDN --> WAF[AWS WAF<br/>rate limit, bot protection]
    WAF --> ALB2[ALB · TLS · 443]

    subgraph ECS_Cluster [ECS Fargate Cluster]
      direction LR
      API1[API task · auto-scale]
      API2[API task]
      W1[Worker task · Arq]
      W2[Worker task · Arq]
    end

    ALB2 --> API1
    ALB2 --> API2
    API1 --> Q[(SQS / Redis Queue)]
    API2 --> Q
    Q --> W1
    Q --> W2

    subgraph DataTier [Data Tier · multi-AZ]
      RDS2[(RDS Postgres 15<br/>multi-AZ)]
      Replica[(Read Replica)]
      Redis2[(ElastiCache Redis)]
      S3B[(S3 Bucket<br/>certificates · feeds)]
    end

    API1 --> RDS2
    API2 --> Replica
    API1 --> Redis2
    W1 --> RDS2
    W1 --> S3B

    Sec[AWS Secrets Manager] -.-> API1
    Sec -.-> API2
    Sec -.-> W1
    Sec -.-> W2

    OTEL[OTEL Collector] --> Prom2[Prometheus + Grafana]
    Sentry2[Sentry SaaS]
    API1 --> OTEL
    W1 --> OTEL
    API1 --> Sentry2

    style ECS_Cluster fill:#0E0D12,color:#ECE8F5
    style DataTier fill:#A87B3C,color:#1a1822
```

---

## 14. Dev Store Setup

> The demo store must be intentionally broken in specific ways so the tool finds real issues and the agent fixes real things.

### Steps

1. Create a free Shopify Partner account at partners.shopify.com.
2. Create a development store from the Partner Dashboard (no credit card required).
3. Add 15–20 products across 2–3 categories (e.g. sleep accessories, bags, home goods).
4. Create a custom app in the dev store admin for the Admin API token. Required scopes: `read_products`, `write_products`, `read_content`, `write_content`, `write_script_tags`.

### Intentional breakage

| What to Break | How | Check Failed |
|---|---|---|
| Product titles | Brand-name only ('The Luna', 'Vertex', 'Apex Pro') | C2 |
| product_type field | Empty on all products | (Mode A C1 proxy; Mode B taxonomy missing) |
| Metafields | `custom.material` empty on all products | C5 |
| Variant option names | Leave as Option1 / Option2 on 5 products | C3 |
| Return policy | "We accept returns within a few weeks" | T1 |
| Schema price | Inject wrong price in theme JSON-LD | Con1 |
| robots.txt | Block `PerplexityBot` | D1a |
| GTIN | Empty barcode + empty vendor on 5 products | C4 |
| Inventory | 3 products set to "continue selling when out of stock" | A2 |
| Schema offer fields | Use a basic theme without `OfferShippingDetails` | T4 |

### What flips after agent runs

- **C1, C2, C3** — taxonomy + title + variant names (agent writes).
- **C5** — metafields (agent extracts from descriptions and writes).
- **T4** — schema injected via `scriptTagCreate` (no theme edit).
- **D1a** — manual fix instruction (theme file edit not auto-applied).
- **Con1** — schema regenerated with correct price as a copy-paste block.

---

## 15. 8-Day Build Plan (Historical Reference)

| Day | Backend | Frontend |
|---|---|---|
| 1 | Project skeleton, Postgres + docker-compose, `001_initial.sql`, `ingestion.py` Mode A | React + TS + Tailwind, `api/client.ts` mock, InputScreen, ProgressScreen |
| 2 | `schemas.py`, all 19 checks in `heuristics.py`, AI Readiness Score in `report_builder.py`, `/analyze` + `/jobs/{id}` | Dashboard, ReadinessScore badge, FindingsTable |
| 3 | `llm_analysis.py`, `perception_diff.py`, `query_matcher.py` | HeatmapGrid, MultiChannelDashboard, QueryMatchSimulator, PerceptionDiff |
| 4 | `competitor.py`, `mcp_simulation.py` | CompetitorPanel, MCPSimulation |
| 5 | Real API integration | Replace mocks with real calls |
| 6 | LangGraph: `state.py`, `nodes.py`, `tools.py`, `graph.py` (with AsyncPostgresSaver same day), `shopify_writer.py` (incl. taxonomy + Script Tags + rollback) | AgentActivity, FixApproval, DiffViewer |
| 7 | `/before-after`, copy-paste package, full loop test on dev store | BeforeAfterReport, ReadinessCertificate (canvas + PNG export) |
| 8 | Demo store breakage applied, deploy to EC2 + RDS, demo rehearsal | Final polish, error states, loading states |

---

## 16. Operational Checklist

Before each demo / deployment:

- [ ] `docker compose up -d` from `shopmirror/` brings up Postgres healthy.
- [ ] `001_initial.sql` and `002_add_script_tag.sql` both applied.
- [ ] `backend/.env` has `GOOGLE_CLOUD_PROJECT`, `DATABASE_URL`, `VERTEX_MODEL`.
- [ ] `backend/start_backend.ps1` (or `uvicorn app.main:app`) starts with no traceback.
- [ ] `GET /health` returns `{"status":"ok"}`.
- [ ] Frontend `npm run dev` renders the landing page.
- [ ] Run full audit on the dev store; check that:
  - [ ] Hero score renders with a band color.
  - [ ] Multi-channel grid populated for all 5 channels.
  - [ ] Deeper-audit tile row shows 4 tiles with non-grey colors (where data is available).
  - [ ] Heatmap renders with at least 3 active columns.
  - [ ] Perception card shows intent + AI perception.
  - [ ] MCP simulation shows mode label (live or simulated).
- [ ] Run fix execution; check that:
  - [ ] Progress screen shows execute steps, not audit steps.
  - [ ] AgentActivity shows applied / reversed (if any) / failed counters.
  - [ ] Each rollback persists across page reload.
  - [ ] BeforeAfterReport shows pillar deltas with at least one improved.
  - [ ] Certificate downloads as a PNG.
- [ ] Run asset downloads — verify no `?admin_token=` appears in browser history.
- [ ] `npx tsc --noEmit` clean.
- [ ] `python -m py_compile app/main.py app/db/queries.py app/schemas.py` clean.

---

## 17. What NOT to Build

- Do NOT use `requests` (use httpx). Do NOT use SQLAlchemy (use asyncpg). Do NOT use Celery (use FastAPI BackgroundTasks).
- Do NOT implement Shopify OAuth. The Admin token is supplied by the merchant as a plain string at request time.
- Do NOT write to Shopify theme files. Schema fixes use Script Tags or copy-paste output.
- Do NOT auto-write policy text. Policy fixes are draft suggestions only.
- Do NOT use Playwright or Selenium. All HTML fetching is raw httpx + BeautifulSoup.
- Do NOT add vector databases. There are no embeddings in this project.
- Do NOT implement user authentication. ShopMirror is a stateless URL-in, report-out tool.
- Do NOT log the admin token. Anywhere. Ever.
- Do NOT put the admin token in a URL string the dashboard renders to the user.

---

## 18. Code Quality Rules

- Every service function has a docstring stating: what it does, what it takes, what it returns.
- Every LLM prompt is defined as a constant string at the top of the file it is used in.
- Every Pydantic model has field descriptions for every field.
- All findings have `spec_citation` filled with the real source document name.
- Heuristic functions are pure: same input always produces same output. No side effects.
- Tools in `agent/tools.py` are decorated with `@tool` from langchain. Each has a clear description string.
- Frontend components defensively guard against missing report fields with `?? {}` / `?? []`.
- All score math goes through `utils/score.ts` — no inline `Math.round(score * 100)` anywhere else.
- All admin-token-bearing fetches go through `handleAssetDownload` — no direct `<a href=…?admin_token=…>` anywhere.

---

## 19. Glossary

| Term | Meaning |
|---|---|
| Mode A / Mode B | URL-only ingestion vs URL + Admin token ingestion |
| MCP | Model Context Protocol — Shopify's `{store}/api/mcp` endpoint |
| Script Tag | Shopify Admin resource that injects JS into the storefront without theme edits |
| Standard Product Taxonomy | Shopify's official category tree (GIDs) — routing layer for AI catalogs |
| llms.txt | Emerging standard analogous to robots.txt that tells AI agents how to use a site |
| Gap score | Per-product severity-weighted sum of failed checks |
| AI Readiness Score | 0–100 weighted composite across all 5 pillars |
| Channel compliance | Per-channel READY / PARTIAL / BLOCKED / NOT_READY status |
| `agent_run` | The block patched into `report_json` after a fix execution; carries `executed_fixes`, `before_after`, `rolled_back_fix_ids` |
| `scan_limited` | Free-tier flag indicating only the first N products were audited |
| `_resolve_admin_token` | Backend helper preferring the `X-Admin-Token` header over the legacy `?admin_token=` query param |
