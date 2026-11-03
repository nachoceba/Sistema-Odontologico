"""Entorno de Alembic: la URL de la base sale de ``get_settings()`` (D-1).

Los tests de integracion pasan otra URL (base ``*_test``) con
``config.attributes["database_url"]``; asi nunca tocan la base de desarrollo.
``target_metadata`` son los modelos de ``app.infrastructure.db`` (C-02): sirve para comparar
modelos y base; la migracion se escribe a mano y el autogenerate es solo un control (D-2).
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import URL

from alembic import context
from app.core.config import get_settings
from app.infrastructure.db import models  # noqa: F401  (registra las tablas en la metadata)
from app.infrastructure.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str | URL:
    override = config.attributes.get("database_url")
    if override is not None:
        return override  # type: ignore[no-any-return]
    return get_settings().DATABASE_URL.get_secret_value()


def run_migrations_offline() -> None:
    """Genera SQL sin conectarse a la base."""
    url = _database_url()
    context.configure(
        url=url if isinstance(url, str) else url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Corre las migraciones contra la base real."""
    connectable = create_engine(_database_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
