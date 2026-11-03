"""La migracion inicial crea, revierte y vuelve a crear el esquema (spec database-schema).

Usa una base temporal propia (``<base>_mig_test``) para no interferir con la base compartida.
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL

from tests.db_support import (
    APP_ENUMS,
    APP_TABLES,
    downgrade_base,
    upgrade_head,
)

ENUM_VALUES = {
    "user_role": ["admin", "receptionist", "dentist"],
    "appointment_status": ["scheduled", "cancelled", "completed", "no_show"],
    "notification_kind": ["confirmation", "reminder"],
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
