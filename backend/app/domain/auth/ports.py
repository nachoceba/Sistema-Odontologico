"""Puerto del repositorio de cuentas: solo lectura (la escritura llega con C-04)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.auth.types import UserAccount


class UserAccountRepository(Protocol):
    def get_by_email(self, email: str) -> UserAccount | None:
        """La cuenta con ese email sin distinguir mayusculas, o None (incluye desactivadas)."""
        ...

    def get_by_id(self, user_id: str) -> UserAccount | None:
        """La cuenta con ese id, o None si no existe o el id esta mal formado."""
        ...
