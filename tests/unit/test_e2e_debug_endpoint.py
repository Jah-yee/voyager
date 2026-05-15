"""Unit tests for the e2e debug endpoint (GET /e2e/recent_writebacks).

The endpoint has layered defense-in-depth (trinity round 1 P1):
  1. VOYAGER_E2E_DEBUG=1 gates everything (404 otherwise)
  2. Loopback-only by default (non-loopback → 404, override with
     VOYAGER_E2E_ALLOW_NON_LOOPBACK=1)
  3. Optional VOYAGER_E2E_TOKEN paired with X-Voyager-E2E-Token header
  4. Cache-Control: no-store on the response

These tests pin all four layers + the unchanged "returns deque contents"
behavior.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch) -> TestClient:
    """Default test client — bypasses loopback check since TestClient's
    request.client.host is `testclient`, not 127.0.0.1. Individual tests
    that exercise the loopback gate override the env explicitly."""
    monkeypatch.setenv("VOYAGER_E2E_ALLOW_NON_LOOPBACK", "1")
    from voyager.server import app

    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Debug-gate layer
# ---------------------------------------------------------------------------


def test_endpoint_404_when_env_unset(monkeypatch, client) -> None:
    monkeypatch.delenv("VOYAGER_E2E_DEBUG", raising=False)
    response = client.get("/e2e/recent_writebacks")
    assert response.status_code == 404


def test_endpoint_404_when_env_explicitly_false(monkeypatch, client) -> None:
    monkeypatch.setenv("VOYAGER_E2E_DEBUG", "0")
    response = client.get("/e2e/recent_writebacks")
    assert response.status_code == 404


def test_endpoint_200_when_env_truthy(monkeypatch, client) -> None:
    monkeypatch.setenv("VOYAGER_E2E_DEBUG", "1")
    response = client.get("/e2e/recent_writebacks")
    assert response.status_code == 200
    body = response.json()
    assert "count" in body
    assert "writebacks" in body
    assert isinstance(body["writebacks"], list)


@pytest.mark.parametrize("truthy", ["true", "TRUE", "Yes", "y", "on"])
def test_endpoint_accepts_various_truthy_forms(monkeypatch, client, truthy) -> None:
    monkeypatch.setenv("VOYAGER_E2E_DEBUG", truthy)
    response = client.get("/e2e/recent_writebacks")
    assert response.status_code == 200


def test_endpoint_returns_deque_contents_when_enabled(monkeypatch, client) -> None:
    """Insert into the deque and confirm the endpoint returns it."""
    from voyager import server

    monkeypatch.setenv("VOYAGER_E2E_DEBUG", "1")
    server._recent_writebacks.clear()
    server._recent_writebacks.append({"delivery_id": "abc", "event": "pr_review", "status": "OK"})

    response = client.get("/e2e/recent_writebacks")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["writebacks"][0]["delivery_id"] == "abc"

    server._recent_writebacks.clear()


# ---------------------------------------------------------------------------
# Cache-Control header
# ---------------------------------------------------------------------------


def test_endpoint_sets_no_store_cache_header(monkeypatch, client) -> None:
    """Sensitive payload — no caching by intermediaries."""
    monkeypatch.setenv("VOYAGER_E2E_DEBUG", "1")
    response = client.get("/e2e/recent_writebacks")
    assert response.status_code == 200
    cache = response.headers.get("cache-control", "")
    assert "no-store" in cache, f"expected no-store in Cache-Control, got: {cache!r}"


# ---------------------------------------------------------------------------
# Loopback gate
# ---------------------------------------------------------------------------


def test_endpoint_404_for_non_loopback_when_override_unset(monkeypatch) -> None:
    """Without the override, non-loopback clients (e.g. TestClient with
    `testclient` host) get a 404 — same shape as the debug-gate 404 so
    it doesn't leak the endpoint's existence."""
    monkeypatch.setenv("VOYAGER_E2E_DEBUG", "1")
    monkeypatch.delenv("VOYAGER_E2E_ALLOW_NON_LOOPBACK", raising=False)
    from voyager.server import app

    raw_client = TestClient(app, raise_server_exceptions=False)
    response = raw_client.get("/e2e/recent_writebacks")
    assert response.status_code == 404


def test_endpoint_200_when_loopback_override_set(monkeypatch) -> None:
    """The escape hatch for operators running on bastions etc."""
    monkeypatch.setenv("VOYAGER_E2E_DEBUG", "1")
    monkeypatch.setenv("VOYAGER_E2E_ALLOW_NON_LOOPBACK", "1")
    from voyager.server import app

    raw_client = TestClient(app, raise_server_exceptions=False)
    response = raw_client.get("/e2e/recent_writebacks")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Token gate (when VOYAGER_E2E_TOKEN is set)
# ---------------------------------------------------------------------------


def test_endpoint_401_when_token_required_and_header_missing(monkeypatch, client) -> None:
    monkeypatch.setenv("VOYAGER_E2E_DEBUG", "1")
    monkeypatch.setenv("VOYAGER_E2E_TOKEN", "secret-abc")
    response = client.get("/e2e/recent_writebacks")
    assert response.status_code == 401


def test_endpoint_401_when_token_required_and_header_wrong(monkeypatch, client) -> None:
    monkeypatch.setenv("VOYAGER_E2E_DEBUG", "1")
    monkeypatch.setenv("VOYAGER_E2E_TOKEN", "secret-abc")
    response = client.get("/e2e/recent_writebacks", headers={"X-Voyager-E2E-Token": "wrong-token"})
    assert response.status_code == 401


def test_endpoint_200_when_token_required_and_header_matches(monkeypatch, client) -> None:
    monkeypatch.setenv("VOYAGER_E2E_DEBUG", "1")
    monkeypatch.setenv("VOYAGER_E2E_TOKEN", "secret-abc")
    response = client.get("/e2e/recent_writebacks", headers={"X-Voyager-E2E-Token": "secret-abc"})
    assert response.status_code == 200


def test_endpoint_token_unset_means_no_header_required(monkeypatch, client) -> None:
    """Backward-compat: existing operators who set only VOYAGER_E2E_DEBUG=1
    keep working without configuring a token."""
    monkeypatch.setenv("VOYAGER_E2E_DEBUG", "1")
    monkeypatch.delenv("VOYAGER_E2E_TOKEN", raising=False)
    response = client.get("/e2e/recent_writebacks")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Schema visibility
# ---------------------------------------------------------------------------


def test_endpoint_not_in_openapi_schema(client) -> None:
    """Operator-discoverable surfaces (/docs, /openapi.json) must not list
    this endpoint — GLM r1 P3."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json().get("paths", {})
    assert "/e2e/recent_writebacks" not in paths
