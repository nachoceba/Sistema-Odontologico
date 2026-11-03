"""OpenAPI documenta el login y el esquema Bearer (spec user-authentication)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_openapi_lists_login_and_me_with_bearer_scheme(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert "post" in schema["paths"]["/api/v1/auth/login"]
    assert "get" in schema["paths"]["/api/v1/auth/me"]
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert schema["paths"]["/api/v1/auth/me"]["get"]["security"] == [{"HTTPBearer": []}]


def test_login_and_health_declare_no_security(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert "security" not in schema["paths"]["/api/v1/auth/login"]["post"]
    assert "security" not in schema["paths"]["/api/v1/health"]["get"]
