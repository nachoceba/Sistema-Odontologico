"""Repositorio de pacientes sobre PostgreSQL (puerto de C-05d ampliado en C-06).

Los rechazos de la base (documento repetido, paciente con turnos) se traducen sin registrar
ni conservar el detalle de la excepcion: lleva el valor del documento (RN-PR-02).
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.appointments.errors import PatientNotFoundError
from app.domain.patients.errors import DocumentTakenError, PatientHasAppointmentsError
from app.domain.patients.rules import normalize_document_prefix
from app.domain.patients.types import NewPatient, Patient, PatientChanges, PatientRecord
from app.domain.professionals.types import Unset
from app.infrastructure.db.models import PatientModel
from app.infrastructure.db.repositories._ids import parse_uuid
from app.infrastructure.db.scope import SessionScope

DOCUMENT_UNIQUE_CONSTRAINT = "uq_patients_document_number"
FOREIGN_KEY_VIOLATION = "23503"


def _record(row: PatientModel) -> PatientRecord:
    return PatientRecord(
        id=str(row.id),
        first_name=row.first_name,
        last_name=row.last_name,
        document_number=row.document_number,
        email=row.email,
        phone=row.phone,
        birth_date=row.birth_date,
        active=row.active,
    )


def _apply(row: PatientModel, changes: PatientChanges) -> None:
    if changes.first_name is not None:
        row.first_name = changes.first_name
    if changes.last_name is not None:
        row.last_name = changes.last_name
    if changes.document_number is not None:
        row.document_number = changes.document_number
    if changes.email is not None:
        row.email = changes.email
    if not isinstance(changes.phone, Unset):
        row.phone = changes.phone
    if not isinstance(changes.birth_date, Unset):
        row.birth_date = changes.birth_date


def _is_document_conflict(error: IntegrityError) -> bool:
    diag = getattr(error.orig, "diag", None)
    return getattr(diag, "constraint_name", None) == DOCUMENT_UNIQUE_CONSTRAINT


class SqlAlchemyPatientRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        *,
        scope: SessionScope | None = None,
    ) -> None:
        # Sin alcance propio cada operacion abre su transaccion; dentro de una unidad de trabajo
        # la sesion es compartida y la confirma la unidad (C-15).
        self._scope = scope if scope is not None else SessionScope(session_factory)

    def get(self, patient_id: str) -> Patient | None:
        key = parse_uuid(patient_id)
        if key is None:
            return None
        with self._scope.read() as session:
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

    def get_by_document(self, document_number: str) -> PatientRecord | None:
        query = select(PatientModel).where(PatientModel.document_number == document_number)
        with self._scope.read() as session:
            row = session.scalars(query).first()
            return None if row is None else _record(row)

    def get_record(self, patient_id: str) -> PatientRecord | None:
        key = parse_uuid(patient_id)
        if key is None:
            return None
        with self._scope.read() as session:
            row = session.get(PatientModel, key)
            return None if row is None else _record(row)

    def search(self, *, text: str, include_inactive: bool, limit: int) -> list[PatientRecord]:
        query = select(PatientModel)
        needle = text.strip()
        if needle:
            conditions = [PatientModel.last_name.icontains(needle, autoescape=True)]
            prefix = normalize_document_prefix(needle)
            if prefix is not None:
                conditions.append(PatientModel.document_number.startswith(prefix, autoescape=True))
            query = query.where(or_(*conditions))
        if not include_inactive:
            query = query.where(PatientModel.active.is_(True))
        query = query.order_by(
            PatientModel.last_name, PatientModel.first_name, PatientModel.id
        ).limit(limit)
        with self._scope.read() as session:
            return [_record(row) for row in session.scalars(query)]

    def add(self, patient: NewPatient) -> PatientRecord:
        row = PatientModel(
            first_name=patient.first_name,
            last_name=patient.last_name,
            document_number=patient.document_number,
            email=patient.email,
            phone=patient.phone,
            birth_date=patient.birth_date,
            active=True,
        )
        try:
            with self._scope.write() as session:
                session.add(row)
                session.flush()  # fuerza aca los errores de la base, dentro de la transaccion
                return _record(row)
        except IntegrityError as error:
            if _is_document_conflict(error):
                raise DocumentTakenError from None
            raise

    def update(self, patient_id: str, changes: PatientChanges) -> PatientRecord:
        key = parse_uuid(patient_id)
        if key is None:
            raise PatientNotFoundError
        try:
            with self._scope.write() as session:
                row = session.get(PatientModel, key)
                if row is None:
                    raise PatientNotFoundError
                _apply(row, changes)
                session.flush()  # fuerza aca los errores de la base, dentro de la transaccion
                return _record(row)
        except IntegrityError as error:
            if _is_document_conflict(error):
                raise DocumentTakenError from None
            raise

    def set_active(self, patient_id: str, active: bool) -> PatientRecord:
        key = parse_uuid(patient_id)
        if key is None:
            raise PatientNotFoundError
        with self._scope.write() as session:
            row = session.get(PatientModel, key)
            if row is None:
                raise PatientNotFoundError
            row.active = active
            session.flush()
            return _record(row)

    def delete(self, patient_id: str) -> bool:
        key = parse_uuid(patient_id)
        if key is None:
            return False
        try:
            with self._scope.write() as session:
                row = session.get(PatientModel, key)
                if row is None:
                    return False
                session.delete(row)
                session.flush()  # fuerza aca la clave foranea (ON DELETE RESTRICT, DD-39)
                return True
        except IntegrityError as error:
            if getattr(error.orig, "sqlstate", None) == FOREIGN_KEY_VIOLATION:
                raise PatientHasAppointmentsError from None
            raise
