# ShopMirror — Decision Log

Core technical and product decisions only. Format: **Chose X over Y — reason.**

---

## Architecture

- **Internal domain objects use `dataclasses`, not Pydantic `BaseModel`** — domain objects like `MerchantData` and `Finding` carry data, they don't need validation. Pydantic is reserved for LLM structured output and API request/response shapes.

- **LLM calls use `with_structured_output(PydanticModel)` exclusively** — no free-text parsing anywhere. Every LLM call has a typed Pydantic schema; if the model can't fill it, it fails loudly rather than silently returning garbage.

- **Fix backups written to DB before every Shopify write** — rollback is a first-class feature, not an afterthought. Every `shopify_writer.py` function creates a `fix_backups` row before mutating anything.

- **Shopify Admin token is plain string input, no OAuth** — hackathon scope. OAuth adds a full auth flow and redirect handling; merchant pastes their token directly into the UI.

- **FastAPI `BackgroundTasks` for job execution, not Celery** — Celery requires a broker (Redis/RabbitMQ) and worker processes. `BackgroundTasks` runs in-process and is sufficient for a single-server hackathon demo. Known tradeoff: jobs are lost on server restart.

## Data / Storage

- **`update_job_report` atomically sets `status`, `progress_pct`, and `completed_at`** — writing the report and closing the job are one operation. Separate calls risk a job stuck in a non-terminal state if the server crashes between them.

- **Queries return `dict | None`, not dataclasses** — asyncpg `Record` maps directly to dict; API handlers serialise straight to JSON. A dataclass round-trip adds no value.

## Competitor Discovery

- **DDGS (DuckDuckGo) as primary search, SerpAPI as optional upgrade** — DDGS is free, requires no key, and has no per-query cost, keeping the free tier truly $0 to operate. SerpAPI is configured via `SERPAPI_KEY` env var and activates automatically when set. In a production system this maps cleanly to a tiered cost model: free-tier analyses use DDGS, paid-tier analyses (or high-volume deployments) configure SerpAPI for guaranteed SLA and higher rate limits. The abstraction is a single `search_competitors(query)` function in `competitor.py` that checks for `SERPAPI_KEY` and routes accordingly — callers never know the difference.

## LangGraph State Persistence (Deferred to Day 6)

- **LangGraph graph checkpointing deferred — current design is in-memory only** — `BackgroundTasks` runs the graph in-process with no checkpoint saver. If the server restarts between the approval gate interrupt and `POST /execute`, the graph state is lost. This is a known limitation. On Day 6 (LangGraph implementation day) we will wire in LangGraph's `AsyncPostgresSaver` using the existing asyncpg pool — the DB connection is already there, checkpointing is a configuration addition not a structural change. This is the correct production pattern: stateful agent runs should be durable, not held in process memory.

## API Schemas

- **API request/response Pydantic schemas live in `app/schemas.py`, not `app/models/`** — models/ holds internal domain dataclasses with no validation. schemas.py holds FastAPI wire shapes (Pydantic BaseModel) validated on every request/response. File is created empty with all shapes commented — implement on Day 2 before adding any route handlers to main.py.

- **`update_job_report` takes an optional `status` parameter (default `'complete'`)** — free tier always passes complete. Paid tier passes `'awaiting_approval'` after analysis so the job stays open for fix execution. `completed_at` is only stamped when status is `'complete'`.

## Rollback Storage

- **Fix backups stored in `fix_backups` DB table, not Shopify metafields** — the PRD mentions "saved to `shopmirror.backup.[field]` metafield on the Shopify product". This is wrong and was not implemented. DB storage is correct: it's queryable, auditable, doesn't pollute the merchant's Shopify data, and doesn't require an extra write to a metafield namespace we don't own. Rollback reads from `fix_backups` and writes the original value back via Admin GraphQL.

## Audit Findings Accuracy

- **Schema/HTML checks (Con1, Con2, D4) are sampled across 5 pages only** — only the top 5 products by variant count are crawled. Findings from these checks will be reported as "based on X crawled pages" in the finding's `impact_statement`, not extrapolated to the full catalog. This is honest reporting — we checked what we could access without an Admin token.

## Dependencies

- **`langchain>=0.3.0` + `langgraph>=0.2.28`** — `langgraph==0.2.0` predates langchain 0.3's `langchain-core>=0.3` requirement. `langgraph 0.2.28` is the first release with compatible `langchain-core 0.3.x` support.

---

## Strategic Rebuild — Accuracy + Shopify-Native Upgrades

