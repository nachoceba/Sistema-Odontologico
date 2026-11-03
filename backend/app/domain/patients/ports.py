"""Puerto del repositorio de pacientes: solo lectura minima (decision P-4).

Alta, busqueda y unicidad de documento se agregan en C-06.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.patients.types import Patient


class PatientRepository(Protocol):
    def get(self, patient_id: str) -> Patient | None:
        """El paciente, o None si no existe (no es un error)."""
        ...
