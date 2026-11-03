"""Repositorio de cuentas sobre PostgreSQL (solo lectura, con el profesional asociado)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.auth import Role, UserAccount
from app.infrastructure.db.models import ProfessionalModel, UserModel
from app.infrastructure.db.repositories._ids import parse_uuid


def _account(user: UserModel, professional_id: object | None) -> UserAccount:
    return UserAccount(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        password_hash=user.password_hash,
        role=Role(user.role.value),
        active=user.active,
        professional_id=None if professional_id is None else str(professional_id),
    )


class SqlAlchemyUserAccountRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_by_email(self, email: str) -> UserAccount | None:
        # lower(email) usa el indice unico uq_users_email_lower (DD-38).
        statement = (
            select(UserModel, ProfessionalModel.id)
            .outerjoin(ProfessionalModel, ProfessionalModel.user_id == UserModel.id)
            .where(func.lower(UserModel.email) == email.lower())
        )
        with self._session_factory() as session:
            row = session.execute(statement).first()
        return None if row is None else _account(row[0], row[1])

    def get_by_id(self, user_id: str) -> UserAccount | None:
        key = parse_uuid(user_id)
        if key is None:
            return None
        statement = (
            select(UserModel, ProfessionalModel.id)
            .outerjoin(ProfessionalModel, ProfessionalModel.user_id == UserModel.id)
            .where(UserModel.id == key)
        )
        with self._session_factory() as session:
            row = session.execute(statement).first()
        return None if row is None else _account(row[0], row[1])
