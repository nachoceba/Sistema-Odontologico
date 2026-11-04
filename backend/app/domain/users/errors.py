"""Errores de la gestion de usuarios; los mensajes son los de la pantalla (spec frontend)."""

from __future__ import annotations

from typing import ClassVar

from app.core.errors import DomainError


class UserNotFoundError(DomainError):
    code: ClassVar[str] = "USER_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__("El usuario ya no existe")


class EmailTakenError(DomainError):
    code: ClassVar[str] = "EMAIL_TAKEN"

    def __init__(self) -> None:
        super().__init__("Ya existe un usuario con ese email")


class RoleChangeNotAllowedError(DomainError):
    code: ClassVar[str] = "ROLE_CHANGE_NOT_ALLOWED"

    def __init__(self) -> None:
        super().__init__("No se puede cambiar el rol de un odontólogo")


class SelfModificationError(DomainError):
    code: ClassVar[str] = "SELF_MODIFICATION_NOT_ALLOWED"

    def __init__(self) -> None:
        super().__init__("No podés desactivar ni cambiar el rol de tu propia cuenta")
