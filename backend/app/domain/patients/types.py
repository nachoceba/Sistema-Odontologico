"""Tipos del dominio de pacientes. Solo libreria estandar."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain.professionals.types import UNSET, Unset


@dataclass(frozen=True)
class Patient:
    """Paciente para consulta; ``active`` es bool (se pasa a check_patient_can_book)."""

    id: str
    first_name: str
    last_name: str
    email: str
    active: bool


@dataclass(frozen=True)
class PatientRecord:
    """Ficha completa de un paciente (documento ya normalizado)."""

    id: str
    first_name: str
    last_name: str
    document_number: str
    email: str
    phone: str | None
    birth_date: date | None
    active: bool


@dataclass(frozen=True)
class NewPatient:
    """Datos ya validados de un alta; el paciente se guarda activo."""

    first_name: str
    last_name: str
    document_number: str
    email: str
    phone: str | None = None
    birth_date: date | None = None


@dataclass(frozen=True)
class PatientChanges:
    """Cambios parciales: ``None`` en un obligatorio y ``UNSET`` significan "no cambia".

    ``phone`` y ``birth_date`` aceptan ``None`` para borrar el dato.
    """

    first_name: str | None = None
    last_name: str | None = None
    document_number: str | None = None
    email: str | None = None
    phone: str | None | Unset = UNSET
    birth_date: date | None | Unset = UNSET
