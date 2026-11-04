"""Endpoints de gestion de usuarios, solo para el administrador (spec user-management, D-5).

Toda la ruta exige sesion y rol ``admin`` (``require_role`` a nivel del router). Ninguna
respuesta incluye el hash ni la contrasena (RN-PR-03, DD-41).
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import AfterValidator, BaseModel, BeforeValidator, Field

from app.api.dependencies import UserRepository, require_role
from app.api.validators import strip_text
from app.application import users as use_cases
from app.domain.auth import Principal, Role, UserAccount
from app.domain.users.rules import is_valid_email

_admin_only = require_role(Role.ADMIN)
AdminUser = Annotated[Principal, Depends(_admin_only)]

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(_admin_only)])


def _check_email(value: str) -> str:
    if not is_valid_email(value):
        raise ValueError("El email no tiene un formato válido")
    return value


Email = Annotated[
    str,
    BeforeValidator(strip_text),
    Field(min_length=3, max_length=254),
    AfterValidator(_check_email),
]
FullName = Annotated[str, BeforeValidator(strip_text), Field(min_length=1, max_length=200)]
DisplayName = Annotated[str, BeforeValidator(strip_text), Field(min_length=1, max_length=200)]
LicenseNumber = Annotated[str, BeforeValidator(strip_text), Field(min_length=1, max_length=50)]
# La contrasena NO se recorta: se guarda tal como la escribio el administrador.
Password = Annotated[str, Field(min_length=8, max_length=128)]
RoleName = Literal["admin", "receptionist", "dentist"]


class ManagedUserOut(BaseModel):
    """Una cuenta tal como la ve el administrador: sin hash ni contrasena."""

    id: str
    email: str
    full_name: str
    role: RoleName
    active: bool
    professional_id: str | None

    @classmethod
    def from_account(cls, account: UserAccount) -> ManagedUserOut:
        return cls(
            id=account.id,
            email=account.email,
            full_name=account.full_name,
            role=account.role.value,
            active=account.active,
            professional_id=account.professional_id,
        )


class CreateUserRequest(BaseModel):
    email: Email
    full_name: FullName
    role: RoleName
    password: Password
    display_name: DisplayName | None = None
    license_number: LicenseNumber | None = None


class UpdateUserRequest(BaseModel):
    """Los campos no enviados (o ``null``) no cambian."""

    full_name: FullName | None = None
    email: Email | None = None
    role: RoleName | None = None


class SetPasswordRequest(BaseModel):
    password: Password


@router.get("")
def list_users(repo: UserRepository) -> list[ManagedUserOut]:
    return [ManagedUserOut.from_account(account) for account in use_cases.list_users(repo)]


@router.post("", status_code=201)
def create_user(body: CreateUserRequest, repo: UserRepository) -> ManagedUserOut:
    account = use_cases.create_user(
        repo,
        email=body.email,
        full_name=body.full_name,
        role=Role(body.role),
        password=body.password,
        display_name=body.display_name,
        license_number=body.license_number,
    )
    return ManagedUserOut.from_account(account)


@router.patch("/{user_id}")
def update_user(
    user_id: str, body: UpdateUserRequest, repo: UserRepository, principal: AdminUser
) -> ManagedUserOut:
    account = use_cases.update_user(
        repo,
        principal,
        user_id,
        full_name=body.full_name,
        email=body.email,
        role=None if body.role is None else Role(body.role),
    )
    return ManagedUserOut.from_account(account)


@router.post("/{user_id}/deactivate")
def deactivate_user(user_id: str, repo: UserRepository, principal: AdminUser) -> ManagedUserOut:
    return ManagedUserOut.from_account(use_cases.deactivate_user(repo, principal, user_id))


@router.post("/{user_id}/reactivate")
def reactivate_user(user_id: str, repo: UserRepository) -> ManagedUserOut:
    return ManagedUserOut.from_account(use_cases.reactivate_user(repo, user_id))


@router.put("/{user_id}/password", status_code=204)
def set_password(user_id: str, body: SetPasswordRequest, repo: UserRepository) -> Response:
    use_cases.set_password(repo, user_id, body.password)
    return Response(status_code=204)
