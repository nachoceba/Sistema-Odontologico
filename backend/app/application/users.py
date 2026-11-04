"""Casos de uso de la gestion de usuarios por el administrador (design D-4, sin FastAPI).

Reciben el repositorio y, cuando la regla lo pide, el ``Principal`` del administrador (para
saber si el pedido es sobre su propia cuenta). Nunca devuelven el texto de una contrasena.
"""

from __future__ import annotations

from app.core.security import hash_password
from app.domain.auth import Principal, Role, UserAccount, UserAccountRepository
from app.domain.users.errors import UserNotFoundError
from app.domain.users.rules import (
    check_can_deactivate,
    check_role_change,
    normalize_email,
    professional_for_new_dentist,
)
from app.domain.users.types import AccountChanges, NewAccount


def _load(repo: UserAccountRepository, user_id: str) -> UserAccount:
    account = repo.get_by_id(user_id)
    if account is None:
        raise UserNotFoundError
    return account


def list_users(repo: UserAccountRepository) -> list[UserAccount]:
    return repo.list_all()


def create_user(
    repo: UserAccountRepository,
    *,
    email: str,
    full_name: str,
    role: Role,
    password: str,
    display_name: str | None = None,
    license_number: str | None = None,
) -> UserAccount:
    """Alta con contrasena inicial; la ficha solo se crea para el rol ``dentist`` (P-10)."""
    professional = (
        professional_for_new_dentist(full_name, display_name, license_number)
        if role is Role.DENTIST
        else None
    )
    return repo.create(
        NewAccount(
            email=normalize_email(email),
            full_name=full_name,
            password_hash=hash_password(password),
            role=role,
            professional=professional,
        )
    )


def update_user(
    repo: UserAccountRepository,
    principal: Principal,
    user_id: str,
    *,
    full_name: str | None = None,
    email: str | None = None,
    role: Role | None = None,
) -> UserAccount:
    """Edita nombre, email y rol; los campos en ``None`` no cambian (P-3, P-4, P-5)."""
    account = _load(repo, user_id)
    new_role: Role | None = None
    new_professional = None
    if role is not None and role is not account.role:
        check_role_change(account.role, role, is_self=account.id == principal.user_id)
        new_role = role
        if role is Role.DENTIST and account.professional_id is None:
            new_professional = professional_for_new_dentist(
                full_name or account.full_name, None, None
            )
    return repo.update(
        account.id,
        AccountChanges(
            full_name=full_name,
            email=None if email is None else normalize_email(email),
            role=new_role,
            new_professional=new_professional,
        ),
    )


def deactivate_user(repo: UserAccountRepository, principal: Principal, user_id: str) -> UserAccount:
    account = _load(repo, user_id)
    check_can_deactivate(is_self=account.id == principal.user_id)
    return repo.update(account.id, AccountChanges(active=False))


def reactivate_user(repo: UserAccountRepository, user_id: str) -> UserAccount:
    account = _load(repo, user_id)
    return repo.update(account.id, AccountChanges(active=True))


def set_password(repo: UserAccountRepository, user_id: str, password: str) -> None:
    account = _load(repo, user_id)
    repo.update(account.id, AccountChanges(password_hash=hash_password(password)))
