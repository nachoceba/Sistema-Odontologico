"""Validacion previa de rangos compartida por los repositorios (design D-6)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.domain.appointments.ranges import (
    require_query_range,
    require_range,
    require_time_off_range,
)
from tests.unit.domain.appointments.helpers import monday


def test_valid_range_is_accepted() -> None:
    require_range(monday(10), monday(10, 30))


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        (datetime(2026, 10, 5, 13), monday(11), "zona"),
        (monday(10), datetime(2026, 10, 5, 14), "zona"),
        (monday(10), monday(10), "anterior"),
        (monday(11), monday(10), "anterior"),
    ],
)
def test_invalid_range_raises_value_error(start: datetime, end: datetime, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        require_range(start, end)


def test_query_range_allows_open_end_and_valid_pairs() -> None:
    require_query_range(monday(10), None)
    require_query_range(monday(10), monday(11))


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (datetime(2026, 10, 5, 13), None),
        (monday(10), datetime(2026, 10, 5, 14)),
        (monday(10), monday(10)),
        (monday(11), monday(10)),
    ],
)
def test_invalid_query_range_raises_value_error(start: datetime, end: datetime | None) -> None:
    with pytest.raises(ValueError):
        require_query_range(start, end)


def test_time_off_of_one_day_is_valid_and_inverted_is_not() -> None:
    require_time_off_range(date(2026, 10, 9), date(2026, 10, 9))
    with pytest.raises(ValueError, match="licencia"):
        require_time_off_range(date(2026, 10, 10), date(2026, 10, 9))
