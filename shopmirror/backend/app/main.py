import asyncio
import dataclasses
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db.connection import close_pool, get_pool
from app.db.queries import (
    create_job,
    get_job,
    update_job_error,
    update_job_fix_plan,
    update_job_report,
    update_job_status,
)
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    BeforeAfterResponse,
    ExecuteRequest,
    ExecuteResponse,
    FixPlanResponse,
    JobProgressResponse,
    JobStatusResponse,
    QueryMatchResponse,
    RollbackRequest,
    RollbackResponse,
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /analyze
# ---------------------------------------------------------------------------

@app.post("/analyze", status_code=202)
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks) -> AnalyzeResponse:
    try:
        await validate_shopify_url(request.store_url)
    except (ValueError, Exception):
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

    # Try to find the closest pre-computed query match result from the stored report.
    # Full re-matching requires live product data (not stored in DB), so we fall back
    # to keyword matching against product titles from all_products in the stored report.
    precomputed: list[dict] = report_json.get("query_match_results") or []
    all_products: list[dict] = report_json.get("all_products") or report_json.get("worst_5_products") or []
    total_products: int = report_json.get("total_products", 0)

    # Check if any pre-computed result contains the query as a substring (case-insensitive)
    query_lower = query.lower()
    for result in precomputed:
        if query_lower in result.get("query", "").lower():
            return QueryMatchResponse(
                query=query,
                matched_product_ids=result.get("matched_product_ids", []),
                total_products=result.get("total_products", total_products),
                match_count=result.get("match_count", 0),
                failing_attributes=result.get("failing_attributes", {}),
            )

    # Fallback: lightweight title-based match from stored product summaries
    query_words = [w for w in query_lower.split() if len(w) > 2]
    matched_ids: list[str] = []
    failing_attrs: dict[str, int] = {}
    for p in all_products:
        title_lower = p.get("title", "").lower()
        failing_checks = set(p.get("failing_check_ids", []))
        if any(w in title_lower for w in query_words):
            # Only "match" if product isn't failing C1/C2 (product type + title)
            if "C1" not in failing_checks and "C2" not in failing_checks:
                matched_ids.append(p["product_id"])
            else:
                for cid in failing_checks:
                    failing_attrs[cid] = failing_attrs.get(cid, 0) + 1

    return QueryMatchResponse(
        query=query,
        matched_product_ids=matched_ids,
        total_products=total_products,
        match_count=len(matched_ids),
        failing_attributes=failing_attrs,
    )


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/fix-plan
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/fix-plan")
async def get_fix_plan(job_id: str) -> FixPlanResponse:
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not row["has_token"]:
        raise HTTPException(status_code=403, detail="Fix plan requires admin token")
    fix_plan = row.get("fix_plan_json") or {}
    return FixPlanResponse(fixes=fix_plan.get("fixes", []))


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/execute
# ---------------------------------------------------------------------------

@app.post("/jobs/{job_id}/execute", status_code=202)
async def execute_fixes(
    job_id: str,
    request: ExecuteRequest,
    background_tasks: BackgroundTasks,
) -> ExecuteResponse:
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if row["status"] not in ("awaiting_approval", "complete"):
        raise HTTPException(status_code=400, detail="Job not in a state that allows fix execution")
    if not row["has_token"]:
        raise HTTPException(status_code=403, detail="Fix execution requires admin token")

    background_tasks.add_task(run_fix_agent_task, job_id, request.approved_fix_ids, request.admin_token, request.merchant_intent)
    return ExecuteResponse(execution_job_id=job_id)


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/rollback/{fix_id}
# ---------------------------------------------------------------------------

@app.post("/jobs/{job_id}/rollback/{fix_id}")
async def rollback_fix(job_id: str, fix_id: str, request: RollbackRequest) -> RollbackResponse:
    """Rollback a fix. Admin token is required in the request body."""
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    from app.db.queries import get_fix_backup
    backup = await get_fix_backup(fix_id)
    if backup is None:
        raise HTTPException(status_code=404, detail="Fix backup not found")

    store_domain = row.get("store_domain") or row["store_url"].replace("https://", "").split("/")[0]

    from app.services.shopify_writer import rollback_fix as do_rollback
    try:
        field, restored_value = await do_rollback(fix_id, store_domain, request.admin_token)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return RollbackResponse(status="rolled_back", field=field, restored_value=restored_value)


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/before-after
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/before-after")
async def get_before_after(job_id: str) -> BeforeAfterResponse:
    """Return before/after comparison computed by the fix agent."""
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    report_json = row.get("report_json") or {}
    agent_run = report_json.get("agent_run") or {}
    before_after = agent_run.get("before_after")

    if before_after is None:
        raise HTTPException(status_code=404, detail="No before-after data — agent has not run yet")

    return BeforeAfterResponse(
        original_pillars=before_after.get("original_pillars") or {},
        current_pillars=before_after.get("current_pillars") or {},
        checks_improved=before_after.get("checks_improved") or [],
        checks_unchanged=before_after.get("checks_unchanged") or [],
        mcp_before=before_after.get("mcp_before"),
        mcp_after=before_after.get("mcp_after"),
        manual_action_items=before_after.get("manual_action_items") or [],
    )


