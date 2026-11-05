"""Turnos de punta a punta contra PostgreSQL con los usuarios del seed (specs appointment-api y
access-control, DD-53).

Se levanta la API real con repositorios SQL y un reloj fijo; las cuentas y los profesionales son
los del seed ficticio (la contrasena es solo de este test).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from types import TracebackType

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_agenda_deps, get_user_repository
from app.application.appointments import AgendaDeps
from app.core.config import get_settings
from app.core.timezone import to_utc
from app.domain.appointments import (
    AgendaUnitOfWork,
    AppointmentStatus,
    NewAppointment,
    NotificationRepository,
)
from app.infrastructure.db.models import (
    AppointmentModel,
    EmailNotificationModel,
    PatientModel,
    ProfessionalModel,
    UserModel,
)
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
from scripts.seed import run_seed
from tests.unit.api.conftest import API_ENV
from tests.unit.application.agenda_helpers import RecordingDispatcher

PASSWORD = "clave-demo-solo-de-este-test"
ZONE = "America/Argentina/Buenos_Aires"
BASE = "/api/v1/appointments"


def at(hour: int, minute: int = 0, day: int = 9) -> datetime:
    """Noviembre de 2026 (lunes 9 por defecto) a la hora local del consultorio, en UTC."""
    return to_utc(datetime(2026, 11, day, hour, minute), ZONE)


@dataclass
class Scene:
    client: TestClient
    sessions: sessionmaker[Session]
    now: list[datetime] = field(default_factory=lambda: [at(8, day=6)])  # viernes previo
    patient_ids: dict[str, str] = field(default_factory=dict)
    professional_ids: dict[str, str] = field(default_factory=dict)
    user_ids: dict[str, str] = field(default_factory=dict)
    dispatcher: RecordingDispatcher = field(default_factory=RecordingDispatcher)

    def deps(self, unit_of_work: Callable[[], AgendaUnitOfWork] | None = None) -> AgendaDeps:
        """Casos de uso sobre PostgreSQL; ``unit_of_work`` permite forzar una falla."""
        sessions = self.sessions
        return AgendaDeps(
            appointments=SqlAlchemyAppointmentRepository(sessions),
            patients=SqlAlchemyPatientRepository(sessions),
            professionals=SqlAlchemyProfessionalRepository(sessions),
            working_hours=SqlAlchemyWorkingHoursRepository(sessions),
            time_off=SqlAlchemyTimeOffRepository(sessions),
            settings=SqlAlchemyClinicSettingsRepository(sessions),
            unit_of_work=unit_of_work or (lambda: SqlAlchemyAgendaUnitOfWork(sessions)),
            dispatcher=self.dispatcher,
            clock=lambda: self.now[0],
        )

    def headers(self, email: str) -> dict[str, str]:
        response = self.client.post(
            "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def seed_appointment(
        self, professional: str, starts_at: datetime, patient: str = "Gomez"
    ) -> str:
        saved = SqlAlchemyAppointmentRepository(self.sessions).add(
            NewAppointment(
                patient_id=self.patient_ids[patient],
                professional_id=self.professional_ids[professional],
                starts_at=starts_at,
                ends_at=starts_at + timedelta(minutes=30),
                created_by=self.user_ids["recepcion@example.com"],
            )
        )
        return saved.id

    def rows(self) -> list[tuple[str, str, datetime, str]]:
        with self.sessions() as session:
            return [
                (str(r.id), str(r.professional_id), r.starts_at, r.status.value)
                for r in session.scalars(
                    select(AppointmentModel).order_by(AppointmentModel.starts_at)
                )
            ]


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
    current = Scene(client=TestClient(app), sessions=session_factory)
    app.dependency_overrides[get_user_repository] = lambda: SqlAlchemyUserAccountRepository(
        session_factory
    )
    app.dependency_overrides[get_agenda_deps] = lambda: current.deps()
    with session_factory() as session:
        current.patient_ids = {
            p.last_name: str(p.id) for p in session.scalars(select(PatientModel))
        }
        current.professional_ids = {
            ("A" if "Ana" in p.display_name else "B"): str(p.id)
            for p in session.scalars(select(ProfessionalModel))
        }
        current.user_ids = {u.email: str(u.id) for u in session.scalars(select(UserModel))}
    yield current
    get_settings.cache_clear()


def _book(
    scene: Scene, headers: dict[str, str], starts_at: datetime, patient: str = "Perez"
) -> Response:
    return scene.client.post(
        BASE,
        json={
            "patient_id": scene.patient_ids[patient],
            "professional_id": scene.professional_ids["A"],
            "starts_at": starts_at.isoformat(),
        },
        headers=headers,
    )


@pytest.mark.integration
def test_booking_stores_utc_and_a_second_booking_of_the_slot_is_409(scene: Scene) -> None:
    reception = scene.headers("recepcion@example.com")

    first = _book(scene, reception, at(10))
    clash = _book(scene, reception, at(10), patient="Gomez")

    assert first.status_code == 201, first.text
    assert clash.status_code == 409
    assert clash.json()["error"]["code"] == "SLOT_TAKEN"
    with scene.sessions() as session:
        stored = session.get(AppointmentModel, first.json()["id"])
        assert stored is not None
        assert stored.starts_at.astimezone(UTC) == datetime(2026, 11, 9, 13, 0, tzinfo=UTC)
        assert str(stored.created_by) == scene.user_ids["recepcion@example.com"]
        offset = session.execute(
            text("SELECT extract(hour FROM starts_at AT TIME ZONE 'UTC') FROM appointments")
        ).scalar_one()
    assert offset == 13
    assert [row[3] for row in scene.rows()] == ["scheduled"]


@pytest.mark.integration
def test_cancelling_frees_the_slot_and_it_can_be_booked_again(scene: Scene) -> None:
    reception = scene.headers("recepcion@example.com")
    booked = _book(scene, reception, at(10)).json()

    cancelled = scene.client.post(
        f"{BASE}/{booked['id']}/cancel", json={"reason": "Avisó por teléfono"}, headers=reception
    )
    again = _book(scene, reception, at(10), patient="Gomez")

    assert cancelled.status_code == 200
    assert cancelled.json()["cancel_reason"] == "Avisó por teléfono"
    assert again.status_code == 201, again.text
    assert sorted(row[3] for row in scene.rows()) == ["cancelled", "scheduled"]


@pytest.mark.integration
def test_rescheduling_moves_the_row_and_a_taken_target_leaves_it_untouched(scene: Scene) -> None:
    reception = scene.headers("recepcion@example.com")
    mine = _book(scene, reception, at(10)).json()["id"]
    _book(scene, reception, at(11), patient="Gomez")

    clash = scene.client.post(
        f"{BASE}/{mine}/reschedule", json={"starts_at": at(11).isoformat()}, headers=reception
    )
    moved = scene.client.post(
        f"{BASE}/{mine}/reschedule", json={"starts_at": at(15).isoformat()}, headers=reception
    )

    assert clash.status_code == 409
    assert clash.json()["error"]["code"] == "SLOT_TAKEN"
    assert moved.status_code == 200, moved.text
    stored = {row[0]: row[2] for row in scene.rows()}
    assert stored[mine].astimezone(UTC) == at(15)


@pytest.mark.integration
def test_the_dentist_marks_attendance_of_her_own_started_appointment(scene: Scene) -> None:
    reception = scene.headers("recepcion@example.com")
    mine = _book(scene, reception, at(10)).json()["id"]
    dentist = scene.headers("dra.a@example.com")

    before = scene.client.post(
        f"{BASE}/{mine}/attendance", json={"status": "completed"}, headers=dentist
    )
    scene.now[0] = at(10, 10)
    after = scene.client.post(
        f"{BASE}/{mine}/attendance", json={"status": "completed"}, headers=dentist
    )

    assert before.status_code == 409
    assert before.json()["error"]["code"] == "NOT_STARTED_YET"
    assert after.status_code == 200, after.text
    assert after.json()["status"] == AppointmentStatus.COMPLETED.value


@pytest.mark.integration
def test_a_dentist_of_the_seed_cannot_see_or_mark_the_other_dentists_appointments(
    scene: Scene,
) -> None:
    """DD-53 de punta a punta: la Dra. A recibe 403 sobre los turnos del Dr. B."""
    foreign = scene.seed_appointment("B", at(14))
    scene.now[0] = at(14, 10)
    dentist = scene.headers("dra.a@example.com")
    before = scene.rows()

    detail = scene.client.get(f"{BASE}/{foreign}", headers=dentist)
    listing = scene.client.get(
        BASE,
        params={
            "professional_id": scene.professional_ids["B"],
            "from": at(0).isoformat(),
            "to": at(23).isoformat(),
        },
        headers=dentist,
    )
    mark = scene.client.post(
        f"{BASE}/{foreign}/attendance", json={"status": "completed"}, headers=dentist
    )
    slots = scene.client.get(
        f"/api/v1/professionals/{scene.professional_ids['B']}/slots",
        params={"date": "2026-11-09"},
        headers=dentist,
    )

    for response in (detail, listing, mark, slots):
        assert response.status_code == 403, response.text
        assert response.json() == {
            "error": {"code": "FORBIDDEN", "message": "No tenés permiso para esta acción"}
        }
    assert scene.rows() == before


@pytest.mark.integration
def test_the_dentist_lists_her_own_agenda_and_slots(scene: Scene) -> None:
    reception = scene.headers("recepcion@example.com")
    _book(scene, reception, at(10))
    dentist = scene.headers("dra.a@example.com")

    listing = scene.client.get(
        BASE,
        params={
            "professional_id": scene.professional_ids["A"],
            "from": at(0).isoformat(),
            "to": at(23).isoformat(),
        },
        headers=dentist,
    )
    slots = scene.client.get(
        f"/api/v1/professionals/{scene.professional_ids['A']}/slots",
        params={"date": "2026-11-09"},
        headers=dentist,
    )

    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert slots.status_code == 200
    busy = [s for s in slots.json() if s["status"] == "BUSY"]
    assert [s["starts_at"] for s in busy] == [at(10).isoformat().replace("+00:00", "Z")]


def _week(scene: Scene, headers: dict[str, str], professional: str = "A") -> Response:
    return scene.client.get(
        BASE,
        params={
            "professional_id": scene.professional_ids[professional],
            "from": at(0).isoformat(),
            "to": at(0, day=16).isoformat(),
        },
        headers=headers,
    )


@pytest.mark.integration
def test_the_week_lists_the_patient_name_even_after_the_patient_is_deactivated(
    scene: Scene,
) -> None:
    """C-09, DD-79: nombre vigente contra PostgreSQL; desactivar al paciente no oculta el turno."""
    reception = scene.headers("recepcion@example.com")
    booked = _book(scene, reception, at(10)).json()

    listed = _week(scene, reception).json()
    assert [(r["patient_first_name"], r["patient_last_name"]) for r in listed] == [
        ("Juan", "Perez")
    ]
    assert set(listed[0]) >= {"patient_first_name", "patient_last_name", "patient_id"}
    assert "email" not in listed[0]

    with scene.sessions() as session, session.begin():
        patient = session.get(PatientModel, scene.patient_ids["Perez"])
        assert patient is not None
        patient.active = False

    after = _week(scene, reception).json()
    assert after[0]["id"] == booked["id"]
    assert after[0]["status"] == "scheduled"
    assert after[0]["patient_first_name"] == "Juan"
    detail = scene.client.get(f"{BASE}/{booked['id']}", headers=reception).json()
    assert detail["patient_last_name"] == "Perez"


@pytest.mark.integration
def test_the_dentist_gets_403_without_names_on_the_other_dentists_week(scene: Scene) -> None:
    scene.seed_appointment("B", at(14))
    before = scene.rows()

    response = _week(scene, scene.headers("dra.a@example.com"), professional="B")

    assert response.status_code == 403
    assert "patient_first_name" not in response.text
    assert "Juan" not in response.text
    assert scene.rows() == before


class NotificationWriteFailed(Exception):
    pass


class FailingNotificationsUnitOfWork:
    """La unidad real, pero registrar la confirmacion falla despues de escribir el turno."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._inner = SqlAlchemyAgendaUnitOfWork(sessions)
        self.appointments = self._inner.appointments

    @property
    def notifications(self) -> NotificationRepository:
        raise NotificationWriteFailed

    def __enter__(self) -> FailingNotificationsUnitOfWork:
        self._inner.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._inner.__exit__(exc_type, exc, traceback)


