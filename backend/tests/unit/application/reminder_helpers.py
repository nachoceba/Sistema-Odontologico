"""Escenario de los tests de la pasada de recordatorios: agenda en memoria y remitente falso."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from app.application.notifications import NotificationDeps
from app.application.reminders import ReminderDeps
from app.domain.appointments import Notification
from app.domain.settings.types import ClinicSettings
from app.infrastructure.in_memory import (
    InMemoryAgendaUnitOfWork,
    InMemoryClinicSettingsRepository,
    InMemoryProfessionalRepository,
)
from tests.email_fakes import FakeEmailSender
from tests.unit.application.agenda_helpers import PROF_A, PROF_B, World
from tests.unit.domain.appointments.helpers import local

# Domingo 4 de octubre de 2026 a las 09:00 locales: la pasada apunta al lunes 5.
SUNDAY_9 = local(2026, 10, 4, 9)


@dataclass
class ReminderWorld:
    """La agenda con dos profesionales, el reloj en la hora de la pasada y un remitente falso."""

    world: World = field(default_factory=World)
    sender: FakeEmailSender = field(default_factory=FakeEmailSender)
    clinic: ClinicSettings = field(
        default_factory=lambda: ClinicSettings(
            clinic_name="Consultorio Demo", address="Av. Siempre Viva 742", reminder_send_hour=9
        )
    )

    def __post_init__(self) -> None:
        for professional_id, name in ((PROF_A, "Dra. A"), (PROF_B, "Dr. B")):
            professional = self.world.accounts.professionals[professional_id]
            self.world.accounts.professionals[professional_id] = replace(
                professional, display_name=name
            )
        self.world.now = SUNDAY_9

    def deps(self) -> ReminderDeps:
        """Las dependencias leen la configuracion vigente en el momento de armarlas."""
        settings = InMemoryClinicSettingsRepository(self.clinic)
        return ReminderDeps(
            unit_of_work=lambda: InMemoryAgendaUnitOfWork(
                self.world.appointments, self.world.notifications
            ),
            appointments=self.world.appointments,
            settings=settings,
            notification_deps=NotificationDeps(
                unit_of_work=lambda: InMemoryAgendaUnitOfWork(
                    self.world.appointments, self.world.notifications
                ),
                patients=self.world.patients,
                professionals=InMemoryProfessionalRepository(self.world.accounts),
                settings=settings,
                sender=self.sender,
                clock=lambda: self.world.now,
            ),
            clock=lambda: self.world.now,
        )

    def rows(self, appointment_id: str) -> list[Notification]:
        return self.world.notifications.list_for_appointment(appointment_id)
