"""
agent/state.py — LangGraph state TypedDict for the fix agent.
"""

from __future__ import annotations

from typing import TypedDict

from app.models.merchant import MerchantData
from app.models.findings import Finding
from app.models.fixes import FixItem, FixResult


class StoreOptimizationState(TypedDict):
    job_id: str
    store_data: MerchantData
    admin_token: str
    merchant_intent: str | None       # merchant's stated brand voice, from /analyze request
    audit_findings: list[Finding]
    fix_plan: list[FixItem]           # all planned fixes
    approved_fix_ids: list[str]       # merchant-approved subset
    executed_fixes: list[FixResult]
    failed_fixes: list[FixResult]
    current_fix_id: str | None        # fix being processed right now
    retry_count: int                  # resets per fix, max 2
    iteration: int                    # total iterations, max 50
    verification_results: dict        # check_id -> bool after re-run
    manual_action_items: list[Finding]
    final_report: dict | None
