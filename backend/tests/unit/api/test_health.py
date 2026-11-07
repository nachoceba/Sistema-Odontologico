"""Tests de GET /api/v1/health y CORS (spec api-health)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import get_settings


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


# --- CORS estricto: metodos y encabezados explicitos, sin credenciales (C-13, D-3) ---

ALLOWED_ORIGIN = "http://localhost:5173"


def preflight(client: TestClient, *, origin: str, method: str, headers: str):  # type: ignore[no-untyped-def]
    return client.options(
        "/api/v1/patients",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )


def test_preflight_with_frontend_headers_is_allowed_without_credentials(
    client: TestClient,
) -> None:
    response = preflight(
        client, origin=ALLOWED_ORIGIN, method="PATCH", headers="authorization, content-type"
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "PATCH" in response.headers["access-control-allow-methods"]
    allowed = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed and "content-type" in allowed
    assert "access-control-allow-credentials" not in response.headers


def test_preflight_with_an_unused_header_is_not_authorized(client: TestClient) -> None:
    response = preflight(client, origin=ALLOWED_ORIGIN, method="GET", headers="x-otro-encabezado")

    assert response.status_code == 400
    assert "x-otro-encabezado" not in response.headers.get("access-control-allow-headers", "")


def test_preflight_with_an_unused_method_is_not_authorized(client: TestClient) -> None:
    response = preflight(client, origin=ALLOWED_ORIGIN, method="HEAD", headers="authorization")

    assert response.status_code == 400


def test_preflight_from_an_unlisted_origin_gets_no_allow_origin(client: TestClient) -> None:
    response = preflight(
        client,
        origin="http://malicioso.example",
        method="PATCH",
        headers="authorization, content-type",
    )

    assert "access-control-allow-origin" not in response.headers


def test_demo_origin_is_allowed_when_listed_in_cors_origins(
    monkeypatch: pytest.MonkeyPatch,
    make_client: Callable[[], tuple[FastAPI, TestClient]],
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080")
    get_settings.cache_clear()
    _, demo_client = make_client()

    response = demo_client.get("/api/v1/health", headers={"Origin": "http://localhost:8080"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:8080"
