"""Permisos por rol de cada endpoint de /api/v1/users (spec user-management, regla dura 4)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domain.auth import UserAccount
from app.infrastructure.in_memory import InMemoryUserAccountRepository
from tests.unit.api.conftest import bearer, login_token

TARGET = "u-rec"
NEW_USER = {
    "email": "nueva@example.com",
    "full_name": "Nueva Persona",
    "role": "receptionist",
    "password": "clave-inicial-12",
}

# (metodo, ruta, cuerpo, estado esperado para el administrador)
ENDPOINTS: list[tuple[str, str, dict[str, Any] | None, int]] = [
    ("GET", "/api/v1/users", None, 200),
    ("POST", "/api/v1/users", NEW_USER, 201),
    ("PATCH", f"/api/v1/users/{TARGET}", {"full_name": "Otro Nombre"}, 200),
    ("POST", f"/api/v1/users/{TARGET}/deactivate", None, 200),
    ("POST", f"/api/v1/users/{TARGET}/reactivate", None, 200),
    ("PUT", f"/api/v1/users/{TARGET}/password", {"password": "clave-nueva-123"}, 204),
]
IDS = [f"{method} {path}" for method, path, _, _ in ENDPOINTS]


def snapshot(repo: InMemoryUserAccountRepository) -> list[UserAccount]:
    return repo.list_all()


@pytest.mark.parametrize(("method", "path", "body", "expected"), ENDPOINTS, ids=IDS)
def test_admin_gets_a_success_status(
    auth_client: TestClient, method: str, path: str, body: dict[str, Any] | None, expected: int
) -> None:
    token = login_token(auth_client, "admin@example.com")
    response = auth_client.request(method, path, json=body, headers=bearer(token))
    assert response.status_code == expected, response.text


@pytest.mark.parametrize("email", ["recepcion@example.com", "dra.a@example.com"])
@pytest.mark.parametrize(("method", "path", "body", "expected"), ENDPOINTS, ids=IDS)
def test_non_admin_roles_get_403_and_nothing_changes(
    auth_client: TestClient,
    user_repo: InMemoryUserAccountRepository,
    email: str,
    method: str,
    path: str,
    body: dict[str, Any] | None,
    expected: int,
) -> None:
    token = login_token(auth_client, email)
    before = snapshot(user_repo)

    response = auth_client.request(method, path, json=body, headers=bearer(token))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert snapshot(user_repo) == before


@pytest.mark.parametrize(("method", "path", "body", "expected"), ENDPOINTS, ids=IDS)
def test_missing_token_gets_401_not_403(
    auth_client: TestClient,
    user_repo: InMemoryUserAccountRepository,
    method: str,
    path: str,
    body: dict[str, Any] | None,
    expected: int,
) -> None:
    before = snapshot(user_repo)

    response = auth_client.request(method, path, json=body)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"
    assert snapshot(user_repo) == before
