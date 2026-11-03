"""Tipos de dominio de la autenticacion: roles, cuenta leida y principal de una request."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(Enum):
    """Roles del sistema (``03_actores_y_roles.md``); mismos valores que ``UserRole``."""

    ADMIN = "admin"
    RECEPTIONIST = "receptionist"
    DENTIST = "dentist"


@dataclass(frozen=True)
class UserAccount:
    """Cuenta de usuario tal como la lee el repositorio (incluye el hash: nunca sale de la API)."""

    id: str
    email: str
    full_name: str
    password_hash: str
    role: Role
    active: bool
    professional_id: str | None = None


@dataclass(frozen=True)
class Principal:
    """Lo que sabe una request autenticada: quien es, con que rol y cual es su ficha."""

    user_id: str
    role: Role
    professional_id: str | None = None
