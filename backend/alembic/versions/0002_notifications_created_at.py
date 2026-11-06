"""Antiguedad de cada notificacion: ``created_at`` e indice parcial de las ``pending``.

``reencolar_pendientes`` toma las ``pending`` creadas hace mas de unos minutos (P-3 de C-11).
Las filas existentes reciben el instante de la migracion (``DEFAULT now()``; en PostgreSQL 16
agregar una columna con un valor por defecto estable no reescribe la tabla). El indice es
parcial: solo cubre las ``pending``, que son pocas, y sirve para ordenarlas por antiguedad.

Revision ID: 0002_notifications_created_at
Revises: 0001_initial_schema
Create Date: 2026-11-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_notifications_created_at"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "ix_email_notifications_pending_created_at"


def upgrade() -> None:
    op.add_column(
        "email_notifications",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        op.f(INDEX_NAME),
        "email_notifications",
        ["created_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index(
        op.f(INDEX_NAME),
        table_name="email_notifications",
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.drop_column("email_notifications", "created_at")
