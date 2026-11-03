"""Repositorio de pacientes sobre PostgreSQL (solo lectura, como el puerto de C-05d)."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.domain.patients.types import Patient
from app.infrastructure.db.models import PatientModel
from app.infrastructure.db.repositories._ids import parse_uuid


class SqlAlchemyPatientRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get(self, patient_id: str) -> Patient | None:
        key = parse_uuid(patient_id)
        if key is None:
            return None
        with self._session_factory() as session:
            row = session.get(PatientModel, key)
            if row is None:
                return None
            return Patient(
                id=str(row.id),
                first_name=row.first_name,
                last_name=row.last_name,
                email=row.email,
                active=row.active,
            )
