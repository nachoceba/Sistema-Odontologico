"""Validacion de horarios de trabajo y licencias de un profesional.

Funciones puras, solo libreria estandar. Los tipos WorkingHours y TimeOff viven en
app.domain.appointments.types (design D-2); la dependencia es schedules -> tipos.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import time
from enum import Enum
from itertools import combinations

from app.domain.appointments.types import TimeOff, WorkingHours


class ScheduleProblemCode(Enum):
    START_NOT_BEFORE_END = "START_NOT_BEFORE_END"
    INVALID_WEEKDAY = "INVALID_WEEKDAY"
    OVERLAPPING_BLOCKS = "OVERLAPPING_BLOCKS"
    SUB_MINUTE_PRECISION = "SUB_MINUTE_PRECISION"
    END_BEFORE_START = "END_BEFORE_START"


@dataclass(frozen=True)
class ScheduleProblem:
    """Un problema; block_indexes son posiciones en la entrada original."""

    code: ScheduleProblemCode
    block_indexes: tuple[int, ...] = ()


@dataclass(frozen=True)
class ScheduleValidationResult:
    """valid <=> problems vacio."""

    valid: bool
    problems: tuple[ScheduleProblem, ...] = ()

    @classmethod
    def from_problems(cls, problems: Sequence[ScheduleProblem]) -> ScheduleValidationResult:
        return cls(valid=not problems, problems=tuple(problems))


def validate_time_off(leave: TimeOff) -> ScheduleValidationResult:
    """Constraint de time_off: starts_on <= ends_on. No mira otras licencias ni la fecha actual."""
    if leave.starts_on > leave.ends_on:
        return ScheduleValidationResult.from_problems(
            [ScheduleProblem(ScheduleProblemCode.END_BEFORE_START)]
        )
    return ScheduleValidationResult.from_problems([])


def _is_whole_minute(moment: time) -> bool:
    return moment.second == 0 and moment.microsecond == 0


def _problem_sort_key(problem: ScheduleProblem) -> tuple[int, str, tuple[int, ...]]:
    first = problem.block_indexes[0] if problem.block_indexes else -1
    return (first, problem.code.value, problem.block_indexes)


def validate_working_hours(blocks: Sequence[WorkingHours]) -> ScheduleValidationResult:
    """RN-HO-01 / RN-HO-02: revisa el conjunto completo de tramos y informa todos los problemas.

    Primero los problemas individuales (dia 0-6, minutos exactos, inicio < fin, sin cruzar la
    medianoche); luego, solo entre tramos sin problemas individuales, la superposicion de
    intervalos semiabiertos del mismo dia (tramos contiguos NO se superponen). Los
    ``block_indexes`` son posiciones en la entrada; el orden de salida es determinista.
    No detecta turnos en conflicto con el horario (RN-HO-04, eso es de C-07).
    """
    problems: list[ScheduleProblem] = []
    clean: list[int] = []
    for index, block in enumerate(blocks):
        individual: list[ScheduleProblemCode] = []
        if not 0 <= block.weekday <= 6:
            individual.append(ScheduleProblemCode.INVALID_WEEKDAY)
        if not (_is_whole_minute(block.start_time) and _is_whole_minute(block.end_time)):
            individual.append(ScheduleProblemCode.SUB_MINUTE_PRECISION)
        if block.start_time >= block.end_time:
            individual.append(ScheduleProblemCode.START_NOT_BEFORE_END)
        problems.extend(ScheduleProblem(code, (index,)) for code in individual)
        if not individual:
            clean.append(index)

    by_weekday: dict[int, list[int]] = {}
    for index in clean:
        by_weekday.setdefault(blocks[index].weekday, []).append(index)
    for indexes in by_weekday.values():
        for first, second in combinations(indexes, 2):
            a, b = blocks[first], blocks[second]
            if a.start_time < b.end_time and b.start_time < a.end_time:
                problems.append(
                    ScheduleProblem(ScheduleProblemCode.OVERLAPPING_BLOCKS, (first, second))
                )

    return ScheduleValidationResult.from_problems(sorted(problems, key=_problem_sort_key))
