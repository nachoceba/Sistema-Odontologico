"""Migracion 0004: tipo de notificacion del aviso de vencimiento (spec database-schema, DD-140).

Insertos SQL directos: prueban que la base protege sola, sin repositorios ni dominio.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError, IntegrityError

from alembic import command
from tests.db_support import alembic_config, upgrade_head
from tests.integration.db.helpers import World, at, insert_appointment, make_world

PREVIOUS_REVISION = "0003_online_appointments"


def _insert_notification(
    connection: Connection, appointment: Any, kind: str, starts_at: Any
) -> None:
    connection.execute(
        text(
            "INSERT INTO email_notifications (appointment_id, kind, appointment_starts_at) "
            "VALUES (:appointment, CAST(:kind AS notification_kind), :starts)"
        ),
        {"appointment": appointment, "kind": kind, "starts": starts_at},
    )


def _appointment(connection: Connection, world: World) -> Any:
    return insert_appointment(connection, world, at(10), at(10, 30))


def _kind_labels(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT e.enumlabel FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid "
                "WHERE t.typname = 'notification_kind' ORDER BY e.enumsortorder"
            )
        )
        return [row[0] for row in rows]


@pytest.fixture
def migrated(fresh_url: URL) -> Engine:
    upgrade_head(fresh_url)
    return create_engine(fresh_url)


def test_the_expiry_notice_kind_is_accepted(migrated: Engine) -> None:
    with migrated.begin() as connection:
        world = make_world(connection)
        appointment = _appointment(connection, world)
        _insert_notification(connection, appointment, "booking_expired", at(10))
        stored = connection.execute(text("SELECT kind::text FROM email_notifications")).scalar_one()

    assert stored == "booking_expired"
    assert _kind_labels(migrated) == ["confirmation", "reminder", "booking_expired"]


def test_a_second_expiry_notice_for_the_same_appointment_and_start_is_rejected(
    migrated: Engine,
) -> None:
    with migrated.connect() as connection:
        world = make_world(connection)
        appointment = _appointment(connection, world)
        _insert_notification(connection, appointment, "booking_expired", at(10))
        with pytest.raises(IntegrityError) as raised:
            _insert_notification(connection, appointment, "booking_expired", at(10))

    assert "uq_email_notifications_appointment_kind_starts_at" in str(raised.value)


def test_the_unique_constraint_still_allows_other_kinds_for_the_same_appointment(
    migrated: Engine,
) -> None:
    with migrated.begin() as connection:
        world = make_world(connection)
        appointment = _appointment(connection, world)
        _insert_notification(connection, appointment, "confirmation", at(10))
        _insert_notification(connection, appointment, "booking_expired", at(10))
        total = connection.execute(text("SELECT count(*) FROM email_notifications")).scalar_one()

    assert total == 2


def test_downgrade_fails_and_changes_nothing_when_there_are_expiry_notices(
    migrated: Engine, fresh_url: URL
) -> None:
    with migrated.begin() as connection:
        world = make_world(connection)
        appointment = _appointment(connection, world)
        _insert_notification(connection, appointment, "booking_expired", at(10))

    with pytest.raises(DBAPIError):
        command.downgrade(alembic_config(fresh_url), PREVIOUS_REVISION)

    assert _kind_labels(migrated) == ["confirmation", "reminder", "booking_expired"]
    with migrated.connect() as connection:
        total = connection.execute(text("SELECT count(*) FROM email_notifications")).scalar_one()
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert total == 1
    assert version.startswith("0005")


def test_downgrade_without_expiry_notices_restores_the_two_original_kinds(
    migrated: Engine, fresh_url: URL
) -> None:
    with migrated.begin() as connection:
        world = make_world(connection)
        appointment = _appointment(connection, world)
        _insert_notification(connection, appointment, "confirmation", at(10))

    command.downgrade(alembic_config(fresh_url), PREVIOUS_REVISION)

    assert _kind_labels(migrated) == ["confirmation", "reminder"]
    with migrated.connect() as connection:
        kept = connection.execute(text("SELECT kind::text FROM email_notifications")).scalar_one()
    assert kept == "confirmation"
    upgrade_head(fresh_url)
    assert _kind_labels(migrated) == ["confirmation", "reminder", "booking_expired"]
