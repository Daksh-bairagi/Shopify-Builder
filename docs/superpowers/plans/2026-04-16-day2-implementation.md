# Day 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to execute this plan task-by-task.

**Goal:** Implement the full audit pipeline for Day 2 — schemas, 19 heuristic checks, report assembly, and API routes.

**Architecture:** Four sequential tasks. schemas.py must land first (API contract). heuristics.py and report_builder.py are independent of each other but both feed into main.py routes.

**Tech Stack:** Python 3.12, FastAPI, asyncpg, Pydantic v2, dataclasses

**Execution order:** Task 1 → Task 2 → Task 3 → Task 4

---

## Task 1: schemas.py — All Pydantic API shapes

**File:** `shopmirror/backend/app/schemas.py`

Implement all commented shapes already documented in the file. Add also:
- `QueryMatchResponse` for `GET /jobs/{id}/query-match`

All fields must have correct types. No extra fields beyond spec.

---

## Task 2: heuristics.py — 19 deterministic check functions

**File:** `shopmirror/backend/app/services/heuristics.py`

Implement all 19 check functions + `run_all_checks`. Zero LLM calls. Pure functions.

Checks: D1a, D1b, D2, D3, D5, C1, C2, C3, C4, C5, C6, Con1, Con2, Con3, T1, T2, T4, A1, A2

---

## Task 3: report_builder.py — Score + compliance + report assembly

**File:** `shopmirror/backend/app/services/report_builder.py`

Implement:
- `calculate_ai_readiness_score(pillars)` → float 0-100
- `calculate_channel_compliance(findings)` → ChannelCompliance
- `calculate_pillar_scores(findings, total_checks_per_pillar)` → dict[str, PillarScore]
- `get_worst_products(products, findings, n=5)` → list[ProductSummary]
- `assemble_report(...)` → AuditReport

---

## Task 4: main.py — POST /analyze + GET /jobs/{id}

**File:** `shopmirror/backend/app/main.py`

Wire two routes using BackgroundTasks:
- `POST /analyze` — validates URL, creates job, starts background pipeline
- `GET /jobs/{id}` — polls job status + returns report when complete
- `GET /jobs/{id}/query-match` — runs query matcher against stored job data
