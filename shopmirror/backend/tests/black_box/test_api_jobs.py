"""
Black-box tests for job-related endpoints:

  GET  /jobs/{job_id}            — status + report
  GET  /jobs/{job_id}/fix-plan   — fix plan (admin-mode guard)
  GET  /jobs/{job_id}/before-after  — existence check

Tests verify HTTP contracts: status codes, JSON shape, 404 on missing job,
403 on permission gates, and that report data is only exposed once complete.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest


# ===========================================================================
# GET /jobs/{job_id}
# ===========================================================================

class TestGetJobStatus:

    def test_existing_job_returns_200(self, api_client):
        resp = api_client.get("/jobs/any-job-id")
        assert resp.status_code == 200

    def test_missing_job_returns_404(self, api_client_no_job):
        resp = api_client_no_job.get("/jobs/nonexistent-id")
        assert resp.status_code == 404

    def test_404_body_contains_detail(self, api_client_no_job):
        resp = api_client_no_job.get("/jobs/nonexistent-id")
        assert "detail" in resp.json()

    def test_response_has_status_field(self, api_client):
        resp = api_client.get("/jobs/any-job-id")
        body = resp.json()
        assert "status" in body

    def test_response_has_progress_field(self, api_client):
        body = api_client.get("/jobs/any-job-id").json()
        assert "progress" in body
        assert "step" in body["progress"]
        assert "pct" in body["progress"]

    def test_complete_job_exposes_report(self, fake_job_row):
        report = {"store_name": "Test Store", "ai_readiness_score": 72.5}
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="complete", report_json=report)
            )),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/jobs/any-id")
        body = resp.json()
        assert body["report"] is not None
        assert body["report"]["store_name"] == "Test Store"

    def test_in_progress_job_does_not_expose_report(self, fake_job_row):
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="ingesting", report_json={"secret": "data"})
            )),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/jobs/any-id")
        body = resp.json()
        assert body["report"] is None

    def test_awaiting_approval_exposes_report(self, fake_job_row):
        report = {"findings": []}
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="awaiting_approval", report_json=report)
            )),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/jobs/any-id")
        assert resp.json()["report"] is not None

    def test_failed_job_exposes_report_if_present(self, fake_job_row):
        report = {"ai_readiness_score": 10.0}
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="failed", report_json=report, error_message="LLM timeout")
            )),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/jobs/any-id")
        body = resp.json()
        assert body["report"] is not None
        assert body["error"] == "LLM timeout"

    def test_error_field_is_null_when_no_error(self, api_client):
        body = api_client.get("/jobs/any-id").json()
        assert body["error"] is None


# ===========================================================================
# GET /jobs/{job_id}/fix-plan
# ===========================================================================

class TestGetFixPlan:

    def test_existing_job_with_token_returns_200(self, api_client):
        resp = api_client.get("/jobs/any-job-id/fix-plan")
        assert resp.status_code == 200

    def test_missing_job_returns_404(self, api_client_no_job):
        resp = api_client_no_job.get("/jobs/nonexistent/fix-plan")
        assert resp.status_code == 404

    def test_job_without_admin_token_returns_403(self, fake_job_row):
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(has_token=False)
            )),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/jobs/any-id/fix-plan")
        assert resp.status_code == 403

    def test_response_has_fixes_field(self, api_client):
        resp = api_client.get("/jobs/any-job-id/fix-plan")
        body = resp.json()
        assert "fixes" in body
        assert isinstance(body["fixes"], list)

    def test_fix_plan_json_propagated_to_response(self, fake_job_row):
        fix_plan = {"fixes": [{"fix_id": "f1", "type": "improve_title"}]}
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(fix_plan_json=fix_plan)
            )),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/jobs/any-id/fix-plan")
        body = resp.json()
        assert len(body["fixes"]) == 1
        assert body["fixes"][0]["fix_id"] == "f1"


# ===========================================================================
# GET /jobs/{job_id}/before-after  (section endpoints use stored report)
# ===========================================================================

class TestBeforeAfterEndpoint:

    def test_missing_job_returns_404(self, api_client_no_job):
        resp = api_client_no_job.get("/jobs/nonexistent/before-after")
        assert resp.status_code == 404

    def test_job_without_before_after_in_report_returns_404_or_400(self, fake_job_row):
        # Report exists but has no agent_run.before_after key
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(report_json={"agent_run": {}})
            )),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/jobs/any-id/before-after")
        assert resp.status_code in (400, 404)

    def test_before_after_in_report_returns_200(self, fake_job_row):
        before_after = {
            "original_pillars": {},
            "current_pillars": {},
            "checks_improved": ["C2"],
            "checks_unchanged": [],
        }
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(
                    report_json={"agent_run": {"before_after": before_after}}
                )
            )),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/jobs/any-id/before-after")
        assert resp.status_code == 200
        body = resp.json()
        assert "checks_improved" in body
        assert "C2" in body["checks_improved"]
