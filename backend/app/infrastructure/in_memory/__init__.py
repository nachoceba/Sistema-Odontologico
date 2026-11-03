"""Adaptadores en memoria de los puertos de dominio, para tests de aplicacion.

Dobles de prueba: ningun modulo de produccion los conecta (design D-6).
"""

from app.infrastructure.in_memory.appointments import InMemoryAppointmentRepository
from app.infrastructure.in_memory.patients import InMemoryPatientRepository
from app.infrastructure.in_memory.schedules import (
    InMemoryTimeOffRepository,
    InMemoryWorkingHoursRepository,
)
from app.infrastructure.in_memory.settings import InMemoryClinicSettingsRepository

__all__ = [
    "InMemoryAppointmentRepository",
    "InMemoryClinicSettingsRepository",
    "InMemoryPatientRepository",
    "InMemoryTimeOffRepository",
    "InMemoryWorkingHoursRepository",
]
