"""Tests de app.core.timezone (spec clinic-timezone). Datos ficticios."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.timezone import local_day_bounds, to_local, to_utc

BA = "America/Argentina/Buenos_Aires"
UTC = UTC


@pytest.mark.parametrize(
    ("instant", "expected_local", "expected_offset"),
    [
        pytest.param(
            datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
            (2026, 10, 5, 9, 0),
            timedelta(hours=-3),
            id="conversion_simple_12utc_09local",
        ),
        pytest.param(
            datetime(2026, 10, 6, 1, 30, tzinfo=UTC),
            (2026, 10, 5, 22, 30),
            timedelta(hours=-3),
            id="cambia_fecha_0130utc_martes_es_2230_lunes",
        ),
    ],
)
def test_to_local_converts_utc_instant(
    instant: datetime, expected_local: tuple[int, int, int, int, int], expected_offset: timedelta
) -> None:
    result = to_local(instant, BA)

    assert (result.year, result.month, result.day, result.hour, result.minute) == expected_local
    assert result.utcoffset() == expected_offset
    assert result == instant  # mismo instante, otra representacion


def test_to_local_rejects_naive_instant() -> None:
    with pytest.raises(ValueError):
        to_local(datetime(2026, 10, 5, 12, 0), BA)


@pytest.mark.parametrize(
    ("local_naive", "expected_utc"),
    [
        pytest.param(
            datetime(2026, 10, 5, 9, 0),
            datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
            id="hora_local_0900_es_1200utc",
        ),
        pytest.param(
            datetime(2026, 10, 5, 23, 30),
            datetime(2026, 10, 6, 2, 30, tzinfo=UTC),
            id="hora_local_2330_pasa_al_dia_siguiente_utc",
        ),
    ],
)
def test_to_utc_converts_local_wall_clock(local_naive: datetime, expected_utc: datetime) -> None:
    result = to_utc(local_naive, BA)

    assert result == expected_utc
    assert result.utcoffset() == timedelta(0)


def test_to_utc_rejects_aware_datetime() -> None:
    with pytest.raises(ValueError):
        to_utc(datetime(2026, 10, 5, 9, 0, tzinfo=UTC), BA)


def test_local_day_bounds() -> None:
    start, end = local_day_bounds(date(2026, 10, 5), BA)

    assert start == datetime(2026, 10, 5, 3, 0, tzinfo=UTC)
    assert end == datetime(2026, 10, 6, 3, 0, tzinfo=UTC)
    assert start.utcoffset() == timedelta(0) and end.utcoffset() == timedelta(0)
    assert end - start == timedelta(hours=24)


def test_day_end_belongs_to_next_day() -> None:
    instant = datetime(2026, 10, 6, 3, 0, tzinfo=UTC)

    local_instant = to_local(instant, BA)
    tuesday_start, _ = local_day_bounds(date(2026, 10, 6), BA)
    monday_start, monday_end = local_day_bounds(date(2026, 10, 5), BA)

    assert local_instant.date() == date(2026, 10, 6)
    assert (local_instant.hour, local_instant.minute) == (0, 0)
    assert instant == tuesday_start == monday_end
    assert not (monday_start <= instant < monday_end)
