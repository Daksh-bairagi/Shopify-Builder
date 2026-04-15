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
