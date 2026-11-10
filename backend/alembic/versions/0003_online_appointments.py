"""Turnos online: ``created_by`` opcional y reserva pendiente de confirmacion (C-15, DD-130).

Un turno online no tiene usuario creador (``created_by`` nulo). Un turno pendiente de
confirmacion sigue siendo ``scheduled`` (lo cubre ``ex_appointments_no_overlap`` sin cambios) y
guarda ``pending_until`` y el hash SHA-256 de su token: las dos columnas van juntas y solo en
turnos sin creador. El hash es unico (indice parcial) y ``pending_until`` tiene su propio indice
parcial para la tarea de vencimiento. No toca el tipo ``appointment_status`` ni la exclusion.

La reversion falla a proposito si hay turnos sin usuario creador: volver a ``NOT NULL`` los
perderia o los inventaria.

Revision ID: 0003_online_appointments
Revises: 0002_notifications_created_at
Create Date: 2026-11-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_online_appointments"
down_revision: str | Sequence[str] | None = "0002_notifications_created_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TOGETHER = "ck_appointments_pending_columns_together"
ONLY_ONLINE = "ck_appointments_pending_only_online"
UNIQUE_HASH = "uq_appointments_confirmation_token_hash"
PENDING_INDEX = "ix_appointments_pending_until"


def upgrade() -> None:
    op.alter_column("appointments", "created_by", nullable=True)
    op.add_column("appointments", sa.Column("pending_until", sa.DateTime(timezone=True)))
    op.add_column("appointments", sa.Column("confirmation_token_hash", sa.Text()))
    op.create_check_constraint(
        op.f(TOGETHER),
        "appointments",
        "(pending_until IS NULL) = (confirmation_token_hash IS NULL)",
    )
    op.create_check_constraint(
        op.f(ONLY_ONLINE), "appointments", "pending_until IS NULL OR created_by IS NULL"
    )
    op.create_index(
        op.f(UNIQUE_HASH),
        "appointments",
        ["confirmation_token_hash"],
        unique=True,
        postgresql_where=sa.text("confirmation_token_hash IS NOT NULL"),
    )
    op.create_index(
        op.f(PENDING_INDEX),
        "appointments",
        ["pending_until"],
        postgresql_where=sa.text("pending_until IS NOT NULL"),
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM appointments WHERE created_by IS NULL) THEN "
            "RAISE EXCEPTION 'hay turnos online (sin usuario creador): no se puede revertir 0003'; "
            "END IF; END $$"
        )
    )
    op.drop_index(
        PENDING_INDEX,
        table_name="appointments",
        postgresql_where=sa.text("pending_until IS NOT NULL"),
    )
    op.drop_index(
        UNIQUE_HASH,
        table_name="appointments",
        postgresql_where=sa.text("confirmation_token_hash IS NOT NULL"),
    )
    op.drop_constraint(op.f(ONLY_ONLINE), "appointments", type_="check")
    op.drop_constraint(op.f(TOGETHER), "appointments", type_="check")
    op.drop_column("appointments", "confirmation_token_hash")
    op.drop_column("appointments", "pending_until")
    op.alter_column("appointments", "created_by", nullable=False)
