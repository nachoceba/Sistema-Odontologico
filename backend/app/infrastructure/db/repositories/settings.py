"""Repositorio de la configuracion del consultorio sobre PostgreSQL (solo lectura)."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.domain.settings.types import ClinicSettings
from app.infrastructure.db.models import ClinicSettingsModel


class SqlAlchemyClinicSettingsRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get(self) -> ClinicSettings:
        """Fila unica ``id = 1``; sin fila devuelve los valores por defecto (no la crea)."""
        with self._session_factory() as session:
            row = session.get(ClinicSettingsModel, 1)
            if row is None:
                return ClinicSettings()
            return ClinicSettings(
                slot_minutes=row.slot_minutes,
                timezone=row.timezone,
                min_notice_hours=row.min_notice_hours,
            )
