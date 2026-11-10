"""Horario semanal: leer y reemplazar (spec professional-schedule-use-cases)."""

from __future__ import annotations

from datetime import date, time

import pytest

from app.application.appointments import book_appointment, day_slots
from app.application.professionals import get_working_hours, replace_working_hours
from app.domain.appointments import SlotStatus, WorkingHours
from app.domain.appointments.errors import (
    OutsideWorkingHoursError,
    ProfessionalNotFoundError,
    SlotTakenError,
)
from app.domain.auth import ForbiddenError
from app.domain.schedules.conflicts import ConflictReason
from app.domain.schedules.errors import InvalidWorkingHoursError
from app.domain.schedules.validation import ScheduleProblemCode
from tests.unit.application.agenda_helpers import (
    ADMIN,
    DENTIST_A,
    DENTIST_B,
    PROF_A,
    PROF_B,
    RECEPTION,
    World,
)
from tests.unit.domain.appointments.helpers import DR_B_HOURS, DRA_A_HOURS, local, monday

UNKNOWN = "99999999-9999-4999-8999-999999999999"


def block(weekday: int, start: str, end: str) -> WorkingHours:
    return WorkingHours(weekday, time.fromisoformat(start), time.fromisoformat(end))


# --- Leer -------------------------------------------------------------------------------------


def test_read_returns_the_blocks_ordered_and_scoped_by_role() -> None:
    world = World()
    world.working_hours.replace_for_professional(
        PROF_A,
        [block(2, "09:00", "10:00"), block(0, "14:00", "18:00"), block(0, "09:00", "13:00")],
    )
    expected = [block(0, "09:00", "13:00"), block(0, "14:00", "18:00"), block(2, "09:00", "10:00")]
    deps = world.schedule_deps()
    for principal in (ADMIN, RECEPTION, DENTIST_A):
        assert get_working_hours(deps, principal, PROF_A) == expected


def test_a_dentist_cannot_read_another_professionals_hours() -> None:
    with pytest.raises(ForbiddenError):
        get_working_hours(World().schedule_deps(), DENTIST_A, PROF_B)


def test_reading_an_unknown_professional_is_not_found() -> None:
    with pytest.raises(ProfessionalNotFoundError):
        get_working_hours(World().schedule_deps(), ADMIN, UNKNOWN)


# --- Reemplazar -------------------------------------------------------------------------------


def test_replace_saves_several_blocks_per_day_sorted_without_conflicts() -> None:
    world = World()
    new_week = [block(1, "09:00", "13:00"), block(0, "14:00", "18:00"), block(0, "09:00", "13:00")]
    saved = replace_working_hours(world.schedule_deps(), ADMIN, PROF_A, new_week)
    expected = [block(0, "09:00", "13:00"), block(0, "14:00", "18:00"), block(1, "09:00", "13:00")]
    assert saved.blocks == expected
    assert saved.conflicts == []
    assert world.working_hours.list_for_professional(PROF_A) == expected
    assert world.working_hours.list_for_professional(PROF_B) == DR_B_HOURS


def test_overlapping_blocks_are_rejected_and_nothing_changes() -> None:
    world = World()
    with pytest.raises(InvalidWorkingHoursError) as raised:
        replace_working_hours(
            world.schedule_deps(),
            ADMIN,
            PROF_A,
            [block(0, "09:00", "13:00"), block(0, "12:00", "15:00")],
        )
    assert [(p.code, p.block_indexes) for p in raised.value.problems] == [
        (ScheduleProblemCode.OVERLAPPING_BLOCKS, (0, 1))
    ]
    assert world.working_hours.list_for_professional(PROF_A) == DRA_A_HOURS


def test_start_after_end_and_weekday_seven_are_rejected_and_nothing_changes() -> None:
    world = World()
    deps = world.schedule_deps()
    with pytest.raises(InvalidWorkingHoursError) as inverted:
        replace_working_hours(deps, ADMIN, PROF_A, [block(1, "18:00", "09:00")])
    assert [p.code for p in inverted.value.problems] == [ScheduleProblemCode.START_NOT_BEFORE_END]
    with pytest.raises(InvalidWorkingHoursError) as bad_day:
        replace_working_hours(deps, ADMIN, PROF_B, [block(7, "09:00", "10:00")])
    assert [p.code for p in bad_day.value.problems] == [ScheduleProblemCode.INVALID_WEEKDAY]
    assert world.working_hours.list_for_professional(PROF_A) == DRA_A_HOURS
    assert world.working_hours.list_for_professional(PROF_B) == DR_B_HOURS


