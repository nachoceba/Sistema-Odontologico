"""Importar el dominio o el modulo de sesion no carga la configuracion ni abre conexiones."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from app.infrastructure.db.session import create_db_engine, create_session_factory

BACKEND_DIR = Path(__file__).resolve().parents[3]

CHECK = """
import app.domain.appointments, app.domain.schedules, app.domain.patients, app.domain.settings
import app.infrastructure.db.session
from app.core.config import get_settings
from app.infrastructure.db.session import get_engine
assert get_settings.cache_info().currsize == 0, "settings cargada al importar"
assert get_engine.cache_info().currsize == 0, "engine creado al importar"
print("ok")
"""


def test_importing_domain_and_session_module_loads_nothing() -> None:
    result = subprocess.run(
        [sys.executable, "-c", CHECK],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_engine_and_factory_are_built_from_the_given_url_without_connecting() -> None:
    engine = create_db_engine("postgresql+psycopg://u:p@db-que-no-existe:5432/x_test")
    assert engine.url.database == "x_test"
    factory = create_session_factory(engine)
    assert isinstance(factory, sessionmaker)
    engine.dispose()
