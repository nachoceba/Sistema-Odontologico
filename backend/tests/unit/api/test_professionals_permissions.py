"""Permisos por rol de los nueve endpoints de profesionales (spec professional-schedule-api)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.unit.api.conftest import ScheduleScene, bearer, login_token
from tests.unit.application.agenda_helpers import PROF_A, PROF_B

ADMIN = "admin@example.com"
RECEPTION = "recepcion@example.com"
DENTIST_A = "dra.a@example.com"
NO_FILE = "sinficha@example.com"
UNKNOWN = "99999999-9999-4999-8999-999999999999"

WEEK = {"blocks": [{"weekday": 0, "start_time": "09:00", "end_time": "13:00"}]}


@dataclass(frozen=True)
class Call:
    method: str
    path: str
    body: dict[str, Any] | None = None


def _calls(professional_id: str, time_off_id: str) -> dict[str, Call]:
    base = f"/api/v1/professionals/{professional_id}"
    return {
        "list": Call("GET", "/api/v1/professionals"),
        "detail": Call("GET", base),
        "update": Call("PATCH", base, {"display_name": "Nombre Nuevo", "license_number": "MN-77"}),
        "hours_read": Call("GET", f"{base}/working-hours"),
        "hours_replace": Call("PUT", f"{base}/working-hours", WEEK),
        "time_off_list": Call("GET", f"{base}/time-off"),
        "time_off_add": Call(
            "POST", f"{base}/time-off", {"starts_on": "2026-11-02", "ends_on": "2026-11-03"}
        ),
        "time_off_delete": Call("DELETE", f"{base}/time-off/{time_off_id}"),
        "conflicts": Call("GET", f"{base}/conflicts"),
    }


def own(scene: ScheduleScene) -> dict[str, Call]:
    return _calls(PROF_A, scene.time_off_a)


def foreign(scene: ScheduleScene) -> dict[str, Call]:
    return _calls(PROF_B, scene.time_off_b)


SUCCESS = {
    "list": 200,
    "detail": 200,
    "update": 200,
    "hours_read": 200,
    "hours_replace": 200,
    "time_off_list": 200,
    "time_off_add": 201,
    "time_off_delete": 204,
    "conflicts": 200,
}
WRITES = ["update", "hours_replace", "time_off_add", "time_off_delete"]
READS = ["detail", "hours_read", "time_off_list", "conflicts"]
ALL = list(SUCCESS)
Target = Callable[[ScheduleScene], dict[str, Call]]


def send(client: TestClient, call: Call, token: str | None) -> Any:
    headers = bearer(token) if token else {}
    return client.request(call.method, call.path, json=call.body, headers=headers)


@pytest.mark.parametrize("endpoint", ALL)
@pytest.mark.parametrize("target", [own, foreign], ids=["own", "foreign"])
def test_admin_reaches_every_endpoint_for_any_professional(
    auth_client: TestClient, schedule: ScheduleScene, endpoint: str, target: Target
) -> None:
    response = send(auth_client, target(schedule)[endpoint], login_token(auth_client, ADMIN))
    assert response.status_code == SUCCESS[endpoint], response.text


@pytest.mark.parametrize("endpoint", ["list", *READS])
@pytest.mark.parametrize("target", [own, foreign], ids=["own", "foreign"])
def test_reception_reads_any_professional(
    auth_client: TestClient, schedule: ScheduleScene, endpoint: str, target: Target
) -> None:
    response = send(auth_client, target(schedule)[endpoint], login_token(auth_client, RECEPTION))
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("endpoint", ["list", *READS])
def test_a_dentist_reads_their_own_professional(
    auth_client: TestClient, schedule: ScheduleScene, endpoint: str
) -> None:
    response = send(auth_client, own(schedule)[endpoint], login_token(auth_client, DENTIST_A))
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("endpoint", READS)
def test_a_dentist_cannot_read_a_foreign_professional(
    auth_client: TestClient, schedule: ScheduleScene, endpoint: str
) -> None:
    response = send(auth_client, foreign(schedule)[endpoint], login_token(auth_client, DENTIST_A))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize("endpoint", READS)
def test_a_dentist_cannot_read_with_a_malformed_id(
    auth_client: TestClient, schedule: ScheduleScene, endpoint: str
) -> None:
    call = own(schedule)[endpoint]
    malformed = Call(call.method, call.path.replace(PROF_A, "no-es-un-uuid"), call.body)
    assert send(auth_client, malformed, login_token(auth_client, DENTIST_A)).status_code == 403


@pytest.mark.parametrize("endpoint", READS)
def test_a_dentist_without_a_file_cannot_read_anyone(
    auth_client: TestClient, schedule: ScheduleScene, endpoint: str
) -> None:
    response = send(auth_client, own(schedule)[endpoint], login_token(auth_client, NO_FILE))
    assert response.status_code == 403


def test_a_dentist_without_a_file_gets_an_empty_list(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    response = send(auth_client, own(schedule)["list"], login_token(auth_client, NO_FILE))
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("email", [RECEPTION, DENTIST_A, NO_FILE])
@pytest.mark.parametrize("endpoint", WRITES)
@pytest.mark.parametrize("target", [own, foreign], ids=["own", "foreign"])
def test_only_the_admin_writes_and_nothing_changes_otherwise(
    auth_client: TestClient, schedule: ScheduleScene, email: str, endpoint: str, target: Target
) -> None:
    before = schedule.snapshot()
    response = send(auth_client, target(schedule)[endpoint], login_token(auth_client, email))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert schedule.snapshot() == before


@pytest.mark.parametrize("endpoint", ALL)
def test_without_a_token_every_endpoint_is_401_and_nothing_changes(
    auth_client: TestClient, schedule: ScheduleScene, endpoint: str
) -> None:
    before = schedule.snapshot()
    response = send(auth_client, own(schedule)[endpoint], None)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"
    assert response.headers["www-authenticate"] == "Bearer"
    assert schedule.snapshot() == before


@pytest.mark.parametrize(
    ("endpoint", "bad_body"),
    [
        ("update", {"display_name": "   "}),
        ("hours_replace", {"blocks": "no es una lista"}),
        ("time_off_add", {"starts_on": "ayer"}),
    ],
)
@pytest.mark.parametrize("email", [RECEPTION, DENTIST_A])
def test_403_comes_before_422_for_invalid_bodies(
    auth_client: TestClient,
    schedule: ScheduleScene,
    email: str,
    endpoint: str,
    bad_body: dict[str, Any],
) -> None:
    call = own(schedule)[endpoint]
    bad = Call(call.method, call.path, bad_body)
    assert send(auth_client, bad, login_token(auth_client, email)).status_code == 403


@pytest.mark.parametrize("email", [ADMIN, RECEPTION])
@pytest.mark.parametrize("endpoint", READS)
def test_an_unknown_professional_is_404_for_admin_and_reception(
    auth_client: TestClient, schedule: ScheduleScene, email: str, endpoint: str
) -> None:
    call = own(schedule)[endpoint]
    unknown = Call(call.method, call.path.replace(PROF_A, UNKNOWN), call.body)
    response = send(auth_client, unknown, login_token(auth_client, email))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROFESSIONAL_NOT_FOUND"
