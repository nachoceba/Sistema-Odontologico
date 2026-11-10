"""Endpoints de turnos: contrato HTTP, fechas, validacion y rechazos (spec appointment-api)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domain.patients.types import PatientChanges
from tests.unit.api.conftest import AgendaScene, bearer, login_token
from tests.unit.application.agenda_helpers import CONSULTA_ID, LIMPIEZA_ID, PROF_A
from tests.unit.domain.appointments.helpers import monday

BASE = "/api/v1/appointments"


@pytest.fixture
def reception(auth_client: TestClient) -> dict[str, str]:
    return bearer(login_token(auth_client, "recepcion@example.com"))


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _book_body(starts_at: str, patient_id: str = "pac-1") -> dict[str, str]:
    return {
        "patient_id": patient_id,
        "professional_id": PROF_A,
        "treatment_id": CONSULTA_ID,
        "starts_at": starts_at,
    }


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
        "origin",
        "pending_until",
        "treatment_id",
    }
    assert body["treatment_id"] == CONSULTA_ID
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
        {**_book_body("2026-10-05T19:00:00Z"), "patient_id": ""},
        {**_book_body("2026-10-05T19:00:00Z"), "professional_id": "  "},
        _book_body("no-es-una-fecha"),
        {"patient_id": "pac-1", "professional_id": PROF_A, "treatment_id": CONSULTA_ID},
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
        "treatment_id": CONSULTA_ID,
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
            "treatment_id": CONSULTA_ID,
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


# --- Nombre del paciente en listado y detalle (C-09, DD-79) -------------------------------------

NAME_KEYS = {
    "id",
    "treatment_id",
    "treatment_name",
    "patient_id",
    "patient_first_name",
    "patient_last_name",
    "professional_id",
    "starts_at",
    "ends_at",
    "status",
    "cancel_reason",
    "created_by",
    "origin",
    "pending_until",
}
DAY = {
    "professional_id": PROF_A,
    "from": monday(0).isoformat(),
    "to": (monday(0) + timedelta(days=1)).isoformat(),
}


def test_listing_carries_first_and_last_name_and_no_other_patient_data(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    response = auth_client.get(BASE, params=DAY, headers=reception)

    assert response.status_code == 200
    rows = response.json()
    assert [(r["patient_first_name"], r["patient_last_name"]) for r in rows] == [
        ("Juan", "Pérez"),
        ("Ana", "Gómez"),
    ]
    assert all(set(r) == NAME_KEYS for r in rows)
    for leaked in ("juan@example.com", "ana@example.com", "phone", "document_number", "birth_date"):
        assert leaked not in response.text


def test_detail_carries_the_current_name_after_the_patient_is_edited(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    agenda.world.patients.update("pac-2", PatientChanges(first_name="Anita"))

    response = auth_client.get(f"{BASE}/{agenda.future_a}", headers=reception)

    body = response.json()
    assert set(body) == NAME_KEYS
    assert (body["patient_first_name"], body["patient_last_name"]) == ("Anita", "Gómez")
    assert "email" not in body


def test_booking_cancelling_and_rescheduling_keep_their_response_shape(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    booked = auth_client.post(BASE, json=_book_body(monday(16).isoformat()), headers=reception)
    moved = auth_client.post(
        f"{BASE}/{agenda.future_a}/reschedule",
        json={"starts_at": monday(17).isoformat()},
        headers=reception,
    )
    cancelled = auth_client.post(
        f"{BASE}/{agenda.future_a}/cancel", json={"reason": "x"}, headers=reception
    )
    marked = auth_client.post(
        f"{BASE}/{agenda.started_a}/attendance", json={"status": "completed"}, headers=reception
    )

    for response in (booked, moved, cancelled, marked):
        assert response.status_code in (200, 201), response.text
        assert "patient_first_name" not in response.json()
        assert "patient_last_name" not in response.json()


def test_consulting_the_agenda_changes_nothing(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    before = agenda.snapshot()
    notifications = agenda.world.notifications.__dict__.copy()

    auth_client.get(BASE, params=DAY, headers=reception)
    auth_client.get(f"{BASE}/{agenda.future_a}", headers=reception)

    assert agenda.snapshot() == before
    assert agenda.world.notifications.__dict__ == notifications


# --- Origen y turnos pendientes de la reserva online (C-15, spec appointment-api) ---------------

ONLINE_DOC = "40999888"


def _online_pending(agenda: AgendaScene) -> str:
    from tests.unit.api.test_public_booking import booking

    deps = agenda.world.public_deps()
    from app.application.public_booking import book_online

    book_online(
        deps,
        professional_id=PROF_A,
        treatment_id=CONSULTA_ID,
        starts_at=monday(16),
        document_number=booking()["document_number"],
        first_name="Lucía",
        last_name="Díaz",
        email="lucia@example.com",
        phone=None,
    )
    return next(a.id for a in agenda.world.everything() if a.created_by is None)


def test_a_staff_appointment_says_origin_staff_and_has_no_pending_until(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    response = auth_client.get(f"{BASE}/{agenda.future_a}", headers=reception)

    body = response.json()
    assert body["origin"] == "staff"
    assert body["created_by"] == "u-rec"
    assert body["pending_until"] is None


def test_a_pending_online_appointment_has_origin_online_and_its_deadline(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    pending_id = _online_pending(agenda)

    body = auth_client.get(f"{BASE}/{pending_id}", headers=reception).json()

    assert body["origin"] == "online"
    assert body["created_by"] is None
    assert _parse(body["pending_until"]) == agenda.world.now + timedelta(hours=1)
    assert _parse(body["pending_until"]).utcoffset() == timedelta(0)
    assert body["patient_first_name"] == "Lucía"


def test_a_confirmed_online_appointment_keeps_origin_online_without_deadline(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    from app.application.public_booking import confirm_online_booking

    pending_id = _online_pending(agenda)
    confirm_online_booking(agenda.world.public_deps(), "tok-1")

    body = auth_client.get(f"{BASE}/{pending_id}", headers=reception).json()

    assert (body["origin"], body["created_by"], body["pending_until"]) == ("online", None, None)


def test_the_listing_carries_origin_and_pending_until_for_every_row(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    _online_pending(agenda)

    rows = auth_client.get(BASE, params=DAY, headers=reception).json()

    assert {r["origin"] for r in rows} == {"staff", "online"}
    assert all("pending_until" in r for r in rows)
    assert [r["origin"] for r in rows if r["pending_until"] is not None] == ["online"]


def test_rescheduling_a_pending_appointment_is_409_pending_confirmation(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    pending_id = _online_pending(agenda)

    response = auth_client.post(
        f"{BASE}/{pending_id}/reschedule",
        json={"starts_at": monday(17).isoformat()},
        headers=reception,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PENDING_CONFIRMATION"


def test_receptionist_can_still_cancel_a_pending_appointment(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    pending_id = _online_pending(agenda)

    response = auth_client.post(
        f"{BASE}/{pending_id}/cancel", json={"reason": "Paciente no confirmó"}, headers=reception
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["pending_until"] is None


# --- Tratamiento (C-17) ---------------------------------------------------------------------------


def _without(body: dict[str, str], key: str) -> dict[str, str]:
    return {k: v for k, v in body.items() if k != key}


def test_booking_without_a_treatment_is_422_and_writes_nothing(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    before = agenda.snapshot()

    response = auth_client.post(
        BASE, json=_without(_book_body(monday(16).isoformat()), "treatment_id"), headers=reception
    )

    assert response.status_code == 422
    assert agenda.snapshot() == before


def test_booking_with_a_blank_or_non_text_treatment_is_422(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    before = agenda.snapshot()
    for value in ("", "   ", 5, None):
        body: dict[str, Any] = {**_book_body(monday(16).isoformat()), "treatment_id": value}
        response = auth_client.post(BASE, json=body, headers=reception)
        assert response.status_code == 422, value
    assert agenda.snapshot() == before


def test_booking_with_the_treatment_returns_it_and_saves_it(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    body = {**_book_body(monday(16).isoformat()), "treatment_id": LIMPIEZA_ID}

    response = auth_client.post(BASE, json=body, headers=reception)

    assert response.status_code == 201, response.text
    assert response.json()["treatment_id"] == LIMPIEZA_ID
    stored = agenda.world.appointments.get(response.json()["id"])
    assert stored is not None and stored.treatment_id == LIMPIEZA_ID


def test_listing_and_detail_carry_the_treatment_name_and_old_rows_have_none(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    body = {**_book_body(monday(16).isoformat()), "treatment_id": LIMPIEZA_ID}
    created = auth_client.post(BASE, json=body, headers=reception).json()

    listing = auth_client.get(
        BASE,
        params={
            "professional_id": PROF_A,
            "from": monday(0).isoformat(),
            "to": (monday(0) + timedelta(days=1)).isoformat(),
        },
        headers=reception,
    )
    detail = auth_client.get(f"{BASE}/{created['id']}", headers=reception)
    old = auth_client.get(f"{BASE}/{agenda.future_a}", headers=reception)

    names = {r["id"]: r["treatment_name"] for r in listing.json()}
    assert names[created["id"]] == "Limpieza dental"
    assert names[agenda.future_a] is None
    assert detail.json()["treatment_name"] == "Limpieza dental"
    assert detail.json()["treatment_id"] == LIMPIEZA_ID
    assert old.json()["treatment_name"] is None


def test_an_inactive_treatment_is_409_not_available_and_writes_nothing(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    agenda.world.treatments.update(LIMPIEZA_ID, active=False)
    before = agenda.snapshot()
    body = {**_book_body(monday(16).isoformat()), "treatment_id": LIMPIEZA_ID}

    response = auth_client.post(BASE, json=body, headers=reception)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TREATMENT_NOT_AVAILABLE"
    assert agenda.snapshot() == before


def test_a_treatment_the_professional_does_not_offer_is_409_not_available(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    agenda.world.treatments.replace_for_professional(PROF_A, [CONSULTA_ID])
    body = {**_book_body(monday(16).isoformat()), "treatment_id": LIMPIEZA_ID}

    response = auth_client.post(BASE, json=body, headers=reception)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TREATMENT_NOT_AVAILABLE"


def test_an_unknown_treatment_is_404_not_found(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    before = agenda.snapshot()
    body = {**_book_body(monday(16).isoformat()), "treatment_id": "no-existe"}

    response = auth_client.post(BASE, json=body, headers=reception)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TREATMENT_NOT_FOUND"
    assert agenda.snapshot() == before


def test_rescheduling_ignores_a_treatment_in_the_body_and_keeps_the_original(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str]
) -> None:
    created = auth_client.post(
        BASE,
        json={**_book_body(monday(16).isoformat()), "treatment_id": LIMPIEZA_ID},
        headers=reception,
    ).json()

    response = auth_client.post(
        f"{BASE}/{created['id']}/reschedule",
        json={"starts_at": monday(17).isoformat(), "treatment_id": CONSULTA_ID},
        headers=reception,
    )

    assert response.status_code == 200, response.text
    assert response.json()["treatment_id"] == LIMPIEZA_ID
