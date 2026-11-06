"""``current_user``, ``require_role`` y ``require_professional_access`` (spec access-control)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    current_user,
    require_professional_access,
    require_role,
)
from app.core.security import create_access_token
from app.domain.auth import Principal, Role
from app.infrastructure.in_memory import InMemoryUserAccountRepository
from tests.unit.api.conftest import (
    PROFESSIONAL_A,
    PROFESSIONAL_B,
    bearer,
    login_token,
    make_account,
)

SECRET = "k" * 48
ALL_ROLE_EMAILS = {
    Role.ADMIN: "admin@example.com",
    Role.RECEPTIONIST: "recepcion@example.com",
    Role.DENTIST: "dra.a@example.com",
}


def _whoami(principal: Annotated[Principal, Depends(current_user)]) -> dict[str, str]:
    return {"id": principal.user_id, "role": principal.role.value}


def _admin_only(
    principal: Annotated[Principal, Depends(require_role(Role.ADMIN))],
) -> dict[str, str]:
    return {"id": principal.user_id}


def _admin_or_reception(
    principal: Annotated[Principal, Depends(require_role(Role.ADMIN, Role.RECEPTIONIST))],
) -> dict[str, str]:
    return {"id": principal.user_id}


def _professional(
    professional_id: str,
    _principal: Annotated[Principal, Depends(require_professional_access)],
) -> dict[str, str]:
    return {"professional_id": professional_id}


@pytest.fixture
def client(auth_app: tuple[FastAPI, TestClient]) -> TestClient:
    app, test_client = auth_app
    app.add_api_route("/api/v1/_test/whoami", _whoami)
    app.add_api_route("/api/v1/_test/admin", _admin_only)
    app.add_api_route("/api/v1/_test/staff", _admin_or_reception)
    app.add_api_route("/api/v1/_test/professionals/{professional_id}", _professional)
    return test_client


def _token(
    user_id: str, role: Role, *, expires_minutes: int = 30, now: datetime | None = None
) -> str:
    return create_access_token(
        user_id=user_id, role=role, secret=SECRET, expires_minutes=expires_minutes, now=now
    )


def assert_not_authenticated(response_status: int, body: dict[str, dict[str, str]]) -> None:
    assert response_status == 401
    assert body["error"]["code"] == "NOT_AUTHENTICATED"


def test_valid_token_resolves_the_principal(client: TestClient) -> None:
    token = login_token(client, "recepcion@example.com")
    response = client.get("/api/v1/_test/whoami", headers=bearer(token))
    assert response.status_code == 200
    assert response.json() == {"id": "u-rec", "role": "receptionist"}


def test_missing_header_is_401_with_uniform_body(client: TestClient) -> None:
    response = client.get("/api/v1/_test/whoami")
    assert_not_authenticated(response.status_code, response.json())
    assert response.headers["www-authenticate"] == "Bearer"
    assert "detail" not in response.json()


def test_basic_scheme_is_401(client: TestClient) -> None:
    response = client.get("/api/v1/_test/whoami", headers={"Authorization": "Basic YTpi"})
    assert_not_authenticated(response.status_code, response.json())


def test_garbage_bearer_token_is_401(client: TestClient) -> None:
    response = client.get("/api/v1/_test/whoami", headers=bearer("no.es.un.token"))
    assert_not_authenticated(response.status_code, response.json())


def test_expired_token_is_401(client: TestClient) -> None:
    old = datetime.now(UTC) - timedelta(minutes=31)
    token = _token("u-rec", Role.RECEPTIONIST, now=old)
    response = client.get("/api/v1/_test/whoami", headers=bearer(token))
    assert_not_authenticated(response.status_code, response.json())


def test_deactivated_account_with_valid_token_is_401(client: TestClient) -> None:
    token = _token("u-baja", Role.RECEPTIONIST)
    response = client.get("/api/v1/_test/whoami", headers=bearer(token))
    assert_not_authenticated(response.status_code, response.json())


def test_account_deactivated_after_login_is_cut_off(
    client: TestClient, user_repo: InMemoryUserAccountRepository
) -> None:
    token = login_token(client, "recepcion@example.com")
    user_repo.add(make_account("u-rec", "recepcion@example.com", Role.RECEPTIONIST, active=False))
    response = client.get("/api/v1/_test/whoami", headers=bearer(token))
    assert_not_authenticated(response.status_code, response.json())


def test_role_changed_after_login_is_401(
    client: TestClient, user_repo: InMemoryUserAccountRepository
) -> None:
    token = login_token(client, "recepcion@example.com")
    user_repo.add(make_account("u-rec", "recepcion@example.com", Role.ADMIN))
    response = client.get("/api/v1/_test/whoami", headers=bearer(token))
    assert_not_authenticated(response.status_code, response.json())


def test_token_for_deleted_account_is_401(client: TestClient) -> None:
    response = client.get("/api/v1/_test/whoami", headers=bearer(_token("fantasma", Role.ADMIN)))
    assert_not_authenticated(response.status_code, response.json())


@pytest.mark.parametrize(
    ("path", "allowed"),
    [
        ("/api/v1/_test/admin", {Role.ADMIN}),
        ("/api/v1/_test/staff", {Role.ADMIN, Role.RECEPTIONIST}),
    ],
)
@pytest.mark.parametrize("role", list(Role))
def test_role_matrix_for_a_route(
    client: TestClient, path: str, allowed: set[Role], role: Role
) -> None:
    token = login_token(client, ALL_ROLE_EMAILS[role])
    response = client.get(path, headers=bearer(token))
    if role in allowed:
        assert response.status_code == 200
    else:
        assert response.status_code == 403
        assert response.json() == {
            "error": {"code": "FORBIDDEN", "message": "No tenés permiso para esta acción"}
        }
        assert "www-authenticate" not in response.headers


@pytest.mark.parametrize("path", ["/api/v1/_test/admin", "/api/v1/_test/staff"])
def test_no_token_on_role_route_is_401_not_403(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert_not_authenticated(response.status_code, response.json())


def test_dentist_accesses_own_professional(client: TestClient) -> None:
    token = login_token(client, "dra.a@example.com")
    response = client.get(f"/api/v1/_test/professionals/{PROFESSIONAL_A}", headers=bearer(token))
    assert response.status_code == 200


def test_dentist_gets_403_for_another_professional(client: TestClient) -> None:
    token = login_token(client, "dra.a@example.com")
    response = client.get(f"/api/v1/_test/professionals/{PROFESSIONAL_B}", headers=bearer(token))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_dentist_without_record_gets_403(client: TestClient) -> None:
    token = login_token(client, "sinficha@example.com")
    response = client.get(f"/api/v1/_test/professionals/{PROFESSIONAL_A}", headers=bearer(token))
    assert response.status_code == 403


def test_malformed_professional_id_is_403_for_dentist(client: TestClient) -> None:
    token = login_token(client, "dra.a@example.com")
    response = client.get("/api/v1/_test/professionals/no-es-uuid", headers=bearer(token))
    assert response.status_code == 403


@pytest.mark.parametrize("email", ["recepcion@example.com", "admin@example.com"])
@pytest.mark.parametrize("target", [PROFESSIONAL_A, PROFESSIONAL_B])
def test_reception_and_admin_access_any_professional(
    client: TestClient, email: str, target: str
) -> None:
    token = login_token(client, email)
    response = client.get(f"/api/v1/_test/professionals/{target}", headers=bearer(token))
    assert response.status_code == 200


def test_professional_route_without_token_is_401(client: TestClient) -> None:
    response = client.get(f"/api/v1/_test/professionals/{PROFESSIONAL_A}")
    assert_not_authenticated(response.status_code, response.json())


# --- Dependencias de agenda (C-08, design D-4 y D-7) ---


def test_the_default_clock_is_the_current_utc_instant() -> None:
    from app.api.dependencies import get_clock

    before = datetime.now(UTC)
    moment = get_clock()()
    after = datetime.now(UTC)

    assert moment.utcoffset() == timedelta(0)
    assert before <= moment <= after


def test_the_default_agenda_wiring_has_the_celery_dispatcher() -> None:
    from app.api.dependencies import get_agenda_deps
    from app.infrastructure.tasks.dispatcher import CeleryNotificationDispatcher

    fixed = datetime(2026, 10, 5, 13, 0, tzinfo=UTC)
    deps = get_agenda_deps(lambda: fixed)

    assert isinstance(deps.dispatcher, CeleryNotificationDispatcher)
    assert deps.clock() == fixed
