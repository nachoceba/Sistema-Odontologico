"""API publica de reserva online contra PostgreSQL con los datos del seed (spec public-booking-api,
C-15). Reloj fijo (viernes 6 de noviembre de 2026) y limite de pedidos en memoria; el aviso por
email se anota sin salir a Redis.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import (
    get_agenda_deps,
    get_public_booking_deps,
    get_rate_limiter,
    get_user_repository,
)
from app.application.appointments import AgendaDeps
from app.application.public_booking import PublicBookingDeps
from app.core.config import get_settings
from app.core.security import hash_confirmation_token
from app.infrastructure.db.repositories import (
    SqlAlchemyAgendaUnitOfWork,
    SqlAlchemyAppointmentRepository,
    SqlAlchemyClinicSettingsRepository,
    SqlAlchemyPatientRepository,
    SqlAlchemyProfessionalRepository,
    SqlAlchemyTimeOffRepository,
    SqlAlchemyUserAccountRepository,
    SqlAlchemyWorkingHoursRepository,
)
from app.infrastructure.in_memory import InMemoryRateLimiter
from scripts.seed import run_seed
from tests.integration.test_appointments_api import PASSWORD, ZONE, at
from tests.unit.api.conftest import API_ENV
from tests.unit.application.agenda_helpers import RecordingDispatcher, RecordingVerification

PUBLIC = "/api/v1/public"
NOW = at(8, day=6)  # viernes previo


@dataclass
class Scene:
    client: TestClient
    sessions: sessionmaker[Session]
    engine: Engine
    verification: RecordingVerification = field(default_factory=RecordingVerification)
    professional_id: str = ""
    patient_documents: dict[str, str] = field(default_factory=dict)

    def book(self, **overrides: object) -> Response:
        body: dict[str, object] = {
            "professional_id": self.professional_id,
            "starts_at": at(10).isoformat(),
            "document_number": "41000111",
            "first_name": "Lucia",
            "last_name": "Diaz",
            "email": "lucia@example.com",
        }
        body.update(overrides)
        response: Response = self.client.post(f"{PUBLIC}/appointments", json=body)
        return response


@pytest.fixture
def scene(
    monkeypatch: pytest.MonkeyPatch, engine: Engine, session_factory: sessionmaker[Session]
) -> Iterator[Scene]:
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    for name, value in API_ENV.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    from app.main import create_app

    app = create_app()
    current = Scene(client=TestClient(app), sessions=session_factory, engine=engine)

    def agenda() -> AgendaDeps:
        return AgendaDeps(
            appointments=SqlAlchemyAppointmentRepository(session_factory),
            patients=SqlAlchemyPatientRepository(session_factory),
            professionals=SqlAlchemyProfessionalRepository(session_factory),
            working_hours=SqlAlchemyWorkingHoursRepository(session_factory),
            time_off=SqlAlchemyTimeOffRepository(session_factory),
            settings=SqlAlchemyClinicSettingsRepository(session_factory),
            unit_of_work=lambda: SqlAlchemyAgendaUnitOfWork(session_factory),
            dispatcher=RecordingDispatcher(),
            clock=lambda: NOW,
        )

    tokens = iter(f"tok-int-{n}" for n in range(1, 100))
    limiter = InMemoryRateLimiter(lambda: NOW)
    app.dependency_overrides[get_user_repository] = lambda: SqlAlchemyUserAccountRepository(
        session_factory
    )
    app.dependency_overrides[get_agenda_deps] = agenda
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    app.dependency_overrides[get_public_booking_deps] = lambda: PublicBookingDeps(
        agenda=agenda(),
        new_token=lambda: next(tokens),
        hash_token=hash_confirmation_token,
        hold_minutes=60,
        verification=current.verification,
    )
    listed = current.client.get(f"{PUBLIC}/professionals").json()
    current.professional_id = next(p["id"] for p in listed if "Ana" in p["display_name"])
    yield current
    get_settings.cache_clear()


def _rows(scene: Scene) -> list[tuple[str, bool, bool]]:
    with scene.engine.connect() as connection:
        return [
            (str(r[0]), r[1], r[2])
            for r in connection.execute(
                text(
                    "SELECT status, created_by IS NULL, confirmation_token_hash IS NOT NULL "
                    "FROM appointments"
                )
            )
        ]


def test_a_booking_stores_a_pending_appointment_and_the_response_has_no_patient_data(
    scene: Scene,
) -> None:
    response = scene.book()

    assert response.status_code == 202, response.text
    for secret in ("41000111", "lucia@example.com", "Lucia", "Diaz"):
        assert secret not in response.text
    assert _rows(scene) == [("scheduled", True, True)]
    [(appointment_id, token)] = scene.verification.calls
    assert token == "tok-int-1"
    assert appointment_id


def test_confirming_clears_the_pending_state_and_the_token_works_once(scene: Scene) -> None:
    scene.book()

    first = scene.client.post(f"{PUBLIC}/appointment-confirmations", json={"token": "tok-int-1"})
    second = scene.client.post(f"{PUBLIC}/appointment-confirmations", json={"token": "tok-int-1"})

    assert first.status_code == 200, first.text
    assert second.status_code == 410
    assert second.json()["error"]["code"] == "CONFIRMATION_LINK_INVALID"
    assert _rows(scene) == [("scheduled", True, False)]
    with scene.engine.connect() as connection:
        kinds = [r[0] for r in connection.execute(text("SELECT kind FROM email_notifications"))]
    assert kinds == ["confirmation"]


def test_the_booked_slot_leaves_the_public_list_and_a_clash_is_409_without_a_patient(
    scene: Scene,
) -> None:
    scene.book()
    day = "2026-11-09"

    slots = scene.client.get(f"{PUBLIC}/professionals/{scene.professional_id}/slots?date={day}")
    clash = scene.book(document_number="41000222", email="otra@example.com")

    assert at(10).isoformat() not in [s["starts_at"].replace("Z", "+00:00") for s in slots.json()]
    assert clash.status_code == 409
    assert clash.json()["error"]["code"] == "SLOT_TAKEN"
    with scene.engine.connect() as connection:
        found = connection.execute(
            text("SELECT count(*) FROM patients WHERE document_number = '41000222'")
        ).scalar_one()
    assert found == 0


def test_an_existing_document_with_another_name_is_the_generic_rejection(scene: Scene) -> None:
    with scene.engine.connect() as connection:
        document = str(
            connection.execute(text("SELECT document_number FROM patients LIMIT 1")).scalar_one()
        )

    response = scene.book(document_number=document, first_name="Otra", last_name="Persona")

    assert response.status_code == 409
    assert response.json() == {
        "error": {"code": "BOOKING_NOT_POSSIBLE", "message": "Verifique sus datos ingresados."}
    }
    assert _rows(scene) == []


def test_reception_sees_the_pending_appointment_and_can_only_cancel_it(scene: Scene) -> None:
    scene.book()
    login = scene.client.post(
        "/api/v1/auth/login", json={"email": "recepcion@example.com", "password": PASSWORD}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    with scene.engine.connect() as connection:
        appointment_id = str(connection.execute(text("SELECT id FROM appointments")).scalar_one())

    detail = scene.client.get(f"/api/v1/appointments/{appointment_id}", headers=headers).json()
    moved = scene.client.post(
        f"/api/v1/appointments/{appointment_id}/reschedule",
        json={"starts_at": at(11).isoformat()},
        headers=headers,
    )
    cancelled = scene.client.post(
        f"/api/v1/appointments/{appointment_id}/cancel",
        json={"reason": "No confirmó"},
        headers=headers,
    )

    assert (detail["origin"], detail["created_by"]) == ("online", None)
    assert detail["pending_until"] is not None
    assert moved.status_code == 409
    assert moved.json()["error"]["code"] == "PENDING_CONFIRMATION"
    assert cancelled.status_code == 200
    assert _rows(scene) == [("cancelled", True, False)]


def test_the_honeypot_writes_nothing(scene: Scene) -> None:
    response = scene.book(website="http://spam")

    assert response.status_code == 400
    assert _rows(scene) == []
    assert scene.verification.calls == []
