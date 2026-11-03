"""Horarios, licencias, identidad, borrado y configuracion del consultorio (SQL directo)."""

from __future__ import annotations

from datetime import date, time

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.integration.db.helpers import (
    at,
    insert_appointment,
    insert_patient,
    insert_professional,
    insert_user,
    insert_working_hours,
    make_world,
    scalar,
)

CLINIC_INSERT = "INSERT INTO clinic_settings (clinic_name, address, {column}) VALUES ('A', 'B', :v)"

# --- 3.4 Horarios y licencias -----------------------------------------------------


def test_valid_block_is_accepted(engine: Engine) -> None:
    with engine.begin() as connection:
        professional = insert_professional(connection)
        insert_working_hours(connection, professional, 0, time(9), time(13))
        assert scalar(connection, "SELECT count(*) FROM working_hours") == 1


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(time(13), time(9), id="invertido"),
        pytest.param(time(9), time(9), id="vacio"),
    ],
)
def test_inverted_or_empty_block_is_rejected(engine: Engine, start: time, end: time) -> None:
    with (
        pytest.raises(IntegrityError, match="ck_working_hours_start_before_end"),
        engine.begin() as connection,
    ):
        insert_working_hours(connection, insert_professional(connection), 0, start, end)


@pytest.mark.parametrize("weekday", [7, -1])
def test_weekday_out_of_range_is_rejected(engine: Engine, weekday: int) -> None:
    with (
        pytest.raises(IntegrityError, match="ck_working_hours_weekday_range"),
        engine.begin() as connection,
    ):
        insert_working_hours(
            connection, insert_professional(connection), weekday, time(9), time(13)
        )


@pytest.mark.parametrize("weekday", [0, 6])
def test_weekday_limits_are_accepted(engine: Engine, weekday: int) -> None:
    with engine.begin() as connection:
        insert_working_hours(
            connection, insert_professional(connection), weekday, time(9), time(13)
        )


def test_last_possible_end_of_the_day_is_accepted(engine: Engine) -> None:
    with engine.begin() as connection:
        insert_working_hours(connection, insert_professional(connection), 0, time(18), time(23, 59))


@pytest.mark.parametrize(
    ("start", "end", "constraint"),
    [
        pytest.param(time(9, 0, 30), time(13), "start_no_seconds", id="inicio_con_segundos"),
        pytest.param(time(9), time(13, 0, 30), "end_no_seconds", id="fin_con_segundos"),
    ],
)
def test_times_with_seconds_are_rejected(
    engine: Engine, start: time, end: time, constraint: str
) -> None:
    with pytest.raises(IntegrityError, match=constraint), engine.begin() as connection:
        insert_working_hours(connection, insert_professional(connection), 0, start, end)


def test_overlapping_blocks_of_the_same_day_are_not_checked_by_the_database(
    engine: Engine,
) -> None:
    """P-6: la no superposicion de tramos es del dominio (schedule-validation)."""
    with engine.begin() as connection:
        professional = insert_professional(connection)
        insert_working_hours(connection, professional, 0, time(9), time(13))
        insert_working_hours(connection, professional, 0, time(12), time(15))
        assert scalar(connection, "SELECT count(*) FROM working_hours") == 2


def insert_time_off(connection: object, professional: object, start: date, end: date) -> None:
    connection.execute(  # type: ignore[attr-defined]
        text(
            "INSERT INTO time_off (professional_id, starts_on, ends_on) VALUES (:p, :start, :end)"
        ),
        {"p": professional, "start": start, "end": end},
    )


def test_time_off_ending_before_it_starts_is_rejected(engine: Engine) -> None:
    with (
        pytest.raises(IntegrityError, match="ck_time_off_starts_before_or_on_ends"),
        engine.begin() as connection,
    ):
        insert_time_off(
            connection, insert_professional(connection), date(2026, 10, 10), date(2026, 10, 9)
        )


def test_one_day_time_off_is_accepted(engine: Engine) -> None:
    with engine.begin() as connection:
        insert_time_off(
            connection, insert_professional(connection), date(2026, 10, 9), date(2026, 10, 9)
        )
        assert scalar(connection, "SELECT count(*) FROM time_off") == 1


# --- 3.5 Identidad ----------------------------------------------------------------


def test_repeated_document_number_is_rejected(engine: Engine) -> None:
    with engine.begin() as connection:
        insert_patient(connection, document="30111222")
    with (
        pytest.raises(IntegrityError, match="uq_patients_document_number"),
        engine.begin() as connection,
    ):
        insert_patient(connection, first="Otro", document="30111222")


def test_patient_without_email_is_rejected(engine: Engine) -> None:
    with pytest.raises(IntegrityError, match="email"), engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO patients (first_name, last_name, document_number) "
                "VALUES ('Juan', 'Perez', '30111222')"
            )
        )


def test_user_email_is_unique_ignoring_case(engine: Engine) -> None:
    with engine.begin() as connection:
        insert_user(connection, email="recepcion@example.com")
    with pytest.raises(IntegrityError, match="uq_users_email_lower"), engine.begin() as connection:
        insert_user(connection, email="Recepcion@Example.com")


def test_different_user_emails_are_accepted(engine: Engine) -> None:
    with engine.begin() as connection:
        insert_user(connection, email="uno@example.com")
        insert_user(connection, email="dos@example.com")
        assert scalar(connection, "SELECT count(*) FROM users") == 2


def test_unknown_role_is_rejected(engine: Engine) -> None:
    with pytest.raises(DBAPIError, match="user_role"), engine.begin() as connection:
        insert_user(connection, role="patient")


