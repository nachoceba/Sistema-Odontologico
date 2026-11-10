"""Puerto del catalogo de tratamientos y de lo que ofrece cada profesional (C-17, D-1)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.treatments.types import NewTreatment, Treatment


class TreatmentRepository(Protocol):
    def list_all(self) -> list[Treatment]:
        """Todo el catalogo (activos e inactivos), ordenado por nombre."""
        ...

    def get(self, treatment_id: str) -> Treatment | None:
        """El tratamiento, o None si no existe o el id esta mal formado."""
        ...

    def add(self, new: NewTreatment) -> Treatment:
        """Crea un tratamiento activo. Nombre repetido (por clave): TreatmentNameTakenError."""
        ...

    def update(
        self, treatment_id: str, *, name: str | None = None, active: bool | None = None
    ) -> Treatment:
        """Cambia nombre y/o estado; ``None`` no cambia. Inexistente: TreatmentNotFoundError;
        nombre de otro tratamiento: TreatmentNameTakenError."""
        ...

    def list_for_professional(self, professional_id: str) -> list[Treatment]:
        """Los asignados al profesional, activos e inactivos, ordenados por nombre."""
        ...

    def offered_ids(self, professional_id: str) -> frozenset[str]:
        """Ids de los tratamientos asignados y activos del profesional."""
        ...

    def list_offered(self, professional_id: str) -> list[Treatment]:
        """Los asignados y activos del profesional, ordenados por nombre."""
        ...

    def replace_for_professional(self, professional_id: str, treatment_ids: Sequence[str]) -> None:
        """Reemplaza el conjunto asignado; los repetidos cuentan una vez."""
        ...
