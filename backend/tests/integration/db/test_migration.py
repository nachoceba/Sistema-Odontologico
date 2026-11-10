"""La migracion inicial crea, revierte y vuelve a crear el esquema (spec database-schema).

Usa una base temporal propia (``<base>_mig_test``) para no interferir con la base compartida.
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL

from alembic import command
from tests.db_support import (
    APP_ENUMS,
    APP_TABLES,
    alembic_config,
    downgrade_base,
    upgrade_head,
)

ENUM_VALUES = {
    "user_role": ["admin", "receptionist", "dentist"],
    "appointment_status": ["scheduled", "cancelled", "completed", "no_show"],
    "notification_kind": ["confirmation", "reminder", "booking_expired"],
    "notification_status": ["pending", "sent", "failed"],
}


def snapshot(engine: Engine) -> dict[str, list[tuple[object, ...]]]:
    """Tablas, columnas, constraints e indices de la base, para comparar dos migraciones."""
    queries = {
        "tables": "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
        "AND tablename <> 'alembic_version' ORDER BY 1",
        "columns": "SELECT table_name, column_name, data_type, is_nullable, column_default "
        "FROM information_schema.columns WHERE table_schema = 'public' "
        "AND table_name <> 'alembic_version' ORDER BY 1, 2",
        "constraints": "SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid) "
        "FROM pg_constraint WHERE connamespace = 'public'::regnamespace "
        "AND conrelid::regclass::text <> 'alembic_version' ORDER BY 1, 2",
        "indexes": "SELECT tablename, indexname, indexdef FROM pg_indexes "
        "WHERE schemaname = 'public' AND tablename <> 'alembic_version' ORDER BY 1, 2",
    }
    with engine.connect() as connection:
        return {key: [tuple(r) for r in connection.execute(text(q))] for key, q in queries.items()}


def own_tables(engine: Engine) -> set[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        return {row[0] for row in rows} & set(APP_TABLES)


def own_enums(engine: Engine) -> dict[str, list[str]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT t.typname, e.enumlabel FROM pg_type t "
                "JOIN pg_enum e ON e.enumtypid = t.oid "
                "WHERE t.typname = ANY(:names) ORDER BY t.typname, e.enumsortorder"
            ),
            {"names": list(APP_ENUMS)},
        )
        found: dict[str, list[str]] = {}
        for name, label in rows:
            found.setdefault(name, []).append(label)
        return found


def test_upgrade_creates_tables_enums_extension_and_exclusion_constraint(fresh_url: URL) -> None:
    upgrade_head(fresh_url)
    engine = create_engine(fresh_url)
    try:
        assert own_tables(engine) == set(APP_TABLES)
        assert len(APP_TABLES) == 8
        assert own_enums(engine) == ENUM_VALUES
        with engine.connect() as connection:
            extension = connection.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'btree_gist'")
            ).scalar()
            exclusion = connection.execute(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conname = 'ex_appointments_no_overlap' AND contype = 'x'"
                )
            ).scalar()
        assert extension == 1
        assert exclusion is not None
        assert "gist" in exclusion
        assert "tstzrange(starts_at, ends_at" in exclusion
        assert "scheduled" in exclusion
    finally:
        engine.dispose()


def test_downgrade_leaves_no_own_tables_or_types_and_upgrade_again_is_identical(
    fresh_url: URL,
) -> None:
    engine = create_engine(fresh_url)
    try:
        upgrade_head(fresh_url)
        first = snapshot(engine)
        downgrade_base(fresh_url)
        assert own_tables(engine) == set()
        assert own_enums(engine) == {}
        upgrade_head(fresh_url)
        assert snapshot(engine) == first
        assert first["tables"]
    finally:
        engine.dispose()


def test_applying_twice_changes_nothing_and_does_not_fail(fresh_url: URL) -> None:
    engine = create_engine(fresh_url)
    try:
        upgrade_head(fresh_url)
        first = snapshot(engine)
        upgrade_head(fresh_url)
        assert snapshot(engine) == first
        with engine.connect() as connection:
            versions = connection.execute(text("SELECT count(*) FROM alembic_version")).scalar()
        assert versions == 1
    finally:
        engine.dispose()


# --- Migracion 0002: antiguedad de las notificaciones (spec database-schema, P-3) ---------------

FIRST_REVISION = "0001_initial_schema"
INDEX_NAME = "ix_email_notifications_pending_created_at"


def _upgrade_to(url: URL, revision: str) -> None:
    command.upgrade(alembic_config(url), revision)


def _insert_pending_notification(engine: Engine) -> str:
    """Una notificacion `pending` sobre un turno minimo, con el esquema de la migracion inicial."""
    with engine.begin() as connection:
        user = connection.execute(
            text(
                "INSERT INTO users (email, password_hash, full_name, role) "
                "VALUES ('rec@example.com', 'hash-ficticio', 'Recepcion', 'receptionist') "
                "RETURNING id"
            )
        ).scalar_one()
        dentist = connection.execute(
            text(
                "INSERT INTO users (email, password_hash, full_name, role) "
                "VALUES ('dra@example.com', 'hash-ficticio', 'Dra. A', 'dentist') RETURNING id"
            )
        ).scalar_one()
        professional = connection.execute(
            text(
                "INSERT INTO professionals (user_id, display_name) "
                "VALUES (:u, 'Dra. A') RETURNING id"
            ),
            {"u": dentist},
        ).scalar_one()
        patient = connection.execute(
            text(
                "INSERT INTO patients (first_name, last_name, document_number, email) "
                "VALUES ('Juan', 'Perez', '30000001', 'juan@example.com') RETURNING id"
            )
        ).scalar_one()
        appointment = connection.execute(
            text(
                "INSERT INTO appointments (patient_id, professional_id, starts_at, ends_at, "
                "created_by) VALUES (:p, :d, '2026-11-09 13:00+00', '2026-11-09 13:30+00', :u) "
                "RETURNING id"
            ),
            {"p": patient, "d": professional, "u": user},
        ).scalar_one()
        return str(
            connection.execute(
                text(
                    "INSERT INTO email_notifications (appointment_id, kind, appointment_starts_at) "
                    "VALUES (:a, 'confirmation', '2026-11-09 13:00+00') RETURNING id"
                ),
                {"a": appointment},
            ).scalar_one()
        )


def _notification_columns(engine: Engine) -> set[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'email_notifications'"
            )
        )
        return {row[0] for row in rows}


def test_0002_keeps_existing_rows_and_stamps_them_with_the_migration_instant(
    fresh_url: URL,
) -> None:
    engine = create_engine(fresh_url)
    try:
        _upgrade_to(fresh_url, FIRST_REVISION)
        assert "created_at" not in _notification_columns(engine)
        notification_id = _insert_pending_notification(engine)

        upgrade_head(fresh_url)

        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT status, kind, appointment_starts_at, created_at, "
                    "now() - created_at AS age FROM email_notifications WHERE id = :id"
                ),
                {"id": notification_id},
            ).one()
        assert (row.status, row.kind) == ("pending", "confirmation")
        assert row.created_at is not None
        assert row.age.total_seconds() < 60
    finally:
        engine.dispose()


def test_inserting_without_created_at_uses_the_insertion_instant(fresh_url: URL) -> None:
    engine = create_engine(fresh_url)
    try:
        upgrade_head(fresh_url)
        notification_id = _insert_pending_notification(engine)
        with engine.connect() as connection:
            age = connection.execute(
                text("SELECT now() - created_at FROM email_notifications WHERE id = :id"),
                {"id": notification_id},
            ).scalar_one()
        assert age.total_seconds() < 60
    finally:
        engine.dispose()


def test_the_pending_index_is_partial_on_created_at(fresh_url: URL) -> None:
    engine = create_engine(fresh_url)
    try:
        upgrade_head(fresh_url)
        with engine.connect() as connection:
            definition = connection.execute(
                text("SELECT indexdef FROM pg_indexes WHERE indexname = :name"),
                {"name": INDEX_NAME},
            ).scalar_one()
        assert "(created_at)" in definition
        assert "pending" in definition
    finally:
        engine.dispose()


def test_0002_downgrade_drops_column_and_index_but_keeps_rows_and_reapplies_identically(
    fresh_url: URL,
) -> None:
    engine = create_engine(fresh_url)
    try:
        upgrade_head(fresh_url)
        before = snapshot(engine)
        _insert_pending_notification(engine)

        command.downgrade(alembic_config(fresh_url), FIRST_REVISION)

        assert "created_at" not in _notification_columns(engine)
        with engine.connect() as connection:
            remaining = connection.execute(text("SELECT count(*) FROM email_notifications"))
            assert remaining.scalar_one() == 1
            index = connection.execute(
                text("SELECT 1 FROM pg_indexes WHERE indexname = :name"), {"name": INDEX_NAME}
            ).scalar()
        assert index is None

        upgrade_head(fresh_url)
        assert snapshot(engine) == before
    finally:
        engine.dispose()
