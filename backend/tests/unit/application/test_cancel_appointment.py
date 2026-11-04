"""Caso de uso cancelar un turno (spec appointment-use-cases)."""

from __future__ import annotations

import pytest

from app.application.appointments import book_appointment, cancel_appointment
from app.domain.appointments import AppointmentStatus
from app.domain.appointments.errors import (
    AlreadyStartedError,
    AppointmentNotFoundError,
    AttendanceAlreadyRecordedError,
    CancelledIsFinalError,
)
from tests.unit.application.agenda_helpers import PROF_A, RECEPTION, World
from tests.unit.domain.appointments.helpers import monday

REASON = "El paciente avisó por teléfono"


def test_cancels_with_the_reason_without_deleting_the_appointment() -> None:
    world = World()
    scheduled = world.seed(monday(10))

    cancelled = cancel_appointment(world.deps(), scheduled.id, REASON)

    assert cancelled.status is AppointmentStatus.CANCELLED
    assert cancelled.cancel_reason == REASON
    assert world.appointments.get(scheduled.id) == cancelled


def test_the_cancelled_slot_can_be_booked_again() -> None:
    world = World()
    scheduled = world.seed(monday(10))
    cancel_appointment(world.deps(), scheduled.id, REASON)

    again = book_appointment(
        world.deps(), RECEPTION, patient_id="pac-2", professional_id=PROF_A, starts_at=monday(10)
    )

    assert again.id != scheduled.id
    assert again.status is AppointmentStatus.SCHEDULED


def test_an_appointment_that_already_started_cannot_be_cancelled() -> None:
    world = World(now=monday(10, 5))
    scheduled = world.seed(monday(10))

    with pytest.raises(AlreadyStartedError):
        cancel_appointment(world.deps(), scheduled.id, REASON)

    assert world.appointments.get(scheduled.id) == scheduled


def test_the_exact_start_already_counts_as_started() -> None:
    world = World(now=monday(10))
    scheduled = world.seed(monday(10))
    with pytest.raises(AlreadyStartedError):
        cancel_appointment(world.deps(), scheduled.id, REASON)


def test_cancelling_twice_keeps_the_original_reason() -> None:
    world = World()
    scheduled = world.seed(monday(10))
    cancel_appointment(world.deps(), scheduled.id, REASON)

    with pytest.raises(CancelledIsFinalError):
        cancel_appointment(world.deps(), scheduled.id, "Otro motivo")

    stored = world.appointments.get(scheduled.id)
    assert stored is not None
    assert stored.cancel_reason == REASON


def test_an_appointment_with_recorded_attendance_cannot_be_cancelled() -> None:
    world = World()
    done = world.seed(monday(10))
    world.appointments.change_status(done.id, AppointmentStatus.COMPLETED)
    with pytest.raises(AttendanceAlreadyRecordedError):
        cancel_appointment(world.deps(), done.id, REASON)


def test_cancelling_works_for_an_inactive_professional_or_patient() -> None:
    world = World()
    scheduled = world.seed(monday(10))
    world.set_professional_active(PROF_A, False)
    world.set_patient_active("pac-1", False)

    cancelled = cancel_appointment(world.deps(), scheduled.id, REASON)

    assert cancelled.status is AppointmentStatus.CANCELLED


def test_an_unknown_appointment_is_not_found() -> None:
    world = World()
    with pytest.raises(AppointmentNotFoundError):
        cancel_appointment(world.deps(), "no-existe", REASON)


@pytest.mark.parametrize("reason", ["", "   "])
def test_an_empty_reason_is_a_programming_error(reason: str) -> None:
    world = World()
    scheduled = world.seed(monday(10))
    with pytest.raises(ValueError):
        cancel_appointment(world.deps(), scheduled.id, reason)
    assert world.appointments.get(scheduled.id) == scheduled
