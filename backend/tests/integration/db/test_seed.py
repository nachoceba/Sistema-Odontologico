"""El seed carga datos ficticios, es idempotente y no guarda secretos (spec seed-data)."""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL

from app.domain.appointments.types import WorkingHours
from app.domain.schedules.validation import validate_working_hours
from scripts.seed import PASSWORD_VARIABLE, SeedError, main, run_seed
from tests.db_support import upgrade_head
from tests.integration.db.helpers import scalar

PASSWORD = "clave-demo-ficticia-de-prueba"
ZONE = "America/Argentina/Cordoba"
TABLES = (
    "users",
    "professionals",
    "working_hours",
    "time_off",
    "patients",
    "appointments",
    "email_notifications",
    "clinic_settings",
    "treatments",
    "professional_treatments",
)


def counts(engine: Engine) -> dict[str, int]:
    with engine.connect() as connection:
        return {t: int(scalar(connection, f"SELECT count(*) FROM {t}")) for t in TABLES}


def test_seed_on_an_empty_database_loads_the_demo_data(engine: Engine) -> None:
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    with engine.connect() as connection:
        role_rows = connection.execute(text("SELECT role, count(*) FROM users GROUP BY role"))
        roles = {str(row[0]): int(row[1]) for row in role_rows}
        professionals = connection.execute(
            text(
                "SELECT p.display_name, u.role FROM professionals p "
                "JOIN users u ON u.id = p.user_id"
            )
        ).all()
        weekdays = {
            row[0] for row in connection.execute(text("SELECT DISTINCT weekday FROM working_hours"))
        }
        settings = connection.execute(
            text(
                "SELECT slot_minutes, timezone, reminder_send_hour, min_notice_hours, clinic_name "
                "FROM clinic_settings"
            )
        ).one()
        active_patients = scalar(connection, "SELECT count(*) FROM patients WHERE active")
    assert roles == {"admin": 1, "receptionist": 1, "dentist": 2}
    assert len(professionals) == 2
    assert {role for _, role in professionals} == {"dentist"}
    assert weekdays == {0, 1, 2, 3, 4}
    assert tuple(settings)[:4] == (30, ZONE, 9, 6)
    assert settings[4]
    assert active_patients == 10
    totals = counts(engine)
    assert (totals["appointments"], totals["email_notifications"], totals["time_off"]) == (0, 0, 0)
    assert totals["patients"] == 10


def test_working_hours_loaded_by_the_seed_pass_the_domain_validation(engine: Engine) -> None:
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    with engine.connect() as connection:
        professional_ids = [r[0] for r in connection.execute(text("SELECT id FROM professionals"))]
        assert len(professional_ids) == 2
        for professional_id in professional_ids:
            rows = connection.execute(
                text(
                    "SELECT weekday, start_time, end_time FROM working_hours "
                    "WHERE professional_id = :p"
                ),
                {"p": professional_id},
            ).all()
            assert rows
            blocks = [WorkingHours(weekday=w, start_time=s, end_time=e) for w, s, e in rows]
            assert validate_working_hours(blocks).valid


def test_timezone_comes_from_the_argument_not_from_a_fixed_value(engine: Engine) -> None:
    run_seed(engine, password=PASSWORD, timezone="America/Argentina/Salta")
    with engine.connect() as connection:
        assert scalar(connection, "SELECT timezone FROM clinic_settings") == (
            "America/Argentina/Salta"
        )


def test_passwords_are_stored_only_as_argon2_hashes(engine: Engine) -> None:
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    with engine.connect() as connection:
        hashes = [r[0] for r in connection.execute(text("SELECT password_hash FROM users"))]
    assert len(hashes) == 4
    assert all(h.startswith("$argon2") and PASSWORD not in h for h in hashes)
    assert len(set(hashes)) == 4  # sal distinta por cuenta


def test_only_fictitious_example_com_emails(engine: Engine) -> None:
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    with engine.connect() as connection:
        emails = [r[0] for r in connection.execute(text("SELECT email FROM users"))]
        emails += [r[0] for r in connection.execute(text("SELECT email FROM patients"))]
    assert len(emails) == 14
    assert all(e.endswith("@example.com") for e in emails)


