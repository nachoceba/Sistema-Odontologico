"""Reglas compartidas por validate_appointment y compute_slots (una sola fuente).

Funciones puras, solo libreria estandar. Evitan que la validacion de un turno nuevo
y el calculo de franjas diverjan (design D-8).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, time

from app.core.timezone import to_local
from app.domain.appointments.types import (
    Appointment,
    AppointmentStatus,
    ExistingAppointment,
    WorkingHours,
)


def minutes_of_day(moment: time) -> int:
    """Minutos desde las 00:00 de una hora local."""
    return moment.hour * 60 + moment.minute


def is_on_grid(minutes: int, block_start_minutes: int, slot_minutes: int) -> bool:
    """RN-TU-02: la grilla se cuenta desde el inicio del tramo en pasos de slot_minutes."""
    return (minutes - block_start_minutes) % slot_minutes == 0


def ranges_overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
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


def has_sub_minute_precision(instant: datetime) -> bool:
    """P-12b: un inicio con segundos o fracciones se rechaza (la grilla solo mira minutos)."""
    return instant.second != 0 or instant.microsecond != 0


def patient_has_overlap(
    patient_id: str,
    starts_at: datetime,
    ends_at: datetime,
    existing: Sequence[Appointment],
    *,
    exclude_id: str | None = None,
) -> bool:
    """P-3 (DD-63): el paciente ya tiene un scheduled superpuesto (de cualquier profesional).

    ``exclude_id`` deja afuera el propio turno al reprogramar.
    """
    return any(
        appointment.patient_id == patient_id
        and appointment.id != exclude_id
        and appointment.status == AppointmentStatus.SCHEDULED
        and ranges_overlap(starts_at, ends_at, appointment.starts_at, appointment.ends_at)
        for appointment in existing
    )


def fits_in_working_hours(
    local_start: datetime,
    ends_at: datetime,
    working_hours: Sequence[WorkingHours],
    timezone: str,
) -> bool:
    """RN-TU-03: inicio y fin dentro de un mismo tramo del dia de la semana local.

    Fuente unica del criterio "entra en un tramo": la usan validate_appointment y la
    deteccion de conflictos de horario (RN-HO-04) para que nunca diverjan.
    """
    local_end = to_local(ends_at, timezone)
    if local_end.date() != local_start.date():
        return False
    return any(
        block.weekday == local_start.weekday()
        and block.start_time <= local_start.time()
        and local_end.time() <= block.end_time
        for block in working_hours
    )
