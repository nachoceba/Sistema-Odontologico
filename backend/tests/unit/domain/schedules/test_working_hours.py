"""validate_working_hours: RN-HO-01, RN-HO-02 y bordes de la spec schedule-validation."""

from __future__ import annotations

from datetime import time

import pytest

from app.domain.appointments import WorkingHours
from app.domain.schedules import (
    ScheduleProblem,
    validate_working_hours,
)
from app.domain.schedules import (
    ScheduleProblemCode as Code,
)

MON, TUE, FRI, SUN = 0, 1, 4, 6


def wh(weekday: int, start: time, end: time) -> WorkingHours:
    return WorkingHours(weekday=weekday, start_time=start, end_time=end)


def codes(blocks: list[WorkingHours]) -> list[tuple[Code, tuple[int, ...]]]:
    return [(p.code, p.block_indexes) for p in validate_working_hours(blocks).problems]


def test_valid_weekly_schedule() -> None:
    result = validate_working_hours(
        [
            wh(MON, time(9), time(13)),
            wh(MON, time(14), time(18)),
            wh(2, time(9), time(13)),
        ]
    )
    assert result.valid is True
    assert result.problems == ()


def test_empty_schedule_is_valid() -> None:
    result = validate_working_hours([])
    assert result.valid is True
    assert result.problems == ()


@pytest.mark.parametrize(
    "block",
    [
        pytest.param(wh(MON, time(13), time(9)), id="inicio_posterior"),
        pytest.param(wh(MON, time(9), time(9)), id="duracion_cero"),
        pytest.param(wh(FRI, time(20), time(0)), id="cruza_medianoche"),
    ],
)
def test_start_not_before_end(block: WorkingHours) -> None:
    assert codes([block]) == [(Code.START_NOT_BEFORE_END, (0,))]


@pytest.mark.parametrize(
    ("blocks", "expected"),
    [
        pytest.param([wh(7, time(9), time(13))], [(Code.INVALID_WEEKDAY, (0,))], id="dia_7"),
        pytest.param(
            [wh(SUN, time(9), time(12)), wh(-1, time(9), time(12))],
            [(Code.INVALID_WEEKDAY, (1,))],
            id="dia_negativo_y_domingo",
        ),
    ],
)
def test_invalid_weekday(
    blocks: list[WorkingHours], expected: list[tuple[Code, tuple[int, ...]]]
) -> None:
    assert codes(blocks) == expected


@pytest.mark.parametrize(
    ("blocks", "pairs"),
    [
        pytest.param(
            [wh(MON, time(9), time(13)), wh(MON, time(12), time(15))], [(0, 1)], id="superpuestos"
        ),
        pytest.param(
            [wh(MON, time(9), time(18)), wh(MON, time(10), time(11))], [(0, 1)], id="contenido"
        ),
        pytest.param(
            [wh(MON, time(9), time(13)), wh(MON, time(9), time(13))], [(0, 1)], id="duplicado"
        ),
        pytest.param(
            [
                wh(MON, time(9), time(12)),
                wh(MON, time(10), time(13)),
                wh(MON, time(11), time(14)),
            ],
            [(0, 1), (0, 2), (1, 2)],
            id="tres_por_pares",
        ),
    ],
)
def test_overlapping_blocks(blocks: list[WorkingHours], pairs: list[tuple[int, int]]) -> None:
    assert codes(blocks) == [(Code.OVERLAPPING_BLOCKS, pair) for pair in pairs]


@pytest.mark.parametrize(
    "blocks",
    [
        pytest.param([wh(MON, time(9), time(13)), wh(MON, time(13), time(17))], id="contiguos"),
        pytest.param([wh(MON, time(9), time(13)), wh(TUE, time(9), time(13))], id="dias_distintos"),
    ],
)
def test_non_overlapping_blocks(blocks: list[WorkingHours]) -> None:
    assert validate_working_hours(blocks).valid is True


def test_input_order_does_not_change_result() -> None:
    a = wh(MON, time(12), time(15))
    b = wh(MON, time(9), time(13))
    forward = validate_working_hours([a, b])
    backward = validate_working_hours([b, a])
    assert [p.code for p in forward.problems] == [Code.OVERLAPPING_BLOCKS]
    assert [p.code for p in backward.problems] == [Code.OVERLAPPING_BLOCKS]
    # los indices siguen la posicion en la entrada de cada llamada
    assert forward.problems == (ScheduleProblem(Code.OVERLAPPING_BLOCKS, (0, 1)),)
    assert backward.problems == (ScheduleProblem(Code.OVERLAPPING_BLOCKS, (0, 1)),)


def test_invalid_block_skips_overlap_check() -> None:
    blocks = [wh(MON, time(15), time(8)), wh(MON, time(9), time(13))]
    assert codes(blocks) == [(Code.START_NOT_BEFORE_END, (0,))]


def test_sub_minute_precision() -> None:
    blocks = [wh(MON, time(9, 0, 30), time(13))]
    assert codes(blocks) == [(Code.SUB_MINUTE_PRECISION, (0,))]
    assert codes([wh(MON, time(9), time(13, 0, 0, 500))]) == [(Code.SUB_MINUTE_PRECISION, (0,))]


def test_block_shorter_than_slot_is_valid() -> None:
    assert validate_working_hours([wh(MON, time(9, 0), time(9, 15))]).valid is True


def test_multiple_problems_reported_together() -> None:
    blocks = [
        wh(MON, time(10), time(9)),
        wh(TUE, time(9), time(12)),
        wh(TUE, time(11), time(13)),
    ]
    result = validate_working_hours(blocks)
    assert result.valid is False
    assert [(p.code, p.block_indexes) for p in result.problems] == [
        (Code.START_NOT_BEFORE_END, (0,)),
        (Code.OVERLAPPING_BLOCKS, (1, 2)),
    ]


def test_problems_ordered_by_index_then_code() -> None:
    blocks = [
        wh(7, time(13), time(9)),  # dos problemas en el mismo tramo
        wh(MON, time(9), time(12, 0, 5)),
    ]
    assert codes(blocks) == [
        (Code.INVALID_WEEKDAY, (0,)),
        (Code.START_NOT_BEFORE_END, (0,)),
        (Code.SUB_MINUTE_PRECISION, (1,)),
    ]
