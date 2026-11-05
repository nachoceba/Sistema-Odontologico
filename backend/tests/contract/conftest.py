"""Fixtures de la bateria de contrato, parametrizadas por fabrica (design D-7, D-9).

Cada escenario corre contra la fabrica en memoria y contra la de PostgreSQL (esta ultima solo
con ``pytest -m integration``). Los tests solo usan los puertos, nunca atributos de una
implementacion concreta, y piden a la fabrica las referencias a profesionales, pacientes y
usuarios: en memoria son el mismo texto, en PostgreSQL el UUID de una fila creada para el test.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.domain.appointments.ports import (
    AgendaUnitOfWork,
    AppointmentRepository,
    NotificationRepository,
)
from app.domain.appointments.types import Notification, NotificationKind, NotificationStatus
from app.domain.auth import Role, UserAccount, UserAccountRepository
from app.domain.patients.ports import PatientRepository
from app.domain.patients.types import Patient, PatientRecord
from app.domain.professionals import Professional, ProfessionalRepository
from app.domain.schedules.ports import TimeOffRepository, WorkingHoursRepository
from app.domain.settings.ports import ClinicSettingsRepository
from app.domain.settings.types import ClinicSettings
from app.infrastructure.db import enums
from app.infrastructure.db.enums import UserRole
from app.infrastructure.db.models import (
    ClinicSettingsModel,
    EmailNotificationModel,
    PatientModel,
    ProfessionalModel,
    UserModel,
)
from app.infrastructure.db.repositories import (
    SqlAlchemyAgendaUnitOfWork,
    SqlAlchemyAppointmentRepository,
    SqlAlchemyClinicSettingsRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyPatientRepository,
    SqlAlchemyProfessionalRepository,
    SqlAlchemyTimeOffRepository,
    SqlAlchemyUserAccountRepository,
    SqlAlchemyWorkingHoursRepository,
)
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


class RepositoryFactory(Protocol):
    """Crea repositorios vacios (o con estado inicial) para un test."""

    def professional(self, name: str) -> str:
        """Referencia a un profesional (y su cuenta) que existe donde la implementacion lo exige."""
        ...

    def user(self, name: str) -> str:
        """Referencia a un usuario creador de turnos."""
        ...

    def patient(self, name: str) -> str:
        """Referencia a un paciente: el cargado con ese id en ``patients(initial)`` o uno minimo."""
        ...

    def appointments(self) -> AppointmentRepository: ...

    def unit_of_work(self) -> Callable[[], AgendaUnitOfWork]:
        """Fabrica de unidades de trabajo sobre los mismos repositorios de la fabrica."""
        ...

    def notifications(self) -> NotificationRepository: ...

    def seed_notification(
        self,
        appointment_id: str,
        kind: NotificationKind,
        status: NotificationStatus,
        starts_at: datetime,
    ) -> Notification:
        """Carga una fila con cualquier estado (el envio y el estado son de C-11)."""
        ...

    def working_hours(self) -> WorkingHoursRepository: ...

    def time_off(self) -> TimeOffRepository: ...

    def patients(self, initial: Sequence[Patient | PatientRecord] = ()) -> PatientRepository: ...

    def settings(self, initial: ClinicSettings | None = None) -> ClinicSettingsRepository: ...

    def add_account(
        self,
        name: str,
        *,
        email: str,
        role: Role,
        active: bool = True,
        with_professional: bool = False,
    ) -> UserAccount:
        """Crea una cuenta (y su ficha si es odontologo) y devuelve lo que debe leer el repo."""
        ...

    def user_accounts(self) -> UserAccountRepository: ...

    def professionals(self) -> ProfessionalRepository: ...


class InMemoryFactory:
    """Las referencias son el propio nombre: en memoria no hay claves foraneas."""

    def __init__(self) -> None:
        self._accounts = InMemoryUserAccountRepository()
        self._notifications = InMemoryNotificationRepository()
        self._appointments = InMemoryAppointmentRepository()

    def professional(self, name: str) -> str:
        return name

    def user(self, name: str) -> str:
        return name

    def patient(self, name: str) -> str:
        return name

    def appointments(self) -> AppointmentRepository:
        return self._appointments

    def unit_of_work(self) -> Callable[[], AgendaUnitOfWork]:
        return lambda: InMemoryAgendaUnitOfWork(self._appointments, self._notifications)

    def notifications(self) -> NotificationRepository:
        return self._notifications

    def seed_notification(
        self,
        appointment_id: str,
        kind: NotificationKind,
        status: NotificationStatus,
        starts_at: datetime,
    ) -> Notification:
        return self._notifications.seed(appointment_id, kind, status, starts_at)

    def working_hours(self) -> WorkingHoursRepository:
        return InMemoryWorkingHoursRepository()

    def time_off(self) -> TimeOffRepository:
        return InMemoryTimeOffRepository()

    def patients(self, initial: Sequence[Patient | PatientRecord] = ()) -> PatientRepository:
        return InMemoryPatientRepository(initial)

    def settings(self, initial: ClinicSettings | None = None) -> ClinicSettingsRepository:
        return InMemoryClinicSettingsRepository(initial)

    def add_account(
        self,
        name: str,
        *,
        email: str,
        role: Role,
        active: bool = True,
        with_professional: bool = False,
    ) -> UserAccount:
        account = UserAccount(
            id=str(uuid.uuid4()),
            email=email,
            full_name=f"Usuario {name}",
            password_hash="hash-ficticio",
            role=role,
            active=active,
            professional_id=str(uuid.uuid4()) if with_professional else None,
        )
        self._accounts.add(account)
        if account.professional_id is not None:
            self._accounts.professionals[account.professional_id] = Professional(
                id=account.professional_id,
                user_id=account.id,
                display_name=f"Profesional {name}",
                license_number=None,
                active=active,
            )
        return account

    def user_accounts(self) -> UserAccountRepository:
        return self._accounts

    def professionals(self) -> ProfessionalRepository:
        return InMemoryProfessionalRepository(self._accounts)


class PostgresFactory:
    """Repositorios sobre la base de pruebas; crea las filas que exigen las claves foraneas.

    Cada referencia con nombre se crea una sola vez por test (la base se vacia entre tests).
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory
        self._professionals: dict[str, str] = {}
        self._users: dict[str, str] = {}
        self._patients: dict[str, str] = {}

    def _new_user(self, name: str, role: UserRole) -> uuid.UUID:
        user = UserModel(
            email=f"{name}-{uuid.uuid4().hex[:8]}@example.com",
            password_hash="hash-ficticio",
            full_name=f"Usuario {name}",
            role=role,
        )
        with self._sessions.begin() as session:
            session.add(user)
        return user.id

    def professional(self, name: str) -> str:
        if name not in self._professionals:
            owner = self._new_user(name, UserRole.DENTIST)
            row = ProfessionalModel(user_id=owner, display_name=f"Profesional {name}")
            with self._sessions.begin() as session:
                session.add(row)
            self._professionals[name] = str(row.id)
        return self._professionals[name]

    def user(self, name: str) -> str:
        if name not in self._users:
            self._users[name] = str(self._new_user(name, UserRole.RECEPTIONIST))
        return self._users[name]

    def patient(self, name: str) -> str:
        if name not in self._patients:
            self._add_patient(
                name,
                Patient(
                    id=name,
                    first_name="Paciente",
                    last_name=name,
                    email=f"{name}@example.com",
                    active=True,
                ),
            )
        return self._patients[name]

    def _add_patient(self, name: str, patient: Patient | PatientRecord) -> None:
        if isinstance(patient, PatientRecord):
            document_number = patient.document_number
            phone, birth_date = patient.phone, patient.birth_date
        else:
            document_number = f"DOC-{name}-{uuid.uuid4().hex[:8]}"
            phone, birth_date = None, None
        row = PatientModel(
            first_name=patient.first_name,
            last_name=patient.last_name,
            document_number=document_number,
            email=patient.email,
            phone=phone,
            birth_date=birth_date,
            active=patient.active,
        )
        with self._sessions.begin() as session:
            session.add(row)
        self._patients[name] = str(row.id)

    def appointments(self) -> AppointmentRepository:
        return SqlAlchemyAppointmentRepository(self._sessions)

    def unit_of_work(self) -> Callable[[], AgendaUnitOfWork]:
        return lambda: SqlAlchemyAgendaUnitOfWork(self._sessions)

    def notifications(self) -> NotificationRepository:
        return SqlAlchemyNotificationRepository(self._sessions)

    def seed_notification(
        self,
        appointment_id: str,
        kind: NotificationKind,
        status: NotificationStatus,
        starts_at: datetime,
    ) -> Notification:
        row = EmailNotificationModel(
            appointment_id=uuid.UUID(appointment_id),
            kind=enums.NotificationKind(kind.value),
            status=enums.NotificationStatus(status.value),
            sent_at=starts_at if status is NotificationStatus.SENT else None,
            error="fallo simulado" if status is NotificationStatus.FAILED else None,
            appointment_starts_at=starts_at,
        )
        with self._sessions.begin() as session:
            session.add(row)
        return Notification(
            id=str(row.id),
            appointment_id=appointment_id,
            kind=kind,
            status=status,
            sent_at=row.sent_at,
            error=row.error,
            appointment_starts_at=starts_at,
        )

    def working_hours(self) -> WorkingHoursRepository:
        return SqlAlchemyWorkingHoursRepository(self._sessions)

    def time_off(self) -> TimeOffRepository:
        return SqlAlchemyTimeOffRepository(self._sessions)

    def patients(self, initial: Sequence[Patient | PatientRecord] = ()) -> PatientRepository:
        for patient in initial:
            self._add_patient(patient.id, patient)
        return SqlAlchemyPatientRepository(self._sessions)

    def settings(self, initial: ClinicSettings | None = None) -> ClinicSettingsRepository:
        if initial is not None:
            row = ClinicSettingsModel(
                id=1,
                clinic_name="Consultorio Demo",
                address="Calle Ficticia 123",
                slot_minutes=initial.slot_minutes,
                timezone=initial.timezone,
                min_notice_hours=initial.min_notice_hours,
            )
            with self._sessions.begin() as session:
                session.add(row)
        return SqlAlchemyClinicSettingsRepository(self._sessions)

    def add_account(
        self,
        name: str,
        *,
        email: str,
        role: Role,
        active: bool = True,
        with_professional: bool = False,
    ) -> UserAccount:
        user = UserModel(
            email=email,
            password_hash="hash-ficticio",
            full_name=f"Usuario {name}",
            role=UserRole(role.value),
            active=active,
        )
        with self._sessions.begin() as session:
            session.add(user)
        professional_id: str | None = None
        if with_professional:
            row = ProfessionalModel(user_id=user.id, display_name=f"Profesional {name}")
            with self._sessions.begin() as session:
                session.add(row)
            professional_id = str(row.id)
        return UserAccount(
            id=str(user.id),
            email=email,
            full_name=f"Usuario {name}",
            password_hash="hash-ficticio",
            role=role,
            active=active,
            professional_id=professional_id,
        )

    def user_accounts(self) -> UserAccountRepository:
        return SqlAlchemyUserAccountRepository(self._sessions)

    def professionals(self) -> ProfessionalRepository:
        return SqlAlchemyProfessionalRepository(self._sessions)


