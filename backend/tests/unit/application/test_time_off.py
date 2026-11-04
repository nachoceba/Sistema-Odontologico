"""Licencias: listar, cargar y borrar (spec professional-schedule-use-cases)."""

from __future__ import annotations

from datetime import date, time

import pytest

from app.application.appointments import day_slots
from app.application.professionals import (
    add_time_off,
    delete_time_off,
    list_time_off,
)
from app.domain.appointments import SlotStatus, WorkingHours
from app.domain.appointments.errors import ProfessionalNotFoundError
from app.domain.auth import ForbiddenError
from app.domain.schedules.conflicts import ConflictReason
from app.domain.schedules.errors import InvalidTimeOffError, TimeOffNotFoundError
from tests.unit.application.agenda_helpers import (
    ADMIN,
    DENTIST_A,
    DENTIST_B,
    PROF_A,
    PROF_B,
    RECEPTION,
    World,
)
from tests.unit.domain.appointments.helpers import local

UNKNOWN = "99999999-9999-4999-8999-999999999999"
OCT_12, OCT_16 = date(2026, 10, 12), date(2026, 10, 16)


def test_add_with_reason_saves_it_and_reports_no_conflicts() -> None:
    world = World()
    saved = add_time_off(world.schedule_deps(), ADMIN, PROF_A, OCT_12, OCT_16, "Congreso")
    assert saved.conflicts == []
    entry = saved.time_off
    assert (entry.professional_id, entry.starts_on, entry.ends_on, entry.reason) == (
        PROF_A,
        OCT_12,
        OCT_16,
        "Congreso",
    )
    assert world.time_off.list_for_professional(PROF_A) == [entry]


def test_added_time_off_makes_the_day_unavailable() -> None:
    world = World()
    world.working_hours.replace_for_professional(PROF_A, [WorkingHours(2, time(9), time(13))])
    add_time_off(world.schedule_deps(), ADMIN, PROF_A, OCT_12, OCT_16)
    slots = day_slots(world.deps(), ADMIN, PROF_A, date(2026, 10, 14))
    assert {s.status for s in slots} == {SlotStatus.OUTSIDE_HOURS}


def test_time_off_over_appointments_lists_them_and_keeps_them_scheduled() -> None:
    world = World()
    world.working_hours.replace_for_professional(PROF_A, [WorkingHours(2, time(9), time(18))])
    first = world.seed(local(2026, 10, 14, 9))
    second = world.seed(local(2026, 10, 14, 15), patient_id="pac-2")
    saved = add_time_off(world.schedule_deps(), ADMIN, PROF_A, OCT_12, OCT_16)
    assert [(c.appointment.id, c.reason) for c in saved.conflicts] == [
        (first.id, ConflictReason.TIME_OFF),
        (second.id, ConflictReason.TIME_OFF),
    ]
    assert world.everything() == [first, second]


def test_end_before_start_is_rejected_and_nothing_is_saved() -> None:
    world = World()
    with pytest.raises(InvalidTimeOffError):
        add_time_off(world.schedule_deps(), ADMIN, PROF_A, OCT_16, OCT_12)
    assert world.time_off.list_for_professional(PROF_A) == []


def test_single_day_and_past_and_overlapping_time_off_are_accepted() -> None:
    world = World()
    deps = world.schedule_deps()
    add_time_off(deps, ADMIN, PROF_A, date(2026, 10, 5), date(2026, 10, 5))
    add_time_off(deps, ADMIN, PROF_A, date(2026, 9, 1), date(2026, 9, 3))
    add_time_off(deps, ADMIN, PROF_A, date(2026, 10, 5), date(2026, 10, 9))
    listed = list_time_off(deps, ADMIN, PROF_A)
    assert [(e.starts_on, e.ends_on) for e in listed] == [
        (date(2026, 9, 1), date(2026, 9, 3)),
        (date(2026, 10, 5), date(2026, 10, 5)),
        (date(2026, 10, 5), date(2026, 10, 9)),
    ]


