"""Catalogo de tratamientos y tratamiento del turno (C-17, DD-141 a DD-150).

Crea ``treatments`` (nombre, ``name_key`` unico normalizado por el dominio y estado),
``professional_treatments`` (que tratamientos ofrece cada profesional) y la columna nula
``appointments.treatment_id``. No cambia ``ex_appointments_no_overlap``, el tipo
``appointment_status`` ni ninguna columna existente, y no completa el tratamiento de los
turnos anteriores (DD-148). Todas las claves foraneas son ``ON DELETE RESTRICT``.

La reversion falla a proposito, sin cambiar nada, si algun turno tiene tratamiento: quitar la
columna perderia ese dato.

Revision ID: 0005_treatments
Revises: 0004_booking_expired_kind
Create Date: 2026-11-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_treatments"
down_revision: str | Sequence[str] | None = "0004_booking_expired_kind"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APPOINTMENT_INDEX = "ix_appointments_treatment_id"
ASSIGNMENT_INDEX = "ix_professional_treatments_treatment_id"
APPOINTMENT_FK = "fk_appointments_treatment_id_treatments"


def upgrade() -> None:
    op.create_table(
        "treatments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_key", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 80", name=op.f("ck_treatments_name_length")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_treatments")),
        sa.UniqueConstraint("name_key", name=op.f("uq_treatments_name_key")),
    )
    op.create_table(
        "professional_treatments",
        sa.Column("professional_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("treatment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professionals.id"],
            name=op.f("fk_professional_treatments_professional_id_professionals"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["treatment_id"],
            ["treatments.id"],
            name=op.f("fk_professional_treatments_treatment_id_treatments"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "professional_id", "treatment_id", name=op.f("pk_professional_treatments")
        ),
    )
    op.create_index(op.f(ASSIGNMENT_INDEX), "professional_treatments", ["treatment_id"])
    op.add_column(
        "appointments", sa.Column("treatment_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        op.f(APPOINTMENT_FK),
        "appointments",
        "treatments",
        ["treatment_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f(APPOINTMENT_INDEX), "appointments", ["treatment_id"])


def downgrade() -> None:
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM appointments WHERE treatment_id IS NOT NULL) THEN "
            "RAISE EXCEPTION "
            "'hay turnos con tratamiento: no se puede revertir 0005'; "
            "END IF; END $$"
        )
    )
    op.drop_index(APPOINTMENT_INDEX, table_name="appointments")
    op.drop_constraint(APPOINTMENT_FK, "appointments", type_="foreignkey")
    op.drop_column("appointments", "treatment_id")
    op.drop_index(ASSIGNMENT_INDEX, table_name="professional_treatments")
    op.drop_table("professional_treatments")
    op.drop_table("treatments")
