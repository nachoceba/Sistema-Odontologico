"""Endpoints de turnos: contrato HTTP, fechas, validacion y rechazos (spec appointment-api)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.unit.api.conftest import AgendaScene, bearer, login_token
from tests.unit.application.agenda_helpers import PROF_A
from tests.unit.domain.appointments.helpers import monday

BASE = "/api/v1/appointments"


@pytest.fixture
def reception(auth_client: TestClient) -> dict[str, str]:
    return bearer(login_token(auth_client, "recepcion@example.com"))


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _book_body(starts_at: str, patient_id: str = "pac-1") -> dict[str, str]:
    return {"patient_id": patient_id, "professional_id": PROF_A, "starts_at": starts_at}


# --- Endpoints ---------------------------------------------------------------------------------


def test_booking_returns_201_with_the_created_appointment_in_utc(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    response = auth_client.post(BASE, json=_book_body(monday(16).isoformat()), headers=reception)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["patient_id"] == "pac-1"
    assert body["professional_id"] == PROF_A
    assert body["cancel_reason"] is None
    assert body["created_by"] == "u-rec"
    assert _parse(body["starts_at"]) == monday(16)
    assert _parse(body["ends_at"]) == monday(16, 30)
    assert _parse(body["starts_at"]).utcoffset() == timedelta(0)
    assert set(body) == {
        "id",
        "patient_id",
        "professional_id",
        "starts_at",
        "ends_at",
        "status",
        "cancel_reason",
        "created_by",
    }
    stored = agenda.world.appointments.get(body["id"])
    assert stored is not None
    assert stored.starts_at == monday(16)


def test_an_input_with_another_zone_is_stored_and_returned_as_utc(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    # 22:00+03:00 = 19:00 UTC = 16:00 hora del consultorio (UTC-3)
    response = auth_client.post(
        BASE, json=_book_body("2026-10-05T22:00:00+03:00"), headers=reception
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert _parse(body["starts_at"]) == datetime(2026, 10, 5, 19, 0, tzinfo=UTC)
    assert _parse(body["starts_at"]).utcoffset() == timedelta(0)
    stored = agenda.world.appointments.get(body["id"])
    assert stored is not None
    assert stored.starts_at.utcoffset() == timedelta(0)


def test_detail_cancel_reschedule_and_attendance_flow(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    detail = auth_client.get(f"{BASE}/{agenda.future_a}", headers=reception)
    assert detail.status_code == 200
    assert detail.json()["id"] == agenda.future_a

    moved = auth_client.post(
        f"{BASE}/{agenda.future_a}/reschedule",
        json={"starts_at": monday(17).isoformat()},
        headers=reception,
    )
    assert moved.status_code == 200
    assert _parse(moved.json()["starts_at"]) == monday(17)

    cancelled = auth_client.post(
        f"{BASE}/{agenda.future_a}/cancel",
        json={"reason": "  Aviso por teléfono  "},
        headers=reception,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancel_reason"] == "Aviso por teléfono"

    marked = auth_client.post(
        f"{BASE}/{agenda.started_a}/attendance", json={"status": "no_show"}, headers=reception
    )
    assert marked.status_code == 200
    assert marked.json()["status"] == "no_show"


def test_listing_returns_every_status_ordered_by_start(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    auth_client.post(f"{BASE}/{agenda.future_a}/cancel", json={"reason": "x"}, headers=reception)

    response = auth_client.get(
        BASE,
        params={
            "professional_id": PROF_A,
            "from": monday(0).isoformat(),
            "to": (monday(0) + timedelta(days=1)).isoformat(),
        },
        headers=reception,
    )

    assert response.status_code == 200
    rows = response.json()
    assert [r["id"] for r in rows] == [agenda.started_a, agenda.future_a]
    assert [r["status"] for r in rows] == ["scheduled", "cancelled"]


def test_slots_endpoint_returns_free_busy_and_outside_hours(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    response = auth_client.get(
        f"/api/v1/professionals/{PROF_A}/slots", params={"date": "2026-10-05"}, headers=reception
    )

    assert response.status_code == 200
    by_start = {_parse(s["starts_at"]): s for s in response.json()}
    assert by_start[monday(10)]["status"] == "BUSY"
    assert by_start[monday(9)]["status"] == "FREE"
    assert by_start[monday(13)]["status"] == "OUTSIDE_HOURS"
    assert _parse(by_start[monday(9)]["ends_at"]) == monday(9, 30)


def test_delete_does_not_exist(auth_client: TestClient, agenda: AgendaScene) -> None:
    admin = bearer(login_token(auth_client, "admin@example.com"))
    before = agenda.snapshot()

    response = auth_client.delete(f"{BASE}/{agenda.future_a}", headers=admin)

    assert response.status_code == 405
    assert agenda.snapshot() == before


def test_an_unknown_appointment_is_404(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    response = auth_client.get(f"{BASE}/no-existe", headers=reception)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "APPOINTMENT_NOT_FOUND"


# --- Fechas y validacion -----------------------------------------------------------------------


def test_a_start_without_a_zone_is_422_and_writes_nothing(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    before = agenda.snapshot()

    response = auth_client.post(BASE, json=_book_body("2026-10-05T16:00:00"), headers=reception)

    assert response.status_code == 422
    assert agenda.snapshot() == before


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"patient_id": "", "professional_id": PROF_A, "starts_at": "2026-10-05T19:00:00Z"},
        {"patient_id": "pac-1", "professional_id": "  ", "starts_at": "2026-10-05T19:00:00Z"},
        {"patient_id": "pac-1", "professional_id": PROF_A, "starts_at": "no-es-una-fecha"},
        {"patient_id": "pac-1", "professional_id": PROF_A},
    ],
    ids=["empty", "blank-patient", "blank-professional", "bad-date", "missing-start"],
)
def test_invalid_booking_bodies_are_422(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str], body: dict[str, Any]
) -> None:
    before = agenda.snapshot()
    response = auth_client.post(BASE, json=body, headers=reception)
    assert response.status_code == 422
    assert agenda.snapshot() == before


@pytest.mark.parametrize("reason", ["   ", "", "x" * 501])
def test_an_invalid_cancel_reason_is_422_without_echo_and_keeps_the_appointment(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str], reason: str
) -> None:
    before = agenda.snapshot()

    response = auth_client.post(
        f"{BASE}/{agenda.future_a}/cancel", json={"reason": reason}, headers=reception
    )

    assert response.status_code == 422
    assert "input" not in response.text
    if reason.strip():
        assert reason not in response.text
    assert agenda.snapshot() == before


def test_a_cancel_reason_of_500_characters_is_accepted(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    response = auth_client.post(
        f"{BASE}/{agenda.future_a}/cancel", json={"reason": "x" * 500}, headers=reception
    )
    assert response.status_code == 200


def test_an_invalid_attendance_status_is_422(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    for status in ("scheduled", "cancelled", "otro"):
        response = auth_client.post(
            f"{BASE}/{agenda.started_a}/attendance", json={"status": status}, headers=reception
        )
        assert response.status_code == 422


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (monday(0), monday(0) + timedelta(days=32)),
        (monday(10), monday(10)),
        (monday(12), monday(10)),
    ],
    ids=["32-days", "empty", "inverted"],
)
def test_an_invalid_listing_range_is_422(
    auth_client: TestClient,
    agenda: AgendaScene,
    reception: dict[str, str],
    start: datetime,
    end: datetime,
) -> None:
    response = auth_client.get(
        BASE,
        params={"professional_id": PROF_A, "from": start.isoformat(), "to": end.isoformat()},
        headers=reception,
    )
    assert response.status_code == 422


def test_a_listing_range_of_exactly_31_days_is_accepted(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    response = auth_client.get(
        BASE,
        params={
            "professional_id": PROF_A,
            "from": monday(0).isoformat(),
            "to": (monday(0) + timedelta(days=31)).isoformat(),
        },
        headers=reception,
    )
    assert response.status_code == 200


def test_listing_requires_all_three_parameters_and_zoned_instants(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    missing = auth_client.get(BASE, params={"professional_id": PROF_A}, headers=reception)
    naive = auth_client.get(
        BASE,
        params={
            "professional_id": PROF_A,
            "from": "2026-10-05T00:00:00",
            "to": "2026-10-06T00:00:00",
        },
        headers=reception,
    )
    assert missing.status_code == 422
    assert naive.status_code == 422


@pytest.mark.parametrize("value", ["2026-13-45", "ayer", ""])
def test_an_invalid_slots_date_is_422(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str], value: str
) -> None:
    response = auth_client.get(
        f"/api/v1/professionals/{PROF_A}/slots", params={"date": value}, headers=reception
    )
    assert response.status_code == 422


# --- Rechazos de negocio -----------------------------------------------------------------


def test_a_taken_slot_is_409_slot_taken(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    before = agenda.snapshot()

    response = auth_client.post(
        BASE, json=_book_body(monday(15).isoformat(), "pac-1"), headers=reception
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SLOT_TAKEN"
    assert response.json()["error"]["message"] == "Ese horario acaba de ocuparse. Elegí otro."
    assert agenda.snapshot() == before


def test_outside_working_hours_is_400(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    response = auth_client.post(
        BASE, json=_book_body(monday(13, 30).isoformat()), headers=reception
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "OUTSIDE_WORKING_HOURS"


def test_double_booking_is_409_and_reveals_nothing_about_the_other_appointment(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    # pac-2 ya tiene el turno de las 15:00 con la Dra. A; se lo pide con la misma hora y el Dr. B
    body = {
        "patient_id": "pac-2",
        "professional_id": "22222222-2222-4222-8222-222222222222",
        "starts_at": monday(15).isoformat(),
    }
    agenda.world.working_hours.replace_for_professional(
        body["professional_id"], agenda.world.working_hours.list_for_professional(PROF_A)
    )

    response = auth_client.post(BASE, json=body, headers=reception)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PATIENT_DOUBLE_BOOKED"
    for leaked in ("Gómez", "Pérez", PROF_A, agenda.future_a, "15:00"):
        assert leaked not in response.text


def test_unknown_patient_and_professional_are_404(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    patient = auth_client.post(
        BASE, json=_book_body(monday(16).isoformat(), "no-existe"), headers=reception
    )
    professional = auth_client.post(
        BASE,
        json={
            "patient_id": "pac-1",
            "professional_id": "99999999-9999-4999-8999-999999999999",
            "starts_at": monday(16).isoformat(),
        },
        headers=reception,
    )
    assert patient.status_code == 404
    assert patient.json()["error"]["code"] == "PATIENT_NOT_FOUND"
    assert professional.status_code == 404
    assert professional.json()["error"]["code"] == "PROFESSIONAL_NOT_FOUND"


def test_cancelling_an_appointment_that_already_started_is_409(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    response = auth_client.post(
        f"{BASE}/{agenda.started_a}/cancel", json={"reason": "x"}, headers=reception
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ALREADY_STARTED"


def test_marking_attendance_before_the_start_is_409(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    response = auth_client.post(
        f"{BASE}/{agenda.future_a}/attendance", json={"status": "completed"}, headers=reception
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NOT_STARTED_YET"


def test_acting_on_a_cancelled_appointment_is_409(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    auth_client.post(f"{BASE}/{agenda.future_a}/cancel", json={"reason": "x"}, headers=reception)

    again = auth_client.post(
        f"{BASE}/{agenda.future_a}/cancel", json={"reason": "otra vez"}, headers=reception
    )
    moved = auth_client.post(
        f"{BASE}/{agenda.future_a}/reschedule",
        json={"starts_at": monday(17).isoformat()},
        headers=reception,
    )

    assert (again.status_code, again.json()["error"]["code"]) == (409, "CANCELLED_IS_FINAL")
    assert (moved.status_code, moved.json()["error"]["code"]) == (409, "CANCELLED_IS_FINAL")


def test_rescheduling_to_the_same_time_is_400(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    response = auth_client.post(
        f"{BASE}/{agenda.future_a}/reschedule",
        json={"starts_at": monday(15).isoformat()},
        headers=reception,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "RESCHEDULE_SAME_TIME"


def test_a_failing_dispatcher_still_answers_201_and_keeps_appointment_and_notification(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    agenda.world.dispatcher.error = RuntimeError("fallo del servicio de colas")

    response = auth_client.post(BASE, json=_book_body(monday(16).isoformat()), headers=reception)

    assert response.status_code == 201, response.text
    created = response.json()["id"]
    assert agenda.world.appointments.get(created) is not None
    rows = agenda.world.notifications.list_for_appointment(created)
    assert [(r.kind.value, r.status.value) for r in rows] == [("confirmation", "pending")]