def test_shortening_the_hours_lists_the_affected_appointment_without_touching_it() -> None:
    world = World()
    turno = world.seed(monday(16))
    saved = replace_working_hours(
        world.schedule_deps(), ADMIN, PROF_A, [block(0, "09:00", "13:00")]
    )
    assert [(c.appointment, c.reason) for c in saved.conflicts] == [
        (turno, ConflictReason.OUTSIDE_WORKING_HOURS)
    ]
    assert world.everything() == [turno]


def test_emptying_the_week_lists_every_future_appointment() -> None:
    world = World()
    first = world.seed(monday(10), professional_id=PROF_B)
    second = world.seed(monday(11), patient_id="pac-2", professional_id=PROF_B)
    saved = replace_working_hours(world.schedule_deps(), ADMIN, PROF_B, [])
    assert [c.appointment.id for c in saved.conflicts] == [first.id, second.id]
    assert world.working_hours.list_for_professional(PROF_B) == []
    slots = day_slots(world.deps(), ADMIN, PROF_B, date(2026, 10, 5))
    assert {s.status for s in slots} == {SlotStatus.OUTSIDE_HOURS}


def test_conflicts_include_existing_time_off() -> None:
    world = World()
    turno = world.seed(monday(10))
    world.time_off.add(PROF_A, date(2026, 10, 5), date(2026, 10, 5))
    saved = replace_working_hours(
        world.schedule_deps(), ADMIN, PROF_A, [block(0, "09:00", "13:00")]
    )
    assert [(c.appointment, c.reason) for c in saved.conflicts] == [
        (turno, ConflictReason.TIME_OFF)
    ]


def test_the_new_hours_apply_immediately_to_booking_and_slots() -> None:
    world = World()
    wednesday_nine = local(2026, 10, 7, 9)
    with pytest.raises(OutsideWorkingHoursError):
        book_appointment(
            world.deps(),
            RECEPTION,
            patient_id="pac-1",
            professional_id=PROF_A,
            treatment_id=world.treatment_id,
            starts_at=wednesday_nine,
        )
    replace_working_hours(
        world.schedule_deps(), ADMIN, PROF_A, [*DRA_A_HOURS, block(2, "09:00", "13:00")]
    )
    booked = book_appointment(
        world.deps(),
        RECEPTION,
        patient_id="pac-1",
        professional_id=PROF_A,
        treatment_id=world.treatment_id,
        starts_at=wednesday_nine,
    )
    assert booked.starts_at == wednesday_nine
    slots = day_slots(world.deps(), RECEPTION, PROF_A, date(2026, 10, 7))
    assert SlotStatus.FREE in {s.status for s in slots}


def test_changing_the_hours_does_not_allow_overlapping_appointments() -> None:
    world = World()
    existing = world.seed(monday(10))
    saved = replace_working_hours(
        world.schedule_deps(), ADMIN, PROF_A, [block(0, "10:00", "14:00")]
    )
    assert saved.conflicts == []
    with pytest.raises(SlotTakenError):
        book_appointment(
            world.deps(),
            RECEPTION,
            patient_id="pac-2",
            professional_id=PROF_A,
            treatment_id=world.treatment_id,
            starts_at=monday(10),
        )
    assert world.everything() == [existing]


def test_replacing_for_an_unknown_professional_saves_nothing() -> None:
    world = World()
    with pytest.raises(ProfessionalNotFoundError):
        replace_working_hours(world.schedule_deps(), ADMIN, UNKNOWN, [block(0, "09:00", "10:00")])
    assert world.working_hours.list_for_professional(UNKNOWN) == []


def test_an_inactive_professional_accepts_the_change() -> None:
    world = World()
    world.set_professional_active(PROF_B, False)
    saved = replace_working_hours(
        world.schedule_deps(), ADMIN, PROF_B, [block(3, "09:00", "10:00")]
    )
    assert saved.blocks == [block(3, "09:00", "10:00")]


@pytest.mark.parametrize("principal", [RECEPTION, DENTIST_A, DENTIST_B])
def test_non_admins_cannot_replace_hours_and_nothing_changes(principal: object) -> None:
    world = World()
    with pytest.raises(ForbiddenError):
        replace_working_hours(
            world.schedule_deps(),
            principal,  # type: ignore[arg-type]
            PROF_A,
            [block(0, "09:00", "10:00")],
        )
    assert world.working_hours.list_for_professional(PROF_A) == DRA_A_HOURS
