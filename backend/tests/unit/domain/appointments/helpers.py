"""Helpers y datos de ejemplo comunes a los tests de validacion de turnos."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from app.domain.appointments import (
    AppointmentStatus,
    ExistingAppointment,
    Slot,
    TimeOff,
    ValidationResult,
    WorkingHours,
    validate_appointment,
)

BA = ZoneInfo("America/Argentina/Buenos_Aires")
MONDAY = 0
TUESDAY = 1


def local(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    """Instante UTC correspondiente a una hora local de Buenos Aires."""
    return datetime(year, month, day, hour, minute, tzinfo=BA).astimezone(UTC)


def monday(hour: int, minute: int = 0) -> datetime:
    """Lunes 5 de octubre de 2026 a la hora local indicada (en UTC)."""
    return local(2026, 10, 5, hour, minute)


NOW = local(2026, 10, 3, 10, 0)  # sabado 3 de octubre de 2026, 10:00 local

DRA_A_HOURS: list[WorkingHours] = [
    WorkingHours(weekday=MONDAY, start_time=time(9, 0), end_time=time(13, 0)),
    WorkingHours(weekday=MONDAY, start_time=time(14, 0), end_time=time(18, 0)),
]
DR_B_HOURS: list[WorkingHours] = [
    WorkingHours(weekday=MONDAY, start_time=time(9, 0), end_time=time(13, 0)),
]


def appointment(
    professional_id: str,
    starts_at: datetime,
    ends_at: datetime,
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
) -> ExistingAppointment:
    return ExistingAppointment(
        professional_id=professional_id,
        starts_at=starts_at,
        ends_at=ends_at,
        status=status,
    )


def validate(
    starts_at: datetime,
    *,
    professional_id: str = "dra-a",
    now: datetime = NOW,
    working_hours: Sequence[WorkingHours] = tuple(DRA_A_HOURS),
    time_off: Sequence[TimeOff] = (),
    existing_appointments: Sequence[ExistingAppointment] = (),
    min_notice_hours: int = 6,
) -> ValidationResult:
    return validate_appointment(
        professional_id=professional_id,
        starts_at=starts_at,
        now=now,
        working_hours=working_hours,
        time_off=time_off,
        existing_appointments=existing_appointments,
        min_notice_hours=min_notice_hours,
    )


def slot_at(
    slots: Sequence[Slot], hour: int, minute: int = 0, day: tuple[int, int, int] = (2026, 10, 5)
) -> Slot:
    """Franja cuyo inicio es la hora local indicada (por defecto, lunes 5/10/2026)."""
    target = local(day[0], day[1], day[2], hour, minute)
    matches = [slot for slot in slots if slot.starts_at == target]
    assert len(matches) == 1, f"no hay una unica franja que empiece a {hour:02d}:{minute:02d}"
    return matches[0]


def count_by_status(slots: Sequence[Slot]) -> dict[str, int]:
    """Cantidad de franjas por nombre de estado, ej. {'FREE': 16, 'OUTSIDE_HOURS': 32}."""
    counts: dict[str, int] = {}
    for slot in slots:
        counts[slot.status.name] = counts.get(slot.status.name, 0) + 1
    return counts
