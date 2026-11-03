"""GET /api/v1/auth/me (spec user-authentication, P-9)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domain.auth import Role
from app.infrastructure.in_memory import InMemoryUserAccountRepository
from tests.unit.api.conftest import PROFESSIONAL_A, bearer, login_token, make_account

ME = "/api/v1/auth/me"


@pytest.mark.parametrize(
    ("email", "expected"),
    [
        (
            "admin@example.com",
            {
                "id": "u-admin",
                "email": "admin@example.com",
                "full_name": "Admin Demo",
                "role": "admin",
                "professional_id": None,
            },
        ),
        (
            "recepcion@example.com",
            {
                "id": "u-rec",
                "email": "recepcion@example.com",
                "full_name": "Rec Demo",
                "role": "receptionist",
                "professional_id": None,
            },
        ),
        (
            "dra.a@example.com",
            {
                "id": "u-dra-a",
                "email": "dra.a@example.com",
                "full_name": "Dra A",
                "role": "dentist",
                "professional_id": PROFESSIONAL_A,
            },
        ),
    ],
)
def test_each_role_receives_its_own_data(
    auth_client: TestClient, email: str, expected: dict[str, str | None]
) -> None:
    token = login_token(auth_client, email)
    response = auth_client.get(ME, headers=bearer(token))
    assert response.status_code == 200
    assert response.json() == expected
    assert "password_hash" not in response.text
    assert "argon2" not in response.text


def test_no_token_is_401(auth_client: TestClient) -> None:
    response = auth_client.get(ME)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_changed_name_in_repository_is_reflected(
    auth_client: TestClient, user_repo: InMemoryUserAccountRepository
) -> None:
    token = login_token(auth_client, "recepcion@example.com")
    user_repo.add(
        make_account("u-rec", "recepcion@example.com", Role.RECEPTIONIST, full_name="Nombre Nuevo")
    )
    response = auth_client.get(ME, headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["full_name"] == "Nombre Nuevo"
