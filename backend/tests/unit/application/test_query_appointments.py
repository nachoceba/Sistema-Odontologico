"""Consultas de agenda: detalle, listado por profesional y franjas de un dia."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.application.appointments import (
    book_appointment,
    day_slots,
    get_appointment,
    list_appointments,
)
from app.domain.appointments import AppointmentStatus, SlotStatus
from app.domain.appointments.errors import AppointmentNotFoundError, ProfessionalNotFoundError
from app.domain.auth import ForbiddenError
from tests.unit.application.agenda_helpers import (
    ADMIN,
    DENTIST_A,
    DENTIST_NO_FILE,
    PROF_A,
    PROF_B,
    RECEPTION,
    World,
)
from tests.unit.domain.appointments.helpers import local, monday

MONDAY = date(2026, 10, 5)
NIL_APPOINTMENT = "no-existe"


# --- Detalle ---------------------------------------------------------------------------------


def test_reception_and_admin_read_any_appointment() -> None:
    world = World()
    own = world.seed(monday(10), professional_id=PROF_A)
    other = world.seed(monday(10), patient_id="pac-2", professional_id=PROF_B)

    assert get_appointment(world.deps(), RECEPTION, own.id) == own
    assert get_appointment(world.deps(), ADMIN, other.id) == other


def test_a_dentist_reads_their_own_appointment() -> None:
    world = World()
    own = world.seed(monday(10), professional_id=PROF_A)
    assert get_appointment(world.deps(), DENTIST_A, own.id) == own


def test_a_dentist_cannot_read_another_professionals_appointment() -> None:
    world = World()
    foreign = world.seed(monday(10), professional_id=PROF_B)
    with pytest.raises(ForbiddenError):
        get_appointment(world.deps(), DENTIST_A, foreign.id)


def test_a_dentist_without_a_file_cannot_read_any_appointment() -> None:
    world = World()
    own = world.seed(monday(10), professional_id=PROF_A)
    with pytest.raises(ForbiddenError):
        get_appointment(world.deps(), DENTIST_NO_FILE, own.id)


def test_an_unknown_appointment_is_not_found_for_every_role() -> None:
    world = World()
    for principal in (ADMIN, RECEPTION, DENTIST_A):
        with pytest.raises(AppointmentNotFoundError):
            get_appointment(world.deps(), principal, NIL_APPOINTMENT)


# --- Listado ---------------------------------------------------------------------------------


def test_reception_lists_the_week_with_every_status_ordered_by_start() -> None:
    world = World()
    late = world.seed(monday(11), patient_id="pac-2")
    cancelled = world.seed(monday(9))
    world.appointments.change_status(cancelled.id, AppointmentStatus.CANCELLED, "aviso")
    done = world.seed(monday(10))
    world.appointments.change_status(done.id, AppointmentStatus.COMPLETED)
    outside = world.seed(monday(10) + timedelta(days=8), patient_id="pac-2")

    listed = list_appointments(
        world.deps(), RECEPTION, PROF_A, local(2026, 10, 5, 0), local(2026, 10, 12, 0)
    )

    assert [a.id for a in listed] == [cancelled.id, done.id, late.id]
    assert outside.id not in [a.id for a in listed]


def test_a_dentist_lists_their_own_agenda_but_not_another() -> None:
    world = World()
    world.seed(monday(10), professional_id=PROF_A)
    world.seed(monday(10), patient_id="pac-2", professional_id=PROF_B)
    start, end = local(2026, 10, 5, 0), local(2026, 10, 6, 0)

    assert len(list_appointments(world.deps(), DENTIST_A, PROF_A, start, end)) == 1
    with pytest.raises(ForbiddenError):
        list_appointments(world.deps(), DENTIST_A, PROF_B, start, end)
    with pytest.raises(ForbiddenError):
        list_appointments(world.deps(), DENTIST_NO_FILE, PROF_A, start, end)


def test_an_appointment_crossing_the_range_start_is_listed() -> None:
    world = World()
    crossing = world.seed(monday(9, 45))  # 09:45 a 10:15
    listed = list_appointments(world.deps(), RECEPTION, PROF_A, monday(10), monday(12))
    assert [a.id for a in listed] == [crossing.id]


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (local(2026, 10, 5, 0), local(2026, 10, 5, 0)),
        (local(2026, 10, 6, 0), local(2026, 10, 5, 0)),
        (local(2026, 10, 5, 0), local(2026, 10, 5, 0) + timedelta(days=32)),
    ],
    ids=["empty", "inverted", "too-long"],
)
def test_an_invalid_range_is_rejected_as_a_bad_request(start: datetime, end: datetime) -> None:
    world = World()
    with pytest.raises(ValueError):
        list_appointments(world.deps(), RECEPTION, PROF_A, start, end)


def test_a_range_of_exactly_31_days_is_accepted() -> None:
    world = World()
    start = local(2026, 10, 5, 0)
    assert (
        list_appointments(world.deps(), RECEPTION, PROF_A, start, start + timedelta(days=31)) == []
    )


# --- Franjas ---------------------------------------------------------------------------------


def _by_start(world: World, professional_id: str = PROF_A) -> dict[str, SlotStatus]:
    slots = day_slots(world.deps(), RECEPTION, professional_id, MONDAY)
    return {slot.starts_at.isoformat(): slot.status for slot in slots}


def test_day_with_one_appointment_shows_free_busy_and_outside_hours() -> None:
    world = World()
    world.seed(monday(10))

    statuses = _by_start(world)

    assert statuses[monday(9).isoformat()] is SlotStatus.FREE
    assert statuses[monday(9, 30).isoformat()] is SlotStatus.FREE
    assert statuses[monday(10).isoformat()] is SlotStatus.BUSY
    assert statuses[monday(10, 30).isoformat()] is SlotStatus.FREE
    assert statuses[monday(13).isoformat()] is SlotStatus.OUTSIDE_HOURS
    assert statuses[local(2026, 10, 5, 0).isoformat()] is SlotStatus.OUTSIDE_HOURS


def test_slots_ignore_other_professionals_appointments() -> None:
    world = World()
    world.seed(monday(10), patient_id="pac-2", professional_id=PROF_B)
    assert _by_start(world)[monday(10).isoformat()] is SlotStatus.FREE


def test_a_time_off_day_has_no_free_slots() -> None:
    world = World()
    world.time_off.add(PROF_A, MONDAY, MONDAY)
    assert set(_by_start(world).values()) == {SlotStatus.OUTSIDE_HOURS}


def test_slots_use_the_clinic_slot_minutes() -> None:
    world = World(slot_minutes=20)
    statuses = _by_start(world)
    assert statuses[monday(9, 20).isoformat()] is SlotStatus.FREE
    assert monday(9, 30).isoformat() not in statuses


def test_slots_for_an_unknown_professional_are_not_found() -> None:
    world = World()
    with pytest.raises(ProfessionalNotFoundError):
        day_slots(world.deps(), RECEPTION, "99999999-9999-4999-8999-999999999999", MONDAY)


def test_a_dentist_asks_only_for_their_own_slots() -> None:
    world = World()
    assert day_slots(world.deps(), DENTIST_A, PROF_A, MONDAY)
    with pytest.raises(ForbiddenError):
        day_slots(world.deps(), DENTIST_A, PROF_B, MONDAY)
    with pytest.raises(ForbiddenError):
        day_slots(world.deps(), DENTIST_NO_FILE, PROF_A, MONDAY)


def test_an_unknown_professional_is_forbidden_not_not_found_for_a_dentist() -> None:
    world = World()
    with pytest.raises(ForbiddenError):
        day_slots(world.deps(), DENTIST_A, "99999999-9999-4999-8999-999999999999", MONDAY)


def test_an_inactive_professional_still_shows_slots() -> None:
    world = World()
    world.set_professional_active(PROF_A, False)
    assert day_slots(world.deps(), RECEPTION, PROF_A, MONDAY)


def test_every_free_slot_far_enough_in_the_future_can_be_booked() -> None:
    world = World()
    world.seed(monday(10))
    free = [
        s for s in day_slots(world.deps(), RECEPTION, PROF_A, MONDAY) if s.status is SlotStatus.FREE
    ]
    assert len(free) > 5

    for slot in free:
        fresh = World()
        fresh.seed(monday(10))
        saved = book_appointment(
            fresh.deps(),
            RECEPTION,
            patient_id="pac-2",
            professional_id=PROF_A,
            starts_at=slot.starts_at,
        )
        assert saved.ends_at == slot.ends_at