@pytest.mark.parametrize(
    ("raw", "stored"), [("   ", None), ("", None), ("  Congreso  ", "Congreso")]
)
def test_reason_is_trimmed_and_blank_means_no_reason(raw: str, stored: str | None) -> None:
    saved = add_time_off(World().schedule_deps(), ADMIN, PROF_B, OCT_12, OCT_16, raw)
    assert saved.time_off.reason == stored


def test_reason_longer_than_500_is_a_programming_error() -> None:
    world = World()
    with pytest.raises(ValueError):
        add_time_off(world.schedule_deps(), ADMIN, PROF_A, OCT_12, OCT_16, "x" * 501)
    assert world.time_off.list_for_professional(PROF_A) == []


def test_delete_removes_the_time_off_and_gives_availability_back() -> None:
    world = World()
    world.working_hours.replace_for_professional(PROF_A, [WorkingHours(2, time(9), time(13))])
    deps = world.schedule_deps()
    entry = add_time_off(deps, ADMIN, PROF_A, OCT_12, OCT_16).time_off
    keep = add_time_off(deps, ADMIN, PROF_A, date(2026, 10, 5), date(2026, 10, 5)).time_off
    delete_time_off(deps, ADMIN, PROF_A, entry.id)
    assert list_time_off(deps, ADMIN, PROF_A) == [keep]
    slots = day_slots(world.deps(), ADMIN, PROF_A, date(2026, 10, 14))
    assert SlotStatus.FREE in {s.status for s in slots}


def test_delete_of_another_professionals_time_off_is_not_found() -> None:
    world = World()
    deps = world.schedule_deps()
    foreign = add_time_off(deps, ADMIN, PROF_B, OCT_12, OCT_16).time_off
    with pytest.raises(TimeOffNotFoundError):
        delete_time_off(deps, ADMIN, PROF_A, foreign.id)
    assert list_time_off(deps, ADMIN, PROF_B) == [foreign]


def test_delete_of_an_unknown_time_off_is_not_found() -> None:
    with pytest.raises(TimeOffNotFoundError):
        delete_time_off(World().schedule_deps(), ADMIN, PROF_A, UNKNOWN)


def test_unknown_professional_is_not_found_for_every_operation() -> None:
    deps = World().schedule_deps()
    with pytest.raises(ProfessionalNotFoundError):
        list_time_off(deps, ADMIN, UNKNOWN)
    with pytest.raises(ProfessionalNotFoundError):
        add_time_off(deps, ADMIN, UNKNOWN, OCT_12, OCT_16)
    with pytest.raises(ProfessionalNotFoundError):
        delete_time_off(deps, ADMIN, UNKNOWN, UNKNOWN)


def test_reads_are_scoped_by_role() -> None:
    world = World()
    deps = world.schedule_deps()
    entry = add_time_off(deps, ADMIN, PROF_A, OCT_12, OCT_16).time_off
    for principal in (ADMIN, RECEPTION, DENTIST_A):
        assert list_time_off(deps, principal, PROF_A) == [entry]
    with pytest.raises(ForbiddenError):
        list_time_off(deps, DENTIST_B, PROF_A)


@pytest.mark.parametrize("principal", [RECEPTION, DENTIST_A, DENTIST_B])
def test_non_admins_cannot_add_or_delete_and_nothing_changes(principal: object) -> None:
    world = World()
    deps = world.schedule_deps()
    entry = add_time_off(deps, ADMIN, PROF_A, OCT_12, OCT_16).time_off
    with pytest.raises(ForbiddenError):
        add_time_off(deps, principal, PROF_A, OCT_12, OCT_16)  # type: ignore[arg-type]
    with pytest.raises(ForbiddenError):
        delete_time_off(deps, principal, PROF_A, entry.id)  # type: ignore[arg-type]
    assert world.time_off.list_for_professional(PROF_A) == [entry]
