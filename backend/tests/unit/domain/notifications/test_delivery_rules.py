"""Decision pura de envio (spec notification-sending, design D-2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.appointments import (
    Appointment,
    AppointmentStatus,
    Notification,
    NotificationKind,
    NotificationStatus,
)
from app.domain.notifications import DeliveryDecision, decide_delivery

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
START = datetime(2026, 11, 9, 13, 0, tzinfo=UTC)


def make_notification(
    *,
    status: NotificationStatus = NotificationStatus.PENDING,
    starts_at: datetime = START,
    kind: NotificationKind = NotificationKind.CONFIRMATION,
) -> Notification:
    return Notification("n-1", "t-1", kind, status, None, None, starts_at)


def make_appointment(
    *, status: AppointmentStatus = AppointmentStatus.SCHEDULED, starts_at: datetime = START
) -> Appointment:
    end = starts_at + timedelta(minutes=30)
    return Appointment("t-1", "p-1", "d-1", starts_at, end, status, None, "u")


def test_a_pending_notification_of_a_future_scheduled_appointment_is_sent() -> None:
    assert decide_delivery(make_notification(), make_appointment(), NOW) is DeliveryDecision.SEND


def test_a_pending_reminder_with_other_start_and_zone_input_is_sent() -> None:
    other = datetime(2026, 12, 1, 3, 30, tzinfo=UTC)
    decision = decide_delivery(
        make_notification(starts_at=other, kind=NotificationKind.REMINDER),
        make_appointment(starts_at=other),
        NOW,
    )
    assert decision is DeliveryDecision.SEND


@pytest.mark.parametrize("status", [NotificationStatus.SENT, NotificationStatus.FAILED])
def test_a_notification_that_is_not_pending_is_skipped(status: NotificationStatus) -> None:
    decision = decide_delivery(make_notification(status=status), make_appointment(), NOW)
    assert decision is DeliveryDecision.SKIP


def test_a_notification_for_another_start_is_skipped() -> None:
    moved = datetime(2026, 11, 9, 14, 0, tzinfo=UTC)
    decision = decide_delivery(make_notification(), make_appointment(starts_at=moved), NOW)
    assert decision is DeliveryDecision.SKIP


def test_the_start_comparison_is_by_instant_not_by_zone() -> None:
    from zoneinfo import ZoneInfo

    same_instant = START.astimezone(ZoneInfo("America/Argentina/Buenos_Aires"))
    decision = decide_delivery(make_notification(starts_at=same_instant), make_appointment(), NOW)
    assert decision is DeliveryDecision.SEND


@pytest.mark.parametrize("now", [START, datetime(2026, 11, 9, 13, 30, tzinfo=UTC)])
def test_an_appointment_that_starts_now_or_already_started_expires(now: datetime) -> None:
    assert decide_delivery(make_notification(), make_appointment(), now) is DeliveryDecision.EXPIRE


@pytest.mark.parametrize("status", [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED])
def test_an_appointment_that_is_not_scheduled_expires(status: AppointmentStatus) -> None:
    decision = decide_delivery(make_notification(), make_appointment(status=status), NOW)
    assert decision is DeliveryDecision.EXPIRE


def test_a_sent_notification_of_a_past_appointment_is_skipped_not_expired() -> None:
    decision = decide_delivery(
        make_notification(status=NotificationStatus.SENT),
        make_appointment(),
        datetime(2026, 11, 10, tzinfo=UTC),
    )
    assert decision is DeliveryDecision.SKIP