# --- Idempotencia -----------------------------------------------------------------


def test_running_twice_leaves_the_same_row_counts(engine: Engine) -> None:
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    first = counts(engine)
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    assert counts(engine) == first
    assert first["users"] == 4


def test_later_changes_and_passwords_are_kept_on_a_second_run(engine: Engine) -> None:
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    with engine.begin() as connection:
        connection.execute(text("UPDATE clinic_settings SET slot_minutes = 20"))
        connection.execute(
            text(
                "UPDATE patients SET active = false WHERE document_number = "
                "(SELECT min(document_number) FROM patients)"
            )
        )
        connection.execute(text("UPDATE users SET password_hash = 'hash-cambiado'"))
        connection.execute(text("DELETE FROM working_hours WHERE weekday = 4"))
    run_seed(engine, password="otra-clave-ficticia", timezone="America/Argentina/Salta")
    with engine.connect() as connection:
        assert scalar(connection, "SELECT slot_minutes FROM clinic_settings") == 20
        assert scalar(connection, "SELECT timezone FROM clinic_settings") == ZONE
        assert scalar(connection, "SELECT count(*) FROM patients WHERE NOT active") == 1
        assert scalar(connection, "SELECT count(DISTINCT password_hash) FROM users") == 1
        assert scalar(connection, "SELECT count(*) FROM working_hours WHERE weekday = 4") == 0


def test_user_that_already_exists_with_other_case_is_not_duplicated(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (email, password_hash, full_name, role) "
                "VALUES ('ADMIN@Example.com', 'hash-previo', 'Admin previo', 'admin')"
            )
        )
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    with engine.connect() as connection:
        assert scalar(connection, "SELECT count(*) FROM users WHERE role = 'admin'") == 1
        assert scalar(connection, "SELECT count(*) FROM users") == 4


# --- Errores ----------------------------------------------------------------------


def test_seed_without_migration_fails_and_creates_nothing(fresh_url: URL) -> None:
    engine = create_engine(fresh_url)
    try:
        with pytest.raises(SeedError, match="alembic upgrade head"):
            run_seed(engine, password=PASSWORD, timezone=ZONE)
        with engine.connect() as connection:
            tables = scalar(
                connection,
                "SELECT count(*) FROM pg_tables WHERE schemaname = 'public' "
                "AND tablename = 'users'",
            )
        assert tables == 0
    finally:
        engine.dispose()


