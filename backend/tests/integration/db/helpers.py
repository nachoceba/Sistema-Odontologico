"""Inserts SQL directos (sin repositorios ni dominio) para probar que la base protege sola.

Todos los datos son ficticios. Las horas se dan en hora local de Buenos Aires (UTC-03:00) del
lunes 5 de octubre de 2026; la base guarda instantes (RN-GL-01).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import Connection, text

BA = ZoneInfo("America/Argentina/Buenos_Aires")
_counter = itertools.count(1)


def at(hour: int, minute: int = 0, *, day: int = 5) -> datetime:
    """Instante UTC de una hora local de Buenos Aires de octubre de 2026."""
    return datetime(2026, 10, day, hour, minute, tzinfo=BA).astimezone(UTC)


def insert_user(
    connection: Connection, *, email: str | None = None, role: str = "receptionist"
) -> UUID:
    n = next(_counter)
    return _one(
        connection,
        "INSERT INTO users (email, password_hash, full_name, role) "
        "VALUES (:email, 'hash-ficticio', :name, :role) RETURNING id",
        {"email": email or f"usuario{n}@example.com", "name": f"Usuario {n}", "role": role},
    )


def insert_professional(
    connection: Connection, *, name: str = "Dra. A", user_id: UUID | None = None
) -> UUID:
    owner = user_id or insert_user(connection, role="dentist")
    return _one(
        connection,
        "INSERT INTO professionals (user_id, display_name) VALUES (:user, :name) RETURNING id",
        {"user": owner, "name": name},
    )


def insert_patient(
    connection: Connection, *, first: str = "Juan", last: str = "Perez", document: str | None = None
) -> UUID:
    n = next(_counter)
    return _one(
        connection,
        "INSERT INTO patients (first_name, last_name, document_number, email) "
        "VALUES (:first, :last, :document, :email) RETURNING id",
        {
            "first": first,
            "last": last,
            "document": document or f"3000{n:04d}",
            "email": f"paciente{n}@example.com",
        },
    )


@dataclass(frozen=True)
class World:
    """Datos minimos para insertar turnos: dos profesionales, dos pacientes, una recepcionista."""

    dra_a: UUID
    dr_b: UUID
    juan: UUID
    ana: UUID
    reception: UUID


def make_world(connection: Connection) -> World:
    return World(
        dra_a=insert_professional(connection, name="Dra. A"),
        dr_b=insert_professional(connection, name="Dr. B"),
        juan=insert_patient(connection, first="Juan", last="Perez"),
        ana=insert_patient(connection, first="Ana", last="Gomez"),
        reception=insert_user(connection, email="recepcion@example.com"),
    )


def insert_appointment(
    connection: Connection,
    world: World,
    start: datetime,
    end: datetime,
    *,
    professional: UUID | None = None,
    patient: UUID | None = None,
    status: str | None = None,
) -> UUID:
    columns = "patient_id, professional_id, starts_at, ends_at, created_by"
    values = ":patient, :professional, :start, :end, :user"
    params: dict[str, Any] = {
        "patient": patient or world.juan,
        "professional": professional or world.dra_a,
        "start": start,
        "end": end,
        "user": world.reception,
    }
    if status is not None:
        columns += ", status"
        values += ", :status"
        params["status"] = status
    return _one(
        connection,
        f"INSERT INTO appointments ({columns}) VALUES ({values}) RETURNING id",
        params,
    )


def insert_working_hours(
    connection: Connection, professional: UUID, weekday: int, start: time, end: time
) -> UUID:
    return _one(
        connection,
        "INSERT INTO working_hours (professional_id, weekday, start_time, end_time) "
        "VALUES (:professional, :weekday, :start, :end) RETURNING id",
        {"professional": professional, "weekday": weekday, "start": start, "end": end},
    )


def scalar(connection: Connection, sql: str, **params: Any) -> Any:
    return connection.execute(text(sql), params).scalar()


def _one(connection: Connection, sql: str, params: dict[str, Any]) -> UUID:
    value = connection.execute(text(sql), params).scalar_one()
    assert isinstance(value, UUID)
    return value
