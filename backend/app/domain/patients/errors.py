"""Errores de la gestion de pacientes; mensajes fijos, sin datos del paciente (RN-PR-02)."""

from __future__ import annotations

from typing import ClassVar

from app.core.errors import DomainError


class DocumentTakenError(DomainError):
    code: ClassVar[str] = "DOCUMENT_TAKEN"

    def __init__(self) -> None:
        super().__init__("Ya existe un paciente con ese documento")


class PatientHasAppointmentsError(DomainError):
    code: ClassVar[str] = "PATIENT_HAS_APPOINTMENTS"

    def __init__(self) -> None:
        super().__init__("No se puede borrar: tiene turnos. Desactivalo en su lugar")


class InvalidPatientDataError(DomainError):
    code: ClassVar[str] = "INVALID_PATIENT_DATA"

    def __init__(self) -> None:
        super().__init__("La fecha de nacimiento no puede ser futura ni anterior a 1900")
