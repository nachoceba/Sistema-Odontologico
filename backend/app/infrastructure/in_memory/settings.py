"""Repositorio de configuracion del consultorio en memoria."""

from __future__ import annotations

from app.domain.settings.types import ClinicSettings


class InMemoryClinicSettingsRepository:
    def __init__(self, initial: ClinicSettings | None = None) -> None:
        self._settings = initial if initial is not None else ClinicSettings()

    def get(self) -> ClinicSettings:
        return self._settings
