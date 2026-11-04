"""Tests de la familia de errores de dominio (spec error-model)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar

import pytest

from app.core.errors import DomainError
from app.core.timezone import to_local
from app.domain.appointments.errors import AppointmentNotFoundError, SlotTakenError


def test_domain_error_has_default_code() -> None:
    assert DomainError.code == "DOMAIN_ERROR"
    assert isinstance(DomainError("algo"), Exception)


def test_subclass_can_define_its_own_code() -> None:
    class PacienteInactivoError(DomainError):
        code: ClassVar[str] = "PATIENT_INACTIVE"

    error = PacienteInactivoError("inactivo")

    assert isinstance(error, DomainError)
    assert error.code == "PATIENT_INACTIVE"
    assert DomainError.code == "DOMAIN_ERROR"


def test_slot_taken_belongs_to_family_and_keeps_data() -> None:
    starts_at = datetime(2026, 10, 5, 13, 0, tzinfo=UTC)

    error = SlotTakenError("dra-a", starts_at)

    assert isinstance(error, DomainError)
    assert error.code == "SLOT_TAKEN"
    assert error.professional_id == "dra-a"
    assert error.starts_at == starts_at
    assert str(error) == "Ese horario acaba de ocuparse. Elegí otro."


def test_appointment_not_found_belongs_to_family_and_keeps_data() -> None:
    error = AppointmentNotFoundError("apt-1")

    assert isinstance(error, DomainError)
    assert error.code == "APPOINTMENT_NOT_FOUND"
    assert error.appointment_id == "apt-1"
    assert str(error) == "APPOINTMENT_NOT_FOUND: apt-1"


def test_caller_input_errors_are_value_error_outside_the_family() -> None:
    with pytest.raises(ValueError) as info:
        to_local(datetime(2026, 10, 5, 10, 0), "America/Argentina/Buenos_Aires")

    assert not isinstance(info.value, DomainError)
