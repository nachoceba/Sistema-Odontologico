"""Migracion 0005: catalogo de tratamientos y tratamiento del turno (spec database-schema, C-17).

Insertos SQL directos: prueban que la base protege sola, sin repositorios ni dominio.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError, IntegrityError

from alembic import command
from tests.db_support import alembic_config, upgrade_head
from tests.integration.db.helpers import (
    World,
    at,
    insert_appointment,
    insert_patient,
    insert_professional,
    insert_user,
    make_world,
)

PREVIOUS_REVISION = "0004_booking_expired_kind"


def _insert_treatment(connection: Connection, name: str, key: str | None = None) -> UUID:
    value = connection.execute(
        text("INSERT INTO treatments (name, name_key) VALUES (:name, :key) RETURNING id"),
        {"name": name, "key": key or name.upper()},
    ).scalar_one()
    assert isinstance(value, UUID)
    return value


def _insert_appointment_with(
    connection: Connection, world: World, treatment: Any, start: int, *, professional: Any = None
) -> UUID:
    appointment = insert_appointment(
        connection, world, at(start), at(start, 30), professional=professional
    )
    connection.execute(
        text("UPDATE appointments SET treatment_id = :t WHERE id = :a"),
        {"t": treatment, "a": appointment},
    )
    return appointment


@pytest.fixture
def migrated(fresh_url: URL) -> Engine:
    upgrade_head(fresh_url)
    return create_engine(fresh_url)


def test_an_appointment_with_an_existing_treatment_is_accepted(migrated: Engine) -> None:
    with migrated.begin() as connection:
        world = make_world(connection)
        treatment = _insert_treatment(connection, "Limpieza dental")
        appointment = _insert_appointment_with(connection, world, treatment, 10)
        stored = connection.execute(
            text("SELECT treatment_id FROM appointments WHERE id = :a"), {"a": appointment}
        ).scalar_one()
    assert stored == treatment


def test_an_appointment_with_an_unknown_treatment_is_rejected_by_the_foreign_key(
    migrated: Engine,
) -> None:
    with migrated.connect() as connection:
        world = make_world(connection)
        appointment = insert_appointment(connection, world, at(10), at(10, 30))
        with pytest.raises(IntegrityError) as raised:
            connection.execute(
                text("UPDATE appointments SET treatment_id = gen_random_uuid() WHERE id = :a"),
                {"a": appointment},
            )
    assert "fk_appointments_treatment_id_treatments" in str(raised.value)


def test_a_repeated_name_key_is_rejected(migrated: Engine) -> None:
    with migrated.connect() as connection:
        _insert_treatment(connection, "Extracción", "EXTRACCION")
        with pytest.raises(IntegrityError) as raised:
            _insert_treatment(connection, "EXTRACCION", "EXTRACCION")
    assert "uq_treatments_name_key" in str(raised.value)


@pytest.mark.parametrize("name", ["", "x" * 81])
def test_the_name_length_check_rejects_empty_and_too_long_names(
    migrated: Engine, name: str
) -> None:
    with migrated.connect() as connection, pytest.raises(IntegrityError) as raised:
        _insert_treatment(connection, name, "CLAVE")
    assert "name_length" in str(raised.value)


def test_names_of_one_and_eighty_characters_are_accepted(migrated: Engine) -> None:
    with migrated.begin() as connection:
        _insert_treatment(connection, "x", "X")
        _insert_treatment(connection, "y" * 80, "Y" * 80)
        total = connection.execute(text("SELECT count(*) FROM treatments")).scalar_one()
    assert total == 2


def test_a_repeated_professional_treatment_pair_is_rejected(migrated: Engine) -> None:
    with migrated.connect() as connection:
        world = make_world(connection)
        treatment = _insert_treatment(connection, "Consulta")
        sql = "INSERT INTO professional_treatments (professional_id, treatment_id) VALUES (:p, :t)"
        params = {"p": world.dra_a, "t": treatment}
        connection.execute(text(sql), params)
        with pytest.raises(IntegrityError) as raised:
            connection.execute(text(sql), params)
    assert "pk_professional_treatments" in str(raised.value)


def test_a_treatment_with_an_appointment_or_a_professional_cannot_be_deleted(
    migrated: Engine,
) -> None:
    with migrated.begin() as connection:
        world = make_world(connection)
        used = _insert_treatment(connection, "Consulta")
        assigned = _insert_treatment(connection, "Limpieza dental")
        _insert_appointment_with(connection, world, used, 10)
        connection.execute(
            text("INSERT INTO professional_treatments VALUES (:p, :t)"),
            {"p": world.dra_a, "t": assigned},
        )

    for treatment in (used, assigned):
        with migrated.connect() as connection, pytest.raises(IntegrityError):
            connection.execute(text("DELETE FROM treatments WHERE id = :t"), {"t": treatment})


def test_previous_appointments_keep_a_null_treatment_after_migrating(
    fresh_url: URL,
) -> None:
    command.upgrade(alembic_config(fresh_url), PREVIOUS_REVISION)
    engine = create_engine(fresh_url)
    with engine.begin() as connection:
        # Antes de 0005 no existen las tablas de tratamientos: el mundo se arma sin ellas.
        world = World(
            dra_a=insert_professional(connection, name="Dra. A"),
            dr_b=insert_professional(connection, name="Dr. B"),
            juan=insert_patient(connection, first="Juan", last="Perez"),
            ana=insert_patient(connection, first="Ana", last="Gomez"),
            reception=insert_user(connection, email="recepcion@example.com"),
            consulta=uuid4(),
            limpieza=uuid4(),
        )
        insert_appointment(connection, world, at(10), at(10, 30))

    upgrade_head(fresh_url)

    with engine.connect() as connection:
        rows = connection.execute(text("SELECT treatment_id FROM appointments")).all()
    assert rows == [(None,)]


def test_overlapping_appointments_with_different_treatments_are_still_rejected(
    migrated: Engine,
) -> None:
    with migrated.connect() as connection:
        world = make_world(connection)
        first = _insert_treatment(connection, "Consulta")
        second = _insert_treatment(connection, "Extracción")
        _insert_appointment_with(connection, world, first, 10)
        with pytest.raises(IntegrityError) as raised:
            _insert_appointment_with(connection, world, second, 10)
    assert "ex_appointments_no_overlap" in str(raised.value)


def test_status_enum_and_exclusion_constraint_did_not_change(migrated: Engine) -> None:
    with migrated.connect() as connection:
        labels = [
            row[0]
            for row in connection.execute(
                text(
                    "SELECT e.enumlabel FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid "
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
    assert "EXCLUDE USING gist" in definition
    assert "professional_id WITH =" in definition
    assert "status = 'scheduled'" in definition


def test_downgrade_fails_and_changes_nothing_when_an_appointment_has_a_treatment(
    migrated: Engine, fresh_url: URL
) -> None:
    with migrated.begin() as connection:
        world = make_world(connection)
        treatment = _insert_treatment(connection, "Revision")
        _insert_appointment_with(connection, world, treatment, 10)
        before = connection.execute(text("SELECT count(*) FROM treatments")).scalar_one()

    with pytest.raises(DBAPIError):
        command.downgrade(alembic_config(fresh_url), PREVIOUS_REVISION)

    with migrated.connect() as connection:
        total = connection.execute(text("SELECT count(*) FROM treatments")).scalar_one()
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert total == before
    assert version.startswith("0005")


def test_downgrade_without_treated_appointments_restores_the_previous_schema(
    migrated: Engine, fresh_url: URL
) -> None:
    with migrated.begin() as connection:
        world = make_world(connection)
        insert_appointment(connection, world, at(10), at(10, 30))
        _insert_treatment(connection, "Consulta")

    command.downgrade(alembic_config(fresh_url), PREVIOUS_REVISION)

    with migrated.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
        }
        columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'appointments'"
                )
            )
        }
        kept = connection.execute(text("SELECT count(*) FROM appointments")).scalar_one()
    assert "treatments" not in tables
    assert "professional_treatments" not in tables
    assert "treatment_id" not in columns
    assert kept == 1
    upgrade_head(fresh_url)
