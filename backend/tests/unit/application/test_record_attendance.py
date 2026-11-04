"""Caso de uso marcar atencion (spec appointment-use-cases, RN-TU-07, DD-22, DD-23)."""

from __future__ import annotations

import pytest

from app.application.appointments import record_attendance
from app.domain.appointments import AppointmentStatus
from app.domain.appointments.errors import (
    AppointmentNotFoundError,
    AttendanceAlreadyRecordedError,
    CancelledIsFinalError,
    NotStartedYetError,
)
from app.domain.auth import ForbiddenError, Principal
from tests.unit.application.agenda_helpers import (
    ADMIN,
    DENTIST_A,
    DENTIST_NO_FILE,
    PROF_A,
    PROF_B,
    RECEPTION,
    World,
)
from tests.unit.domain.appointments.helpers import monday


def test_the_dentist_marks_their_own_ongoing_appointment_completed() -> None:
    world = World(now=monday(10, 10))
    scheduled = world.seed(monday(10))

    marked = record_attendance(world.deps(), DENTIST_A, scheduled.id, AppointmentStatus.COMPLETED)

    assert marked.status is AppointmentStatus.COMPLETED
    assert world.appointments.get(scheduled.id) == marked


def test_an_appointment_that_has_not_started_cannot_be_marked() -> None:
    world = World(now=monday(9, 59))
    scheduled = world.seed(monday(10))

    with pytest.raises(NotStartedYetError):
        record_attendance(world.deps(), DENTIST_A, scheduled.id, AppointmentStatus.NO_SHOW)

    assert world.appointments.get(scheduled.id) == scheduled


def test_the_exact_start_is_accepted() -> None:
    world = World(now=monday(10))
    scheduled = world.seed(monday(10))
    marked = record_attendance(world.deps(), DENTIST_A, scheduled.id, AppointmentStatus.NO_SHOW)
    assert marked.status is AppointmentStatus.NO_SHOW


def test_a_dentist_cannot_mark_another_professionals_appointment() -> None:
    world = World(now=monday(10, 10))
    foreign = world.seed(monday(10), professional_id=PROF_B)

    with pytest.raises(ForbiddenError):
        record_attendance(world.deps(), DENTIST_A, foreign.id, AppointmentStatus.COMPLETED)

    assert world.appointments.get(foreign.id) == foreign


def test_a_foreign_appointment_is_forbidden_before_any_other_rule() -> None:
    # Ni siquiera empezo: igual se informa FORBIDDEN, sin revelar su estado.
    world = World(now=monday(9))
    foreign = world.seed(monday(10), professional_id=PROF_B)
    with pytest.raises(ForbiddenError):
        record_attendance(world.deps(), DENTIST_A, foreign.id, AppointmentStatus.COMPLETED)


def test_a_dentist_without_a_file_cannot_mark_anything() -> None:
    world = World(now=monday(10, 10))
    scheduled = world.seed(monday(10))
    with pytest.raises(ForbiddenError):
        record_attendance(world.deps(), DENTIST_NO_FILE, scheduled.id, AppointmentStatus.COMPLETED)


@pytest.mark.parametrize("principal", [RECEPTION, ADMIN])
def test_reception_and_admin_mark_any_appointment(principal: Principal) -> None:
    world = World(now=monday(10, 10))
    foreign = world.seed(monday(10), professional_id=PROF_B)
    marked = record_attendance(world.deps(), principal, foreign.id, AppointmentStatus.NO_SHOW)
    assert marked.status is AppointmentStatus.NO_SHOW


def test_a_recorded_attendance_cannot_be_corrected() -> None:
    world = World(now=monday(10, 10))
    scheduled = world.seed(monday(10))
    record_attendance(world.deps(), DENTIST_A, scheduled.id, AppointmentStatus.NO_SHOW)

    with pytest.raises(AttendanceAlreadyRecordedError):
        record_attendance(world.deps(), DENTIST_A, scheduled.id, AppointmentStatus.COMPLETED)

    stored = world.appointments.get(scheduled.id)
    assert stored is not None
    assert stored.status is AppointmentStatus.NO_SHOW


def test_a_cancelled_appointment_cannot_be_marked() -> None:
    world = World(now=monday(10, 10))
    scheduled = world.seed(monday(10))
    world.appointments.change_status(scheduled.id, AppointmentStatus.CANCELLED, "aviso")
    with pytest.raises(CancelledIsFinalError):
        record_attendance(world.deps(), DENTIST_A, scheduled.id, AppointmentStatus.COMPLETED)


def test_an_inactive_professional_file_does_not_block_marking() -> None:
    world = World(now=monday(10, 10))
    scheduled = world.seed(monday(10))
    world.set_professional_active(PROF_A, False)
    marked = record_attendance(world.deps(), RECEPTION, scheduled.id, AppointmentStatus.COMPLETED)
    assert marked.status is AppointmentStatus.COMPLETED


def test_an_unknown_appointment_is_not_found() -> None:
    world = World()
    with pytest.raises(AppointmentNotFoundError):
        record_attendance(world.deps(), DENTIST_A, "no-existe", AppointmentStatus.COMPLETED)


@pytest.mark.parametrize("status", [AppointmentStatus.SCHEDULED, AppointmentStatus.CANCELLED])
def test_only_completed_and_no_show_are_valid_targets(status: AppointmentStatus) -> None:
    world = World(now=monday(10, 10))
    scheduled = world.seed(monday(10))
    with pytest.raises(ValueError):
        record_attendance(world.deps(), RECEPTION, scheduled.id, status)
    assert world.appointments.get(scheduled.id) == scheduled
