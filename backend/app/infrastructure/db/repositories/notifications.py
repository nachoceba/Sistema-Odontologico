"""Registro de notificaciones sobre PostgreSQL (design D-6).

``UNIQUE (turno, tipo, horario)`` evita duplicados (RN-NO-03): el alta usa
``INSERT ... ON CONFLICT DO NOTHING`` para no abortar la transaccion externa cuando la fila ya
existe. No envia nada: el envio es de C-11.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from app.domain.appointments.types import Notification, NotificationKind, NotificationStatus
from app.infrastructure.db import enums
from app.infrastructure.db.models import EmailNotificationModel
from app.infrastructure.db.repositories._ids import parse_uuid
from app.infrastructure.db.scope import SessionScope

UNIQUE_NAME = "uq_email_notifications_appointment_kind_starts_at"


def _to_domain(row: EmailNotificationModel) -> Notification:
    return Notification(
        id=str(row.id),
        appointment_id=str(row.appointment_id),
        kind=NotificationKind(row.kind.value),
        status=NotificationStatus(row.status.value),
        sent_at=None if row.sent_at is None else row.sent_at.astimezone(UTC),
        error=row.error,
        appointment_starts_at=row.appointment_starts_at.astimezone(UTC),
    )


def _required_uuid(value: str) -> uuid.UUID:
    key = parse_uuid(value)
    if key is None:
        raise ValueError("identificador de turno invalido")
    return key


class SqlAlchemyNotificationRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        *,
        scope: SessionScope | None = None,
    ) -> None:
        self._scope = scope if scope is not None else SessionScope(session_factory)

    def add_pending_confirmation(
        self, appointment_id: str, starts_at: datetime
    ) -> Notification | None:
        statement = (
            pg_insert(EmailNotificationModel)
            .values(
                appointment_id=_required_uuid(appointment_id),
                kind=enums.NotificationKind.CONFIRMATION,
                status=enums.NotificationStatus.PENDING,
                appointment_starts_at=starts_at,
            )
            .on_conflict_do_nothing(constraint=UNIQUE_NAME)
            .returning(EmailNotificationModel)
        )
        with self._scope.write() as session:
            row = session.scalars(statement).first()
            return None if row is None else _to_domain(row)

    def delete_pending(self, appointment_id: str, *, starts_at: datetime | None = None) -> int:
        key = parse_uuid(appointment_id)
        if key is None:
            return 0
        statement = delete(EmailNotificationModel).where(
            EmailNotificationModel.appointment_id == key,
            EmailNotificationModel.status == enums.NotificationStatus.PENDING,
        )
        if starts_at is not None:
            statement = statement.where(EmailNotificationModel.appointment_starts_at == starts_at)
        with self._scope.write() as session:
            result = session.execute(statement)
            return int(result.rowcount)  # type: ignore[attr-defined]

    def list_for_appointment(self, appointment_id: str) -> list[Notification]:
        key = parse_uuid(appointment_id)
        if key is None:
            return []
        query = (
            select(EmailNotificationModel)
            .where(EmailNotificationModel.appointment_id == key)
            .order_by(EmailNotificationModel.appointment_starts_at, EmailNotificationModel.kind)
        )
        with self._scope.read() as session:
            return [_to_domain(row) for row in session.scalars(query)]
