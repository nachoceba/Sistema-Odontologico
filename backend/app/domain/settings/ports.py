"""Puerto de solo lectura de la configuracion del consultorio."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.settings.types import ClinicSettings


class ClinicSettingsRepository(Protocol):
    def get(self) -> ClinicSettings:
        """Configuracion vigente; los valores por defecto si no hay datos cargados."""
        ...
