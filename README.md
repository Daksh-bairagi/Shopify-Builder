# ShopMirror

ShopMirror is an AI representation auditor for Shopify merchants. It analyzes storefront and catalog data, finds issues that reduce AI visibility, and helps merchants move from audit to fix plan to verified improvement.

## Problem Statement

Many Shopify stores have good products but weak AI-facing data. Missing taxonomy, inconsistent trust signals, incomplete product attributes, and weak structured catalog data make it harder for AI shopping systems to classify, trust, and surface products. ShopMirror addresses this as a Track 5 problem by making those representation gaps visible and turning them into an actionable remediation workflow.

## Features

- AI readiness audit for Shopify storefront and catalog data
- Findings dashboard with severity, evidence, and impact
- AI visibility and query-match style analysis
- Fix planning with approval flow
- Before/after readiness reporting
- Rollback-aware remediation flow for supported changes

## Testing

ShopMirror includes both white-box and black-box testing for the backend system(total 256 tests).

- White-box tests cover internal logic such as deterministic audit checks, score calculation, fix-plan generation, node routing, dependency ordering, and before/after reporting behavior.
- Black-box tests cover API contracts such as status codes, response shapes, auth guards, job-state guards, execute/rollback behavior, and error handling.
- External infrastructure is mocked in the backend test suite, so tests validate system behavior without requiring live Shopify, database, or AI-provider calls.

Test suites live in `shopmirror/backend/tests/white_box/` and `shopmirror/backend/tests/black_box/`.

## Product Screenshots

### Landing

![ShopMirror Landing](product_ss/landing.png)

### Audit In Progress

![ShopMirror Analyzing](product_ss/analyzing.png)

### Heatmap and Findings

![ShopMirror Heatmap](product_ss/heatmap.png)

### Fix Approval

![ShopMirror Fix Flow](product_ss/fix.png)

### Readiness Report

![ShopMirror Readiness Report](product_ss/readiness.png)

## Demo Video

Add the 3-5 minute narrated walkthrough link here.

- Demo link: https://drive.google.com/file/d/1CcnzKo2OSRM1Wp47D4TLg0LcpFdnoi4P/view?usp=sharing

## Repository Contents

- `shopmirror/` - application source code
- `ShopMirror_PRD.md` - product requirements document
- `ShopMirror_TechSpec.md` - technical specification
- `DECISION_LOG.md` - key architecture and product decisions

## Tech Stack

- Backend: FastAPI, Python, asyncpg, LangGraph, LangChain
- Frontend: React, TypeScript, Vite, Tailwind
- Database: PostgreSQL via Docker Compose
- AI providers: Gemini plus optional external provider probes

## Prerequisites

Before you start, make sure you have:

- Python 3.11+ or 3.12
- Node.js 18+
- npm
- Docker Desktop
- A PostgreSQL-compatible Docker environment

## Quick Start

If you want the fastest setup path, run this from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_shopmirror.ps1
```

This bootstrap script:

- creates `shopmirror/backend/.venv` if it does not exist
- installs backend dependencies from `requirements.txt`
- installs frontend dependencies with `npm install`
- creates `shopmirror/backend/.env` from `.env.example` if missing


After the script finishes:

1. Fill in `shopmirror/backend/.env`
2. Start the database
3. Start the backend
4. Start the frontend

## Environment Variables

### Backend

Copy `shopmirror/backend/.env.example` to `shopmirror/backend/.env` if it does not already exist.

Core values:

```env
VERTEX_MODEL=gemini-2.0-flash
GEMINI_API_KEY=your-gemini-api-key
DATABASE_URL=postgresql://user:pass@localhost:5432/shopmirror
ENVIRONMENT=development
LOG_LEVEL=INFO
```

Optional provider keys:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
PERPLEXITY_API_KEY=
PERPLEXITY_MODEL=sonar-pro
ANTHROPIC_API_KEY=
CLAUDE_MODEL=claude-sonnet-4-6
```

Optional integrations:

```env
SERPAPI_KEY=
```

### Frontend

Copy `shopmirror/frontend/.env.example` to `shopmirror/frontend/.env`.

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_POLLING_INTERVAL_MS=2000
```

## Installation

### Option 1: Standard setup

#### 1. Clone the repository

```powershell
git clone https://github.com/Daksh-bairagi/Shopify-Builder.git
cd Shopify-Builder
```

#### 2. Set up the backend

```powershell
cd shopmirror\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Update `.env` with your keys and local values.

#### 3. Set up the frontend

```powershell
cd ..\frontend
npm install
Copy-Item .env.example .env
```

#### 4. Start the database

```powershell
cd ..
docker compose up -d
```

### Option 2: One-command bootstrap

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_shopmirror.ps1
```

This is the easier path for local setup, but the manual steps above are included because that is the format most GitHub users expect when they want to understand exactly what is happening.

## Running the Application

### Start the backend

Recommended:

```powershell
powershell -ExecutionPolicy Bypass -File .\shopmirror\backend\start_backend.ps1
```

Manual:

```powershell
cd shopmirror\backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

### Start the frontend

```powershell
cd shopmirror\frontend
npm run dev
```

### Start the database if not already running

```powershell
cd shopmirror
docker compose up -d
```

## Local URLs

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Backend health check: `http://localhost:8000/health`

## Common Setup Notes

- `GEMINI_API_KEY` is needed for the direct Gemini-based AI visibility probe.
- `VERTEX_MODEL` is just the model name selector used by the app.
- The normal admin-token flow does not use backend env vars. Paste the Shopify Admin token in the app UI when you want an admin-token audit.
- `SERPAPI_KEY` is optional if you are okay with degraded or alternate competitor discovery behavior.

## Project Structure

```text
shopmirror/
  backend/
    app/
    tests/
    requirements.txt
    start_backend.ps1
  frontend/
    src/
  scripts/
```

## Documentation

- [ShopMirror_PRD.md](./ShopMirror_PRD.md)
- [ShopMirror_TechSpec.md](./ShopMirror_TechSpec.md)
- [DECISION_LOG.md](./DECISION_LOG.md)
- [CONTRIBUTION_NOTE.md](./CONTRIBUTION_NOTE.md)

## Notes

This repository is intentionally kept focused on the shipped product and its core documentation. Personal workspace settings, local secrets, generated caches, and assistant-specific tooling should stay out of version control.
