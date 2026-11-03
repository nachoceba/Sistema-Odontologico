"""Casos de uso de autenticacion: login y resolucion del principal (sin FastAPI)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.domain.auth import (
    InvalidCredentialsError,
    NotAuthenticatedError,
    Principal,
    UserAccount,
    UserAccountRepository,
)


@dataclass(frozen=True)
class TokenConfig:
    secret: str
    expires_minutes: int
    algorithm: str = "HS256"

    @classmethod
    def from_settings(cls, settings: Settings) -> TokenConfig:
        return cls(
            secret=settings.JWT_SECRET_KEY.get_secret_value(),
            expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            algorithm=settings.JWT_ALGORITHM,
        )


@lru_cache
def _dummy_hash() -> str:
    """Hash ficticio para igualar el tiempo de respuesta cuando el email no existe (D-3)."""
    return hash_password("contrasena-ficticia-para-igualar-tiempos")


def authenticate(
    email: str,
    password: str,
    repo: UserAccountRepository,
    config: TokenConfig,
    now: datetime | None = None,
) -> tuple[str, UserAccount]:
    """Valida credenciales y emite el token. Los tres fallos son el mismo error (P-5)."""
    account = repo.get_by_email(email.strip().lower())
    hash_to_check = account.password_hash if account is not None else _dummy_hash()
    password_ok = verify_password(hash_to_check, password)
    if account is None or not password_ok or not account.active:
        raise InvalidCredentialsError
    token = create_access_token(
        user_id=account.id,
        role=account.role,
        secret=config.secret,
        expires_minutes=config.expires_minutes,
        now=now,
        algorithm=config.algorithm,
    )
    return token, account


def resolve_principal(
    token: str,
    repo: UserAccountRepository,
    config: TokenConfig,
    now: datetime | None = None,
) -> Principal:
    """Token valido + cuenta existente, activa y con el mismo rol (P-8, RN-AU-03)."""
    claims = decode_access_token(token, secret=config.secret, now=now, algorithm=config.algorithm)
    account = repo.get_by_id(claims.user_id)
    if account is None or not account.active or account.role is not claims.role:
        raise NotAuthenticatedError
    return Principal(user_id=account.id, role=account.role, professional_id=account.professional_id)