def test_two_professionals_for_the_same_user_are_rejected(engine: Engine) -> None:
    with engine.begin() as connection:
        owner = insert_user(connection, role="dentist")
        insert_professional(connection, user_id=owner)
    with (
        pytest.raises(IntegrityError, match="uq_professionals_user_id"),
        engine.begin() as connection,
    ):
        insert_professional(connection, name="Otra ficha", user_id=owner)


def test_professional_without_a_user_is_rejected(engine: Engine) -> None:
    with pytest.raises(IntegrityError, match="user_id"), engine.begin() as connection:
        connection.execute(text("INSERT INTO professionals (display_name) VALUES ('Sin cuenta')"))


def test_patient_user_and_professional_are_active_by_default(engine: Engine) -> None:
    with engine.begin() as connection:
        insert_patient(connection)
        insert_professional(connection)
        assert scalar(connection, "SELECT bool_and(active) FROM patients") is True
        assert scalar(connection, "SELECT bool_and(active) FROM users") is True
        assert scalar(connection, "SELECT bool_and(active) FROM professionals") is True


# --- 3.6 Borrado (P-3) ------------------------------------------------------------


def test_deleting_a_patient_with_appointments_is_rejected_and_the_appointment_survives(
    engine: Engine,
) -> None:
    with engine.begin() as connection:
        world = make_world(connection)
        insert_appointment(connection, world, at(10), at(10, 30), status="cancelled")
    with (
        pytest.raises(IntegrityError, match="fk_appointments_patient_id_patients"),
        engine.begin() as connection,
    ):
        connection.execute(text("DELETE FROM patients WHERE id = :i"), {"i": world.juan})
    with engine.connect() as connection:
        assert scalar(connection, "SELECT count(*) FROM appointments") == 1
        assert scalar(connection, "SELECT count(*) FROM patients WHERE id = :i", i=world.juan) == 1


def test_deleting_a_patient_without_appointments_is_allowed(engine: Engine) -> None:
    with engine.begin() as connection:
        mistaken = insert_patient(connection, document="99999999")
        connection.execute(text("DELETE FROM patients WHERE id = :i"), {"i": mistaken})
        assert scalar(connection, "SELECT count(*) FROM patients") == 0


@pytest.mark.parametrize(
    ("table", "owner", "constraint"),
    [
        ("professionals", "dra_a", "fk_appointments_professional_id_professionals"),
        ("users", "reception", "fk_appointments_created_by_users"),
    ],
)
def test_deleting_a_professional_or_creator_user_with_appointments_is_rejected(
    engine: Engine, table: str, owner: str, constraint: str
) -> None:
    with engine.begin() as connection:
        world = make_world(connection)
        insert_appointment(connection, world, at(10), at(10, 30))
    with pytest.raises(IntegrityError, match=constraint), engine.begin() as connection:
        connection.execute(text(f"DELETE FROM {table} WHERE id = :i"), {"i": getattr(world, owner)})


def test_deleting_an_appointment_with_notifications_is_rejected(engine: Engine) -> None:
    with engine.begin() as connection:
        world = make_world(connection)
        appointment = insert_appointment(connection, world, at(10), at(10, 30))
        connection.execute(
            text(
                "INSERT INTO email_notifications (appointment_id, kind, appointment_starts_at) "
                "VALUES (:a, 'confirmation', :s)"
            ),
            {"a": appointment, "s": at(10)},
        )
    with (
        pytest.raises(IntegrityError, match="fk_email_notifications_appointment_id"),
        engine.begin() as connection,
    ):
        connection.execute(text("DELETE FROM appointments WHERE id = :i"), {"i": appointment})


# --- 3.6 Configuracion del consultorio --------------------------------------------


def test_clinic_settings_defaults(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO clinic_settings (clinic_name, address) "
                "VALUES ('Consultorio Demo', 'Calle Falsa 123')"
            )
        )
        row = connection.execute(
            text(
                "SELECT id, slot_minutes, timezone, reminder_send_hour, min_notice_hours "
                "FROM clinic_settings"
            )
        ).one()
    assert tuple(row) == (1, 30, "America/Argentina/Buenos_Aires", 9, 6)


def test_second_clinic_settings_row_is_rejected(engine: Engine) -> None:
    insert = text("INSERT INTO clinic_settings (clinic_name, address) VALUES ('A', 'B')")
    with engine.begin() as connection:
        connection.execute(insert)
    with pytest.raises(IntegrityError, match="pk_clinic_settings"), engine.begin() as connection:
        connection.execute(insert)
    with (
        pytest.raises(IntegrityError, match="ck_clinic_settings_single_row"),
        engine.begin() as connection,
    ):
        connection.execute(
            text("INSERT INTO clinic_settings (id, clinic_name, address) VALUES (2, 'A', 'B')")
        )


@pytest.mark.parametrize(
    ("column", "value", "constraint"),
    [
        ("slot_minutes", 0, "slot_minutes_positive"),
        ("slot_minutes", -5, "slot_minutes_positive"),
        ("min_notice_hours", -1, "min_notice_hours_not_negative"),
        ("reminder_send_hour", 24, "reminder_send_hour_range"),
        ("reminder_send_hour", -1, "reminder_send_hour_range"),
    ],
)
def test_clinic_settings_out_of_range_values_are_rejected(
    engine: Engine, column: str, value: int, constraint: str
) -> None:
    with pytest.raises(IntegrityError, match=constraint), engine.begin() as connection:
        connection.execute(
            text(CLINIC_INSERT.format(column=column)),
            {"v": value},
        )


@pytest.mark.parametrize(
    ("column", "value"),
    [("min_notice_hours", 0), ("reminder_send_hour", 0), ("reminder_send_hour", 23)],
)
def test_clinic_settings_range_limits_are_accepted(engine: Engine, column: str, value: int) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(CLINIC_INSERT.format(column=column)),
            {"v": value},
        )
