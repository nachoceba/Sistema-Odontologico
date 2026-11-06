"""Despachador que no hace nada: doble de tests (en produccion encola el de Celery)."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.appointments.types import Notification


class NoOpNotificationDispatcher:
    def dispatch(self, notifications: Sequence[Notification]) -> None:
        return None
