"""Reglas compartidas por validate_appointment y compute_slots (una sola fuente).

Funciones puras, solo libreria estandar. Evitan que la validacion de un turno nuevo
y el calculo de franjas diverjan (design D-8).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, time

from app.domain.appointments.types import AppointmentStatus, ExistingAppointment


def minutes_of_day(moment: time) -> int:
    """Minutos desde las 00:00 de una hora local."""
    return moment.hour * 60 + moment.minute


def is_on_grid(minutes: int, block_start_minutes: int, slot_minutes: int) -> bool:
    """RN-TU-02: la grilla se cuenta desde el inicio del tramo en pasos de slot_minutes."""
    return (minutes - block_start_minutes) % slot_minutes == 0


def ranges_overlap(
    start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime
) -> bool:
    """Rangos semiabiertos [inicio, fin): tocarse en el borde no es superponerse."""
    return start_a < end_b and start_b < end_a


def overlaps_scheduled(
    professional_id: str,
    starts_at: datetime,
    ends_at: datetime,
    existing_appointments: Sequence[ExistingAppointment],
) -> bool:
    """RN-TU-01: solo cuentan los turnos scheduled del mismo profesional."""
    return any(
        existing.professional_id == professional_id
        and existing.status == AppointmentStatus.SCHEDULED
        and ranges_overlap(starts_at, ends_at, existing.starts_at, existing.ends_at)
        for existing in existing_appointments
    )
