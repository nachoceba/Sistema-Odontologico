"""Bateria de contrato de horarios y licencias (spec schedule-repository)."""

from __future__ import annotations

from datetime import date, time

import pytest

from app.domain.appointments import SlotStatus, WorkingHours, compute_slots
from app.domain.schedules.ports import TimeOffRepository, WorkingHoursRepository
from tests.contract.conftest import Refs
from tests.unit.domain.appointments.helpers import count_by_status

BA = "America/Argentina/Buenos_Aires"
MON, TUE, WED = 0, 1, 2


def block(weekday: int, start_hour: int, end_hour: int) -> WorkingHours:
    return WorkingHours(weekday=weekday, start_time=time(start_hour), end_time=time(end_hour))


# --- Tramos de horario ------------------------------------------------------------


def test_replace_then_read_returns_week_ordered_by_weekday_and_start(
    working_hours_repo: WorkingHoursRepository,
    ids: Refs,
) -> None:
    working_hours_repo.replace_for_professional(
        ids.dra_a, [block(TUE, 14, 18), block(MON, 14, 18), block(MON, 9, 13)]
    )
    assert working_hours_repo.list_for_professional(ids.dra_a) == [
        block(MON, 9, 13),
        block(MON, 14, 18),
        block(TUE, 14, 18),
    ]


def test_new_replacement_discards_previous_blocks(
    working_hours_repo: WorkingHoursRepository,
    ids: Refs,
) -> None:
    working_hours_repo.replace_for_professional(ids.dra_a, [block(MON, 9, 13), block(TUE, 9, 13)])
    working_hours_repo.replace_for_professional(ids.dra_a, [block(WED, 9, 13)])
    assert working_hours_repo.list_for_professional(ids.dra_a) == [block(WED, 9, 13)]


def test_replacing_one_professional_does_not_touch_another(
    working_hours_repo: WorkingHoursRepository,
    ids: Refs,
) -> None:
    working_hours_repo.replace_for_professional(ids.dra_a, [block(MON, 9, 13)])
    working_hours_repo.replace_for_professional(ids.dr_b, [block(MON, 9, 13)])
    working_hours_repo.replace_for_professional(ids.dra_a, [])
    assert working_hours_repo.list_for_professional(ids.dra_a) == []
    assert working_hours_repo.list_for_professional(ids.dr_b) == [block(MON, 9, 13)]


def test_professional_without_schedule_reads_empty(
    working_hours_repo: WorkingHoursRepository,
    ids: Refs,
) -> None:
    assert working_hours_repo.list_for_professional(ids.dr_b) == []


# --- Licencias --------------------------------------------------------------------


def test_add_and_list_time_off_with_reason_ordered_by_start(
    time_off_repo: TimeOffRepository,
    ids: Refs,
) -> None:
    congress = time_off_repo.add(ids.dra_a, date(2026, 10, 12), date(2026, 10, 16), "Congreso")
    single = time_off_repo.add(ids.dra_a, date(2026, 10, 5), date(2026, 10, 5))
    listed = time_off_repo.list_for_professional(ids.dra_a)
    assert [entry.id for entry in listed] == [single.id, congress.id]
    assert single.id != congress.id
    assert [entry.reason for entry in listed] == [None, "Congreso"]
    assert (listed[1].professional_id, listed[1].starts_on, listed[1].ends_on) == (
        ids.dra_a,
        date(2026, 10, 12),
        date(2026, 10, 16),
    )


def test_time_off_of_another_professional_does_not_appear(
    time_off_repo: TimeOffRepository,
    ids: Refs,
) -> None:
    time_off_repo.add(ids.dr_b, date(2026, 10, 12), date(2026, 10, 16))
    assert time_off_repo.list_for_professional(ids.dra_a) == []


def test_overlapping_time_off_entries_are_both_saved(
    time_off_repo: TimeOffRepository,
    ids: Refs,
) -> None:
    time_off_repo.add(ids.dra_a, date(2026, 10, 12), date(2026, 10, 16))
    time_off_repo.add(ids.dra_a, date(2026, 10, 14), date(2026, 10, 20))
    assert len(time_off_repo.list_for_professional(ids.dra_a)) == 2


