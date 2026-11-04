"""Fichas, horarios y licencias de punta a punta contra PostgreSQL con los usuarios del seed
(specs professional-schedule-api y schedule-repository, DD-53, regla dura 6).

Se levanta la API real con repositorios SQL y un reloj fijo; las cuentas y los profesionales son
los del seed ficticio (la contrasena es solo de este test).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_agenda_deps, get_schedule_deps, get_user_repository
from app.application.appointments import AgendaDeps
from app.application.professionals import ScheduleDeps
from app.core.config import get_settings
from app.core.timezone import to_utc
from app.domain.appointments import NewAppointment
from app.infrastructure.db.models import (
    AppointmentModel,
    PatientModel,
    ProfessionalModel,
    TimeOffModel,
    UserModel,
    WorkingHoursModel,
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
ADMIN = "admin@example.com"
RECEPTION = "recepcion@example.com"
DRA_A = "dra.a@example.com"


def at(hour: int, minute: int = 0, day: int = 9) -> datetime:
    """Noviembre de 2026 (lunes 9 por defecto) a la hora local del consultorio, en UTC."""
    return to_utc(datetime(2026, 11, day, hour, minute), ZONE)


def block(weekday: int, start: str, end: str) -> dict[str, object]:
    return {"weekday": weekday, "start_time": start, "end_time": end}


@dataclass
class Scene:
    client: TestClient
    sessions: sessionmaker[Session]
    now: datetime = field(default_factory=lambda: at(8, day=6))  # viernes previo
    patient_ids: dict[str, str] = field(default_factory=dict)
    professional_ids: dict[str, str] = field(default_factory=dict)
    user_ids: dict[str, str] = field(default_factory=dict)

    def headers(self, email: str) -> dict[str, str]:
        response = self.client.post(
            "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def base(self, who: str) -> str:
        return f"/api/v1/professionals/{self.professional_ids[who]}"

    def seed_appointment(self, who: str, starts_at: datetime, patient: str = "Gomez") -> str:
        saved = SqlAlchemyAppointmentRepository(self.sessions).add(
            NewAppointment(
                patient_id=self.patient_ids[patient],
                professional_id=self.professional_ids[who],
                starts_at=starts_at,
                ends_at=starts_at + timedelta(minutes=30),
                created_by=self.user_ids[RECEPTION],
            )
        )
        return saved.id

    def appointment_rows(self) -> list[tuple[str, str, datetime, str]]:
        with self.sessions() as session:
            return [
                (str(r.id), str(r.professional_id), r.starts_at, r.status.value)
                for r in session.scalars(
                    select(AppointmentModel).order_by(AppointmentModel.starts_at)
                )
            ]

    def hours_rows(self, who: str) -> list[tuple[int, str, str]]:
        with self.sessions() as session:
            rows = session.scalars(
                select(WorkingHoursModel)
                .where(WorkingHoursModel.professional_id == self.professional_ids[who])
                .order_by(WorkingHoursModel.weekday, WorkingHoursModel.start_time)
            )
            return [
                (r.weekday, r.start_time.strftime("%H:%M"), r.end_time.strftime("%H:%M"))
                for r in rows
            ]

    def time_off_count(self, who: str) -> int:
        with self.sessions() as session:
            return len(
                session.scalars(
                    select(TimeOffModel).where(
                        TimeOffModel.professional_id == self.professional_ids[who]
                    )
                ).all()
            )

    def professional_row(self, who: str) -> tuple[str, str | None, bool]:
        with self.sessions() as session:
            row = session.get(ProfessionalModel, self.professional_ids[who])
            assert row is not None
            return (row.display_name, row.license_number, row.active)


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
    sessions = session_factory
    app.dependency_overrides[get_user_repository] = lambda: SqlAlchemyUserAccountRepository(
        sessions
    )
    app.dependency_overrides[get_schedule_deps] = lambda: ScheduleDeps(
        professionals=SqlAlchemyProfessionalRepository(sessions),
        working_hours=SqlAlchemyWorkingHoursRepository(sessions),
        time_off=SqlAlchemyTimeOffRepository(sessions),
        appointments=SqlAlchemyAppointmentRepository(sessions),
        settings=SqlAlchemyClinicSettingsRepository(sessions),
        clock=lambda: current.now,
    )
    app.dependency_overrides[get_agenda_deps] = lambda: AgendaDeps(
        appointments=SqlAlchemyAppointmentRepository(sessions),
        patients=SqlAlchemyPatientRepository(sessions),
        professionals=SqlAlchemyProfessionalRepository(sessions),
        working_hours=SqlAlchemyWorkingHoursRepository(sessions),
        time_off=SqlAlchemyTimeOffRepository(sessions),
        settings=SqlAlchemyClinicSettingsRepository(sessions),
        unit_of_work=lambda: SqlAlchemyAgendaUnitOfWork(sessions),
        dispatcher=RecordingDispatcher(),
        clock=lambda: current.now,
    )
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


@pytest.mark.integration
def test_admin_changes_the_hours_and_the_real_slots_and_conflicts_follow(scene: Scene) -> None:
    admin = scene.headers(ADMIN)
    late = scene.seed_appointment("A", at(16))
    slots_url = f"{scene.base('A')}/slots"

    response = scene.client.put(
        f"{scene.base('A')}/working-hours",
        json={"blocks": [block(0, "09:00", "12:00")]},
        headers=admin,
    )

    assert response.status_code == 200, response.text
    assert response.json()["blocks"] == [block(0, "09:00", "12:00")]
    assert [c["appointment_id"] for c in response.json()["conflicts"]] == [late]
    assert scene.hours_rows("A") == [(0, "09:00", "12:00")]
    assert [row[3] for row in scene.appointment_rows()] == ["scheduled"]
    monday = scene.client.get(slots_url, params={"date": "2026-11-09"}, headers=admin).json()
    free = [s for s in monday if s["status"] == "FREE"]
    assert len(free) == 6
    tuesday = scene.client.get(slots_url, params={"date": "2026-11-10"}, headers=admin).json()
    assert {s["status"] for s in tuesday} == {"OUTSIDE_HOURS"}


@pytest.mark.integration
def test_time_off_blocks_slots_lists_the_appointment_and_deleting_gives_them_back(
    scene: Scene,
) -> None:
    admin = scene.headers(ADMIN)
    booked = scene.seed_appointment("A", at(10))
    slots_url = f"{scene.base('A')}/slots"

    added = scene.client.post(
        f"{scene.base('A')}/time-off",
        json={"starts_on": "2026-11-09", "ends_on": "2026-11-10", "reason": "Congreso"},
        headers=admin,
    )

    assert added.status_code == 201, added.text
    assert [(c["appointment_id"], c["reason"]) for c in added.json()["conflicts"]] == [
        (booked, "TIME_OFF")
    ]
    assert [row[3] for row in scene.appointment_rows()] == ["scheduled"]
    blocked = scene.client.get(slots_url, params={"date": "2026-11-09"}, headers=admin).json()
    assert {s["status"] for s in blocked} == {"OUTSIDE_HOURS"}
    listed = scene.client.get(f"{scene.base('A')}/conflicts", headers=scene.headers(RECEPTION))
    assert [c["appointment_id"] for c in listed.json()] == [booked]

    time_off_id = added.json()["time_off"]["id"]
    deleted = scene.client.delete(f"{scene.base('A')}/time-off/{time_off_id}", headers=admin)

    assert deleted.status_code == 204
    assert scene.time_off_count("A") == 0
    back = scene.client.get(slots_url, params={"date": "2026-11-09"}, headers=admin).json()
    assert "FREE" in {s["status"] for s in back}
    assert scene.client.get(f"{scene.base('A')}/conflicts", headers=admin).json() == []
    missing = scene.client.delete(f"{scene.base('A')}/time-off/{time_off_id}", headers=admin)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "TIME_OFF_NOT_FOUND"


@pytest.mark.integration
def test_admin_edits_display_name_and_license_and_inactive_files_too(scene: Scene) -> None:
    admin = scene.headers(ADMIN)

    renamed = scene.client.patch(
        scene.base("A"),
        json={"display_name": "Dra. Ana Pérez", "license_number": "MAT-9001"},
        headers=admin,
    )
    cleared = scene.client.patch(scene.base("B"), json={"license_number": None}, headers=admin)

    assert renamed.status_code == 200, renamed.text
    assert scene.professional_row("A") == ("Dra. Ana Pérez", "MAT-9001", True)
    assert cleared.status_code == 200
    assert scene.professional_row("B") == ("Dr. Bruno Benitez", None, True)
    listing = scene.client.get("/api/v1/professionals", headers=scene.headers(RECEPTION)).json()
    assert [row["display_name"] for row in listing] == ["Dr. Bruno Benitez", "Dra. Ana Pérez"]


@pytest.mark.integration
def test_dd53_the_dentist_and_reception_cannot_touch_what_they_do_not_own(scene: Scene) -> None:
    dentist = scene.headers(DRA_A)
    reception = scene.headers(RECEPTION)
    hours_before = (scene.hours_rows("A"), scene.hours_rows("B"))
    profile_before = (scene.professional_row("A"), scene.professional_row("B"))

    for suffix in ("working-hours", "time-off", "conflicts"):
        foreign = scene.client.get(f"{scene.base('B')}/{suffix}", headers=dentist)
        assert foreign.status_code == 403, (suffix, foreign.text)
        assert foreign.json()["error"]["code"] == "FORBIDDEN"
    own = scene.client.get(f"{scene.base('A')}/working-hours", headers=dentist)
    assert own.status_code == 200

    own_writes = [
        scene.client.put(f"{scene.base('A')}/working-hours", json={"blocks": []}, headers=dentist),
        scene.client.post(
            f"{scene.base('A')}/time-off",
            json={"starts_on": "2026-11-09", "ends_on": "2026-11-09"},
            headers=dentist,
        ),
        scene.client.patch(scene.base("A"), json={"display_name": "Otra"}, headers=dentist),
    ]
    reception_write = scene.client.put(
        f"{scene.base('A')}/working-hours", json={"blocks": []}, headers=reception
    )

    for response in (*own_writes, reception_write):
        assert response.status_code == 403, response.text
    assert (scene.hours_rows("A"), scene.hours_rows("B")) == hours_before
    assert scene.time_off_count("A") == 0
    assert (scene.professional_row("A"), scene.professional_row("B")) == profile_before


@pytest.mark.integration
def test_hard_rule_6_changing_the_hours_never_allows_overlapping_appointments(
    scene: Scene,
) -> None:
    admin = scene.headers(ADMIN)
    reception = scene.headers(RECEPTION)
    existing = scene.seed_appointment("A", at(10))

    changed = scene.client.put(
        f"{scene.base('A')}/working-hours",
        json={"blocks": [block(0, "10:00", "14:00")]},
        headers=admin,
    )
    clash = scene.client.post(
        "/api/v1/appointments",
        json={
            "patient_id": scene.patient_ids["Perez"],
            "professional_id": scene.professional_ids["A"],
            "starts_at": at(10).isoformat(),
        },
        headers=reception,
    )

    assert changed.status_code == 200, changed.text
    assert changed.json()["conflicts"] == []
    assert clash.status_code == 409, clash.text
    assert clash.json()["error"]["code"] == "SLOT_TAKEN"
    rows = [row for row in scene.appointment_rows() if row[3] == "scheduled"]
    assert [(row[0], row[2]) for row in rows] == [(existing, at(10))]
