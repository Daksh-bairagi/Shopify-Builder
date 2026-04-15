from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FixItem:
    fix_id: str
    type: str                       # 'classify_product_type' | 'improve_title' | 'fill_metafield' | 'generate_alt_text'
    product_id: str
    product_title: str
    field: str                      # which field is being changed
    current_value: Optional[str]
    proposed_value: str
    reason: str
    risk: str                       # 'LOW'
    reversible: bool


@dataclass
class FixPlan:
    fixes: list[FixItem]


@dataclass
class FixResult:
    fix_id: str
    success: bool
    error: Optional[str]
    shopify_gid: Optional[str]      # GID of the written Shopify resource
    applied_at: Optional[datetime]
