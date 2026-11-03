"""Humo: la base de pruebas existe, esta migrada y se vacia entre tests."""

from __future__ import annotations

from sqlalchemy import Engine, text


def test_select_one_on_the_test_database(engine: Engine) -> None:
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar() == 1
        name = connection.execute(text("SELECT current_database()")).scalar()
    assert str(name).endswith("_test")


def test_a_inserted_row_is_visible_inside_its_own_test(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO patients (first_name, last_name, document_number, email) "
                "VALUES ('Juan', 'Perez', '30111222', 'juan.perez@example.com')"
            )
        )
        count = connection.execute(text("SELECT count(*) FROM patients")).scalar()
    assert count == 1


def test_b_tables_are_emptied_before_the_next_test(engine: Engine) -> None:
    # Depende de test_a: pytest corre los tests de un archivo en el orden en que se definen.
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM patients")).scalar() == 0
