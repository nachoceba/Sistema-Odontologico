"""Reglas puras de datos del paciente (spec patient-data-rules)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.core.timezone import to_local
from app.domain.patients.errors import InvalidPatientDataError
from app.domain.patients.rules import (
    check_birth_date,
    clean_email,
    clean_name,
    clean_phone,
    normalize_document,
    normalize_document_prefix,
)

BUENOS_AIRES = "America/Argentina/Buenos_Aires"


# --- Documento (RN-PA-01) ---


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("30.111.222", "30111222"),
        (" aa 123-456 ", "AA123456"),
        ("30111222", "30111222"),
        ("x" * 20, "X" * 20),
        ("a" * 6, "A" * 6),
    ],
)
def test_document_is_normalized(typed: str, expected: str) -> None:
    assert normalize_document(typed) == expected


@pytest.mark.parametrize("typed", ["12.345", "30111222/1", "", "   ", "x" * 21, "30111ñ22", "..."])
def test_invalid_document_is_rejected(typed: str) -> None:
    with pytest.raises(ValueError):
        normalize_document(typed)


def test_same_document_written_differently_is_the_same() -> None:
    assert normalize_document("30.111.222") == normalize_document("30 111-222")


# --- Nombre, apellido y email (RN-PA-02) ---


def test_names_are_trimmed_and_kept_as_typed() -> None:
    assert clean_name(" Juan ") == "Juan"
    assert clean_name("Pérez") == "Pérez"


@pytest.mark.parametrize("typed", ["", "   "])
def test_blank_name_is_rejected(typed: str) -> None:
    with pytest.raises(ValueError):
        clean_name(typed)


def test_name_length_limit_is_100() -> None:
    assert clean_name("a" * 100) == "a" * 100
    with pytest.raises(ValueError):
        clean_name("a" * 101)


def test_email_is_trimmed_and_lowercased() -> None:
    assert clean_email(" Juan.Perez@Example.com ") == "juan.perez@example.com"
    assert clean_email("OTRA@Example.ORG") == "otra@example.org"


@pytest.mark.parametrize("typed", ["juan.example.com", "", "a@", "@b.com", "a b@c.com", "a@@b.com"])
def test_invalid_email_is_rejected(typed: str) -> None:
    with pytest.raises(ValueError):
        clean_email(typed)


# --- Teléfono ---


@pytest.mark.parametrize("typed", ["011-5550-0001", "+54 (11) 5550 0001", "123456"])
def test_valid_phone_is_kept_as_typed(typed: str) -> None:
    assert clean_phone(typed) == typed


def test_phone_is_trimmed() -> None:
    assert clean_phone("  011-5550-0001 ") == "011-5550-0001"


@pytest.mark.parametrize("typed", ["llamar tarde", "12345", "1" * 31, "011-5550-0001 int 2"])
def test_invalid_phone_is_rejected(typed: str) -> None:
    with pytest.raises(ValueError):
        clean_phone(typed)


@pytest.mark.parametrize("typed", ["", "   "])
def test_blank_phone_means_no_phone(typed: str) -> None:
    assert clean_phone(typed) is None


def test_phone_length_limit_is_30() -> None:
    thirty = "1" * 30
    assert clean_phone(thirty) == thirty


# --- Fecha de nacimiento ---

TODAY = date(2026, 11, 4)


def test_future_birth_date_is_rejected() -> None:
    with pytest.raises(InvalidPatientDataError):
        check_birth_date(date(2026, 11, 5), today=TODAY)


def test_born_today_is_accepted() -> None:
    check_birth_date(date(2026, 11, 4), today=TODAY)


def test_ordinary_past_date_is_accepted() -> None:
    check_birth_date(date(1990, 5, 10), today=TODAY)


def test_local_day_change_is_decided_by_clinic_timezone() -> None:
    clock = datetime(2026, 11, 5, 1, 0, tzinfo=UTC)  # 22:00 del 4 en Buenos Aires
    today = to_local(clock, BUENOS_AIRES).date()
    assert today == date(2026, 11, 4)
    with pytest.raises(InvalidPatientDataError):
        check_birth_date(date(2026, 11, 5), today=today)


def test_date_before_1900_is_rejected() -> None:
    with pytest.raises(InvalidPatientDataError):
        check_birth_date(date(1899, 12, 31), today=TODAY)
    check_birth_date(date(1900, 1, 1), today=TODAY)


# --- Inicio de documento para buscar ---


@pytest.mark.parametrize(
    ("typed", "expected"),
    [("30.111", "30111"), (" aa-1 ", "AA1"), ("3", "3"), ("30111222", "30111222")],
)
def test_document_prefix_is_normalized_without_length_limits(typed: str, expected: str) -> None:
    assert normalize_document_prefix(typed) == expected


@pytest.mark.parametrize("typed", ["", "  ", "..", "perez!", "Pérez", "x" * 21])
def test_text_that_cannot_start_a_document_gives_none(typed: str) -> None:
    assert normalize_document_prefix(typed) is None
