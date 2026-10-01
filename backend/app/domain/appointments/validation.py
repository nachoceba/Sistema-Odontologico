"""Validacion pura de la creacion de un turno (sin I/O, sin leer el reloj)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.appointments.types import (
    AppointmentStatus,
    ExistingAppointment,
    RejectionReason,
    TimeOff,
    ValidationResult,
    WorkingHours,
)


def validate_appointment(
    *,
    professional_id: str,
    starts_at: datetime,
    now: datetime,
    working_hours: Sequence[WorkingHours],
    time_off: Sequence[TimeOff],
    existing_appointments: Sequence[ExistingAppointment],
    slot_minutes: int = 30,
    timezone: str = "America/Argentina/Buenos_Aires",
    min_notice_hours: int = 6,
) -> ValidationResult:
    """Decide si se puede crear un turno de ``slot_minutes`` para un profesional.

    Devuelve un resultado (no lanza por motivos de negocio) con un unico motivo:
    el de la primera regla incumplida, en este orden fijo:

    1. Anticipacion minima (RN-TU-12; cubre RN-TU-04, turnos en el pasado).
    2. Grilla de slots anclada al inicio de cada tramo (RN-TU-02).
    3. Turno completo dentro del horario de trabajo (RN-TU-03).
    4. Fuera de licencias, dias completos inclusivos (RN-TU-03, RN-HO-03).
    5. Sin solapamiento con turnos scheduled del mismo profesional (RN-TU-01).

    Contrato: ``starts_at`` y ``now`` son datetime con zona (UTC); si no, ValueError
    (error de programacion). ``working_hours`` y ``time_off`` ya vienen filtrados del
    profesional; ``existing_appointments`` puede traer varios profesionales y se
    filtra aca. Horario y licencia se evaluan en hora local (``timezone``);
    anticipacion y solapamiento, en instantes UTC. ``now`` se inyecta: el dominio
    nunca lee el reloj.
    """
    if starts_at.tzinfo is None or now.tzinfo is None:
        raise ValueError("starts_at y now deben ser datetime con zona horaria (UTC)")
    if _has_insufficient_notice(starts_at, now, min_notice_hours):
        return ValidationResult.reject(RejectionReason.INSUFFICIENT_NOTICE)
    local_start = _to_local(starts_at, timezone)
    if _is_off_grid(local_start, working_hours, slot_minutes):
        return ValidationResult.reject(RejectionReason.OFF_GRID)
    ends_at = starts_at + timedelta(minutes=slot_minutes)
    if not _fits_in_working_hours(local_start, ends_at, working_hours, timezone):
        return ValidationResult.reject(RejectionReason.OUTSIDE_WORKING_HOURS)
    if _is_on_time_off(local_start, time_off):
        return ValidationResult.reject(RejectionReason.PROFESSIONAL_TIME_OFF)
    if _overlaps_existing(professional_id, starts_at, ends_at, existing_appointments):
        return ValidationResult.reject(RejectionReason.OVERLAPS_EXISTING)
    return ValidationResult.accept(ends_at)


def _has_insufficient_notice(
    starts_at: datetime, now: datetime, min_notice_hours: int
) -> bool:
    """RN-TU-12: el inicio debe ser >= now + anticipacion minima (igualdad se acepta)."""
    return starts_at < now + timedelta(hours=min_notice_hours)


def _to_local(instant: datetime, timezone: str) -> datetime:
    return instant.astimezone(ZoneInfo(timezone))


def _blocks_containing_start(
    local_start: datetime, working_hours: Sequence[WorkingHours]
) -> list[WorkingHours]:
    """Tramos del dia de la semana local que contienen el inicio: [start_time, end_time)."""
    return [
        block
        for block in working_hours
        if block.weekday == local_start.weekday()
        and block.start_time <= local_start.time() < block.end_time
    ]


def _minutes_of_day(moment: time) -> int:
    return moment.hour * 60 + moment.minute


def _is_off_grid(
    local_start: datetime, working_hours: Sequence[WorkingHours], slot_minutes: int
) -> bool:
    """RN-TU-02: grilla anclada al inicio de cada tramo. Sin tramo -> no es tema de grilla."""
    for block in _blocks_containing_start(local_start, working_hours):
        offset = _minutes_of_day(local_start.time()) - _minutes_of_day(block.start_time)
        if offset % slot_minutes != 0:
            return True
    return False


def _fits_in_working_hours(
    local_start: datetime,
    ends_at: datetime,
    working_hours: Sequence[WorkingHours],
    timezone: str,
) -> bool:
    """RN-TU-03: inicio y fin dentro de un mismo tramo del dia de la semana local."""
    local_end = _to_local(ends_at, timezone)
    if local_end.date() != local_start.date():
        return False
    return any(
        block.weekday == local_start.weekday()
        and block.start_time <= local_start.time()
        and local_end.time() <= block.end_time
        for block in working_hours
    )


def _is_on_time_off(local_start: datetime, time_off: Sequence[TimeOff]) -> bool:
    """RN-TU-03 / RN-HO-03: la fecha local cae en una licencia [starts_on, ends_on] inclusiva."""
    return any(
        leave.starts_on <= local_start.date() <= leave.ends_on for leave in time_off
    )


def _ranges_overlap(
    start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime
) -> bool:
    """Rangos semiabiertos [inicio, fin): tocarse en el borde no es superponerse."""
    return start_a < end_b and start_b < end_a


def _overlaps_existing(
    professional_id: str,
    starts_at: datetime,
    ends_at: datetime,
    existing_appointments: Sequence[ExistingAppointment],
) -> bool:
    """RN-TU-01: solo cuentan los turnos scheduled del mismo profesional."""
    return any(
        existing.professional_id == professional_id
        and existing.status == AppointmentStatus.SCHEDULED
        and _ranges_overlap(starts_at, ends_at, existing.starts_at, existing.ends_at)
        for existing in existing_appointments
    )
