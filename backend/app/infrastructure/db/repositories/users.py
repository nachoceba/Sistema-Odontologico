"""Repositorio de cuentas sobre PostgreSQL: lectura y escritura con la ficha asociada.

Cada operacion de escritura usa **una** transaccion (``session.begin()``): cuenta y ficha se
guardan juntas o no se guarda nada (design D-3). La unicidad del email la decide el indice
``uq_users_email_lower``; su violacion se traduce a ``EmailTakenError``.
"""

from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.auth import Role, UserAccount
from app.domain.users.errors import EmailTakenError, UserNotFoundError
from app.domain.users.types import AccountChanges, NewAccount, NewProfessional
from app.infrastructure.db.enums import UserRole
from app.infrastructure.db.models import ProfessionalModel, UserModel
from app.infrastructure.db.repositories._ids import parse_uuid

EMAIL_UNIQUE_INDEX = "uq_users_email_lower"


def _account(user: UserModel, professional: ProfessionalModel | None) -> UserAccount:
    return UserAccount(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        password_hash=user.password_hash,
        role=Role(user.role.value),
        active=user.active,
        professional_id=None if professional is None else str(professional.id),
    )


def _accounts_query() -> Select[UserModel, ProfessionalModel]:
    """Cuentas con su ficha (si tienen): la consulta que comparten todas las lecturas."""
    return select(UserModel, ProfessionalModel).outerjoin(
        ProfessionalModel, ProfessionalModel.user_id == UserModel.id
    )


def _is_email_conflict(error: IntegrityError) -> bool:
    diag = getattr(error.orig, "diag", None)
    return getattr(diag, "constraint_name", None) == EMAIL_UNIQUE_INDEX


def _new_professional_row(user_id: object, data: NewProfessional) -> ProfessionalModel:
    return ProfessionalModel(
        user_id=user_id, display_name=data.display_name, license_number=data.license_number
    )


class SqlAlchemyUserAccountRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_by_email(self, email: str) -> UserAccount | None:
        # lower(email) usa el indice unico uq_users_email_lower (DD-38).
        statement = _accounts_query().where(func.lower(UserModel.email) == email.lower())
        with self._session_factory() as session:
            row = session.execute(statement).first()
        return None if row is None else _account(row[0], row[1])

    def get_by_id(self, user_id: str) -> UserAccount | None:
        key = parse_uuid(user_id)
        if key is None:
            return None
        statement = _accounts_query().where(UserModel.id == key)
        with self._session_factory() as session:
            row = session.execute(statement).first()
        return None if row is None else _account(row[0], row[1])

    def list_all(self) -> list[UserAccount]:
        statement = _accounts_query().order_by(func.lower(UserModel.full_name), UserModel.id)
        with self._session_factory() as session:
            rows = session.execute(statement).all()
        return [_account(user, professional) for user, professional in rows]

    def create(self, account: NewAccount) -> UserAccount:
        user = UserModel(
            email=account.email,
            password_hash=account.password_hash,
            full_name=account.full_name,
            role=UserRole(account.role.value),
        )
        professional: ProfessionalModel | None = None
        try:
            with self._session_factory.begin() as session:
                session.add(user)
                session.flush()  # la base genera el id (DD-37) que necesita la ficha
                if account.professional is not None:
                    professional = _new_professional_row(user.id, account.professional)
                    session.add(professional)
                    session.flush()
                return _account(user, professional)
        except IntegrityError as error:
            if _is_email_conflict(error):
                raise EmailTakenError from error
            raise

    def update(self, user_id: str, changes: AccountChanges) -> UserAccount:
        key = parse_uuid(user_id)
        if key is None:
            raise UserNotFoundError
        statement = _accounts_query().where(UserModel.id == key)
        try:
            with self._session_factory.begin() as session:
                row = session.execute(statement).first()
                if row is None:
                    raise UserNotFoundError
                user: UserModel = row[0]
                professional: ProfessionalModel | None = row[1]
                self._apply(user, changes)
                if professional is None and changes.new_professional is not None:
                    professional = _new_professional_row(user.id, changes.new_professional)
                    professional.active = user.active
                    session.add(professional)
                elif professional is not None and changes.active is not None:
                    professional.active = changes.active
                session.flush()  # fuerza aca los errores de la base, dentro de la transaccion
                return _account(user, professional)
        except IntegrityError as error:
            if _is_email_conflict(error):
                raise EmailTakenError from error
            raise

    @staticmethod
    def _apply(user: UserModel, changes: AccountChanges) -> None:
        if changes.full_name is not None:
            user.full_name = changes.full_name
        if changes.email is not None:
            user.email = changes.email
        if changes.role is not None:
            user.role = UserRole(changes.role.value)
        if changes.active is not None:
            user.active = changes.active
        if changes.password_hash is not None:
            user.password_hash = changes.password_hash
