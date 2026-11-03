"""Dominio de autenticacion y control de acceso (C-03)."""

from app.domain.auth.errors import ForbiddenError, InvalidCredentialsError, NotAuthenticatedError
from app.domain.auth.ports import UserAccountRepository
from app.domain.auth.rules import can_access_professional
from app.domain.auth.types import Principal, Role, UserAccount

__all__ = [
    "ForbiddenError",
    "InvalidCredentialsError",
    "NotAuthenticatedError",
    "Principal",
    "Role",
    "UserAccount",
    "UserAccountRepository",
    "can_access_professional",
]
