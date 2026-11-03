"""Esquema inicial: 8 tablas, 4 enumerados y el constraint de exclusion de turnos.

Escrita a mano (design D-2): el autogenerate de Alembic no genera bien el
``ExcludeConstraint`` con ``tstzrange`` y ``WHERE``. Un test compara esta migracion con los
modelos de ``app.infrastructure.db.models``. Los nombres de constraints son los que produce la
convencion de ``Base`` y se pasan con ``op.f`` para que no se les antepongan prefijos.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUMS: dict[str, tuple[str, ...]] = {
    "user_role": ("admin", "receptionist", "dentist"),
    "appointment_status": ("scheduled", "cancelled", "completed", "no_show"),
    "notification_kind": ("confirmation", "reminder"),
    "notification_status": ("pending", "sent", "failed"),
}


def _enum(name: str) -> postgresql.ENUM:
    """Referencia a un tipo ya creado (``create_type=False``)."""
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def _id() -> sa.Column[object]:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def _uuid_col(column: str) -> sa.Column[object]:
    """Columna de clave foranea; el constraint se declara aparte con ``_fk_constraint``."""
    return sa.Column(column, postgresql.UUID(as_uuid=True), nullable=False)


def _fk_constraint(table: str, column: str, target: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column],
        [f"{target}.id"],
        name=op.f(f"fk_{table}_{column}_{target}"),
        ondelete="RESTRICT",
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    bind = op.get_bind()
    for name, values in ENUMS.items():
        postgresql.ENUM(*values, name=name).create(bind, checkfirst=False)

    op.create_table(
        "users",
        _id(),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role", _enum("user_role"), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    # P-2: email unico sin distinguir mayusculas.
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "patients",
        _id(),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("document_number", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patients")),
        sa.UniqueConstraint("document_number", name=op.f("uq_patients_document_number")),
    )
    op.create_index("ix_patients_last_name", "patients", ["last_name"])

    op.create_table(
        "clinic_settings",
        sa.Column("id", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("clinic_name", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("slot_minutes", sa.Integer(), server_default=sa.text("30"), nullable=False),
        sa.Column(
            "timezone",
            sa.Text(),
            server_default=sa.text("'America/Argentina/Buenos_Aires'"),
            nullable=False,
        ),
        sa.Column(
            "reminder_send_hour", sa.SmallInteger(), server_default=sa.text("9"), nullable=False
        ),
        sa.Column(
            "min_notice_hours", sa.SmallInteger(), server_default=sa.text("6"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clinic_settings")),
        sa.CheckConstraint("id = 1", name=op.f("ck_clinic_settings_single_row")),
        sa.CheckConstraint(
            "slot_minutes > 0", name=op.f("ck_clinic_settings_slot_minutes_positive")
        ),
        sa.CheckConstraint(
            "min_notice_hours >= 0", name=op.f("ck_clinic_settings_min_notice_hours_not_negative")
        ),
        sa.CheckConstraint(
            "reminder_send_hour BETWEEN 0 AND 23",
            name=op.f("ck_clinic_settings_reminder_send_hour_range"),
        ),
    )

    op.create_table(
        "professionals",
        _id(),
        _uuid_col("user_id"),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("license_number", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_professionals")),
        _fk_constraint("professionals", "user_id", "users"),
        sa.UniqueConstraint("user_id", name=op.f("uq_professionals_user_id")),
    )

    op.create_table(
        "working_hours",
        _id(),
        _uuid_col("professional_id"),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_working_hours")),
        _fk_constraint("working_hours", "professional_id", "professionals"),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name=op.f("ck_working_hours_weekday_range")),
        sa.CheckConstraint("start_time < end_time", name=op.f("ck_working_hours_start_before_end")),
        sa.CheckConstraint(
            "EXTRACT(SECOND FROM start_time) = 0", name=op.f("ck_working_hours_start_no_seconds")
        ),
        sa.CheckConstraint(
            "EXTRACT(SECOND FROM end_time) = 0", name=op.f("ck_working_hours_end_no_seconds")
        ),
    )
    op.create_index(
        "ix_working_hours_professional_weekday_start",
        "working_hours",
        ["professional_id", "weekday", "start_time"],
    )

    op.create_table(
        "time_off",
        _id(),
        _uuid_col("professional_id"),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_time_off")),
        _fk_constraint("time_off", "professional_id", "professionals"),
        sa.CheckConstraint(
            "starts_on <= ends_on", name=op.f("ck_time_off_starts_before_or_on_ends")
        ),
    )
    op.create_index(
        "ix_time_off_professional_starts_on", "time_off", ["professional_id", "starts_on"]
    )

    op.create_table(
        "appointments",
        _id(),
        _uuid_col("patient_id"),
        _uuid_col("professional_id"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            _enum("appointment_status"),
            server_default=sa.text("'scheduled'"),
            nullable=False,
        ),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        _uuid_col("created_by"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appointments")),
        _fk_constraint("appointments", "patient_id", "patients"),
        _fk_constraint("appointments", "professional_id", "professionals"),
        _fk_constraint("appointments", "created_by", "users"),
        sa.CheckConstraint("starts_at < ends_at", name=op.f("ck_appointments_starts_before_ends")),
        # Regla dura 3 y 6 (RN-TU-01, DD-04): PostgreSQL rechaza dos turnos scheduled
        # superpuestos del mismo profesional, rangos semiabiertos [inicio, fin). Va dentro de
        # create_table porque op.create_exclude_constraint no admite expresiones de texto
        # (tstzrange(...)) en el elemento: exige nombres de columna.
        postgresql.ExcludeConstraint(
            ("professional_id", "="),
            (sa.text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            using="gist",
            where=sa.text("status = 'scheduled'"),
            name="ex_appointments_no_overlap",
        ),
    )
    op.create_index(
        "ix_appointments_professional_starts_at", "appointments", ["professional_id", "starts_at"]
    )
    op.create_index("ix_appointments_starts_at", "appointments", ["starts_at"])
    op.create_index(
        "ix_appointments_patient_starts_at", "appointments", ["patient_id", "starts_at"]
    )
    op.create_index("ix_appointments_created_by", "appointments", ["created_by"])

    op.create_table(
        "email_notifications",
        _id(),
        _uuid_col("appointment_id"),
        sa.Column("kind", _enum("notification_kind"), nullable=False),
        sa.Column(
            "status",
            _enum("notification_status"),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("appointment_starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_notifications")),
        _fk_constraint("email_notifications", "appointment_id", "appointments"),
        # RN-NO-03: un email por tipo, turno y horario del turno.
        sa.UniqueConstraint(
            "appointment_id",
            "kind",
            "appointment_starts_at",
            name=op.f("uq_email_notifications_appointment_kind_starts_at"),
        ),
    )


def downgrade() -> None:
    """Deja la base sin tablas ni tipos del sistema. ``btree_gist`` se conserva (inocua)."""
    op.drop_table("email_notifications")
    op.drop_table("appointments")  # arrastra sus indices y el constraint de exclusion
    op.drop_table("time_off")
    op.drop_table("working_hours")
    op.drop_table("professionals")
    op.drop_table("clinic_settings")
    op.drop_table("patients")
    op.drop_table("users")  # arrastra uq_users_email_lower
    bind = op.get_bind()
    for name in reversed(list(ENUMS)):
        postgresql.ENUM(name=name).drop(bind, checkfirst=False)
