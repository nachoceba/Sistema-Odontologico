"""Puerto del repositorio de turnos (design D-1, D-4).

Los tipos se importan solo para anotar (TYPE_CHECKING): evita ciclos de imports (D-2).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from types import TracebackType
from typing import TYPE_CHECKING, Protocol, Self

if TYPE_CHECKING:
    from app.domain.appointments.types import (
        Appointment,
        AppointmentStatus,
        NewAppointment,
        Notification,
    )


class AppointmentRepository(Protocol):
    """Contrato de persistencia de turnos.

    Toda escritura que deje un turno scheduled se rechaza con SlotTakenError si se
    superpone con otro scheduled del mismo profesional (RN-TU-01, regla dura 6).
    Un id inexistente en change_status/reschedule lanza AppointmentNotFoundError.
    Instantes sin zona o rangos invertidos lanzan ValueError.
    """

    def add(self, new: NewAppointment) -> Appointment: ...

    def get(self, appointment_id: str) -> Appointment | None: ...

    def change_status(
        self,
        appointment_id: str,
        status: AppointmentStatus,
        cancel_reason: str | None = None,
    ) -> Appointment: ...

    def reschedule(
        self, appointment_id: str, starts_at: datetime, ends_at: datetime
    ) -> Appointment: ...

    def list_for_professional(
        self, professional_id: str, start: datetime, end: datetime | None = None
    ) -> list[Appointment]:
        """Turnos de cualquier estado que se superponen con [start, end), por inicio."""
        ...

    def list_for_patient(
        self, patient_id: str, start: datetime, end: datetime | None = None
    ) -> list[Appointment]:
        """Igual que list_for_professional, filtrando por paciente."""
        ...


class NotificationRepository(Protocol):
    """Registro de ``email_notifications``: alta, borrado y estado del envio (C-11)."""

    def add_pending_confirmation(
        self, appointment_id: str, starts_at: datetime
    ) -> Notification | None:
        """Registra una ``confirmation`` ``pending`` para el turno y su horario.

        Devuelve ``None`` si ya existia una con ese turno, tipo y horario (RN-NO-03).
        """
        ...

    def delete_pending(self, appointment_id: str, *, starts_at: datetime | None = None) -> int:
        """Borra las ``pending`` del turno (todas, o las de ese horario); devuelve cuantas.

        Nunca toca las ``sent`` ni las ``failed`` (historial, DD-62).
        """
        ...

    def list_for_appointment(self, appointment_id: str) -> list[Notification]:
        """Todas las notificaciones del turno, por horario del turno y tipo."""
        ...

    def list_pending_created_before(self, before: datetime, limit: int) -> list[Notification]:
        """Las ``pending`` creadas antes de ``before``, de la mas antigua, hasta ``limit``."""
        ...

    def claim_pending(self, notification_id: str) -> Notification | None:
        """Toma una ``pending`` para enviarla; nada si no existe, no es ``pending`` o la tiene otro.

        En PostgreSQL bloquea la fila hasta el fin de la transaccion (``FOR UPDATE SKIP LOCKED``):
        otro procesamiento simultaneo no espera, recibe ``None`` (design D-3).
        """
        ...

    def mark_sent(self, notification_id: str, sent_at: datetime) -> bool:
        """Marca ``sent`` una ``pending``; ``False`` (sin cambios) si no estaba ``pending``."""
        ...

    def mark_failed(self, notification_id: str, error: str) -> bool:
        """Marca ``failed`` con ``error`` una ``pending``; ``False`` si no estaba ``pending``."""
        ...


class AgendaUnitOfWork(Protocol):
    """Una transaccion que agrupa turnos y notificaciones (DD-36, D-2).

    Al salir del bloque ``with`` sin excepcion se confirma todo; con una excepcion se revierte
    todo. Las excepciones no se suprimen.
    """

    @property
    def appointments(self) -> AppointmentRepository: ...

    @property
    def notifications(self) -> NotificationRepository: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


class NotificationSendUnitOfWork(Protocol):
    """Transaccion del envio: toma la fila y lee el turno con la misma sesion (design D-3).

    Al salir sin excepcion se confirma; con una excepcion se revierte (la fila sigue ``pending``).
    Las unidades de trabajo de la agenda (memoria y PostgreSQL) ya cumplen este contrato.
    """

    @property
    def appointments(self) -> AppointmentRepository: ...

    @property
    def notifications(self) -> NotificationRepository: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


class NotificationDispatcher(Protocol):
    """Aviso posterior al commit (D-7): C-11 encola un ``enviar_email`` por notificacion."""

    def dispatch(self, notifications: Sequence[Notification]) -> None: ...
