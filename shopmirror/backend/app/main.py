from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.connection import close_pool, get_pool

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
