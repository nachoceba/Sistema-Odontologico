"""Tareas Celery de notificaciones, en modo inmediato y con el remitente falso (spec
notification-tasks, design D-7)."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import replace
from datetime import timedelta

import pytest
from kombu.connection import Connection
from sqlalchemy.exc import OperationalError

from app.application.notifications import RequeueDeps
from app.application.reminders import ReminderDeps
from app.domain.appointments import NotificationKind, NotificationStatus
from app.domain.settings.types import ClinicSettings
from app.infrastructure.tasks import wiring
from app.infrastructure.tasks.notifications import (
    enviar_email,
    enviar_recordatorios,
    reencolar_pendientes,
)
from tests.unit.application.notification_helpers import SendWorld
from tests.unit.application.reminder_helpers import ReminderWorld
from tests.unit.domain.appointments.helpers import local, monday


@pytest.fixture
def scenario(monkeypatch: pytest.MonkeyPatch) -> Iterator[SendWorld]:
    world = SendWorld()
    world.world.now = local(2026, 10, 2, 9)
    monkeypatch.setattr(wiring, "build_notification_deps", lambda: world.deps())
    yield world


def run(notification_id: str) -> str:
    result = enviar_email.apply(args=[notification_id], throw=False)
    value = result.get()
    assert isinstance(value, str)
    return value


def test_success_sends_one_email_and_marks_sent(scenario: SendWorld) -> None:
    assert run(scenario.notification.id) == "SENT"

    assert len(scenario.sender.sent) == 1
    assert scenario.rows()[0].status is NotificationStatus.SENT


def test_a_permanent_failure_marks_failed_without_retrying(scenario: SendWorld) -> None:
    scenario.sender.fail_next(1, temporary=False, code="550")

    assert run(scenario.notification.id) == "FAILED"

    assert scenario.sender.attempts == 1
    assert scenario.rows()[0].error == "SMTP_PERMANENT 550"


def test_a_temporary_failure_is_retried_and_then_sent(scenario: SendWorld) -> None:
    scenario.sender.fail_next(1, temporary=True, code="TIMEOUT")

    assert run(scenario.notification.id) == "SENT"

    assert scenario.sender.attempts == 2
    assert len(scenario.sender.sent) == 1


def test_three_temporary_failures_end_failed_with_no_fourth_attempt(scenario: SendWorld) -> None:
    scenario.sender.fail_next(5, temporary=True, code="451")

    assert run(scenario.notification.id) == "FAILED"

    assert scenario.sender.attempts == 3
    assert scenario.rows()[0].error == "SMTP_TEMPORARY 451"


def test_running_the_same_task_twice_sends_a_single_message(scenario: SendWorld) -> None:
    assert run(scenario.notification.id) == "SENT"
    assert run(scenario.notification.id) == "SKIPPED"

    assert len(scenario.sender.sent) == 1


@pytest.mark.parametrize("bad_id", ["no-existe", "", "5b0a1c3e-7f64-4a0e-9d57-2f5c3a1d9e11"])
def test_an_unknown_or_malformed_id_ends_without_sending_or_retrying(
    scenario: SendWorld, bad_id: str
) -> None:
    assert run(bad_id) == "SKIPPED"

    assert scenario.sender.attempts == 0


def test_the_published_message_carries_only_the_notification_id(scenario: SendWorld) -> None:
    with Connection("memory://") as connection:  # type: ignore[no-untyped-call]
        enviar_email.apply_async(args=[scenario.notification.id], connection=connection)
        queue = connection.SimpleQueue("celery")
        message = queue.get(timeout=2)
        raw = json.dumps(message.payload)
        message.ack()
        queue.close()

    assert scenario.notification.id in raw
    assert "juan@example.com" not in raw
    assert "Pérez" not in raw and "P\\u00e9rez" not in raw
    assert "@" not in raw


def test_requeue_task_requests_old_pending_and_the_original_queued_task_sends_nothing_more(
    scenario: SendWorld, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = scenario.world
    monkeypatch.setattr(
        wiring,
        "build_requeue_deps",
        lambda: RequeueDeps(
            notifications=world.notifications,
            publish=lambda nid: enviar_email.apply(args=[nid], throw=False),
            clock=lambda: world.now + timedelta(hours=1),
        ),
    )
    old = world.notifications.seed(
        scenario.appointment.id,
        NotificationKind.REMINDER,
        NotificationStatus.PENDING,
        scenario.appointment.starts_at,
        world.now - timedelta(hours=1),
    )

    first = reencolar_pendientes.apply(throw=True).get()
    second = reencolar_pendientes.apply(throw=True).get()
    already_queued = run(old.id)  # la tarea original, que ya estaba en la cola

    assert (first, second) == (1, 0)  # la confirmacion recien creada no se toma
    assert already_queued == "SKIPPED"
    assert len(scenario.sender.sent) == 1
    assert scenario.sender.sent[0].subject.startswith("Recordatorio de turno")


# --- Recordatorios (C-12) -----------------------------------------------------------------------


@pytest.fixture
def reminders(monkeypatch: pytest.MonkeyPatch) -> Iterator[ReminderWorld]:
    world = ReminderWorld()
    monkeypatch.setattr(wiring, "build_reminder_deps", lambda: world.deps())
    yield world


def test_the_reminder_task_sends_the_reminder_at_the_configured_hour(
    reminders: ReminderWorld,
) -> None:
    appointment = reminders.world.seed(monday(10))

    result = enviar_recordatorios.apply(throw=True).get()

    assert result == {"processed": 1, "sent": 1, "failed": 0, "pending": 0}
    [email] = reminders.sender.sent
    assert email.subject.startswith("Recordatorio de turno")
    assert [row.status for row in reminders.rows(appointment.id)] == [NotificationStatus.SENT]


def test_the_reminder_task_does_nothing_outside_the_configured_hour(
    reminders: ReminderWorld,
) -> None:
    appointment = reminders.world.seed(monday(10))
    reminders.world.now = local(2026, 10, 4, 14)

    result = enviar_recordatorios.apply(throw=True).get()

    assert result == {"processed": 0, "sent": 0, "failed": 0, "pending": 0}
    assert reminders.sender.attempts == 0
    assert reminders.rows(appointment.id) == []


def test_the_reminder_task_can_be_forced_outside_the_hour_and_twice_sends_once(
    reminders: ReminderWorld,
) -> None:
    reminders.world.seed(monday(10))
    reminders.world.now = local(2026, 10, 4, 14)

    first = enviar_recordatorios.apply(kwargs={"forzar": True}, throw=True).get()
    second = enviar_recordatorios.apply(kwargs={"forzar": True}, throw=True).get()

    assert first["sent"] == 1
    assert second["processed"] == 0
    assert len(reminders.sender.sent) == 1


class UnreachableSettings:
    def get(self) -> ClinicSettings:
        raise OperationalError("SELECT 1", {}, Exception("la base no responde"))


def test_a_database_error_at_the_start_ends_the_task_logged_without_retrying_or_patient_data(
    reminders: ReminderWorld, caplog: pytest.LogCaptureFixture
) -> None:
    reminders.world.seed(monday(10))
    deps = reminders.deps()

    def broken_deps() -> ReminderDeps:
        return replace(deps, settings=UnreachableSettings())

    with pytest.MonkeyPatch.context() as patch, caplog.at_level(logging.ERROR):
        patch.setattr(wiring, "build_reminder_deps", broken_deps)
        result = enviar_recordatorios.apply(throw=False)

    assert result.failed()
    assert result.traceback is not None
    assert result.result.__class__ is OperationalError
    assert "OperationalError" in caplog.text
    assert "juan@example.com" not in caplog.text
    assert "Pérez" not in caplog.text
    assert reminders.sender.attempts == 0


# --- Verificacion de una reserva online (C-15) ---


def test_the_verification_task_sends_the_email_when_the_pending_appointment_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.infrastructure.tasks.notifications import enviar_verificacion_reserva
    from tests.unit.application.test_send_verification import Scenario

    scenario = Scenario()
    monkeypatch.setattr(wiring, "build_verification_deps", lambda: scenario.deps())

    result = enviar_verificacion_reserva.apply(
        args=[scenario.appointment_id, scenario.token], throw=False
    )

    assert result.get() == "SENT"
    assert len(scenario.sender.sent) == 1


def test_the_verification_task_retries_a_temporary_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.infrastructure.tasks.notifications import enviar_verificacion_reserva
    from tests.unit.application.test_send_verification import Scenario

    scenario = Scenario()
    scenario.sender.fail_next(1, temporary=True, code="TIMEOUT")
    monkeypatch.setattr(wiring, "build_verification_deps", lambda: scenario.deps())

    result = enviar_verificacion_reserva.apply(
        args=[scenario.appointment_id, scenario.token], throw=False
    )

    assert result.get() == "SENT"
    assert scenario.sender.attempts == 2
