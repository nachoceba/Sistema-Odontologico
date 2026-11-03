"""Transiciones de estado y reprogramacion (RN-TU-05, RN-TU-06, RN-TU-07, US-010)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.appointments import (
    AppointmentStatus as S,
)
from app.domain.appointments import (
    TransitionRejection as R,
)
from app.domain.appointments import (
    TransitionResult,
    validate_reschedule_eligibility,
    validate_status_change,
)
from tests.unit.domain.appointments.helpers import BA, local, monday

STARTS_AT = monday(10)  # lunes 5/10/2026 10:00 local
SATURDAY = local(2026, 10, 3, 10)
ALL_TARGETS = [S.COMPLETED, S.NO_SHOW, S.SCHEDULED, S.CANCELLED]


def change(current: S, target: S, now: datetime) -> TransitionResult:
    return validate_status_change(current, target, STARTS_AT, now)


def test_cancel_before_start_is_allowed() -> None:
    result = change(S.SCHEDULED, S.CANCELLED, SATURDAY)
    assert result == TransitionResult.accept()
    assert result.allowed is True and result.reason is None


@pytest.mark.parametrize("target", ALL_TARGETS)
def test_cancelled_is_final(target: S) -> None:
    result = change(S.CANCELLED, target, monday(11))
    assert result == TransitionResult.reject(R.CANCELLED_IS_FINAL)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        pytest.param(S.COMPLETED, S.NO_SHOW, id="completed_a_no_show"),
        pytest.param(S.COMPLETED, S.CANCELLED, id="completed_a_cancelled"),
        pytest.param(S.NO_SHOW, S.COMPLETED, id="no_show_a_completed"),
    ],
)
def test_attendance_already_recorded(current: S, target: S) -> None:
    assert change(current, target, monday(11)).reason is R.ATTENDANCE_ALREADY_RECORDED


def test_target_scheduled_is_invalid() -> None:
    assert change(S.SCHEDULED, S.SCHEDULED, SATURDAY) == TransitionResult.reject(
        R.INVALID_TARGET_STATUS
    )


@pytest.mark.parametrize(
    ("target", "now"),
    [
        pytest.param(S.COMPLETED, monday(10, 20), id="completed_despues_inicio"),
        pytest.param(S.COMPLETED, monday(10, 0), id="inicio_exacto"),
        pytest.param(S.NO_SHOW, local(2026, 10, 8, 10), id="dias_despues"),
    ],
)
def test_mark_attendance(target: S, now: datetime) -> None:
    assert change(S.SCHEDULED, target, now).allowed is True


@pytest.mark.parametrize(
    ("target", "now"),
    [
        pytest.param(S.NO_SHOW, monday(9, 59), id="no_show_0959"),
        pytest.param(
            S.COMPLETED,
            datetime(2026, 10, 5, 9, 59, tzinfo=BA),  # 09:59 UTC-3 = 12:59 UTC
            id="instantes_no_hora_local",
        ),
    ],
)
def test_mark_before_start_rejected(target: S, now: datetime) -> None:
    assert change(S.SCHEDULED, target, now) == TransitionResult.reject(R.NOT_STARTED_YET)


def test_cancel_one_minute_before() -> None:
    assert change(S.SCHEDULED, S.CANCELLED, monday(9, 59)).allowed is True


def test_cancel_after_start_rejected() -> None:
    assert change(S.SCHEDULED, S.CANCELLED, monday(10, 0)) == TransitionResult.reject(
        R.ALREADY_STARTED
    )
    assert change(S.SCHEDULED, S.CANCELLED, monday(10, 1)).reason is R.ALREADY_STARTED


def test_aware_non_utc_now_is_compared_as_instant() -> None:
    now = datetime(2026, 10, 5, 10, 0, tzinfo=BA)  # 13:00 UTC = inicio exacto
    assert change(S.SCHEDULED, S.COMPLETED, now).allowed is True
    assert change(S.SCHEDULED, S.CANCELLED, now).reason is R.ALREADY_STARTED


@pytest.mark.parametrize(
    ("starts_at", "now"),
    [
        pytest.param(STARTS_AT, datetime(2026, 10, 3, 10, 0), id="now_naive"),
        pytest.param(datetime(2026, 10, 5, 13, 0), SATURDAY, id="inicio_naive"),
    ],
)
def test_naive_datetime_raises(starts_at: datetime, now: datetime) -> None:
    with pytest.raises(ValueError):
        validate_status_change(S.SCHEDULED, S.CANCELLED, starts_at, now)
    with pytest.raises(ValueError):
        validate_reschedule_eligibility(S.SCHEDULED, starts_at, now)


@pytest.mark.parametrize(
    ("current", "now", "expected"),
    [
        pytest.param(S.SCHEDULED, SATURDAY, None, id="futuro_permitido"),
        pytest.param(S.CANCELLED, SATURDAY, R.CANCELLED_IS_FINAL, id="cancelado"),
        pytest.param(S.SCHEDULED, monday(10, 0), R.ALREADY_STARTED, id="ya_iniciado"),
        pytest.param(S.COMPLETED, SATURDAY, R.ATTENDANCE_ALREADY_RECORDED, id="completed"),
        pytest.param(S.NO_SHOW, SATURDAY, R.ATTENDANCE_ALREADY_RECORDED, id="no_show"),
    ],
)
def test_reschedule_eligibility(current: S, now: datetime, expected: R | None) -> None:
    result = validate_reschedule_eligibility(current, STARTS_AT, now)
    assert result.reason is expected
    assert result.allowed is (expected is None)


def test_utc_offset_zero_now_equals_start_boundary() -> None:
    now = STARTS_AT.astimezone(UTC) - timedelta(seconds=1)
    assert change(S.SCHEDULED, S.CANCELLED, now).allowed is True
