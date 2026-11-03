"""Seguridad: hash y verificacion de contrasenas (argon2) y token de acceso JWT (PyJWT).

Viven en ``core`` y no en ``domain`` por coherencia con DD-41 (el dominio no importa librerias
de terceros). Los errores de token se traducen a ``NotAuthenticatedError`` (un solo codigo, P-5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.domain.auth import NotAuthenticatedError, Role

logger = logging.getLogger(__name__)

_hasher = PasswordHasher()
ALGORITHM = "HS256"
REQUIRED_CLAIMS = ["exp", "iat", "sub"]


def hash_password(plain: str) -> str:
    """Hash argon2 (con sal aleatoria) de una contrasena; nunca se guarda el texto plano."""
    return _hasher.hash(plain)


def verify_password(password_hash: str, plain: str) -> bool:
    """True si la contrasena coincide. Hash corrupto o no coincidencia dan False, sin excepcion."""
    try:
        return _hasher.verify(password_hash, plain)
    except InvalidHashError:
        # Un hash corrupto en la base no debe dar 500 en el login; sin datos sensibles en el log.
        logger.warning("Hash de contrasena con formato invalido en la base")
        return False
    except VerificationError:
        return False


@dataclass(frozen=True)
class TokenClaims:
    user_id: str
    role: Role


def create_access_token(
    *,
    user_id: str,
    role: Role,
    secret: str,
    expires_minutes: int,
    now: datetime | None = None,
    algorithm: str = ALGORITHM,
) -> str:
    """Token firmado con solo ``sub``, ``role``, ``iat`` y ``exp`` (sin email ni nombre)."""
    issued_at = now or datetime.now(UTC)
    payload = {
        "sub": user_id,
        "role": role.value,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(
    token: str,
    *,
    secret: str,
    now: datetime | None = None,
    algorithm: str = ALGORITHM,
) -> TokenClaims:
    """Valida firma, algoritmo (lista blanca), claims obligatorios y vencimiento.

    El reloj es inyectable: el vencimiento se compara aca contra ``now`` en lugar de dejarlo a
    PyJWT, que usa siempre la hora real.
    """
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={"require": REQUIRED_CLAIMS, "verify_exp": False},
        )
        expires_at = float(claims["exp"])
        token_claims = TokenClaims(user_id=str(claims["sub"]), role=Role(claims["role"]))
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError) as error:
        raise NotAuthenticatedError from error
    if expires_at <= (now or datetime.now(UTC)).timestamp():
        raise NotAuthenticatedError
    return token_claims
