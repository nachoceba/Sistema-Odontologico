"""Despachador de notificaciones de C-08: no hace nada (C-11 lo reemplaza por el encolado)."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.appointments.types import Notification


class NoOpNotificationDispatcher:
    def dispatch(self, notifications: Sequence[Notification]) -> None:
        return None
