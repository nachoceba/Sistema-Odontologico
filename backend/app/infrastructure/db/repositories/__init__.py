"""Repositorios PostgreSQL (SQLAlchemy) de los puertos de dominio (design D-6, D-7)."""

from app.infrastructure.db.repositories.appointments import SqlAlchemyAppointmentRepository
from app.infrastructure.db.repositories.patients import SqlAlchemyPatientRepository
from app.infrastructure.db.repositories.professionals import SqlAlchemyProfessionalRepository
from app.infrastructure.db.repositories.schedules import (
    SqlAlchemyTimeOffRepository,
    SqlAlchemyWorkingHoursRepository,
)
from app.infrastructure.db.repositories.settings import SqlAlchemyClinicSettingsRepository
from app.infrastructure.db.repositories.users import SqlAlchemyUserAccountRepository

__all__ = [
    "SqlAlchemyAppointmentRepository",
    "SqlAlchemyClinicSettingsRepository",
    "SqlAlchemyPatientRepository",
    "SqlAlchemyProfessionalRepository",
    "SqlAlchemyTimeOffRepository",
    "SqlAlchemyUserAccountRepository",
    "SqlAlchemyWorkingHoursRepository",
]
