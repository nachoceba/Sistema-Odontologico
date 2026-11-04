"""Tests de la traduccion de errores a JSON (spec error-model)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import ClassVar

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.errors import DomainError
from app.domain.appointments.errors import AppointmentNotFoundError, SlotTakenError
from app.domain.auth import ForbiddenError, InvalidCredentialsError, NotAuthenticatedError
from app.domain.users.errors import (
    EmailTakenError,
    RoleChangeNotAllowedError,
    SelfModificationError,
    UserNotFoundError,
)


class CodigoSinEstadoError(DomainError):
    code: ClassVar[str] = "CODIGO_SIN_TABLA"


def _boom_not_found() -> None:
    raise AppointmentNotFoundError("apt-1")


def _boom_slot_taken() -> None:
    raise SlotTakenError("dra-a", datetime(2026, 10, 5, 13, 0, tzinfo=UTC))


def _boom_unmapped() -> None:
    raise CodigoSinEstadoError("sin estado asignado")


def _boom_internal() -> None:
    raise RuntimeError("secreto interno: password=hunter2")


@pytest.fixture
def raising_client(make_client: Callable[[], tuple[FastAPI, TestClient]]) -> TestClient:
    app, test_client = make_client()
    app.add_api_route("/__test__/not-found", _boom_not_found)
    app.add_api_route("/__test__/slot-taken", _boom_slot_taken)
    app.add_api_route("/__test__/unmapped", _boom_unmapped)
    app.add_api_route("/__test__/internal", _boom_internal)
    return test_client


def test_known_code_maps_to_404(raising_client: TestClient) -> None:
    response = raising_client.get("/__test__/not-found")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "APPOINTMENT_NOT_FOUND"
    assert body["error"]["message"]


def test_slot_taken_maps_to_409(raising_client: TestClient) -> None:
    response = raising_client.get("/__test__/slot-taken")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SLOT_TAKEN"


def test_code_without_table_entry_maps_to_400(raising_client: TestClient) -> None:
    response = raising_client.get("/__test__/unmapped")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CODIGO_SIN_TABLA"


def test_unexpected_error_is_500_without_internal_details(raising_client: TestClient) -> None:
    response = raising_client.get("/__test__/internal")

    assert response.status_code == 500
    assert response.json() == {"error": {"code": "INTERNAL_ERROR", "message": "Error interno"}}
    assert "hunter2" not in response.text
    assert "Traceback" not in response.text


def _boom_invalid_credentials() -> None:
    raise InvalidCredentialsError


def _boom_not_authenticated() -> None:
    raise NotAuthenticatedError


def _boom_forbidden() -> None:
    raise ForbiddenError


@pytest.fixture
def auth_client(make_client: Callable[[], tuple[FastAPI, TestClient]]) -> TestClient:
    app, test_client = make_client()
    app.add_api_route("/__test__/invalid-credentials", _boom_invalid_credentials)
    app.add_api_route("/__test__/not-authenticated", _boom_not_authenticated)
    app.add_api_route("/__test__/forbidden", _boom_forbidden)
    return test_client


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("/__test__/invalid-credentials", "INVALID_CREDENTIALS"),
        ("/__test__/not-authenticated", "NOT_AUTHENTICATED"),
    ],
)
def test_authentication_errors_are_401_with_www_authenticate(
    auth_client: TestClient, path: str, code: str
) -> None:
    response = auth_client.get(path)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["message"]


def test_forbidden_is_403_without_www_authenticate(auth_client: TestClient) -> None:
    response = auth_client.get("/__test__/forbidden")

    assert response.status_code == 403
    assert "www-authenticate" not in response.headers
    assert response.json() == {
        "error": {"code": "FORBIDDEN", "message": "No tenés permiso para esta acción"}
    }


def test_non_401_domain_errors_do_not_get_www_authenticate(raising_client: TestClient) -> None:
    response = raising_client.get("/__test__/slot-taken")

    assert response.status_code == 409
    assert "www-authenticate" not in response.headers


# --- Gestion de usuarios (C-04) ------------------------------------------------------------------


def _boom_user_not_found() -> None:
    raise UserNotFoundError


def _boom_email_taken() -> None:
    raise EmailTakenError


def _boom_role_change() -> None:
    raise RoleChangeNotAllowedError


def _boom_self_modification() -> None:
    raise SelfModificationError


class SecretBody(BaseModel):
    email: str = Field(pattern=r"^[^@]+@[^@]+$")
    password: str = Field(min_length=8, max_length=20)


def _echo(body: SecretBody) -> dict[str, str]:
    return {"email": body.email}


@pytest.fixture
def users_client(make_client: Callable[[], tuple[FastAPI, TestClient]]) -> TestClient:
    app, test_client = make_client()
    app.add_api_route("/__test__/user-not-found", _boom_user_not_found)
    app.add_api_route("/__test__/email-taken", _boom_email_taken)
    app.add_api_route("/__test__/role-change", _boom_role_change)
    app.add_api_route("/__test__/self-modification", _boom_self_modification)
    app.add_api_route("/__test__/echo", _echo, methods=["POST"])
    return test_client


def test_user_not_found_is_404(users_client: TestClient) -> None:
    response = users_client.get("/__test__/user-not-found")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("/__test__/email-taken", "EMAIL_TAKEN"),
        ("/__test__/role-change", "ROLE_CHANGE_NOT_ALLOWED"),
        ("/__test__/self-modification", "SELF_MODIFICATION_NOT_ALLOWED"),
    ],
)
def test_user_management_conflicts_are_409_without_www_authenticate(
    users_client: TestClient, path: str, code: str
) -> None:
    response = users_client.get(path)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["message"]
    assert "www-authenticate" not in response.headers


def test_validation_error_keeps_the_field_list_but_not_the_values_sent(
    users_client: TestClient,
) -> None:
    secret = "contrasena-valida-123"
    response = users_client.post("/__test__/echo", json={"email": "sin-arroba", "password": secret})

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert errors[0]["loc"] == ["body", "email"]
    assert errors[0]["msg"]
    assert errors[0]["type"]
    assert all("input" not in error and "ctx" not in error for error in errors)
    assert secret not in response.text
    assert "sin-arroba" not in response.text


def test_validation_error_on_the_password_itself_does_not_echo_it(
    users_client: TestClient,
) -> None:
    too_long = "x" * 21
    response = users_client.post("/__test__/echo", json={"email": "a@b", "password": too_long})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "password"]
    assert too_long not in response.text
