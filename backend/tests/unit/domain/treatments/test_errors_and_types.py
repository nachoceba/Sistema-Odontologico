"""Errores con codigo estable, tipos y puerto del catalogo de tratamientos."""

from __future__ import annotations

import dataclasses

import pytest

from app.core.errors import DomainError
from app.domain.treatments.errors import (
    InvalidTreatmentNameError,
    TreatmentNameTakenError,
    TreatmentNotAvailableError,
    TreatmentNotFoundError,
)
from app.domain.treatments.types import NewTreatment, Treatment


@pytest.mark.parametrize(
    ("error_class", "code"),
    [
        (TreatmentNotFoundError, "TREATMENT_NOT_FOUND"),
        (TreatmentNotAvailableError, "TREATMENT_NOT_AVAILABLE"),
        (TreatmentNameTakenError, "TREATMENT_NAME_TAKEN"),
    ],
)
def test_errors_have_a_stable_code_and_a_fixed_message(
    error_class: type[DomainError], code: str
) -> None:
    error = error_class()
    assert isinstance(error, DomainError)
    assert error.code == code
    assert str(error)


def test_invalid_name_is_a_value_error_not_a_domain_error() -> None:
    assert issubclass(InvalidTreatmentNameError, ValueError)
    assert not issubclass(InvalidTreatmentNameError, DomainError)


def test_types_are_immutable() -> None:
    treatment = Treatment(id="t1", name="Consulta", active=True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        treatment.name = "Otra"  # type: ignore[misc]
    assert NewTreatment(name="Consulta").name == "Consulta"
