"""Repositorio de profesionales sobre PostgreSQL (solo lectura, design D-8)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.appointments.errors import ProfessionalNotFoundError
from app.domain.professionals import UNSET, Professional, Unset
from app.infrastructure.db.models import ProfessionalModel
from app.infrastructure.db.repositories._ids import parse_uuid


def _professional(row: ProfessionalModel) -> Professional:
    return Professional(
        id=str(row.id),
        user_id=str(row.user_id),
        display_name=row.display_name,
        license_number=row.license_number,
        active=row.active,
    )


class SqlAlchemyProfessionalRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list(self, *, only_active: bool = False) -> list[Professional]:
        statement = select(ProfessionalModel).order_by(
            func.lower(ProfessionalModel.display_name), ProfessionalModel.id
        )
        if only_active:
            statement = statement.where(ProfessionalModel.active.is_(True))
        with self._session_factory() as session:
            rows = session.scalars(statement).all()
        return [_professional(row) for row in rows]

    def get_by_id(self, professional_id: str) -> Professional | None:
        key = parse_uuid(professional_id)
        if key is None:
            return None
        with self._session_factory() as session:
            row = session.get(ProfessionalModel, key)
        return None if row is None else _professional(row)

    def update(
        self,
        professional_id: str,
        *,
        display_name: str | None = None,
        license_number: str | None | Unset = UNSET,
    ) -> Professional:
        key = parse_uuid(professional_id)
        if key is None:
            raise ProfessionalNotFoundError
        with self._session_factory.begin() as session:
            row = session.get(ProfessionalModel, key)
            if row is None:
                raise ProfessionalNotFoundError
            if display_name is not None:
                row.display_name = display_name
            if not isinstance(license_number, Unset):
                row.license_number = license_number
            session.flush()
            return _professional(row)