FACTORIES = [
    pytest.param("in_memory", id="in_memory"),
    pytest.param("postgres", id="postgres", marks=pytest.mark.integration),
]


@pytest.fixture(params=FACTORIES)
def factory(request: pytest.FixtureRequest) -> RepositoryFactory:
    if request.param == "in_memory":
        return InMemoryFactory()
    # La base solo se pide (y se vacia) cuando corre la variante postgres.
    session_factory: sessionmaker[Session] = request.getfixturevalue("session_factory")
    return PostgresFactory(session_factory)


@dataclass(frozen=True)
class Refs:
    """Las referencias con nombre que usan los escenarios de turnos y horarios."""

    dra_a: str
    dr_b: str
    pac_1: str
    pac_2: str
    rec_1: str


@pytest.fixture
def ids(factory: RepositoryFactory) -> Refs:
    return Refs(
        dra_a=factory.professional("dra-a"),
        dr_b=factory.professional("dr-b"),
        pac_1=factory.patient("pac-1"),
        pac_2=factory.patient("pac-2"),
        rec_1=factory.user("rec-1"),
    )


@pytest.fixture
def appointment_repo(factory: RepositoryFactory) -> AppointmentRepository:
    return factory.appointments()


@pytest.fixture
def working_hours_repo(factory: RepositoryFactory) -> WorkingHoursRepository:
    return factory.working_hours()


@pytest.fixture
def time_off_repo(factory: RepositoryFactory) -> TimeOffRepository:
    return factory.time_off()
