"""Unidad de trabajo en memoria: copia el estado al entrar y lo restaura si hay una excepcion.

Es el doble de ``SqlAlchemyAgendaUnitOfWork`` para los tests de casos de uso (D-2).
"""

from __future__ import annotations

from types import TracebackType

from app.infrastructure.in_memory.appointments import InMemoryAppointmentRepository
from app.infrastructure.in_memory.notifications import InMemoryNotificationRepository
from app.infrastructure.in_memory.patients import InMemoryPatientRepository


class InMemoryAgendaUnitOfWork:
    def __init__(
        self,
        appointments: InMemoryAppointmentRepository,
        notifications: InMemoryNotificationRepository,
        patients: InMemoryPatientRepository | None = None,
    ) -> None:
        self.appointments = appointments
        self.notifications = notifications
        self.patients = patients if patients is not None else InMemoryPatientRepository()
        self._appointments_state = appointments.snapshot()
        self._notifications_state = notifications.snapshot()
        self._patients_state = self.patients.snapshot()

    def __enter__(self) -> InMemoryAgendaUnitOfWork:
        self._appointments_state = self.appointments.snapshot()
        self._notifications_state = self.notifications.snapshot()
        self._patients_state = self.patients.snapshot()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.appointments.restore(self._appointments_state)
            self.notifications.restore(self._notifications_state)
            self.patients.restore(self._patients_state)
