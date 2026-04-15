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
