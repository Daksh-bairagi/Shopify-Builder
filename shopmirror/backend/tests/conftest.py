"""
Root conftest.py — shared fixtures available to every test in the suite.
"""

from __future__ import annotations

import sys
import os
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure the backend root is on sys.path so `app.*` imports resolve when
# pytest is run from the backend/ directory or from inside tests/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Re-export fixture helpers so test files can import from conftest directly
# ---------------------------------------------------------------------------

from tests.fixtures.merchant_data import (  # noqa: E402
    make_variant,
    make_image,
    make_option,
    make_product,
    make_policies,
    make_merchant,
    clean_store_admin,
    broken_store_admin,
)


# ---------------------------------------------------------------------------
# Fake DB row builders used by black-box API tests
# ---------------------------------------------------------------------------

def _fake_job_row(
    job_id: str | None = None,
    status: str = "complete",
    has_token: bool = True,
    store_url: str = "https://test-store.myshopify.com",
    store_domain: str = "test-store.myshopify.com",
    report_json: dict | None = None,
    fix_plan_json: dict | None = None,
    error_message: str | None = None,
) -> dict:
    return {
        "job_id": job_id or str(uuid.uuid4()),
        "status": status,
        "has_token": has_token,
        "store_url": store_url,
        "store_domain": store_domain,
        "progress_step": "Analysis complete",
        "progress_pct": 100,
        "report_json": report_json or {},
        "fix_plan_json": fix_plan_json or {"fixes": []},
        "error_message": error_message,
    }


# ---------------------------------------------------------------------------
# FastAPI TestClient with mocked DB and mocked pipeline
# ---------------------------------------------------------------------------

@pytest.fixture()
def api_client():
    """
    TestClient with all external I/O mocked out:
    - DB pool initialisation silenced
    - create_job / get_job mocked with a canned response
    - run_analysis_pipeline replaced with a no-op so tests are deterministic
    """
    with (
        patch("app.main.get_pool", new=AsyncMock()),
        patch("app.main.close_pool", new=AsyncMock()),
        patch("app.main.create_job", new=AsyncMock(return_value=str(uuid.uuid4()))),
        patch("app.main.get_job", new=AsyncMock(return_value=_fake_job_row())),
        patch("app.main.update_job_status", new=AsyncMock()),
        patch("app.main.update_job_report", new=AsyncMock()),
        patch("app.main.update_job_error", new=AsyncMock()),
        patch("app.main.patch_report_section", new=AsyncMock(return_value=True)),
        patch("app.main.run_analysis_pipeline", new=AsyncMock()),
        patch("app.main.run_fix_agent_task", new=AsyncMock()),
        patch("app.main.validate_shopify_url", new=AsyncMock()),
    ):
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client


@pytest.fixture()
def api_client_no_job():
    """TestClient whose get_job always returns None (job not found)."""
    with (
        patch("app.main.get_pool", new=AsyncMock()),
        patch("app.main.close_pool", new=AsyncMock()),
        patch("app.main.create_job", new=AsyncMock(return_value=str(uuid.uuid4()))),
        patch("app.main.get_job", new=AsyncMock(return_value=None)),
        patch("app.main.run_analysis_pipeline", new=AsyncMock()),
        patch("app.main.validate_shopify_url", new=AsyncMock()),
    ):
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client


@pytest.fixture()
def fake_job_row():
    return _fake_job_row
