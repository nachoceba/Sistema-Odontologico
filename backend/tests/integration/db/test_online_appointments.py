"""Migracion 0003: turnos online y reserva pendiente (spec database-schema, C-15, DD-130).

Insertos SQL directos: prueban que la base protege sola, sin repositorios ni dominio.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError, IntegrityError

from alembic import command
from tests.db_support import alembic_config, upgrade_head
from tests.integration.db.helpers import World, at, insert_appointment, make_world

HASH_A = "a" * 64
HASH_B = "b" * 64
BEFORE_ONLINE = "0002_notifications_created_at"  # 0004 y 0003 se revierten juntas


def _insert_online(
    connection: Connection,
    world: World,
    start: datetime,
    end: datetime,
    *,
    created_by: Any = None,
    pending_until: datetime | None = None,
    token_hash: str | None = None,
    patient: Any = None,
) -> None:
    connection.execute(
        text(
            "INSERT INTO appointments (patient_id, professional_id, starts_at, ends_at, "
            "created_by, pending_until, confirmation_token_hash) "
            "VALUES (:patient, :professional, :start, :end, :created_by, :pending, :hash)"
        ),
        {
            "patient": patient or world.ana,
            "professional": world.dra_a,
            "start": start,
            "end": end,
            "created_by": created_by,
            "pending": pending_until,
            "hash": token_hash,
        },
    )


@pytest.fixture
def migrated(fresh_url: URL) -> Engine:
    upgrade_head(fresh_url)
    return create_engine(fresh_url)


def test_an_online_appointment_without_creator_is_accepted(migrated: Engine) -> None:
    with migrated.begin() as connection:
        world = make_world(connection)
        _insert_online(connection, world, at(10), at(10, 30))
        count = connection.execute(
            text("SELECT count(*) FROM appointments WHERE created_by IS NULL")
        ).scalar_one()
    assert count == 1


def test_a_well_formed_pending_appointment_is_accepted(migrated: Engine) -> None:
    with migrated.begin() as connection:
        world = make_world(connection)
        _insert_online(
            connection, world, at(10), at(10, 30), pending_until=at(9), token_hash=HASH_A
        )
        row = connection.execute(
            text("SELECT status, pending_until, confirmation_token_hash FROM appointments")
        ).one()
    assert (row.status, row.confirmation_token_hash) == ("scheduled", HASH_A)
    assert row.pending_until == at(9)


@pytest.mark.parametrize(
    ("pending", "token_hash"),
    [(at(9), None), (None, HASH_A)],
    ids=["solo-pending_until", "solo-hash"],
)
def test_pending_until_and_hash_are_both_set_or_both_null(
    migrated: Engine, pending: datetime | None, token_hash: str | None
) -> None:
    with migrated.connect() as connection, pytest.raises(IntegrityError) as raised:
        world = make_world(connection)
        _insert_online(
            connection, world, at(10), at(10, 30), pending_until=pending, token_hash=token_hash
        )
    assert "ck_appointments_pending_columns_together" in str(raised.value)


def test_a_pending_appointment_cannot_have_a_staff_creator(migrated: Engine) -> None:
    with migrated.connect() as connection, pytest.raises(IntegrityError) as raised:
        world = make_world(connection)
        _insert_online(
            connection,
            world,
            at(10),
            at(10, 30),
            created_by=world.reception,
            pending_until=at(9),
            token_hash=HASH_A,
        )
    assert "ck_appointments_pending_only_online" in str(raised.value)


def test_a_staff_appointment_without_pending_columns_still_works(migrated: Engine) -> None:
    with migrated.begin() as connection:
        world = make_world(connection)
        insert_appointment(connection, world, at(10), at(10, 30))


def test_the_token_hash_is_unique(migrated: Engine) -> None:
    with migrated.connect() as connection, pytest.raises(IntegrityError) as raised:
        world = make_world(connection)
        _insert_online(
            connection, world, at(10), at(10, 30), pending_until=at(9), token_hash=HASH_A
        )
        _insert_online(
            connection,
            world,
            at(11),
            at(11, 30),
            pending_until=at(9),
            token_hash=HASH_A,
            patient=world.juan,
        )
    assert "uq_appointments_confirmation_token_hash" in str(raised.value)


def test_two_appointments_without_hash_do_not_collide(migrated: Engine) -> None:
    with migrated.begin() as connection:
        world = make_world(connection)
        _insert_online(connection, world, at(10), at(10, 30))
        _insert_online(connection, world, at(11), at(11, 30), patient=world.juan)


def test_the_pending_until_index_is_partial(migrated: Engine) -> None:
    with migrated.connect() as connection:
        definition = connection.execute(
            text(
                "SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_appointments_pending_until'"
            )
        ).scalar_one()
    assert "(pending_until)" in definition
    assert "IS NOT NULL" in definition


def test_downgrade_fails_when_there_are_online_appointments(
    migrated: Engine, fresh_url: URL
) -> None:
    with migrated.begin() as connection:
        world = make_world(connection)
        _insert_online(connection, world, at(10), at(10, 30))

    with pytest.raises(DBAPIError):
        command.downgrade(alembic_config(fresh_url), BEFORE_ONLINE)

    with migrated.connect() as connection:
        columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'appointments'"
                )
            )
        }
        online = connection.execute(
            text("SELECT count(*) FROM appointments WHERE created_by IS NULL")
        ).scalar_one()
    assert {"pending_until", "confirmation_token_hash"} <= columns
    assert online == 1


def test_downgrade_without_online_appointments_restores_the_previous_schema(
    migrated: Engine, fresh_url: URL
) -> None:
    command.downgrade(alembic_config(fresh_url), BEFORE_ONLINE)
    with migrated.connect() as connection:
        columns = {
            row[0]: row[1]
            for row in connection.execute(
                text(
                    "SELECT column_name, is_nullable FROM information_schema.columns "
                    "WHERE table_name = 'appointments'"
                )
            )
        }
    assert "pending_until" not in columns
    assert "confirmation_token_hash" not in columns
    assert columns["created_by"] == "NO"
    upgrade_head(fresh_url)


def test_a_pending_appointment_cannot_overlap_a_confirmed_one(migrated: Engine) -> None:
    """Regla dura 6: el pendiente ocupa su franja igual que un turno confirmado."""
    with migrated.connect() as connection:
        world = make_world(connection)
        insert_appointment(connection, world, at(10), at(10, 30))
        with pytest.raises(IntegrityError) as raised:
            _insert_online(
                connection,
                world,
                at(10, 15),
                at(10, 45),
                pending_until=at(9),
                token_hash=HASH_A,
                patient=world.ana,
            )
    assert "ex_appointments_no_overlap" in str(raised.value)


def test_two_online_appointments_cannot_overlap_either(migrated: Engine) -> None:
    with migrated.connect() as connection:
        world = make_world(connection)
        _insert_online(
            connection, world, at(10), at(10, 30), pending_until=at(9), token_hash=HASH_A
        )
        with pytest.raises(IntegrityError) as raised:
            _insert_online(
                connection,
                world,
                at(10),
                at(10, 30),
                pending_until=at(9),
                token_hash=HASH_B,
                patient=world.juan,
            )
    assert "ex_appointments_no_overlap" in str(raised.value)


def test_the_status_type_and_the_exclusion_constraint_did_not_change(migrated: Engine) -> None:
    with migrated.connect() as connection:
        labels = [
            row[0]
            for row in connection.execute(
                text(
                    "SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                    "WHERE t.typname = 'appointment_status' ORDER BY e.enumsortorder"
                )
            )
        ]
        definition = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'ex_appointments_no_overlap'"
            )
        ).scalar_one()
    assert labels == ["scheduled", "cancelled", "completed", "no_show"]
    assert "status = 'scheduled'" in definition
