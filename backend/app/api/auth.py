"""Endpoints de autenticacion: login publico (D-9)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, BeforeValidator, Field

from app.api.dependencies import CurrentUser, TokenSettings, UserRepository
from app.api.validators import strip_text
from app.application.auth import authenticate
from app.domain.auth import NotAuthenticatedError, UserAccount

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    # El email se recorta (P-6); la contrasena NO se recorta.
    email: Annotated[str, BeforeValidator(strip_text), Field(min_length=1, max_length=254)]
    password: Annotated[str, Field(min_length=1, max_length=128)]


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    professional_id: str | None

    @classmethod
    def from_account(cls, account: UserAccount) -> UserOut:
        return cls(
            id=account.id,
            email=account.email,
            full_name=account.full_name,
            role=account.role.value,
            professional_id=account.professional_id,
        )


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserOut


@router.post("/login")
def login(body: LoginRequest, repo: UserRepository, config: TokenSettings) -> LoginResponse:
    token, account = authenticate(body.email, body.password, repo, config)
    return LoginResponse(
        access_token=token,
        token_type="bearer",  # noqa: S106
        expires_in=config.expires_minutes * 60,
        user=UserOut.from_account(account),
    )


@router.get("/me")
def me(principal: CurrentUser, repo: UserRepository) -> UserOut:
    """Datos publicos de la cuenta autenticada (P-9); lee la cuenta vigente, no el token."""
    account = repo.get_by_id(principal.user_id)
    if account is None:  # la cuenta se borro entre la validacion y esta lectura
        raise NotAuthenticatedError
    return UserOut.from_account(account)