- **Replaced D1 "CRITICAL — AI cannot see your products" with D1a (MEDIUM) + D1b (CRITICAL)** — Shopify products reach ChatGPT Shopping via Shopify's Catalog API, not web crawling. Blocking GPTBot in robots.txt has no effect on Shopify Catalog visibility. D1a accurately flags web-index AI impact at MEDIUM; D1b is the real CRITICAL check: Shopify Catalog eligibility via taxonomy + required fields.

- **Replaced C1 (product_type string check) with Shopify Standard Taxonomy mapping** — Shopify's 2024 Standard Product Taxonomy is the actual routing layer for Shopify Catalog, Google Shopping, and Meta Catalog. A non-empty product_type string (e.g. "stuff") passes the old check with zero routing value. A taxonomy GID routes products to the correct AI category. Autonomous fix: Gemini classifies → `productUpdate` mutation writes `category` field GID.

- **Removed D4 (price in raw HTML) and T3 (AggregateRating schema)** — D4 universally passes Shopify Liquid-rendered stores; T3 universally fails default Shopify themes. Checks that don't discriminate provide no signal. Slots reallocated to D1b (Catalog eligibility) and D5 (Markets translation).

- **T4 fix upgraded from copy-paste to autonomous Script Tags injection** — Shopify's `scriptTagCreate` Admin GraphQL mutation injects JSON-LD schema into every storefront page without any theme modification. Fully reversible via `scriptTagDelete`. `script_tag_id` stored in `fix_backups` table for rollback. This converts the most CRITICAL finding from a finding merchants ignore into a finding the agent autonomously fixes.

- **AsyncPostgresSaver wired same day as LangGraph graph** — The approval gate interrupt requires persistent graph state. Without `AsyncPostgresSaver`, the paused graph lives in process memory and silently breaks under multi-worker deployment. No longer deferred; both are Day 6.

- **Added AI Readiness Score (0–100) as headline metric** — Weighted composite across 5 pillars (Discoverability 20%, Completeness 30%, Consistency 20%, Trust_Policies 15%, Transaction 15%). Every credible SaaS tool has a single headline score merchants can track. This is the demo's primary emotional anchor.

- **Added Multi-Channel Compliance Dashboard** — Maps existing checks to 5 channels: Shopify Catalog, Google Shopping, Meta Catalog, Perplexity Web, ChatGPT Shopping. Each shows READY/PARTIAL/BLOCKED. No competitor tool provides this single view at this price point.

- **Added AI Query Match Simulator** — Closes the evidence-of-impact gap. One LLM call parses the query into structured attributes; deterministic matching loop runs against machine-readable product fields. Shows merchants exactly how many of their products would match an AI shopping query, before and after fixes. No unverifiable claims about real ChatGPT results.

- **Added AI Readiness Certificate** — PNG-exportable before/after summary generated after agent run. Retention mechanism + viral distribution channel for merchant communities.

## Day 6 Implementation

- **Admin token not stored in DB; fix agent runs in dry-run mode when token unavailable** — storing plaintext admin tokens in PostgreSQL is a security risk. For the hackathon, the POST /execute route re-runs the agent without live writes when the token isn't available from the DB row. Production fix: store an encrypted token in a short-TTL session cache (Redis). The dry-run path still exercises the full LangGraph state machine and reports what would have been written.

- **Approval gate implemented as pass-through, not LangGraph interrupt** — the `/execute` request already carries `approved_fix_ids`, so the graph doesn't need to interrupt and wait. The `approval_gate_node` exists structurally (matching the spec) but doesn't call `interrupt()`. Production multi-turn approval would add the interrupt; for the demo the approval step is handled in the frontend before calling `/execute`.

- **fix plan generation runs in analysis pipeline (not agent planner_node)** — the spec says planner_node generates the fix plan on first agent run. For the UI flow (GET /fix-plan before any agent invocation), the plan must be in the DB first. Generating it at the end of the analysis pipeline achieves both: the endpoint works immediately, and the planner_node reads the same plan from state.

## Day 3 Implementation

- **`perception_diff.py` uses one batch LLM call for all products, not two calls per product** — spec originally described 2 LLM calls per product (`get_product_perception`). Replaced with a single `BatchProductPerceptionOutput` call across up to 10 products. Fewer LLM calls, lower latency, same analytical quality — correct tradeoff for a hackathon demo with live API costs.

- **`llm_analysis.py` LLM instantiation is lazy (first call), not module-level** — `ChatVertexAI(model="gemini-2.0-flash", temperature=0)` deferred to first invocation. Prevents import-time crash in CI or local dev environments without Vertex AI credentials configured.
