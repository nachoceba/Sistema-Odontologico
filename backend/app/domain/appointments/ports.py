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
    from app.domain.patients.ports import PatientRepository


class AppointmentRepository(Protocol):
    """Contrato de persistencia de turnos.

    Toda escritura que deje un turno scheduled se rechaza con SlotTakenError si se
    superpone con otro scheduled del mismo profesional (RN-TU-01, regla dura 6).
    Un id inexistente en change_status/reschedule lanza AppointmentNotFoundError.
    Instantes sin zona o rangos invertidos lanzan ValueError.
    """

    def add(self, new: NewAppointment) -> Appointment: ...

    def add_pending(
        self, new: NewAppointment, token_hash: str, pending_until: datetime
    ) -> Appointment:
        """Guarda un turno online ``scheduled`` pendiente de confirmacion (C-15, DD-130).

        ``new.created_by`` debe ser ``None``. Misma garantia anti-superposicion que ``add``. El
        hash del token queda guardado pero nunca sale en el ``Appointment``.
        """
        ...

    def confirm_by_token_hash(self, token_hash: str, now: datetime) -> Appointment | None:
        """Confirma el turno pendiente con ese hash y devuelve el turno ya confirmado.

        Toma la fila con bloqueo. Devuelve ``None``, sin cambiar nada, si el hash no existe o el
        turno no se puede confirmar (vencido, cancelado o ya empezado). Al confirmar borra
        ``pending_until`` y el hash: el token sirve una sola vez.
        """
        ...

    def find_pending_by_token_hash(self, token_hash: str, now: datetime) -> Appointment | None:
        """El turno pendiente con ese hash si todavia se puede confirmar; sin cambiar nada."""
        ...

    def expire_pending(self, now: datetime, limit: int = 200) -> list[Appointment]:
        """Cancela los turnos ``scheduled`` pendientes cuyo ``pending_until`` es ``<= now``.

        Cada uno queda ``cancelled`` con el motivo ``EXPIRED_BOOKING_REASON`` y sin
        ``pending_until`` ni hash. Atiende hasta ``limit`` por llamada, del vencimiento mas
        antiguo al mas nuevo. En PostgreSQL toma las filas con ``FOR UPDATE SKIP LOCKED``: una
        fila que otro proceso tiene tomada (por ejemplo una confirmacion en curso) se saltea.
        Devuelve los turnos cancelados, tal como eran al vencer (inicio incluido). Nunca toca
        turnos confirmados ni de la recepcion (C-16, DD-132).
        """
        ...

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

    def list_scheduled_starting_between(self, start: datetime, end: datetime) -> list[Appointment]:
        """Turnos ``scheduled`` confirmados de todos los profesionales que EMPIEZAN en [start, end).

        Excluye los pendientes de confirmacion (C-15): no reciben recordatorio.

        Criterio por inicio y no por superposicion (DD-66): orden ``(starts_at, id)``. Ambos
        limites son obligatorios; sin zona o ``start >= end`` lanza ``ValueError``.
        """
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

    def add_pending_booking_expired(
        self, appointment_id: str, starts_at: datetime
    ) -> Notification | None:
        """Registra un ``booking_expired`` ``pending`` para el turno y su horario (C-16, DD-140).

        Devuelve ``None`` si ya existia uno con ese turno, tipo y horario (RN-NO-03). Se llama
        en la misma unidad de trabajo que la cancelacion por vencimiento.
        """
        ...

    def add_pending_reminder(self, appointment_id: str, starts_at: datetime) -> Notification | None:
        """Registra un ``reminder`` ``pending`` solo si el turno sigue vigente con ese horario.

        Devuelve ``None``, sin error, si el turno no existe, ya no esta ``scheduled``, ahora
        empieza en otro horario, o si ya existia un ``reminder`` de ese turno y horario en
        cualquier estado (RN-NO-03). En PostgreSQL espera a una reprogramacion o cancelacion en
        curso y decide con el dato confirmado (``FOR SHARE``, design D-4).
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
    """Una transaccion que agrupa turnos, notificaciones y pacientes (DD-36, D-2, C-15).

    Al salir del bloque ``with`` sin excepcion se confirma todo; con una excepcion se revierte
    todo. Las excepciones no se suprimen.
    """

    @property
    def appointments(self) -> AppointmentRepository: ...

    @property
    def notifications(self) -> NotificationRepository: ...

    @property
    def patients(self) -> PatientRepository: ...

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
