# ShopMirror — Test Suite

## Structure

```
tests/
├── conftest.py                          Shared pytest fixtures and API client factory
├── fixtures/
│   └── merchant_data.py                 Factory helpers for MerchantData, Product, etc.
├── white_box/
│   ├── test_heuristics.py               All 19 deterministic audit checks (180+ cases)
│   ├── test_report_builder.py           Pillar scoring, AI readiness score, channel compliance
│   ├── test_fix_plan.py                 Fix plan generation, deduplication, ordering
│   └── test_nodes_routing.py            LangGraph node routing, before/after delta, schema generation
└── black_box/
    ├── test_api_health_analyze.py        GET /health and POST /analyze contracts
    ├── test_api_jobs.py                  GET /jobs/* status, fix-plan, before-after
    └── test_api_execute_rollback.py      POST /execute and POST /rollback guard conditions
```

## Running Tests

From the `backend/` directory:

```bash
# Install test dependencies (if not already installed)
pip install pytest pytest-asyncio httpx

# Run the full suite
pytest

# Run only white-box tests
pytest tests/white_box/

# Run only black-box tests
pytest tests/black_box/

# Run a specific file
pytest tests/white_box/test_heuristics.py -v

# Run a specific test class or test
pytest tests/white_box/test_heuristics.py::TestCheckRobotCrawlers -v
pytest tests/white_box/test_heuristics.py::TestCheckRobotCrawlers::test_gptbot_full_block_fires -v

# Run with coverage
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

## Test Philosophy

### White-Box Tests
Tests that know the internal implementation. They verify:
- **Boundary conditions** — exactly at thresholds (e.g., exactly 80% catalog eligibility, exactly 70% alt text coverage, price diff exactly $0.01)
- **Edge cases** — empty products, None values, whitespace-only strings, zero prices
- **Mode gates** — checks that only run in `admin_token` mode are skipped in `url_only` mode
- **Spec invariants** — D1a severity is always MEDIUM (never CRITICAL), single finding per check per `run_all_checks()` call
- **Deduplication logic** — store-level fixes are deduplicated, product+type pairs aren't duplicated
- **Dependency ordering** — `map_taxonomy` always precedes `improve_title` in the fix plan

### Black-Box Tests
Tests that treat the API as a black box and only care about HTTP contracts. They verify:
- **Status codes** — 200/202/400/403/404/422/500 in the right scenarios
- **Response shapes** — required fields present, correct types
- **Auth guards** — endpoints that need admin token return 403 without it
- **State guards** — `/execute` only works when job is `awaiting_approval`
- **Security** — report data not exposed on in-progress jobs, backups scoped to correct job_id

All external I/O (DB pool, Shopify API, analysis pipeline) is mocked via `unittest.mock.patch`
so tests run without any infrastructure and complete in under 5 seconds.

## Key Test Cases

| File | Notable Cases |
|------|--------------|
| `test_heuristics.py` | D1a wildcard vs named-bot distinction; D1b exactly-80% boundary; C6 empty-string alt counts as missing; Con1 price within $0.01 tolerance; A2 untracked+continue does NOT fire (only shopify+continue does) |
| `test_report_builder.py` | Same check_id twice counts as 1 failed check; higher-weight pillar hurts score more; `get_worst_products` gap score accumulates across findings |
| `test_fix_plan.py` | T1+T2 both map to `suggest_policy_fix` → deduplicated to 1 item; D1b missing-taxonomy-only creates `map_taxonomy` but not `repair_catalog_eligibility`; 30 affected products → capped at 20 |
| `test_nodes_routing.py` | Iteration guard stops at 50; `_compute_before_after` distinguishes improved vs unchanged checks; return-days extracted from policy text |
| `test_api_execute_rollback.py` | Wrong job status → 400 not 500; backup belongs to different job → 404; Shopify writer error → 500 |

## Dependencies

- `pytest >= 7.0`
- `pytest-asyncio >= 0.21`
- `httpx >= 0.24` (required by FastAPI TestClient)
- `fastapi[testclient]`

No real database, no Shopify API credentials, and no Google Vertex AI keys are needed to run
the test suite. All external calls are mocked.
