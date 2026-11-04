"""Turnos en conflicto con el horario o las licencias (RN-HO-04). Funcion pura.

No lee el reloj ni guarda nada: ``now`` llega como dato. Usa el mismo criterio de
"entra en un tramo" que validate_appointment (rules.fits_in_working_hours).
Este modulo no se re-exporta desde ``schedules/__init__`` para no crear un ciclo
con ``app.domain.appointments``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.core.timezone import to_local
from app.domain.appointments.rules import fits_in_working_hours
from app.domain.appointments.types import Appointment, AppointmentStatus, TimeOff, WorkingHours
from app.domain.schedules.time_off import is_date_in_time_off


class ConflictReason(Enum):
    OUTSIDE_WORKING_HOURS = "OUTSIDE_WORKING_HOURS"
    TIME_OFF = "TIME_OFF"


@dataclass(frozen=True)
class ScheduleConflict:
    appointment: Appointment
    reason: ConflictReason


def find_schedule_conflicts(
    *,
    professional_id: str,
    working_hours: Sequence[WorkingHours],
    time_off: Sequence[TimeOff],
    appointments: Sequence[Appointment],
    now: datetime,
    timezone: str,
) -> list[ScheduleConflict]:
    """Turnos scheduled futuros del profesional fuera del horario o en licencia.

    Contrato: ``now`` con zona (si no, ValueError, DD-18). Se ordena por inicio y id.
    Si se cumplen los dos motivos, gana ``TIME_OFF``. La grilla no cuenta (P-3).
    """
    if now.tzinfo is None:
        raise ValueError("now debe ser un datetime con zona horaria (UTC)")
    conflicts: list[ScheduleConflict] = []
    for appointment in appointments:
        if (
            appointment.professional_id != professional_id
            or appointment.status != AppointmentStatus.SCHEDULED
            or appointment.starts_at <= now
        ):
            continue
        local_start = to_local(appointment.starts_at, timezone)
        if is_date_in_time_off(local_start.date(), time_off):
            conflicts.append(ScheduleConflict(appointment, ConflictReason.TIME_OFF))
        elif not fits_in_working_hours(local_start, appointment.ends_at, working_hours, timezone):
            conflicts.append(ScheduleConflict(appointment, ConflictReason.OUTSIDE_WORKING_HOURS))
    conflicts.sort(key=lambda c: (c.appointment.starts_at, c.appointment.id))
    return conflicts
