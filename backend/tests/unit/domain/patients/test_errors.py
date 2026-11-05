"""Errores de la gestion de pacientes (spec error-model y patient-api)."""

from __future__ import annotations

import pytest

from app.core.errors import DomainError
from app.domain.patients.errors import (
    DocumentTakenError,
    InvalidPatientDataError,
    PatientHasAppointmentsError,
)


@pytest.mark.parametrize(
    ("error_class", "code", "message"),
    [
        (DocumentTakenError, "DOCUMENT_TAKEN", "Ya existe un paciente con ese documento"),
        (
            PatientHasAppointmentsError,
            "PATIENT_HAS_APPOINTMENTS",
            "No se puede borrar: tiene turnos. Desactivalo en su lugar",
        ),
        (
            InvalidPatientDataError,
            "INVALID_PATIENT_DATA",
            "La fecha de nacimiento no puede ser futura ni anterior a 1900",
        ),
    ],
)
def test_error_has_code_and_fixed_message(
    error_class: type[DomainError], code: str, message: str
) -> None:
    error = error_class()
    assert isinstance(error, DomainError)
    assert error.code == code
    assert str(error) == message
