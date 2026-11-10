"""Errores de la reserva online con codigo estable (C-15)."""

from __future__ import annotations

import pytest

from app.core.errors import DomainError
from app.domain.public_booking.errors import (
    BookingNotPossibleError,
    BookingRejectedError,
    ConfirmationLinkInvalidError,
    PendingConfirmationError,
    SlotUnavailableError,
    TooManyRequestsError,
)


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (SlotUnavailableError(), "SLOT_UNAVAILABLE"),
        (BookingNotPossibleError(), "BOOKING_NOT_POSSIBLE"),
        (ConfirmationLinkInvalidError(), "CONFIRMATION_LINK_INVALID"),
        (PendingConfirmationError(), "PENDING_CONFIRMATION"),
        (BookingRejectedError(), "BOOKING_REJECTED"),
        (TooManyRequestsError(retry_after=42), "TOO_MANY_REQUESTS"),
    ],
)
def test_each_error_has_its_stable_code(error: DomainError, code: str) -> None:
    assert isinstance(error, DomainError)
    assert error.code == code


def test_booking_not_possible_has_the_generic_message() -> None:
    assert str(BookingNotPossibleError()) == "Verifique sus datos ingresados."


def test_confirmation_link_invalid_message() -> None:
    assert str(ConfirmationLinkInvalidError()) == "El enlace no es válido o ya venció."


def test_too_many_requests_keeps_retry_after() -> None:
    assert TooManyRequestsError(retry_after=42).retry_after == 42
