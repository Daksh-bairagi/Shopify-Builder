# ShopMirror

ShopMirror is an AI representation auditor for Shopify merchants. It scans catalog and storefront data, identifies gaps that reduce visibility in AI shopping systems, and produces fix plans with verification and rollback support.

## What Belongs In This Repo

- Working application code in `shopmirror/`
- Product documentation in `ShopMirror_PRD.md`
- Technical documentation in `ShopMirror_TechSpec.md`
- Architectural and product decisions in `DECISION_LOG.md`

## Project Structure

```text
shopmirror/
  backend/   FastAPI API, audit engine, agent workflow, tests
  frontend/  React dashboard and remediation UI
  scripts/   Local helper scripts
```

## Local Development

```powershell
cd shopmirror
docker compose up -d
```

Backend entrypoint: `shopmirror/backend/app/main.py`  
Frontend entrypoint: `shopmirror/frontend/src/main.tsx`

## Notes

This repository is intentionally kept focused on the shipped product and its core documentation. Local assistant tooling, personal workspace settings, and generated caches should stay out of version control.
