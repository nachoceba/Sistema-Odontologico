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


def test_openapi_lists_the_six_user_operations_with_bearer_scheme(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    operations = {
        ("get", "/api/v1/users"),
        ("post", "/api/v1/users"),
        ("patch", "/api/v1/users/{user_id}"),
        ("post", "/api/v1/users/{user_id}/deactivate"),
        ("post", "/api/v1/users/{user_id}/reactivate"),
        ("put", "/api/v1/users/{user_id}/password"),
    }
    for method, path in operations:
        assert paths[path][method]["security"] == [{"HTTPBearer": []}], (method, path)
    user_paths = {path for path in paths if path.startswith("/api/v1/users")}
    assert user_paths == {path for _, path in operations}


def test_openapi_lists_the_seven_appointment_operations_with_bearer_scheme(
    client: TestClient,
) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    operations = {
        ("post", "/api/v1/appointments"),
        ("get", "/api/v1/appointments"),
        ("get", "/api/v1/appointments/{appointment_id}"),
        ("post", "/api/v1/appointments/{appointment_id}/cancel"),
        ("post", "/api/v1/appointments/{appointment_id}/reschedule"),
        ("post", "/api/v1/appointments/{appointment_id}/attendance"),
        ("get", "/api/v1/professionals/{professional_id}/slots"),
    }
    for method, path in operations:
        assert paths[path][method]["security"] == [{"HTTPBearer": []}], (method, path)
    assert "delete" not in paths["/api/v1/appointments/{appointment_id}"]
