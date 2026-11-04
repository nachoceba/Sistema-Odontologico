"""Registro de notificaciones en memoria: doble fiel de ``email_notifications`` (D-6).

Respeta el ``UNIQUE (turno, tipo, horario)`` de la base. No es seguro entre hilos.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.domain.appointments.types import Notification, NotificationKind, NotificationStatus


class InMemoryNotificationRepository:
    def __init__(self) -> None:
        self._rows: dict[str, Notification] = {}

    def snapshot(self) -> dict[str, Notification]:
        """Copia del estado, para que la unidad de trabajo pueda revertir."""
        return dict(self._rows)

    def restore(self, state: dict[str, Notification]) -> None:
        self._rows = dict(state)

    def add_pending_confirmation(
        self, appointment_id: str, starts_at: datetime
    ) -> Notification | None:
        if self._exists(appointment_id, NotificationKind.CONFIRMATION, starts_at):
            return None
        return self.seed(
            appointment_id, NotificationKind.CONFIRMATION, NotificationStatus.PENDING, starts_at
        )

    def delete_pending(self, appointment_id: str, *, starts_at: datetime | None = None) -> int:
        doomed = [
            row.id
            for row in self._rows.values()
            if row.appointment_id == appointment_id
            and row.status is NotificationStatus.PENDING
            and (starts_at is None or row.appointment_starts_at == starts_at)
        ]
        for row_id in doomed:
            del self._rows[row_id]
        return len(doomed)

    def list_for_appointment(self, appointment_id: str) -> list[Notification]:
        rows = [row for row in self._rows.values() if row.appointment_id == appointment_id]
        return sorted(rows, key=lambda row: (row.appointment_starts_at, row.kind.value))

    def seed(
        self,
        appointment_id: str,
        kind: NotificationKind,
        status: NotificationStatus,
        starts_at: datetime,
    ) -> Notification:
        """Carga una fila con cualquier estado (atajo de tests: el envio es de C-11)."""
        if self._exists(appointment_id, kind, starts_at):
            raise ValueError("ya existe una notificacion con ese turno, tipo y horario")
        row = Notification(
            id=str(uuid4()),
            appointment_id=appointment_id,
            kind=kind,
            status=status,
            sent_at=starts_at if status is NotificationStatus.SENT else None,
            error="fallo simulado" if status is NotificationStatus.FAILED else None,
            appointment_starts_at=starts_at,
        )
        self._rows[row.id] = row
        return row

    def _exists(self, appointment_id: str, kind: NotificationKind, starts_at: datetime) -> bool:
        return any(
            row.appointment_id == appointment_id
            and row.kind is kind
            and row.appointment_starts_at == starts_at
            for row in self._rows.values()
        )
