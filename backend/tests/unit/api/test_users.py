"""Endpoints /api/v1/users con el repositorio en memoria (spec user-management)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security import verify_password
from app.infrastructure.in_memory import InMemoryUserAccountRepository
from tests.unit.api.conftest import AUTH_PASSWORD, bearer, login_token

USERS = "/api/v1/users"
LOGIN = "/api/v1/auth/login"
NEW_PASSWORD = "clave-inicial-12"


@pytest.fixture
def admin(auth_client: TestClient) -> dict[str, str]:
    return bearer(login_token(auth_client, "admin@example.com"))


def _new_user(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "email": "nueva@example.com",
        "full_name": "Nueva Persona",
        "role": "receptionist",
        "password": NEW_PASSWORD,
    }
    body.update(overrides)
    return body


def _login(client: TestClient, email: str, password: str) -> int:
    return client.post(LOGIN, json={"email": email, "password": password}).status_code


# --- Listado -------------------------------------------------------------------------------------


def test_list_returns_all_accounts_ordered_without_secrets(
    auth_client: TestClient, admin: dict[str, str]
) -> None:
    response = auth_client.get(USERS, headers=admin)

    assert response.status_code == 200
    items = response.json()
    assert [item["full_name"] for item in items] == [
        "Admin Demo",
        "Dra A",
        "Rec Demo",
        "Usuario Demo",
        "Usuario Demo",
    ]
    assert set(items[0]) == {"id", "email", "full_name", "role", "active", "professional_id"}
    dra = next(item for item in items if item["id"] == "u-dra-a")
    assert dra["professional_id"] is not None
    assert next(item for item in items if item["id"] == "u-baja")["active"] is False
    assert "password" not in response.text
    assert "argon2" not in response.text


# --- Alta ----------------------------------------------------------------------------------------


def test_create_receptionist_returns_201_and_the_account_can_log_in(
    auth_client: TestClient, admin: dict[str, str]
) -> None:
    response = auth_client.post(
        USERS, json=_new_user(email="Nueva.Recepcion@Example.com "), headers=admin
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "nueva.recepcion@example.com"
    assert body["active"] is True
    assert body["role"] == "receptionist"
    assert body["professional_id"] is None
    assert NEW_PASSWORD not in response.text
    assert _login(auth_client, "nueva.recepcion@example.com", NEW_PASSWORD) == 200


def test_the_password_is_stored_only_as_an_argon2_hash(
    auth_client: TestClient, admin: dict[str, str], user_repo: InMemoryUserAccountRepository
) -> None:
    created = auth_client.post(USERS, json=_new_user(), headers=admin).json()

    stored = user_repo.get_by_id(created["id"])
    assert stored is not None
    assert stored.password_hash != NEW_PASSWORD
    assert stored.password_hash.startswith("$argon2")
    assert verify_password(stored.password_hash, NEW_PASSWORD) is True


def test_create_dentist_creates_the_professional_with_the_given_data(
    auth_client: TestClient, admin: dict[str, str], user_repo: InMemoryUserAccountRepository
) -> None:
    response = auth_client.post(
        USERS,
        json=_new_user(
            role="dentist",
            full_name="Dra. Ficticia Nueva",
            display_name="Dra. Ficticia Nueva",
            license_number="MN-0001",
        ),
        headers=admin,
    )

    assert response.status_code == 201
    professional_id = response.json()["professional_id"]
    professional = user_repo.professionals[professional_id]
    assert (professional.display_name, professional.license_number, professional.active) == (
        "Dra. Ficticia Nueva",
        "MN-0001",
        True,
    )


def test_create_dentist_without_display_name_uses_the_full_name(
    auth_client: TestClient, admin: dict[str, str], user_repo: InMemoryUserAccountRepository
) -> None:
    response = auth_client.post(
        USERS, json=_new_user(role="dentist", full_name="Dr. Sin Alias"), headers=admin
    )

    assert user_repo.professionals[response.json()["professional_id"]].display_name == (
        "Dr. Sin Alias"
    )


def test_create_receptionist_ignores_the_professional_fields(
    auth_client: TestClient, admin: dict[str, str]
) -> None:
    response = auth_client.post(USERS, json=_new_user(license_number="MN-9"), headers=admin)

    assert response.status_code == 201
    assert response.json()["professional_id"] is None


def test_create_with_a_taken_email_in_capitals_is_409(
    auth_client: TestClient, admin: dict[str, str], user_repo: InMemoryUserAccountRepository
) -> None:
    before = len(user_repo.list_all())

    response = auth_client.post(USERS, json=_new_user(email="RECEPCION@EXAMPLE.COM"), headers=admin)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_TAKEN"
    assert len(user_repo.list_all()) == before


@pytest.mark.parametrize(
    "overrides",
    [
        {"password": "1234567"},
        {"email": "sin-arroba.example.com"},
        {"email": "dos@arrobas@example.com"},
        {"email": "con espacio@example.com"},
        {"role": "superadmin"},
        {"full_name": "   "},
        {"password": "x" * 129},
        {"display_name": ""},
    ],
    ids=[
        "password-7",
        "email-sin-arroba",
        "email-dos-arrobas",
        "email-con-espacio",
        "rol-inexistente",
        "nombre-vacio",
        "password-129",
        "display-name-vacio",
    ],
)
def test_invalid_creation_data_is_422_and_creates_nothing(
    auth_client: TestClient,
    admin: dict[str, str],
    user_repo: InMemoryUserAccountRepository,
    overrides: dict[str, object],
) -> None:
    before = len(user_repo.list_all())
    body = _new_user(**overrides)

    response = auth_client.post(USERS, json=body, headers=admin)

    assert response.status_code == 422
    assert len(user_repo.list_all()) == before
    assert str(body["password"]) not in response.text


def test_missing_fields_are_422(auth_client: TestClient, admin: dict[str, str]) -> None:
    assert auth_client.post(USERS, json={"email": "a@b.com"}, headers=admin).status_code == 422


def test_422_for_a_bad_email_does_not_echo_the_valid_password(
    auth_client: TestClient, admin: dict[str, str]
) -> None:
    response = auth_client.post(USERS, json=_new_user(email="sin-arroba"), headers=admin)

    assert response.status_code == 422
    assert NEW_PASSWORD not in response.text
    assert any(error["loc"][-1] == "email" for error in response.json()["detail"])


def test_password_is_not_trimmed(auth_client: TestClient, admin: dict[str, str]) -> None:
    padded = "  clave con espacios  "
    auth_client.post(USERS, json=_new_user(password=padded), headers=admin)

    assert _login(auth_client, "nueva@example.com", padded) == 200
    assert _login(auth_client, "nueva@example.com", padded.strip()) == 401


# --- Edicion -------------------------------------------------------------------------------------


def test_patch_changes_the_name_and_nothing_else(
    auth_client: TestClient, admin: dict[str, str]
) -> None:
    response = auth_client.patch(
        f"{USERS}/u-rec", json={"full_name": " Nombre Nuevo "}, headers=admin
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "u-rec",
        "email": "recepcion@example.com",
        "full_name": "Nombre Nuevo",
        "role": "receptionist",
        "active": True,
        "professional_id": None,
    }


def test_patch_email_lets_the_account_log_in_with_the_new_one_only(
    auth_client: TestClient, admin: dict[str, str]
) -> None:
    rec_token = login_token(auth_client, "recepcion@example.com")

    response = auth_client.patch(
        f"{USERS}/u-rec", json={"email": "Nuevo.Mail@Example.com"}, headers=admin
    )

    assert response.status_code == 200
    assert response.json()["email"] == "nuevo.mail@example.com"
    assert auth_client.get("/api/v1/auth/me", headers=bearer(rec_token)).status_code == 200
    assert _login(auth_client, "nuevo.mail@example.com", AUTH_PASSWORD) == 200
    assert _login(auth_client, "recepcion@example.com", AUTH_PASSWORD) == 401


def test_patch_with_the_email_of_another_account_is_409(
    auth_client: TestClient, admin: dict[str, str], user_repo: InMemoryUserAccountRepository
) -> None:
    before = user_repo.get_by_id("u-rec")

    response = auth_client.patch(
        f"{USERS}/u-rec", json={"email": "DRA.A@example.com"}, headers=admin
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_TAKEN"
    assert user_repo.get_by_id("u-rec") == before


def test_patch_with_the_own_email_in_other_case_is_200(
    auth_client: TestClient, admin: dict[str, str]
) -> None:
    response = auth_client.patch(
        f"{USERS}/u-rec", json={"email": "RECEPCION@Example.com"}, headers=admin
    )

    assert response.status_code == 200
    assert response.json()["email"] == "recepcion@example.com"


def test_patch_role_to_admin_invalidates_the_open_session(
    auth_client: TestClient, admin: dict[str, str]
) -> None:
    rec_token = login_token(auth_client, "recepcion@example.com")

    response = auth_client.patch(f"{USERS}/u-rec", json={"role": "admin"}, headers=admin)

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    after = auth_client.get("/api/v1/auth/me", headers=bearer(rec_token))
    assert after.status_code == 401


def test_patch_role_to_dentist_creates_the_professional(
    auth_client: TestClient, admin: dict[str, str], user_repo: InMemoryUserAccountRepository
) -> None:
    response = auth_client.patch(f"{USERS}/u-rec", json={"role": "dentist"}, headers=admin)

    assert response.status_code == 200
    professional = user_repo.professionals[response.json()["professional_id"]]
    assert (professional.display_name, professional.active) == ("Rec Demo", True)


def test_patch_role_of_a_dentist_is_409_and_changes_nothing(
    auth_client: TestClient, admin: dict[str, str], user_repo: InMemoryUserAccountRepository
) -> None:
    before = user_repo.get_by_id("u-dra-a")

    response = auth_client.patch(f"{USERS}/u-dra-a", json={"role": "receptionist"}, headers=admin)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ROLE_CHANGE_NOT_ALLOWED"
    assert user_repo.get_by_id("u-dra-a") == before


def test_patch_same_role_is_200_and_changes_nothing(
    auth_client: TestClient, admin: dict[str, str], user_repo: InMemoryUserAccountRepository
) -> None:
    before = user_repo.get_by_id("u-dra-a")

    response = auth_client.patch(f"{USERS}/u-dra-a", json={"role": "dentist"}, headers=admin)

    assert response.status_code == 200
    assert user_repo.get_by_id("u-dra-a") == before


def test_the_admin_cannot_change_the_own_role(
    auth_client: TestClient, admin: dict[str, str]
) -> None:
    response = auth_client.patch(f"{USERS}/u-admin", json={"role": "receptionist"}, headers=admin)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SELF_MODIFICATION_NOT_ALLOWED"


def test_patch_with_an_invalid_role_or_email_is_422(
    auth_client: TestClient, admin: dict[str, str]
) -> None:
    assert auth_client.patch(f"{USERS}/u-rec", json={"role": "x"}, headers=admin).status_code == 422
    bad_email = auth_client.patch(f"{USERS}/u-rec", json={"email": "sin-arroba"}, headers=admin)
    assert bad_email.status_code == 422


# --- Desactivar y reactivar ----------------------------------------------------------------------


def test_deactivate_blocks_login_and_kills_the_open_session(
    auth_client: TestClient, admin: dict[str, str]
) -> None:
    rec_token = login_token(auth_client, "recepcion@example.com")

    response = auth_client.post(f"{USERS}/u-rec/deactivate", headers=admin)

    assert response.status_code == 200
    assert response.json()["active"] is False
    assert _login(auth_client, "recepcion@example.com", AUTH_PASSWORD) == 401
    stale = auth_client.get("/api/v1/auth/me", headers=bearer(rec_token))
    assert stale.status_code == 401
    assert stale.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_deactivate_a_dentist_deactivates_the_professional_and_reactivate_restores_it(
    auth_client: TestClient, admin: dict[str, str], user_repo: InMemoryUserAccountRepository
) -> None:
    professional_id = user_repo.get_by_id("u-dra-a").professional_id  # type: ignore[union-attr]
    assert professional_id is not None

    off = auth_client.post(f"{USERS}/u-dra-a/deactivate", headers=admin)
    assert off.json()["active"] is False
    assert user_repo.professionals[professional_id].active is False

    on = auth_client.post(f"{USERS}/u-dra-a/reactivate", headers=admin)
    assert on.json()["active"] is True
    assert user_repo.professionals[professional_id].active is True
    assert _login(auth_client, "dra.a@example.com", AUTH_PASSWORD) == 200


def test_reactivate_lets_a_deactivated_account_log_in_again(
    auth_client: TestClient, admin: dict[str, str]
) -> None:
    response = auth_client.post(f"{USERS}/u-baja/reactivate", headers=admin)

    assert response.status_code == 200
    assert response.json()["active"] is True
    assert _login(auth_client, "baja@example.com", AUTH_PASSWORD) == 200


def test_deactivate_twice_is_200_both_times(auth_client: TestClient, admin: dict[str, str]) -> None:
    first = auth_client.post(f"{USERS}/u-baja/deactivate", headers=admin)
    second = auth_client.post(f"{USERS}/u-baja/deactivate", headers=admin)

    assert (first.status_code, second.status_code) == (200, 200)
    assert second.json()["active"] is False


def test_the_admin_cannot_deactivate_the_own_account(
    auth_client: TestClient, admin: dict[str, str]
) -> None:
    response = auth_client.post(f"{USERS}/u-admin/deactivate", headers=admin)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SELF_MODIFICATION_NOT_ALLOWED"
    assert auth_client.get("/api/v1/auth/me", headers=admin).status_code == 200


# --- Contrasena ----------------------------------------------------------------------------------


def test_set_password_replaces_the_old_one(auth_client: TestClient, admin: dict[str, str]) -> None:
    response = auth_client.put(
        f"{USERS}/u-rec/password", json={"password": "clave-nueva-123"}, headers=admin
    )

    assert response.status_code == 204
    assert response.content == b""
    assert _login(auth_client, "recepcion@example.com", "clave-nueva-123") == 200
    assert _login(auth_client, "recepcion@example.com", AUTH_PASSWORD) == 401


@pytest.mark.parametrize("password", ["x" * 129, "1234567", ""])
def test_set_password_with_an_invalid_length_is_422_and_keeps_the_old_one(
    auth_client: TestClient, admin: dict[str, str], password: str
) -> None:
    response = auth_client.put(
        f"{USERS}/u-rec/password", json={"password": password}, headers=admin
    )

    assert response.status_code == 422
    assert password == "" or password not in response.text
    assert _login(auth_client, "recepcion@example.com", AUTH_PASSWORD) == 200


# --- Cuenta inexistente --------------------------------------------------------------------------


@pytest.mark.parametrize("user_id", [str(uuid.uuid4()), "no-es-un-uuid"])
@pytest.mark.parametrize(
    ("method", "suffix", "body"),
    [
        ("PATCH", "", {"full_name": "X"}),
        ("POST", "/deactivate", None),
        ("POST", "/reactivate", None),
        ("PUT", "/password", {"password": "clave-nueva-123"}),
    ],
)
def test_unknown_or_malformed_id_is_404(
    auth_client: TestClient,
    admin: dict[str, str],
    user_id: str,
    method: str,
    suffix: str,
    body: dict[str, str] | None,
) -> None:
    response = auth_client.request(method, f"{USERS}/{user_id}{suffix}", json=body, headers=admin)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"
