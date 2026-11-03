"""Calculo puro de las franjas de un dia local de un profesional (sin I/O)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta

from app.core.timezone import to_utc
from app.domain.appointments.rules import (
    minutes_of_day,
    overlaps_scheduled,
)
from app.domain.appointments.types import (
    ExistingAppointment,
    Slot,
    SlotStatus,
    TimeOff,
    WorkingHours,
)
from app.domain.schedules import is_date_in_time_off

_DAY_MINUTES = 24 * 60


def compute_slots(
    *,
    professional_id: str,
    day: date,
    working_hours: Sequence[WorkingHours],
    time_off: Sequence[TimeOff],
    existing_appointments: Sequence[ExistingAppointment],
    slot_minutes: int = 30,
    timezone: str = "America/Argentina/Buenos_Aires",
) -> list[Slot]:
    """Franjas del dia local completo (00:00 a 24:00) de un profesional.

    Precedencia de estados (un unico punto, ``_classify``): OUTSIDE_HOURS (fuera de
    tramo, resto parcial de un tramo o dia de licencia) > BUSY (turno scheduled del
    mismo profesional que se solapa) > FREE. No informa conflictos (RN-HO-04):
    eso es de C-07; C-09 muestra los turnos con su propia consulta. No aplica la
    anticipacion minima (RN-TU-12): la resuelve validate_appointment.

    Contrato: ``day`` es la fecha LOCAL del consultorio (``date``, no ``datetime``);
    ``slot_minutes`` > 0; si no, ValueError (error de programacion). ``working_hours``
    y ``time_off`` ya vienen filtrados del profesional y los tramos se asumen validos;
    ``existing_appointments`` puede traer varios profesionales y llega en UTC con
    zona (precondicion heredada de validate_appointment). ``timezone`` desconocida
    propaga el error de zoneinfo. Devuelve franjas contiguas con inicio y fin en UTC;
    solo las OUTSIDE_HOURS pueden durar menos de ``slot_minutes``.
    """
    _validate_inputs(day, slot_minutes)
    if is_date_in_time_off(day, time_off):
        blocks: list[WorkingHours] = []
    else:
        blocks = sorted(
            (block for block in working_hours if block.weekday == day.weekday()),
            key=lambda block: block.start_time,
        )
    result: list[Slot] = []
    cursor = 0  # minutos desde las 00:00 locales
    for block in blocks:
        block_start = minutes_of_day(block.start_time)
        block_end = minutes_of_day(block.end_time)
        result += _gap_slots(day, cursor, block_start, slot_minutes, timezone)
        result += _block_slots(day, block_start, block_end, slot_minutes, timezone)
        cursor = block_end
    result += _gap_slots(day, cursor, _DAY_MINUTES, slot_minutes, timezone)
    return [_classify(slot, professional_id, existing_appointments) for slot in result]


def _validate_inputs(day: object, slot_minutes: int) -> None:
    # datetime hereda de date: se rechaza antes para no ignorar la hora en silencio.
    if isinstance(day, datetime) or not isinstance(day, date):
        raise ValueError("day debe ser una fecha (date), no una fecha y hora ni un texto")
    if slot_minutes <= 0:
        raise ValueError("slot_minutes debe ser mayor que cero")


def _classify(
    slot: Slot, professional_id: str, existing: Sequence[ExistingAppointment]
) -> Slot:
    """Unico punto de precedencia: OUTSIDE_HOURS > BUSY > FREE."""
    if slot.status is SlotStatus.OUTSIDE_HOURS:
        return slot
    if overlaps_scheduled(professional_id, slot.starts_at, slot.ends_at, existing):
        return Slot(slot.starts_at, slot.ends_at, SlotStatus.BUSY)
    return slot


def _make_slot(
    day: date, start_min: int, end_min: int, status: SlotStatus, timezone: str
) -> Slot:
    midnight = datetime.combine(day, time.min)
    return Slot(
        starts_at=to_utc(midnight + timedelta(minutes=start_min), timezone),
        ends_at=to_utc(midnight + timedelta(minutes=end_min), timezone),
        status=status,
    )


def _gap_slots(
    day: date, start_min: int, end_min: int, slot_minutes: int, timezone: str
) -> list[Slot]:
    """Franjas OUTSIDE_HOURS de un hueco, recortadas al final del hueco."""
    slots: list[Slot] = []
    cursor = start_min
    while cursor < end_min:
        stop = min(cursor + slot_minutes, end_min)
        slots.append(_make_slot(day, cursor, stop, SlotStatus.OUTSIDE_HOURS, timezone))
        cursor = stop
    return slots


def _block_slots(
    day: date, start_min: int, end_min: int, slot_minutes: int, timezone: str
) -> list[Slot]:
    """Franjas de un tramo, ancladas a su inicio; el resto parcial es OUTSIDE_HOURS."""
    slots: list[Slot] = []
    cursor = start_min
    while cursor + slot_minutes <= end_min:
        slots.append(
            _make_slot(day, cursor, cursor + slot_minutes, SlotStatus.FREE, timezone)
        )
        cursor += slot_minutes
    if cursor < end_min:
        slots.append(_make_slot(day, cursor, end_min, SlotStatus.OUTSIDE_HOURS, timezone))
    return slots
