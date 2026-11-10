"""Repositorio de pacientes en memoria (doble de prueba; el estado inicial se inyecta)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import replace

from app.domain.appointments.errors import PatientNotFoundError
from app.domain.patients.errors import DocumentTakenError
from app.domain.patients.rules import normalize_document_prefix
from app.domain.patients.types import NewPatient, Patient, PatientChanges, PatientRecord
from app.domain.professionals.types import Unset


def _record_of(patient: Patient | PatientRecord) -> PatientRecord:
    """Un ``Patient`` minimo se carga con un documento ficticio derivado de su id."""
    if isinstance(patient, PatientRecord):
        return patient
    return PatientRecord(
        id=patient.id,
        first_name=patient.first_name,
        last_name=patient.last_name,
        document_number=f"DOC{patient.id}".upper(),
        email=patient.email,
        phone=None,
        birth_date=None,
        active=patient.active,
    )


class InMemoryPatientRepository:
    def __init__(self, initial: Iterable[Patient | PatientRecord] = ()) -> None:
        self._records = {record.id: record for record in map(_record_of, initial)}

    def get(self, patient_id: str) -> Patient | None:
        record = self._records.get(patient_id)
        if record is None:
            return None
        return Patient(
            id=record.id,
            first_name=record.first_name,
            last_name=record.last_name,
            email=record.email,
            active=record.active,
        )

    def snapshot(self) -> dict[str, PatientRecord]:
        """Copia del estado, para que la unidad de trabajo pueda revertir."""
        return dict(self._records)

    def restore(self, state: dict[str, PatientRecord]) -> None:
        self._records = dict(state)

    def get_by_document(self, document_number: str) -> PatientRecord | None:
        return next(
            (r for r in self._records.values() if r.document_number == document_number), None
        )

    def get_record(self, patient_id: str) -> PatientRecord | None:
        return self._records.get(patient_id)

    def search(self, *, text: str, include_inactive: bool, limit: int) -> list[PatientRecord]:
        needle = text.strip().casefold()
        prefix = normalize_document_prefix(text)
        matches = [
            record
            for record in self._records.values()
            if (include_inactive or record.active)
            and (
                not needle
                or needle in record.last_name.casefold()
                or (prefix is not None and record.document_number.startswith(prefix))
            )
        ]
        matches.sort(key=lambda r: (r.last_name, r.first_name, r.id))
        return matches[:limit]

    def add(self, patient: NewPatient) -> PatientRecord:
        if any(r.document_number == patient.document_number for r in self._records.values()):
            raise DocumentTakenError
        record = PatientRecord(
            id=str(uuid.uuid4()),
            first_name=patient.first_name,
            last_name=patient.last_name,
            document_number=patient.document_number,
            email=patient.email,
            phone=patient.phone,
            birth_date=patient.birth_date,
            active=True,
        )
        self._records[record.id] = record
        return record

    def update(self, patient_id: str, changes: PatientChanges) -> PatientRecord:
        current = self._require(patient_id)
        document = changes.document_number
        if document is not None and any(
            r.document_number == document and r.id != patient_id for r in self._records.values()
        ):
            raise DocumentTakenError
        updated = replace(
            current,
            first_name=current.first_name if changes.first_name is None else changes.first_name,
            last_name=current.last_name if changes.last_name is None else changes.last_name,
            document_number=current.document_number if document is None else document,
            email=current.email if changes.email is None else changes.email,
            phone=current.phone if isinstance(changes.phone, Unset) else changes.phone,
            birth_date=(
                current.birth_date if isinstance(changes.birth_date, Unset) else changes.birth_date
            ),
        )
        self._records[patient_id] = updated
        return updated

    def set_active(self, patient_id: str, active: bool) -> PatientRecord:
        updated = replace(self._require(patient_id), active=active)
        self._records[patient_id] = updated
        return updated

    def _require(self, patient_id: str) -> PatientRecord:
        record = self._records.get(patient_id)
        if record is None:
            raise PatientNotFoundError
        return record

    def delete(self, patient_id: str) -> bool:
        return self._records.pop(patient_id, None) is not None
