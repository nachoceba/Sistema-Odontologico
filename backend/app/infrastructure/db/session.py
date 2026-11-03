"""Motor y sesiones de SQLAlchemy (design D-1, D-7).

Nada se crea al importar: el engine se arma a demanda desde ``get_settings()``, igual que
la configuracion (importar el dominio nunca la dispara).
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def create_db_engine(url: str) -> Engine:
    """Engine para una URL dada (la de pruebas usa esta funcion con ``TEST_DATABASE_URL``)."""
    return create_engine(url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Fabrica de sesiones; cada operacion de repositorio abre la suya (DD-36)."""
    return sessionmaker(engine, expire_on_commit=False)


@lru_cache
def get_engine() -> Engine:
    return create_db_engine(get_settings().DATABASE_URL.get_secret_value())


def get_session_factory() -> sessionmaker[Session]:
    return create_session_factory(get_engine())
