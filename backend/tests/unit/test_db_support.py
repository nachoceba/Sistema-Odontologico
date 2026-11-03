"""La guarda que impide que los tests de integracion toquen una base que no es de pruebas."""

from __future__ import annotations

import pytest

from tests.db_support import UnsafeDatabaseError, parse_test_url, require_test_database


def test_url_with_test_suffix_is_accepted() -> None:
    url = parse_test_url("postgresql+psycopg://u:p@db:5432/odonto_test")
    assert url.database == "odonto_test"


@pytest.mark.parametrize("name", ["odonto", "odonto_test_backup", "test", None, "", "a-b_test"])
def test_database_names_not_ending_in_test_are_refused(name: str | None) -> None:
    with pytest.raises(UnsafeDatabaseError):
        require_test_database(name)


def test_missing_variable_fails_with_a_message_naming_it() -> None:
    with pytest.raises(UnsafeDatabaseError, match="TEST_DATABASE_URL"):
        parse_test_url(None)


def test_url_pointing_to_the_development_database_is_refused() -> None:
    with pytest.raises(UnsafeDatabaseError):
        parse_test_url("postgresql+psycopg://u:p@db:5432/odonto")


def test_error_message_does_not_leak_the_password() -> None:
    with pytest.raises(UnsafeDatabaseError) as raised:
        parse_test_url("postgresql+psycopg://u:secreto-ficticio@db:5432/odonto")
    assert "secreto-ficticio" not in str(raised.value)
