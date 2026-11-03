"""Seed idempotente de datos ficticios de demostracion (spec seed-data, design D-10).

Uso (dentro del contenedor ``api``, despues de ``alembic upgrade head``)::

    python -m scripts.seed

Todo es ficticio: nombres, documentos, matriculas y emails ``@example.com``. La contrasena de
las cuentas de demo NO esta en el codigo: sale de la variable de entorno ``SEED_DEMO_PASSWORD``
y en la base solo queda su hash argon2. Volver a correr el seed solo agrega lo que falta: no pisa
cambios posteriores ni cambia contrasenas.
"""

from __future__ import annotations

import os
import sys
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.domain.appointments.types import WorkingHours
from app.domain.schedules.validation import validate_working_hours
from app.infrastructure.db.enums import UserRole
from app.infrastructure.db.models import (
    ClinicSettingsModel,
    PatientModel,
    ProfessionalModel,
    UserModel,
    WorkingHoursModel,
)

PASSWORD_VARIABLE = "SEED_DEMO_PASSWORD"
TIMEZONE_VARIABLE = "CLINIC_TIMEZONE"
BACKEND_DIR = Path(__file__).resolve().parents[1]

WEEKDAYS = range(5)  # lunes (0) a viernes (4)


class SeedError(RuntimeError):
    """El seed no puede correr; el mensaje nunca incluye valores sensibles."""


@dataclass(frozen=True)
class UserSeed:
    email: str
    full_name: str
    role: UserRole


@dataclass(frozen=True)
class ProfessionalSeed:
    user_email: str
    display_name: str
    license_number: str
    day_blocks: tuple[tuple[time, time], ...]


@dataclass(frozen=True)
class PatientSeed:
    first_name: str
    last_name: str
    document_number: str
    phone: str


USERS = (
    UserSeed("admin@example.com", "Administrador Demo", UserRole.ADMIN),
    UserSeed("recepcion@example.com", "Recepcion Demo", UserRole.RECEPTIONIST),
    UserSeed("dra.a@example.com", "Ana Alvarez", UserRole.DENTIST),
    UserSeed("dr.b@example.com", "Bruno Benitez", UserRole.DENTIST),
)

PROFESSIONALS = (
    ProfessionalSeed(
        "dra.a@example.com",
        "Dra. Ana Alvarez",
        "MAT-0001",
        ((time(9), time(13)), (time(14), time(18))),
    ),
    ProfessionalSeed("dr.b@example.com", "Dr. Bruno Benitez", "MAT-0002", ((time(13), time(20)),)),
)

PATIENTS = (
    PatientSeed("Juan", "Perez", "30111222", "011-5550-0001"),
    PatientSeed("Ana", "Gomez", "30111223", "011-5550-0002"),
    PatientSeed("Luis", "Fernandez", "30111224", "011-5550-0003"),
    PatientSeed("Marta", "Lopez", "30111225", "011-5550-0004"),
    PatientSeed("Carlos", "Diaz", "30111226", "011-5550-0005"),
    PatientSeed("Sofia", "Ramirez", "30111227", "011-5550-0006"),
    PatientSeed("Diego", "Sosa", "30111228", "011-5550-0007"),
    PatientSeed("Lucia", "Torres", "30111229", "011-5550-0008"),
    PatientSeed("Pablo", "Molina", "30111230", "011-5550-0009"),
    PatientSeed("Valeria", "Castro", "30111231", "011-5550-0010"),
)

CLINIC_NAME = "Consultorio Odontologico Demo"
CLINIC_ADDRESS = "Calle Ficticia 123, Ciudad Demo"
CLINIC_PHONE = "011-5550-0000"


def _ensure_migrated(engine: Engine) -> None:
    """La base debe estar en la ultima revision de Alembic; si no, no se crea nada."""
    config = Config((BACKEND_DIR / "alembic.ini").as_posix())
    config.set_main_option("script_location", (BACKEND_DIR / "alembic").as_posix())
    head = ScriptDirectory.from_config(config).get_current_head()
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
    if current != head:
        raise SeedError(
            "La base no tiene el esquema al dia: ejecute `alembic upgrade head` antes del seed."
        )


def _find_user_id(session: Session, email: str) -> uuid.UUID | None:
    return session.scalar(select(UserModel.id).where(func.lower(UserModel.email) == email.lower()))


