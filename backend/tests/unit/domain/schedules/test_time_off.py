"""Licencias: fecha dentro de una licencia (RN-HO-03) y validez (constraint de time_off)."""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.appointments import TimeOff
from app.domain.schedules import (
    ScheduleProblemCode,
    is_date_in_time_off,
    validate_time_off,
)

LEAVE = [TimeOff(starts_on=date(2026, 10, 12), ends_on=date(2026, 10, 16))]


@pytest.mark.parametrize(
    ("day", "leaves", "expected"),
    [
        pytest.param(date(2026, 10, 14), LEAVE, True, id="dentro"),
        pytest.param(date(2026, 10, 12), LEAVE, True, id="primer_dia"),
        pytest.param(date(2026, 10, 16), LEAVE, True, id="ultimo_dia"),
        pytest.param(date(2026, 10, 17), LEAVE, False, id="dia_siguiente"),
        pytest.param(date(2026, 10, 11), LEAVE, False, id="dia_anterior"),
        pytest.param(date(2026, 10, 14), [], False, id="sin_licencias"),
        pytest.param(
            date(2026, 10, 14),
            LEAVE + [TimeOff(date(2026, 10, 13), date(2026, 10, 20))],
            True,
            id="licencias_superpuestas",
        ),
    ],
)
def test_is_date_in_time_off(day: date, leaves: list[TimeOff], expected: bool) -> None:
    assert is_date_in_time_off(day, leaves) is expected


@pytest.mark.parametrize(
    ("starts_on", "ends_on", "valid"),
    [
        pytest.param(date(2026, 10, 12), date(2026, 10, 16), True, id="varios_dias"),
        pytest.param(date(2026, 10, 12), date(2026, 10, 12), True, id="un_solo_dia"),
        pytest.param(date(2026, 10, 16), date(2026, 10, 12), False, id="fin_antes_de_inicio"),
        pytest.param(date(2020, 1, 1), date(2020, 1, 3), True, id="pasada_aceptada"),
    ],
)
def test_validate_time_off(starts_on: date, ends_on: date, valid: bool) -> None:
    result = validate_time_off(TimeOff(starts_on=starts_on, ends_on=ends_on))
    assert result.valid is valid
    if valid:
        assert result.problems == ()
    else:
        assert [p.code for p in result.problems] == [ScheduleProblemCode.END_BEFORE_START]
        assert result.problems[0].block_indexes == ()
