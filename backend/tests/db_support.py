"""Ayudas para los tests contra PostgreSQL real (design D-8).

Seguridad: nada de lo que borra datos corre si el nombre de la base no termina en ``_test``.
"""

from __future__ import annotations

import re
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DB_SUFFIX = "_test"
TEST_URL_VARIABLE = "TEST_DATABASE_URL"
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_]+$")

# Orden de borrado seguro: primero las que referencian.
APP_TABLES = (
    "email_notifications",
    "appointments",
    "professional_treatments",
    "treatments",
    "time_off",
    "working_hours",
    "professionals",
    "users",
    "patients",
    "clinic_settings",
)
APP_ENUMS = ("user_role", "appointment_status", "notification_kind", "notification_status")


class UnsafeDatabaseError(RuntimeError):
    """El nombre de la base no termina en ``_test``: no se toca."""


def parse_test_url(raw: str | None) -> URL:
    """Valida ``TEST_DATABASE_URL``: presente y con una base cuyo nombre termine en ``_test``."""
    if not raw:
        raise UnsafeDatabaseError(
            f"Falta la variable {TEST_URL_VARIABLE}: los tests de integracion necesitan una "
            f"base de pruebas aparte (el nombre debe terminar en {TEST_DB_SUFFIX}). "
            "Ver .env.example."
        )
    url = make_url(raw)
    require_test_database(url.database)
    return url


def require_test_database(name: str | None) -> None:
    if not name or not name.endswith(TEST_DB_SUFFIX) or not _SAFE_NAME.match(name):
        raise UnsafeDatabaseError(
            f"La base '{name}' no termina en {TEST_DB_SUFFIX}: los tests de integracion se "
            "niegan a correr sobre ella."
        )


def ensure_database(url: URL) -> None:
    """Crea la base si falta (conectandose a la base de mantenimiento ``postgres``)."""
    require_test_database(url.database)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        admin.dispose()


def drop_database(url: URL) -> None:
    require_test_database(url.database)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
    finally:
        admin.dispose()


def alembic_config(url: URL) -> Config:
    config = Config((BACKEND_DIR / "alembic.ini").as_posix())
    config.set_main_option("script_location", (BACKEND_DIR / "alembic").as_posix())
    config.attributes["database_url"] = url
    return config


def upgrade_head(url: URL) -> None:
    require_test_database(url.database)
    command.upgrade(alembic_config(url), "head")


def _clear_online_appointments(url: URL) -> None:
    """La migracion 0003 no se revierte con turnos online: se vacian los de la base de pruebas."""
    engine = create_engine(url)
    try:
        if not inspect(engine).has_table("appointments"):
            return
        with engine.begin() as connection:
            online = connection.execute(
                text("SELECT count(*) FROM appointments WHERE created_by IS NULL")
            ).scalar_one()
            if online:
                connection.execute(text("TRUNCATE appointments CASCADE"))
    finally:
        engine.dispose()


def _clear_expiry_notices(url: URL) -> None:
    """La migracion 0004 no se revierte con avisos ``booking_expired``: se borran en pruebas."""
    engine = create_engine(url)
    try:
        if not inspect(engine).has_table("email_notifications"):
            return
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM email_notifications WHERE kind::text = 'booking_expired'")
            )
    finally:
        engine.dispose()


def downgrade_base(url: URL) -> None:
    require_test_database(url.database)
    _clear_expiry_notices(url)
    _clear_online_appointments(url)
    command.downgrade(alembic_config(url), "base")
