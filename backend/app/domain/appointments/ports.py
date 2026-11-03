"""Puerto del repositorio de turnos (design D-1, D-4).

Los tipos se importan solo para anotar (TYPE_CHECKING): evita ciclos de imports (D-2).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.appointments.types import (
        Appointment,
        AppointmentStatus,
        NewAppointment,
    )


class AppointmentRepository(Protocol):
    """Contrato de persistencia de turnos.

    Toda escritura que deje un turno scheduled se rechaza con SlotTakenError si se
    superpone con otro scheduled del mismo profesional (RN-TU-01, regla dura 6).
    Un id inexistente en change_status/reschedule lanza AppointmentNotFoundError.
    Instantes sin zona o rangos invertidos lanzan ValueError.
    """

    def add(self, new: NewAppointment) -> Appointment: ...

    def get(self, appointment_id: str) -> Appointment | None: ...

    def change_status(
        self,
        appointment_id: str,
        status: AppointmentStatus,
        cancel_reason: str | None = None,
    ) -> Appointment: ...

    def reschedule(
        self, appointment_id: str, starts_at: datetime, ends_at: datetime
    ) -> Appointment: ...

    def list_for_professional(
        self, professional_id: str, start: datetime, end: datetime | None = None
    ) -> list[Appointment]:
        """Turnos de cualquier estado que se superponen con [start, end), por inicio."""
        ...

    def list_for_patient(
        self, patient_id: str, start: datetime, end: datetime | None = None
    ) -> list[Appointment]:
        """Igual que list_for_professional, filtrando por paciente."""
        ...
