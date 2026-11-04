"""Escenario compartido por los tests de los casos de uso de agenda: repositorios en memoria."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta

from app.application.appointments import AgendaDeps
from app.application.professionals import ScheduleDeps
from app.domain.appointments import Appointment, NewAppointment, Notification
from app.domain.auth import Principal, Role, UserAccount
from app.domain.patients.types import Patient
from app.domain.settings.types import ClinicSettings
from app.infrastructure.in_memory import (
    InMemoryAgendaUnitOfWork,
    InMemoryAppointmentRepository,
    InMemoryClinicSettingsRepository,
    InMemoryNotificationRepository,
    InMemoryPatientRepository,
    InMemoryProfessionalRepository,
    InMemoryTimeOffRepository,
    InMemoryUserAccountRepository,
    InMemoryWorkingHoursRepository,
)
from tests.unit.domain.appointments.helpers import DR_B_HOURS, DRA_A_HOURS, NOW

PROF_A = "11111111-1111-4111-8111-111111111111"
PROF_B = "22222222-2222-4222-8222-222222222222"
RECEPTION = Principal(user_id="u-rec", role=Role.RECEPTIONIST)
ADMIN = Principal(user_id="u-admin", role=Role.ADMIN)
DENTIST_A = Principal(user_id="u-dra-a", role=Role.DENTIST, professional_id=PROF_A)
DENTIST_B = Principal(user_id="u-dr-b", role=Role.DENTIST, professional_id=PROF_B)
DENTIST_NO_FILE = Principal(user_id="u-sin-ficha", role=Role.DENTIST)


def _dentist(user_id: str, professional_id: str) -> UserAccount:
    return UserAccount(
        id=user_id,
        email=f"{user_id}@example.com",
        full_name=user_id,
        password_hash="hash",
        role=Role.DENTIST,
        active=True,
        professional_id=professional_id,
    )


class RecordingDispatcher:
    """Despachador de prueba: anota cada llamada; puede fallar a pedido."""

    def __init__(self) -> None:
        self.calls: list[list[Notification]] = []
        self.error: Exception | None = None

    def dispatch(self, notifications: Sequence[Notification]) -> None:
        self.calls.append(list(notifications))
        if self.error is not None:
            raise self.error


@dataclass
class World:
    """Repositorios cargados con dos profesionales y tres pacientes; reloj mutable."""

    now: datetime = NOW
    slot_minutes: int = 30
    min_notice_hours: int = 6
    accounts: InMemoryUserAccountRepository = field(default_factory=InMemoryUserAccountRepository)
    appointments: InMemoryAppointmentRepository = field(
        default_factory=InMemoryAppointmentRepository
    )
    working_hours: InMemoryWorkingHoursRepository = field(
        default_factory=InMemoryWorkingHoursRepository
    )
    time_off: InMemoryTimeOffRepository = field(default_factory=InMemoryTimeOffRepository)
    notifications: InMemoryNotificationRepository = field(
        default_factory=InMemoryNotificationRepository
    )
    dispatcher: RecordingDispatcher = field(default_factory=RecordingDispatcher)
    patient_list: list[Patient] = field(
        default_factory=lambda: [
            Patient("pac-1", "Juan", "Pérez", "juan@example.com", True),
            Patient("pac-2", "Ana", "Gómez", "ana@example.com", True),
            Patient("pac-off", "Paula", "Baja", "paula@example.com", False),
        ]
    )

    def __post_init__(self) -> None:
        self.accounts.add(_dentist("u-dra-a", PROF_A))
        self.accounts.add(_dentist("u-dr-b", PROF_B))
        self.working_hours.replace_for_professional(PROF_A, DRA_A_HOURS)
        self.working_hours.replace_for_professional(PROF_B, DR_B_HOURS)

    def set_professional_active(self, professional_id: str, active: bool) -> None:
        professional = self.accounts.professionals[professional_id]
        self.accounts.professionals[professional_id] = replace(professional, active=active)

    def set_patient_active(self, patient_id: str, active: bool) -> None:
        self.patient_list = [
            replace(p, active=active) if p.id == patient_id else p for p in self.patient_list
        ]

    def deps(self) -> AgendaDeps:
        return AgendaDeps(
            appointments=self.appointments,
            patients=InMemoryPatientRepository(self.patient_list),
            professionals=InMemoryProfessionalRepository(self.accounts),
            working_hours=self.working_hours,
            time_off=self.time_off,
            settings=InMemoryClinicSettingsRepository(
                ClinicSettings(
                    slot_minutes=self.slot_minutes, min_notice_hours=self.min_notice_hours
                )
            ),
            unit_of_work=lambda: InMemoryAgendaUnitOfWork(self.appointments, self.notifications),
            dispatcher=self.dispatcher,
            clock=lambda: self.now,
        )

    def schedule_deps(self) -> ScheduleDeps:
        """Las mismas fuentes que ``deps()``, para los casos de uso de C-07."""
        return ScheduleDeps(
            professionals=InMemoryProfessionalRepository(self.accounts),
            working_hours=self.working_hours,
            time_off=self.time_off,
            appointments=self.appointments,
            settings=InMemoryClinicSettingsRepository(
                ClinicSettings(
                    slot_minutes=self.slot_minutes, min_notice_hours=self.min_notice_hours
                )
            ),
            clock=lambda: self.now,
        )

    def seed(
        self,
        starts_at: datetime,
        *,
        patient_id: str = "pac-1",
        professional_id: str = PROF_A,
        minutes: int = 30,
    ) -> Appointment:
        """Un turno scheduled cargado directo en el repositorio."""
        return self.appointments.add(
            NewAppointment(
                patient_id=patient_id,
                professional_id=professional_id,
                starts_at=starts_at,
                ends_at=starts_at + timedelta(minutes=minutes),
                created_by="u-rec",
            )
        )

    def everything(self, professional_id: str = PROF_A) -> list[Appointment]:
        """Todos los turnos del profesional en cualquier estado (para 'no se escribio nada')."""
        return self.appointments.list_for_professional(
            professional_id, datetime(2000, 1, 1, tzinfo=UTC)
        )
