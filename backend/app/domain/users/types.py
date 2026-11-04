"""Tipos de entrada de la escritura de cuentas (design D-1, D-2)."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.auth.types import Role


@dataclass(frozen=True)
class NewProfessional:
    """Datos de la ficha que se crea junto con una cuenta de odontologo."""

    display_name: str
    license_number: str | None = None


@dataclass(frozen=True)
class NewAccount:
    """Cuenta nueva; ``professional`` solo se informa para el rol ``dentist``."""

    email: str
    full_name: str
    password_hash: str
    role: Role
    professional: NewProfessional | None = None


@dataclass(frozen=True)
class AccountChanges:
    """Cambios parciales de una cuenta: ``None`` significa "no cambia".

    ``new_professional`` acompaña un cambio de rol a ``dentist`` para cuentas sin ficha.
    """

    full_name: str | None = None
    email: str | None = None
    role: Role | None = None
    active: bool | None = None
    password_hash: str | None = None
    new_professional: NewProfessional | None = None
