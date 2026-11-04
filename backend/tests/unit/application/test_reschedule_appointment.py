"""Caso de uso reprogramar un turno (spec appointment-use-cases, RN-TU-06)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.application.appointments import book_appointment, reschedule_appointment
from app.core.errors import DomainError
from app.domain.appointments import AppointmentStatus
from app.domain.appointments.errors import (
    AlreadyStartedError,
    AppointmentNotFoundError,
    AttendanceAlreadyRecordedError,
    CancelledIsFinalError,
    InsufficientNoticeError,
    OffGridError,
    OutsideWorkingHoursError,
    PatientDoubleBookedError,
    PatientInactiveError,
    ProfessionalInactiveError,
    ProfessionalTimeOffError,
    RescheduleSameTimeError,
    SlotTakenError,
)
from tests.unit.application.agenda_helpers import PROF_A, PROF_B, RECEPTION, World
from tests.unit.domain.appointments.helpers import local, monday

MONDAY_DATE = monday(10).date()


def _assert_unchanged_on_error(
    world: World, appointment_id: str, error_class: type[DomainError], starts_at: datetime
) -> None:
    before = world.appointments.get(appointment_id)
    with pytest.raises(error_class):
        reschedule_appointment(world.deps(), appointment_id, starts_at)
    assert world.appointments.get(appointment_id) == before


def test_moves_to_a_free_slot_keeping_identity_patient_professional_and_creator() -> None:
    world = World()
    original = world.seed(monday(10))

    moved = reschedule_appointment(world.deps(), original.id, monday(11))

    assert moved.id == original.id
    assert (moved.starts_at, moved.ends_at) == (monday(11), monday(11, 30))
    assert moved.patient_id == original.patient_id
    assert moved.professional_id == original.professional_id
    assert moved.created_by == original.created_by
    assert moved.status is AppointmentStatus.SCHEDULED
    assert world.appointments.get(original.id) == moved


def test_the_old_slot_becomes_free() -> None:
    world = World()
    original = world.seed(monday(10))
    reschedule_appointment(world.deps(), original.id, monday(11))

    other = book_appointment(
        world.deps(), RECEPTION, patient_id="pac-2", professional_id=PROF_A, starts_at=monday(10)
    )

    assert other.starts_at == monday(10)


def test_a_taken_new_slot_is_rejected_and_the_original_stays() -> None:
    world = World()
    original = world.seed(monday(10))
    world.seed(monday(11), patient_id="pac-2")
    _assert_unchanged_on_error(world, original.id, SlotTakenError, monday(11))


def test_insufficient_notice_on_the_new_start_is_rejected() -> None:
    world = World(now=monday(8))
    original = world.seed(monday(10) + timedelta(days=1))
    _assert_unchanged_on_error(world, original.id, InsufficientNoticeError, monday(10))


def test_moving_over_its_own_previous_slot_is_accepted_with_the_current_duration() -> None:
    world = World(slot_minutes=20)
    original = world.seed(monday(10), minutes=30)  # se agendo cuando la duracion era 30

    moved = reschedule_appointment(world.deps(), original.id, monday(10, 20))

    assert (moved.starts_at, moved.ends_at) == (monday(10, 20), monday(10, 40))


def test_the_same_time_is_rejected() -> None:
    world = World()
    original = world.seed(monday(10))
    _assert_unchanged_on_error(world, original.id, RescheduleSameTimeError, monday(10))


def test_a_started_appointment_cannot_be_rescheduled() -> None:
    world = World(now=monday(10, 5))
    original = world.seed(monday(10))
    _assert_unchanged_on_error(world, original.id, AlreadyStartedError, monday(11))


def test_attendance_and_cancelled_states_are_final() -> None:
    world = World()
    done = world.seed(monday(10))
    world.appointments.change_status(done.id, AppointmentStatus.COMPLETED)
    gone = world.seed(monday(9), patient_id="pac-2")
    world.appointments.change_status(gone.id, AppointmentStatus.CANCELLED, "aviso")

    _assert_unchanged_on_error(world, done.id, AttendanceAlreadyRecordedError, monday(11))
    _assert_unchanged_on_error(world, gone.id, CancelledIsFinalError, monday(11))


def test_a_deactivated_patient_cannot_have_the_appointment_rescheduled() -> None:
    world = World()
    original = world.seed(monday(10), patient_id="pac-2")
    world.set_patient_active("pac-2", False)
    _assert_unchanged_on_error(world, original.id, PatientInactiveError, monday(11))


def test_an_inactive_professional_cannot_receive_a_reschedule() -> None:
    world = World()
    original = world.seed(monday(10))
    world.set_professional_active(PROF_A, False)
    _assert_unchanged_on_error(world, original.id, ProfessionalInactiveError, monday(11))


def test_business_rules_of_booking_apply_to_the_new_start() -> None:
    world = World()
    original = world.seed(monday(10))
    world.time_off.add(PROF_A, MONDAY_DATE + timedelta(days=7), MONDAY_DATE + timedelta(days=7))

    _assert_unchanged_on_error(world, original.id, OffGridError, monday(11, 10))
    _assert_unchanged_on_error(world, original.id, OffGridError, monday(11) + timedelta(seconds=30))
    _assert_unchanged_on_error(world, original.id, OutsideWorkingHoursError, monday(13, 30))
    _assert_unchanged_on_error(
        world, original.id, ProfessionalTimeOffError, local(2026, 10, 12, 10)
    )


def test_the_patient_cannot_end_up_with_two_overlapping_appointments() -> None:
    world = World()
    original = world.seed(monday(10), patient_id="pac-1", professional_id=PROF_A)
    world.seed(monday(11), patient_id="pac-1", professional_id=PROF_B)
    _assert_unchanged_on_error(world, original.id, PatientDoubleBookedError, monday(11))


def test_an_unknown_appointment_is_not_found() -> None:
    world = World()
    with pytest.raises(AppointmentNotFoundError):
        reschedule_appointment(world.deps(), "no-existe", monday(11))
