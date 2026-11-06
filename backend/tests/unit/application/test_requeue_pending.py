"""Reencolar las pendientes antiguas (spec notification-sending, con repositorio en memoria)."""

from __future__ import annotations

import logging
from datetime import timedelta

import pytest
from kombu.exceptions import OperationalError

from app.application.notifications import RequeueDeps, requeue_pending
from app.domain.appointments import NotificationKind, NotificationStatus
from app.infrastructure.in_memory import InMemoryNotificationRepository
from tests.unit.domain.appointments.helpers import monday

NOW = monday(9)
PENDING = NotificationStatus.PENDING


class Published:
    def __init__(self) -> None:
        self.ids: list[str] = []

    def __call__(self, notification_id: str) -> None:
        self.ids.append(notification_id)


def build(repo: InMemoryNotificationRepository, published: Published) -> RequeueDeps:
    return RequeueDeps(notifications=repo, publish=published, clock=lambda: NOW)


def test_a_pending_older_than_five_minutes_is_requested() -> None:
    repo, published = InMemoryNotificationRepository(), Published()
    old = repo.seed(
        "t-1", NotificationKind.CONFIRMATION, PENDING, monday(10), NOW - timedelta(minutes=20)
    )

    count = requeue_pending(build(repo, published))

    assert count == 1
    assert published.ids == [old.id]


@pytest.mark.parametrize("age_minutes", [1, 5])
def test_a_recent_pending_is_not_taken_yet(age_minutes: int) -> None:
    repo, published = InMemoryNotificationRepository(), Published()
    repo.seed(
        "t-1",
        NotificationKind.CONFIRMATION,
        PENDING,
        monday(10),
        NOW - timedelta(minutes=age_minutes),
    )

    assert requeue_pending(build(repo, published)) == 0
    assert published.ids == []


def test_six_minutes_old_is_taken() -> None:
    repo, published = InMemoryNotificationRepository(), Published()
    repo.seed("t-1", NotificationKind.CONFIRMATION, PENDING, monday(10), NOW - timedelta(minutes=6))
    assert requeue_pending(build(repo, published)) == 1


def test_sent_and_failed_are_never_requested() -> None:
    repo, published = InMemoryNotificationRepository(), Published()
    old = NOW - timedelta(hours=5)
    repo.seed("t-1", NotificationKind.CONFIRMATION, NotificationStatus.SENT, monday(10), old)
    repo.seed("t-1", NotificationKind.REMINDER, NotificationStatus.FAILED, monday(10), old)

    assert requeue_pending(build(repo, published)) == 0
    assert published.ids == []


def test_with_150_old_ones_only_the_100_oldest_are_requested() -> None:
    repo, published = InMemoryNotificationRepository(), Published()
    seeded = [
        repo.seed(
            "t-1",
            NotificationKind.CONFIRMATION,
            PENDING,
            monday(10) + timedelta(days=n),
            NOW - timedelta(hours=1, minutes=150 - n),
        )
        for n in range(150)
    ]

    count = requeue_pending(build(repo, published))

    assert count == 100
    assert published.ids == [row.id for row in seeded[:100]]
    assert requeue_pending(build(repo, Published())) == 100  # las otras 50 siguen pendientes


def test_it_logs_only_the_count(caplog: pytest.LogCaptureFixture) -> None:
    repo, published = InMemoryNotificationRepository(), Published()
    repo.seed(
        "turno-secreto",
        NotificationKind.CONFIRMATION,
        PENDING,
        monday(10),
        NOW - timedelta(hours=1),
    )
    caplog.set_level(logging.INFO)

    requeue_pending(build(repo, published))

    assert "1" in caplog.text
    assert "turno-secreto" not in caplog.text


def test_a_failing_publish_does_not_stop_the_pass_and_is_not_counted() -> None:
    repo = InMemoryNotificationRepository()
    first = repo.seed(
        "t-1", NotificationKind.CONFIRMATION, PENDING, monday(10), NOW - timedelta(hours=2)
    )
    second = repo.seed(
        "t-1", NotificationKind.CONFIRMATION, PENDING, monday(11), NOW - timedelta(hours=1)
    )
    published: list[str] = []

    def publish(notification_id: str) -> None:
        if notification_id == first.id:
            raise OperationalError("redis caido")
        published.append(notification_id)

    deps = RequeueDeps(notifications=repo, publish=publish, clock=lambda: NOW)

    assert requeue_pending(deps) == 1
    assert published == [second.id]
