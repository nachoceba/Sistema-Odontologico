"""POST /api/v1/auth/login (spec user-authentication)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.unit.api.conftest import AUTH_PASSWORD, PROFESSIONAL_A

LOGIN = "/api/v1/auth/login"
GENERIC = {"code": "INVALID_CREDENTIALS", "message": "Email o contraseña incorrectos"}


def test_valid_login_returns_token_and_public_user_data(auth_client: TestClient) -> None:
    response = auth_client.post(
        LOGIN, json={"email": "admin@example.com", "password": AUTH_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] == 30 * 60
    assert body["user"] == {
        "id": "u-admin",
        "email": "admin@example.com",
        "full_name": "Admin Demo",
        "role": "admin",
        "professional_id": None,
    }
    assert "password_hash" not in response.text
    assert "argon2" not in response.text
    assert AUTH_PASSWORD not in response.text


def test_dentist_login_includes_professional_id(auth_client: TestClient) -> None:
    response = auth_client.post(
        LOGIN, json={"email": "dra.a@example.com", "password": AUTH_PASSWORD}
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "dentist"
    assert response.json()["user"]["professional_id"] == PROFESSIONAL_A


def test_failures_are_401_with_identical_generic_message(auth_client: TestClient) -> None:
    wrong_password = auth_client.post(
        LOGIN, json={"email": "admin@example.com", "password": "mala"}
    )
    unknown_email = auth_client.post(
        LOGIN, json={"email": "nadie@example.com", "password": AUTH_PASSWORD}
    )
    deactivated = auth_client.post(
        LOGIN, json={"email": "baja@example.com", "password": AUTH_PASSWORD}
    )

    for response in (wrong_password, unknown_email, deactivated):
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert response.json() == {"error": GENERIC}
        assert "access_token" not in response.text


def test_email_with_uppercase_and_spaces_logs_in(auth_client: TestClient) -> None:
    response = auth_client.post(
        LOGIN, json={"email": "  Admin@Example.COM ", "password": AUTH_PASSWORD}
    )

    assert response.status_code == 200
    assert response.json()["user"]["id"] == "u-admin"


def test_empty_fields_are_422(auth_client: TestClient) -> None:
    assert auth_client.post(LOGIN, json={"email": "", "password": "x"}).status_code == 422
    assert auth_client.post(LOGIN, json={"email": "a@b.com", "password": ""}).status_code == 422
    assert auth_client.post(LOGIN, json={}).status_code == 422


def test_password_longer_than_128_is_422(auth_client: TestClient) -> None:
    long = "x" * 129
    assert auth_client.post(LOGIN, json={"email": "a@b.com", "password": long}).status_code == 422
    ok = "x" * 128
    assert auth_client.post(LOGIN, json={"email": "a@b.com", "password": ok}).status_code == 401


def test_422_on_a_too_long_password_does_not_echo_it(auth_client: TestClient) -> None:
    long = "x" * 129
    response = auth_client.post(LOGIN, json={"email": "a@b.com", "password": long})

    assert response.status_code == 422
    assert long not in response.text
