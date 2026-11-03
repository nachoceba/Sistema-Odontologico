"""Fixtures compartidas por los tests que usan PostgreSQL real (design D-8).

Viven en la raiz de ``tests`` porque las usan tanto ``tests/integration`` como la fabrica
``postgres`` de la bateria de contrato. Ninguna se evalua si el test no la pide, asi que los
tests por defecto no necesitan base. Si falta ``TEST_DATABASE_URL`` los tests de integracion
FALLAN con un mensaje claro (no se saltan en silencio).
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from tests.db_support import (
    APP_TABLES,
    TEST_URL_VARIABLE,
    UnsafeDatabaseError,
    downgrade_base,
    ensure_database,
    parse_test_url,
    require_test_database,
    upgrade_head,
)


@pytest.fixture(scope="session")
def test_database_url() -> URL:
    try:
        return parse_test_url(os.environ.get(TEST_URL_VARIABLE))
    except UnsafeDatabaseError as error:
        pytest.fail(str(error), pytrace=False)


@pytest.fixture(scope="session")
def migrated_engine(test_database_url: URL) -> Iterator[Engine]:
    """Base de pruebas creada si falta y migrada desde cero una vez por sesion."""
    ensure_database(test_database_url)
    downgrade_base(test_database_url)
    upgrade_head(test_database_url)
    engine = create_engine(test_database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def engine(migrated_engine: Engine) -> Engine:
    """Engine sobre la base de pruebas con las 8 tablas vacias."""
    require_test_database(migrated_engine.url.database)
    with migrated_engine.begin() as connection:
        tables = ", ".join(APP_TABLES)
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    return migrated_engine


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
