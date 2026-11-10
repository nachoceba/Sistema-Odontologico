"""Reglas puras de la reserva pendiente (DD-130, DD-132). Solo libreria estandar."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.domain.appointments.types import Appointment, AppointmentStatus


def pending_until_for(now: datetime, starts_at: datetime, hold_minutes: int) -> datetime:
    """Hasta cuando se puede confirmar: el menor entre ``now + hold`` y el inicio del turno."""
    return min(now + timedelta(minutes=hold_minutes), starts_at)


def can_confirm(appointment: Appointment, now: datetime) -> bool:
    """Un turno ``scheduled`` pendiente, que no vencio y cuyo inicio todavia no llego."""
    return (
        appointment.status is AppointmentStatus.SCHEDULED
        and appointment.pending_until is not None
        and now < appointment.pending_until
        and now < appointment.starts_at
    )
