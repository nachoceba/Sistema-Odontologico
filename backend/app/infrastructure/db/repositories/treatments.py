"""Repositorio de tratamientos sobre PostgreSQL (C-17, D-2).

El nombre unico lo garantiza ``uq_treatments_name_key``: se escribe y se traduce la violacion a
``TreatmentNameTakenError`` (igual que ``DocumentTakenError`` con el documento). ``name_key`` lo
calcula el dominio.
"""

from __future__ import annotations

from collections.abc import Sequence

from psycopg import errors as pg_errors
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.treatments.errors import TreatmentNameTakenError, TreatmentNotFoundError
from app.domain.treatments.rules import treatment_name_key
from app.domain.treatments.types import NewTreatment, Treatment
from app.infrastructure.db.models import ProfessionalTreatmentModel, TreatmentModel
from app.infrastructure.db.repositories._ids import parse_uuid

_ORDER = (TreatmentModel.name_key, TreatmentModel.id)


def _treatment(row: TreatmentModel) -> Treatment:
    return Treatment(id=str(row.id), name=row.name, active=row.active)


class SqlAlchemyTreatmentRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_all(self) -> list[Treatment]:
        with self._session_factory() as session:
            rows = session.scalars(select(TreatmentModel).order_by(*_ORDER)).all()
        return [_treatment(row) for row in rows]

    def get(self, treatment_id: str) -> Treatment | None:
        key = parse_uuid(treatment_id)
        if key is None:
            return None
        with self._session_factory() as session:
            row = session.get(TreatmentModel, key)
        return None if row is None else _treatment(row)

    def add(self, new: NewTreatment) -> Treatment:
        row = TreatmentModel(name=new.name, name_key=treatment_name_key(new.name))
        try:
            with self._session_factory.begin() as session:
                session.add(row)
                session.flush()
                return _treatment(row)
        except IntegrityError as error:
            if isinstance(error.orig, pg_errors.UniqueViolation):
                raise TreatmentNameTakenError from error
            raise

    def update(
        self, treatment_id: str, *, name: str | None = None, active: bool | None = None
    ) -> Treatment:
        key = parse_uuid(treatment_id)
        if key is None:
            raise TreatmentNotFoundError
        try:
            with self._session_factory.begin() as session:
                row = session.get(TreatmentModel, key, with_for_update=True)
                if row is None:
                    raise TreatmentNotFoundError
                if name is not None:
                    row.name = name
                    row.name_key = treatment_name_key(name)
                if active is not None:
                    row.active = active
                session.flush()
                return _treatment(row)
        except IntegrityError as error:
            if isinstance(error.orig, pg_errors.UniqueViolation):
                raise TreatmentNameTakenError from error
            raise

    def list_for_professional(self, professional_id: str) -> list[Treatment]:
        return self._assigned(professional_id, only_active=False)

    def offered_ids(self, professional_id: str) -> frozenset[str]:
        return frozenset(t.id for t in self._assigned(professional_id, only_active=True))

    def list_offered(self, professional_id: str) -> list[Treatment]:
        return self._assigned(professional_id, only_active=True)

    def replace_for_professional(self, professional_id: str, treatment_ids: Sequence[str]) -> None:
        owner = parse_uuid(professional_id)
        if owner is None:
            raise ValueError("identificador de profesional invalido")
        wanted = set()
        for treatment_id in treatment_ids:
            key = parse_uuid(treatment_id)
            if key is None:
                raise TreatmentNotFoundError
            wanted.add(key)
        with self._session_factory.begin() as session:
            session.execute(
                delete(ProfessionalTreatmentModel).where(
                    ProfessionalTreatmentModel.professional_id == owner
                )
            )
            session.add_all(
                ProfessionalTreatmentModel(professional_id=owner, treatment_id=key)
                for key in wanted
            )

    def _assigned(self, professional_id: str, *, only_active: bool) -> list[Treatment]:
        owner = parse_uuid(professional_id)
        if owner is None:
            return []
        query = (
            select(TreatmentModel)
            .join(
                ProfessionalTreatmentModel,
                ProfessionalTreatmentModel.treatment_id == TreatmentModel.id,
            )
            .where(ProfessionalTreatmentModel.professional_id == owner)
            .order_by(*_ORDER)
        )
        if only_active:
            query = query.where(TreatmentModel.active.is_(True))
        with self._session_factory() as session:
            return [_treatment(row) for row in session.scalars(query)]
