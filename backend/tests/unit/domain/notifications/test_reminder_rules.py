"""Regla pura de la pasada de recordatorios (spec reminder-scheduling)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.domain.notifications import ReminderRunSummary, reminder_target_day

BA = "America/Argentina/Buenos_Aires"


def test_acts_at_the_configured_local_hour_and_targets_the_next_local_day() -> None:
    # Domingo 08/11/2026 a las 09:00 locales (UTC-3) = 12:00 UTC.
    now = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)

    assert reminder_target_day(now, BA, 9) == date(2026, 11, 9)


@pytest.mark.parametrize(
    "now",
    [
        datetime(2026, 11, 8, 12, 0, 0, tzinfo=UTC),  # 09:00:00 locales
        datetime(2026, 11, 8, 12, 59, 59, tzinfo=UTC),  # 09:59:59 locales
    ],
)
def test_acts_at_any_moment_of_the_configured_hour(now: datetime) -> None:
    assert reminder_target_day(now, BA, 9) == date(2026, 11, 9)


@pytest.mark.parametrize(
    "now",
    [
        datetime(2026, 11, 8, 11, 59, 59, tzinfo=UTC),  # 08:59:59 locales
        datetime(2026, 11, 8, 13, 0, 0, tzinfo=UTC),  # 10:00:00 locales
    ],
)
def test_does_not_act_one_second_outside_the_configured_hour(now: datetime) -> None:
    assert reminder_target_day(now, BA, 9) is None


def test_the_hour_is_measured_in_the_clinic_zone_not_in_utc() -> None:
    # 09:00 UTC son las 06:00 locales: no es la hora configurada.
    assert reminder_target_day(datetime(2026, 11, 8, 9, 0, tzinfo=UTC), BA, 9) is None


@pytest.mark.parametrize(
    ("send_hour", "now", "expected"),
    [
        (0, datetime(2026, 11, 8, 3, 30, tzinfo=UTC), date(2026, 11, 9)),  # 00:30 locales
        (23, datetime(2026, 11, 9, 2, 30, tzinfo=UTC), date(2026, 11, 9)),  # dom 23:30 locales
    ],
)
def test_extreme_configured_hours_zero_and_twenty_three(
    send_hour: int, now: datetime, expected: date
) -> None:
    assert reminder_target_day(now, BA, send_hour) == expected


def test_new_year_rolls_over_to_the_next_year() -> None:
    now = datetime(2026, 12, 31, 12, 0, tzinfo=UTC)  # 09:00 locales

    assert reminder_target_day(now, BA, 9) == date(2027, 1, 1)


def test_force_acts_outside_the_hour_with_the_same_target_day() -> None:
    now = datetime(2026, 11, 8, 18, 0, tzinfo=UTC)  # 15:00 locales

    assert reminder_target_day(now, BA, 9, force=True) == date(2026, 11, 9)
    assert reminder_target_day(now, BA, 9) is None


def test_an_instant_without_zone_is_rejected() -> None:
    with pytest.raises(ValueError, match="zona horaria"):
        reminder_target_day(datetime(2026, 11, 8, 9, 0), BA, 9)


def test_summary_counts_processed_as_the_sum_and_renders_a_log_line() -> None:
    summary = ReminderRunSummary(sent=3, failed=1, pending=0)

    assert summary.processed == 4
    assert summary.log_text() == "recordatorios: processed=4 sent=3 failed=1 pending=0"


def test_an_empty_summary_reports_zero_everywhere() -> None:
    assert ReminderRunSummary().log_text() == (
        "recordatorios: processed=0 sent=0 failed=0 pending=0"
    )
    assert ReminderRunSummary(sent=1, failed=2, pending=3).processed == 6
