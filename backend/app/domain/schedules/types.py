"""Tipos con identidad de horarios y licencias (design D-3).

TimeOff se importa en tiempo de ejecucion igual que en validation.py; este modulo se
importa al final de ``schedules/__init__`` para no reintroducir el ciclo (D-2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain.appointments.types import TimeOff


@dataclass(frozen=True)
class TimeOffEntry:
    """Licencia guardada: fechas locales inclusivas y motivo opcional (US-005)."""

    id: str
    professional_id: str
    starts_on: date
    ends_on: date
    reason: str | None

    def to_time_off(self) -> TimeOff:
        """Dato que consumen validate_appointment, compute_slots e is_date_in_time_off."""
        return TimeOff(starts_on=self.starts_on, ends_on=self.ends_on)
