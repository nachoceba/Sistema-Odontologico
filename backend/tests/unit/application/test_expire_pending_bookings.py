"""Caso de uso del vencimiento de reservas online con repositorios en memoria (C-16)."""

from __future__ import annotations

import logging
from datetime import date, timedelta

import pytest

from app.application.appointments import cancel_appointment
from app.application.public_booking import (
    ExpiryDeps,
    OnlineBooking,
    book_online,
    confirm_online_booking,
    expire_pending_bookings,
    public_day_slots,
)
from app.domain.appointments import Appointment, AppointmentStatus, NotificationKind
from app.domain.appointments import NotificationStatus as Status
from app.domain.public_booking.rules import EXPIRED_BOOKING_REASON
from tests.unit.application.agenda_helpers import PROF_A, World
from tests.unit.domain.appointments.helpers import local, monday


def booked(
    world: World, hour: int = 10, document: str = "40999888", mail: str = "l@example.com"
) -> OnlineBooking:
    """Una reserva online pendiente del lunes a la hora dada, hecha el sabado 10:00."""
    return book_online(
        world.public_deps(hold_minutes=60),
        professional_id=PROF_A,
        treatment_id=world.treatment_id,
        starts_at=monday(hour),
        document_number=document,
        first_name="Lucía",
        last_name="Díaz",
        email=mail,
        phone=None,
    )


def pending_of(world: World) -> list[Appointment]:
    return [a for a in world.everything() if a.created_by is None]


def run(world: World) -> int:
    return expire_pending_bookings(world.expiry_deps())


def test_an_expired_reservation_is_cancelled_with_the_reason_and_its_notice_is_dispatched() -> None:
    world = World()
    booked(world)
    world.now = local(2026, 10, 3, 11, 2)  # el plazo de 60 minutos vencio a las 11:00

    assert run(world) == 1

    [saved] = pending_of(world)
    assert saved.status is AppointmentStatus.CANCELLED
    assert saved.cancel_reason == EXPIRED_BOOKING_REASON
    assert saved.pending_until is None
    [row] = world.notifications.list_for_appointment(saved.id)
    assert (row.kind, row.status) == (NotificationKind.BOOKING_EXPIRED, Status.PENDING)
    assert row.appointment_starts_at == monday(10)
    assert world.dispatcher.calls == [[row]]


def test_two_expired_reservations_are_cancelled_in_one_pass_and_return_the_count() -> None:
    world = World()
    booked(world, 10, "40999888")
    booked(world, 11, "40999777", "m@example.com")
    world.now = local(2026, 10, 3, 12)

    assert run(world) == 2

    assert {a.status for a in pending_of(world)} == {AppointmentStatus.CANCELLED}
    [call] = world.dispatcher.calls
    assert len(call) == 2


def test_a_reservation_that_is_still_valid_is_left_alone() -> None:
    world = World()
    booked(world)
    world.now = local(2026, 10, 3, 10, 55)

    assert run(world) == 0

    [saved] = pending_of(world)
    assert saved.status is AppointmentStatus.SCHEDULED
    assert world.dispatcher.calls == []
    assert world.notifications.list_for_appointment(saved.id) == []


def test_the_exact_expiry_instant_cancels() -> None:
    world = World()
    booked(world)
    world.now = local(2026, 10, 3, 11, 0)

    assert run(world) == 1


def test_running_twice_changes_nothing_and_leaves_one_notice() -> None:
    world = World()
    booked(world)
    world.now = local(2026, 10, 3, 11, 5)
    run(world)

    assert run(world) == 0

    [saved] = pending_of(world)
    assert len(world.notifications.list_for_appointment(saved.id)) == 1
    assert len(world.dispatcher.calls) == 1


def test_confirmed_and_reception_appointments_are_never_touched() -> None:
    world = World()
    booked(world, 10)
    world.now = local(2026, 10, 3, 10, 30)
    confirm_online_booking(world.public_deps(), "tok-1")
    dispatched_before = len(world.dispatcher.calls)
    walk_in = world.seed(monday(11))
    world.now = local(2026, 10, 4, 10)

    assert run(world) == 0

    assert world.appointments.get(walk_in.id) == walk_in
    [saved] = pending_of(world)
    assert saved.status is AppointmentStatus.SCHEDULED
    assert len(world.dispatcher.calls) == dispatched_before
    assert all(
        row.kind is not NotificationKind.BOOKING_EXPIRED
        for row in world.notifications.list_for_appointment(saved.id)
    )


def test_a_failing_dispatcher_does_not_undo_the_cancellation_and_leaves_the_notice_pending(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = World()
    booked(world)
    world.dispatcher.error = ConnectionError("redis caido")
    world.now = local(2026, 10, 3, 11, 5)

    with caplog.at_level(logging.WARNING):
        assert run(world) == 1

    [saved] = pending_of(world)
    assert saved.status is AppointmentStatus.CANCELLED
    [row] = world.notifications.list_for_appointment(saved.id)
    assert row.status is Status.PENDING
    assert "ConnectionError" in caplog.text
    assert "l@example.com" not in caplog.text


def test_a_failure_registering_the_notice_rolls_the_cancellation_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = World()
    booked(world)
    world.now = local(2026, 10, 3, 11, 5)

    def boom(*_: object, **__: object) -> None:
        raise RuntimeError

    monkeypatch.setattr(world.notifications, "add_pending_booking_expired", boom)

    with pytest.raises(RuntimeError):
        run(world)

    [saved] = pending_of(world)
    assert saved.status is AppointmentStatus.SCHEDULED
    assert saved.pending_until is not None
    assert world.dispatcher.calls == []


def test_the_reception_cancelling_a_pending_reservation_registers_no_expiry_notice() -> None:
    world = World()
    booked(world)
    [saved] = pending_of(world)

    cancel_appointment(world.deps(), saved.id, "El paciente avisó por teléfono")
    world.now = world.now + timedelta(days=1)

    assert run(world) == 0
    assert world.notifications.list_for_appointment(saved.id) == []


def test_the_freed_slot_is_free_again_for_the_public_page() -> None:
    world = World()
    booked(world, 10)
    day = date(2026, 10, 5)
    before = public_day_slots(world.public_deps(), PROF_A, day)
    world.now = local(2026, 10, 3, 11, 5)
    run(world)
    after = public_day_slots(world.public_deps(), PROF_A, day)

    assert monday(10) not in [s.starts_at for s in before]
    assert monday(10) in [s.starts_at for s in after]


def test_expiry_deps_is_just_the_unit_of_work_the_dispatcher_and_the_clock() -> None:
    world = World()

    deps = world.expiry_deps()

    assert isinstance(deps, ExpiryDeps)
    assert set(vars(deps)) == {"unit_of_work", "dispatcher", "clock"}
