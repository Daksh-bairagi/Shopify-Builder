"""
FastAPI entrypoint for ShopMirror.

This module stays intentionally thin: it validates requests, creates jobs,
starts background workflows, and exposes the polling and remediation endpoints
used by the frontend. Most domain logic lives in `app.services.*` and
`app.agent.*`, which makes this file a good top-down entrypoint for judges.
"""

import asyncio
import dataclasses
import logging
from contextlib import asynccontextmanager

import httpx

logger = logging.getLogger(__name__)

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db.connection import close_pool, get_pool
from app.db.queries import (
    create_job,
    get_job,
    patch_report_section,
    update_job_error,
    update_job_fix_plan,
    update_job_report,
    update_job_store_domain,
    update_job_status,
)
from app.schemas import (
    AIVisibilityRequest,
    AnalyzeRequest,
    AnalyzeResponse,
    BeforeAfterResponse,
    CompetitorRequest,
    CopyRewriteRequest,
    ExecuteRequest,
    ExecuteResponse,
    FAQRequest,
    FixPlanResponse,
    JobProgressResponse,
    JobStatusResponse,
    RollbackRequest,
    RollbackResponse,
)
from app.utils.validators import validate_shopify_url
from fastapi import Response
from fastapi.responses import PlainTextResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up shared resources once and close them cleanly on shutdown."""
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
    expose_headers=[
        "Content-Disposition",
        "X-Feed-Total-Items",
        "X-Feed-Total-Lines",
        "X-Feed-Currency",
        "X-Skipped-No-Identifier",
        "X-Ingestion-Mode",
    ],
)


def _resolve_admin_token(query_token: str | None, header_token: str | None) -> str | None:
    """Prefer the header-supplied token (private) over the query string (legacy/fallback)."""
    return header_token or query_token


def _friendly_background_error(exc: Exception, phase: str) -> str:
    """Convert low-level background-task exceptions into operator-friendly UI text."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        url = str(exc.request.url)
        if status == 401 and "/admin/api/" in url:
            return (
                "Shopify Admin API rejected the admin token for this store (401 Unauthorized). "
                "This usually means the token is wrong, revoked, belongs to a different Shopify store, "
                "or the custom app is missing required Admin API scopes."
            )
        if status == 403 and "/admin/api/" in url:
            return (
                "Shopify Admin API denied access for this custom app (403 Forbidden). "
                "The token is valid but the app likely does not have the required Admin API scopes "
                "for this action."
            )
        return f"{phase} failed with HTTP {status}: {exc}"
    return str(exc)


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /analyze
# ---------------------------------------------------------------------------

