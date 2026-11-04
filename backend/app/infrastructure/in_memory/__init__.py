"""Adaptadores en memoria de los puertos de dominio, para tests de aplicacion.

Dobles de prueba: ningun modulo de produccion los conecta (design D-6).
"""

from app.infrastructure.in_memory.appointments import InMemoryAppointmentRepository
from app.infrastructure.in_memory.notifications import InMemoryNotificationRepository
from app.infrastructure.in_memory.patients import InMemoryPatientRepository
from app.infrastructure.in_memory.professionals import InMemoryProfessionalRepository
from app.infrastructure.in_memory.schedules import (
    InMemoryTimeOffRepository,
    InMemoryWorkingHoursRepository,
)
from app.infrastructure.in_memory.settings import InMemoryClinicSettingsRepository
from app.infrastructure.in_memory.unit_of_work import InMemoryAgendaUnitOfWork
from app.infrastructure.in_memory.users import InMemoryUserAccountRepository

__all__ = [
    "InMemoryAgendaUnitOfWork",
    "InMemoryAppointmentRepository",
    "InMemoryClinicSettingsRepository",
    "InMemoryNotificationRepository",
    "InMemoryPatientRepository",
    "InMemoryProfessionalRepository",
    "InMemoryTimeOffRepository",
    "InMemoryUserAccountRepository",
    "InMemoryWorkingHoursRepository",
]