# ---------------------------------------------------------------------------
# Background task: run LangGraph fix agent
# ---------------------------------------------------------------------------

async def run_fix_agent_task(job_id: str, approved_fix_ids: list[str], admin_token: str, merchant_intent: str | None = None) -> None:
    """Background task: re-ingests store data and runs the LangGraph fix agent."""
    try:
        row = await get_job(job_id)
        if row is None:
            return

        fix_plan_data = row.get("fix_plan_json") or {}
        fix_items_raw = fix_plan_data.get("fixes", [])

        from app.models.fixes import FixItem
        from app.agent.graph import run_fix_agent
        from app.agent.state import StoreOptimizationState
        from app.services.ingestion import fetch_admin_data

        fix_items = [FixItem(**f) for f in fix_items_raw]

        store_url = row["store_url"]

        # Re-ingest with the admin token so the agent has live product data
        await update_job_status(job_id, "executing", "Re-fetching store data for agent", 5)
        try:
            merchant_data = await fetch_admin_data(store_url, admin_token)
        except Exception as exc:
            logger.warning("run_fix_agent_task: re-ingestion failed for %s: %s", job_id, exc)
            # Fall back to stub so the agent can still run reporting
            from app.models.merchant import MerchantData, Policies
            store_domain = row.get("store_domain") or store_url.replace("https://", "").split("/")[0]
            merchant_data = MerchantData(
                store_domain=store_domain,
                store_name=store_domain,
                products=[],
                collections=[],
                policies=Policies(),
                robots_txt="",
                sitemap_present=False,
                sitemap_has_products=False,
                llms_txt=None,
                schema_by_url={},
                price_in_html={},
                ingestion_mode="admin_token",
                metafields_by_product={},
                seo_by_product={},
                inventory_by_variant={},
            )

        initial_state: StoreOptimizationState = {
            "job_id": job_id,
            "store_data": merchant_data,
            "admin_token": admin_token,
            "merchant_intent": merchant_intent,
            "audit_findings": [],
            "fix_plan": fix_items,
            "approved_fix_ids": approved_fix_ids,
            "executed_fixes": [],
            "failed_fixes": [],
            "current_fix_id": None,
            "retry_count": 0,
            "iteration": 0,
            "verification_results": {},
            "manual_action_items": [],
            "final_report": None,
        }

        await run_fix_agent(initial_state)

    except Exception as exc:
        logger.error("run_fix_agent_task failed for job %s: %s", job_id, exc)


# ---------------------------------------------------------------------------
# Background task: analysis pipeline
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

        await update_job_status(job_id, "simulating", "Matching AI queries", 75)
        query_match_results = await run_default_queries(
            merchant_data, paid_tier=bool(request.admin_token)
        )

        await update_job_status(job_id, "simulating", "Simulating MCP responses", 80)
        from app.services.mcp_simulation import run_mcp_simulation
        from app.services.competitor import run_competitor_analysis

        mcp_results, competitor_results = await asyncio.gather(
            run_mcp_simulation(merchant_data, findings),
            run_competitor_analysis(
                merchant_data,
                findings,
                competitor_urls=request.competitor_urls if request.competitor_urls else None,
            ),
        )

        # Step 4: assemble report
        await update_job_status(job_id, "simulating", "Assembling report", 90)
        from app.services.report_builder import assemble_report

        report = await assemble_report(
            merchant_data=merchant_data,
            findings=findings,
            perception_diff=perception_diff,
            product_perceptions=product_perceptions,
            mcp_results=mcp_results,
            query_match_results=query_match_results,
            competitor_results=competitor_results,
            copy_paste_items=[],
        )

        # Step 5: generate fix plan (paid tier only) and save
        if request.admin_token:
            await update_job_status(job_id, "simulating", "Planning fixes", 95)
            from app.agent.nodes import generate_fix_plan
            fix_items = generate_fix_plan(findings)
            fix_plan_dict = {"fixes": [dataclasses.asdict(f) for f in fix_items]}
            await update_job_fix_plan(job_id, fix_plan_dict)

        status = "awaiting_approval" if request.admin_token else "complete"
        await update_job_report(job_id, dataclasses.asdict(report), status=status)

    except Exception as exc:
        await update_job_error(job_id, str(exc))
