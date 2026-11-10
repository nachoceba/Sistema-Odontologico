"""Errores del catalogo de tratamientos; mensajes fijos, sin datos de pacientes."""

from __future__ import annotations

from typing import ClassVar

from app.core.errors import DomainError


class InvalidTreatmentNameError(ValueError):
    """Nombre vacio o de mas de 80 caracteres (la API ya lo rechazo con 422, DD-18)."""

    def __init__(self) -> None:
        super().__init__("el nombre debe tener de 1 a 80 caracteres")


class TreatmentNotFoundError(DomainError):
    code: ClassVar[str] = "TREATMENT_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__("El tratamiento no existe")


class TreatmentNotAvailableError(DomainError):
    code: ClassVar[str] = "TREATMENT_NOT_AVAILABLE"

    def __init__(self) -> None:
        super().__init__("Ese tratamiento no está disponible con este profesional")


class TreatmentNameTakenError(DomainError):
    code: ClassVar[str] = "TREATMENT_NAME_TAKEN"

    def __init__(self) -> None:
        super().__init__("Ya existe un tratamiento con ese nombre")
