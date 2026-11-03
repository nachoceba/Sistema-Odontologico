"""Bateria de contrato del repositorio de pacientes (spec patient-repository)."""

from __future__ import annotations

from app.domain.patients import EligibilityRejection, check_patient_can_book
from app.domain.patients.types import Patient
from tests.contract.conftest import RepositoryFactory

JUAN = Patient(
    id="pac-1",
    first_name="Juan",
    last_name="Perez",
    email="juan.perez@example.com",
    active=True,
)
ANA = Patient(
    id="pac-2",
    first_name="Ana",
    last_name="Gomez",
    email="ana.gomez@example.com",
    active=False,
)


def test_active_patient_is_found_with_all_fields(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN])
    found = repo.get("pac-1")
    assert found == JUAN
    assert found is not None
    assert found.active is True


def test_inactive_patient_active_flag_feeds_eligibility_rule(
    factory: RepositoryFactory,
) -> None:
    repo = factory.patients([JUAN, ANA])
    found = repo.get("pac-2")
    assert found is not None
    assert found.active is False
    result = check_patient_can_book(found.active)
    assert not result.allowed
    assert result.reason == EligibilityRejection.PATIENT_INACTIVE
    juan = repo.get("pac-1")
    assert juan is not None
    assert check_patient_can_book(juan.active).allowed


def test_unknown_patient_returns_none_without_error(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN])
    assert repo.get("no-existe") is None
