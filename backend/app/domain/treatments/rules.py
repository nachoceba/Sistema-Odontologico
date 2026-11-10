"""Reglas puras del catalogo de tratamientos (spec treatment-management). Solo estandar."""

from __future__ import annotations

from enum import Enum

from app.domain.text import comparable_text
from app.domain.treatments.errors import InvalidTreatmentNameError
from app.domain.treatments.types import Treatment

NAME_MAX_LENGTH = 80


class BookingCheck(Enum):
    """Resultado de ``check_treatment_for_booking``: aceptado o el motivo del rechazo."""

    OK = "OK"
    NOT_FOUND = "NOT_FOUND"
    INACTIVE = "INACTIVE"
    NOT_OFFERED = "NOT_OFFERED"


def clean_treatment_name(raw: str) -> str:
    """Recortado, con un solo espacio entre palabras y de 1 a 80 caracteres (DD-145)."""
    cleaned = " ".join(raw.split())
    if not cleaned or len(cleaned) > NAME_MAX_LENGTH:
        raise InvalidTreatmentNameError
    return cleaned


def treatment_name_key(name: str) -> str:
    """Clave unica del nombre: sin mayusculas, tildes ni espacios repetidos."""
    return comparable_text(name)


def check_treatment_for_booking(
    treatment: Treatment | None, offered_ids: frozenset[str]
) -> BookingCheck:
    """Un turno nuevo exige un tratamiento existente, activo y asignado al profesional.

    ``offered_ids`` son los tratamientos asignados al profesional del turno (DD-142).
    """
    if treatment is None:
        return BookingCheck.NOT_FOUND
    if not treatment.active:
        return BookingCheck.INACTIVE
    if treatment.id not in offered_ids:
        return BookingCheck.NOT_OFFERED
    return BookingCheck.OK