@app.post("/analyze", status_code=202)
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks) -> AnalyzeResponse:
    """Create an analysis job and hand the full pipeline to a background task."""
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
    """Return the latest persisted job state for frontend polling."""
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        status=row["status"],
        progress=JobProgressResponse(
            step=row["progress_step"] or "",
            pct=row["progress_pct"] or 0,
        ),
        report=row["report_json"] if row["status"] in {"complete", "awaiting_approval", "failed"} else None,
        error=row["error_message"],
    )


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/fix-plan
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/fix-plan")
async def get_fix_plan(job_id: str) -> FixPlanResponse:
    """Expose the generated fix plan after an admin-token audit."""
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
    """Start the LangGraph remediation flow for the selected fix ids."""
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if row["status"] != "awaiting_approval":
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

    from app.db.queries import get_fix_backup, list_fix_backups_for_prefix
    backup = await get_fix_backup(fix_id)
    backups = [backup] if backup is not None else await list_fix_backups_for_prefix(f"{fix_id}_")
    backups = [row for row in backups if row.get("job_id") == job_id]
    if not backups:
        raise HTTPException(status_code=404, detail="Fix backup not found for this job")

    store_domain = row.get("store_domain") or row["store_url"].replace("https://", "").split("/")[0]

    from app.services.shopify_writer import rollback_fix as do_rollback
    try:
        field, restored_value = await do_rollback(
            fix_id,
            store_domain,
            request.admin_token,
            expected_job_id=job_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Persist rollback into the stored agent_run so a page refresh keeps the
    # "Reversed" status visible instead of reverting to "Applied".
    try:
        report_json = row.get("report_json") or {}
        agent_run = report_json.get("agent_run") or {}
        rolled_ids = set(agent_run.get("rolled_back_fix_ids") or [])
        # Mark every backup matching this fix_id (or prefix) as rolled back in the report.
        for b in backups:
            rolled_ids.add(b["fix_id"])
        agent_run["rolled_back_fix_ids"] = sorted(rolled_ids)
        # Also mark inside executed_fixes so the dashboard renders a Reversed badge.
        for ef in agent_run.get("executed_fixes") or []:
            if ef.get("fix_id") in rolled_ids:
                ef["rolled_back"] = True
        await patch_report_section(job_id, "agent_run", agent_run)
    except Exception as exc:
        logger.warning("rollback persist failed for %s/%s: %s", job_id, fix_id, exc)

    return RollbackResponse(status="rolled_back", field=field, restored_value=restored_value)


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/before-after
# ---------------------------------------------------------------------------

# ===========================================================================
# AI Visibility extensions — April 2026
# ===========================================================================

async def _load_merchant_data_for_job(job_id: str, admin_token: str | None = None):
    """Re-ingest merchant data for endpoints that need full Product objects.
    Reads store_url from the job row; admin_token optional for richer data.
    """
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    store_url = row["store_url"]
    from app.services.ingestion import fetch_admin_data, fetch_public_data
    if admin_token:
        return await fetch_admin_data(store_url, admin_token)
    return await fetch_public_data(store_url)


def _stored_audit_section(report_json: dict | None, key: str) -> dict:
    if not report_json:
        raise HTTPException(status_code=400, detail="Job not yet complete")
    section = report_json.get(key)
    if section is None:
        raise HTTPException(status_code=404, detail=f"{key} not present in this report")
    return section


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/bot-access
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/bot-access")
async def get_bot_access(job_id: str) -> dict:
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _stored_audit_section(row.get("report_json"), "bot_access")


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/identifiers
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/identifiers")
async def get_identifiers(job_id: str) -> dict:
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _stored_audit_section(row.get("report_json"), "identifier_audit")


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/golden-record
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/golden-record")
async def get_golden_record(job_id: str) -> dict:
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _stored_audit_section(row.get("report_json"), "golden_record")


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/trust-signals
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/trust-signals")
async def get_trust_signals(job_id: str) -> dict:
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _stored_audit_section(row.get("report_json"), "trust_signals")


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/llms-txt and /llms-full-txt — text/plain, ready to host
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/llms-txt", response_class=PlainTextResponse)
async def get_llms_txt(
    job_id: str,
    admin_token: str | None = None,
    x_admin_token: str | None = Header(default=None),
) -> PlainTextResponse:
    token = _resolve_admin_token(admin_token, x_admin_token)
    merchant_data = await _load_merchant_data_for_job(job_id, admin_token=token)
    from app.services.llms_txt import generate_llms_txt
    return PlainTextResponse(generate_llms_txt(merchant_data), media_type="text/plain; charset=utf-8")


@app.get("/jobs/{job_id}/llms-full-txt", response_class=PlainTextResponse)
async def get_llms_full_txt(
    job_id: str,
    admin_token: str | None = None,
    x_admin_token: str | None = Header(default=None),
) -> PlainTextResponse:
    token = _resolve_admin_token(admin_token, x_admin_token)
    merchant_data = await _load_merchant_data_for_job(job_id, admin_token=token)
    from app.services.llms_txt import generate_llms_full_txt
    return PlainTextResponse(generate_llms_full_txt(merchant_data), media_type="text/plain; charset=utf-8")


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/schema-package — JSON-LD blocks per product
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/schema-package")
async def get_schema_package(
    job_id: str,
    admin_token: str | None = None,
    x_admin_token: str | None = Header(default=None),
) -> dict:
    token = _resolve_admin_token(admin_token, x_admin_token)
    merchant_data = await _load_merchant_data_for_job(job_id, admin_token=token)
    from app.services.schema_enricher import generate_schema_package
    return generate_schema_package(merchant_data)


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/feeds/chatgpt — JSONL
# ---------------------------------------------------------------------------
# Pass ?admin_token=… to ingest with the same auth used at /analyze; otherwise
# the feed only sees public storefront data and can show fewer identifiers
# than the stored audit.

@app.get("/jobs/{job_id}/feeds/chatgpt")
async def get_chatgpt_feed(
    job_id: str,
    admin_token: str | None = None,
    x_admin_token: str | None = Header(default=None),
) -> Response:
    token = _resolve_admin_token(admin_token, x_admin_token)
    merchant_data = await _load_merchant_data_for_job(job_id, admin_token=token)
    from app.services.feed_generator import build_chatgpt_feed
    feed = build_chatgpt_feed(merchant_data)
    return Response(
        content=feed["jsonl"],
        media_type="application/x-ndjson",
        headers={
            "X-Feed-Total-Lines": str(feed["summary"]["total_lines"]),
            "X-Feed-Currency": feed["summary"]["currency"],
            "X-Ingestion-Mode": merchant_data.ingestion_mode,
            "Content-Disposition": f'attachment; filename="chatgpt-feed-{job_id[:8]}.jsonl"',
        },
    )


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/feeds/perplexity — XML
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/feeds/perplexity")
async def get_perplexity_feed(
    job_id: str,
    admin_token: str | None = None,
    x_admin_token: str | None = Header(default=None),
) -> Response:
    token = _resolve_admin_token(admin_token, x_admin_token)
    merchant_data = await _load_merchant_data_for_job(job_id, admin_token=token)
    from app.services.feed_generator import build_perplexity_feed
    feed = build_perplexity_feed(merchant_data)
    return Response(
        content=feed["xml"],
        media_type="application/xml",
        headers={
            "X-Feed-Total-Items": str(feed["summary"]["total_items"]),
            "X-Skipped-No-Identifier": str(feed["summary"]["skipped_without_identifier"]),
            "X-Ingestion-Mode": merchant_data.ingestion_mode,
            "Content-Disposition": f'attachment; filename="perplexity-feed-{job_id[:8]}.xml"',
        },
    )


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/feeds/google — XML (Merchant Center / AI Mode)
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/feeds/google")
async def get_google_feed(
    job_id: str,
    admin_token: str | None = None,
    x_admin_token: str | None = Header(default=None),
) -> Response:
    token = _resolve_admin_token(admin_token, x_admin_token)
    merchant_data = await _load_merchant_data_for_job(job_id, admin_token=token)
    from app.services.feed_generator import build_google_feed
    feed = build_google_feed(merchant_data)
    return Response(
        content=feed["xml"],
        media_type="application/xml",
        headers={
            "X-Feed-Total-Items": str(feed["summary"]["total_items"]),
            "X-Ingestion-Mode": merchant_data.ingestion_mode,
            "Content-Disposition": f'attachment; filename="google-feed-{job_id[:8]}.xml"',
        },
    )


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/robots-suggestion — text/plain robots.txt patch
# ---------------------------------------------------------------------------

@app.get("/jobs/{job_id}/robots-suggestion", response_class=PlainTextResponse)
async def get_robots_suggestion(job_id: str) -> PlainTextResponse:
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    audit = _stored_audit_section(row.get("report_json"), "bot_access")
    from app.services.bot_audit import suggested_robots_txt_additions
    return PlainTextResponse(
        suggested_robots_txt_additions(audit),
        media_type="text/plain; charset=utf-8",
    )


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/ai-visibility — FLAGSHIP live multi-LLM probe
# ---------------------------------------------------------------------------

@app.post("/jobs/{job_id}/ai-visibility")
async def post_ai_visibility(job_id: str, request: AIVisibilityRequest) -> dict:
    merchant_data = await _load_merchant_data_for_job(job_id, admin_token=request.admin_token)
    from app.services.ai_visibility import probe_ai_visibility
    result = await probe_ai_visibility(
        merchant_data=merchant_data,
        prompts=request.prompts,
        providers=request.providers,
    )
    # Persist into the report so the dashboard can read ai_visibility from
    # the same /jobs/{id} response that surfaces the rest of the audit.
    try:
        await patch_report_section(job_id, "ai_visibility", result)
    except Exception as exc:
        logger.warning("ai-visibility patch failed for %s: %s", job_id, exc)
    return result


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/copy-rewrite — per-channel copy rewriter
# ---------------------------------------------------------------------------

@app.post("/jobs/{job_id}/copy-rewrite")
async def post_copy_rewrite(job_id: str, request: CopyRewriteRequest) -> dict:
    merchant_data = await _load_merchant_data_for_job(job_id, admin_token=request.admin_token)
    from app.services.copy_rewriter import rewrite_top_products
    products = merchant_data.products
    if request.product_ids:
        wanted = set(request.product_ids)
        products = [p for p in products if p.id in wanted]
    rewrites = await rewrite_top_products(products, limit=request.limit, channels=request.channels)
    return {"count": len(rewrites), "rewrites": rewrites}


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/faq-schema — FAQPage JSON-LD generator
# ---------------------------------------------------------------------------

@app.post("/jobs/{job_id}/faq-schema")
async def post_faq_schema(job_id: str, request: FAQRequest) -> dict:
    merchant_data = await _load_merchant_data_for_job(job_id, admin_token=request.admin_token)
    from app.services.faq_generator import generate_faq_for_top_products
    products = merchant_data.products
    if request.product_ids:
        wanted = set(request.product_ids)
        products = [p for p in products if p.id in wanted]
    faqs = await generate_faq_for_top_products(products, limit=request.limit)
    return {"count": len(faqs), "faqs": faqs}


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/competitors — on-demand competitor analysis
# ---------------------------------------------------------------------------

@app.post("/jobs/{job_id}/competitors")
async def post_competitors(job_id: str, request: CompetitorRequest) -> dict:
    """Run competitor analysis for a completed job.

    If competitor_urls is empty, SerpAPI / DuckDuckGo auto-discovery is used.
    Results are also patched back into the stored report for future /jobs/{id} calls.
    """
    row = await get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Re-ingest public merchant data (needed for product_types + store context)
    merchant_data = await _load_merchant_data_for_job(job_id)

    # Reconstruct findings from stored report so we can compute gaps
    report_json = row.get("report_json") or {}
    findings_raw = report_json.get("findings", [])
    from app.models.findings import Finding
    findings = [Finding(**f) for f in findings_raw]

    from app.services.competitor import run_competitor_analysis_with_meta
    results, meta = await run_competitor_analysis_with_meta(
        merchant_data=merchant_data,
        merchant_findings=findings,
        competitor_urls=request.competitor_urls if request.competitor_urls else None,
    )

    # Persist so the next /jobs/{id} poll returns competitor_comparison
    try:
        await patch_report_section(
            job_id,
            "competitor_comparison",
            [dataclasses.asdict(r) for r in results],
        )
    except Exception as exc:
        logger.warning("competitor patch failed for %s: %s", job_id, exc)

    return {
        "results": [dataclasses.asdict(r) for r in results],
        "status": meta.status,
        "message": meta.message,
        "mode": meta.mode,
        "scope_label": meta.scope_label,
        "candidates_considered": meta.candidates_considered,
        "audited_competitors": meta.audited_competitors,
        "notes": meta.notes,
    }


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
        findings_raw = (row.get("report_json") or {}).get("findings", [])

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
                admin_domain=store_domain,
            )

        from app.models.findings import Finding
        initial_state: StoreOptimizationState = {
            "job_id": job_id,
            "store_data": merchant_data,
            "admin_token": admin_token,
            "merchant_intent": merchant_intent,
            "audit_findings": [Finding(**finding) for finding in findings_raw],
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

        # Safety net: if the graph returned without marking the job terminal,
        # force a failed terminal state so the frontend never polls forever.
        final_row = await get_job(job_id)
        if final_row is not None and final_row.get("status") == "executing":
            await update_job_error(
                job_id,
                "Fix execution stopped without producing a terminal result. "
                "The last run likely hit an internal agent/reporting error.",
            )

    except Exception as exc:
        logger.error("run_fix_agent_task failed for job %s: %s", job_id, exc)
        try:
            await update_job_error(job_id, f"Fix execution failed: {_friendly_background_error(exc, 'Fix execution')}")
        except Exception:
            logger.exception("run_fix_agent_task: failed to persist execution error for %s", job_id)


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
        await update_job_store_domain(
            job_id,
            getattr(merchant_data, "admin_domain", None) or merchant_data.store_domain,
        )

        # Free tier: cap scan at 10 products
        FREE_PRODUCT_LIMIT = 10
        full_product_count = len(merchant_data.products)
        scan_limited = not request.admin_token and full_product_count > FREE_PRODUCT_LIMIT
        if scan_limited:
            merchant_data.products = sorted(
                merchant_data.products,
                key=lambda product: (
                    -(len(product.variants) or 0),
                    product.handle or "",
                    product.id or "",
                ),
            )[:FREE_PRODUCT_LIMIT]

        # Step 2: auditing
        await update_job_status(job_id, "auditing", "Running 19 checks", 40)
        from app.services.heuristics import run_all_checks
        from app.services.llm_analysis import analyze_products

        llm_results = await analyze_products(merchant_data.products)
        findings = run_all_checks(merchant_data, llm_results=llm_results)

        # Step 3: simulating (perception diff + query match)
        await update_job_status(job_id, "simulating", "Simulating AI perception", 65)
        from app.services.perception_diff import compute_combined_perception

        perception_diff, product_perceptions = await compute_combined_perception(
            merchant_data, findings, merchant_intent=request.merchant_intent
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

        # Step 3.5: AI-visibility extensions (April 2026 channel readiness)
        await update_job_status(job_id, "simulating", "Auditing AI bot access + identifiers", 85)
        from app.services.bot_audit import audit_bot_access
        from app.services.identifier_audit import audit_identifiers
        from app.services.golden_record import score_store
        from app.services.trust_signals import score_trust_signals
        from app.services.feed_generator import (
            build_chatgpt_feed,
            build_perplexity_feed,
            build_google_feed,
        )
        from app.services.llms_txt import generate_llms_txt

        bot_access = audit_bot_access(merchant_data.robots_txt)
        identifier_audit = audit_identifiers(merchant_data)
        golden_record = score_store(merchant_data)
        trust_signals = score_trust_signals(merchant_data)
        feed_summaries = {
            "chatgpt":    build_chatgpt_feed(merchant_data)["summary"],
            "perplexity": build_perplexity_feed(merchant_data)["summary"],
            "google":     build_google_feed(merchant_data)["summary"],
        }
        llms_txt_preview = generate_llms_txt(merchant_data)[:1500]

        fix_items = []
        copy_paste_items = []
        if request.admin_token:
            await update_job_status(job_id, "simulating", "Planning fixes", 95)
            from app.agent.nodes import build_copy_paste_items, generate_fix_plan
            fix_items = generate_fix_plan(findings, merchant_data=merchant_data)
            copy_paste_items = build_copy_paste_items(fix_items)
            fix_plan_dict = {"fixes": [dataclasses.asdict(f) for f in fix_items]}
            await update_job_fix_plan(job_id, fix_plan_dict)

        # Step 4: assemble report
        await update_job_status(job_id, "simulating", "Assembling report", 98)
        from app.services.report_builder import assemble_report

        report = await assemble_report(
            merchant_data=merchant_data,
            findings=findings,
            perception_diff=perception_diff,
            product_perceptions=product_perceptions,
            mcp_results=mcp_results,
            query_match_results=[],
            competitor_results=competitor_results,
            copy_paste_items=copy_paste_items,
            bot_access=bot_access,
            identifier_audit=identifier_audit,
            golden_record=golden_record,
            trust_signals=trust_signals,
            feed_summaries=feed_summaries,
            llms_txt_preview=llms_txt_preview,
            scan_limited=scan_limited,
            full_product_count=full_product_count,
        )

        status = "awaiting_approval" if request.admin_token else "complete"
        await update_job_report(job_id, dataclasses.asdict(report), status=status)

    except Exception as exc:
        await update_job_error(job_id, _friendly_background_error(exc, "Analysis"))
