"""Errores de dominio del repositorio de turnos. Solo libreria estandar."""

from __future__ import annotations

from datetime import datetime


class SlotTakenError(Exception):
    """El horario ya esta ocupado por otro turno scheduled del profesional."""

    code = "SLOT_TAKEN"

    def __init__(self, professional_id: str, starts_at: datetime) -> None:
        super().__init__(f"{self.code}: {professional_id} a las {starts_at.isoformat()}")
        self.professional_id = professional_id
        self.starts_at = starts_at


class AppointmentNotFoundError(Exception):
    """No existe un turno con ese identificador."""

    code = "APPOINTMENT_NOT_FOUND"

    def __init__(self, appointment_id: str) -> None:
        super().__init__(f"{self.code}: {appointment_id}")
        self.appointment_id = appointment_id
