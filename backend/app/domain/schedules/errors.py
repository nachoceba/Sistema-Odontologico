"""Errores de dominio de horarios y licencias (design D-2). Solo libreria estandar.

Los mensajes nombran el problema y la posicion 1-based de cada tramo para personas;
nunca incluyen horas ni textos enviados por el cliente.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from app.core.errors import DomainError
from app.domain.schedules.validation import ScheduleProblem, ScheduleProblemCode


def _describe(problem: ScheduleProblem) -> str:
    positions = [index + 1 for index in problem.block_indexes]
    if problem.code is ScheduleProblemCode.OVERLAPPING_BLOCKS:
        names = " y ".join(str(position) for position in positions)
        return f"Los tramos {names} se superponen"
    subject = f"El tramo {positions[0]}" if len(positions) == 1 else "Un tramo"
    texts = {
        ScheduleProblemCode.START_NOT_BEFORE_END: "tiene el inicio después del fin",
        ScheduleProblemCode.INVALID_WEEKDAY: "tiene un día de la semana inválido",
        ScheduleProblemCode.SUB_MINUTE_PRECISION: "tiene horas con segundos",
        ScheduleProblemCode.END_BEFORE_START: "tiene el fin antes del inicio",
    }
    return f"{subject} {texts[problem.code]}"


class InvalidWorkingHoursError(DomainError):
    """La semana de tramos enviada no es valida; lleva cada problema encontrado."""

    code: ClassVar[str] = "INVALID_WORKING_HOURS"

    def __init__(self, problems: Sequence[ScheduleProblem]) -> None:
        self.problems = tuple(problems)
        super().__init__(". ".join(_describe(problem) for problem in self.problems) + ".")


class InvalidTimeOffError(DomainError):
    """La licencia tiene la fecha de fin anterior a la de inicio."""

    code: ClassVar[str] = "INVALID_TIME_OFF"

    def __init__(self) -> None:
        super().__init__("La fecha de fin no puede ser anterior a la de inicio.")


class TimeOffNotFoundError(DomainError):
    """No existe esa licencia para ese profesional."""

    code: ClassVar[str] = "TIME_OFF_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__("La licencia no existe")
