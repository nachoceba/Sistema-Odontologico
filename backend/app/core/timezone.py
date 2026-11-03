"""Conversion unica entre UTC y la hora local del consultorio (RN-GL-01).

Solo libreria estandar. Supuesto SU-01: la zona no tiene horario de verano (sin
confirmar); el codigo igual calcula los limites del dia con la zona, sin asumir
que el dia dura 24 horas.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def to_local(instant: datetime, timezone_name: str) -> datetime:
    """Instante con zona -> hora local del consultorio (mismo instante).

    Lanza ValueError si ``instant`` no tiene zona horaria.
    """
    if instant.tzinfo is None:
        raise ValueError("instant debe ser un datetime con zona horaria")
    return instant.astimezone(ZoneInfo(timezone_name))


def to_utc(local_naive: datetime, timezone_name: str) -> datetime:
    """Hora de reloj local del consultorio (sin zona) -> instante UTC.

    Lanza ValueError si ``local_naive`` ya trae zona horaria (no se reinterpreta).
    """
    if local_naive.tzinfo is not None:
        raise ValueError("local_naive no debe traer zona horaria")
    return local_naive.replace(tzinfo=ZoneInfo(timezone_name)).astimezone(UTC)


def local_day_bounds(day: date, timezone_name: str) -> tuple[datetime, datetime]:
    """Inicio (incluido) y fin (excluido) del dia local, ambos en UTC."""
    start = to_utc(datetime.combine(day, time.min), timezone_name)
    end = to_utc(datetime.combine(day + timedelta(days=1), time.min), timezone_name)
    return start, end