def _seed_users(session: Session, password: str) -> None:
    for seed in USERS:
        if _find_user_id(session, seed.email) is None:
            session.add(
                UserModel(
                    email=seed.email,
                    password_hash=hash_password(password),  # sal propia por cuenta
                    full_name=seed.full_name,
                    role=seed.role,
                )
            )
            session.flush()


def _seed_professionals(session: Session) -> None:
    for seed in PROFESSIONALS:
        user_id = _find_user_id(session, seed.user_email)
        if user_id is None:  # pragma: no cover  (los usuarios se crean justo antes)
            raise SeedError(f"Falta la cuenta {seed.user_email} para el profesional")
        professional = session.scalar(
            select(ProfessionalModel).where(ProfessionalModel.user_id == user_id)
        )
        if professional is None:
            professional = ProfessionalModel(
                user_id=user_id,
                display_name=seed.display_name,
                license_number=seed.license_number,
            )
            session.add(professional)
            session.flush()
        _seed_working_hours(session, professional, seed)


def _seed_working_hours(
    session: Session, professional: ProfessionalModel, seed: ProfessionalSeed
) -> None:
    """Los tramos se cargan solo si el profesional no tiene ninguno."""
    has_blocks = session.scalar(
        select(func.count())
        .select_from(WorkingHoursModel)
        .where(WorkingHoursModel.professional_id == professional.id)
    )
    if has_blocks:
        return
    blocks = [
        WorkingHours(weekday=weekday, start_time=start, end_time=end)
        for weekday in WEEKDAYS
        for start, end in seed.day_blocks
    ]
    if not validate_working_hours(blocks).valid:  # pragma: no cover  (datos constantes)
        raise SeedError(f"Los tramos de {seed.display_name} no son validos")
    session.add_all(
        WorkingHoursModel(
            professional_id=professional.id,
            weekday=block.weekday,
            start_time=block.start_time,
            end_time=block.end_time,
        )
        for block in blocks
    )


def _seed_clinic_settings(session: Session, timezone: str) -> None:
    if session.get(ClinicSettingsModel, 1) is None:
        session.add(
            ClinicSettingsModel(
                id=1,
                clinic_name=CLINIC_NAME,
                address=CLINIC_ADDRESS,
                phone=CLINIC_PHONE,
                slot_minutes=30,
                timezone=timezone,
                reminder_send_hour=9,
                min_notice_hours=6,
            )
        )


def _seed_patients(session: Session) -> None:
    for seed in PATIENTS:
        exists = session.scalar(
            select(PatientModel.id).where(PatientModel.document_number == seed.document_number)
        )
        if exists is None:
            session.add(
                PatientModel(
                    first_name=seed.first_name,
                    last_name=seed.last_name,
                    document_number=seed.document_number,
                    email=f"{seed.first_name}.{seed.last_name}@example.com".lower(),
                    phone=seed.phone,
                )
            )


def run_seed(engine: Engine, *, password: str, timezone: str) -> None:
    """Carga los datos de demo en una sola transaccion: o queda todo o no queda nada."""
    if not password:
        raise SeedError(f"Falta la variable de entorno {PASSWORD_VARIABLE}")
    _ensure_migrated(engine)
    with Session(engine) as session, session.begin():
        _seed_users(session, password)
        _seed_professionals(session)
        _seed_clinic_settings(session, timezone)
        _seed_patients(session)


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "")
    if not value:
        raise SeedError(f"Falta la variable de entorno {name}")
    return value


def main(env: Mapping[str, str] | None = None, engine: Engine | None = None) -> int:
    """Punto de entrada: devuelve 0 si cargo (o ya estaba cargado) y 1 ante un error."""
    environment = os.environ if env is None else env
    try:
        password = _required(environment, PASSWORD_VARIABLE)
        timezone = _required(environment, TIMEZONE_VARIABLE)
        try:
            ZoneInfo(timezone)
        except (ValueError, OSError, KeyError) as error:
            raise SeedError(f"{TIMEZONE_VARIABLE} no es una zona horaria IANA valida") from error
        if engine is None:
            from app.infrastructure.db.session import get_engine

            engine = get_engine()
        run_seed(engine, password=password, timezone=timezone)
    except SeedError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print("Seed completo: datos ficticios de demostracion cargados (solo lo que faltaba).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
