from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FixItem:
    fix_id: str
    type: str   # 'classify_product_type' | 'improve_title' | 'fill_metafield' |
                # 'generate_alt_text' | 'map_taxonomy' | 'inject_schema_script' |
                # 'create_metafield_definitions' | 'generate_schema_snippet' | 'suggest_policy_fix'
    product_id: str
    product_title: str
    field: str                      # which field is being changed (check_id, e.g. 'C1')
    current_value: Optional[str]
    proposed_value: str
    reason: str
    risk: str                       # 'LOW'
    reversible: bool
    severity: str = "MEDIUM"        # 'CRITICAL' | 'HIGH' | 'MEDIUM' — from the source finding
    fix_type: str = "auto"          # 'auto' | 'copy_paste' | 'manual' | 'developer'
    check_id: str = ""              # mirrors field for frontend compatibility


@dataclass
class FixPlan:
    fixes: list[FixItem]


@dataclass
class FixResult:
    fix_id: str
    success: bool
    error: Optional[str]
    shopify_gid: Optional[str]      # GID of the written Shopify resource
    script_tag_id: Optional[str]    # Shopify script tag ID — stored for inject_schema_script rollback
    applied_at: Optional[datetime]
