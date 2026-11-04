"""Tipos de notificacion del dominio: mismos valores que los enumerados de la base (D-1)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.appointments import Notification, NotificationKind, NotificationStatus
from app.infrastructure.db import enums


def test_notification_kind_has_exactly_the_database_values() -> None:
    assert {kind.value for kind in NotificationKind} == {
        kind.value for kind in enums.NotificationKind
    }


def test_notification_status_has_exactly_the_database_values() -> None:
    assert {s.value for s in NotificationStatus} == {s.value for s in enums.NotificationStatus}


def test_every_database_value_converts_to_the_domain_enum_by_value() -> None:
    for kind in enums.NotificationKind:
        assert NotificationKind(kind.value).name == kind.name
    for status in enums.NotificationStatus:
        assert NotificationStatus(status.value).name == status.name


def test_a_pending_confirmation_has_no_send_date_or_error() -> None:
    starts_at = datetime(2026, 10, 5, 13, 0, tzinfo=UTC)
    notification = Notification(
        id="n-1",
        appointment_id="t-1",
        kind=NotificationKind.CONFIRMATION,
        status=NotificationStatus.PENDING,
        sent_at=None,
        error=None,
        appointment_starts_at=starts_at,
    )
    assert notification.sent_at is None
    assert notification.error is None
    assert notification.appointment_starts_at == starts_at


def test_notifications_are_immutable() -> None:
    notification = Notification(
        id="n-1",
        appointment_id="t-1",
        kind=NotificationKind.REMINDER,
        status=NotificationStatus.SENT,
        sent_at=datetime(2026, 10, 4, 12, 0, tzinfo=UTC),
        error=None,
        appointment_starts_at=datetime(2026, 10, 5, 13, 0, tzinfo=UTC),
    )
    with pytest.raises(AttributeError):
        notification.status = NotificationStatus.FAILED  # type: ignore[misc]