def _notification_rows(scene: Scene) -> int:
    with scene.sessions() as session:
        return len(session.scalars(select(EmailNotificationModel)).all())


@pytest.mark.integration
def test_booking_stores_one_pending_confirmation_with_the_appointment(scene: Scene) -> None:
    reception = scene.headers("recepcion@example.com")

    booked = _book(scene, reception, at(10)).json()

    with scene.sessions() as session:
        rows = session.scalars(select(EmailNotificationModel)).all()
    assert [(str(r.appointment_id), r.kind.value, r.status.value) for r in rows] == [
        (booked["id"], "confirmation", "pending")
    ]
    assert rows[0].appointment_starts_at.astimezone(UTC) == at(10)
    assert [len(call) for call in scene.dispatcher.calls] == [1]


@pytest.mark.integration
def test_reschedule_and_cancel_replace_and_discard_pending_notifications(scene: Scene) -> None:
    reception = scene.headers("recepcion@example.com")
    booked = _book(scene, reception, at(10)).json()["id"]

    scene.client.post(
        f"{BASE}/{booked}/reschedule", json={"starts_at": at(11).isoformat()}, headers=reception
    )
    with scene.sessions() as session:
        moved = session.scalars(select(EmailNotificationModel)).all()
    assert [r.appointment_starts_at.astimezone(UTC) for r in moved] == [at(11)]

    scene.client.post(f"{BASE}/{booked}/cancel", json={"reason": "Avisó"}, headers=reception)
    assert _notification_rows(scene) == 0


@pytest.mark.integration
def test_a_forced_notification_failure_leaves_no_appointment_and_no_notification(
    scene: Scene,
) -> None:
    reception = scene.headers("recepcion@example.com")
    deps = scene.deps(unit_of_work=lambda: FailingNotificationsUnitOfWork(scene.sessions))
    scene.client.app.dependency_overrides[get_agenda_deps] = lambda: deps  # type: ignore[attr-defined]

    with pytest.raises(NotificationWriteFailed):
        _book(scene, reception, at(10))

    assert scene.rows() == []
    assert _notification_rows(scene) == 0
    assert scene.dispatcher.calls == []