def test_time_off_with_end_before_start_raises_and_saves_nothing(
    time_off_repo: TimeOffRepository,
    ids: Refs,
) -> None:
    with pytest.raises(ValueError):
        time_off_repo.add(ids.dra_a, date(2026, 10, 16), date(2026, 10, 12))
    assert time_off_repo.list_for_professional(ids.dra_a) == []


# --- Integracion con compute_slots ------------------------------------------------


def test_saved_time_off_blocks_availability(
    working_hours_repo: WorkingHoursRepository,
    ids: Refs,
    time_off_repo: TimeOffRepository,
) -> None:
    working_hours_repo.replace_for_professional(ids.dra_a, [block(MON, 9, 13)])
    time_off_repo.add(ids.dra_a, date(2026, 10, 5), date(2026, 10, 5))
    slots = compute_slots(
        professional_id=ids.dra_a,
        day=date(2026, 10, 5),
        working_hours=working_hours_repo.list_for_professional(ids.dra_a),
        time_off=[e.to_time_off() for e in time_off_repo.list_for_professional(ids.dra_a)],
        existing_appointments=[],
    )
    assert slots
    assert count_by_status(slots) == {SlotStatus.OUTSIDE_HOURS.name: len(slots)}


# --- Borrar licencias (C-07, P-4) ---------------------------------------------------


def test_delete_own_time_off_removes_only_that_entry(
    time_off_repo: TimeOffRepository,
    ids: Refs,
) -> None:
    congress = time_off_repo.add(ids.dra_a, date(2026, 10, 12), date(2026, 10, 16), "Congreso")
    single = time_off_repo.add(ids.dra_a, date(2026, 10, 5), date(2026, 10, 5))
    assert time_off_repo.delete(ids.dra_a, congress.id) is True
    assert [e.id for e in time_off_repo.list_for_professional(ids.dra_a)] == [single.id]
    assert time_off_repo.delete(ids.dra_a, congress.id) is False


def test_delete_with_another_professional_does_not_remove_the_entry(
    time_off_repo: TimeOffRepository,
    ids: Refs,
) -> None:
    entry = time_off_repo.add(ids.dr_b, date(2026, 10, 12), date(2026, 10, 16))
    assert time_off_repo.delete(ids.dra_a, entry.id) is False
    assert [e.id for e in time_off_repo.list_for_professional(ids.dr_b)] == [entry.id]


@pytest.mark.parametrize("time_off_id", ["00000000-0000-4000-8000-000000000000", "no-es-un-uuid"])
def test_delete_unknown_or_malformed_id_returns_false(
    time_off_repo: TimeOffRepository,
    ids: Refs,
    time_off_id: str,
) -> None:
    keep = time_off_repo.add(ids.dra_a, date(2026, 10, 12), date(2026, 10, 16))
    assert time_off_repo.delete(ids.dra_a, time_off_id) is False
    assert [e.id for e in time_off_repo.list_for_professional(ids.dra_a)] == [keep.id]


def test_delete_time_off_gives_availability_back(
    working_hours_repo: WorkingHoursRepository,
    ids: Refs,
    time_off_repo: TimeOffRepository,
) -> None:
    working_hours_repo.replace_for_professional(ids.dra_a, [block(MON, 9, 13)])
    entry = time_off_repo.add(ids.dra_a, date(2026, 10, 5), date(2026, 10, 5))
    assert time_off_repo.delete(ids.dra_a, entry.id) is True
    slots = compute_slots(
        professional_id=ids.dra_a,
        day=date(2026, 10, 5),
        working_hours=working_hours_repo.list_for_professional(ids.dra_a),
        time_off=[e.to_time_off() for e in time_off_repo.list_for_professional(ids.dra_a)],
        existing_appointments=[],
    )
    free = [s for s in slots if s.status == SlotStatus.FREE]
    assert len(free) == 8
    assert working_hours_repo.list_for_professional(ids.dra_a) == [block(MON, 9, 13)]
