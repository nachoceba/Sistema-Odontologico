"""La base rechaza por si sola dos turnos scheduled superpuestos (regla dura 3 y 6, RN-TU-01).

SQL directo: la escritura no pasa por el dominio ni por los repositorios.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from tests.integration.db.helpers import (
    World,
    at,
    insert_appointment,
    make_world,
    scalar,
)

EXCLUSION_VIOLATION = "23P01"


@pytest.fixture
def world(engine: Engine) -> World:
    with engine.begin() as connection:
        return make_world(connection)


def count_for_dra_a(engine: Engine, world: World) -> int:
    with engine.connect() as connection:
        value = scalar(
            connection,
            "SELECT count(*) FROM appointments WHERE professional_id = :p",
            p=world.dra_a,
        )
    return int(value)


def sqlstate(error: pytest.ExceptionInfo[IntegrityError]) -> str | None:
    return getattr(error.value.orig, "sqlstate", None)


def test_overlapping_scheduled_appointment_is_rejected_and_table_unchanged(
    engine: Engine, world: World
) -> None:
    with engine.begin() as connection:
        insert_appointment(connection, world, at(10), at(10, 30))
    with pytest.raises(IntegrityError) as raised, engine.begin() as connection:
        insert_appointment(connection, world, at(10, 15), at(10, 45))
    assert sqlstate(raised) == EXCLUSION_VIOLATION
    assert "ex_appointments_no_overlap" in str(raised.value)
    assert count_for_dra_a(engine, world) == 1


def test_same_exact_slot_with_another_patient_is_rejected(engine: Engine, world: World) -> None:
    with engine.begin() as connection:
        insert_appointment(connection, world, at(10), at(10, 30), patient=world.juan)
    with pytest.raises(IntegrityError) as raised, engine.begin() as connection:
        insert_appointment(connection, world, at(10), at(10, 30), patient=world.ana)
    assert sqlstate(raised) == EXCLUSION_VIOLATION


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(at(9, 30), at(11), id="contiene_a_otro"),
        pytest.param(at(10, 20), at(10, 25), id="contenido_en_otro"),
        pytest.param(at(9, 45), at(10, 15), id="cruza_el_inicio"),
    ],
)
def test_other_overlapping_shapes_are_rejected(
    engine: Engine, world: World, start: datetime, end: datetime
) -> None:
    with engine.begin() as connection:
        insert_appointment(connection, world, at(10), at(10, 30))
    with pytest.raises(IntegrityError) as raised, engine.begin() as connection:
        insert_appointment(connection, world, start, end)
    assert sqlstate(raised) == EXCLUSION_VIOLATION


def test_adjacent_appointments_are_accepted_half_open_range(engine: Engine, world: World) -> None:
    with engine.begin() as connection:
        insert_appointment(connection, world, at(10), at(10, 30))
        insert_appointment(connection, world, at(10, 30), at(11))
        insert_appointment(connection, world, at(9, 30), at(10))
    assert count_for_dra_a(engine, world) == 3


def test_cancelled_appointment_does_not_block(engine: Engine, world: World) -> None:
    with engine.begin() as connection:
        insert_appointment(connection, world, at(10), at(10, 30), status="cancelled")
        insert_appointment(connection, world, at(10), at(10, 30))
    assert count_for_dra_a(engine, world) == 2


def test_completed_and_no_show_do_not_block(engine: Engine, world: World) -> None:
    with engine.begin() as connection:
        insert_appointment(connection, world, at(10), at(10, 30), status="completed")
        insert_appointment(connection, world, at(11), at(11, 30), status="no_show")
        insert_appointment(connection, world, at(10), at(10, 30))
        insert_appointment(connection, world, at(11), at(11, 30))
    assert count_for_dra_a(engine, world) == 4


def test_different_professionals_at_the_same_time_are_accepted(
    engine: Engine, world: World
) -> None:
    with engine.begin() as connection:
        insert_appointment(connection, world, at(10), at(10, 30), professional=world.dra_a)
        insert_appointment(connection, world, at(10), at(10, 30), professional=world.dr_b)
    with engine.connect() as connection:
        assert scalar(connection, "SELECT count(*) FROM appointments") == 2


def test_reactivating_a_cancelled_appointment_over_a_taken_slot_is_rejected(
    engine: Engine, world: World
) -> None:
    with engine.begin() as connection:
        cancelled = insert_appointment(connection, world, at(10), at(10, 30), status="cancelled")
        insert_appointment(connection, world, at(10), at(10, 30))
    with pytest.raises(IntegrityError) as raised, engine.begin() as connection:
        connection.execute(
            text("UPDATE appointments SET status = 'scheduled' WHERE id = :id"), {"id": cancelled}
        )
    assert sqlstate(raised) == EXCLUSION_VIOLATION
    with engine.connect() as connection:
        assert scalar(connection, "SELECT status FROM appointments WHERE id = :i", i=cancelled) == (
            "cancelled"
        )


def test_reactivating_a_cancelled_appointment_over_a_free_slot_is_accepted(
    engine: Engine, world: World
) -> None:
    with engine.begin() as connection:
        cancelled = insert_appointment(connection, world, at(10), at(10, 30), status="cancelled")
        connection.execute(
            text("UPDATE appointments SET status = 'scheduled' WHERE id = :id"), {"id": cancelled}
        )
    with engine.connect() as connection:
        assert scalar(connection, "SELECT status FROM appointments WHERE id = :i", i=cancelled) == (
            "scheduled"
        )


def test_moving_an_appointment_on_top_of_another_is_rejected_and_keeps_its_time(
    engine: Engine, world: World
) -> None:
    with engine.begin() as connection:
        insert_appointment(connection, world, at(10), at(10, 30))
        second = insert_appointment(connection, world, at(11), at(11, 30))
    with pytest.raises(IntegrityError) as raised, engine.begin() as connection:
        connection.execute(
            text("UPDATE appointments SET starts_at = :s, ends_at = :e WHERE id = :id"),
            {"s": at(10, 15), "e": at(10, 45), "id": second},
        )
    assert sqlstate(raised) == EXCLUSION_VIOLATION
    with engine.connect() as connection:
        starts = scalar(connection, "SELECT starts_at FROM appointments WHERE id = :i", i=second)
    assert starts == at(11)


def test_moving_an_appointment_over_its_own_previous_slot_is_accepted(
    engine: Engine, world: World
) -> None:
    with engine.begin() as connection:
        mine = insert_appointment(connection, world, at(10), at(10, 30))
        connection.execute(
            text("UPDATE appointments SET starts_at = :s, ends_at = :e WHERE id = :id"),
            {"s": at(10, 15), "e": at(10, 45), "id": mine},
        )
    with engine.connect() as connection:
        assert scalar(connection, "SELECT starts_at FROM appointments WHERE id = :i", i=mine) == at(
            10, 15
        )


def test_appointment_crossing_midnight_blocks_the_next_day_by_instants(
    engine: Engine, world: World
) -> None:
    with engine.begin() as connection:
        insert_appointment(connection, world, at(23, 45), at(0, 15, day=6))
    with pytest.raises(IntegrityError) as raised, engine.begin() as connection:
        insert_appointment(connection, world, at(0, 0, day=6), at(0, 30, day=6))
    assert sqlstate(raised) == EXCLUSION_VIOLATION
