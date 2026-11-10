"""Permisos por rol de los cinco endpoints de tratamientos (spec treatment-api, regla dura 4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.unit.api.conftest import bearer, login_token
from tests.unit.application.agenda_helpers import CONSULTA_ID, PROF_A, PROF_B, World

ADMIN = "admin@example.com"
RECEPTION = "recepcion@example.com"
DENTIST_A = "dra.a@example.com"
NO_FILE = "sinficha@example.com"


@dataclass(frozen=True)
class Call:
    method: str
    path: str
    body: dict[str, Any] | None = None


def _calls(professional_id: str) -> dict[str, Call]:
    base = f"/api/v1/professionals/{professional_id}/treatments"
    return {
        "list": Call("GET", "/api/v1/treatments"),
        "create": Call("POST", "/api/v1/treatments", {"name": "Nuevo tratamiento"}),
        "update": Call("PATCH", f"/api/v1/treatments/{CONSULTA_ID}", {"active": False}),
        "assigned": Call("GET", base),
        "replace": Call("PUT", base, {"treatment_ids": [CONSULTA_ID]}),
    }


def send(client: TestClient, email: str, call: Call) -> int:
    response = client.request(
        call.method, call.path, json=call.body, headers=bearer(login_token(client, email))
    )
    return response.status_code


WRITES = ["create", "update", "replace"]
READS = ["list", "assigned"]


@pytest.mark.parametrize("name", WRITES)
@pytest.mark.parametrize("email", [RECEPTION, DENTIST_A])
def test_only_the_admin_writes(
    auth_client: TestClient, treatments_world: World, name: str, email: str
) -> None:
    before = (
        treatments_world.treatments.list_all(),
        treatments_world.treatments.offered_ids(PROF_A),
    )

    assert send(auth_client, email, _calls(PROF_A)[name]) == 403

    after = (
        treatments_world.treatments.list_all(),
        treatments_world.treatments.offered_ids(PROF_A),
    )
    assert after == before


@pytest.mark.parametrize("name", WRITES)
def test_the_role_is_checked_before_the_body_is_validated(
    auth_client: TestClient, treatments_world: World, name: str
) -> None:
    call = _calls(PROF_A)[name]
    broken = Call(call.method, call.path, {"cualquier": "cosa"})
    assert send(auth_client, RECEPTION, broken) == 403


@pytest.mark.parametrize("name", WRITES)
def test_the_admin_writes(auth_client: TestClient, treatments_world: World, name: str) -> None:
    assert send(auth_client, ADMIN, _calls(PROF_A)[name]) in (200, 201)


@pytest.mark.parametrize("name", READS)
@pytest.mark.parametrize("email", [ADMIN, RECEPTION])
def test_admin_and_reception_read(
    auth_client: TestClient, treatments_world: World, name: str, email: str
) -> None:
    assert send(auth_client, email, _calls(PROF_B)[name]) == 200


def test_a_dentist_reads_the_catalog_and_their_own_assignment(
    auth_client: TestClient, treatments_world: World
) -> None:
    assert send(auth_client, DENTIST_A, _calls(PROF_A)["list"]) == 200
    assert send(auth_client, DENTIST_A, _calls(PROF_A)["assigned"]) == 200


def test_a_dentist_cannot_read_another_professionals_assignment(
    auth_client: TestClient, treatments_world: World
) -> None:
    assert send(auth_client, DENTIST_A, _calls(PROF_B)["assigned"]) == 403


def test_a_dentist_without_a_file_cannot_read_any_assignment(
    auth_client: TestClient, treatments_world: World
) -> None:
    assert send(auth_client, NO_FILE, _calls(PROF_A)["assigned"]) == 403


@pytest.mark.parametrize("name", WRITES + READS)
def test_every_route_needs_a_session(
    auth_client: TestClient, treatments_world: World, name: str
) -> None:
    call = _calls(PROF_A)[name]
    response = auth_client.request(call.method, call.path, json=call.body)
    assert response.status_code == 401
