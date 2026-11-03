"""Consulta de licencias (RN-HO-03). Unica fuente de la regla (design D-3).

TimeOff se importa solo para tipado: asi appointments/rules.py puede importar este
modulo sin crear un ciclo de imports con app.domain.appointments.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.appointments.types import TimeOff


def is_date_in_time_off(local_date: date, time_off: Sequence[TimeOff]) -> bool:
    """RN-HO-03: la fecha local cae en una licencia [starts_on, ends_on] inclusiva."""
    return any(leave.starts_on <= local_date <= leave.ends_on for leave in time_off)
