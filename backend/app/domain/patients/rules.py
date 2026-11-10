"""Reglas puras de los datos del paciente (spec patient-data-rules). Solo libreria estandar.

Los textos invalidos lanzan ``ValueError`` (la API ya los rechazo con 422 antes de llegar
aca); la fecha de nacimiento invalida lanza ``InvalidPatientDataError`` (400).
"""

from __future__ import annotations

import re
from datetime import date

from app.domain.patients.errors import InvalidPatientDataError
from app.domain.text import comparable_text
from app.domain.users.rules import is_valid_email, normalize_email

DOCUMENT_MIN_LENGTH = 6
DOCUMENT_MAX_LENGTH = 20
NAME_MAX_LENGTH = 100
PHONE_MAX_LENGTH = 30
PHONE_MIN_DIGITS = 6
EARLIEST_BIRTH_DATE = date(1900, 1, 1)

_DOCUMENT_SEPARATORS = re.compile(r"[\s.\-]")
_DOCUMENT_PATTERN = re.compile(rf"^[A-Z0-9]{{{DOCUMENT_MIN_LENGTH},{DOCUMENT_MAX_LENGTH}}}$")
_PHONE_PATTERN = re.compile(r"^[0-9 +\-()]+$")


def normalize_document(text: str) -> str:
    """RN-PA-01: sin espacios, puntos ni guiones, en mayusculas; 6 a 20 letras A-Z y digitos."""
    normalized = _DOCUMENT_SEPARATORS.sub("", text).upper()
    if not normalized.isascii() or not _DOCUMENT_PATTERN.match(normalized):
        raise ValueError("documento invalido")
    return normalized


def clean_name(text: str) -> str:
    """Nombre o apellido recortado, de 1 a 100 caracteres."""
    cleaned = text.strip()
    if not cleaned or len(cleaned) > NAME_MAX_LENGTH:
        raise ValueError("el texto debe tener de 1 a 100 caracteres")
    return cleaned


def clean_email(text: str) -> str:
    """RN-PA-02: recortado, en minusculas y con el mismo formato que el email de las cuentas."""
    cleaned = normalize_email(text)
    if not is_valid_email(cleaned):
        raise ValueError("email invalido")
    return cleaned


def clean_phone(text: str) -> str | None:
    """Telefono recortado; en blanco es "sin telefono". Hasta 30 caracteres y 6 digitos."""
    cleaned = text.strip()
    if not cleaned:
        return None
    digits = sum(char.isdigit() for char in cleaned)
    if (
        len(cleaned) > PHONE_MAX_LENGTH
        or not _PHONE_PATTERN.match(cleaned)
        or digits < PHONE_MIN_DIGITS
    ):
        raise ValueError("telefono invalido")
    return cleaned


def check_birth_date(value: date, *, today: date) -> None:
    """Ni futura (``today`` es el dia local del consultorio) ni anterior a 1900-01-01."""
    if value > today or value < EARLIEST_BIRTH_DATE:
        raise InvalidPatientDataError


def normalize_document_prefix(text: str) -> str | None:
    """El inicio de un documento escrito a medias, normalizado; None si no puede serlo.

    Sirve para buscar: ``30.111`` -> ``30111``. Sin limite inferior de largo.
    """
    normalized = _DOCUMENT_SEPARATORS.sub("", text).upper()
    if not normalized or len(normalized) > DOCUMENT_MAX_LENGTH:
        return None
    if not normalized.isascii() or not normalized.isalnum():
        return None
    return normalized


def same_person_name(first: str, second: str) -> bool:
    """True si dos nombres (o apellidos) son el mismo sin contar mayusculas, tildes ni espacios."""
    left, right = comparable_text(first), comparable_text(second)
    return bool(left) and left == right
