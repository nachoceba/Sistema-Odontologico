"""Permisos por rol de cada endpoint de turnos (spec appointment-api, regla dura 4)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.unit.api.conftest import AgendaScene, bearer, login_token
from tests.unit.application.agenda_helpers import CONSULTA_ID, PROF_A, PROF_B
from tests.unit.domain.appointments.helpers import monday

ADMIN = "admin@example.com"
RECEPTION = "recepcion@example.com"
DENTIST_A = "dra.a@example.com"
NO_FILE = "sinficha@example.com"


@dataclass(frozen=True)
class Call:
    method: str
    path: str
    body: dict[str, Any] | None = None
    params: dict[str, str] | None = None


def _book(professional_id: str, hour: int, minute: int) -> Callable[[AgendaScene], Call]:
    return lambda s: Call(
        "POST",
        "/api/v1/appointments",
        {
            "patient_id": "pac-2",
            "professional_id": professional_id,
            "treatment_id": CONSULTA_ID,
            "starts_at": monday(hour, minute).isoformat(),
        },
    )


def _listing(professional_id: str) -> Callable[[AgendaScene], Call]:
    return lambda s: Call(
        "GET",
        "/api/v1/appointments",
        params={
            "professional_id": professional_id,
            "from": monday(0).isoformat(),
            "to": monday(23).isoformat(),
        },
    )


# Endpoint -> como se llama sobre un recurso de la Dra. A (propio) o del Dr. B (ajeno).
OWN: dict[str, Callable[[AgendaScene], Call]] = {
    "book": _book(PROF_A, 17, 30),
    "detail": lambda s: Call("GET", f"/api/v1/appointments/{s.future_a}"),
    "list": _listing(PROF_A),
    "cancel": lambda s: Call(
        "POST", f"/api/v1/appointments/{s.future_a}/cancel", {"reason": "Aviso del paciente"}
    ),
    "reschedule": lambda s: Call(
        "POST",
        f"/api/v1/appointments/{s.future_a}/reschedule",
        {"starts_at": monday(17).isoformat()},
    ),
    "attendance": lambda s: Call(
        "POST", f"/api/v1/appointments/{s.started_a}/attendance", {"status": "completed"}
    ),
    "slots": lambda s: Call(
        "GET", f"/api/v1/professionals/{PROF_A}/slots", params={"date": "2026-10-05"}
    ),
}
FOREIGN: dict[str, Callable[[AgendaScene], Call]] = {
    "book": _book(PROF_B, 12, 30),
    "detail": lambda s: Call("GET", f"/api/v1/appointments/{s.future_b}"),
    "list": _listing(PROF_B),
    "cancel": lambda s: Call(
        "POST", f"/api/v1/appointments/{s.future_b}/cancel", {"reason": "Aviso del paciente"}
    ),
    "reschedule": lambda s: Call(
        "POST",
        f"/api/v1/appointments/{s.future_b}/reschedule",
        {"starts_at": monday(11).isoformat()},
    ),
    "attendance": lambda s: Call(
        "POST", f"/api/v1/appointments/{s.started_b}/attendance", {"status": "completed"}
    ),
    "slots": lambda s: Call(
        "GET", f"/api/v1/professionals/{PROF_B}/slots", params={"date": "2026-10-05"}
    ),
}
SUCCESS = {
    "book": 201,
    "detail": 200,
    "list": 200,
    "cancel": 200,
    "reschedule": 200,
    "attendance": 200,
    "slots": 200,
}
WRITES = ["book", "cancel", "reschedule"]
READS_AND_ATTENDANCE = ["detail", "list", "attendance", "slots"]
ALL = list(SUCCESS)


def send(client: TestClient, call: Call, token: str | None) -> Any:
    headers = bearer(token) if token else {}
    return client.request(
        call.method, call.path, json=call.body, params=call.params, headers=headers
    )


@pytest.mark.parametrize("email", [ADMIN, RECEPTION])
@pytest.mark.parametrize("endpoint", ALL)
@pytest.mark.parametrize("target", [OWN, FOREIGN], ids=["own", "foreign"])
def test_admin_and_reception_reach_every_endpoint_for_any_professional(
    auth_client: TestClient,
    agenda: AgendaScene,
    email: str,
    endpoint: str,
    target: dict[str, Callable[[AgendaScene], Call]],
) -> None:
    token = login_token(auth_client, email)
    response = send(auth_client, target[endpoint](agenda), token)
    assert response.status_code == SUCCESS[endpoint], response.text


@pytest.mark.parametrize("endpoint", READS_AND_ATTENDANCE)
def test_a_dentist_reaches_reads_and_attendance_of_their_own_professional(
    auth_client: TestClient, agenda: AgendaScene, endpoint: str
) -> None:
    token = login_token(auth_client, DENTIST_A)
    response = send(auth_client, OWN[endpoint](agenda), token)
    assert response.status_code == SUCCESS[endpoint], response.text


@pytest.mark.parametrize("endpoint", WRITES)
@pytest.mark.parametrize("target", [OWN, FOREIGN], ids=["own", "foreign"])
def test_a_dentist_cannot_book_cancel_or_reschedule(
    auth_client: TestClient,
    agenda: AgendaScene,
    endpoint: str,
    target: dict[str, Callable[[AgendaScene], Call]],
) -> None:
    token = login_token(auth_client, DENTIST_A)
    before = agenda.snapshot()

    response = send(auth_client, target[endpoint](agenda), token)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert agenda.snapshot() == before


@pytest.mark.parametrize("endpoint", READS_AND_ATTENDANCE)
def test_a_dentist_cannot_touch_another_professionals_data(
    auth_client: TestClient, agenda: AgendaScene, endpoint: str
) -> None:
    token = login_token(auth_client, DENTIST_A)
    before = agenda.snapshot()

    response = send(auth_client, FOREIGN[endpoint](agenda), token)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert "pac-" not in response.text  # ningun dato del turno ajeno
    assert agenda.snapshot() == before


@pytest.mark.parametrize("endpoint", ALL)
def test_a_dentist_without_a_file_gets_403_everywhere(
    auth_client: TestClient, agenda: AgendaScene, endpoint: str
) -> None:
    token = login_token(auth_client, NO_FILE)
    before = agenda.snapshot()

    response = send(auth_client, OWN[endpoint](agenda), token)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert agenda.snapshot() == before


@pytest.mark.parametrize("endpoint", ALL)
@pytest.mark.parametrize("target", [OWN, FOREIGN], ids=["own", "foreign"])
def test_without_a_token_every_endpoint_answers_401_before_any_role_check(
    auth_client: TestClient,
    agenda: AgendaScene,
    endpoint: str,
    target: dict[str, Callable[[AgendaScene], Call]],
) -> None:
    before = agenda.snapshot()

    response = send(auth_client, target[endpoint](agenda), None)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"
    assert agenda.snapshot() == before


# --- Los dos endpoints con nombre del paciente, por rol (C-09, DD-79) -----------------------------

NAMED = ["detail", "list"]


@pytest.mark.parametrize("email", [ADMIN, RECEPTION, DENTIST_A])
@pytest.mark.parametrize("endpoint", NAMED)
def test_allowed_roles_see_the_patient_name_on_their_own_agenda(
    auth_client: TestClient, agenda: AgendaScene, email: str, endpoint: str
) -> None:
    response = send(auth_client, OWN[endpoint](agenda), login_token(auth_client, email))

    assert response.status_code == 200
    body = response.json()
    rows = body if isinstance(body, list) else [body]
    assert rows
    assert all(r["patient_first_name"] and r["patient_last_name"] for r in rows)


@pytest.mark.parametrize("email", [ADMIN, RECEPTION])
@pytest.mark.parametrize("endpoint", NAMED)
def test_staff_sees_the_name_on_another_professionals_agenda(
    auth_client: TestClient, agenda: AgendaScene, email: str, endpoint: str
) -> None:
    response = send(auth_client, FOREIGN[endpoint](agenda), login_token(auth_client, email))

    assert response.status_code == 200
    assert "patient_first_name" in response.text


@pytest.mark.parametrize("email", [DENTIST_A, NO_FILE])
@pytest.mark.parametrize("endpoint", NAMED)
def test_a_forbidden_dentist_gets_no_names_in_the_body(
    auth_client: TestClient, agenda: AgendaScene, email: str, endpoint: str
) -> None:
    response = send(auth_client, FOREIGN[endpoint](agenda), login_token(auth_client, email))

    assert response.status_code == 403
    for name in ("Juan", "Pérez", "Ana", "Gómez", "patient_first_name"):
        assert name not in response.text


@pytest.mark.parametrize("endpoint", NAMED)
def test_without_a_token_the_named_endpoints_answer_401_with_no_names(
    auth_client: TestClient, agenda: AgendaScene, endpoint: str
) -> None:
    response = send(auth_client, OWN[endpoint](agenda), None)

    assert response.status_code == 401
    assert "patient_first_name" not in response.text
