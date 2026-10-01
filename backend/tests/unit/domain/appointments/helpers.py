"""Helpers y datos de ejemplo comunes a los tests de validacion de turnos."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from app.domain.appointments import (
    AppointmentStatus,
    ExistingAppointment,
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
    return datetime(year, month, day, hour, minute, tzinfo=BA).astimezone(timezone.utc)


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
