"""Errores de la reserva online. Mensajes fijos: nunca nombran al paciente ni el motivo."""

from __future__ import annotations

from typing import ClassVar

from app.core.errors import DomainError


class SlotUnavailableError(DomainError):
    """El inicio no es reservable (grilla, horario, licencia, anticipacion u horizonte)."""

    code: ClassVar[str] = "SLOT_UNAVAILABLE"

    def __init__(self) -> None:
        super().__init__("Ese horario ya no está disponible. Elija otro.")


class BookingNotPossibleError(DomainError):
    """Rechazo generico: nombre que no coincide, paciente inactivo, turno superpuesto o carrera."""

    code: ClassVar[str] = "BOOKING_NOT_POSSIBLE"

    def __init__(self) -> None:
        super().__init__("Verifique sus datos ingresados.")


class ConfirmationLinkInvalidError(DomainError):
    code: ClassVar[str] = "CONFIRMATION_LINK_INVALID"

    def __init__(self) -> None:
        super().__init__("El enlace no es válido o ya venció.")


class PendingConfirmationError(DomainError):
    code: ClassVar[str] = "PENDING_CONFIRMATION"

    def __init__(self) -> None:
        super().__init__("Este turno espera la confirmación del paciente.")


class BookingRejectedError(DomainError):
    code: ClassVar[str] = "BOOKING_REJECTED"

    def __init__(self) -> None:
        super().__init__("No se pudo procesar la solicitud.")


class TooManyRequestsError(DomainError):
    code: ClassVar[str] = "TOO_MANY_REQUESTS"

    def __init__(self, retry_after: int) -> None:
        super().__init__("Demasiados pedidos. Espere un rato y vuelva a probar.")
        self.retry_after = retry_after
