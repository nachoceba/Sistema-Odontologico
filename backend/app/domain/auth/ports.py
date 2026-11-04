"""Puerto del repositorio de cuentas: lectura (C-03) y escritura (C-04, design D-2)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.auth.types import UserAccount
    from app.domain.users.types import AccountChanges, NewAccount


class UserAccountRepository(Protocol):
    def get_by_email(self, email: str) -> UserAccount | None:
        """La cuenta con ese email sin distinguir mayusculas, o None (incluye desactivadas)."""
        ...

    def get_by_id(self, user_id: str) -> UserAccount | None:
        """La cuenta con ese id, o None si no existe o el id esta mal formado."""
        ...

    def list_all(self) -> list[UserAccount]:
        """Todas las cuentas (activas o no), ordenadas por nombre sin distinguir mayusculas."""
        ...

    def create(self, account: NewAccount) -> UserAccount:
        """Crea la cuenta activa (y su ficha si trae ``professional``) en una sola operacion.

        Lanza ``EmailTakenError`` si el email ya existe sin distinguir mayusculas.
        """
        ...

    def update(self, user_id: str, changes: AccountChanges) -> UserAccount:
        """Aplica los cambios y devuelve la cuenta; efectos sobre la ficha en la misma operacion.

        Lanza ``UserNotFoundError`` (id inexistente o mal formado) o ``EmailTakenError``.
        """
        ...
