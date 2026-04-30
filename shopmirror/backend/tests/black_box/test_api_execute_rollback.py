"""
Black-box tests for fix execution and rollback endpoints:

  POST /jobs/{job_id}/execute         — trigger fix agent
  POST /jobs/{job_id}/rollback/{fix_id} — reverse a single fix

These are the highest-stakes endpoints in ShopMirror: they write to a live
Shopify store and mutate the job report. Tests verify every guard condition,
auth check, and response contract without making real Shopify API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# ===========================================================================
# POST /jobs/{job_id}/execute
# ===========================================================================

class TestExecuteEndpoint:

    def test_valid_awaiting_approval_returns_202(self, fake_job_row):
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="awaiting_approval", has_token=True)
            )),
            patch("app.main.run_fix_agent_task", new=AsyncMock()),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/jobs/job-1/execute",
                    json={
                        "approved_fix_ids": ["fix-1", "fix-2"],
                        "admin_token": "shpat_test",
                    },
                )
        assert resp.status_code == 202

    def test_returns_execution_job_id(self, fake_job_row):
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="awaiting_approval", has_token=True)
            )),
            patch("app.main.run_fix_agent_task", new=AsyncMock()),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/jobs/job-1/execute",
                    json={"approved_fix_ids": ["fix-1"], "admin_token": "shpat_test"},
                )
        assert "execution_job_id" in resp.json()

    def test_missing_job_returns_404(self, api_client_no_job):
        resp = api_client_no_job.post(
            "/jobs/nonexistent/execute",
            json={"approved_fix_ids": [], "admin_token": "token"},
        )
        assert resp.status_code == 404

    def test_wrong_status_returns_400(self, fake_job_row):
        # Job is 'complete', not 'awaiting_approval'
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="complete", has_token=True)
            )),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/jobs/job-1/execute",
                    json={"approved_fix_ids": ["fix-1"], "admin_token": "shpat_test"},
                )
        assert resp.status_code == 400

    def test_ingesting_status_returns_400(self, fake_job_row):
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="ingesting", has_token=True)
            )),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/jobs/job-1/execute",
                    json={"approved_fix_ids": ["fix-1"], "admin_token": "shpat_test"},
                )
        assert resp.status_code == 400

    def test_no_admin_token_returns_403(self, fake_job_row):
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="awaiting_approval", has_token=False)
            )),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/jobs/job-1/execute",
                    json={"approved_fix_ids": ["fix-1"], "admin_token": "shpat_test"},
                )
        assert resp.status_code == 403

    def test_missing_body_returns_422(self, fake_job_row):
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="awaiting_approval", has_token=True)
            )),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/jobs/job-1/execute", json={})
        assert resp.status_code == 422

    def test_empty_approved_fix_ids_accepted(self, fake_job_row):
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="awaiting_approval", has_token=True)
            )),
            patch("app.main.run_fix_agent_task", new=AsyncMock()),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/jobs/job-1/execute",
                    json={"approved_fix_ids": [], "admin_token": "shpat_test"},
                )
        assert resp.status_code == 202


# ===========================================================================
# POST /jobs/{job_id}/rollback/{fix_id}
# ===========================================================================

class TestRollbackEndpoint:

    def _make_client_with_backup(self, fake_job_row, backup_row: dict):
        """Set up a TestClient where get_fix_backup returns a specific backup."""
        return (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(
                    status="complete",
                    report_json={"agent_run": {"executed_fixes": [], "rolled_back_fix_ids": []}}
                )
            )),
            patch("app.db.queries.get_fix_backup", new=AsyncMock(return_value=backup_row)),
            patch("app.db.queries.list_fix_backups_for_prefix", new=AsyncMock(return_value=[])),
            patch("app.main.patch_report_section", new=AsyncMock(return_value=True)),
            patch("app.db.queries.mark_fix_rolled_back", new=AsyncMock()),
            patch(
                "app.services.shopify_writer.rollback_fix",
                new=AsyncMock(return_value=("title", "Original Title")),
            ),
        )

    def test_valid_rollback_returns_200(self, fake_job_row):
        backup = {
            "fix_id": "fix-1",
            "job_id": "job-1",
            "shopify_gid": "gid://shopify/Product/123",
            "field_type": "title",
            "field_key": "title",
            "original_value": "Original Title",
            "new_value": "Improved Title",
        }
        ctx_managers = self._make_client_with_backup(fake_job_row, backup)
        with ctx_managers[0], ctx_managers[1], ctx_managers[2], ctx_managers[3], \
             ctx_managers[4], ctx_managers[5], ctx_managers[6], ctx_managers[7]:
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/jobs/job-1/rollback/fix-1",
                    json={"admin_token": "shpat_test"},
                )
        assert resp.status_code == 200

    def test_rollback_response_has_required_fields(self, fake_job_row):
        backup = {
            "fix_id": "fix-1",
            "job_id": "job-1",
            "shopify_gid": "gid://shopify/Product/123",
            "field_type": "title",
            "field_key": "title",
            "original_value": "Original Title",
            "new_value": "Improved Title",
        }
        ctx_managers = self._make_client_with_backup(fake_job_row, backup)
        with ctx_managers[0], ctx_managers[1], ctx_managers[2], ctx_managers[3], \
             ctx_managers[4], ctx_managers[5], ctx_managers[6], ctx_managers[7]:
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/jobs/job-1/rollback/fix-1",
                    json={"admin_token": "shpat_test"},
                )
        body = resp.json()
        assert "status" in body
        assert body["status"] == "rolled_back"
        assert "field" in body
        assert "restored_value" in body

    def test_missing_job_returns_404(self, api_client_no_job):
        resp = api_client_no_job.post(
            "/jobs/nonexistent/rollback/fix-1",
            json={"admin_token": "shpat_test"},
        )
        assert resp.status_code == 404

    def test_no_backup_found_returns_404(self, fake_job_row):
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="complete")
            )),
            patch("app.db.queries.get_fix_backup", new=AsyncMock(return_value=None)),
            patch("app.db.queries.list_fix_backups_for_prefix", new=AsyncMock(return_value=[])),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/jobs/job-1/rollback/ghost-fix-id",
                    json={"admin_token": "shpat_test"},
                )
        assert resp.status_code == 404

    def test_backup_belongs_to_different_job_returns_404(self, fake_job_row):
        # Backup exists but has a different job_id
        wrong_job_backup = {
            "fix_id": "fix-1",
            "job_id": "OTHER-JOB",  # belongs to different job
            "shopify_gid": "gid://shopify/Product/123",
            "field_type": "title",
        }
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="complete")
            )),
            patch("app.db.queries.get_fix_backup", new=AsyncMock(return_value=wrong_job_backup)),
            patch("app.db.queries.list_fix_backups_for_prefix", new=AsyncMock(return_value=[])),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/jobs/job-1/rollback/fix-1",
                    json={"admin_token": "shpat_test"},
                )
        # Backup filtered out because job_id doesn't match → 404
        assert resp.status_code == 404

    def test_missing_admin_token_in_body_returns_422(self, api_client):
        resp = api_client.post("/jobs/job-1/rollback/fix-1", json={})
        assert resp.status_code == 422

    def test_shopify_writer_error_returns_500(self, fake_job_row):
        backup = {
            "fix_id": "fix-1",
            "job_id": "job-1",
            "shopify_gid": "gid://shopify/Product/123",
            "field_type": "title",
        }
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.get_job", new=AsyncMock(
                return_value=fake_job_row(status="complete")
            )),
            patch("app.db.queries.get_fix_backup", new=AsyncMock(return_value=backup)),
            patch("app.db.queries.list_fix_backups_for_prefix", new=AsyncMock(return_value=[])),
            patch(
                "app.services.shopify_writer.rollback_fix",
                new=AsyncMock(side_effect=RuntimeError("Shopify API error")),
            ),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/jobs/job-1/rollback/fix-1",
                    json={"admin_token": "shpat_test"},
                )
        assert resp.status_code == 500
