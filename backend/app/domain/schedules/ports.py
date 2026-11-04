"""Puertos de horarios y licencias. Los tipos solo se importan para anotar (D-2)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.appointments.types import WorkingHours
    from app.domain.schedules.types import TimeOffEntry


class WorkingHoursRepository(Protocol):
    """No valida los tramos: el caso de uso llama antes a validate_working_hours (D-8)."""

    def list_for_professional(self, professional_id: str) -> list[WorkingHours]:
        """Tramos ordenados por dia de la semana y hora de inicio."""
        ...

    def replace_for_professional(
        self, professional_id: str, blocks: Sequence[WorkingHours]
    ) -> None:
        """Sustituye el conjunto completo de tramos del profesional."""
        ...


class TimeOffRepository(Protocol):
    def add(
        self,
        professional_id: str,
        starts_on: date,
        ends_on: date,
        reason: str | None = None,
    ) -> TimeOffEntry:
        """Guarda una licencia; ValueError si ends_on < starts_on."""
        ...

    def list_for_professional(self, professional_id: str) -> list[TimeOffEntry]:
        """Todas las licencias del profesional, ordenadas por fecha de inicio."""
        ...

    def delete(self, professional_id: str, time_off_id: str) -> bool:
        """Borra la licencia de ese profesional; False si no existe, es de otro o el id es malo."""
        ...
