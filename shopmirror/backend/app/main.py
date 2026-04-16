import dataclasses
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException

from app.db.connection import close_pool, get_pool
from app.db.queries import (
    create_job,
    get_job,
    update_job_error,
    update_job_report,
    update_job_status,
)
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    JobProgressResponse,
    JobStatusResponse,
    QueryMatchResponse,
)
from app.utils.validators import validate_shopify_url

# Route implementations (to be added per day plan):
#   POST /analyze                      — Day 2, schemas: AnalyzeRequest, AnalyzeResponse
#   GET  /jobs/{id}                    — Day 2, schemas: JobStatusResponse
#   GET  /jobs/{id}/query-match        — Day 3, schemas: QueryMatchResponse (query param: query: str)
#   GET  /jobs/{id}/fix-plan           — Day 6, schemas: FixPlanResponse
#   POST /jobs/{id}/execute            — Day 6, schemas: ExecuteRequest, ExecuteResponse
#   POST /jobs/{id}/rollback/{fix_id}  — Day 6, schemas: RollbackResponse
#   GET  /jobs/{id}/before-after       — Day 7, schemas: BeforeAfterResponse
# All request/response shapes live in app/schemas.py


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await get_pool()
    except Exception as exc:
        print(f"WARNING: DB pool not initialised at startup — {exc}")
    yield
    await close_pool()


app = FastAPI(
    title="ShopMirror API",
    description="AI representation optimizer for Shopify merchants",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /analyze
# ---------------------------------------------------------------------------

@app.post("/analyze", status_code=202)
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks) -> AnalyzeResponse:
    if not validate_shopify_url(request.store_url):
        raise HTTPException(status_code=400, detail="Invalid Shopify store URL")

    job_id = await create_job(
        request.store_url,
        has_token=bool(request.admin_token),
        store_domain=None,
    )
    background_tasks.add_task(run_analysis_pipeline, job_id, request)
    return AnalyzeResponse(job_id=job_id)


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> JobStatusResponse:
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        status=row["status"],
        progress=JobProgressResponse(
            step=row["progress_step"] or "",
            pct=row["progress_pct"] or 0,
        ),
        report=row["report_json"] if row["status"] == "complete" else None,
        error=row["error_message"],
    )


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/query-match
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/query-match")
async def query_match(job_id: str, query: str) -> QueryMatchResponse:
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    report_json = row["report_json"]
    if report_json is None:
        raise HTTPException(status_code=400, detail="Job not yet complete")

    # Stub: full query-match logic deferred to Day 5 integration when
    # live merchant_data is available in-memory.
    return QueryMatchResponse(
        query=query,
        matched_product_ids=[],
        total_products=report_json.get("total_products", 0),
        match_count=0,
        failing_attributes={},
    )


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

async def run_analysis_pipeline(job_id: str, request: AnalyzeRequest) -> None:
    """Background task: runs ingestion → heuristics → report assembly."""
    try:
        # Step 1: ingesting
        await update_job_status(job_id, "ingesting", "Fetching store data", 10)

        from app.services.ingestion import fetch_admin_data, fetch_public_data

        merchant_data = await fetch_public_data(request.store_url)
        if request.admin_token:
            merchant_data = await fetch_admin_data(request.store_url, request.admin_token)

        # Step 2: auditing
        await update_job_status(job_id, "auditing", "Running 19 checks", 40)
        from app.services.heuristics import run_all_checks
        from app.services.llm_analysis import analyze_products

        llm_results = await analyze_products(merchant_data.products)
        findings = run_all_checks(merchant_data, llm_results=llm_results)

        # Step 3: simulating (perception diff + query match)
        await update_job_status(job_id, "simulating", "Simulating AI perception", 65)
        from app.services.perception_diff import (
            compute_store_perception_diff,
            compute_product_perceptions,
        )
        from app.services.query_matcher import run_default_queries

        perception_diff = await compute_store_perception_diff(
            merchant_data, findings, merchant_intent=request.merchant_intent
        )
        product_perceptions = await compute_product_perceptions(
            merchant_data.products, findings, merchant_intent=request.merchant_intent
        )

        await update_job_status(job_id, "simulating", "Matching AI queries", 80)
        query_match_results = await run_default_queries(
            merchant_data, paid_tier=bool(request.admin_token)
        )

        # Step 4: assemble report
        from app.services.report_builder import assemble_report

        report = await assemble_report(
            merchant_data=merchant_data,
            findings=findings,
            perception_diff=perception_diff,
            product_perceptions=product_perceptions,
            mcp_results=None,
            query_match_results=query_match_results,
            competitor_results=[],
            copy_paste_items=[],
        )

        # Step 5: save
        status = "awaiting_approval" if request.admin_token else "complete"
        await update_job_report(job_id, dataclasses.asdict(report), status=status)

    except Exception as exc:
        await update_job_error(job_id, str(exc))
