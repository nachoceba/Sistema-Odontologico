"""Agendar, reprogramar y cancelar registran notificaciones y avisan al despachador
(spec notification-registration y appointment-unit-of-work, con repositorios en memoria)."""

from __future__ import annotations

import logging
from datetime import datetime

import pytest

from app.application.appointments import (
    book_appointment,
    cancel_appointment,
    record_attendance,
    reschedule_appointment,
)
from app.domain.appointments import (
    AppointmentStatus,
    Notification,
    NotificationKind,
    NotificationStatus,
)
from app.domain.appointments.errors import SlotTakenError
from app.infrastructure.in_memory import InMemoryNotificationRepository
from tests.unit.application.agenda_helpers import PROF_A, RECEPTION, World
from tests.unit.domain.appointments.helpers import monday

PENDING = NotificationStatus.PENDING
CONFIRMATION = NotificationKind.CONFIRMATION


class NotificationWriteFailed(Exception):
    pass


class FailingNotifications(InMemoryNotificationRepository):
    """Falla al registrar la confirmacion, despues de que el turno ya se escribio."""

    def add_pending_confirmation(
        self, appointment_id: str, starts_at: datetime
    ) -> Notification | None:
        raise NotificationWriteFailed


def book(world: World, starts_at: datetime | None = None, patient_id: str = "pac-1") -> str:
    return book_appointment(
        world.deps(),
        RECEPTION,
        patient_id=patient_id,
        professional_id=PROF_A,
        treatment_id=world.treatment_id,
        starts_at=starts_at or monday(10),
    ).id


def statuses(world: World, appointment_id: str) -> list[tuple[datetime, NotificationStatus]]:
    rows = world.notifications.list_for_appointment(appointment_id)
    return [(row.appointment_starts_at, row.status) for row in rows]


# --- Agendar -----------------------------------------------------------------------------------


def test_booking_registers_one_pending_confirmation_for_the_start() -> None:
    world = World()

    appointment_id = book(world)

    rows = world.notifications.list_for_appointment(appointment_id)
    assert len(rows) == 1
    assert rows[0].kind is CONFIRMATION
    assert rows[0].status is PENDING
    assert rows[0].sent_at is None
    assert rows[0].error is None
    assert rows[0].appointment_starts_at == monday(10)


def test_a_rejected_booking_registers_nothing_and_does_not_notify() -> None:
    world = World()
    world.seed(monday(10), patient_id="pac-2")

    with pytest.raises(SlotTakenError):
        book(world)

    assert world.notifications.snapshot() == {}
    assert world.dispatcher.calls == []


def test_the_dispatcher_receives_exactly_the_new_confirmation_after_the_commit() -> None:
    world = World()
    seen_in_database: list[bool] = []
    original = world.dispatcher.dispatch

    def dispatch_and_check(notifications):  # type: ignore[no-untyped-def]
        seen_in_database.append(
            all(world.appointments.get(n.appointment_id) is not None for n in notifications)
        )
        original(notifications)

    world.dispatcher.dispatch = dispatch_and_check  # type: ignore[method-assign]

    appointment_id = book(world)

    assert len(world.dispatcher.calls) == 1
    (sent,) = world.dispatcher.calls[0]
    assert sent.appointment_id == appointment_id
    assert sent.kind is CONFIRMATION
    assert seen_in_database == [True]


def test_a_failure_registering_the_notification_leaves_no_appointment() -> None:
    world = World(notifications=FailingNotifications())

    with pytest.raises(NotificationWriteFailed):
        book(world)

    assert world.everything() == []
    assert world.dispatcher.calls == []


def test_a_failing_dispatcher_does_not_undo_the_booking_and_logs_no_patient_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = World()
    world.dispatcher.error = RuntimeError("juan@example.com Juan Pérez")

    with caplog.at_level(logging.WARNING):
        appointment_id = book(world)

    assert world.appointments.get(appointment_id) is not None
    assert len(world.notifications.list_for_appointment(appointment_id)) == 1
    assert caplog.records, "el fallo del despachador debe quedar registrado"
    logged = " ".join(record.getMessage() for record in caplog.records)
    assert appointment_id in logged
    for private in ("juan@example.com", "Juan", "Pérez"):
        assert private not in logged
    assert all(record.exc_info is None for record in caplog.records)


# --- Reprogramar -------------------------------------------------------------------------------


def test_rescheduling_replaces_the_pending_confirmation_of_the_old_start() -> None:
    world = World()
    appointment_id = book(world, monday(10))
    world.dispatcher.calls.clear()

    reschedule_appointment(world.deps(), appointment_id, monday(11))

    assert statuses(world, appointment_id) == [(monday(11), PENDING)]
    assert [[n.appointment_starts_at for n in call] for call in world.dispatcher.calls] == [
        [monday(11)]
    ]


