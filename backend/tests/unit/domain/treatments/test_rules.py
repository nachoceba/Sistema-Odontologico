"""Reglas puras del catalogo de tratamientos (spec treatment-management)."""

from __future__ import annotations

import pytest

from app.domain.treatments.errors import InvalidTreatmentNameError
from app.domain.treatments.rules import (
    BookingCheck,
    check_treatment_for_booking,
    clean_treatment_name,
    treatment_name_key,
)
from app.domain.treatments.types import Treatment


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Limpieza   dental ", "Limpieza dental"),
        ("Extracción", "Extracción"),
        ("x", "x"),
        ("y" * 80, "y" * 80),
        ("a\t b\n c", "a b c"),
    ],
)
def test_clean_treatment_name_trims_and_collapses_spaces(raw: str, expected: str) -> None:
    assert clean_treatment_name(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "\t\n", "y" * 81, " " + "y" * 81 + " "])
def test_clean_treatment_name_rejects_empty_and_too_long_names(raw: str) -> None:
    with pytest.raises(InvalidTreatmentNameError):
        clean_treatment_name(raw)


def test_clean_treatment_name_counts_length_after_collapsing_spaces() -> None:
    assert clean_treatment_name("a" + " " * 10 + "b" * 78) == "a " + "b" * 78


def test_name_key_ignores_case_marks_and_spaces() -> None:
    assert treatment_name_key("Extracción") == treatment_name_key("  extraccion ")
    assert treatment_name_key("Limpieza dental") == "LIMPIEZA DENTAL"


def test_name_key_differs_for_different_treatments() -> None:
    assert treatment_name_key("Consulta") != treatment_name_key("Consultas")


def _treatment(*, active: bool = True) -> Treatment:
    return Treatment(id="t1", name="Limpieza dental", active=active)


def test_check_accepts_an_active_offered_treatment() -> None:
    assert check_treatment_for_booking(_treatment(), frozenset({"t1", "t2"})) is BookingCheck.OK


def test_check_rejects_a_missing_treatment() -> None:
    assert check_treatment_for_booking(None, frozenset({"t1"})) is BookingCheck.NOT_FOUND


def test_check_rejects_an_inactive_treatment_even_when_assigned() -> None:
    result = check_treatment_for_booking(_treatment(active=False), frozenset({"t1"}))
    assert result is BookingCheck.INACTIVE


def test_check_rejects_a_treatment_the_professional_does_not_offer() -> None:
    assert check_treatment_for_booking(_treatment(), frozenset({"t2"})) is BookingCheck.NOT_OFFERED


def test_check_with_nothing_offered_rejects_as_not_offered() -> None:
    assert check_treatment_for_booking(_treatment(), frozenset()) is BookingCheck.NOT_OFFERED


def test_check_reports_inactive_before_not_offered() -> None:
    result = check_treatment_for_booking(_treatment(active=False), frozenset())
    assert result is BookingCheck.INACTIVE
