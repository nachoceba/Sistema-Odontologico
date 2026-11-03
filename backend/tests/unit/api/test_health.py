"""Tests de GET /api/v1/health y CORS (spec api-health)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_is_public_and_returns_only_status_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_does_not_need_the_database(client: TestClient) -> None:
    # DATABASE_URL apunta a un host inexistente (conftest): igual responde 200.
    assert client.get("/api/v1/health").status_code == 200


def test_health_rejects_post(client: TestClient) -> None:
    assert client.post("/api/v1/health").status_code == 405


def test_health_outside_versioned_prefix_is_404(client: TestClient) -> None:
    assert client.get("/health").status_code == 404


def test_openapi_lists_health_operation(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert "get" in schema["paths"]["/api/v1/health"]


def test_cors_allowed_origin(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_unlisted_origin_gets_no_header(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://malicioso.example"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