def test_seed_with_outdated_migration_state_fails(fresh_url: URL) -> None:
    upgrade_head(fresh_url)
    engine = create_engine(fresh_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num = '0000_viejo'"))
        with pytest.raises(SeedError, match="alembic upgrade head"):
            run_seed(engine, password=PASSWORD, timezone=ZONE)
        assert counts_if_possible(engine) == 0
    finally:
        engine.dispose()


def counts_if_possible(engine: Engine) -> int:
    with engine.connect() as connection:
        return int(scalar(connection, "SELECT count(*) FROM users"))


@pytest.mark.parametrize("password", [None, ""])
def test_missing_password_variable_names_it_creates_nothing_and_leaks_nothing(
    engine: Engine, password: str | None, capsys: pytest.CaptureFixture[str]
) -> None:
    env = {"CLINIC_TIMEZONE": ZONE}
    if password is not None:
        env[PASSWORD_VARIABLE] = password
    assert main(env, engine=engine) == 1
    error = capsys.readouterr().err
    assert PASSWORD_VARIABLE in error
    assert ZONE not in error
    assert counts(engine)["users"] == 0


def test_main_runs_the_seed_with_the_environment_and_reports_success(
    engine: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    env = {PASSWORD_VARIABLE: PASSWORD, "CLINIC_TIMEZONE": ZONE}
    assert main(env, engine=engine) == 0
    output = capsys.readouterr()
    assert PASSWORD not in output.out + output.err
    assert counts(engine)["users"] == 4


def test_main_with_missing_timezone_fails_naming_the_variable(
    engine: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main({PASSWORD_VARIABLE: PASSWORD}, engine=engine) == 1
    assert "CLINIC_TIMEZONE" in capsys.readouterr().err
    assert counts(engine)["users"] == 0


# --- Tratamientos de ejemplo (C-17, DD-151) -------------------------------------------------

ALL_FIVE = {"Consulta", "Limpieza dental", "Extracción", "Arreglo de caries", "Blanqueamiento"}
ANA = "Dra. Ana Alvarez"
BRUNO = "Dr. Bruno Benitez"


def offered_names(engine: Engine, professional: str, *, only_active: bool = True) -> set[str]:
    sql = (
        "SELECT t.name FROM treatments t "
        "JOIN professional_treatments pt ON pt.treatment_id = t.id "
        "JOIN professionals p ON p.id = pt.professional_id "
        "WHERE p.display_name = :name"
    )
    if only_active:
        sql += " AND t.active"
    with engine.connect() as connection:
        return {str(r[0]) for r in connection.execute(text(sql), {"name": professional})}


def test_the_seed_loads_exactly_the_five_active_example_treatments(engine: Engine) -> None:
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT name, active FROM treatments")).all()
    assert {str(r[0]) for r in rows} == ALL_FIVE
    assert len(rows) == 5
    assert all(r[1] for r in rows)


def test_ana_offers_the_five_and_bruno_all_but_whitening(engine: Engine) -> None:
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    assert offered_names(engine, ANA) == ALL_FIVE
    assert offered_names(engine, BRUNO) == ALL_FIVE - {"Blanqueamiento"}


def test_both_professionals_are_offered_online_with_different_public_treatments(
    engine: Engine,
) -> None:
    from sqlalchemy.orm import sessionmaker

    from app.infrastructure.db.repositories import SqlAlchemyTreatmentRepository

    run_seed(engine, password=PASSWORD, timezone=ZONE)
    repo = SqlAlchemyTreatmentRepository(sessionmaker(engine))
    with engine.connect() as connection:
        ids = {
            str(r[0]): str(r[1])
            for r in connection.execute(text("SELECT display_name, id FROM professionals"))
        }
    public = {name: {t.name for t in repo.list_offered(pid)} for name, pid in ids.items()}
    assert public[ANA] == ALL_FIVE
    assert public[BRUNO] == ALL_FIVE - {"Blanqueamiento"}
    assert public[ANA] != public[BRUNO]


def test_the_seed_creates_no_appointments_for_the_treatments(engine: Engine) -> None:
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    assert counts(engine)["appointments"] == 0


def test_later_treatment_changes_are_kept_on_a_second_run(engine: Engine) -> None:
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE treatments SET active = false WHERE name = 'Blanqueamiento'")
        )
        connection.execute(
            text(
                "DELETE FROM professional_treatments WHERE professional_id = "
                "(SELECT id FROM professionals WHERE display_name = :b) AND treatment_id = "
                "(SELECT id FROM treatments WHERE name = 'Extracción')"
            ),
            {"b": BRUNO},
        )
    before = counts(engine)
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    assert counts(engine) == before
    with engine.connect() as connection:
        assert (
            scalar(connection, "SELECT active FROM treatments WHERE name = 'Blanqueamiento'")
            is False
        )
    assert "Extracción" not in offered_names(engine, BRUNO)


def test_a_renamed_treatment_keeps_its_new_name(engine: Engine) -> None:
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE treatments SET name = 'Limpieza profunda', name_key = 'limpieza profunda' "
                "WHERE name = 'Limpieza dental'"
            )
        )
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    with engine.connect() as connection:
        assert (
            scalar(connection, "SELECT count(*) FROM treatments WHERE name = 'Limpieza profunda'")
            == 1
        )


def test_a_database_seeded_before_c17_receives_the_treatments_and_nothing_else_changes(
    engine: Engine,
) -> None:
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM professional_treatments"))
        connection.execute(text("DELETE FROM treatments"))
    before = counts(engine)
    assert before["treatments"] == 0
    run_seed(engine, password=PASSWORD, timezone=ZONE)
    after = counts(engine)
    assert after["treatments"] == 5
    assert after["professional_treatments"] == 9
    assert {k: v for k, v in after.items() if not k.endswith("treatments")} == {
        k: v for k, v in before.items() if not k.endswith("treatments")
    }
    assert offered_names(engine, ANA) == ALL_FIVE
