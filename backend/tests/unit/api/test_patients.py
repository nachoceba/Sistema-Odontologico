"""Endpoints de pacientes: formato, errores y validacion sin eco (spec patient-api)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.unit.api.conftest import PatientScene, bearer, login_token

BASE = "/api/v1/patients"
LAURA = {
    "first_name": "Laura",
    "last_name": "Ruiz",
    "document_number": "40.222.334",
    "email": "laura.ruiz@example.com",
}
PATIENT_KEYS = {
    "id",
    "first_name",
    "last_name",
    "document_number",
    "email",
    "phone",
    "birth_date",
    "active",
}


@pytest.fixture
def headers(auth_client: TestClient) -> dict[str, str]:
    return bearer(login_token(auth_client, "recepcion@example.com"))


# --- Endpoints ---


def test_create_then_read_returns_the_same_patient(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    created = auth_client.post(BASE, json=LAURA, headers=headers)
    assert created.status_code == 201, created.text
    body = created.json()
    assert set(body) == PATIENT_KEYS
    assert (body["document_number"], body["phone"], body["birth_date"], body["active"]) == (
        "40222334",
        None,
        None,
        True,
    )
    read = auth_client.get(f"{BASE}/{body['id']}", headers=headers)
    assert read.status_code == 200
    assert read.json() == body


def test_create_with_all_optional_data_returns_them_as_text(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    payload = LAURA | {"phone": "011-5550-0002", "birth_date": "1990-05-10"}
    body = auth_client.post(BASE, json=payload, headers=headers).json()
    assert (body["phone"], body["birth_date"]) == ("011-5550-0002", "1990-05-10")


def test_search_returns_items_and_truncated(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    response = auth_client.get(f"{BASE}?q=P%C3%A9rez", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["truncated"] is False
    assert [item["last_name"] for item in body["items"]] == ["Pérez"]
    assert set(body["items"][0]) == PATIENT_KEYS


def test_search_hides_inactive_unless_asked(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    default = auth_client.get(f"{BASE}?q=G%C3%B3mez", headers=headers).json()
    assert default["items"] == []
    with_inactive = auth_client.get(
        f"{BASE}?q=G%C3%B3mez&include_inactive=true", headers=headers
    ).json()
    assert [i["active"] for i in with_inactive["items"]] == [False]


def test_deactivate_returns_the_patient_and_its_upcoming_appointments(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    response = auth_client.post(f"{BASE}/pac-1/deactivate", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["patient"]["active"] is False
    [upcoming] = body["upcoming_appointments"]
    assert set(upcoming) == {"id", "professional_id", "starts_at", "ends_at", "status"}
    assert upcoming["id"] == patients_scene.appointment_id
    assert upcoming["status"] == "scheduled"
    assert upcoming["starts_at"].endswith("Z") or upcoming["starts_at"].endswith("+00:00")
    assert upcoming["starts_at"].startswith("2026-10-05T13:00:00")


def test_reactivate_returns_the_active_patient(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    response = auth_client.post(f"{BASE}/pac-2/reactivate", headers=headers)
    assert response.status_code == 200
    assert response.json()["active"] is True


def test_patch_with_null_clears_an_optional_field_and_absent_fields_do_not_change(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    created = auth_client.post(
        BASE, json=LAURA | {"phone": "011-5550-0002", "birth_date": "1990-05-10"}, headers=headers
    ).json()
    url = f"{BASE}/{created['id']}"
    first = auth_client.patch(url, json={"phone": None}, headers=headers).json()
    assert (first["phone"], first["birth_date"]) == (None, "1990-05-10")
    second = auth_client.patch(url, json={"email": "nuevo@example.com"}, headers=headers).json()
    assert (second["email"], second["phone"]) == ("nuevo@example.com", None)
    third = auth_client.patch(url, json={"birth_date": None}, headers=headers).json()
    assert third["birth_date"] is None


def test_admin_deletes_a_patient_without_appointments_with_204(
    auth_client: TestClient, patients_scene: PatientScene
) -> None:
    admin = bearer(login_token(auth_client, "admin@example.com"))
    response = auth_client.delete(f"{BASE}/{patients_scene.laura_id}", headers=admin)
    assert response.status_code == 204
    assert response.content == b""
    assert auth_client.get(f"{BASE}/{patients_scene.laura_id}", headers=admin).status_code == 404


def test_delete_of_a_patient_with_appointments_is_409(
    auth_client: TestClient, patients_scene: PatientScene
) -> None:
    admin = bearer(login_token(auth_client, "admin@example.com"))
    response = auth_client.delete(f"{BASE}/pac-1", headers=admin)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PATIENT_HAS_APPOINTMENTS"


def test_unknown_patient_is_404(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    response = auth_client.get(f"{BASE}/no-existe", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PATIENT_NOT_FOUND"


def test_taken_document_is_409_and_the_body_has_no_patient_data(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    response = auth_client.post(
        BASE, json=LAURA | {"document_number": "40.222.333"}, headers=headers
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DOCUMENT_TAKEN"
    text = response.text
    for forbidden in ("40222333", "40.222.333", "Laura", "Ruiz", "laura"):
        assert forbidden not in text


def test_edit_to_a_taken_document_is_409(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    response = auth_client.patch(
        f"{BASE}/pac-1", json={"document_number": "40222333"}, headers=headers
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DOCUMENT_TAKEN"


# --- Validación de entrada sin eco ---


def _assert_no_echo(response: Any, *secrets: str) -> None:
    for secret in secrets:
        assert secret not in response.text


def test_missing_email_is_422_without_echoing_the_other_data(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    payload = {k: v for k, v in LAURA.items() if k != "email"}
    response = auth_client.post(BASE, json=payload, headers=headers)
    assert response.status_code == 422
    _assert_no_echo(response, "Laura", "Ruiz", "40.222.334")


def test_invalid_document_is_422_without_echo(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    response = auth_client.post(
        BASE, json=LAURA | {"document_number": "30111222/1"}, headers=headers
    )
    assert response.status_code == 422
    _assert_no_echo(response, "30111222/1", "Laura")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "sin-arroba"),
        ("phone", "llamar tarde"),
        ("first_name", "   "),
        ("last_name", "a" * 101),
        ("document_number", "123"),
    ],
)
def test_invalid_text_fields_are_422_without_echo(
    auth_client: TestClient,
    patients_scene: PatientScene,
    headers: dict[str, str],
    field: str,
    value: str,
) -> None:
    response = auth_client.post(BASE, json=LAURA | {field: value}, headers=headers)
    assert response.status_code == 422
    _assert_no_echo(response, "llamar tarde", "sin-arroba")


@pytest.mark.parametrize("value", [0, 946684800, "2026-02-30", "10/05/1990", "1990-5-10", True])
def test_birth_date_must_be_a_real_yyyy_mm_dd_text(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str], value: Any
) -> None:
    response = auth_client.post(BASE, json=LAURA | {"birth_date": value}, headers=headers)
    assert response.status_code == 422


def test_future_birth_date_is_400_invalid_patient_data(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    response = auth_client.post(BASE, json=LAURA | {"birth_date": "2999-01-01"}, headers=headers)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PATIENT_DATA"
    _assert_no_echo(response, "2999")


def test_null_email_on_patch_is_422_and_the_record_does_not_change(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    before = patients_scene.snapshot()
    response = auth_client.patch(f"{BASE}/pac-1", json={"email": None}, headers=headers)
    assert response.status_code == 422
    assert patients_scene.snapshot() == before


@pytest.mark.parametrize("field", ["first_name", "last_name", "document_number"])
def test_null_in_any_required_field_on_patch_is_422(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str], field: str
) -> None:
    response = auth_client.patch(f"{BASE}/pac-1", json={field: None}, headers=headers)
    assert response.status_code == 422


def test_unknown_field_is_422(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    assert (
        auth_client.post(BASE, json=LAURA | {"active": False}, headers=headers).status_code == 422
    )
    assert (
        auth_client.patch(f"{BASE}/pac-1", json={"id": "otro"}, headers=headers).status_code == 422
    )


def test_search_text_longer_than_100_characters_is_422(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    assert auth_client.get(f"{BASE}?q={'a' * 101}", headers=headers).status_code == 422
    assert auth_client.get(f"{BASE}?q={'a' * 100}", headers=headers).status_code == 200


def test_include_inactive_must_be_a_boolean(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    assert auth_client.get(f"{BASE}?include_inactive=quizas", headers=headers).status_code == 422


def test_text_fields_are_trimmed_and_the_email_lowercased(
    auth_client: TestClient, patients_scene: PatientScene, headers: dict[str, str]
) -> None:
    payload = LAURA | {"first_name": "  Laura ", "email": " Laura.Ruiz@Example.COM "}
    body = auth_client.post(BASE, json=payload, headers=headers).json()
    assert (body["first_name"], body["email"]) == ("Laura", "laura.ruiz@example.com")
