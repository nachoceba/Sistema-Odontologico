"""Login real contra PostgreSQL con usuarios creados en el test (spec user-authentication)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_user_repository
from app.core.config import get_settings
from app.core.security import hash_password
from app.infrastructure.db.enums import UserRole
from app.infrastructure.db.models import ProfessionalModel, UserModel
from app.infrastructure.db.repositories import SqlAlchemyUserAccountRepository
from tests.unit.api.conftest import API_ENV

# Contrasena inventada solo para este test; no es la del seed (DD-40).
PASSWORD = "contrasena-solo-de-este-test"


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> Iterator[TestClient]:
    for name, value in API_ENV.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    from app.main import create_app  # importa a demanda: crea la app con la configuracion

    app = create_app()
    app.dependency_overrides[get_user_repository] = lambda: SqlAlchemyUserAccountRepository(
        session_factory
    )
    yield TestClient(app)
    get_settings.cache_clear()


def _create_user(
    session_factory: sessionmaker[Session],
    email: str,
    role: UserRole,
    *,
    active: bool = True,
    with_professional: bool = False,
) -> tuple[str, str | None]:
    user = UserModel(
        email=email,
        password_hash=hash_password(PASSWORD),
        full_name="Persona de Prueba",
        role=role,
        active=active,
    )
    with session_factory.begin() as session:
        session.add(user)
    professional_id: str | None = None
    if with_professional:
        professional = ProfessionalModel(user_id=user.id, display_name="Dra. de Prueba")
        with session_factory.begin() as session:
            session.add(professional)
        professional_id = str(professional.id)
    return str(user.id), professional_id


@pytest.mark.integration
def test_login_and_me_against_postgres(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    user_id, professional_id = _create_user(
        session_factory, "Dra.Prueba@Example.com", UserRole.DENTIST, with_professional=True
    )

    login = client.post(
        "/api/v1/auth/login", json={"email": " dra.prueba@example.com ", "password": PASSWORD}
    )

    assert login.status_code == 200
    assert login.json()["user"]["id"] == user_id
    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "dentist"
    assert me.json()["professional_id"] == professional_id
    assert "password_hash" not in me.text


@pytest.mark.integration
def test_deactivated_account_cannot_log_in_and_loses_its_session(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    user_id, _ = _create_user(session_factory, "rec@example.com", UserRole.RECEPTIONIST)
    token = client.post(
        "/api/v1/auth/login", json={"email": "rec@example.com", "password": PASSWORD}
    ).json()["access_token"]
    with session_factory.begin() as session:
        user = session.get(UserModel, user_id)
        assert user is not None
        user.active = False

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    login = client.post(
        "/api/v1/auth/login", json={"email": "rec@example.com", "password": PASSWORD}
    )

    assert me.status_code == 401
    assert login.status_code == 401
    assert login.json()["error"]["code"] == "INVALID_CREDENTIALS"
