"""Despachador real: una tarea por notificacion, sin que un fallo de Redis salga (spec
notification-tasks, design D-8)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import pytest
from kombu.exceptions import OperationalError

from app.domain.appointments import Notification, NotificationKind, NotificationStatus
from app.infrastructure.tasks.dispatcher import CeleryNotificationDispatcher

START = datetime(2026, 11, 9, 13, 0, tzinfo=UTC)


def note(number: int) -> Notification:
    return Notification(
        f"n-{number}",
        f"turno-{number}",
        NotificationKind.CONFIRMATION,
        NotificationStatus.PENDING,
        None,
        None,
        START,
    )


def test_it_publishes_one_task_per_notification_with_only_the_id() -> None:
    published: list[str] = []

    CeleryNotificationDispatcher(published.append).dispatch([note(1), note(2)])

    assert published == ["n-1", "n-2"]


def test_it_publishes_nothing_for_an_empty_list() -> None:
    published: list[str] = []
    CeleryNotificationDispatcher(published.append).dispatch([])
    assert published == []


def test_a_publish_error_is_logged_with_the_appointment_id_and_the_next_one_still_goes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    published: list[str] = []

    def publish(notification_id: str) -> None:
        if notification_id == "n-1":
            raise OperationalError("redis caido con juan@example.com")
        published.append(notification_id)

    caplog.set_level(logging.WARNING)

    CeleryNotificationDispatcher(publish).dispatch([note(1), note(2)])

    assert published == ["n-2"]
    assert "turno-1" in caplog.text
    assert "OperationalError" in caplog.text
    assert "juan@example.com" not in caplog.text
    assert "redis caido" not in caplog.text


def test_every_failure_is_swallowed_so_the_booking_never_breaks() -> None:
    def publish(notification_id: str) -> None:
        raise OperationalError("sin redis")

    CeleryNotificationDispatcher(publish).dispatch([note(1), note(2), note(3)])
