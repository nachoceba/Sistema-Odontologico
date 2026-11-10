"""Acciones de la recepcion sobre un turno online pendiente y recordatorios (C-15, DD-133)."""

from __future__ import annotations

import pytest

from app.application.appointments import (
    book_appointment,
    cancel_appointment,
    record_attendance,
    reschedule_appointment,
)
from app.application.public_booking import book_online, confirm_online_booking
from app.application.reminders import send_reminders
from app.domain.appointments import AppointmentStatus
from app.domain.appointments.errors import SlotTakenError
from app.domain.public_booking.errors import (
    ConfirmationLinkInvalidError,
    PendingConfirmationError,
)
from tests.unit.application.agenda_helpers import ADMIN, PROF_A, RECEPTION, World
from tests.unit.application.reminder_helpers import ReminderWorld
from tests.unit.domain.appointments.helpers import monday


def online(world: World, hour: int = 10) -> str:
    """Reserva online de la Dra. A el lunes; devuelve el id del turno pendiente."""
    book_online(
        world.public_deps(),
        professional_id=PROF_A,
        starts_at=monday(hour),
        document_number="40999888",
        first_name="Lucía",
        last_name="Díaz",
        email="lucia@example.com",
        phone=None,
    )
    return world.verification.calls[-1][0]


def test_rescheduling_a_pending_appointment_is_rejected_and_changes_nothing() -> None:
    world = World()
    appointment_id = online(world)
    before = world.everything()

    with pytest.raises(PendingConfirmationError):
        reschedule_appointment(world.deps(), appointment_id, monday(11))

    assert world.everything() == before


def test_marking_attendance_on_a_pending_appointment_is_rejected() -> None:
    world = World(now=monday(9), min_notice_hours=0)
    appointment_id = online(world)

    with pytest.raises(PendingConfirmationError):
        record_attendance(world.deps(), ADMIN, appointment_id, AppointmentStatus.COMPLETED)

    stored = world.appointments.get(appointment_id)
    assert stored is not None
    assert stored.status is AppointmentStatus.SCHEDULED


def test_cancelling_a_pending_appointment_frees_the_slot_and_kills_the_link() -> None:
    world = World()
    appointment_id = online(world)

    cancelled = cancel_appointment(world.deps(), appointment_id, "El paciente llamó")

    assert cancelled.status is AppointmentStatus.CANCELLED
    assert cancelled.pending_until is None
    with pytest.raises(ConfirmationLinkInvalidError):
        confirm_online_booking(world.public_deps(), "tok-1")
    # la franja volvió a estar libre para la recepción
    book_appointment(
        world.deps(), RECEPTION, patient_id="pac-1", professional_id=PROF_A, starts_at=monday(10)
    )


def test_reception_cannot_book_over_a_pending_appointment() -> None:
    world = World()
    online(world)

    with pytest.raises(SlotTakenError):
        book_appointment(
            world.deps(),
            RECEPTION,
            patient_id="pac-1",
            professional_id=PROF_A,
            starts_at=monday(10),
        )


def test_a_confirmed_online_appointment_reschedules_like_any_other() -> None:
    world = World()
    appointment_id = online(world)
    confirm_online_booking(world.public_deps(), "tok-1")

    moved = reschedule_appointment(world.deps(), appointment_id, monday(11))

    assert moved.starts_at == monday(11)
    assert moved.created_by is None


# --- Recordatorios (RN-NO-02, C-12) ---


def test_the_reminder_pass_skips_pending_and_includes_confirmed_online_appointments() -> None:
    scenario = ReminderWorld()
    world = scenario.world
    pending_id = online(world, 10)
    confirmed_id = online_second(world)
    confirm_online_booking(world.public_deps(), "tok-2")

    summary = send_reminders(scenario.deps())

    assert scenario.rows(pending_id) == []
    assert [r.kind.value for r in scenario.rows(confirmed_id)] == ["confirmation", "reminder"]
    assert summary.processed == 1


def online_second(world: World) -> str:
    """Segunda reserva online (otro horario y otro documento) con su propio token."""
    deps = world.public_deps()
    book_online(
        deps,
        professional_id=PROF_A,
        starts_at=monday(11),
        document_number="40888777",
        first_name="Rosa",
        last_name="Mora",
        email="rosa@example.com",
        phone=None,
    )
    return world.verification.calls[-1][0]
