from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Finding:
    id: str                       # e.g. 'finding_D1_001'
    pillar: str                   # 'Discoverability' | 'Completeness' | 'Consistency' | 'Trust_Policies' | 'Transaction'
    check_id: str                 # 'D1' | 'C2' | 'Con1' | etc.
    check_name: str               # human-readable check name
    severity: str                 # 'CRITICAL' | 'HIGH' | 'MEDIUM'
    weight: int                   # 10 | 6 | 2
    title: str                    # short description
    detail: str                   # why it matters for AI agents
    spec_citation: str            # source document being violated
    affected_products: list[str]
    affected_count: int
    impact_statement: str         # e.g. 'Affects 100% of category queries'
    fix_type: str                 # 'auto' | 'copy_paste' | 'manual' | 'developer'
    fix_instruction: str          # exact steps to fix
    fix_content: Optional[str]    # generated content when fix_type is 'copy_paste'


@dataclass
class PillarScore:
    score: float
    checks_passed: int
    checks_total: int


@dataclass
class ProductSummary:
    product_id: str
    title: str
    gap_score: float
    failing_check_ids: list[str]


@dataclass
class PerceptionDiff:
    intended_positioning: str
    ai_perception: str
    gap_reasons: list[str]


@dataclass
class ProductPerception:
    product_id: str
    intended: str
    ai_extracted: str
    cannot_determine: list[str]
    root_finding_ids: list[str]


@dataclass
class MCPResult:
    question: str
    response: str
    classification: str           # 'ANSWERED' | 'UNANSWERED' | 'WRONG'
    ground_truth_mismatch: Optional[str]
    related_finding_ids: list[str]


@dataclass
class CompetitorAudit:
    url: str
    store_domain: str
    check_results: dict[str, bool]   # check_id -> passed


@dataclass
class CompetitorResult:
    competitor: CompetitorAudit
    gaps: list[str]                  # check_ids merchant fails but competitor passes


@dataclass
class CopyPasteItem:
    type: str                        # 'schema_snippet' | 'policy_draft'
    title: str
    content: str
    product_id: Optional[str]


@dataclass
class AuditReport:
    store_name: str
    store_domain: str
    ingestion_mode: str              # 'url_only' | 'admin_token'
    total_products: int
    pillars: dict[str, PillarScore]  # pillar name -> PillarScore
    findings: list[Finding]
    worst_5_products: list[ProductSummary]
    perception_diff: Optional[PerceptionDiff]
    competitor_comparison: list[CompetitorResult]
    mcp_simulation: Optional[list[MCPResult]]
    copy_paste_package: list[CopyPasteItem]
