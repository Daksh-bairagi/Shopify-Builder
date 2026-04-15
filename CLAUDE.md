
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

## Hard Rules — Never Break These
- Always read both spec files before writing any code
- Never deviate from directory structure in TECHSPEC Section 1
- Never use requests library — use httpx
- Never use SQLAlchemy — use asyncpg
- Never use Celery — use FastAPI BackgroundTasks
- Never implement Shopify OAuth — Admin token is plain string input
- Never write to Shopify theme files — schema fixes are copy-paste only
- Never auto-write policy text — policy fixes are drafts only
- All LLM calls use ChatVertexAI(model="gemini-2.0-flash", temperature=0)
- All LLM calls use with_structured_output(PydanticModel) — never parse free text
- All service functions are async
- All I/O uses httpx or asyncpg

## Stack
Python 3.11 / FastAPI / React 18 / PostgreSQL 15 / 
LangGraph / LangChain / Google Cloud Vertex AI / AWS EC2+RDS

## Project Root
All code lives under `shopmirror/` in this repo.
- Backend entry: `shopmirror/backend/app/main.py`
- Frontend entry: `shopmirror/frontend/src/main.tsx`
- Local DB: `docker compose up -d` from `shopmirror/`

## Model Import Paths
```python
from app.models.merchant import MerchantData, Product, ProductVariant, ProductImage, ProductOption, Collection, Policies
from app.models.findings import Finding, PillarScore, AuditReport, PerceptionDiff, ProductPerception, MCPResult, CompetitorAudit, CompetitorResult, CopyPasteItem, ProductSummary
from app.models.fixes import FixItem, FixPlan, FixResult
from app.models.jobs import AnalysisJob, JobStatus, JobProgress
```

## What Is Already Built
- `shopmirror/` — full directory skeleton (all folders + empty files)
- `backend/app/db/migrations/001_initial.sql` — analysis_jobs + fix_backups tables
- `backend/requirements.txt` — all 15 pinned dependencies
- `backend/.env.example` — all env vars with comments
- `frontend/.env.example` — VITE_API_BASE_URL, VITE_POLLING_INTERVAL_MS
- `docker-compose.yml` — postgres:15, db service, named volume for persistence
- `backend/app/models/merchant.py` — MerchantData, Product, Collection, Policies + sub-types
- `backend/app/models/findings.py` — Finding, AuditReport, PillarScore, MCPResult, PerceptionDiff, CompetitorResult, CopyPasteItem
- `backend/app/models/fixes.py` — FixItem, FixPlan, FixResult
- `backend/app/models/jobs.py` — AnalysisJob, JobStatus, JobProgress