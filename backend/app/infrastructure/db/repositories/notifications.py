"""Registro de notificaciones sobre PostgreSQL (design D-6).

``UNIQUE (turno, tipo, horario)`` evita duplicados (RN-NO-03): el alta usa
``INSERT ... ON CONFLICT DO NOTHING`` para no abortar la transaccion externa cuando la fila ya
existe. Tambien toma la fila a enviar y registra el resultado (C-11).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, literal, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql.dml import ReturningInsert

from app.domain.appointments.types import (
    AppointmentStatus,
    Notification,
    NotificationKind,
    NotificationStatus,
)
from app.infrastructure.db import enums
from app.infrastructure.db.models import AppointmentModel, EmailNotificationModel
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
        return self._add_pending(appointment_id, enums.NotificationKind.CONFIRMATION, starts_at)

    def add_pending_booking_expired(
        self, appointment_id: str, starts_at: datetime
    ) -> Notification | None:
        return self._add_pending(appointment_id, enums.NotificationKind.BOOKING_EXPIRED, starts_at)

    def _add_pending(
        self, appointment_id: str, kind: enums.NotificationKind, starts_at: datetime
    ) -> Notification | None:
        statement = (
            pg_insert(EmailNotificationModel)
            .values(
                appointment_id=_required_uuid(appointment_id),
                kind=kind,
                status=enums.NotificationStatus.PENDING,
                appointment_starts_at=starts_at,
            )
            .on_conflict_do_nothing(constraint=UNIQUE_NAME)
            .returning(EmailNotificationModel)
        )
        return self._insert_returning(statement)

    def add_pending_reminder(self, appointment_id: str, starts_at: datetime) -> Notification | None:
        key = parse_uuid(appointment_id)
        if key is None:
            return None
        # Un solo INSERT ... SELECT: ``FOR SHARE`` espera a una reprogramacion o cancelacion en
        # curso (que tiene el turno con ``FOR UPDATE``) y vuelve a evaluar la condicion con el
        # dato confirmado, asi nunca queda una ``pending`` con un horario viejo (design D-4).
        vigente = (
            select(
                AppointmentModel.id,
                literal(enums.NotificationKind.REMINDER, EmailNotificationModel.kind.type),
                literal(enums.NotificationStatus.PENDING, EmailNotificationModel.status.type),
                AppointmentModel.starts_at,
            )
            .where(
                AppointmentModel.id == key,
                AppointmentModel.status == AppointmentStatus.SCHEDULED,
                AppointmentModel.starts_at == starts_at,
            )
            .with_for_update(read=True)
        )
        statement = (
            pg_insert(EmailNotificationModel)
            .from_select(["appointment_id", "kind", "status", "appointment_starts_at"], vigente)
            .on_conflict_do_nothing(constraint=UNIQUE_NAME)
            .returning(EmailNotificationModel)
        )
        return self._insert_returning(statement)

    def _insert_returning(
        self, statement: ReturningInsert[EmailNotificationModel]
    ) -> Notification | None:
        """Corre un alta con ``ON CONFLICT DO NOTHING``: la fila nueva, o ``None`` si no entro."""
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

    def list_pending_created_before(self, before: datetime, limit: int) -> list[Notification]:
        query = (
            select(EmailNotificationModel)
            .where(
                EmailNotificationModel.status == enums.NotificationStatus.PENDING,
                EmailNotificationModel.created_at < before,
            )
            .order_by(EmailNotificationModel.created_at, EmailNotificationModel.id)
            .limit(limit)
        )
        with self._scope.read() as session:
            return [_to_domain(row) for row in session.scalars(query)]

    def claim_pending(self, notification_id: str) -> Notification | None:
        key = parse_uuid(notification_id)
        if key is None:
            return None
        query = (
            select(EmailNotificationModel)
            .where(
                EmailNotificationModel.id == key,
                EmailNotificationModel.status == enums.NotificationStatus.PENDING,
            )
            .with_for_update(skip_locked=True)
        )
        with self._scope.write() as session:
            row = session.scalars(query).first()
            return None if row is None else _to_domain(row)

    def mark_sent(self, notification_id: str, sent_at: datetime) -> bool:
        return self._mark_pending(
            notification_id,
            status=enums.NotificationStatus.SENT,
            sent_at=sent_at,
            error=None,
        )

    def mark_failed(self, notification_id: str, error: str) -> bool:
        return self._mark_pending(
            notification_id,
            status=enums.NotificationStatus.FAILED,
            sent_at=None,
            error=error,
        )

    def _mark_pending(
        self,
        notification_id: str,
        *,
        status: enums.NotificationStatus,
        sent_at: datetime | None,
        error: str | None,
    ) -> bool:
        key = parse_uuid(notification_id)
        if key is None:
            return False
        statement = (
            update(EmailNotificationModel)
            .where(
                EmailNotificationModel.id == key,
                EmailNotificationModel.status == enums.NotificationStatus.PENDING,
            )
            .values(status=status, sent_at=sent_at, error=error)
        )
        with self._scope.write() as session:
            return int(session.execute(statement).rowcount) > 0  # type: ignore[attr-defined]

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
