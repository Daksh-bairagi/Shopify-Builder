from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AnalysisJob:
    id: str                         # UUID
    store_url: str
    store_domain: Optional[str]
    has_token: bool
    status: str                     # 'queued' | 'ingesting' | 'auditing' | 'simulating' | 'complete' | 'failed' | 'awaiting_approval'
    progress_step: Optional[str]
    progress_pct: int
    report_json: Optional[dict]
    fix_plan_json: Optional[dict]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


@dataclass
class JobProgress:
    step: str
    pct: int


@dataclass
class JobStatus:
    status: str                     # 'ingesting' | 'auditing' | 'simulating' | 'awaiting_approval' | 'complete' | 'failed'
    progress: JobProgress
    report: Optional[dict]
    error: Optional[str]
