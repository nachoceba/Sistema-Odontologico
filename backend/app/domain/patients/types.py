"""Tipos del dominio de pacientes. Solo libreria estandar."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Patient:
    """Paciente para consulta; ``active`` es bool (se pasa a check_patient_can_book)."""

    id: str
    first_name: str
    last_name: str
    email: str
    active: bool
