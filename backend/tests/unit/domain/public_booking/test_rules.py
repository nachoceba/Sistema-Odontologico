"""Reglas puras de la reserva online (C-15, DD-130, DD-132)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.appointments.types import Appointment, AppointmentStatus
from app.domain.public_booking.rules import can_confirm, pending_until_for

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def _appointment(
    *,
    starts_at: datetime = NOW + timedelta(days=1),
    pending_until: datetime | None = NOW + timedelta(minutes=60),
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
) -> Appointment:
    return Appointment(
        id="a-1",
        patient_id="p-1",
        professional_id="d-1",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        status=status,
        cancel_reason=None,
        created_by=None,
        pending_until=pending_until,
    )


def test_pending_until_is_now_plus_hold_when_the_appointment_is_far() -> None:
    result = pending_until_for(NOW, NOW + timedelta(days=2), 60)
    assert result == datetime(2026, 11, 9, 13, 0, tzinfo=UTC)


def test_pending_until_is_the_start_when_it_comes_first() -> None:
    starts = NOW + timedelta(minutes=20)
    assert pending_until_for(NOW, starts, 60) == starts


def test_pending_until_at_the_exact_boundary() -> None:
    starts = NOW + timedelta(minutes=60)
    assert pending_until_for(NOW, starts, 60) == starts


def test_can_confirm_in_time() -> None:
    assert can_confirm(_appointment(), NOW) is True


def test_can_confirm_is_false_at_the_exact_pending_until() -> None:
    assert can_confirm(_appointment(), NOW + timedelta(minutes=60)) is False


def test_can_confirm_is_true_one_second_before_pending_until() -> None:
    assert can_confirm(_appointment(), NOW + timedelta(minutes=60, seconds=-1)) is True


def test_can_confirm_is_false_when_not_pending() -> None:
    assert can_confirm(_appointment(pending_until=None), NOW) is False


def test_can_confirm_is_false_when_cancelled() -> None:
    assert can_confirm(_appointment(status=AppointmentStatus.CANCELLED), NOW) is False


@pytest.mark.parametrize("delta", [timedelta(0), timedelta(seconds=-1)])
def test_can_confirm_is_false_when_the_start_is_not_after_now(delta: timedelta) -> None:
    appt = _appointment(starts_at=NOW + delta, pending_until=NOW + timedelta(minutes=5))
    assert can_confirm(appt, NOW) is False
