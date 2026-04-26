
# ShopMirror — Project Context

## What This Is
ShopMirror is an agentic AI system that audits Shopify merchant 
product data against AI shopping platform requirements, identifies 
structural gaps causing AI invisibility, and fixes them autonomously.

Hackathon: Kasparro Agentic Commerce Hackathon, Track 5
Build window: 8 days

## Spec Files
Two specification files live in this repo root. Read both before 
writing any code in every session:
- `ShopMirror_PRD (1).md` — product requirements, features, demo script
- `ShopMirror_TechSpec (1).md` — directory structure, API contracts, 
  service specs, DB schema, LangGraph agent spec, all prompts, 
  8-day build plan

## Git Commits
Never add `Co-Authored-By` lines to commit messages. Commits should appear as authored by Daksh Bairagi only.

## Decision Log
A running log of every meaningful build decision lives in `DECISION_LOG.md` at the repo root.

**Append an entry to `DECISION_LOG.md` only for core decisions:**
- Choosing one architecture, pattern, or library over a real alternative
- A product-level call that affects user-facing behaviour
- Resolving a genuine spec ambiguity in a specific direction

Do NOT log: version bumps, minor code style choices, tooling config, file organisation. If the decision wouldn't matter to someone reading the codebase in 6 months, skip it.

Entry format: `**Chose X over Y — reason.**` One entry per decision, 1–2 sentences max.

## Session Protocol — Hard Rules, Every Session

### On Session Start (BEFORE reading any code file)
1. The session-start system-reminder already shows a claude-mem timeline with observation IDs.
2. **Call `get_observations([IDs])` on the most recent 3–5 IDs** to load full context from memory instead of re-reading source files. This is the token-efficient path — 300 tokens/observation vs thousands for file reads.
3. Only read source files if the observations don't cover the specific detail needed.

```
get_observations([most_recent_IDs_from_timeline])
```

### Before Claiming Any Work Complete (BEFORE every commit)
1. **Invoke `superpowers:verification-before-completion`** — no exceptions.
2. Run the actual verification command (e.g. `npx tsc --noEmit`, `pytest`, build check).
3. Read the full output and exit code.
4. Only state "done" after evidence confirms it.

### Before Any Feature / Creative Work
- Invoke `superpowers:brainstorming` if requirements are unclear.
- Invoke `superpowers:systematic-debugging` before proposing any bug fix.

### Why These Are Hard Rules
Skipping session-start memory loading wastes 10–50k tokens re-reading files that are already captured as observations. Skipping verification-before-completion produces false completion claims. Both have happened — they are not acceptable defaults.

---

## Hard Rules — Never Break These
- Always read both spec files before writing any code
- Never deviate from directory structure in TECHSPEC Section 1
- Never use requests library — use httpx
- Never use SQLAlchemy — use asyncpg
- Never use Celery — use FastAPI BackgroundTasks
- Never implement Shopify OAuth — Admin token is plain string input
- Never write to Shopify theme files — schema fixes use Script Tags API or copy-paste only
- Never auto-write policy text — policy fixes are drafts only
- All LLM calls use ChatVertexAI(model="gemini-2.0-flash", temperature=0)
- All LLM calls use with_structured_output(PydanticModel) — never parse free text
- All service functions are async
- All I/O uses httpx or asyncpg
- All Script Tags injection uses scriptTagCreate Admin GraphQL mutation — never theme file mutation
- All taxonomy writes use Shopify Standard Taxonomy GID format — never raw strings to category field
- AsyncPostgresSaver MUST be wired on the same day as the LangGraph graph (Day 6) — never deferred separately
- D1a check severity is MEDIUM — never CRITICAL; robots.txt does not affect Shopify Catalog pipeline

## Stack
Python 3.12 / FastAPI / React 18 / PostgreSQL 15 / 
LangGraph / LangChain / Google Cloud Vertex AI / AWS EC2+RDS

## Project Root
All code lives under `shopmirror/` in this repo.
- Backend entry: `shopmirror/backend/app/main.py`
- Frontend entry: `shopmirror/frontend/src/main.tsx`
- Local DB: `docker compose up -d` from `shopmirror/`

## Model Import Paths
```python
from app.models.merchant import MerchantData, Product, ProductVariant, ProductImage, ProductOption, Collection, Policies
from app.models.findings import (Finding, PillarScore, AuditReport, PerceptionDiff, ProductPerception,
    MCPResult, CompetitorAudit, CompetitorResult, CopyPasteItem, ProductSummary,
    ChannelStatus, ChannelCompliance, QueryMatchResult)
from app.models.fixes import FixItem, FixPlan, FixResult
from app.models.jobs import AnalysisJob, JobStatus, JobProgress
```

## What Is Already Built
- `shopmirror/` — full directory skeleton (all folders + empty files)
- `backend/app/db/migrations/001_initial.sql` — analysis_jobs + fix_backups tables; fix_id UNIQUE
- `backend/app/db/migrations/002_add_script_tag.sql` — adds script_tag_id column to fix_backups
- `backend/requirements.txt` — all dependencies incl. duckduckgo-search, gql[aiohttp]
- `backend/.env` + `backend/.env.example` — all env vars, DATABASE_URL pre-filled for Docker
- `frontend/.env.example` — VITE_API_BASE_URL, VITE_POLLING_INTERVAL_MS
- `docker-compose.yml` — postgres:15, named volume
- `backend/app/models/merchant.py` — MerchantData, Product, Collection, Policies + taxonomy_by_product, markets_by_product, metafield_definitions (all with default_factory)
- `backend/app/models/findings.py` — Finding, AuditReport (with ai_readiness_score, channel_compliance, query_match_results), PillarScore, MCPResult, PerceptionDiff, CompetitorResult, CopyPasteItem, ChannelStatus, ChannelCompliance, QueryMatchResult
- `backend/app/models/fixes.py` — FixItem (with new fix types), FixPlan, FixResult (with script_tag_id)
- `backend/app/models/jobs.py` — AnalysisJob, JobStatus, JobProgress
- `backend/app/schemas.py` — EMPTY FILE — all API request/response Pydantic schemas go here; implement on Day 2 before adding routes to main.py
- `backend/app/db/connection.py` — asyncpg pool, get_pool(), close_pool()
- `backend/app/db/queries.py` — create_job(), update_job_report(), update_job_error(), save_fix_backup(script_tag_id param added)
- `backend/app/services/query_matcher.py` — AI Query Match Simulator: parse_query_attributes, match_products, run_default_queries
- `backend/app/utils/retry.py` — async_retry decorator, 3 retries, 1/2/4s, 429+503 only
- `backend/app/utils/validators.py` — validate_shopify_url(), detect_shopify()
- `backend/app/main.py` — FastAPI app, lifespan, /health; route stubs commented with day + schema imports needed
- `backend/app/__init__.py` + all subpackage `__init__.py` — package structure complete

## Known Deferred Items
- **`schemas.py` implementation** — file exists, all shapes commented inside. Implement on Day 2 before writing any route handlers in main.py.
- **`dataclasses.asdict()`** — when passing AuditReport or any domain dataclass to `update_job_report`, always call `dataclasses.asdict()` first. json.dumps cannot serialize dataclasses directly.
- **Migration 002** — run `002_add_script_tag.sql` after `001_initial.sql` in any fresh environment.