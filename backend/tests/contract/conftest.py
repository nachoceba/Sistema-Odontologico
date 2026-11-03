"""Fixtures de la bateria de contrato, parametrizadas por fabrica (design D-7).

Hoy solo existe la fabrica en memoria; C-02/C-08 agrega la de PostgreSQL con
``pytest.param(make_sqlalchemy, id="postgres", marks=pytest.mark.integration)``.
Los tests solo usan los puertos, nunca atributos de una implementacion concreta.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import pytest

from app.domain.appointments.ports import AppointmentRepository
from app.domain.patients.ports import PatientRepository
from app.domain.patients.types import Patient
from app.domain.schedules.ports import TimeOffRepository, WorkingHoursRepository
from app.domain.settings.ports import ClinicSettingsRepository
from app.domain.settings.types import ClinicSettings
from app.infrastructure.in_memory import (
    InMemoryAppointmentRepository,
    InMemoryClinicSettingsRepository,
    InMemoryPatientRepository,
    InMemoryTimeOffRepository,
    InMemoryWorkingHoursRepository,
)


class RepositoryFactory(Protocol):
    """Crea repositorios vacios (o con estado inicial) para un test."""

    def appointments(self) -> AppointmentRepository: ...

    def working_hours(self) -> WorkingHoursRepository: ...

    def time_off(self) -> TimeOffRepository: ...

    def patients(self, initial: Sequence[Patient] = ()) -> PatientRepository: ...

    def settings(
        self, initial: ClinicSettings | None = None
    ) -> ClinicSettingsRepository: ...


class InMemoryFactory:
    def appointments(self) -> AppointmentRepository:
        return InMemoryAppointmentRepository()

    def working_hours(self) -> WorkingHoursRepository:
        return InMemoryWorkingHoursRepository()

    def time_off(self) -> TimeOffRepository:
        return InMemoryTimeOffRepository()

    def patients(self, initial: Sequence[Patient] = ()) -> PatientRepository:
        return InMemoryPatientRepository(initial)

    def settings(
        self, initial: ClinicSettings | None = None
    ) -> ClinicSettingsRepository:
        return InMemoryClinicSettingsRepository(initial)


FACTORIES = [pytest.param(InMemoryFactory, id="in_memory")]


@pytest.fixture(params=FACTORIES)
def factory(request: pytest.FixtureRequest) -> RepositoryFactory:
    factory_class: type[RepositoryFactory] = request.param
    return factory_class()


@pytest.fixture
def appointment_repo(factory: RepositoryFactory) -> AppointmentRepository:
    return factory.appointments()


@pytest.fixture
def working_hours_repo(factory: RepositoryFactory) -> WorkingHoursRepository:
    return factory.working_hours()


@pytest.fixture
def time_off_repo(factory: RepositoryFactory) -> TimeOffRepository:
    return factory.time_off()