def test_rescheduling_keeps_a_sent_confirmation_as_history() -> None:
    world = World()
    appointment_id = book(world, monday(10))
    world.notifications.delete_pending(appointment_id)
    world.notifications.seed(appointment_id, CONFIRMATION, NotificationStatus.SENT, monday(10))

    reschedule_appointment(world.deps(), appointment_id, monday(11))

    assert statuses(world, appointment_id) == [
        (monday(10), NotificationStatus.SENT),
        (monday(11), PENDING),
    ]


def test_going_back_to_an_already_confirmed_start_does_not_duplicate_or_fail() -> None:
    world = World()
    appointment_id = book(world, monday(10))
    world.notifications.delete_pending(appointment_id)
    world.notifications.seed(appointment_id, CONFIRMATION, NotificationStatus.SENT, monday(10))
    reschedule_appointment(world.deps(), appointment_id, monday(11))
    world.dispatcher.calls.clear()

    moved_back = reschedule_appointment(world.deps(), appointment_id, monday(10))

    assert moved_back.starts_at == monday(10)
    assert statuses(world, appointment_id) == [(monday(10), NotificationStatus.SENT)]
    assert world.dispatcher.calls == []  # no hay confirmacion nueva que avisar


def test_a_rejected_reschedule_leaves_the_notifications_as_they_were() -> None:
    world = World()
    appointment_id = book(world, monday(10))
    world.seed(monday(11), patient_id="pac-2")
    before = world.notifications.snapshot()
    world.dispatcher.calls.clear()

    with pytest.raises(SlotTakenError):
        reschedule_appointment(world.deps(), appointment_id, monday(11))

    assert world.notifications.snapshot() == before
    assert world.dispatcher.calls == []


def test_rescheduling_to_the_same_time_registers_nothing() -> None:
    world = World()
    appointment_id = book(world, monday(10))
    before = world.notifications.snapshot()

    with pytest.raises(Exception, match="ya está en ese horario"):
        reschedule_appointment(world.deps(), appointment_id, monday(10))

    assert world.notifications.snapshot() == before


def test_a_failure_registering_after_the_move_restores_appointment_and_pending() -> None:
    world = World()
    appointment_id = book(world, monday(10))
    pending_before = world.notifications.snapshot()
    failing = FailingNotifications()
    failing.restore(pending_before)
    world.notifications = failing

    with pytest.raises(NotificationWriteFailed):
        reschedule_appointment(world.deps(), appointment_id, monday(11))

    stored = world.appointments.get(appointment_id)
    assert stored is not None
    assert stored.starts_at == monday(10)
    assert world.notifications.snapshot() == pending_before


# --- Cancelar y marcar atencion -------------------------------------------------------------------


def test_cancelling_discards_pending_and_creates_nothing() -> None:
    world = World()
    appointment_id = book(world)
    world.dispatcher.calls.clear()

    cancelled = cancel_appointment(world.deps(), appointment_id, "Aviso del paciente")

    assert cancelled.status is AppointmentStatus.CANCELLED
    assert world.notifications.list_for_appointment(appointment_id) == []
    assert world.dispatcher.calls == []


def test_cancelling_keeps_a_sent_confirmation() -> None:
    world = World()
    appointment_id = book(world)
    world.notifications.delete_pending(appointment_id)
    world.notifications.seed(appointment_id, CONFIRMATION, NotificationStatus.SENT, monday(10))

    cancel_appointment(world.deps(), appointment_id, "Aviso del paciente")

    assert statuses(world, appointment_id) == [(monday(10), NotificationStatus.SENT)]


def test_a_rejected_cancel_leaves_the_pending_confirmation() -> None:
    world = World(now=monday(10, 5))
    appointment = world.seed(monday(10))
    world.notifications.add_pending_confirmation(appointment.id, monday(10))
    before = world.notifications.snapshot()

    with pytest.raises(Exception, match="ya empezó"):
        cancel_appointment(world.deps(), appointment.id, "tarde")

    assert world.notifications.snapshot() == before


def test_marking_attendance_does_not_touch_notifications() -> None:
    world = World(now=monday(10, 10))
    appointment = world.seed(monday(10))
    world.notifications.add_pending_confirmation(appointment.id, monday(10))
    before = world.notifications.snapshot()

    record_attendance(world.deps(), RECEPTION, appointment.id, AppointmentStatus.COMPLETED)

    assert world.notifications.snapshot() == before
    assert world.dispatcher.calls == []
