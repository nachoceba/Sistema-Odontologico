"""Fixtures de los tests de la base: una base temporal vacia por test."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.engine import URL

from tests.db_support import drop_database, ensure_database


@pytest.fixture
def fresh_url(test_database_url: URL) -> Iterator[URL]:
    """Base temporal vacia (``<base>_mig_test``), borrada al terminar."""
    url = test_database_url.set(database=f"{test_database_url.database}_mig_test")
    drop_database(url)
    ensure_database(url)
    yield url
    drop_database(url)
