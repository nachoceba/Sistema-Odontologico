"""Gestion de usuarios de punta a punta contra PostgreSQL (spec user-management)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_user_repository
from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.infrastructure.db.enums import UserRole
from app.infrastructure.db.models import ProfessionalModel, UserModel
from app.infrastructure.db.repositories import SqlAlchemyUserAccountRepository
from tests.unit.api.conftest import API_ENV

# Contrasenas inventadas solo para este test; no son las del seed (DD-40).
ADMIN_PASSWORD = "contrasena-admin-de-este-test"
NEW_PASSWORD = "contrasena-nueva-de-este-test"
LOGIN = "/api/v1/auth/login"
USERS = "/api/v1/users"


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> Iterator[TestClient]:
    for name, value in API_ENV.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_user_repository] = lambda: SqlAlchemyUserAccountRepository(
        session_factory
    )
    yield TestClient(app)
    get_settings.cache_clear()


@pytest.fixture
def admin_headers(client: TestClient, session_factory: sessionmaker[Session]) -> dict[str, str]:
    with session_factory.begin() as session:
        session.add(
            UserModel(
                email="admin@example.com",
                password_hash=hash_password(ADMIN_PASSWORD),
                full_name="Admin de Prueba",
                role=UserRole.ADMIN,
            )
        )
    token = client.post(LOGIN, json={"email": "admin@example.com", "password": ADMIN_PASSWORD})
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


def _create_dentist(client: TestClient, headers: dict[str, str], email: str) -> dict[str, str]:
    response = client.post(
        USERS,
        json={
            "email": email,
            "full_name": "Dra. Ficticia Nueva",
            "role": "dentist",
            "password": NEW_PASSWORD,
            "display_name": "Dra. Nueva",
            "license_number": "MN-0001",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body: dict[str, str] = response.json()
    return body


@pytest.mark.integration
def test_creating_a_dentist_stores_account_and_professional_and_allows_login(
    client: TestClient, session_factory: sessionmaker[Session], admin_headers: dict[str, str]
) -> None:
    created = _create_dentist(client, admin_headers, "Dra.Nueva@Example.com")

    with session_factory() as session:
        user = session.scalars(select(UserModel).where(UserModel.id == created["id"])).one()
        professional = session.scalars(
            select(ProfessionalModel).where(ProfessionalModel.user_id == user.id)
        ).one()
    assert user.email == "dra.nueva@example.com"
    assert user.password_hash != NEW_PASSWORD
    assert verify_password(user.password_hash, NEW_PASSWORD) is True
    assert str(professional.id) == created["professional_id"]
    assert (professional.display_name, professional.license_number) == ("Dra. Nueva", "MN-0001")
    assert professional.active is True
    login = client.post(LOGIN, json={"email": "dra.nueva@example.com", "password": NEW_PASSWORD})
    assert login.status_code == 200
    assert login.json()["user"]["professional_id"] == created["professional_id"]


@pytest.mark.integration
def test_deactivating_a_dentist_blocks_login_and_deactivates_the_professional(
    client: TestClient, session_factory: sessionmaker[Session], admin_headers: dict[str, str]
) -> None:
    created = _create_dentist(client, admin_headers, "dra.nueva@example.com")
    token = client.post(
        LOGIN, json={"email": "dra.nueva@example.com", "password": NEW_PASSWORD}
    ).json()["access_token"]

    response = client.post(f"{USERS}/{created['id']}/deactivate", headers=admin_headers)

    assert response.status_code == 200
    login = client.post(LOGIN, json={"email": "dra.nueva@example.com", "password": NEW_PASSWORD})
    assert login.status_code == 401
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 401
    with session_factory() as session:
        professional = session.get(ProfessionalModel, created["professional_id"])
    assert professional is not None
    assert professional.active is False

    client.post(f"{USERS}/{created['id']}/reactivate", headers=admin_headers)
    with session_factory() as session:
        reactivated = session.get(ProfessionalModel, created["professional_id"])
    assert reactivated is not None
    assert reactivated.active is True


@pytest.mark.integration
def test_a_repeated_email_in_other_case_is_409_and_creates_nothing(
    client: TestClient, session_factory: sessionmaker[Session], admin_headers: dict[str, str]
) -> None:
    _create_dentist(client, admin_headers, "dra.nueva@example.com")
    with session_factory() as session:
        before = session.scalar(select(func.count()).select_from(UserModel))

    response = client.post(
        USERS,
        json={
            "email": "DRA.NUEVA@EXAMPLE.COM",
            "full_name": "Otra Persona",
            "role": "dentist",
            "password": NEW_PASSWORD,
        },
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_TAKEN"
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(UserModel)) == before
        assert session.scalar(select(func.count()).select_from(ProfessionalModel)) == 1


@pytest.mark.integration
def test_login_upgrades_a_weak_stored_hash_in_the_database(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    from argon2 import PasswordHasher

    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(ADMIN_PASSWORD)
    user = UserModel(
        email="vieja@example.com",
        password_hash=weak,
        full_name="Cuenta Vieja",
        role=UserRole.RECEPTIONIST,
    )
    with session_factory.begin() as session:
        session.add(user)

    response = client.post(LOGIN, json={"email": "vieja@example.com", "password": ADMIN_PASSWORD})

    assert response.status_code == 200
    with session_factory() as session:
        stored = session.get(UserModel, user.id)
    assert stored is not None
    assert stored.password_hash != weak
    assert verify_password(stored.password_hash, ADMIN_PASSWORD) is True
