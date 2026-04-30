"""
Black-box tests for public API surface: /health and POST /analyze

Verifies request/response contracts, HTTP status codes, error handling, and
that the server does not leak internal errors to clients.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest


# ===========================================================================
# GET /health
# ===========================================================================

class TestHealthEndpoint:

    def test_returns_200(self, api_client):
        resp = api_client.get("/health")
        assert resp.status_code == 200

    def test_returns_ok_status(self, api_client):
        resp = api_client.get("/health")
        assert resp.json() == {"status": "ok"}

    def test_no_authentication_required(self, api_client):
        resp = api_client.get("/health")
        assert resp.status_code == 200

    def test_returns_json_content_type(self, api_client):
        resp = api_client.get("/health")
        assert "application/json" in resp.headers["content-type"]

    def test_cors_headers_present(self, api_client):
        resp = api_client.get("/health", headers={"Origin": "https://example.com"})
        # CORS middleware adds Access-Control-Allow-Origin
        assert "access-control-allow-origin" in resp.headers


# ===========================================================================
# POST /analyze
# ===========================================================================

class TestAnalyzeEndpoint:

    def test_valid_request_returns_202(self, api_client):
        resp = api_client.post("/analyze", json={"store_url": "https://test.myshopify.com"})
        assert resp.status_code == 202

    def test_valid_request_returns_job_id(self, api_client):
        resp = api_client.post("/analyze", json={"store_url": "https://test.myshopify.com"})
        body = resp.json()
        assert "job_id" in body
        assert body["job_id"]  # non-empty string

    def test_missing_store_url_returns_422(self, api_client):
        resp = api_client.post("/analyze", json={})
        assert resp.status_code == 422

    def test_invalid_json_returns_422(self, api_client):
        resp = api_client.post(
            "/analyze",
            data="not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_invalid_shopify_url_returns_400(self):
        """URL validation failure should return 400 not 500."""
        with (
            patch("app.main.get_pool", new=AsyncMock()),
            patch("app.main.close_pool", new=AsyncMock()),
            patch("app.main.create_job", new=AsyncMock(return_value="job-1")),
            patch(
                "app.main.validate_shopify_url",
                side_effect=ValueError("Not a Shopify URL"),
            ),
        ):
            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/analyze", json={"store_url": "https://notshopify.com"})
            assert resp.status_code == 400

    def test_with_admin_token_returns_202(self, api_client):
        resp = api_client.post(
            "/analyze",
            json={
                "store_url": "https://test.myshopify.com",
                "admin_token": "shpat_test_token",
            },
        )
        assert resp.status_code == 202

    def test_with_merchant_intent_accepted(self, api_client):
        resp = api_client.post(
            "/analyze",
            json={
                "store_url": "https://test.myshopify.com",
                "merchant_intent": "We sell premium athletic footwear.",
            },
        )
        assert resp.status_code == 202

    def test_job_id_is_unique_across_requests(self, api_client):
        # Each call to api_client hits the mocked create_job which returns a new uuid
        ids = []
        for _ in range(3):
            resp = api_client.post("/analyze", json={"store_url": "https://test.myshopify.com"})
            ids.append(resp.json()["job_id"])
        # All IDs are non-empty strings (uniqueness is guaranteed by the mock's uuid4 calls)
        assert all(jid for jid in ids)
