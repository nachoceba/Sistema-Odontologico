"""Elegibilidad del paciente para turnos nuevos (RN-PA-04)."""

from __future__ import annotations

from typing import Any

import pytest

from app.domain.patients import (
    EligibilityRejection,
    EligibilityResult,
    check_patient_can_book,
)


def test_active_patient_can_book() -> None:
    assert check_patient_can_book(True) == EligibilityResult.accept()


def test_inactive_patient_rejected() -> None:
    result = check_patient_can_book(False)
    assert result.allowed is False
    assert result.reason is EligibilityRejection.PATIENT_INACTIVE


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(None, id="none"),
        pytest.param("false", id="texto_false"),
        pytest.param(0, id="cero"),
    ],
)
def test_non_bool_active_raises(value: Any) -> None:
    with pytest.raises(ValueError):
        check_patient_can_book(value)
