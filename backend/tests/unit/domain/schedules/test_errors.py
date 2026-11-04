"""Errores de dominio de horarios y licencias (design D-2)."""

from __future__ import annotations

from app.core.errors import DomainError
from app.domain.schedules.errors import (
    InvalidTimeOffError,
    InvalidWorkingHoursError,
    TimeOffNotFoundError,
)
from app.domain.schedules.validation import ScheduleProblem, ScheduleProblemCode


def test_error_codes_are_stable() -> None:
    assert InvalidWorkingHoursError.code == "INVALID_WORKING_HOURS"
    assert InvalidTimeOffError.code == "INVALID_TIME_OFF"
    assert TimeOffNotFoundError.code == "TIME_OFF_NOT_FOUND"
    assert issubclass(TimeOffNotFoundError, DomainError)


def test_working_hours_error_message_names_blocks_one_based() -> None:
    problems = (
        ScheduleProblem(ScheduleProblemCode.OVERLAPPING_BLOCKS, (0, 1)),
        ScheduleProblem(ScheduleProblemCode.START_NOT_BEFORE_END, (2,)),
    )
    error = InvalidWorkingHoursError(problems)
    assert error.problems == problems
    assert "Los tramos 1 y 2 se superponen" in str(error)
    assert "El tramo 3 tiene el inicio después del fin" in str(error)


def test_working_hours_error_message_other_problems() -> None:
    problems = (
        ScheduleProblem(ScheduleProblemCode.INVALID_WEEKDAY, (4,)),
        ScheduleProblem(ScheduleProblemCode.SUB_MINUTE_PRECISION, (0,)),
    )
    message = str(InvalidWorkingHoursError(problems))
    assert "El tramo 5 tiene un día de la semana inválido" in message
    assert "El tramo 1 tiene horas con segundos" in message


def test_time_off_error_message_has_no_user_text() -> None:
    assert "fecha de fin" in str(InvalidTimeOffError())
