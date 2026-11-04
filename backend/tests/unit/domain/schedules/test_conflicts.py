"""Conflictos de horario y licencia (RN-HO-04): spec schedule-conflicts."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta

import pytest

from app.domain.appointments.types import (
    Appointment,
    AppointmentStatus,
    TimeOff,
    WorkingHours,
)
from app.domain.schedules.conflicts import (
    ConflictReason,
    ScheduleConflict,
    find_schedule_conflicts,
)

TZ = "America/Argentina/Buenos_Aires"
DRA_A = "prof-a"
DR_B = "prof-b"
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def local(day: int, hour: int, minute: int = 0, month: int = 10) -> datetime:
    """Instante UTC de una hora local de Buenos Aires (UTC-3)."""
    return datetime(2026, month, day, hour + 3, minute, tzinfo=UTC)


def appt(
    appt_id: str,
    starts_at: datetime,
    *,
    professional_id: str = DRA_A,
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
    minutes: int = 30,
) -> Appointment:
    return Appointment(
        id=appt_id,
        patient_id="pac-1",
        professional_id=professional_id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=minutes),
        status=status,
        cancel_reason=None,
        created_by="u-1",
    )


def block(weekday: int, start: str, end: str) -> WorkingHours:
    return WorkingHours(
        weekday=weekday,
        start_time=time.fromisoformat(start),
        end_time=time.fromisoformat(end),
    )


MONDAY_MORNING = [block(0, "09:00", "12:00")]


def find(
    appointments: list[Appointment],
    working_hours: list[WorkingHours],
    time_off: list[TimeOff] | None = None,
    *,
    now: datetime = NOW,
    professional_id: str = DRA_A,
) -> list[ScheduleConflict]:
    return find_schedule_conflicts(
        professional_id=professional_id,
        working_hours=working_hours,
        time_off=time_off or [],
        appointments=appointments,
        now=now,
        timezone=TZ,
    )


def test_shortened_hours_leave_appointment_outside() -> None:
    turno = appt("t1", local(5, 12, 30))
    result = find([turno], MONDAY_MORNING)
    assert result == [
        ScheduleConflict(appointment=turno, reason=ConflictReason.OUTSIDE_WORKING_HOURS)
    ]


def test_time_off_conflicts_are_sorted_by_start() -> None:
    later = appt("t2", local(14, 15))
    earlier = appt("t1", local(14, 9))
    hours = [block(2, "08:00", "18:00")]
    result = find([later, earlier], hours, [TimeOff(date(2026, 10, 12), date(2026, 10, 16))])
    assert [(c.appointment.id, c.reason) for c in result] == [
        ("t1", ConflictReason.TIME_OFF),
        ("t2", ConflictReason.TIME_OFF),
    ]


def test_appointment_still_inside_hours_is_not_conflict() -> None:
    assert find([appt("t1", local(5, 9, 30))], MONDAY_MORNING) == []


@pytest.mark.parametrize(
    "status",
    [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW],
)
def test_non_scheduled_statuses_do_not_count(status: AppointmentStatus) -> None:
    assert find([appt("t1", local(5, 15), status=status)], MONDAY_MORNING) == []


def test_appointment_starting_exactly_now_or_in_past_does_not_count() -> None:
    now = local(5, 15)
    starting_now = appt("t1", now)
    yesterday = appt("t2", local(4, 15))
    assert find([starting_now, yesterday], MONDAY_MORNING, now=now) == []
    one_minute_before = now - timedelta(minutes=1)
    assert [
        c.appointment.id for c in find([starting_now], MONDAY_MORNING, now=one_minute_before)
    ] == ["t1"]


def test_appointment_ending_exactly_at_block_end_fits() -> None:
    assert find([appt("t1", local(5, 11, 30))], MONDAY_MORNING) == []


def test_appointment_straddling_two_blocks_is_conflict() -> None:
    hours = [block(0, "09:00", "11:15"), block(0, "11:15", "13:00")]
    result = find([appt("t1", local(5, 11, 0))], hours)
    assert [c.reason for c in result] == [ConflictReason.OUTSIDE_WORKING_HOURS]


def test_appointment_off_new_grid_but_inside_block_is_not_conflict() -> None:
    assert find([appt("t1", local(5, 10, 0))], [block(0, "09:15", "13:00")]) == []


def test_empty_week_makes_every_future_appointment_conflict() -> None:
    turnos = [appt(f"t{i}", local(5 + i, 10)) for i in range(3)]
    result = find(turnos, [])
    assert [c.reason for c in result] == [ConflictReason.OUTSIDE_WORKING_HOURS] * 3
    assert [c.appointment.id for c in result] == ["t0", "t1", "t2"]


def test_outside_hours_and_time_off_reports_time_off_once() -> None:
    turno = appt("t1", local(12, 15))
    result = find([turno], MONDAY_MORNING, [TimeOff(date(2026, 10, 12), date(2026, 10, 12))])
    assert result == [ScheduleConflict(appointment=turno, reason=ConflictReason.TIME_OFF)]


def test_weekday_is_evaluated_in_local_time() -> None:
    # 01:30 UTC del martes 6 = lunes 5 a las 22:30 local
    turno = appt("t1", datetime(2026, 10, 6, 1, 30, tzinfo=UTC))
    assert find([turno], [block(0, "20:00", "23:00")]) == []
    assert [c.appointment.id for c in find([turno], [block(1, "20:00", "23:00")])] == ["t1"]


def test_time_off_boundaries_are_inclusive_by_local_date() -> None:
    hours = [block(0, "08:00", "18:00"), block(1, "08:00", "18:00")]
    on_the_day = appt("t1", local(12, 9))
    next_day = appt("t2", local(13, 9))
    result = find([on_the_day, next_day], hours, [TimeOff(date(2026, 10, 12), date(2026, 10, 12))])
    assert [(c.appointment.id, c.reason) for c in result] == [("t1", ConflictReason.TIME_OFF)]


def test_local_midnight_start_is_inside_time_off() -> None:
    turno = appt("t1", datetime(2026, 10, 12, 3, 0, tzinfo=UTC))  # 00:00 local
    result = find(
        [turno],
        [block(0, "00:00", "02:00")],
        [TimeOff(date(2026, 10, 12), date(2026, 10, 12))],
    )
    assert [c.reason for c in result] == [ConflictReason.TIME_OFF]


def test_other_professionals_appointments_are_ignored() -> None:
    ajeno = appt("t1", local(5, 15), professional_id=DR_B)
    assert find([ajeno], MONDAY_MORNING) == []
    assert [
        c.appointment.id for c in find([replace(ajeno, professional_id=DRA_A)], MONDAY_MORNING)
    ] == ["t1"]


def test_naive_now_raises_value_error() -> None:
    with pytest.raises(ValueError):
        find([], MONDAY_MORNING, now=datetime(2026, 10, 1, 12, 0))
