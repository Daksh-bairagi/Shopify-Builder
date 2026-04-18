# API request and response Pydantic schemas.
# These are the shapes FastAPI validates on the wire — separate from domain
# dataclasses in app/models/ which are internal-only.
#
# Sections to implement (in order of API routes in TechSpec Section 4):
#
# --- Request bodies ---
# class AnalyzeRequest(BaseModel)
#     store_url: str
#     admin_token: str | None
#     merchant_intent: str | None
#     competitor_urls: list[str]   # max 2
#
# --- Response bodies ---
# class AnalyzeResponse(BaseModel)       POST /analyze -> 202
#     job_id: str
#
# class JobProgressResponse(BaseModel)   GET /jobs/{id} progress payload
#     step: str
#     pct: int
#
# class JobStatusResponse(BaseModel)     GET /jobs/{id}
#     status: str
#     progress: JobProgressResponse
#     report: dict | None
#     error: str | None
#
# class FixPlanResponse(BaseModel)       GET /jobs/{id}/fix-plan
#     fixes: list[dict]
#
# class ExecuteRequest(BaseModel)        POST /jobs/{id}/execute
#     approved_fix_ids: list[str]
#
# class ExecuteResponse(BaseModel)
#     execution_job_id: str
#
# class RollbackResponse(BaseModel)      POST /jobs/{id}/rollback/{fix_id}
#     status: str
#     field: str
#     restored_value: str
#
# class BeforeAfterResponse(BaseModel)   GET /jobs/{id}/before-after
#     original_pillars: dict
#     current_pillars: dict
#     checks_improved: list[str]
#     checks_unchanged: list[str]
#     mcp_before: list[dict] | None
#     mcp_after: list[dict] | None
#     manual_action_items: list[dict]

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze."""

    store_url: str
    admin_token: str | None = None
    merchant_intent: str | None = None
    competitor_urls: list[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    """Response body for POST /analyze (202 Accepted)."""

    job_id: str


class JobProgressResponse(BaseModel):
    """Nested progress payload within JobStatusResponse."""

    step: str
    pct: int


class JobStatusResponse(BaseModel):
    """Response body for GET /jobs/{id}."""

    status: str
    progress: JobProgressResponse
    report: dict | None = None
    error: str | None = None


class FixPlanResponse(BaseModel):
    """Response body for GET /jobs/{id}/fix-plan."""

    fixes: list[dict] = Field(default_factory=list)


class ExecuteRequest(BaseModel):
    """Request body for POST /jobs/{id}/execute."""

    approved_fix_ids: list[str] = Field(default_factory=list)
    admin_token: str          # Required — not stored in DB, must be re-supplied by client
    merchant_intent: str | None = None


class ExecuteResponse(BaseModel):
    """Response body for POST /jobs/{id}/execute."""

    execution_job_id: str


class RollbackRequest(BaseModel):
    """Request body for POST /jobs/{id}/rollback/{fix_id}."""

    admin_token: str


class RollbackResponse(BaseModel):
    """Response body for POST /jobs/{id}/rollback/{fix_id}."""

    status: str
    field: str
    restored_value: str


class BeforeAfterResponse(BaseModel):
    """Response body for GET /jobs/{id}/before-after."""

    original_pillars: dict
    current_pillars: dict
    checks_improved: list[str] = Field(default_factory=list)
    checks_unchanged: list[str] = Field(default_factory=list)
    mcp_before: list[dict] | None = None
    mcp_after: list[dict] | None = None
    manual_action_items: list[dict] = Field(default_factory=list)


class QueryMatchResponse(BaseModel):
    """Response body for GET /jobs/{id}/query-match."""

    query: str
    matched_product_ids: list[str] = Field(default_factory=list)
    total_products: int
    match_count: int
    failing_attributes: dict[str, int] = Field(default_factory=dict)
