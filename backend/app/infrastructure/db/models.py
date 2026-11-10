"""Modelos SQLAlchemy 2.0 de las 8 tablas de ``04_modelo_de_datos.md`` (design D-1, D-3 a D-5).

Solo describen el esquema; el dominio no los importa (regla dura 2) y los repositorios
convierten fila <-> tipo de dominio. La migracion ``0001_initial_schema`` se escribe a mano:
estos modelos son la referencia contra la que un test la compara.

Notas de diseno:
- Enumerados nativos de PostgreSQL con los *valores* del dominio (``values_callable``);
  ``create_type=False`` porque los crea la migracion.
- Todas las claves foraneas son ``ON DELETE RESTRICT``: nada se borra en cadena (P-3).
- Los CHECK llevan nombre corto; la convencion de ``Base`` les antepone ``ck_<tabla>_``.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from enum import Enum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.appointments.types import AppointmentStatus
from app.infrastructure.db.base import Base
from app.infrastructure.db.enums import NotificationKind, NotificationStatus, UserRole

TRUE = text("true")
NOW = func.now()
NEW_UUID = text("gen_random_uuid()")


def _enum(enum_class: type[Enum], name: str) -> ENUM:
    return ENUM(
        enum_class,
        name=name,
        values_callable=lambda members: [member.value for member in members],
        create_type=False,
    )


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=NEW_UUID)


def _uuid_fk(target: str, *, nullable: bool = False, unique: bool = False) -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey(target, ondelete="RESTRICT"),
        nullable=nullable,
        unique=unique,
    )


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (
        # Email unico sin distinguir mayusculas (P-2).
        Index("uq_users_email_lower", func.lower(text("email")), unique=True),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    full_name: Mapped[str] = mapped_column(Text)
    role: Mapped[UserRole] = mapped_column(_enum(UserRole, "user_role"))
    active: Mapped[bool] = mapped_column(server_default=TRUE)


class ProfessionalModel(Base):
    __tablename__ = "professionals"

    id: Mapped[uuid.UUID] = _uuid_pk()
    # Todo profesional tiene su cuenta y una cuenta tiene como mucho una ficha (P-2).
    user_id: Mapped[uuid.UUID] = _uuid_fk("users.id", unique=True)
    display_name: Mapped[str] = mapped_column(Text)
    license_number: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(server_default=TRUE)


class WorkingHoursModel(Base):
    __tablename__ = "working_hours"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        CheckConstraint("start_time < end_time", name="start_before_end"),
        # DD-29: horas de reloj en minutos exactos (P-6).
        CheckConstraint("EXTRACT(SECOND FROM start_time) = 0", name="start_no_seconds"),
        CheckConstraint("EXTRACT(SECOND FROM end_time) = 0", name="end_no_seconds"),
        Index(
            "ix_working_hours_professional_weekday_start",
            "professional_id",
            "weekday",
            "start_time",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    professional_id: Mapped[uuid.UUID] = _uuid_fk("professionals.id")
    weekday: Mapped[int] = mapped_column(SmallInteger)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)


class TimeOffModel(Base):
    __tablename__ = "time_off"
    __table_args__ = (
        CheckConstraint("starts_on <= ends_on", name="starts_before_or_on_ends"),
        Index("ix_time_off_professional_starts_on", "professional_id", "starts_on"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    professional_id: Mapped[uuid.UUID] = _uuid_fk("professionals.id")
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(Text)


class PatientModel(Base):
    __tablename__ = "patients"
    __table_args__ = (Index("ix_patients_last_name", "last_name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str] = mapped_column(Text)
    document_number: Mapped[str] = mapped_column(Text, unique=True)
    email: Mapped[str] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    birth_date: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(server_default=TRUE)


def _no_overlap_constraint() -> ExcludeConstraint:
    """Regla dura 3 y 6: un profesional no tiene dos turnos scheduled superpuestos."""
    elements: tuple[Any, ...] = (
        ("professional_id", "="),
        (text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
    )
    return ExcludeConstraint(
        *elements,
        where=text("status = 'scheduled'"),
        using="gist",
        name="ex_appointments_no_overlap",
    )


class AppointmentModel(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="starts_before_ends"),
        # C-15: las dos columnas de la reserva pendiente van juntas y solo en turnos online.
        CheckConstraint(
            "(pending_until IS NULL) = (confirmation_token_hash IS NULL)",
            name="pending_columns_together",
        ),
        CheckConstraint("pending_until IS NULL OR created_by IS NULL", name="pending_only_online"),
        _no_overlap_constraint(),
        Index("ix_appointments_professional_starts_at", "professional_id", "starts_at"),
        Index("ix_appointments_starts_at", "starts_at"),
        Index("ix_appointments_patient_starts_at", "patient_id", "starts_at"),
        Index("ix_appointments_created_by", "created_by"),
        Index(
            "uq_appointments_confirmation_token_hash",
            "confirmation_token_hash",
            unique=True,
            postgresql_where=text("confirmation_token_hash IS NOT NULL"),
        ),
        Index(
            "ix_appointments_pending_until",
            "pending_until",
            postgresql_where=text("pending_until IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    patient_id: Mapped[uuid.UUID] = _uuid_fk("patients.id")
    professional_id: Mapped[uuid.UUID] = _uuid_fk("professionals.id")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[AppointmentStatus] = mapped_column(
        _enum(AppointmentStatus, "appointment_status"),
        server_default=text("'scheduled'"),
    )
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = _uuid_fk("users.id", nullable=True)  # nulo: online
    pending_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmation_token_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=NOW, onupdate=NOW
    )


class EmailNotificationModel(Base):
    __tablename__ = "email_notifications"
    __table_args__ = (
        # RN-NO-03: un email por tipo, turno y horario del turno (su 1a columna cubre la FK).
        UniqueConstraint(
            "appointment_id",
            "kind",
            "appointment_starts_at",
            name="uq_email_notifications_appointment_kind_starts_at",
        ),
        # reencolar_pendientes: las pending mas antiguas primero (P-3 de C-11).
        Index(
            "ix_email_notifications_pending_created_at",
            "created_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    appointment_id: Mapped[uuid.UUID] = _uuid_fk("appointments.id")
    kind: Mapped[NotificationKind] = mapped_column(_enum(NotificationKind, "notification_kind"))
    status: Mapped[NotificationStatus] = mapped_column(
        _enum(NotificationStatus, "notification_status"),
        server_default=text("'pending'"),
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    appointment_starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class ClinicSettingsModel(Base):
    __tablename__ = "clinic_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="single_row"),
        CheckConstraint("slot_minutes > 0", name="slot_minutes_positive"),
        CheckConstraint("min_notice_hours >= 0", name="min_notice_hours_not_negative"),
        CheckConstraint("reminder_send_hour BETWEEN 0 AND 23", name="reminder_send_hour_range"),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, server_default=text("1"))
    clinic_name: Mapped[str] = mapped_column(Text)
    address: Mapped[str] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    slot_minutes: Mapped[int] = mapped_column(Integer, server_default=text("30"))
    timezone: Mapped[str] = mapped_column(
        Text, server_default=text("'America/Argentina/Buenos_Aires'")
    )
    reminder_send_hour: Mapped[int] = mapped_column(SmallInteger, server_default=text("9"))
    min_notice_hours: Mapped[int] = mapped_column(SmallInteger, server_default=text("6"))
