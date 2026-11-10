"""Aviso de vencimiento de una reserva online: nuevo valor de ``notification_kind`` (C-16, DD-140).

Agrega ``booking_expired`` al tipo ``notification_kind`` sin tocar las filas existentes ni el
``UNIQUE (appointment_id, kind, appointment_starts_at)``. ``ALTER TYPE ... ADD VALUE`` corre
dentro de la transaccion de Alembic (PostgreSQL 12 o superior) siempre que el valor no se use en
esa misma transaccion, y esta migracion no lo usa.

La reversion falla a proposito, sin cambiar nada, si hay avisos ``booking_expired``: quitar el
valor los borraria o los inventaria. Sin avisos, recrea el tipo con ``confirmation`` y
``reminder`` (PostgreSQL no permite quitar un valor de un enumerado).

Revision ID: 0004_booking_expired_kind
Revises: 0003_online_appointments
Create Date: 2026-11-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_booking_expired_kind"
down_revision: str | Sequence[str] | None = "0003_online_appointments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE notification_kind ADD VALUE IF NOT EXISTS 'booking_expired'"))


def downgrade() -> None:
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM email_notifications WHERE kind = 'booking_expired') THEN "
            "RAISE EXCEPTION "
            "'hay avisos booking_expired: no se puede revertir 0004'; "
            "END IF; END $$"
        )
    )
    op.execute(sa.text("ALTER TYPE notification_kind RENAME TO notification_kind_old"))
    op.execute(sa.text("CREATE TYPE notification_kind AS ENUM ('confirmation', 'reminder')"))
    op.execute(
        sa.text(
            "ALTER TABLE email_notifications ALTER COLUMN kind TYPE notification_kind "
            "USING kind::text::notification_kind"
        )
    )
    op.execute(sa.text("DROP TYPE notification_kind_old"))
