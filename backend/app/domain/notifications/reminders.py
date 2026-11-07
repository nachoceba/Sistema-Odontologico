"""Regla pura de la pasada de recordatorios (spec reminder-scheduling, design D-1, D-2).

Solo libreria estandar y ``app.core.timezone``: decide si la pasada actua y a que dia local
apunta, a partir del instante actual, la zona del consultorio y la hora configurada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.core.timezone import to_local


def reminder_target_day(
    now: datetime, timezone_name: str, send_hour: int, *, force: bool = False
) -> date | None:
    """Dia local siguiente al de ``now`` si la pasada actua, o ``None`` si no es la hora.

    Actua cuando la hora local de ``now`` es ``send_hour`` (cualquier minuto de esa hora) o
    cuando ``force`` es verdadero. Lanza ``ValueError`` si ``now`` no tiene zona horaria.
    """
    local_now = to_local(now, timezone_name)
    if not force and local_now.hour != send_hour:
        return None
    return local_now.date() + timedelta(days=1)


@dataclass(frozen=True)
class ReminderRunSummary:
    """Cantidades de una pasada que actuo: solo numeros, ningun dato del paciente (DD-77)."""

    sent: int = 0
    failed: int = 0
    pending: int = 0

    @property
    def processed(self) -> int:
        """Recordatorios registrados en la pasada: ``sent + failed + pending``."""
        return self.sent + self.failed + self.pending

    def log_text(self) -> str:
        return (
            f"recordatorios: processed={self.processed} sent={self.sent} "
            f"failed={self.failed} pending={self.pending}"
        )
