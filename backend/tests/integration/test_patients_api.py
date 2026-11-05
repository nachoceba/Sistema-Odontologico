"""Gestion de pacientes de punta a punta contra PostgreSQL con los datos del seed
(specs patient-api, patient-management y patient-repository, regla dura 6).

Se levanta la API real con repositorios SQL y un reloj fijo; las cuentas, los profesionales y los
pacientes son los del seed ficticio (la contrasena es solo de este test).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_agenda_deps, get_patient_deps, get_user_repository
from app.application.appointments import AgendaDeps
from app.application.patients import PatientDeps
from app.core.config import get_settings
from app.core.timezone import to_utc
from app.domain.appointments import NewAppointment
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
ADMIN = "admin@example.com"
RECEPTION = "recepcion@example.com"
DRA_A = "dra.a@example.com"
BASE = "/api/v1/patients"
LAURA = {
    "first_name": "Laura",
    "last_name": "Ruiz",
    "document_number": "40.222.333",
    "email": "Laura.Ruiz@Example.com",
    "phone": "011-5550-0011",
    "birth_date": "1990-05-10",
}


def at(hour: int, minute: int = 0, day: int = 9) -> datetime:
    """Noviembre de 2026 (lunes 9 por defecto) a la hora local del consultorio, en UTC."""
    return to_utc(datetime(2026, 11, day, hour, minute), ZONE)


@dataclass
class Scene:
    client: TestClient
    sessions: sessionmaker[Session]
    now: datetime = field(default_factory=lambda: at(8, day=6))  # viernes previo, 08:00 local
    patient_ids: dict[str, str] = field(default_factory=dict)
    professional_id: str = ""
    reception_id: str = ""

    def headers(self, email: str) -> dict[str, str]:
        response = self.client.post(
            "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def seed_appointment(self, patient: str, starts_at: datetime) -> str:
        saved = SqlAlchemyAppointmentRepository(self.sessions).add(
            NewAppointment(
                patient_id=self.patient_ids[patient],
                professional_id=self.professional_id,
                starts_at=starts_at,
                ends_at=starts_at + timedelta(minutes=30),
                created_by=self.reception_id,
            )
        )
        return saved.id

    def book(self, headers: dict[str, str], patient: str, starts_at: datetime) -> Any:
        return self.client.post(
            "/api/v1/appointments",
            json={
                "patient_id": self.patient_ids[patient],
                "professional_id": self.professional_id,
                "starts_at": starts_at.isoformat(),
            },
            headers=headers,
        )

    def appointments(self) -> list[tuple[str, str, datetime, str]]:
        with self.sessions() as session:
            return [
                (str(r.id), str(r.patient_id), r.starts_at, r.status.value)
                for r in session.scalars(
                    select(AppointmentModel).order_by(AppointmentModel.starts_at)
                )
            ]

    def patient_rows(self) -> list[tuple[str, str, str, str, str | None, bool]]:
        with self.sessions() as session:
            return [
                (str(p.id), p.last_name, p.document_number, p.email, p.phone, p.active)
                for p in session.scalars(select(PatientModel).order_by(PatientModel.last_name))
            ]

    def notification_count(self) -> int:
        with self.sessions() as session:
            return len(session.scalars(select(EmailNotificationModel)).all())


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
    app.dependency_overrides[get_patient_deps] = lambda: PatientDeps(
        patients=SqlAlchemyPatientRepository(sessions),
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
        current.professional_id = next(
            str(p.id) for p in session.scalars(select(ProfessionalModel)) if "Ana" in p.display_name
        )
        current.reception_id = next(
            str(u.id) for u in session.scalars(select(UserModel)) if u.email == RECEPTION
        )
    yield current
    get_settings.cache_clear()


@pytest.mark.integration
def test_reception_creates_searches_edits_and_cannot_repeat_the_document(
    scene: Scene, caplog: pytest.LogCaptureFixture
) -> None:
    reception = scene.headers(RECEPTION)

    created = scene.client.post(BASE, json=LAURA, headers=reception)
    assert created.status_code == 201, created.text
    laura = created.json()
    assert (laura["document_number"], laura["email"]) == ("40222333", "laura.ruiz@example.com")

    by_name = scene.client.get(BASE, params={"q": "ruiz"}, headers=reception).json()
    assert [p["id"] for p in by_name["items"]] == [laura["id"]]
    by_document = scene.client.get(BASE, params={"q": "40.222"}, headers=reception).json()
    assert [p["id"] for p in by_document["items"]] == [laura["id"]]
    seed_hit = scene.client.get(BASE, params={"q": "30.111"}, headers=reception).json()
    assert len(seed_hit["items"]) == 10
    assert seed_hit["truncated"] is False

    edited = scene.client.patch(f"{BASE}/{laura['id']}", json={"phone": None}, headers=reception)
    assert edited.status_code == 200
    assert edited.json()["phone"] is None
    assert edited.json()["birth_date"] == "1990-05-10"

    rows_before = scene.patient_rows()
    caplog.set_level("DEBUG")
    caplog.clear()
    repeated = scene.client.post(
        BASE, json=LAURA | {"first_name": "Otra", "document_number": "40222333"}, headers=reception
    )
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "DOCUMENT_TAKEN"
    for secret in ("40222333", "40.222.333", "Otra", "Ruiz"):
        assert secret not in repeated.text
    assert scene.patient_rows() == rows_before
    assert "40222333" not in caplog.text  # la base rechazo el UNIQUE: sin detalle en los logs


@pytest.mark.integration
def test_search_is_case_insensitive_and_treats_percent_as_text_on_the_real_database(
    scene: Scene,
) -> None:
    reception = scene.headers(RECEPTION)
    lower = scene.client.get(BASE, params={"q": "perez"}, headers=reception).json()
    upper = scene.client.get(BASE, params={"q": "PEREZ"}, headers=reception).json()
    assert [p["last_name"] for p in lower["items"]] == ["Perez"]
    assert upper == lower
    assert scene.client.get(BASE, params={"q": "%"}, headers=reception).json()["items"] == []
    ordered = scene.client.get(BASE, headers=reception).json()["items"]
    assert [p["last_name"] for p in ordered] == sorted(p["last_name"] for p in ordered)


@pytest.mark.integration
def test_deactivating_lists_the_appointment_keeps_it_scheduled_and_blocks_new_bookings(
    scene: Scene,
) -> None:
    reception = scene.headers(RECEPTION)
    juan_turn = scene.seed_appointment("Perez", at(10))
    notifications_before = scene.notification_count()
    appointments_before = scene.appointments()

    deactivated = scene.client.post(
        f"{BASE}/{scene.patient_ids['Perez']}/deactivate", headers=reception
    )

    assert deactivated.status_code == 200, deactivated.text
    body = deactivated.json()
    assert body["patient"]["active"] is False
    assert [a["id"] for a in body["upcoming_appointments"]] == [juan_turn]
    assert scene.appointments() == appointments_before
    assert scene.notification_count() == notifications_before

    blocked = scene.book(reception, "Perez", at(11))
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "PATIENT_INACTIVE"
    assert scene.appointments() == appointments_before

    reactivated = scene.client.post(
        f"{BASE}/{scene.patient_ids['Perez']}/reactivate", headers=reception
    )
    assert reactivated.status_code == 200
    assert scene.book(reception, "Perez", at(11)).status_code == 201


@pytest.mark.integration
def test_reactivating_does_not_allow_overlapping_a_scheduled_appointment(scene: Scene) -> None:
    reception = scene.headers(RECEPTION)
    taken = scene.seed_appointment("Perez", at(10))
    scene.client.post(f"{BASE}/{scene.patient_ids['Gomez']}/deactivate", headers=reception)
    scene.client.post(f"{BASE}/{scene.patient_ids['Gomez']}/reactivate", headers=reception)

    response = scene.book(reception, "Gomez", at(10))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SLOT_TAKEN"
    scheduled = [a for a in scene.appointments() if a[3] == "scheduled"]
    assert [a[0] for a in scheduled] == [taken]


@pytest.mark.integration
def test_cancelling_an_appointment_of_an_inactive_patient_is_allowed_on_the_real_database(
    scene: Scene,
) -> None:
    reception = scene.headers(RECEPTION)
    turn = scene.seed_appointment("Perez", at(10))
    scene.client.post(f"{BASE}/{scene.patient_ids['Perez']}/deactivate", headers=reception)

    response = scene.client.post(
        f"/api/v1/appointments/{turn}/cancel", json={"reason": "Pidió cancelar"}, headers=reception
    )

    assert response.status_code == 200, response.text
    assert [a[3] for a in scene.appointments()] == ["cancelled"]


@pytest.mark.integration
def test_admin_deletes_a_patient_without_appointments_but_not_one_with_appointments(
    scene: Scene,
) -> None:
    admin = scene.headers(ADMIN)
    laura = scene.client.post(BASE, json=LAURA, headers=admin).json()
    scene.seed_appointment("Perez", at(10))

    deleted = scene.client.delete(f"{BASE}/{laura['id']}", headers=admin)
    assert deleted.status_code == 204
    assert scene.client.get(f"{BASE}/{laura['id']}", headers=admin).status_code == 404

    rows_before = scene.patient_rows()
    refused = scene.client.delete(f"{BASE}/{scene.patient_ids['Perez']}", headers=admin)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "PATIENT_HAS_APPOINTMENTS"
    assert scene.patient_rows() == rows_before

    assert scene.client.post(BASE, json=LAURA, headers=admin).status_code == 201


@pytest.mark.integration
def test_a_cancelled_appointment_also_blocks_the_delete(scene: Scene) -> None:
    admin = scene.headers(ADMIN)
    turn = scene.seed_appointment("Gomez", at(10))
    scene.client.post(
        f"/api/v1/appointments/{turn}/cancel", json={"reason": "Cambio de planes"}, headers=admin
    )
    response = scene.client.delete(f"{BASE}/{scene.patient_ids['Gomez']}", headers=admin)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PATIENT_HAS_APPOINTMENTS"
    assert [a[3] for a in scene.appointments()] == ["cancelled"]


@pytest.mark.integration
def test_the_dentist_reads_but_every_write_is_403_and_the_database_does_not_change(
    scene: Scene,
) -> None:
    dentist = scene.headers(DRA_A)
    juan = scene.patient_ids["Perez"]
    assert scene.client.get(BASE, params={"q": "gomez"}, headers=dentist).status_code == 200
    assert scene.client.get(f"{BASE}/{juan}", headers=dentist).status_code == 200

    rows_before = scene.patient_rows()
    writes = [
        scene.client.post(BASE, json=LAURA, headers=dentist),
        scene.client.patch(f"{BASE}/{juan}", json={"email": "otro@example.com"}, headers=dentist),
        scene.client.post(f"{BASE}/{juan}/deactivate", headers=dentist),
        scene.client.post(f"{BASE}/{juan}/reactivate", headers=dentist),
        scene.client.delete(f"{BASE}/{juan}", headers=dentist),
    ]

    assert [r.status_code for r in writes] == [403] * 5
    assert scene.patient_rows() == rows_before


@pytest.mark.integration
def test_reception_cannot_delete_and_nothing_changes(scene: Scene) -> None:
    reception = scene.headers(RECEPTION)
    rows_before = scene.patient_rows()
    response = scene.client.delete(f"{BASE}/{scene.patient_ids['Sosa']}", headers=reception)
    assert response.status_code == 403
    assert scene.patient_rows() == rows_before
