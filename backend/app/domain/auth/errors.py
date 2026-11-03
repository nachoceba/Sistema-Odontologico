"""Errores de autenticacion y autorizacion (mensajes genericos, P-5)."""

from __future__ import annotations

from typing import ClassVar

from app.core.errors import DomainError


class InvalidCredentialsError(DomainError):
    """Email inexistente, contrasena incorrecta o cuenta desactivada: un solo mensaje."""

    code: ClassVar[str] = "INVALID_CREDENTIALS"

    def __init__(self) -> None:
        super().__init__("Email o contraseña incorrectos")


class NotAuthenticatedError(DomainError):
    """Sin sesion, sesion vencida o invalida."""

    code: ClassVar[str] = "NOT_AUTHENTICATED"

    def __init__(self) -> None:
        super().__init__("Tu sesión terminó. Volvé a ingresar")


class ForbiddenError(DomainError):
    """Con sesion pero sin permiso; el mensaje no revela datos del recurso."""

    code: ClassVar[str] = "FORBIDDEN"

    def __init__(self) -> None:
        super().__init__("No tenés permiso para esta acción")
