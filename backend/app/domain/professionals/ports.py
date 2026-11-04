"""Puerto de lectura de fichas de profesionales (P-13, design D-8)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from app.domain.professionals.types import UNSET, Unset

if TYPE_CHECKING:
    from app.domain.professionals.types import Professional


class ProfessionalRepository(Protocol):
    def list(self, *, only_active: bool = False) -> list[Professional]:
        """Las fichas ordenadas por nombre a mostrar sin distinguir mayusculas."""
        ...

    def get_by_id(self, professional_id: str) -> Professional | None:
        """La ficha (activa o no), o None si no existe o el id esta mal formado."""
        ...

    def update(
        self,
        professional_id: str,
        *,
        display_name: str | None = None,
        license_number: str | None | Unset = UNSET,
    ) -> Professional:
        """Cambia nombre a mostrar y/o matricula; devuelve la ficha actualizada.

        ``display_name=None`` no cambia el nombre. ``license_number=UNSET`` no cambia la
        matricula y ``None`` la borra. Id inexistente o mal formado: ProfessionalNotFoundError.
        """
        ...
