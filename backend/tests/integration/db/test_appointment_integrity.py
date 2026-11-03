"""Integridad de los datos de un turno y de sus notificaciones (SQL directo)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.integration.db.helpers import (
    World,
    at,
    insert_appointment,
    make_world,
    scalar,
)


@pytest.fixture
def world(engine: Engine) -> World:
    with engine.begin() as connection:
        return make_world(connection)


# --- 3.2 Integridad de turnos -----------------------------------------------------


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(at(10, 30), at(10, 30), id="inicio_igual_fin"),
        pytest.param(at(10, 30), at(10), id="inicio_posterior_fin"),
    ],
)
def test_start_not_before_end_is_rejected_by_check(
    engine: Engine, world: World, start: datetime, end: datetime
) -> None:
    with (
        pytest.raises(IntegrityError, match="ck_appointments_starts_before_ends"),
        engine.begin() as connection,
    ):
        insert_appointment(connection, world, start, end)


def test_instant_written_in_another_zone_is_read_as_the_same_instant(
    engine: Engine, world: World
) -> None:
    minus_three = timezone(timedelta(hours=-3))
    with engine.begin() as connection:
        saved = insert_appointment(
            connection,
            world,
            datetime(2026, 10, 5, 10, 0, tzinfo=minus_three),
            datetime(2026, 10, 5, 10, 30, tzinfo=minus_three),
        )
    with engine.connect() as connection:
        starts = scalar(connection, "SELECT starts_at FROM appointments WHERE id = :i", i=saved)
    assert starts == datetime(2026, 10, 5, 13, 0, tzinfo=UTC)
    assert starts.utcoffset() is not None


def test_status_defaults_to_scheduled(engine: Engine, world: World) -> None:
    with engine.begin() as connection:
        saved = insert_appointment(connection, world, at(10), at(10, 30))
    with engine.connect() as connection:
        assert scalar(connection, "SELECT status FROM appointments WHERE id = :i", i=saved) == (
            "scheduled"
        )


def test_status_pending_is_not_a_valid_appointment_status(engine: Engine, world: World) -> None:
    with pytest.raises(DBAPIError, match="appointment_status"), engine.begin() as connection:
        insert_appointment(connection, world, at(10), at(10, 30), status="pending")


@pytest.mark.parametrize("missing", ["patient", "professional", "creator"])
def test_missing_patient_professional_or_creator_is_rejected_by_foreign_key(
    engine: Engine, world: World, missing: str
) -> None:
    params = {
        "patient": world.juan,
        "professional": world.dra_a,
        "creator": world.reception,
        "start": at(10),
        "end": at(10, 30),
    }
    params[missing] = uuid4()
    with pytest.raises(IntegrityError, match="violates foreign key"), engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO appointments "
                "(patient_id, professional_id, starts_at, ends_at, created_by) "
                "VALUES (:patient, :professional, :start, :end, :creator)"
            ),
            params,
        )


def test_updated_at_defaults_to_now_on_insert(engine: Engine, world: World) -> None:
    with engine.begin() as connection:
        saved = insert_appointment(connection, world, at(10), at(10, 30))
        delta = scalar(
            connection,
            "SELECT now() - updated_at FROM appointments WHERE id = :i",
            i=saved,
        )
    assert delta < timedelta(minutes=1)


# --- 3.3 Notificaciones -----------------------------------------------------------


def insert_notification(
    connection: object, appointment: object, kind: str, starts_at: datetime
) -> None:
    connection.execute(  # type: ignore[attr-defined]
        text(
            "INSERT INTO email_notifications (appointment_id, kind, appointment_starts_at) "
            "VALUES (:appointment, :kind, :starts)"
        ),
        {"appointment": appointment, "kind": kind, "starts": starts_at},
    )


def test_duplicate_reminder_for_the_same_appointment_and_start_is_rejected(
    engine: Engine, world: World
) -> None:
    with engine.begin() as connection:
        appointment = insert_appointment(connection, world, at(10), at(10, 30))
        insert_notification(connection, appointment, "reminder", at(10))
    with (
        pytest.raises(IntegrityError, match="uq_email_notifications"),
        engine.begin() as connection,
    ):
        insert_notification(connection, appointment, "reminder", at(10))


def test_rescheduled_appointment_accepts_a_new_confirmation(engine: Engine, world: World) -> None:
    with engine.begin() as connection:
        appointment = insert_appointment(connection, world, at(10), at(10, 30))
        insert_notification(connection, appointment, "confirmation", at(10))
        insert_notification(connection, appointment, "confirmation", at(11))
    with engine.connect() as connection:
        assert scalar(connection, "SELECT count(*) FROM email_notifications") == 2


def test_other_kind_for_the_same_appointment_is_accepted_with_pending_status(
    engine: Engine, world: World
) -> None:
    with engine.begin() as connection:
        appointment = insert_appointment(connection, world, at(10), at(10, 30))
        insert_notification(connection, appointment, "confirmation", at(10))
        insert_notification(connection, appointment, "reminder", at(10))
    with engine.connect() as connection:
        statuses = {
            row[0] for row in connection.execute(text("SELECT status FROM email_notifications"))
        }
    assert statuses == {"pending"}


def test_notification_of_a_missing_appointment_is_rejected(engine: Engine) -> None:
    with pytest.raises(IntegrityError, match="violates foreign key"), engine.begin() as connection:
        insert_notification(connection, uuid4(), "reminder", at(10))
