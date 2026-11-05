"""Permisos por rol de los siete endpoints de pacientes (spec patient-api)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.unit.api.conftest import PatientScene, bearer, login_token

ADMIN = "admin@example.com"
RECEPTION = "recepcion@example.com"
DENTIST_A = "dra.a@example.com"
NO_FILE = "sinficha@example.com"
UNKNOWN = "no-existe"

NEW_PATIENT = {
    "first_name": "Marta",
    "last_name": "López",
    "document_number": "40.555.666",
    "email": "marta@example.com",
}


@dataclass(frozen=True)
class Call:
    method: str
    path: str
    body: dict[str, Any] | None = None


def calls(scene: PatientScene) -> dict[str, Call]:
    base = "/api/v1/patients"
    return {
        "list": Call("GET", f"{base}?q=ruiz"),
        "detail": Call("GET", f"{base}/pac-1"),
        "create": Call("POST", base, NEW_PATIENT),
        "update": Call("PATCH", f"{base}/pac-1", {"email": "nuevo@example.com"}),
        "deactivate": Call("POST", f"{base}/pac-1/deactivate"),
        "reactivate": Call("POST", f"{base}/pac-2/reactivate"),
        "delete": Call("DELETE", f"{base}/{scene.laura_id}"),
    }


SUCCESS = {
    "list": 200,
    "detail": 200,
    "create": 201,
    "update": 200,
    "deactivate": 200,
    "reactivate": 200,
    "delete": 204,
}
READS = ["list", "detail"]
WRITES = ["create", "update", "deactivate", "reactivate"]
ALL = list(SUCCESS)


def send(client: TestClient, call: Call, token: str | None) -> Any:
    headers = bearer(token) if token else {}
    return client.request(call.method, call.path, json=call.body, headers=headers)


@pytest.mark.parametrize("endpoint", ALL)
def test_admin_reaches_every_endpoint(
    auth_client: TestClient, patients_scene: PatientScene, endpoint: str
) -> None:
    response = send(auth_client, calls(patients_scene)[endpoint], login_token(auth_client, ADMIN))
    assert response.status_code == SUCCESS[endpoint], response.text


@pytest.mark.parametrize("endpoint", [*READS, *WRITES])
def test_reception_reads_and_writes_everything_but_delete(
    auth_client: TestClient, patients_scene: PatientScene, endpoint: str
) -> None:
    response = send(
        auth_client, calls(patients_scene)[endpoint], login_token(auth_client, RECEPTION)
    )
    assert response.status_code == SUCCESS[endpoint], response.text


def test_reception_cannot_delete_and_nothing_changes(
    auth_client: TestClient, patients_scene: PatientScene
) -> None:
    before = patients_scene.snapshot()
    response = send(
        auth_client, calls(patients_scene)["delete"], login_token(auth_client, RECEPTION)
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert patients_scene.snapshot() == before


@pytest.mark.parametrize("email", [DENTIST_A, NO_FILE])
@pytest.mark.parametrize("endpoint", READS)
def test_a_dentist_with_or_without_a_file_reads_patients(
    auth_client: TestClient, patients_scene: PatientScene, email: str, endpoint: str
) -> None:
    response = send(auth_client, calls(patients_scene)[endpoint], login_token(auth_client, email))
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("email", [DENTIST_A, NO_FILE])
@pytest.mark.parametrize("endpoint", [*WRITES, "delete"])
def test_a_dentist_cannot_write_and_nothing_changes(
    auth_client: TestClient, patients_scene: PatientScene, email: str, endpoint: str
) -> None:
    before = patients_scene.snapshot()
    response = send(auth_client, calls(patients_scene)[endpoint], login_token(auth_client, email))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert patients_scene.snapshot() == before


@pytest.mark.parametrize("endpoint", ALL)
def test_without_a_token_every_endpoint_is_401_and_nothing_changes(
    auth_client: TestClient, patients_scene: PatientScene, endpoint: str
) -> None:
    before = patients_scene.snapshot()
    response = send(auth_client, calls(patients_scene)[endpoint], None)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"
    assert response.headers["www-authenticate"] == "Bearer"
    assert patients_scene.snapshot() == before


@pytest.mark.parametrize(
    ("endpoint", "bad_body"),
    [("create", {}), ("update", {"email": None}), ("create", {"birth_date": 0})],
)
@pytest.mark.parametrize("email", [DENTIST_A, NO_FILE])
def test_403_comes_before_422_for_invalid_bodies(
    auth_client: TestClient,
    patients_scene: PatientScene,
    email: str,
    endpoint: str,
    bad_body: dict[str, Any],
) -> None:
    call = calls(patients_scene)[endpoint]
    bad = Call(call.method, call.path, bad_body)
    assert send(auth_client, bad, login_token(auth_client, email)).status_code == 403


@pytest.mark.parametrize("email", [ADMIN, RECEPTION])
@pytest.mark.parametrize("endpoint", ["detail", "update", "deactivate", "reactivate"])
def test_an_unknown_patient_is_404(
    auth_client: TestClient, patients_scene: PatientScene, email: str, endpoint: str
) -> None:
    call = calls(patients_scene)[endpoint]
    path = call.path.replace("pac-1", UNKNOWN).replace("pac-2", UNKNOWN)
    response = send(
        auth_client, Call(call.method, path, call.body), login_token(auth_client, email)
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PATIENT_NOT_FOUND"
