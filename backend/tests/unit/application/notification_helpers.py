"""Escenario de los tests de envio: la misma agenda en memoria, con remitente falso."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from app.application.notifications import NotificationDeps
from app.domain.appointments import (
    Appointment,
    Notification,
    NotificationKind,
    NotificationStatus,
)
from app.domain.settings.types import ClinicSettings
from app.infrastructure.in_memory import (
    InMemoryAgendaUnitOfWork,
    InMemoryClinicSettingsRepository,
    InMemoryProfessionalRepository,
)
from tests.email_fakes import FakeEmailSender
from tests.unit.application.agenda_helpers import PROF_A, World
from tests.unit.domain.appointments.helpers import monday

CLINIC = ClinicSettings(
    clinic_name="Consultorio Demo",
    address="Av. Siempre Viva 742",
    phone="011 4000-0000",
)


@dataclass
class SendWorld:
    """Un turno futuro (lunes 10:00) con su confirmacion pendiente y un remitente falso."""

    world: World = field(default_factory=World)
    sender: FakeEmailSender = field(default_factory=FakeEmailSender)

    def __post_init__(self) -> None:
        professional = self.world.accounts.professionals[PROF_A]
        self.world.accounts.professionals[PROF_A] = replace(professional, display_name="Dra. A")
        self.appointment: Appointment = self.world.seed(monday(10))
        pending = self.world.notifications.add_pending_confirmation(
            self.appointment.id, self.appointment.starts_at
        )
        assert pending is not None
        self.notification: Notification = pending

    def deps(self) -> NotificationDeps:
        return NotificationDeps(
            unit_of_work=lambda: InMemoryAgendaUnitOfWork(
                self.world.appointments, self.world.notifications
            ),
            patients=self.world.patients,
            professionals=InMemoryProfessionalRepository(self.world.accounts),
            settings=InMemoryClinicSettingsRepository(CLINIC),
            sender=self.sender,
            clock=lambda: self.world.now,
            public_app_url="https://turnos.example.test",
        )

    def add_reminder(self) -> Notification:
        return self.world.notifications.seed(
            self.appointment.id,
            NotificationKind.REMINDER,
            NotificationStatus.PENDING,
            self.appointment.starts_at,
        )

    def rows(self) -> list[Notification]:
        return self.world.notifications.list_for_appointment(self.appointment.id)
